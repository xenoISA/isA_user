-- Authorization Service Migration: Create auth_permissions table
-- Version: 001 
-- Date: 2025-01-20

CREATE TABLE IF NOT EXISTS dev.auth_permissions (
    id SERIAL PRIMARY KEY,
    permission_type VARCHAR(50) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id VARCHAR(255),
    resource_type VARCHAR(100) NOT NULL,
    resource_name VARCHAR(255) NOT NULL,
    resource_category VARCHAR(100),
    access_level VARCHAR(50) NOT NULL,
    permission_source VARCHAR(50) NOT NULL,
    subscription_tier_required VARCHAR(50),
    granted_by_user_id VARCHAR(255),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_auth_permissions_permission_type ON dev.auth_permissions(permission_type);
CREATE INDEX idx_auth_permissions_target_type ON dev.auth_permissions(target_type);
CREATE INDEX idx_auth_permissions_target_id ON dev.auth_permissions(target_id);
CREATE INDEX idx_auth_permissions_resource_type ON dev.auth_permissions(resource_type);
CREATE INDEX idx_auth_permissions_resource_name ON dev.auth_permissions(resource_name);
CREATE INDEX idx_auth_permissions_access_level ON dev.auth_permissions(access_level);
CREATE INDEX idx_auth_permissions_permission_source ON dev.auth_permissions(permission_source);
CREATE INDEX idx_auth_permissions_is_active ON dev.auth_permissions(is_active);
CREATE INDEX idx_auth_permissions_expires_at ON dev.auth_permissions(expires_at);
CREATE INDEX idx_auth_permissions_target_resource ON dev.auth_permissions(target_id, resource_type, resource_name);
CREATE INDEX idx_auth_permissions_subscription_tier ON dev.auth_permissions(subscription_tier_required);

-- Composite index for common lookups
CREATE INDEX idx_auth_permissions_user_lookup ON dev.auth_permissions(permission_type, target_id, resource_type, resource_name, is_active);

-- Trigger
CREATE TRIGGER trigger_update_auth_permissions_updated_at
    BEFORE UPDATE ON dev.auth_permissions
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Permissions  
GRANT ALL ON dev.auth_permissions TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.auth_permissions TO authenticated;

-- Comments
COMMENT ON TABLE dev.auth_permissions IS 'Unified authorization permissions table for all permission types';
COMMENT ON COLUMN dev.auth_permissions.permission_type IS 'Type of permission (user_permission, resource_config, org_permission, audit_log)';
COMMENT ON COLUMN dev.auth_permissions.target_type IS 'Type of target (user, organization, global, system)';
COMMENT ON COLUMN dev.auth_permissions.target_id IS 'ID of the target entity';
COMMENT ON COLUMN dev.auth_permissions.resource_type IS 'Type of resource being accessed';
COMMENT ON COLUMN dev.auth_permissions.resource_name IS 'Name of the specific resource';
COMMENT ON COLUMN dev.auth_permissions.resource_category IS 'Category of the resource';
COMMENT ON COLUMN dev.auth_permissions.access_level IS 'Level of access granted (read, write, admin, etc.)';
COMMENT ON COLUMN dev.auth_permissions.permission_source IS 'Source of the permission (system_default, organization_admin, manual, etc.)';
COMMENT ON COLUMN dev.auth_permissions.subscription_tier_required IS 'Required subscription tier for this permission';
COMMENT ON COLUMN dev.auth_permissions.granted_by_user_id IS 'User who granted this permission';
COMMENT ON COLUMN dev.auth_permissions.expires_at IS 'Expiration timestamp for temporary permissions';
COMMENT ON COLUMN dev.auth_permissions.is_active IS 'Whether permission is currently active';
COMMENT ON COLUMN dev.auth_permissions.description IS 'Description of the permission';