-- Run this as postgres superuser to enable the vector extension
-- Command: sudo -u postgres psql -d incentivos -f migrations/001_enable_vector.sql

CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
