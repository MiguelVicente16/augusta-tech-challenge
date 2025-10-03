"""
SQL queries for incentives table

All queries related to incentives data retrieval and manipulation.
These queries can be used by agents as tools.
"""

# ============================================================================
# CREATE / INSERT
# ============================================================================

INSERT_INCENTIVE = """
INSERT INTO incentives (
    incentive_project_id, project_id, title, description, ai_description,
    ai_description_structured, eligibility_criteria, document_urls, date_publication,
    date_start, date_end, total_budget, source_link, status
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
RETURNING id
"""

BATCH_INSERT_INCENTIVE = """
INSERT INTO incentives (
    incentive_project_id, project_id, title, description, ai_description,
    ai_description_structured, eligibility_criteria, document_urls, date_publication,
    date_start, date_end, total_budget, source_link, status
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
"""

# ============================================================================
# READ / SELECT
# ============================================================================

SELECT_BY_ID = """
SELECT * FROM incentives WHERE id = $1
"""

SELECT_ALL = """
SELECT * FROM incentives
ORDER BY created_at DESC
LIMIT $1 OFFSET $2
"""

COUNT_ALL = """
SELECT COUNT(*) FROM incentives
"""

# ============================================================================
# SEARCH
# ============================================================================

SEARCH_FULL_TEXT = """
SELECT * FROM incentives
WHERE to_tsvector('portuguese', title || ' ' || COALESCE(description, ''))
      @@ plainto_tsquery('portuguese', $1)
ORDER BY ts_rank(
    to_tsvector('portuguese', title || ' ' || COALESCE(description, '')),
    plainto_tsquery('portuguese', $1)
) DESC
LIMIT $2
"""

SEARCH_BY_TITLE = """
SELECT id, title, description
FROM incentives
WHERE title ILIKE $1
ORDER BY title
LIMIT $2
"""

SEARCH_BY_SECTOR = """
SELECT * FROM incentives
WHERE ai_description_structured @> $1::jsonb
LIMIT $2
"""

# ============================================================================
# FILTERS
# ============================================================================

FILTER_BY_BUDGET_RANGE = """
SELECT * FROM incentives
WHERE total_budget BETWEEN $1 AND $2
ORDER BY total_budget DESC
LIMIT $3
"""

FILTER_BY_DATE_RANGE = """
SELECT * FROM incentives
WHERE date_start >= $1 AND date_end <= $2
ORDER BY date_start
"""

FILTER_ACTIVE = """
SELECT * FROM incentives
WHERE status = 'active'
  AND date_start <= CURRENT_DATE
  AND (date_end IS NULL OR date_end >= CURRENT_DATE)
ORDER BY date_start DESC
LIMIT $1
"""

# ============================================================================
# STATISTICS
# ============================================================================

COUNT_WITH_BUDGET = """
SELECT COUNT(*) FROM incentives WHERE total_budget IS NOT NULL
"""

COUNT_WITH_DATES = """
SELECT COUNT(*) FROM incentives
WHERE date_start IS NOT NULL AND date_end IS NOT NULL
"""

COUNT_WITH_ELIGIBILITY = """
SELECT COUNT(*) FROM incentives WHERE eligibility_criteria IS NOT NULL
"""

COUNT_WITH_AI_STRUCTURED = """
SELECT COUNT(*) FROM incentives WHERE ai_description_structured IS NOT NULL
"""

BUDGET_STATISTICS = """
SELECT
    MIN(total_budget) as min_budget,
    MAX(total_budget) as max_budget,
    AVG(total_budget) as avg_budget,
    COUNT(*) as count_with_budget
FROM incentives
WHERE total_budget IS NOT NULL
"""

# ============================================================================
# AGENT TOOLS - Specific queries for AI agents
# ============================================================================

GET_INCENTIVE_FOR_MATCHING = """
SELECT
    id,
    title,
    description,
    ai_description,
    ai_description_structured,
    eligibility_criteria,
    total_budget,
    date_start,
    date_end,
    status
FROM incentives
WHERE id = $1
"""

GET_ALL_ACTIVE_INCENTIVES_FOR_MATCHING = """
SELECT
    id,
    title,
    ai_description_structured,
    eligibility_criteria,
    total_budget
FROM incentives
WHERE status = 'active'
  AND (date_end IS NULL OR date_end >= CURRENT_DATE)
ORDER BY id
"""

SEARCH_INCENTIVES_BY_KEYWORDS = """
SELECT id, title, description, ai_description_structured
FROM incentives
WHERE to_tsvector('portuguese', title || ' ' || COALESCE(description, '') || ' ' || COALESCE(ai_description, ''))
      @@ plainto_tsquery('portuguese', $1)
ORDER BY ts_rank(
    to_tsvector('portuguese', title || ' ' || COALESCE(description, '') || ' ' || COALESCE(ai_description, '')),
    plainto_tsquery('portuguese', $1)
) DESC
LIMIT $2
"""
