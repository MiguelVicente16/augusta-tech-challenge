-- Migration: Add pgvector extension and vector columns
-- Run this manually: psql -h localhost -U miguel_v16 -d incentivos -f migrations/001_add_pgvector.sql

-- Enable pgvector extension (requires pgvector to be installed system-wide)
-- If this fails, install with: sudo apt-get install postgresql-14-pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop old embedding columns if they exist (from previous implementation)
ALTER TABLE companies DROP COLUMN IF EXISTS embedding_vector;
ALTER TABLE companies DROP COLUMN IF EXISTS embedding_updated_at;
ALTER TABLE incentives DROP COLUMN IF EXISTS embedding_vector;
ALTER TABLE incentives DROP COLUMN IF EXISTS embedding_updated_at;

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
