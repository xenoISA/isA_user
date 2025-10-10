-- Organization Service Migration: Create family sharing tables
-- Version: 002
-- Date: 2025-10-04
-- Description: Tables for family sharing functionality supporting subscription, device, storage, wallet, and media library sharing

-- Drop existing tables if needed (be careful in production!)
DROP TABLE IF EXISTS dev.family_sharing_usage_stats CASCADE;
DROP TABLE IF EXISTS dev.family_sharing_member_permissions CASCADE;
DROP TABLE IF EXISTS dev.family_sharing_resources CASCADE;

-- Create family sharing resources table
-- Stores shared resources (subscriptions, devices, storage, wallets, etc.)
CREATE TABLE dev.family_sharing_resources (
    id SERIAL PRIMARY KEY,
    sharing_id VARCHAR(255) NOT NULL UNIQUE,
    organization_id VARCHAR(255) NOT NULL,
    resource_type VARCHAR(50) NOT NULL, -- subscription, device, storage, wallet, media_library, calendar, shopping_list, location
    resource_id VARCHAR(255) NOT NULL,
    resource_name VARCHAR(255),
    created_by VARCHAR(255) NOT NULL,
    share_with_all_members BOOLEAN DEFAULT FALSE,
    default_permission VARCHAR(50) NOT NULL DEFAULT 'read_write', -- owner, admin, full_access, read_write, read_only, limited, view_only
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- active, paused, expired, revoked, pending
    quota_settings JSONB DEFAULT '{}'::jsonb,
    restrictions JSONB DEFAULT '{}'::jsonb,
    expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_sharing_organization FOREIGN KEY (organization_id)
        REFERENCES dev.organizations(organization_id) ON DELETE CASCADE,
    CONSTRAINT fk_sharing_created_by FOREIGN KEY (created_by)
        REFERENCES dev.users(user_id) ON DELETE CASCADE,
    CONSTRAINT sharing_resource_type_valid CHECK (resource_type IN ('subscription', 'device', 'storage', 'wallet', 'media_library', 'calendar', 'shopping_list', 'location')),
    CONSTRAINT sharing_default_permission_valid CHECK (default_permission IN ('owner', 'admin', 'full_access', 'read_write', 'read_only', 'limited', 'view_only')),
    CONSTRAINT sharing_status_valid CHECK (status IN ('active', 'paused', 'expired', 'revoked', 'pending')),
    CONSTRAINT sharing_resource_name_not_empty CHECK (resource_name IS NULL OR length(trim(resource_name)) > 0),
    UNIQUE (organization_id, resource_type, resource_id)
);

-- Create family sharing member permissions table
-- Stores individual member permissions for shared resources
CREATE TABLE dev.family_sharing_member_permissions (
    id SERIAL PRIMARY KEY,
    permission_id VARCHAR(255) NOT NULL UNIQUE,
    sharing_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    permission_level VARCHAR(50) NOT NULL, -- owner, admin, full_access, read_write, read_only, limited, view_only
    quota_allocated JSONB DEFAULT '{}'::jsonb,
    quota_used JSONB DEFAULT '{}'::jsonb,
    restrictions JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_permission_sharing FOREIGN KEY (sharing_id)
        REFERENCES dev.family_sharing_resources(sharing_id) ON DELETE CASCADE,
    CONSTRAINT fk_permission_user FOREIGN KEY (user_id)
        REFERENCES dev.users(user_id) ON DELETE CASCADE,
    CONSTRAINT permission_level_valid CHECK (permission_level IN ('owner', 'admin', 'full_access', 'read_write', 'read_only', 'limited', 'view_only')),
    UNIQUE (sharing_id, user_id)
);

-- Create family sharing usage statistics table
-- Tracks usage statistics for shared resources
CREATE TABLE dev.family_sharing_usage_stats (
    id SERIAL PRIMARY KEY,
    stats_id VARCHAR(255) NOT NULL UNIQUE,
    sharing_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    period_type VARCHAR(20) NOT NULL, -- daily, weekly, monthly
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    usage_data JSONB DEFAULT '{}'::jsonb,
    quota_utilization DECIMAL(5, 2), -- Percentage 0-100
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_usage_sharing FOREIGN KEY (sharing_id)
        REFERENCES dev.family_sharing_resources(sharing_id) ON DELETE CASCADE,
    CONSTRAINT fk_usage_user FOREIGN KEY (user_id)
        REFERENCES dev.users(user_id) ON DELETE CASCADE,
    CONSTRAINT usage_period_type_valid CHECK (period_type IN ('daily', 'weekly', 'monthly')),
    CONSTRAINT usage_quota_utilization_valid CHECK (quota_utilization IS NULL OR (quota_utilization >= 0 AND quota_utilization <= 100)),
    CONSTRAINT usage_period_valid CHECK (period_start < period_end),
    UNIQUE (sharing_id, user_id, period_type, period_start)
);

-- Create indexes for performance
CREATE INDEX idx_sharing_resources_organization_id ON dev.family_sharing_resources(organization_id);
CREATE INDEX idx_sharing_resources_resource_type ON dev.family_sharing_resources(resource_type);
CREATE INDEX idx_sharing_resources_resource_id ON dev.family_sharing_resources(resource_id);
CREATE INDEX idx_sharing_resources_created_by ON dev.family_sharing_resources(created_by);
CREATE INDEX idx_sharing_resources_status ON dev.family_sharing_resources(status) WHERE status = 'active';
CREATE INDEX idx_sharing_resources_created_at ON dev.family_sharing_resources(created_at DESC);
CREATE INDEX idx_sharing_resources_expires_at ON dev.family_sharing_resources(expires_at) WHERE expires_at IS NOT NULL;

CREATE INDEX idx_member_permissions_sharing_id ON dev.family_sharing_member_permissions(sharing_id);
CREATE INDEX idx_member_permissions_user_id ON dev.family_sharing_member_permissions(user_id);
CREATE INDEX idx_member_permissions_permission_level ON dev.family_sharing_member_permissions(permission_level);
CREATE INDEX idx_member_permissions_is_active ON dev.family_sharing_member_permissions(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_member_permissions_granted_at ON dev.family_sharing_member_permissions(granted_at DESC);
CREATE INDEX idx_member_permissions_last_accessed ON dev.family_sharing_member_permissions(last_accessed_at DESC) WHERE last_accessed_at IS NOT NULL;

CREATE INDEX idx_usage_stats_sharing_id ON dev.family_sharing_usage_stats(sharing_id);
CREATE INDEX idx_usage_stats_user_id ON dev.family_sharing_usage_stats(user_id);
CREATE INDEX idx_usage_stats_period_type ON dev.family_sharing_usage_stats(period_type);
CREATE INDEX idx_usage_stats_period_start ON dev.family_sharing_usage_stats(period_start DESC);

-- Create composite indexes for common queries
CREATE INDEX idx_sharing_resources_org_type ON dev.family_sharing_resources(organization_id, resource_type);
CREATE INDEX idx_sharing_resources_org_status ON dev.family_sharing_resources(organization_id, status);
CREATE INDEX idx_sharing_resources_type_status ON dev.family_sharing_resources(resource_type, status);
CREATE INDEX idx_member_permissions_user_active ON dev.family_sharing_member_permissions(user_id, is_active);
CREATE INDEX idx_member_permissions_sharing_active ON dev.family_sharing_member_permissions(sharing_id, is_active);
CREATE INDEX idx_usage_stats_sharing_period ON dev.family_sharing_usage_stats(sharing_id, period_type, period_start);
CREATE INDEX idx_usage_stats_user_period ON dev.family_sharing_usage_stats(user_id, period_type, period_start);

-- Create update triggers
CREATE TRIGGER trigger_update_sharing_resources_updated_at
    BEFORE UPDATE ON dev.family_sharing_resources
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_member_permissions_updated_at
    BEFORE UPDATE ON dev.family_sharing_member_permissions
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_usage_stats_updated_at
    BEFORE UPDATE ON dev.family_sharing_usage_stats
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Grant permissions
GRANT ALL ON dev.family_sharing_resources TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.family_sharing_resources TO authenticated;
GRANT ALL ON SEQUENCE dev.family_sharing_resources_id_seq TO authenticated;

GRANT ALL ON dev.family_sharing_member_permissions TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.family_sharing_member_permissions TO authenticated;
GRANT ALL ON SEQUENCE dev.family_sharing_member_permissions_id_seq TO authenticated;

GRANT ALL ON dev.family_sharing_usage_stats TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.family_sharing_usage_stats TO authenticated;
GRANT ALL ON SEQUENCE dev.family_sharing_usage_stats_id_seq TO authenticated;

-- Add comments for documentation
COMMENT ON TABLE dev.family_sharing_resources IS 'Shared resources within family/organization';
COMMENT ON TABLE dev.family_sharing_member_permissions IS 'Member-specific permissions for shared resources';
COMMENT ON TABLE dev.family_sharing_usage_stats IS 'Usage statistics tracking for shared resources';

COMMENT ON COLUMN dev.family_sharing_resources.sharing_id IS 'Unique sharing identifier (business key)';
COMMENT ON COLUMN dev.family_sharing_resources.resource_type IS 'Type of shared resource (subscription, device, storage, etc.)';
COMMENT ON COLUMN dev.family_sharing_resources.resource_id IS 'External resource identifier';
COMMENT ON COLUMN dev.family_sharing_resources.share_with_all_members IS 'Auto-share with all organization members';
COMMENT ON COLUMN dev.family_sharing_resources.default_permission IS 'Default permission level for shared members';
COMMENT ON COLUMN dev.family_sharing_resources.quota_settings IS 'Quota configuration (limits, types, etc.)';
COMMENT ON COLUMN dev.family_sharing_resources.restrictions IS 'Access restrictions (time, location, etc.)';

COMMENT ON COLUMN dev.family_sharing_member_permissions.permission_level IS 'Member permission level for this resource';
COMMENT ON COLUMN dev.family_sharing_member_permissions.quota_allocated IS 'Quota allocated to this member';
COMMENT ON COLUMN dev.family_sharing_member_permissions.quota_used IS 'Quota consumed by this member';
COMMENT ON COLUMN dev.family_sharing_member_permissions.restrictions IS 'Member-specific restrictions';
COMMENT ON COLUMN dev.family_sharing_member_permissions.last_accessed_at IS 'Last time member accessed this resource';

COMMENT ON COLUMN dev.family_sharing_usage_stats.period_type IS 'Statistics aggregation period (daily, weekly, monthly)';
COMMENT ON COLUMN dev.family_sharing_usage_stats.usage_data IS 'Usage metrics and statistics';
COMMENT ON COLUMN dev.family_sharing_usage_stats.quota_utilization IS 'Percentage of quota used (0-100)';
