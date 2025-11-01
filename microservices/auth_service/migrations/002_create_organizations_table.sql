-- Auth Service Migration: Create organizations table for API key management
-- Version: 004
-- Date: 2025-01-20

CREATE TABLE IF NOT EXISTS auth.organizations (
    organization_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    api_keys JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_organizations_organization_id ON auth.organizations(organization_id);
CREATE INDEX IF NOT EXISTS idx_organizations_name ON auth.organizations(name);
CREATE INDEX IF NOT EXISTS idx_organizations_api_keys ON auth.organizations USING GIN(api_keys);

-- Comments
COMMENT ON TABLE auth.organizations IS 'Organizations with API key management (JSONB storage)';
COMMENT ON COLUMN auth.organizations.organization_id IS 'Unique organization identifier';
COMMENT ON COLUMN auth.organizations.name IS 'Organization name';
COMMENT ON COLUMN auth.organizations.api_keys IS 'JSONB array of API keys with metadata';
