-- Authorization Service Migration: Create organization_members table
-- Version: 002 
-- Date: 2025-01-20

CREATE TABLE IF NOT EXISTS dev.organization_members (
    id SERIAL PRIMARY KEY,
    organization_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'member',
    status VARCHAR(50) DEFAULT 'active',
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, user_id)
);

-- Indexes
CREATE INDEX idx_organization_members_organization_id ON dev.organization_members(organization_id);
CREATE INDEX idx_organization_members_user_id ON dev.organization_members(user_id);
CREATE INDEX idx_organization_members_status ON dev.organization_members(status);
CREATE INDEX idx_organization_members_role ON dev.organization_members(role);
CREATE INDEX idx_organization_members_joined_at ON dev.organization_members(joined_at);

-- Trigger
CREATE TRIGGER trigger_update_organization_members_updated_at
    BEFORE UPDATE ON dev.organization_members
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Permissions  
GRANT ALL ON dev.organization_members TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.organization_members TO authenticated;

-- Comments
COMMENT ON TABLE dev.organization_members IS 'Organization membership relationships';
COMMENT ON COLUMN dev.organization_members.organization_id IS 'Organization identifier';
COMMENT ON COLUMN dev.organization_members.user_id IS 'User identifier';
COMMENT ON COLUMN dev.organization_members.role IS 'Member role (member, admin, owner)';
COMMENT ON COLUMN dev.organization_members.status IS 'Membership status (active, pending, suspended)';
COMMENT ON COLUMN dev.organization_members.joined_at IS 'When user joined the organization';