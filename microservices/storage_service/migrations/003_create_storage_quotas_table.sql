-- Storage Service Migration: Create storage_quotas table
-- Version: 003 
-- Date: 2025-01-20

CREATE TABLE IF NOT EXISTS storage.storage_quotas (
    id SERIAL PRIMARY KEY,
    quota_type VARCHAR(20) NOT NULL CHECK (quota_type IN ('user', 'organization')),
    entity_id VARCHAR(255) NOT NULL, -- user_id or organization_id
    total_quota_bytes BIGINT NOT NULL DEFAULT 10737418240, -- 10GB default
    used_bytes BIGINT DEFAULT 0,
    file_count INTEGER DEFAULT 0,
    max_file_size BIGINT DEFAULT 104857600, -- 100MB default
    max_file_count INTEGER DEFAULT 10000,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint per quota type
    CONSTRAINT storage_quotas_unique_entity UNIQUE(quota_type, entity_id)
);

-- Indexes
CREATE INDEX idx_storage_quotas_quota_type ON storage.storage_quotas(quota_type);
CREATE INDEX idx_storage_quotas_entity_id ON storage.storage_quotas(entity_id);
CREATE INDEX idx_storage_quotas_type_entity ON storage.storage_quotas(quota_type, entity_id);
CREATE INDEX idx_storage_quotas_is_active ON storage.storage_quotas(is_active);
CREATE INDEX idx_storage_quotas_used_bytes ON storage.storage_quotas(used_bytes);
CREATE INDEX idx_storage_quotas_file_count ON storage.storage_quotas(file_count);
CREATE INDEX idx_storage_quotas_updated_at ON storage.storage_quotas(updated_at);

-- Trigger
CREATE TRIGGER trigger_update_storage_quotas_updated_at
    BEFORE UPDATE ON storage.storage_quotas
    FOR EACH ROW
    EXECUTE FUNCTION storage.update_updated_at();

-- Permissions  
GRANT ALL ON storage.storage_quotas TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON storage.storage_quotas TO authenticated;

-- Comments
COMMENT ON TABLE storage.storage_quotas IS 'Storage quota limits and usage tracking for users and organizations';
COMMENT ON COLUMN storage.storage_quotas.quota_type IS 'Type of quota: user or organization';
COMMENT ON COLUMN storage.storage_quotas.entity_id IS 'User ID or Organization ID (depends on quota_type)';
COMMENT ON COLUMN storage.storage_quotas.total_quota_bytes IS 'Total storage quota in bytes';
COMMENT ON COLUMN storage.storage_quotas.used_bytes IS 'Currently used storage in bytes';
COMMENT ON COLUMN storage.storage_quotas.file_count IS 'Current number of files';
COMMENT ON COLUMN storage.storage_quotas.max_file_size IS 'Maximum allowed file size in bytes';
COMMENT ON COLUMN storage.storage_quotas.max_file_count IS 'Maximum allowed number of files';
COMMENT ON COLUMN storage.storage_quotas.is_active IS 'Whether quota is currently active';