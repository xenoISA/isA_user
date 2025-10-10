-- Storage Service Migration: Create storage_files table
-- Version: 001 
-- Date: 2025-01-20

CREATE TABLE IF NOT EXISTS dev.storage_files (
    id SERIAL PRIMARY KEY,
    file_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    file_name VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000),
    file_size BIGINT NOT NULL,
    content_type VARCHAR(255),
    file_extension VARCHAR(50),
    storage_provider VARCHAR(50) NOT NULL,
    bucket_name VARCHAR(255),
    object_name VARCHAR(500),
    status VARCHAR(50) DEFAULT 'active',
    access_level VARCHAR(50) DEFAULT 'private',
    checksum VARCHAR(255),
    etag VARCHAR(255),
    version_id VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    tags TEXT[],
    download_url TEXT,
    download_url_expires_at TIMESTAMPTZ,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_storage_files_file_id ON dev.storage_files(file_id);
CREATE INDEX idx_storage_files_user_id ON dev.storage_files(user_id);
CREATE INDEX idx_storage_files_organization_id ON dev.storage_files(organization_id);
CREATE INDEX idx_storage_files_file_name ON dev.storage_files(file_name);
CREATE INDEX idx_storage_files_status ON dev.storage_files(status);
CREATE INDEX idx_storage_files_access_level ON dev.storage_files(access_level);
CREATE INDEX idx_storage_files_storage_provider ON dev.storage_files(storage_provider);
CREATE INDEX idx_storage_files_content_type ON dev.storage_files(content_type);
CREATE INDEX idx_storage_files_file_extension ON dev.storage_files(file_extension);
CREATE INDEX idx_storage_files_uploaded_at ON dev.storage_files(uploaded_at);
CREATE INDEX idx_storage_files_updated_at ON dev.storage_files(updated_at);
CREATE INDEX idx_storage_files_deleted_at ON dev.storage_files(deleted_at);
CREATE INDEX idx_storage_files_metadata ON dev.storage_files USING GIN(metadata);
CREATE INDEX idx_storage_files_tags ON dev.storage_files USING GIN(tags);

-- Composite indexes for common queries
CREATE INDEX idx_storage_files_user_active ON dev.storage_files(user_id, status, uploaded_at DESC) WHERE status != 'deleted';
CREATE INDEX idx_storage_files_org_active ON dev.storage_files(organization_id, status, uploaded_at DESC) WHERE status != 'deleted';

-- Trigger
CREATE TRIGGER trigger_update_storage_files_updated_at
    BEFORE UPDATE ON dev.storage_files
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Permissions  
GRANT ALL ON dev.storage_files TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.storage_files TO authenticated;

-- Comments
COMMENT ON TABLE dev.storage_files IS 'File storage metadata and tracking';
COMMENT ON COLUMN dev.storage_files.file_id IS 'Unique file identifier';
COMMENT ON COLUMN dev.storage_files.user_id IS 'Owner user ID';
COMMENT ON COLUMN dev.storage_files.organization_id IS 'Organization ID if applicable';
COMMENT ON COLUMN dev.storage_files.file_name IS 'Original file name';
COMMENT ON COLUMN dev.storage_files.file_path IS 'File path within storage';
COMMENT ON COLUMN dev.storage_files.file_size IS 'File size in bytes';
COMMENT ON COLUMN dev.storage_files.content_type IS 'MIME content type';
COMMENT ON COLUMN dev.storage_files.file_extension IS 'File extension';
COMMENT ON COLUMN dev.storage_files.storage_provider IS 'Storage provider (supabase, aws, gcp, etc.)';
COMMENT ON COLUMN dev.storage_files.bucket_name IS 'Storage bucket name';
COMMENT ON COLUMN dev.storage_files.object_name IS 'Object name in storage';
COMMENT ON COLUMN dev.storage_files.status IS 'File status (active, processing, deleted, etc.)';
COMMENT ON COLUMN dev.storage_files.access_level IS 'Access level (private, public, shared)';
COMMENT ON COLUMN dev.storage_files.checksum IS 'File checksum for integrity';
COMMENT ON COLUMN dev.storage_files.etag IS 'Storage provider ETag';
COMMENT ON COLUMN dev.storage_files.version_id IS 'Version ID for versioned storage';
COMMENT ON COLUMN dev.storage_files.metadata IS 'Additional file metadata stored as JSONB';
COMMENT ON COLUMN dev.storage_files.tags IS 'Array of tags for categorization';
COMMENT ON COLUMN dev.storage_files.download_url IS 'Pre-signed download URL';
COMMENT ON COLUMN dev.storage_files.download_url_expires_at IS 'Download URL expiration timestamp';
COMMENT ON COLUMN dev.storage_files.uploaded_at IS 'When file was uploaded';
COMMENT ON COLUMN dev.storage_files.deleted_at IS 'When file was deleted (soft delete)';