-- Authorization Service Migration: Create permissions table
-- Version: 001
-- Date: 2025-01-24

-- Create authz schema (authorization)
CREATE SCHEMA IF NOT EXISTS authz;

-- Create unified permissions table
CREATE TABLE IF NOT EXISTS authz.permissions (
    id SERIAL PRIMARY KEY,
    permission_type VARCHAR(50) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id VARCHAR(255),
    resource_type VARCHAR(50),
    resource_name VARCHAR(255),
    resource_category VARCHAR(100),
    access_level VARCHAR(50),
    permission_source VARCHAR(50),
    subscription_tier_required VARCHAR(50),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_permissions_permission_type ON authz.permissions(permission_type);
CREATE INDEX IF NOT EXISTS idx_permissions_target_type_id ON authz.permissions(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_permissions_resource_type_name ON authz.permissions(resource_type, resource_name);
CREATE INDEX IF NOT EXISTS idx_permissions_is_active ON authz.permissions(is_active);
CREATE INDEX IF NOT EXISTS idx_permissions_metadata ON authz.permissions USING GIN(metadata);

-- Comments
COMMENT ON SCHEMA authz IS 'Authorization service schema (authz) - permissions and access control';
COMMENT ON TABLE authz.permissions IS 'Unified permissions table for all authorization types';
COMMENT ON COLUMN authz.permissions.id IS 'Primary key';
COMMENT ON COLUMN authz.permissions.permission_type IS 'Type of permission (resource_config, user_permission, org_permission, audit_log)';
COMMENT ON COLUMN authz.permissions.target_type IS 'Target type (global, user, organization, resource)';
COMMENT ON COLUMN authz.permissions.target_id IS 'Target identifier';
COMMENT ON COLUMN authz.permissions.resource_type IS 'Type of resource';
COMMENT ON COLUMN authz.permissions.resource_name IS 'Resource name';
COMMENT ON COLUMN authz.permissions.access_level IS 'Access level (none, read_only, read_write, admin, owner)';
COMMENT ON COLUMN authz.permissions.permission_source IS 'Source of permission grant';
COMMENT ON COLUMN authz.permissions.subscription_tier_required IS 'Required subscription tier';
COMMENT ON COLUMN authz.permissions.is_active IS 'Whether permission is active';
COMMENT ON COLUMN authz.permissions.metadata IS 'Additional metadata (JSONB)';
