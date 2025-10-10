-- Auth Service Migration: Create organizations table for API key management
-- Version: 004 
-- Date: 2025-01-20

CREATE TABLE IF NOT EXISTS dev.organizations (
    id SERIAL PRIMARY KEY,
    organization_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    api_keys JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_organizations_organization_id ON dev.organizations(organization_id);
CREATE INDEX idx_organizations_name ON dev.organizations(name);
CREATE INDEX idx_organizations_api_keys ON dev.organizations USING GIN(api_keys);

-- Trigger
CREATE TRIGGER trigger_update_organizations_updated_at
    BEFORE UPDATE ON dev.organizations
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Permissions  
GRANT ALL ON dev.organizations TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.organizations TO authenticated;

-- Comments
COMMENT ON TABLE dev.organizations IS 'Organizations with API key management';
COMMENT ON COLUMN dev.organizations.organization_id IS 'Unique organization identifier';
COMMENT ON COLUMN dev.organizations.name IS 'Organization name';
COMMENT ON COLUMN dev.organizations.api_keys IS 'JSONB array of API keys with metadata';