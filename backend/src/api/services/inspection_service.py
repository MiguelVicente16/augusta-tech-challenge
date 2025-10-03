"""
Database Inspection Service

Provides utilities for inspecting database structure, statistics, and health.
"""

import json
import logging
from typing import Dict, List, Any, Optional

from ...database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class DatabaseInspectionService:
    """Service for database inspection and statistics"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def get_table_list(self) -> List[str]:
        """Get list of all tables in the database"""
        async with self.db_manager.get_connection() as conn:
            tables = await conn.fetch("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            return [t['table_name'] for t in tables]

    async def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema information for a specific table"""
        async with self.db_manager.get_connection() as conn:
            columns = await conn.fetch("""
                SELECT
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = $1
                ORDER BY ordinal_position
            """, table_name)

            return [
                {
                    "column_name": col['column_name'],
                    "data_type": col['data_type'] +
                        (f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""),
                    "nullable": col['is_nullable'] == 'YES',
                    "default": col['column_default']
                }
                for col in columns
            ]

    async def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """Get statistics for a specific table"""
        async with self.db_manager.get_connection() as conn:
            # Total count
            total = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")

            stats = {
                "table_name": table_name,
                "total_records": total
            }

            # Table-specific statistics
            if table_name == 'incentives':
                stats.update(await self._get_incentives_stats(conn, total))
            elif table_name == 'companies':
                stats.update(await self._get_companies_stats(conn, total))
            elif table_name == 'matches':
                stats.update(await self._get_matches_stats(conn, total))

            return stats

    async def _get_incentives_stats(self, conn, total: int) -> Dict[str, Any]:
        """Get incentive-specific statistics"""
        with_budget = await conn.fetchval(
            "SELECT COUNT(*) FROM incentives WHERE total_budget IS NOT NULL"
        )
        with_dates = await conn.fetchval(
            "SELECT COUNT(*) FROM incentives WHERE date_start IS NOT NULL AND date_end IS NOT NULL"
        )
        with_criteria = await conn.fetchval(
            "SELECT COUNT(*) FROM incentives WHERE eligibility_criteria IS NOT NULL"
        )
        with_ai_structured = await conn.fetchval(
            "SELECT COUNT(*) FROM incentives WHERE ai_description_structured IS NOT NULL"
        )

        budget_stats = await conn.fetchrow("""
            SELECT
                MIN(total_budget) as min_budget,
                MAX(total_budget) as max_budget,
                AVG(total_budget) as avg_budget
            FROM incentives
            WHERE total_budget IS NOT NULL
        """)

        return {
            "records_with_budget": with_budget,
            "records_with_dates": with_dates,
            "records_with_eligibility_criteria": with_criteria,
            "records_with_ai_structured": with_ai_structured,
            "budget_stats": {
                "min": float(budget_stats['min_budget']) if budget_stats['min_budget'] else None,
                "max": float(budget_stats['max_budget']) if budget_stats['max_budget'] else None,
                "avg": float(budget_stats['avg_budget']) if budget_stats['avg_budget'] else None
            } if budget_stats['min_budget'] else None
        }

    async def _get_companies_stats(self, conn, total: int) -> Dict[str, Any]:
        """Get company-specific statistics"""
        with_cae = await conn.fetchval(
            "SELECT COUNT(*) FROM companies WHERE cae_primary_label IS NOT NULL"
        )
        with_website = await conn.fetchval(
            "SELECT COUNT(*) FROM companies WHERE website IS NOT NULL AND website != ''"
        )
        with_description = await conn.fetchval(
            "SELECT COUNT(*) FROM companies WHERE trade_description_native IS NOT NULL"
        )

        # Top CAE codes
        top_cae = await conn.fetch("""
            SELECT cae_primary_label, COUNT(*) as count
            FROM companies
            WHERE cae_primary_label IS NOT NULL
            GROUP BY cae_primary_label
            ORDER BY count DESC
            LIMIT 10
        """)

        return {
            "records_with_cae": with_cae,
            "records_with_website": with_website,
            "records_with_description": with_description,
            "top_cae_sectors": [
                {"sector": cae['cae_primary_label'], "count": cae['count']}
                for cae in top_cae
            ]
        }

    async def _get_matches_stats(self, conn, total: int) -> Dict[str, Any]:
        """Get matches-specific statistics"""
        if total == 0:
            return {}

        avg_score = await conn.fetchval(
            "SELECT AVG(score) FROM matches"
        )

        score_distribution = await conn.fetch("""
            SELECT
                CASE
                    WHEN score >= 4.5 THEN 'excellent'
                    WHEN score >= 3.5 THEN 'good'
                    WHEN score >= 2.5 THEN 'moderate'
                    ELSE 'poor'
                END as category,
                COUNT(*) as count
            FROM matches
            GROUP BY category
            ORDER BY MIN(score) DESC
        """)

        return {
            "average_score": float(avg_score) if avg_score else None,
            "score_distribution": [
                {"category": row['category'], "count": row['count']}
                for row in score_distribution
            ]
        }

    async def get_sample_data(
        self,
        table_name: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get sample records from a table"""
        async with self.db_manager.get_connection() as conn:
            rows = await conn.fetch(f"SELECT * FROM {table_name} LIMIT {limit}")

            # Convert to dict and handle special types
            result = []
            for row in rows:
                record = dict(row)
                # Convert Decimal, date, datetime to JSON-serializable types
                for key, value in record.items():
                    if isinstance(value, dict):
                        # JSONB fields
                        record[key] = value
                    elif hasattr(value, 'isoformat'):
                        # Date/datetime
                        record[key] = value.isoformat()
                    elif hasattr(value, '__float__'):
                        # Decimal
                        record[key] = float(value)
                result.append(record)

            return result

    async def search_table(
        self,
        table_name: str,
        search_term: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search records in a table using full-text search"""
        async with self.db_manager.get_connection() as conn:
            if table_name == 'incentives':
                results = await conn.fetch("""
                    SELECT id, title, LEFT(description, 150) as description_preview
                    FROM incentives
                    WHERE to_tsvector('portuguese', title || ' ' || COALESCE(description, ''))
                          @@ plainto_tsquery('portuguese', $1)
                    ORDER BY ts_rank(
                        to_tsvector('portuguese', title || ' ' || COALESCE(description, '')),
                        plainto_tsquery('portuguese', $1)
                    ) DESC
                    LIMIT $2
                """, search_term, limit)

            elif table_name == 'companies':
                results = await conn.fetch("""
                    SELECT id, company_name, cae_primary_label,
                           LEFT(trade_description_native, 100) as description_preview
                    FROM companies
                    WHERE to_tsvector('portuguese', company_name || ' ' || COALESCE(trade_description_native, ''))
                          @@ plainto_tsquery('portuguese', $1)
                    ORDER BY ts_rank(
                        to_tsvector('portuguese', company_name || ' ' || COALESCE(trade_description_native, '')),
                        plainto_tsquery('portuguese', $1)
                    ) DESC
                    LIMIT $2
                """, search_term, limit)

            else:
                return []

            return [dict(row) for row in results]

    async def get_database_health(self) -> Dict[str, Any]:
        """Get overall database health and status"""
        try:
            async with self.db_manager.get_connection() as conn:
                # Get PostgreSQL version
                version = await conn.fetchval("SELECT version()")

                # Get database size
                db_size = await conn.fetchval("""
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """)

                # Get table counts
                tables = await self.get_table_list()
                table_counts = {}
                for table in tables:
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                    table_counts[table] = count

                # Get connection pool stats
                pool_info = self.db_manager.get_pool_stats()

                return {
                    "status": "healthy",
                    "postgresql_version": version.split(',')[0],  # First part of version string
                    "database_size": db_size,
                    "tables": table_counts,
                    "connection_pool": pool_info
                }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
