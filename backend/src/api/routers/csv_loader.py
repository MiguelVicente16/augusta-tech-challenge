"""
CSV Loading Router

Endpoints for loading incentives and companies data from CSV files.
"""

import logging
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field

from ..dependencies import get_db_service
from ..services.csv_service import CSVLoadingService
from ...config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


# Request/Response models
class LoadCSVRequest(BaseModel):
    """Request model for CSV loading"""
    file_name: str = Field(..., description="Name of the CSV file in data/ folder")
    csv_type: str = Field(..., description="Type of CSV: 'incentives' or 'companies'")
    enable_ai_generation: bool = Field(
        default=False,
        description="Enable AI-powered structured description generation (incentives only)"
    )
    ai_provider: str = Field(
        default=None,
        description="AI provider to use: 'openai' or 'gemini' (defaults to config setting)"
    )
    batch_size: int = Field(default=1000, description="Batch size for processing", ge=1, le=5000)

    def get_ai_provider(self) -> str:
        """Get AI provider, falling back to config if not specified"""
        return self.ai_provider or settings.AI_PROVIDER


class LoadCSVResponse(BaseModel):
    """Response model for CSV loading"""
    status: str
    message: str
    total_rows: int = 0
    valid_rows: int = 0
    error_rows: int = 0
    ai_usage: str = None
    ai_provider: str = None


class LoadAllCSVsRequest(BaseModel):
    """Request model for loading all CSVs"""
    enable_ai_generation: bool = Field(
        default=False,
        description="Enable AI-powered structured description generation"
    )
    ai_provider: str = Field(
        default=None,
        description="AI provider to use: 'openai' or 'gemini' (defaults to config setting)"
    )
    batch_size: int = Field(default=1000, description="Batch size for processing", ge=1, le=5000)

    def get_ai_provider(self) -> str:
        """Get AI provider, falling back to config if not specified"""
        return self.ai_provider or settings.AI_PROVIDER


@router.post("/load-csv", response_model=LoadCSVResponse)
async def load_csv(
    request: LoadCSVRequest,
    db_service = Depends(get_db_service)
):
    """
    Load CSV file into database

    Supports loading:
    - incentives.csv: Public incentives data
    - companies.csv: Companies data

    Optional AI generation for structured descriptions (incentives only).
    """
    try:
        logger.info(f"Loading {request.csv_type} CSV: {request.file_name}")

        # Initialize service
        csv_service = CSVLoadingService(db_service)

        # Get file path
        file_path = Path("data") / request.file_name

        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"CSV file not found: {file_path}"
            )

        # Load based on type
        if request.csv_type == "incentives":
            result = await csv_service.load_incentives(
                file_path=file_path,
                enable_ai_generation=request.enable_ai_generation,
                batch_size=request.batch_size,
                ai_provider=request.get_ai_provider()
            )
        elif request.csv_type == "companies":
            result = await csv_service.load_companies(
                file_path=file_path,
                batch_size=request.batch_size
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid csv_type: {request.csv_type}. Must be 'incentives' or 'companies'"
            )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Unknown error during CSV loading")
            )

        return LoadCSVResponse(
            status="success",
            message=f"Successfully loaded {request.csv_type} CSV",
            total_rows=result.get("total_rows", 0),
            valid_rows=result.get("valid_rows", 0),
            error_rows=result.get("error_rows", 0),
            ai_usage=result.get("ai_usage"),
            ai_provider=request.get_ai_provider() if request.csv_type == "incentives" else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load-all-csvs")
async def load_all_csvs(
    request: LoadAllCSVsRequest,
    db_service = Depends(get_db_service)
):
    """
    Load all CSV files (incentives + companies)

    Loads both incentives.csv and companies.csv from the data/ folder.
    Optional AI generation for structured descriptions.
    """
    try:
        logger.info("Loading all CSV files...")

        # Initialize service
        csv_service = CSVLoadingService(db_service)

        # Load all CSVs
        result = await csv_service.load_all(
            enable_ai_generation=request.enable_ai_generation,
            batch_size=request.batch_size,
            ai_provider=request.get_ai_provider()
        )

        return {
            "status": "success" if result.get("overall_success") else "partial_success",
            "message": "CSV loading completed",
            "incentives": result.get("incentives"),
            "companies": result.get("companies")
        }

    except Exception as e:
        logger.error(f"Error loading all CSVs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh-incentives")
async def refresh_incentives(
    enable_ai_generation: bool = False,
    batch_size: int = 1000,
    db_service = Depends(get_db_service)
):
    """
    Refresh incentives table

    Clears incentives table and reloads from CSV.
    Keeps companies and matches intact.
    """
    try:
        logger.info("Refreshing incentives table...")

        # Drop and recreate only incentives table
        await db_service.db_manager.execute_script("""
            DROP TABLE IF EXISTS incentives CASCADE;
        """)

        # Recreate incentives table (from schema)
        from ...database.schema import CREATE_INCENTIVES_TABLE, CREATE_INDICES
        await db_service.db_manager.execute_script(CREATE_INCENTIVES_TABLE)

        # Recreate indices
        indices_script = "\n".join([
            line for line in CREATE_INDICES.split("\n")
            if "incentives" in line.lower()
        ])
        await db_service.db_manager.execute_script(indices_script)

        # Reload data
        csv_service = CSVLoadingService(db_service)
        file_path = Path("data") / "incentives.csv"

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="incentives.csv not found in data/ folder")

        result = await csv_service.load_incentives(
            file_path=file_path,
            enable_ai_generation=enable_ai_generation,
            batch_size=batch_size
        )

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

        return {
            "status": "success",
            "message": "Incentives table refreshed successfully",
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing incentives: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh-companies")
async def refresh_companies(
    batch_size: int = 1000,
    db_service = Depends(get_db_service)
):
    """
    Refresh companies table

    Clears companies table and reloads from CSV.
    Keeps incentives and matches intact.
    """
    try:
        logger.info("Refreshing companies table...")

        # Drop and recreate only companies table
        await db_service.db_manager.execute_script("""
            DROP TABLE IF EXISTS companies CASCADE;
        """)

        # Recreate companies table
        from ...database.schema import CREATE_COMPANIES_TABLE, CREATE_INDICES
        await db_service.db_manager.execute_script(CREATE_COMPANIES_TABLE)

        # Recreate indices
        indices_script = "\n".join([
            line for line in CREATE_INDICES.split("\n")
            if "companies" in line.lower()
        ])
        await db_service.db_manager.execute_script(indices_script)

        # Reload data
        csv_service = CSVLoadingService(db_service)
        file_path = Path("data") / "companies.csv"

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="companies.csv not found in data/ folder")

        result = await csv_service.load_companies(
            file_path=file_path,
            batch_size=batch_size
        )

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

        return {
            "status": "success",
            "message": "Companies table refreshed successfully",
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear-data")
async def clear_all_data(
    confirm: bool = False,
    db_service = Depends(get_db_service)
):
    """
    Clear all data from database (WARNING: DESTRUCTIVE)

    Drops and recreates all tables. Use with caution!
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to clear all data"
        )

    try:
        logger.warning("Clearing all database tables...")

        # Drop and recreate schema
        await db_service.drop_all_tables()
        await db_service.create_schema()

        return {
            "status": "success",
            "message": "All data cleared successfully"
        }

    except Exception as e:
        logger.error(f"Error clearing data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
