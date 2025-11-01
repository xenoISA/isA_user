-- Organization Service Migration: Create organization and member tables
-- Version: 001 (Fixed for PostgreSQL + gRPC)
-- Date: 2025-10-27
-- Description: Core tables for organization management and member tracking
--              ✅ Uses organization schema (not dev)
--              ✅ DOUBLE PRECISION instead of DECIMAL
--              ✅ Removed cross-service foreign keys
--              ✅ Added api_keys and domain fields

-- Create organization schema if not exists
CREATE SCHEMA IF NOT EXISTS organization;

-- Create helper function for automatic timestamp updates
CREATE OR REPLACE FUNCTION organization.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing tables if needed (be careful in production!)
DROP TABLE IF EXISTS organization.organization_members CASCADE;
DROP TABLE IF EXISTS organization.organizations CASCADE;

-- Create organizations table
CREATE TABLE organization.organizations (
    id SERIAL PRIMARY KEY,
    organization_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100),
    description TEXT,
    domain VARCHAR(255),
    industry VARCHAR(50),
    size VARCHAR(50),
    website VARCHAR(255),
    logo_url VARCHAR(255),
    billing_email VARCHAR(255) NOT NULL,
    plan VARCHAR(20) NOT NULL DEFAULT 'free', -- free, starter, professional, enterprise
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- active, inactive, suspended, deleted
    credits_pool DOUBLE PRECISION NOT NULL DEFAULT 0, -- ✅ Changed from DECIMAL to DOUBLE PRECISION
    settings JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    api_keys JSONB DEFAULT '[]'::jsonb, -- ✅ Added api_keys field
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT organizations_name_not_empty CHECK (length(trim(name)) > 0),
    CONSTRAINT organizations_billing_email_valid CHECK (billing_email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT organizations_plan_valid CHECK (plan IN ('free', 'starter', 'professional', 'enterprise')),
    CONSTRAINT organizations_status_valid CHECK (status IN ('active', 'inactive', 'suspended', 'deleted')),
    CONSTRAINT organizations_credits_non_negative CHECK (credits_pool >= 0)
);

-- Create organization members table
CREATE TABLE organization.organization_members (
    id SERIAL PRIMARY KEY,
    organization_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL, -- ✅ No foreign key to users table (validated at application level)
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
        REFERENCES organization.organizations(organization_id) ON DELETE CASCADE,
    -- ✅ Removed fk_member_user foreign key for microservice independence
    CONSTRAINT members_role_valid CHECK (role IN ('owner', 'admin', 'member', 'viewer', 'guest')),
    CONSTRAINT members_status_valid CHECK (status IN ('active', 'inactive', 'pending', 'suspended')),
    UNIQUE (organization_id, user_id)
);

-- Create indexes for performance
CREATE INDEX idx_organizations_name ON organization.organizations(name);
CREATE INDEX idx_organizations_billing_email ON organization.organizations(billing_email);
CREATE INDEX idx_organizations_plan ON organization.organizations(plan);
CREATE INDEX idx_organizations_status ON organization.organizations(status) WHERE status != 'deleted';
CREATE INDEX idx_organizations_created_at ON organization.organizations(created_at DESC);

CREATE INDEX idx_members_organization_id ON organization.organization_members(organization_id);
CREATE INDEX idx_members_user_id ON organization.organization_members(user_id);
CREATE INDEX idx_members_role ON organization.organization_members(role);
CREATE INDEX idx_members_status ON organization.organization_members(status) WHERE status = 'active';
CREATE INDEX idx_members_joined_at ON organization.organization_members(joined_at DESC);
CREATE INDEX idx_members_last_active ON organization.organization_members(last_active DESC);

-- Create composite indexes for common queries
CREATE INDEX idx_organizations_plan_status ON organization.organizations(plan, status);
CREATE INDEX idx_members_org_role ON organization.organization_members(organization_id, role);
CREATE INDEX idx_members_org_status ON organization.organization_members(organization_id, status);
CREATE INDEX idx_members_user_status ON organization.organization_members(user_id, status);

-- Create update triggers
CREATE TRIGGER trigger_update_organizations_updated_at
    BEFORE UPDATE ON organization.organizations
    FOR EACH ROW
    EXECUTE FUNCTION organization.update_updated_at();

CREATE TRIGGER trigger_update_members_updated_at
    BEFORE UPDATE ON organization.organization_members
    FOR EACH ROW
    EXECUTE FUNCTION organization.update_updated_at();

-- Grant permissions
GRANT USAGE ON SCHEMA organization TO postgres;
GRANT USAGE ON SCHEMA organization TO authenticated;

GRANT ALL ON organization.organizations TO postgres;
GRANT SELECT, INSERT, UPDATE ON organization.organizations TO authenticated;
GRANT ALL ON SEQUENCE organization.organizations_id_seq TO authenticated;

GRANT ALL ON organization.organization_members TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON organization.organization_members TO authenticated;
GRANT ALL ON SEQUENCE organization.organization_members_id_seq TO authenticated;

-- Add comments for documentation
COMMENT ON TABLE organization.organizations IS 'Organizations table for multi-tenant support';
COMMENT ON TABLE organization.organization_members IS 'Organization membership with roles and permissions';

COMMENT ON COLUMN organization.organizations.organization_id IS 'Unique organization identifier (business key)';
COMMENT ON COLUMN organization.organizations.name IS 'Organization name (required)';
COMMENT ON COLUMN organization.organizations.display_name IS 'Display name for UI';
COMMENT ON COLUMN organization.organizations.billing_email IS 'Primary billing contact email';
COMMENT ON COLUMN organization.organizations.plan IS 'Subscription plan level';
COMMENT ON COLUMN organization.organizations.status IS 'Organization status';
COMMENT ON COLUMN organization.organizations.credits_pool IS 'Shared organization credits pool';
COMMENT ON COLUMN organization.organizations.settings IS 'Organization-specific settings';
COMMENT ON COLUMN organization.organizations.api_keys IS 'Organization API keys array';

COMMENT ON COLUMN organization.organization_members.role IS 'Member role within organization';
COMMENT ON COLUMN organization.organization_members.status IS 'Member status';
COMMENT ON COLUMN organization.organization_members.permissions IS 'Custom permissions array';
COMMENT ON COLUMN organization.organization_members.is_founder IS 'True if user founded the organization';
COMMENT ON COLUMN organization.organization_members.user_id IS 'User ID (validated at application level via account service, no FK constraint for microservice independence)';
