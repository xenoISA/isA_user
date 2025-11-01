-- Storage Service Initialization Migration
-- Version: 000
-- Date: 2025-10-24
-- Description: Initialize database schemas and roles for microservices architecture

-- ====================
-- Create Schemas
-- ====================

-- Storage Service Schema
CREATE SCHEMA IF NOT EXISTS storage;
COMMENT ON SCHEMA storage IS 'Storage service schema for file storage, sharing, and intelligence indexing';

-- ====================
-- Create Roles
-- ====================

-- Create authenticated role for application access
CREATE ROLE IF NOT EXISTS authenticated;
COMMENT ON ROLE authenticated IS 'Role for authenticated application access to database';

-- ====================
-- Create Helper Functions
-- ====================

-- Helper function for updating updated_at timestamps
CREATE OR REPLACE FUNCTION storage.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION storage.update_updated_at() IS 'Trigger function to automatically update updated_at timestamp';
