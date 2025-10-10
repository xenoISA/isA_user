-- Storage Service Migration: Create storage_quotas table
-- Version: 003 
-- Date: 2025-01-20

CREATE TABLE IF NOT EXISTS dev.storage_quotas (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    organization_id VARCHAR(255),
    total_quota_bytes BIGINT NOT NULL DEFAULT 10737418240, -- 10GB default
    used_bytes BIGINT DEFAULT 0,
    file_count INTEGER DEFAULT 0,
    max_file_size BIGINT DEFAULT 104857600, -- 100MB default
    max_file_count INTEGER DEFAULT 10000,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT storage_quotas_entity_check CHECK (
        (user_id IS NOT NULL AND organization_id IS NULL) OR 
        (user_id IS NULL AND organization_id IS NOT NULL)
    ),
    UNIQUE(user_id),
    UNIQUE(organization_id)
);

-- Indexes
CREATE INDEX idx_storage_quotas_user_id ON dev.storage_quotas(user_id);
CREATE INDEX idx_storage_quotas_organization_id ON dev.storage_quotas(organization_id);
CREATE INDEX idx_storage_quotas_is_active ON dev.storage_quotas(is_active);
CREATE INDEX idx_storage_quotas_used_bytes ON dev.storage_quotas(used_bytes);
CREATE INDEX idx_storage_quotas_file_count ON dev.storage_quotas(file_count);
CREATE INDEX idx_storage_quotas_updated_at ON dev.storage_quotas(updated_at);

-- Trigger
CREATE TRIGGER trigger_update_storage_quotas_updated_at
    BEFORE UPDATE ON dev.storage_quotas
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Permissions  
GRANT ALL ON dev.storage_quotas TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.storage_quotas TO authenticated;

-- Comments
COMMENT ON TABLE dev.storage_quotas IS 'Storage quota limits and usage tracking for users and organizations';
COMMENT ON COLUMN dev.storage_quotas.user_id IS 'User ID for individual user quotas';
COMMENT ON COLUMN dev.storage_quotas.organization_id IS 'Organization ID for organization quotas';
COMMENT ON COLUMN dev.storage_quotas.total_quota_bytes IS 'Total storage quota in bytes';
COMMENT ON COLUMN dev.storage_quotas.used_bytes IS 'Currently used storage in bytes';
COMMENT ON COLUMN dev.storage_quotas.file_count IS 'Current number of files';
COMMENT ON COLUMN dev.storage_quotas.max_file_size IS 'Maximum allowed file size in bytes';
COMMENT ON COLUMN dev.storage_quotas.max_file_count IS 'Maximum allowed number of files';
COMMENT ON COLUMN dev.storage_quotas.is_active IS 'Whether quota is currently active';