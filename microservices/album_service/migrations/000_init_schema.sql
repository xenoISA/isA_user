-- Album Service Initialization Migration
-- Version: 000
-- Date: 2025-10-24
-- Description: Initialize database schema for album service

-- ====================
-- Create Schema
-- ====================

-- Album Service Schema
CREATE SCHEMA IF NOT EXISTS album;
COMMENT ON SCHEMA album IS 'Album service schema for photo album management';

-- ====================
-- Create Helper Functions
-- ====================

-- Helper function for updating updated_at timestamps
CREATE OR REPLACE FUNCTION album.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION album.update_updated_at() IS 'Trigger function to automatically update updated_at timestamp';
