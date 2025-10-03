import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal

import asyncpg

from .connection import DatabaseManager
from .models import IncentiveModel, CompanyModel, MatchModel, FULL_SCHEMA
from .sql import incentives as incentives_sql
from .sql import companies as companies_sql
from .sql import matches as matches_sql

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service layer for database operations with dependency injection support"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @property
    def pool(self):
        """Expose the connection pool for direct access (needed by VectorDB)"""
        return self.db_manager.pool

    async def create_schema(self) -> None:
        """Create database schema with all tables and indices"""
        try:
            logger.info("Creating database schema...")
            await self.db_manager.execute_script(FULL_SCHEMA)
            logger.info("Database schema created successfully")
        except Exception as e:
            logger.error(f"Failed to create database schema: {e}")
            raise

    async def drop_all_tables(self) -> None:
        """Drop all tables (for testing/cleanup)"""
        drop_script = """
        DROP TABLE IF EXISTS matches CASCADE;
        DROP TABLE IF EXISTS companies CASCADE;
        DROP TABLE IF EXISTS incentives CASCADE;
        """
        try:
            logger.info("Dropping all tables...")
            await self.db_manager.execute_script(drop_script)
            logger.info("All tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise

    # Incentives CRUD operations
    async def create_incentive(self, incentive: IncentiveModel) -> int:
        """Create a new incentive and return its ID"""
        async with self.db_manager.get_connection() as connection:
            return await connection.fetchval(
                incentives_sql.INSERT_INCENTIVE,
                incentive.incentive_project_id,
                incentive.project_id,
                incentive.title,
                incentive.description,
                incentive.ai_description,
                json.dumps(incentive.ai_description_structured) if incentive.ai_description_structured else None,
                json.dumps(incentive.eligibility_criteria) if incentive.eligibility_criteria else None,
                json.dumps(incentive.document_urls) if incentive.document_urls else None,
                incentive.date_publication,
                incentive.date_start,
                incentive.date_end,
                incentive.total_budget,
                incentive.source_link,
                incentive.status
            )

    async def get_incentive(self, incentive_id: int) -> Optional[IncentiveModel]:
        """Get incentive by ID"""
        async with self.db_manager.get_connection() as connection:
            row = await connection.fetchrow(incentives_sql.SELECT_BY_ID, incentive_id)
            return IncentiveModel(**row) if row else None

    async def get_incentives(self, limit: int = 100, offset: int = 0) -> List[IncentiveModel]:
        """Get list of incentives with pagination"""
        query = "SELECT * FROM incentives ORDER BY created_at DESC LIMIT $1 OFFSET $2"

        async with self.db_manager.get_connection() as connection:
            rows = await connection.fetch(query, limit, offset)
            return [IncentiveModel(**row) for row in rows]

    async def search_incentives(self, search_term: str, limit: int = 50) -> List[IncentiveModel]:
        """Search incentives by title and description"""
        query = """
        SELECT * FROM incentives
        WHERE to_tsvector('portuguese', title || ' ' || COALESCE(description, ''))
              @@ plainto_tsquery('portuguese', $1)
        ORDER BY ts_rank(to_tsvector('portuguese', title || ' ' || COALESCE(description, '')),
                        plainto_tsquery('portuguese', $1)) DESC
        LIMIT $2
        """

        async with self.db_manager.get_connection() as connection:
            rows = await connection.fetch(query, search_term, limit)
            return [IncentiveModel(**row) for row in rows]

    async def count_incentives(self) -> int:
        """Count total incentives"""
        async with self.db_manager.get_connection() as connection:
            return await connection.fetchval("SELECT COUNT(*) FROM incentives")

    # Companies CRUD operations
    async def create_company(self, company: CompanyModel) -> int:
        """Create a new company and return its ID"""
        query = """
        INSERT INTO companies (company_name, cae_primary_label, trade_description_native, website)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """

        async with self.db_manager.get_connection() as connection:
            return await connection.fetchval(
                query,
                company.company_name,
                company.cae_primary_label,
                company.trade_description_native,
                company.website
            )

    async def get_company(self, company_id: int) -> Optional[CompanyModel]:
        """Get company by ID"""
        query = "SELECT * FROM companies WHERE id = $1"

        async with self.db_manager.get_connection() as connection:
            row = await connection.fetchrow(query, company_id)
            return CompanyModel(**row) if row else None

    async def get_companies(self, limit: int = 100, offset: int = 0) -> List[CompanyModel]:
        """Get list of companies with pagination"""
        query = "SELECT * FROM companies ORDER BY company_name LIMIT $1 OFFSET $2"

        async with self.db_manager.get_connection() as connection:
            rows = await connection.fetch(query, limit, offset)
            return [CompanyModel(**row) for row in rows]

    async def search_companies(self, search_term: str, limit: int = 50) -> List[CompanyModel]:
        """Search companies by name and description"""
        query = """
        SELECT * FROM companies
        WHERE to_tsvector('portuguese', company_name || ' ' || COALESCE(trade_description_native, ''))
              @@ plainto_tsquery('portuguese', $1)
        ORDER BY ts_rank(to_tsvector('portuguese', company_name || ' ' || COALESCE(trade_description_native, '')),
                        plainto_tsquery('portuguese', $1)) DESC
        LIMIT $2
        """

        async with self.db_manager.get_connection() as connection:
            rows = await connection.fetch(query, search_term, limit)
            return [CompanyModel(**row) for row in rows]

    async def count_companies(self) -> int:
        """Count total companies"""
        async with self.db_manager.get_connection() as connection:
            return await connection.fetchval("SELECT COUNT(*) FROM companies")

    async def get_all_companies(self) -> List[CompanyModel]:
        """Get all companies (for embedding generation)"""
        query = "SELECT * FROM companies ORDER BY id"
        async with self.db_manager.get_connection() as connection:
            rows = await connection.fetch(query)
            return [CompanyModel(**row) for row in rows]

    async def update_company_embedding(self, company_id: int, embedding_bytes: bytes) -> None:
        """Update company embedding vector"""
        query = """
        UPDATE companies
        SET embedding_vector = $1, embedding_updated_at = NOW()
        WHERE id = $2
        """
        async with self.db_manager.get_connection() as connection:
            await connection.execute(query, embedding_bytes, company_id)

    async def get_companies_with_embeddings(self) -> List[tuple]:
        """Get all companies with their embeddings (id, embedding_vector)"""
        query = "SELECT id, embedding_vector FROM companies WHERE embedding_vector IS NOT NULL ORDER BY id"
        async with self.db_manager.get_connection() as connection:
            return await connection.fetch(query)

    async def count_companies_with_embeddings(self) -> int:
        """Count companies that have embeddings"""
        query = "SELECT COUNT(*) FROM companies WHERE embedding_vector IS NOT NULL"
        async with self.db_manager.get_connection() as connection:
            return await connection.fetchval(query)

    # Batch operations for CSV loading
    async def batch_create_incentives(self, incentives: List[IncentiveModel]) -> int:
        """Batch create incentives for efficient CSV loading"""
        if not incentives:
            return 0

        query = """
        INSERT INTO incentives (
            incentive_project_id, project_id, title, description, ai_description,
            ai_description_structured, eligibility_criteria, document_urls, date_publication,
            date_start, date_end, total_budget, source_link, status
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        """

        async with self.db_manager.get_transaction() as connection:
            import json
            batch_data = []
            for inc in incentives:
                # Convert JSON fields to JSON strings if needed
                eligibility_json = inc.eligibility_criteria
                if isinstance(eligibility_json, dict):
                    eligibility_json = json.dumps(eligibility_json)

                ai_description_structured_json = inc.ai_description_structured
                if isinstance(ai_description_structured_json, dict):
                    ai_description_structured_json = json.dumps(ai_description_structured_json)

                document_urls_json = inc.document_urls
                if isinstance(document_urls_json, (dict, list)):
                    document_urls_json = json.dumps(document_urls_json)

                batch_data.append((
                    inc.incentive_project_id, inc.project_id, inc.title,
                    inc.description, inc.ai_description, ai_description_structured_json,
                    eligibility_json, document_urls_json, inc.date_publication,
                    inc.date_start, inc.date_end, inc.total_budget,
                    inc.source_link, inc.status
                ))

            await connection.executemany(query, batch_data)
            return len(batch_data)

    async def batch_create_companies(self, companies: List[CompanyModel]) -> int:
        """Batch create companies for efficient CSV loading"""
        if not companies:
            return 0

        query = """
        INSERT INTO companies (company_name, cae_primary_label, trade_description_native, website)
        VALUES ($1, $2, $3, $4)
        """

        async with self.db_manager.get_transaction() as connection:
            batch_data = []
            for comp in companies:
                batch_data.append((
                    comp.company_name, comp.cae_primary_label,
                    comp.trade_description_native, comp.website
                ))

            await connection.executemany(query, batch_data)
            return len(batch_data)

    # Matches CRUD operations
    async def create_match(self, match: MatchModel) -> int:
        """Create a new match and return its ID"""
        import json
        async with self.db_manager.get_connection() as connection:
            match_id = await connection.fetchval(
                matches_sql.INSERT_MATCH,
                match.incentive_id,
                match.company_id,
                match.score,
                match.rank_position,
                json.dumps(match.reasoning) if match.reasoning else None
            )
            return match_id

    async def get_matches_for_incentive(self, incentive_id: int, limit: int = 10) -> List[MatchModel]:
        """Get all matches for a specific incentive"""
        import json
        async with self.db_manager.get_connection() as connection:
            rows = await connection.fetch(
                matches_sql.GET_TOP_MATCHES_FOR_INCENTIVE,
                incentive_id, limit
            )
            matches = []
            for row in rows:
                row_dict = dict(row)
                # Deserialize reasoning from JSON string to dict
                if row_dict.get('reasoning') and isinstance(row_dict['reasoning'], str):
                    row_dict['reasoning'] = json.loads(row_dict['reasoning'])
                matches.append(MatchModel(**row_dict))
            return matches

    async def get_matches_for_company(self, company_id: int, limit: int = 10) -> List[MatchModel]:
        """Get all matches for a specific company"""
        import json
        async with self.db_manager.get_connection() as connection:
            rows = await connection.fetch(
                matches_sql.GET_TOP_MATCHES_FOR_COMPANY,
                company_id, limit
            )
            matches = []
            for row in rows:
                row_dict = dict(row)
                # Deserialize reasoning from JSON string to dict
                if row_dict.get('reasoning') and isinstance(row_dict['reasoning'], str):
                    row_dict['reasoning'] = json.loads(row_dict['reasoning'])
                matches.append(MatchModel(**row_dict))
            return matches

    async def get_all_matches(self, limit: int = 100, offset: int = 0) -> List[MatchModel]:
        """Get all matches from the database"""
        import json
        async with self.db_manager.get_connection() as connection:
            rows = await connection.fetch(
                "SELECT * FROM matches ORDER BY incentive_id, rank_position LIMIT $1 OFFSET $2",
                limit, offset
            )
            matches = []
            for row in rows:
                row_dict = dict(row)
                # Deserialize reasoning from JSON string to dict
                if row_dict.get('reasoning') and isinstance(row_dict['reasoning'], str):
                    row_dict['reasoning'] = json.loads(row_dict['reasoning'])
                matches.append(MatchModel(**row_dict))
            return matches

    async def clear_all_matches(self) -> None:
        """Clear all matches from the database"""
        async with self.db_manager.get_connection() as connection:
            await connection.execute("DELETE FROM matches")
            logger.info("All matches cleared from database")

    async def get_matching_statistics(self) -> Dict[str, Any]:
        """Get statistics about matching results"""
        async with self.db_manager.get_connection() as connection:
            stats = {}
            
            # Total matches
            stats["total_matches"] = await connection.fetchval("SELECT COUNT(*) FROM matches")
            
            # Matches per incentive
            stats["incentives_with_matches"] = await connection.fetchval(
                "SELECT COUNT(DISTINCT incentive_id) FROM matches"
            )
            
            # Average score
            avg_score = await connection.fetchval("SELECT AVG(score) FROM matches")
            stats["average_score"] = float(avg_score) if avg_score else 0.0
            
            # Score distribution
            score_dist = await connection.fetch(
                "SELECT FLOOR(score) as score_range, COUNT(*) as count FROM matches GROUP BY FLOOR(score) ORDER BY score_range"
            )
            stats["score_distribution"] = {str(row["score_range"]): row["count"] for row in score_dist}
            
            return stats

    # Helper methods for consistent naming
    async def get_incentive_by_id(self, incentive_id: int) -> Optional[IncentiveModel]:
        """Alias for get_incentive for consistent naming"""
        return await self.get_incentive(incentive_id)

    async def get_company_by_id(self, company_id: int) -> Optional[CompanyModel]:
        """Alias for get_company for consistent naming"""
        return await self.get_company(company_id)

    async def get_all_incentives(
        self,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[IncentiveModel]:
        """
        Get all incentives with optional search, limit and offset

        Args:
            search: Optional search term for title/description
            limit: Optional limit on number of results
            offset: Optional offset for pagination
        """
        async with self.db_manager.get_connection() as connection:
            query = "SELECT * FROM incentives"
            params = []

            if search:
                query += " WHERE title ILIKE $1 OR description ILIKE $1 OR ai_description ILIKE $1"
                params.append(f"%{search}%")

            query += " ORDER BY id"

            if limit:
                query += f" LIMIT ${len(params) + 1}"
                params.append(limit)

            if offset:
                query += f" OFFSET ${len(params) + 1}"
                params.append(offset)

            rows = await connection.fetch(query, *params)
            return [IncentiveModel(**dict(row)) for row in rows]

    async def get_all_companies(
        self,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[CompanyModel]:
        """
        Get all companies with optional search, limit and offset

        Args:
            search: Optional search term for company name/description
            limit: Optional limit on number of results
            offset: Optional offset for pagination
        """
        async with self.db_manager.get_connection() as connection:
            query = "SELECT * FROM companies"
            params = []

            if search:
                query += " WHERE company_name ILIKE $1 OR trade_description_native ILIKE $1 OR cae_primary_label ILIKE $1"
                params.append(f"%{search}%")

            query += " ORDER BY id"

            if limit:
                query += f" LIMIT ${len(params) + 1}"
                params.append(limit)

            if offset:
                query += f" OFFSET ${len(params) + 1}"
                params.append(offset)

            rows = await connection.fetch(query, *params)
            return [CompanyModel(**dict(row)) for row in rows]

    # Health and utility methods
    async def health_check(self) -> Dict[str, Any]:
        """Database health check with statistics"""
        try:
            async with self.db_manager.get_connection() as connection:
                # Basic connectivity test
                test_result = await connection.fetchval("SELECT 1")

                # Get table counts
                incentives_count = await connection.fetchval("SELECT COUNT(*) FROM incentives")
                companies_count = await connection.fetchval("SELECT COUNT(*) FROM companies")

                # Check table existence
                tables_query = """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
                tables = await connection.fetch(tables_query)
                table_names = [row['table_name'] for row in tables]

                return {
                    "status": "healthy" if test_result == 1 else "unhealthy",
                    "incentives_count": incentives_count,
                    "companies_count": companies_count,
                    "tables": table_names,
                    "pool_size": self.db_manager.pool.get_size() if self.db_manager.pool else 0,
                    "pool_idle": self.db_manager.pool.get_idle_size() if self.db_manager.pool else 0
                }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def truncate_tables(self) -> None:
        """Truncate all tables for testing"""
        truncate_script = """
        TRUNCATE TABLE matches RESTART IDENTITY CASCADE;
        TRUNCATE TABLE companies RESTART IDENTITY CASCADE;
        TRUNCATE TABLE incentives RESTART IDENTITY CASCADE;
        """

        try:
            logger.info("Truncating all tables...")
            await self.db_manager.execute_script(truncate_script)
            logger.info("All tables truncated successfully")
        except Exception as e:
            logger.error(f"Failed to truncate tables: {e}")
            raise


# FastAPI dependency function
async def get_database_service() -> DatabaseService:
    """FastAPI dependency for database service"""
    from .connection import get_database
    db_manager = await get_database()
    return DatabaseService(db_manager)