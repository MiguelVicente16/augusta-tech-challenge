"""
FastAPI router for embedding generation endpoints

Provides endpoints for:
- Generating embeddings for companies and incentives using pgvector
- Checking embedding status
- Vector search statistics
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...ai.vector_db import VectorDB
from ...database.service import DatabaseService
from ..dependencies import get_db_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/embeddings", tags=["embeddings"])


# ============================================================================
# Request/Response Models
# ============================================================================

class EmbeddingJobRequest(BaseModel):
    """Request model for embedding generation job"""
    batch_size: Optional[int] = 1000
    entity_type: str = "both"  # "companies", "incentives", or "both"
    process_all: bool = False  # If True, process ALL entities (ignores batch_size)


class EmbeddingJobResponse(BaseModel):
    """Response model for embedding job status"""
    status: str
    message: str
    companies_with_embeddings: int
    incentives_with_embeddings: int
    total_companies: int
    total_incentives: int


# ============================================================================
# Embedding Endpoints
# ============================================================================

@router.post("/generate", response_model=EmbeddingJobResponse)
async def generate_embeddings(
    request: EmbeddingJobRequest,
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    Generate embeddings for companies and/or incentives

    Uses LangChain + OpenAI to generate embeddings with structured Documents
    and stores them in PostgreSQL with pgvector extension.

    Parameters:
    - batch_size: Number of entities per batch (default: 1000)
    - entity_type: "companies", "incentives", or "both"
    - process_all: If True, processes ALL entities in batches until done

    Cost: ~$0.40 for 195k companies, ~$0.01 for 500 incentives
    Time: ~30 minutes for full dataset
    """
    try:
        logger.info(f"Starting embedding generation for: {request.entity_type}")

        vector_db = VectorDB(db_service.pool)

        companies_generated = 0
        incentives_generated = 0

        # Generate company embeddings
        if request.entity_type in ["companies", "both"]:
            logger.info("Generating company embeddings...")

            if request.process_all:
                # Process ALL companies in batches until none left
                while True:
                    companies = await db_service.pool.fetch(
                        """
                        SELECT id, company_name, cae_primary_label, trade_description_native, website
                        FROM companies
                        WHERE embedding IS NULL
                        ORDER BY id
                        LIMIT $1
                        """,
                        request.batch_size
                    )

                    if not companies:
                        break

                    company_dicts = [dict(c) for c in companies]
                    batch_count = await vector_db.add_company_embeddings(company_dicts)
                    companies_generated += batch_count
                    logger.info(f"Generated {batch_count} embeddings (total: {companies_generated})")
            else:
                # Process just one batch
                companies = await db_service.pool.fetch(
                    """
                    SELECT id, company_name, cae_primary_label, trade_description_native, website
                    FROM companies
                    WHERE embedding IS NULL
                    LIMIT $1
                    """,
                    request.batch_size
                )

                if companies:
                    company_dicts = [dict(c) for c in companies]
                    companies_generated = await vector_db.add_company_embeddings(company_dicts)
                    logger.info(f"Generated {companies_generated} company embeddings")

        # Generate incentive embeddings
        if request.entity_type in ["incentives", "both"]:
            logger.info("Generating incentive embeddings...")

            if request.process_all:
                # Process ALL incentives in batches until none left
                while True:
                    incentives = await db_service.pool.fetch(
                        """
                        SELECT id, title, description, ai_description_structured,
                               total_budget, date_start, date_end
                        FROM incentives
                        WHERE embedding IS NULL
                        ORDER BY id
                        LIMIT $1
                        """,
                        request.batch_size
                    )

                    if not incentives:
                        break

                    incentive_dicts = [dict(i) for i in incentives]
                    batch_count = await vector_db.add_incentive_embeddings(incentive_dicts)
                    incentives_generated += batch_count
                    logger.info(f"Generated {batch_count} embeddings (total: {incentives_generated})")
            else:
                # Process just one batch
                incentives = await db_service.pool.fetch(
                    """
                    SELECT id, title, description, ai_description_structured,
                           total_budget, date_start, date_end
                    FROM incentives
                    WHERE embedding IS NULL
                    LIMIT $1
                    """,
                    request.batch_size
                )

                if incentives:
                    incentive_dicts = [dict(i) for i in incentives]
                    incentives_generated = await vector_db.add_incentive_embeddings(incentive_dicts)
                    logger.info(f"Generated {incentives_generated} incentive embeddings")

        # Get current stats
        stats = await vector_db.get_stats()
        total_companies = await db_service.count_companies()
        total_incentives = await db_service.pool.fetchval("SELECT COUNT(*) FROM incentives")

        return EmbeddingJobResponse(
            status="completed",
            message=f"Generated {companies_generated} company and {incentives_generated} incentive embeddings",
            companies_with_embeddings=stats['companies_with_embeddings'],
            incentives_with_embeddings=stats['incentives_with_embeddings'],
            total_companies=total_companies,
            total_incentives=total_incentives
        )

    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/status", response_model=EmbeddingJobResponse)
async def get_embedding_status(
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    Get current status of embeddings

    Returns information about how many companies and incentives have embeddings.
    """
    try:
        vector_db = VectorDB(db_service.pool)
        stats = await vector_db.get_stats()

        total_companies = await db_service.count_companies()
        total_incentives = await db_service.pool.fetchval("SELECT COUNT(*) FROM incentives")

        companies_with = stats['companies_with_embeddings']
        incentives_with = stats['incentives_with_embeddings']

        if companies_with == 0 and incentives_with == 0:
            status = "not_started"
            message = "No embeddings generated yet. Run POST /embeddings/generate to start."
        elif companies_with < total_companies or incentives_with < total_incentives:
            status = "partial"
            message = f"Partial embeddings: {companies_with}/{total_companies} companies, {incentives_with}/{total_incentives} incentives"
        else:
            status = "complete"
            message = "All embeddings generated. Matching system ready."

        return EmbeddingJobResponse(
            status=status,
            message=message,
            companies_with_embeddings=companies_with,
            incentives_with_embeddings=incentives_with,
            total_companies=total_companies,
            total_incentives=total_incentives
        )

    except Exception as e:
        logger.error(f"Error getting embedding status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/search")
async def semantic_search(
    query: str,
    table: str = "incentives",
    limit: int = 10,
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    Perform semantic search using natural language

    Args:
        query: Natural language search query
        table: "incentives" or "companies"
        limit: Number of results to return
    """
    try:
        vector_db = VectorDB(db_service.pool)
        results = await vector_db.search_by_text(query, table, limit)

        return {
            "query": query,
            "table": table,
            "results": results
        }

    except Exception as e:
        logger.error(f"Error performing semantic search: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
