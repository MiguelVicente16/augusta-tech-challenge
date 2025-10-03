"""
Chatbot Tools for Pydantic AI Agent

Provides structured tools for querying incentives, companies, and matches.
Agent decides which tool to use based on user query.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from ..database.service import DatabaseService
from ..ai.vector_db import VectorDB

logger = logging.getLogger(__name__)


# ============================================================================
# Tool Input/Output Models
# ============================================================================

class CompanySearchInput(BaseModel):
    """Input for company search by name"""
    company_name: str = Field(..., description="Name of the company to search for")
    exact_match: bool = Field(default=False, description="Whether to use exact matching or fuzzy search")


class IncentiveSearchInput(BaseModel):
    """Input for incentive search by ID or title"""
    incentive_id: Optional[int] = Field(None, description="Specific incentive ID to retrieve")
    title_query: Optional[str] = Field(None, description="Search term for incentive title")


class SectorSearchInput(BaseModel):
    """Input for searching companies by sector"""
    sector: str = Field(..., description="CAE sector label to filter by")
    limit: int = Field(default=10, description="Maximum number of results")


class MatchesInput(BaseModel):
    """Input for getting matches"""
    company_id: Optional[int] = Field(None, description="Company ID to get incentive matches for")
    incentive_id: Optional[int] = Field(None, description="Incentive ID to get company matches for")


class SemanticSearchInput(BaseModel):
    """Input for semantic search"""
    query: str = Field(..., description="Natural language search query")
    entity_type: str = Field(..., description="Type of entity to search: 'incentives' or 'companies'")
    limit: int = Field(default=5, description="Maximum number of results")


# ============================================================================
# Chatbot Tools Class
# ============================================================================

class ChatbotTools:
    """
    Tools for Pydantic AI chatbot agent.

    Provides direct database queries and semantic search capabilities.
    """

    def __init__(self, db_service: DatabaseService):
        """
        Initialize chatbot tools

        Args:
            db_service: Database service instance
        """
        self.db_service = db_service
        self.vector_db = VectorDB(db_service.pool)

    # ========================================================================
    # Company Tools
    # ========================================================================

    async def get_company_by_name(self, company_name: str, exact_match: bool = False) -> Dict[str, Any]:
        """
        Find a company by name using direct database query.

        Use this when user asks for a specific company by name.
        Fast and cost-effective for exact lookups.

        Args:
            company_name: Name of the company
            exact_match: Whether to use exact matching

        Returns:
            Company information including sector and description
        """
        try:
            if exact_match:
                query = "SELECT * FROM companies WHERE LOWER(company_name) = LOWER($1) LIMIT 1"
                row = await self.db_service.pool.fetchrow(query, company_name)
            else:
                # Fuzzy search using ILIKE
                query = "SELECT * FROM companies WHERE company_name ILIKE $1 LIMIT 10"
                rows = await self.db_service.pool.fetch(query, f"%{company_name}%")
                if not rows:
                    return {"error": f"No company found matching '{company_name}'"}

                # Return first match or multiple if found
                if len(rows) == 1:
                    row = rows[0]
                else:
                    return {
                        "multiple_matches": True,
                        "count": len(rows),
                        "companies": [dict(r) for r in rows[:5]]
                    }

            if not row:
                return {"error": f"Company '{company_name}' not found"}

            return dict(row)

        except Exception as e:
            logger.error(f"Error searching company: {e}")
            return {"error": str(e)}

    async def search_companies_by_sector(self, sector: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search companies by CAE sector.

        Use this when user asks about companies in a specific industry/sector.

        Args:
            sector: CAE sector label (e.g., "Agricultura", "Tecnologia")
            limit: Maximum number of results

        Returns:
            List of companies in that sector
        """
        try:
            query = """
            SELECT id, company_name, cae_primary_label, trade_description_native
            FROM companies
            WHERE cae_primary_label ILIKE $1
            LIMIT $2
            """
            rows = await self.db_service.pool.fetch(query, f"%{sector}%", limit)

            if not rows:
                return [{"info": f"No companies found in sector '{sector}'"}]

            return [dict(r) for r in rows]

        except Exception as e:
            logger.error(f"Error searching by sector: {e}")
            return [{"error": str(e)}]

    # ========================================================================
    # Incentive Tools
    # ========================================================================

    async def get_incentive_by_id(self, incentive_id: int) -> Dict[str, Any]:
        """
        Get specific incentive by ID.

        Use this when user mentions a specific incentive ID.

        Args:
            incentive_id: Incentive ID

        Returns:
            Complete incentive information
        """
        try:
            incentive = await self.db_service.get_incentive_by_id(incentive_id)

            if not incentive:
                return {"error": f"Incentive ID {incentive_id} not found"}

            return {
                "id": incentive.id,
                "title": incentive.title,
                "description": incentive.description,
                "budget": float(incentive.total_budget) if incentive.total_budget else None,
                "start_date": str(incentive.date_start) if incentive.date_start else None,
                "end_date": str(incentive.date_end) if incentive.date_end else None,
                "publication_date": str(incentive.date_publication) if incentive.date_publication else None,
                "source_link": incentive.source_link,
                "status": incentive.status
            }

        except Exception as e:
            logger.error(f"Error getting incentive: {e}")
            return {"error": str(e)}

    async def search_incentives_by_title(self, title_query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search incentives by title keyword.

        Use this when user asks about incentives containing specific keywords.
        Uses PostgreSQL full-text search (fast).

        Args:
            title_query: Keywords to search in title
            limit: Maximum number of results

        Returns:
            List of matching incentives
        """
        try:
            query = """
            SELECT id, title, description, total_budget, date_start, date_end, status
            FROM incentives
            WHERE title ILIKE $1 OR description ILIKE $1
            LIMIT $2
            """
            rows = await self.db_service.pool.fetch(query, f"%{title_query}%", limit)

            if not rows:
                return [{"info": f"No incentives found matching '{title_query}'"}]

            return [dict(r) for r in rows]

        except Exception as e:
            logger.error(f"Error searching incentives: {e}")
            return [{"error": str(e)}]

    # ========================================================================
    # Matching Tools
    # ========================================================================

    async def get_matches_for_company(self, company_id: int, limit: int = 5) -> Dict[str, Any]:
        """
        Get top incentive matches for a company.

        Use this when user asks "What incentives are good for company X?"

        Args:
            company_id: Company ID
            limit: Number of top matches to return

        Returns:
            Top matched incentives with scores
        """
        try:
            matches = await self.db_service.get_matches_for_company(company_id, limit=limit)

            if not matches:
                return {"info": f"No matches found for company {company_id}"}

            results = []
            for match in matches:
                incentive = await self.db_service.get_incentive_by_id(match.incentive_id)
                if incentive:
                    results.append({
                        "incentive_id": match.incentive_id,
                        "incentive_title": incentive.title,
                        "score": float(match.score),
                        "rank": match.rank_position,
                        "reasoning": match.reasoning
                    })

            return {
                "company_id": company_id,
                "top_matches": results
            }

        except Exception as e:
            logger.error(f"Error getting company matches: {e}")
            return {"error": str(e)}

    async def get_matches_for_incentive_by_title(self, incentive_title: str) -> Dict[str, Any]:
        """
        Get top 5 company matches for an incentive by searching by title first.

        **PREVENTS LOOPS**: Single tool call that combines search + match retrieval.

        Args:
            incentive_title: Title or partial title of the incentive

        Returns:
            Top 5 companies with match scores, or error if not found
        """
        try:
            # Step 1: Search for incentive by title
            logger.info(f"Searching incentive by title: '{incentive_title}'")

            query = """
            SELECT id, title
            FROM incentives
            WHERE title ILIKE $1
            LIMIT 1
            """
            row = await self.db_service.pool.fetchrow(query, f"%{incentive_title}%")

            if not row:
                return {
                    "error": f"Incentive not found with title matching '{incentive_title}'",
                    "suggestion": "Try searching with a different part of the title or ask for a list of available incentives"
                }

            incentive_id = row['id']
            incentive_title_found = row['title']

            logger.info(f"Found incentive ID {incentive_id}: {incentive_title_found}")

            # Step 2: Get matches for that incentive (auto-computes if needed)
            result = await self.get_matches_for_incentive(incentive_id)

            # Add title to result
            if "error" not in result:
                result["incentive_title"] = incentive_title_found

            return result

        except Exception as e:
            logger.error(f"Error in get_matches_for_incentive_by_title: {e}", exc_info=True)
            return {"error": str(e)}

    async def get_matches_for_incentive(self, incentive_id: int) -> Dict[str, Any]:
        """
        Get top 5 company matches for an incentive.

        **SMART BEHAVIOR**:
        1. If matches exist in DB → return them (fast, like the endpoint)
        2. If no matches exist → auto-compute them (uses MatchingService)

        Mimics the endpoint GET /api/v1/matching/incentive/{incentive_id}/matches
        but with auto-compute fallback for better UX.

        Args:
            incentive_id: Incentive ID

        Returns:
            Top 5 matched companies with scores, rank, and reasoning
        """
        try:
            # Step 1: Try to get existing matches from database (same as endpoint line 178)
            matches = await self.db_service.get_matches_for_incentive(incentive_id)

            # Step 2: Auto-compute if none exist
            if not matches:
                logger.info(f"No matches found for incentive {incentive_id}. Running matching algorithm...")

                from ..api.services.matching_service import MatchingService

                try:
                    matching_service = MatchingService(self.db_service)

                    # Run matching (max cost $0.30)
                    computed_matches = await matching_service.match_companies_for_incentive(
                        incentive_id=incentive_id,
                        max_cost_per_incentive=0.30
                    )

                    # Save to database
                    await matching_service.save_matches_to_database(incentive_id, computed_matches)

                    logger.info(f"Successfully computed {len(computed_matches)} matches for incentive {incentive_id}")

                    # Fetch the newly saved matches
                    matches = await self.db_service.get_matches_for_incentive(incentive_id)

                except Exception as matching_error:
                    logger.error(f"Error computing matches: {matching_error}")
                    return {
                        "incentive_id": incentive_id,
                        "matches": [],
                        "error": f"Failed to compute matches: {str(matching_error)}"
                    }

            if not matches:
                return {
                    "incentive_id": incentive_id,
                    "matches": [],
                    "message": "No matches found."
                }

            # Step 3: Format matches with company details (same as endpoint lines 188-199)
            match_results = []
            for match in matches:
                company = await self.db_service.get_company_by_id(match.company_id)
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
            logger.error(f"Error getting incentive matches: {e}", exc_info=True)
            return {"error": str(e)}

    # ========================================================================
    # Semantic Search Tools (uses pgvector)
    # ========================================================================

    async def semantic_search(
        self,
        query: str,
        entity_type: str = "incentives",
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Semantic search using natural language and embeddings.

        Use this when user asks conceptual questions like:
        - "What incentives exist for green technology?"
        - "Find companies working on AI"

        Uses pgvector embeddings for intelligent matching.

        Args:
            query: Natural language query
            entity_type: "incentives" or "companies"
            limit: Number of results

        Returns:
            Semantically similar results
        """
        try:
            # Use the correct method from VectorDB with timeout
            results = await self.vector_db.semantic_search(
                query, 
                entity_type, 
                limit, 
                timeout=10.0  # 10 second timeout
            )
            return results

        except asyncio.TimeoutError:
            logger.error(f"Semantic search timed out for query: '{query}' on {entity_type}")
            return [{"error": f"Search timed out for '{query}'. Try a more specific query."}]
        except Exception as e:
            logger.error(f"Error in semantic search: {e}", exc_info=True)
            return [{"error": f"Search failed: {str(e)}"}]

    async def search_companies_semantic(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search companies using semantic similarity on embeddings.

        **OPTIMIZED TOOL** - Replaces multiple get_company_by_name calls with a single vector search.

        Use cases:
        - "empresas de energia renovável"
        - "companhias do setor tecnológico"
        - "empresas que trabalham com IA"

        Args:
            query: Sector, industry, or activity description
            limit: Number of companies to return

        Returns:
            List of relevant companies with similarity scores
        """
        try:
            # Use semantic_search method with timeout protection
            results = await self.vector_db.semantic_search(
                query, 
                "companies", 
                limit, 
                timeout=10.0  # 10 second timeout
            )

            if not results:
                return [{"info": f"No companies found matching '{query}'"}]

            # Results already have the right format from VectorDB
            return results

        except asyncio.TimeoutError:
            logger.error(f"Semantic search timed out for query: '{query}'")
            return [{"error": f"Search timed out for '{query}'. Try a more specific query."}]
        except Exception as e:
            logger.error(f"Error in semantic company search: {e}", exc_info=True)
            return [{"error": f"Search failed: {str(e)}"}]

    # ========================================================================
    # Statistics Tools
    # ========================================================================

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Use this when user asks about overall numbers or statistics.

        Returns:
            Count of incentives, companies, and matches
        """
        try:
            total_incentives = await self.db_service.count_incentives()
            total_companies = await self.db_service.count_companies()

            # Get matching stats
            match_stats = await self.db_service.get_matching_statistics()

            return {
                "total_incentives": total_incentives,
                "total_companies": total_companies,
                "matching_statistics": match_stats
            }

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}

    # ========================================================================
    # Match Generation Tools
    # ========================================================================

    async def generate_matches_for_all_incentives(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Generate matches for all incentives using AI matching algorithm.

        This tool automatically refreshes matches if they exist, or generates new ones if they don't.
        The force_refresh parameter allows clearing all existing matches before regeneration.

        Args:
            force_refresh: If True, clears existing matches and regenerates all

        Returns:
            Status of match generation including counts and processing info
        """
        try:
            # Check if matches already exist
            total_matches = await self.db_service.pool.fetchval("SELECT COUNT(*) FROM matches")
            
            # Import the matching service
            from ..api.services.matching_service import MatchingService
            
            matching_service = MatchingService(self.db_service)
            
            if total_matches > 0 and force_refresh:
                # Clear existing matches for force refresh
                await self.db_service.clear_all_matches()
                logger.info(f"Cleared {total_matches} existing matches for force refresh")
                action_taken = "force_refresh"
            elif total_matches > 0:
                # Matches exist, refresh them automatically
                logger.info(f"Found {total_matches} existing matches, refreshing them...")
                action_taken = "refresh_existing"
            else:
                # No matches exist, generate new ones
                action_taken = "generate_new"

            # Run batch matching for all incentives
            logger.info("Starting AI-powered matching for all incentives...")
            results = await matching_service.batch_match_all_incentives(
                max_cost_total=None,  # No cost limit
                save_to_db=True
            )

            return {
                "status": "success",
                "action_taken": action_taken,
                "message": f"Successfully {'refreshed' if action_taken != 'generate_new' else 'generated'} matches for all incentives",
                "total_incentives": results["total_incentives"],
                "successful_matches": results["successful_matches"],
                "failed_matches": results["failed_matches"],
                "total_cost": results["total_cost"],
                "matches_per_incentive": results["matches_per_incentive"],
                "previous_matches_count": total_matches if action_taken != "generate_new" else 0
            }

        except Exception as e:
            logger.error(f"Error generating matches: {e}")
            return {
                "status": "error",
                "message": f"Failed to generate matches: {str(e)}"
            }
