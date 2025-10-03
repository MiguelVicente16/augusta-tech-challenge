"""
SQL schema definitions for all database tables

Contains table creation statements and indices.
Separated from models for clarity.
"""

# ============================================================================
# TABLE CREATION
# ============================================================================

CREATE_INCENTIVES_TABLE = """
CREATE TABLE IF NOT EXISTS incentives (
    id SERIAL PRIMARY KEY,
    incentive_project_id VARCHAR(255),
    project_id VARCHAR(255),
    title TEXT NOT NULL,
    description TEXT,
    ai_description TEXT,
    ai_description_structured JSONB,
    eligibility_criteria JSONB,
    document_urls JSONB,
    date_publication DATE,
    date_start DATE,
    date_end DATE,
    total_budget DECIMAL(15,2),
    source_link TEXT,
    status VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
"""

CREATE_COMPANIES_TABLE = """
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    company_name TEXT NOT NULL,
    cae_primary_label TEXT,
    trade_description_native TEXT,
    website TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
"""

CREATE_MATCHES_TABLE = """
CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    incentive_id INTEGER REFERENCES incentives(id) ON DELETE CASCADE,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    score DECIMAL(5,4) CHECK (score >= 0 AND score <= 5),
    rank_position INTEGER CHECK (rank_position >= 1 AND rank_position <= 5),
    reasoning JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(incentive_id, company_id)
);
"""

# ============================================================================
# INDICES FOR PERFORMANCE
# ============================================================================

CREATE_INDICES = """
-- Incentives table indices
CREATE INDEX IF NOT EXISTS idx_incentives_title ON incentives USING gin(to_tsvector('portuguese', title));
CREATE INDEX IF NOT EXISTS idx_incentives_description ON incentives USING gin(to_tsvector('portuguese', description));
CREATE INDEX IF NOT EXISTS idx_incentives_status ON incentives(status);
CREATE INDEX IF NOT EXISTS idx_incentives_dates ON incentives(date_start, date_end);
CREATE INDEX IF NOT EXISTS idx_incentives_budget ON incentives(total_budget);
CREATE INDEX IF NOT EXISTS idx_incentives_eligibility ON incentives USING gin(eligibility_criteria);
CREATE INDEX IF NOT EXISTS idx_incentives_ai_description_structured ON incentives USING gin(ai_description_structured);

-- Companies table indices
CREATE INDEX IF NOT EXISTS idx_companies_name ON companies USING gin(to_tsvector('portuguese', company_name));
CREATE INDEX IF NOT EXISTS idx_companies_cae ON companies(cae_primary_label);
CREATE INDEX IF NOT EXISTS idx_companies_trade_desc ON companies USING gin(to_tsvector('portuguese', trade_description_native));

-- Matches table indices (for Phase 2)
CREATE INDEX IF NOT EXISTS idx_matches_incentive ON matches(incentive_id);
CREATE INDEX IF NOT EXISTS idx_matches_company ON matches(company_id);
CREATE INDEX IF NOT EXISTS idx_matches_score ON matches(score DESC);
CREATE INDEX IF NOT EXISTS idx_matches_rank ON matches(incentive_id, rank_position);
"""

# ============================================================================
# MIGRATIONS - Schema alterations for existing tables
# ============================================================================

MIGRATIONS = """
-- Add ai_description_structured column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='incentives' AND column_name='ai_description_structured'
    ) THEN
        ALTER TABLE incentives ADD COLUMN ai_description_structured JSONB;
    END IF;
END $$;

-- Add document_urls column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='incentives' AND column_name='document_urls'
    ) THEN
        ALTER TABLE incentives ADD COLUMN document_urls JSONB;
    END IF;
END $$;

-- Add date_publication column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='incentives' AND column_name='date_publication'
    ) THEN
        ALTER TABLE incentives ADD COLUMN date_publication DATE;
    END IF;
END $$;
"""

# ============================================================================
# FULL SCHEMA - Combined script for setup
# ============================================================================

FULL_SCHEMA = f"""
{CREATE_INCENTIVES_TABLE}
{CREATE_COMPANIES_TABLE}
{CREATE_MATCHES_TABLE}
{MIGRATIONS}
{CREATE_INDICES}
"""
