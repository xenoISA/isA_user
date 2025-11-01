-- Memory Service Migration: Initialize memory schema
-- Version: 000
-- Date: 2025-01-24
--
-- IMPORTANT: Architecture
-- - PostgreSQL: Stores structured memory data
-- - Qdrant: Stores vector embeddings for semantic search
-- - No pgvector dependency
--
-- Microservices Best Practices:
-- - No Foreign Keys to other services: user_id has NO FK constraints
-- - Application-level validation via auth_service APIs
-- - Cross-service relationships managed in application layer

-- Create memory schema
CREATE SCHEMA IF NOT EXISTS memory;

-- Create helper function for updated_at trigger
CREATE OR REPLACE FUNCTION memory.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Comments
COMMENT ON SCHEMA memory IS 'Memory service schema for AI-powered intelligent memory storage (PostgreSQL + Qdrant architecture)';
COMMENT ON FUNCTION memory.update_updated_at() IS 'Trigger function to automatically update updated_at timestamp';
