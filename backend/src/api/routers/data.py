"""
Data access router

Provides REST API endpoints for frontend data access:
- List incentives with search
- List companies with search
- Get individual records
- Get matches
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...database.service import DatabaseService
from ..dependencies import get_db_service

logger = logging.getLogger(__name__)

router = APIRouter()


# Response models
class IncentiveResponse(BaseModel):
    id: int
    incentive_project_id: Optional[str] = None
    project_id: Optional[str] = None
    incentive_program: Optional[str] = None
    title: str
    description: Optional[str] = None
    ai_description: Optional[str] = None
    ai_description_structured: Optional[dict] = None
    eligibility_criteria: Optional[dict] = None
    document_urls: Optional[list] = None
    date_publication: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    total_budget: Optional[float] = None
    source_link: Optional[str] = None
    gcs_document_urls: Optional[list] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, incentive):
        """Create IncentiveResponse from database model with proper date conversion"""
        # Convert model to dict and handle date/datetime fields
        data = {}
        for field_name, field_info in cls.model_fields.items():
            value = getattr(incentive, field_name, None)
            
            if value is not None:
                # Convert date and datetime objects to ISO format strings
                if hasattr(value, 'isoformat'):
                    data[field_name] = value.isoformat()
                else:
                    data[field_name] = value
            else:
                data[field_name] = None
                
        return cls(**data)


class CompanyResponse(BaseModel):
    id: int
    company_name: str
    cae_primary_label: Optional[str]
    trade_description_native: Optional[str]
    website: Optional[str]
    created_at: Optional[str]

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, company):
        """Create CompanyResponse from database model with proper date conversion"""
        # Convert model to dict and handle date/datetime fields
        data = {}
        for field_name, field_info in cls.model_fields.items():
            value = getattr(company, field_name, None)
            
            if value is not None:
                # Convert date and datetime objects to ISO format strings
                if hasattr(value, 'isoformat'):
                    data[field_name] = value.isoformat()
                else:
                    data[field_name] = value
            else:
                data[field_name] = None
                
        return cls(**data)


class MatchResponse(BaseModel):
    id: int
    incentive_id: int
    company_id: int
    score: float
    rank_position: int
    reasoning: Optional[dict]
    created_at: Optional[str]
    incentive: Optional[IncentiveResponse]
    company: Optional[CompanyResponse]

    class Config:
        from_attributes = True


# ============================================================================
# Incentives Endpoints
# ============================================================================

@router.get("/incentives/count")
async def count_incentives(
    db_service: DatabaseService = Depends(get_db_service)
):
    """Get total count of incentives"""
    try:
        count = await db_service.count_incentives()
        return {"count": count}
    except Exception as e:
        logger.error(f"Error counting incentives: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/incentives", response_model=List[IncentiveResponse])
async def list_incentives(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=1000),
    search: Optional[str] = None,
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    List all incentives with optional search

    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return
    - **search**: Optional search query for title/description
    """
    try:
        if search:
            # Use the inspection service search endpoint
            from ..services.inspection_service import DatabaseInspectionService
            inspection_service = DatabaseInspectionService(db_service.db_manager)
            results = await inspection_service.search_table('incentives', search, limit)
            return results
        else:
            # Get all incentives
            incentives = await db_service.get_all_incentives(limit=limit, offset=skip)
            result = []
            for inc in incentives:
                result.append(IncentiveResponse.from_model(inc))
            return result
    except Exception as e:
        logger.error(f"Error listing incentives: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incentives/{incentive_id}", response_model=IncentiveResponse)
async def get_incentive(
    incentive_id: int,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Get a specific incentive by ID"""
    try:
        incentive = await db_service.get_incentive_by_id(incentive_id)
        if not incentive:
            raise HTTPException(status_code=404, detail="Incentive not found")
        return IncentiveResponse.from_model(incentive)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting incentive {incentive_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Companies Endpoints
# ============================================================================

@router.get("/companies", response_model=List[CompanyResponse])
async def list_companies(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=1000),
    search: Optional[str] = None,
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    List all companies with optional search

    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return
    - **search**: Optional search query for company name/description
    """
    try:
        if search:
            # Use the inspection service search endpoint
            from ..services.inspection_service import DatabaseInspectionService
            inspection_service = DatabaseInspectionService(db_service.db_manager)
            results = await inspection_service.search_table('companies', search, limit)
            return results
        else:
            # Get all companies
            companies = await db_service.get_all_companies(limit=limit, offset=skip)
            result = []
            for comp in companies:
                result.append(CompanyResponse.from_model(comp))
            return result
    except Exception as e:
        logger.error(f"Error listing companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Get a specific company by ID"""
    try:
        company = await db_service.get_company_by_id(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        return CompanyResponse.from_model(company)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Matches Endpoints
# ============================================================================

@router.get("/matches", response_model=List[MatchResponse])
async def list_matches(
    incentive_id: Optional[int] = None,
    company_id: Optional[int] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=1000),
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    List matches with optional filters

    - **incentive_id**: Filter by incentive
    - **company_id**: Filter by company
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    try:
        if incentive_id:
            matches = await db_service.get_matches_for_incentive(incentive_id, limit=limit)
        elif company_id:
            matches = await db_service.get_matches_for_company(company_id, limit=limit)
        else:
            # Get all matches (this might be slow for large datasets)
            matches = await db_service.get_all_matches(limit=limit, offset=skip)

        # Enrich with incentive and company data
        enriched_matches = []
        for match in matches:
            incentive = await db_service.get_incentive_by_id(match.incentive_id)
            company = await db_service.get_company_by_id(match.company_id)

            match_dict = {
                "id": match.id,
                "incentive_id": match.incentive_id,
                "company_id": match.company_id,
                "score": float(match.score),
                "rank_position": match.rank_position,
                "reasoning": match.reasoning,
                "created_at": match.created_at.isoformat() if match.created_at else None,
                "incentive": IncentiveResponse.from_model(incentive) if incentive else None,
                "company": CompanyResponse.from_model(company) if company else None,
            }
            enriched_matches.append(MatchResponse.model_validate(match_dict))

        return enriched_matches
    except Exception as e:
        logger.error(f"Error listing matches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/matches/incentive/{incentive_id}/top", response_model=List[MatchResponse])
async def get_top_matches_for_incentive(
    incentive_id: int,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Get top 5 matches for a specific incentive"""
    try:
        matches = await db_service.get_matches_for_incentive(incentive_id, limit=5)

        # Enrich with company data
        enriched_matches = []
        for match in matches:
            company = await db_service.get_company_by_id(match.company_id)
            incentive = await db_service.get_incentive_by_id(match.incentive_id)

            match_dict = {
                "id": match.id,
                "incentive_id": match.incentive_id,
                "company_id": match.company_id,
                "score": float(match.score),
                "rank_position": match.rank_position,
                "reasoning": match.reasoning,
                "created_at": match.created_at.isoformat() if match.created_at else None,
                "incentive": IncentiveResponse.from_model(incentive) if incentive else None,
                "company": CompanyResponse.from_model(company) if company else None,
            }
            enriched_matches.append(MatchResponse.model_validate(match_dict))

        return enriched_matches
    except Exception as e:
        logger.error(f"Error getting top matches for incentive {incentive_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
