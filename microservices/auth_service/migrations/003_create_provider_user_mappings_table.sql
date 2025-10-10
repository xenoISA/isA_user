-- Auth Service Migration: Create provider_user_mappings table
-- Version: 003 
-- Date: 2025-01-20

CREATE TABLE IF NOT EXISTS dev.provider_user_mappings (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    internal_user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(provider, provider_user_id)
);

-- Indexes
CREATE INDEX idx_provider_user_mappings_provider ON dev.provider_user_mappings(provider);
CREATE INDEX idx_provider_user_mappings_provider_user_id ON dev.provider_user_mappings(provider_user_id);
CREATE INDEX idx_provider_user_mappings_email ON dev.provider_user_mappings(email);
CREATE INDEX idx_provider_user_mappings_internal_user_id ON dev.provider_user_mappings(internal_user_id);
CREATE INDEX idx_provider_user_mappings_provider_composite ON dev.provider_user_mappings(provider, provider_user_id);

-- Trigger
CREATE TRIGGER trigger_update_provider_user_mappings_updated_at
    BEFORE UPDATE ON dev.provider_user_mappings
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Permissions  
GRANT ALL ON dev.provider_user_mappings TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.provider_user_mappings TO authenticated;

-- Comments
COMMENT ON TABLE dev.provider_user_mappings IS 'Mapping between external authentication providers and internal user IDs';
COMMENT ON COLUMN dev.provider_user_mappings.provider IS 'Authentication provider name (e.g., auth0, google, etc.)';
COMMENT ON COLUMN dev.provider_user_mappings.provider_user_id IS 'User ID from the external provider';
COMMENT ON COLUMN dev.provider_user_mappings.email IS 'User email address from provider';
COMMENT ON COLUMN dev.provider_user_mappings.internal_user_id IS 'Internal user identifier';