"""
Database Inspection Router

Endpoints for database health, statistics, and exploration.
"""

import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, Query, Depends

from ..dependencies import get_db_service
from ..services.inspection_service import DatabaseInspectionService
from ...database.service import DatabaseService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_inspection_service(db_service: DatabaseService = Depends(get_db_service)) -> DatabaseInspectionService:
    """Dependency to get inspection service"""
    return DatabaseInspectionService(db_service.db_manager)


@router.get("/health")
async def health_check(
    inspection_service: DatabaseInspectionService = Depends(get_inspection_service)
):
    """
    Database health check

    Returns database status, version, size, and table counts.
    """
    try:
        health = await inspection_service.get_database_health()
        return health
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables")
async def list_tables(
    inspection_service: DatabaseInspectionService = Depends(get_inspection_service)
):
    """
    List all database tables

    Returns list of table names in the database.
    """
    try:
        tables = await inspection_service.get_table_list()
        return {
            "tables": tables,
            "count": len(tables)
        }
    except Exception as e:
        logger.error(f"Failed to list tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/schema")
async def get_table_schema(
    table_name: str,
    inspection_service: DatabaseInspectionService = Depends(get_inspection_service)
):
    """
    Get table schema

    Returns column definitions for the specified table.
    """
    try:
        # Validate table name (security)
        valid_tables = await inspection_service.get_table_list()
        if table_name not in valid_tables:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

        schema = await inspection_service.get_table_schema(table_name)
        return {
            "table_name": table_name,
            "columns": schema,
            "column_count": len(schema)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schema for {table_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/stats")
async def get_table_statistics(
    table_name: str,
    inspection_service: DatabaseInspectionService = Depends(get_inspection_service)
):
    """
    Get table statistics

    Returns detailed statistics about table contents.
    Includes table-specific metrics:
    - Incentives: budget stats, records with dates/criteria/AI descriptions
    - Companies: CAE sectors, websites, descriptions
    - Matches: score distribution, averages
    """
    try:
        # Validate table name
        valid_tables = await inspection_service.get_table_list()
        if table_name not in valid_tables:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

        stats = await inspection_service.get_table_statistics(table_name)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get statistics for {table_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/sample")
async def get_sample_data(
    table_name: str,
    limit: int = Query(default=5, ge=1, le=20, description="Number of sample records"),
    inspection_service: DatabaseInspectionService = Depends(get_inspection_service)
):
    """
    Get sample records from table

    Returns up to `limit` records from the table for preview.
    """
    try:
        # Validate table name
        valid_tables = await inspection_service.get_table_list()
        if table_name not in valid_tables:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

        samples = await inspection_service.get_sample_data(table_name, limit)
        return {
            "table_name": table_name,
            "count": len(samples),
            "records": samples
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sample data for {table_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/search")
async def search_table(
    table_name: str,
    q: str = Query(..., description="Search query (Portuguese full-text search)"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum results"),
    inspection_service: DatabaseInspectionService = Depends(get_inspection_service)
):
    """
    Search records in table

    Uses PostgreSQL full-text search with Portuguese language support.

    Supported tables:
    - incentives: Searches in title and description
    - companies: Searches in company name and trade description
    """
    try:
        # Validate table name
        if table_name not in ['incentives', 'companies']:
            raise HTTPException(
                status_code=400,
                detail=f"Search not supported for table '{table_name}'. Use 'incentives' or 'companies'."
            )

        results = await inspection_service.search_table(table_name, q, limit)
        return {
            "table_name": table_name,
            "query": q,
            "count": len(results),
            "results": results
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed for {table_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview")
async def database_overview(
    inspection_service: DatabaseInspectionService = Depends(get_inspection_service)
):
    """
    Complete database overview

    Returns comprehensive information including:
    - Health status
    - All table statistics
    - Sample data from main tables
    """
    try:
        # Get health
        health = await inspection_service.get_database_health()

        # Get detailed stats for main tables
        tables_stats = {}
        for table_name in ['incentives', 'companies', 'matches']:
            if table_name in health.get('tables', {}):
                tables_stats[table_name] = await inspection_service.get_table_statistics(table_name)

        return {
            "health": health,
            "statistics": tables_stats
        }
    except Exception as e:
        logger.error(f"Failed to generate overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))
