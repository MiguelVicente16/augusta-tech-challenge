"""
FastAPI router for company-incentive matching endpoints

Provides REST API endpoints for:
- Running matching algorithm for specific incentives
- Getting top matches for incentives/companies  
- Batch processing all incentives
- Exporting results to CSV
"""

import asyncio
import csv
import io
import json
import logging
from typing import AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ...database.service import DatabaseService
from ..dependencies import get_db_service
from ..services.matching_service import MatchingService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/matching", tags=["matching"])


# ============================================================================
# Request/Response Models
# ============================================================================

class MatchingRunRequest(BaseModel):
    """Request model for running matching algorithm"""
    incentive_id: int
    max_cost: Optional[float] = 0.30


class BatchMatchingRequest(BaseModel):
    """Request model for batch matching"""
    max_total_cost: Optional[float] = None
    force_refresh: bool = False


class MatchingResult(BaseModel):
    """Response model for individual match"""
    company_id: int
    company_name: str
    score: float
    rank: int
    reasoning: Dict


class MatchingResponse(BaseModel):
    """Response model for matching operation"""
    incentive_id: int
    matches: List[MatchingResult]
    total_cost: float
    processing_time: float


class BatchMatchingResponse(BaseModel):
    """Response model for batch matching"""
    total_incentives: int
    successful_matches: int
    failed_matches: int
    total_cost: float
    matches_per_incentive: Dict[str, int]


# ============================================================================
# Matching Endpoints
# ============================================================================

@router.post("/run", response_model=MatchingResponse)
async def run_matching_for_incentive(
    request: MatchingRunRequest,
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    Run matching algorithm for a specific incentive
    
    Finds the top 5 companies that best match the given incentive
    based on AI-powered scoring criteria.
    """
    import time
    start_time = time.time()
    
    try:
        matching_service = MatchingService(db_service)

        # Run matching (no initialize needed - uses DB directly)
        matches = await matching_service.match_companies_for_incentive(
            incentive_id=request.incentive_id,
            max_cost_per_incentive=request.max_cost
        )
        
        # Save to database
        await matching_service.save_matches_to_database(request.incentive_id, matches)
        
        # Format response
        match_results = []
        total_cost = 0.0  # Cost tracking removed for simplicity
        
        for match in matches:
            # Get company details
            company = await db_service.get_company_by_id(match.company_id)
            if company:
                match_results.append(MatchingResult(
                    company_id=match.company_id,
                    company_name=company.company_name,
                    score=float(match.score),
                    rank=match.rank,
                    reasoning=match.reasoning
                ))
        
        processing_time = time.time() - start_time
        
        return MatchingResponse(
            incentive_id=request.incentive_id,
            matches=match_results,
            total_cost=total_cost,
            processing_time=processing_time
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error running matching for incentive {request.incentive_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=BatchMatchingResponse)
async def run_batch_matching(
    request: BatchMatchingRequest,
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    Run matching algorithm for all active incentives

    Processes all incentives in the database and finds top 5 companies
    for each, respecting cost constraints.
    """
    try:
        matching_service = MatchingService(db_service)

        # Clear existing matches if force refresh
        if request.force_refresh:
            await db_service.clear_all_matches()
            logger.info("Cleared existing matches for refresh")

        # Run batch matching
        results = await matching_service.batch_match_all_incentives(
            max_cost_total=request.max_total_cost,
            save_to_db=True
        )

        return BatchMatchingResponse(**results)

    except Exception as e:
        logger.error(f"Error in batch matching: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch-stream")
async def run_batch_matching_stream(
    request: BatchMatchingRequest,
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    Run matching algorithm for all active incentives with real-time progress updates

    Returns Server-Sent Events (SSE) stream with progress information.
    """

    async def progress_generator() -> AsyncGenerator[str, None]:
        try:
            matching_service = MatchingService(db_service)

            # Clear existing matches if force refresh
            if request.force_refresh:
                await db_service.clear_all_matches()
                yield json.dumps({
                    "type": "info",
                    "message": "Cleared existing matches for refresh"
                }) + "\n"

            # Get total count
            incentives = await db_service.get_all_incentives()
            total = len(incentives)

            yield json.dumps({
                "type": "start",
                "total": total,
                "message": f"Starting batch matching for {total} incentives"
            }) + "\n"

            total_cost = 0.0
            successful = 0
            failed = 0

            for index, incentive in enumerate(incentives, 1):
                try:
                    if request.max_total_cost and total_cost >= request.max_total_cost:
                        yield json.dumps({
                            "type": "warning",
                            "message": f"Total cost limit reached: ${total_cost:.4f}"
                        }) + "\n"
                        break

                    # Send progress update
                    yield json.dumps({
                        "type": "progress",
                        "current": index,
                        "total": total,
                        "incentive_id": incentive.id,
                        "incentive_title": incentive.title,
                        "message": f"Processing {index}/{total}: {incentive.title[:50]}..."
                    }) + "\n"

                    remaining_budget = request.max_total_cost - total_cost if request.max_total_cost else 0.30
                    incentive_budget = min(0.30, remaining_budget)

                    matches = await matching_service.match_companies_for_incentive(
                        incentive.id,
                        max_cost_per_incentive=incentive_budget
                    )

                    if matches:
                        await matching_service.save_matches_to_database(incentive.id, matches)

                    successful += 1

                    # Send success update
                    yield json.dumps({
                        "type": "success",
                        "current": index,
                        "total": total,
                        "incentive_id": incentive.id,
                        "matches_found": len(matches),
                        "message": f"✓ Completed {incentive.title[:40]}... ({len(matches)} matches)"
                    }) + "\n"

                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to match incentive {incentive.id}: {e}")

                    yield json.dumps({
                        "type": "error",
                        "current": index,
                        "total": total,
                        "incentive_id": incentive.id,
                        "message": f"✗ Failed: {str(e)[:100]}"
                    }) + "\n"

            # Send completion message
            yield json.dumps({
                "type": "complete",
                "total_incentives": total,
                "successful_matches": successful,
                "failed_matches": failed,
                "total_cost": total_cost,
                "message": f"Batch matching completed: {successful} successful, {failed} failed"
            }) + "\n"

        except Exception as e:
            logger.error(f"Error in batch matching stream: {e}")
            yield json.dumps({
                "type": "error",
                "message": f"Fatal error: {str(e)}"
            }) + "\n"

    return EventSourceResponse(progress_generator())


@router.get("/incentive/{incentive_id}/matches")
async def get_matches_for_incentive(
    incentive_id: int,
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    Get top 5 company matches for a specific incentive
    
    Returns previously computed matches from the database.
    If no matches exist, suggests running the matching algorithm first.
    """
    try:
        matches = await db_service.get_matches_for_incentive(incentive_id)
        
        if not matches:
            return {
                "incentive_id": incentive_id,
                "matches": [],
                "message": "No matches found. Run matching algorithm first using POST /matching/run"
            }
        
        # Format matches with company details
        match_results = []
        for match in matches:
            company = await db_service.get_company_by_id(match.company_id)
            if company:
                match_results.append({
                    "company_id": match.company_id,
                    "company_name": company.company_name,
                    "score": float(match.score),
                    "rank": match.rank_position,
                    "reasoning": match.reasoning,
                    "created_at": match.created_at.isoformat() if match.created_at else None
                })
        
        return {
            "incentive_id": incentive_id,
            "matches": match_results
        }
        
    except Exception as e:
        logger.error(f"Error getting matches for incentive {incentive_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/company/{company_id}/matches")
async def get_matches_for_company(
    company_id: int,
    limit: int = 10,
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    Get best incentive matches for a specific company
    
    Returns incentives that are good matches for the given company,
    ordered by match score.
    """
    try:
        matches = await db_service.get_matches_for_company(company_id, limit=limit)
        
        if not matches:
            return {
                "company_id": company_id,
                "matches": [],
                "message": "No matches found for this company"
            }
        
        # Format matches with incentive details
        match_results = []
        for match in matches:
            incentive = await db_service.get_incentive_by_id(match.incentive_id)
            if incentive:
                match_results.append({
                    "incentive_id": match.incentive_id,
                    "incentive_title": incentive.title,
                    "score": float(match.score),
                    "rank": match.rank_position,
                    "reasoning": match.reasoning,
                    "created_at": match.created_at.isoformat() if match.created_at else None
                })
        
        return {
            "company_id": company_id,
            "matches": match_results
        }
        
    except Exception as e:
        logger.error(f"Error getting matches for company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/export")
async def export_matches_csv(
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    Export all matching results to CSV format
    
    Downloads a CSV file containing all company-incentive matches
    with scores, rankings, and basic details.
    """
    try:
        # Get all matches from database
        all_matches = await db_service.get_all_matches()
        
        if not all_matches:
            raise HTTPException(status_code=404, detail="No matches found to export")
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "incentive_id",
            "incentive_title", 
            "company_id",
            "company_name",
            "score",
            "rank",
            "created_at",
            "reasoning_objective",
            "reasoning_quality", 
            "reasoning_execution"
        ])
        
        # Write data rows
        for match in all_matches:
            # Get related entities
            incentive = await db_service.get_incentive_by_id(match.incentive_id)
            company = await db_service.get_company_by_id(match.company_id)
            
            # Extract reasoning details
            reasoning = match.reasoning or {}
            objective_reasoning = reasoning.get("adequacao_estrategia", {}).get("reasoning", "")
            quality_reasoning = reasoning.get("qualidade", {}).get("reasoning", "")
            execution_reasoning = reasoning.get("capacidade_execucao", {}).get("reasoning", "")
            
            writer.writerow([
                match.incentive_id,
                incentive.title if incentive else "",
                match.company_id, 
                company.company_name if company else "",
                float(match.score),
                match.rank_position,
                match.created_at.isoformat() if match.created_at else "",
                objective_reasoning,
                quality_reasoning,
                execution_reasoning
            ])
        
        # Create response
        output.seek(0)
        content = output.getvalue()
        output.close()
        
        return StreamingResponse(
            io.BytesIO(content.encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=incentive_matches.csv"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting matches to CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/stats")
async def get_matching_stats(
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    Get statistics about current matching results
    
    Returns summary statistics about matches in the database.
    """
    try:
        stats = await db_service.get_matching_statistics()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting matching statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")