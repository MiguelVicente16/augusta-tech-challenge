"""
SQL queries for matches table (Phase 2)

All queries related to company-incentive matching.
These queries will be used by matching agents.
"""

# ============================================================================
# CREATE / INSERT
# ============================================================================

INSERT_MATCH = """
INSERT INTO matches (
    incentive_id, company_id, score, rank_position, reasoning
) VALUES ($1, $2, $3, $4, $5)
RETURNING id
"""

BATCH_INSERT_MATCHES = """
INSERT INTO matches (
    incentive_id, company_id, score, rank_position, reasoning
) VALUES ($1, $2, $3, $4, $5)
ON CONFLICT (incentive_id, company_id)
DO UPDATE SET
    score = EXCLUDED.score,
    rank_position = EXCLUDED.rank_position,
    reasoning = EXCLUDED.reasoning,
    created_at = NOW()
"""

# ============================================================================
# READ / SELECT
# ============================================================================

GET_TOP_MATCHES_FOR_INCENTIVE = """
SELECT
    m.*,
    c.company_name,
    c.cae_primary_label,
    c.trade_description_native
FROM matches m
JOIN companies c ON m.company_id = c.id
WHERE m.incentive_id = $1
ORDER BY m.rank_position
LIMIT $2
"""

GET_TOP_MATCHES_FOR_COMPANY = """
SELECT
    m.*,
    i.title,
    i.description,
    i.total_budget,
    i.date_start,
    i.date_end
FROM matches m
JOIN incentives i ON m.incentive_id = i.id
WHERE m.company_id = $1
ORDER BY m.score DESC
LIMIT $2
"""

GET_MATCH_DETAILS = """
SELECT
    m.*,
    i.title as incentive_title,
    i.description as incentive_description,
    c.company_name,
    c.cae_primary_label
FROM matches m
JOIN incentives i ON m.incentive_id = i.id
JOIN companies c ON m.company_id = c.id
WHERE m.id = $1
"""

# ============================================================================
# STATISTICS
# ============================================================================

COUNT_ALL = """
SELECT COUNT(*) FROM matches
"""

AVERAGE_SCORE = """
SELECT AVG(score) FROM matches
"""

SCORE_DISTRIBUTION = """
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
"""

COUNT_MATCHES_PER_INCENTIVE = """
SELECT incentive_id, COUNT(*) as match_count
FROM matches
GROUP BY incentive_id
ORDER BY match_count DESC
"""

COUNT_MATCHES_PER_COMPANY = """
SELECT company_id, COUNT(*) as match_count
FROM matches
GROUP BY company_id
ORDER BY match_count DESC
"""

# ============================================================================
# EXPORT - For CSV generation
# ============================================================================

EXPORT_ALL_MATCHES = """
SELECT
    i.title as incentive_title,
    i.incentive_project_id,
    c.company_name,
    c.cae_primary_label,
    m.score,
    m.rank_position,
    m.reasoning
FROM matches m
JOIN incentives i ON m.incentive_id = i.id
JOIN companies c ON m.company_id = c.id
ORDER BY i.title, m.rank_position
"""

EXPORT_MATCHES_FOR_INCENTIVE = """
SELECT
    c.company_name,
    c.cae_primary_label,
    c.trade_description_native,
    c.website,
    m.score,
    m.rank_position,
    m.reasoning
FROM matches m
JOIN companies c ON m.company_id = c.id
WHERE m.incentive_id = $1
ORDER BY m.rank_position
"""

# ============================================================================
# DELETE / CLEANUP
# ============================================================================

DELETE_MATCHES_FOR_INCENTIVE = """
DELETE FROM matches WHERE incentive_id = $1
"""

DELETE_MATCHES_FOR_COMPANY = """
DELETE FROM matches WHERE company_id = $1
"""

DELETE_LOW_SCORE_MATCHES = """
DELETE FROM matches WHERE score < $1
"""

# ============================================================================
# AGENT TOOLS - For matching algorithms
# ============================================================================

CHECK_EXISTING_MATCH = """
SELECT id, score, rank_position
FROM matches
WHERE incentive_id = $1 AND company_id = $2
"""

GET_INCENTIVES_WITHOUT_MATCHES = """
SELECT i.*
FROM incentives i
LEFT JOIN matches m ON i.id = m.incentive_id
WHERE m.id IS NULL
  AND i.status = 'active'
ORDER BY i.created_at DESC
"""

GET_COMPANIES_WITHOUT_MATCHES = """
SELECT c.*
FROM companies c
LEFT JOIN matches m ON c.id = m.company_id
WHERE m.id IS NULL
ORDER BY c.company_name
LIMIT $1
"""

UPDATE_MATCH_SCORE = """
UPDATE matches
SET score = $1, reasoning = $2, created_at = NOW()
WHERE incentive_id = $3 AND company_id = $4
"""
