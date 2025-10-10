-- Organization Service Migration: Create organization and member tables
-- Version: 001
-- Date: 2025-01-20
-- Description: Core tables for organization management and member tracking

-- Drop existing tables if needed (be careful in production!)
DROP TABLE IF EXISTS dev.organization_members CASCADE;
DROP TABLE IF EXISTS dev.organizations CASCADE;

-- Create organizations table
CREATE TABLE dev.organizations (
    id SERIAL PRIMARY KEY,
    organization_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100),
    description TEXT,
    industry VARCHAR(50),
    size VARCHAR(50),
    website VARCHAR(255),
    logo_url VARCHAR(255),
    billing_email VARCHAR(255) NOT NULL,
    plan VARCHAR(20) NOT NULL DEFAULT 'free', -- free, starter, professional, enterprise
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- active, inactive, suspended, deleted
    credits_pool DECIMAL(20, 8) NOT NULL DEFAULT 0,
    settings JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT organizations_name_not_empty CHECK (length(trim(name)) > 0),
    CONSTRAINT organizations_billing_email_valid CHECK (billing_email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT organizations_plan_valid CHECK (plan IN ('free', 'starter', 'professional', 'enterprise')),
    CONSTRAINT organizations_status_valid CHECK (status IN ('active', 'inactive', 'suspended', 'deleted')),
    CONSTRAINT organizations_credits_non_negative CHECK (credits_pool >= 0)
);

-- Create organization members table
CREATE TABLE dev.organization_members (
    id SERIAL PRIMARY KEY,
    organization_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member', -- owner, admin, member, viewer, guest
    department VARCHAR(100),
    title VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- active, inactive, pending, suspended
    permissions JSONB DEFAULT '[]'::jsonb,
    is_founder BOOLEAN DEFAULT FALSE,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    last_active TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_member_organization FOREIGN KEY (organization_id) 
        REFERENCES dev.organizations(organization_id) ON DELETE CASCADE,
    CONSTRAINT fk_member_user FOREIGN KEY (user_id) 
        REFERENCES dev.users(user_id) ON DELETE CASCADE,
    CONSTRAINT members_role_valid CHECK (role IN ('owner', 'admin', 'member', 'viewer', 'guest')),
    CONSTRAINT members_status_valid CHECK (status IN ('active', 'inactive', 'pending', 'suspended')),
    UNIQUE (organization_id, user_id)
);

-- Create indexes for performance
CREATE INDEX idx_organizations_name ON dev.organizations(name);
CREATE INDEX idx_organizations_billing_email ON dev.organizations(billing_email);
CREATE INDEX idx_organizations_plan ON dev.organizations(plan);
CREATE INDEX idx_organizations_status ON dev.organizations(status) WHERE status != 'deleted';
CREATE INDEX idx_organizations_created_at ON dev.organizations(created_at DESC);

CREATE INDEX idx_members_organization_id ON dev.organization_members(organization_id);
CREATE INDEX idx_members_user_id ON dev.organization_members(user_id);
CREATE INDEX idx_members_role ON dev.organization_members(role);
CREATE INDEX idx_members_status ON dev.organization_members(status) WHERE status = 'active';
CREATE INDEX idx_members_joined_at ON dev.organization_members(joined_at DESC);
CREATE INDEX idx_members_last_active ON dev.organization_members(last_active DESC);

-- Create composite indexes for common queries
CREATE INDEX idx_organizations_plan_status ON dev.organizations(plan, status);
CREATE INDEX idx_members_org_role ON dev.organization_members(organization_id, role);
CREATE INDEX idx_members_org_status ON dev.organization_members(organization_id, status);
CREATE INDEX idx_members_user_status ON dev.organization_members(user_id, status);

-- Create update triggers
CREATE TRIGGER trigger_update_organizations_updated_at
    BEFORE UPDATE ON dev.organizations
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_members_updated_at
    BEFORE UPDATE ON dev.organization_members
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Grant permissions
GRANT ALL ON dev.organizations TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.organizations TO authenticated;
GRANT ALL ON SEQUENCE dev.organizations_id_seq TO authenticated;

GRANT ALL ON dev.organization_members TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.organization_members TO authenticated;
GRANT ALL ON SEQUENCE dev.organization_members_id_seq TO authenticated;

-- Add comments for documentation
COMMENT ON TABLE dev.organizations IS 'Organizations table for multi-tenant support';
COMMENT ON TABLE dev.organization_members IS 'Organization membership with roles and permissions';

COMMENT ON COLUMN dev.organizations.organization_id IS 'Unique organization identifier (business key)';
COMMENT ON COLUMN dev.organizations.name IS 'Organization name (required)';
COMMENT ON COLUMN dev.organizations.display_name IS 'Display name for UI';
COMMENT ON COLUMN dev.organizations.billing_email IS 'Primary billing contact email';
COMMENT ON COLUMN dev.organizations.plan IS 'Subscription plan level';
COMMENT ON COLUMN dev.organizations.status IS 'Organization status';
COMMENT ON COLUMN dev.organizations.credits_pool IS 'Shared organization credits pool';
COMMENT ON COLUMN dev.organizations.settings IS 'Organization-specific settings';

COMMENT ON COLUMN dev.organization_members.role IS 'Member role within organization';
COMMENT ON COLUMN dev.organization_members.status IS 'Member status';
COMMENT ON COLUMN dev.organization_members.permissions IS 'Custom permissions array';
COMMENT ON COLUMN dev.organization_members.is_founder IS 'True if user founded the organization';

-- Insert sample data for testing (optional)
INSERT INTO dev.organizations (
    organization_id, name, display_name, billing_email, plan, status, credits_pool
) VALUES (
    'org_sample_test', 'Sample Organization', 'Sample Org', 'billing@sample.com', 'free', 'active', 1000
) ON CONFLICT (organization_id) DO NOTHING;