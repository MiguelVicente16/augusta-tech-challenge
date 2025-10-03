"""
SQL queries for companies table

All queries related to companies data retrieval and manipulation.
These queries can be used by agents as tools.
"""

# ============================================================================
# CREATE / INSERT
# ============================================================================

INSERT_COMPANY = """
INSERT INTO companies (company_name, cae_primary_label, trade_description_native, website)
VALUES ($1, $2, $3, $4)
RETURNING id
"""

BATCH_INSERT_COMPANY = """
INSERT INTO companies (company_name, cae_primary_label, trade_description_native, website)
VALUES ($1, $2, $3, $4)
"""

# ============================================================================
# READ / SELECT
# ============================================================================

SELECT_BY_ID = """
SELECT * FROM companies WHERE id = $1
"""

SELECT_ALL = """
SELECT * FROM companies
ORDER BY company_name
LIMIT $1 OFFSET $2
"""

COUNT_ALL = """
SELECT COUNT(*) FROM companies
"""

# ============================================================================
# SEARCH
# ============================================================================

SEARCH_FULL_TEXT = """
SELECT * FROM companies
WHERE to_tsvector('portuguese', company_name || ' ' || COALESCE(trade_description_native, ''))
      @@ plainto_tsquery('portuguese', $1)
ORDER BY ts_rank(
    to_tsvector('portuguese', company_name || ' ' || COALESCE(trade_description_native, '')),
    plainto_tsquery('portuguese', $1)
) DESC
LIMIT $2
"""

SEARCH_BY_NAME = """
SELECT id, company_name, cae_primary_label, website
FROM companies
WHERE company_name ILIKE $1
ORDER BY company_name
LIMIT $2
"""

SEARCH_BY_CAE = """
SELECT * FROM companies
WHERE cae_primary_label = $1
ORDER BY company_name
LIMIT $2
"""

SEARCH_BY_CAE_PATTERN = """
SELECT * FROM companies
WHERE cae_primary_label ILIKE $1
ORDER BY company_name
LIMIT $2
"""

# ============================================================================
# STATISTICS
# ============================================================================

COUNT_WITH_CAE = """
SELECT COUNT(*) FROM companies WHERE cae_primary_label IS NOT NULL
"""

COUNT_WITH_WEBSITE = """
SELECT COUNT(*) FROM companies WHERE website IS NOT NULL AND website != ''
"""

COUNT_WITH_DESCRIPTION = """
SELECT COUNT(*) FROM companies WHERE trade_description_native IS NOT NULL
"""

TOP_CAE_SECTORS = """
SELECT cae_primary_label, COUNT(*) as count
FROM companies
WHERE cae_primary_label IS NOT NULL
GROUP BY cae_primary_label
ORDER BY count DESC
LIMIT $1
"""

# ============================================================================
# AGENT TOOLS - Specific queries for AI agents
# ============================================================================

GET_COMPANY_FOR_MATCHING = """
SELECT
    id,
    company_name,
    cae_primary_label,
    trade_description_native,
    website
FROM companies
WHERE id = $1
"""

GET_ALL_COMPANIES_FOR_MATCHING = """
SELECT
    id,
    company_name,
    cae_primary_label,
    trade_description_native
FROM companies
ORDER BY id
"""

GET_COMPANIES_BY_SECTOR = """
SELECT
    id,
    company_name,
    cae_primary_label,
    trade_description_native,
    website
FROM companies
WHERE cae_primary_label = $1
ORDER BY company_name
LIMIT $2
"""

SEARCH_COMPANIES_BY_KEYWORDS = """
SELECT id, company_name, cae_primary_label, trade_description_native
FROM companies
WHERE to_tsvector('portuguese', company_name || ' ' || COALESCE(trade_description_native, '') || ' ' || COALESCE(cae_primary_label, ''))
      @@ plainto_tsquery('portuguese', $1)
ORDER BY ts_rank(
    to_tsvector('portuguese', company_name || ' ' || COALESCE(trade_description_native, '') || ' ' || COALESCE(cae_primary_label, '')),
    plainto_tsquery('portuguese', $1)
) DESC
LIMIT $2
"""

GET_RANDOM_COMPANIES_SAMPLE = """
SELECT * FROM companies
ORDER BY RANDOM()
LIMIT $1
"""
