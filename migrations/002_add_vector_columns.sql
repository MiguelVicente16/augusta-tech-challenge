-- Run this as regular user after enabling the extension
-- Command: PGPASSWORD=augusta_db psql -h localhost -U miguel_v16 -d incentivos -f migrations/002_add_vector_columns.sql

-- Add vector column to incentives table (1536 dimensions for text-embedding-3-small)
ALTER TABLE incentives
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Add vector column to companies table
ALTER TABLE companies
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Create index for fast similarity search on incentives
CREATE INDEX IF NOT EXISTS incentives_embedding_idx
ON incentives
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create index for fast similarity search on companies
CREATE INDEX IF NOT EXISTS companies_embedding_idx
ON companies
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Verify tables
\d incentives
\d companies

-- Check stats
SELECT
    'incentives' as table_name,
    COUNT(*) as total_rows,
    COUNT(embedding) as rows_with_embeddings
FROM incentives
UNION ALL
SELECT
    'companies' as table_name,
    COUNT(*) as total_rows,
    COUNT(embedding) as rows_with_embeddings
FROM companies;
