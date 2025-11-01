-- Media Service Initialization Migration
-- Version: 000
-- Date: 2025-10-24
-- Description: Initialize database schema for media service

-- ====================
-- Create Schema
-- ====================

-- Media Service Schema
CREATE SCHEMA IF NOT EXISTS media;
COMMENT ON SCHEMA media IS 'Media service schema for photo/video processing and management';

-- ====================
-- Create Helper Functions
-- ====================

-- Helper function for updating updated_at timestamps
CREATE OR REPLACE FUNCTION media.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION media.update_updated_at() IS 'Trigger function to automatically update updated_at timestamp';
