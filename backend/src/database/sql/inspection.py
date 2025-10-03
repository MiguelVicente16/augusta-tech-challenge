"""
SQL queries for database inspection and statistics

Meta-queries for analyzing database structure and contents.
"""

# ============================================================================
# SCHEMA INSPECTION
# ============================================================================

LIST_ALL_TABLES = """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name
"""

GET_TABLE_SCHEMA = """
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = $1
ORDER BY ordinal_position
"""

GET_TABLE_SIZE = """
SELECT pg_size_pretty(pg_total_relation_size($1)) as size
"""

# ============================================================================
# DATABASE HEALTH
# ============================================================================

GET_POSTGRES_VERSION = """
SELECT version()
"""

GET_DATABASE_SIZE = """
SELECT pg_size_pretty(pg_database_size(current_database()))
"""

GET_CONNECTION_COUNT = """
SELECT count(*) as connections
FROM pg_stat_activity
WHERE datname = current_database()
"""

# ============================================================================
# SEARCH EXAMPLES - For inspection endpoints
# ============================================================================

SEARCH_INCENTIVES_PREVIEW = """
SELECT id, title, LEFT(description, 100) as description_preview
FROM incentives
WHERE to_tsvector('portuguese', title || ' ' || COALESCE(description, ''))
      @@ plainto_tsquery('portuguese', $1)
ORDER BY ts_rank(
    to_tsvector('portuguese', title || ' ' || COALESCE(description, '')),
    plainto_tsquery('portuguese', $1)
) DESC
LIMIT $2
"""

SEARCH_COMPANIES_PREVIEW = """
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
"""
