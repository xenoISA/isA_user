-- Storage Service Migration: Create file_shares table
-- Version: 002 
-- Date: 2025-01-20

CREATE TABLE IF NOT EXISTS storage.file_shares (
    id SERIAL PRIMARY KEY,
    share_id VARCHAR(255) NOT NULL UNIQUE,
    file_id VARCHAR(255) NOT NULL,
    shared_by VARCHAR(255) NOT NULL,
    shared_with VARCHAR(255),
    shared_with_email VARCHAR(255),
    access_token VARCHAR(255) NOT NULL,
    password VARCHAR(255),
    permissions TEXT[] DEFAULT '{"read"}',
    max_downloads INTEGER,
    download_count INTEGER DEFAULT 0,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    accessed_at TIMESTAMPTZ
    -- No FK - microservices independence (application-level relationship)
);

-- Indexes
CREATE INDEX idx_file_shares_share_id ON storage.file_shares(share_id);
CREATE INDEX idx_file_shares_file_id ON storage.file_shares(file_id);
CREATE INDEX idx_file_shares_shared_by ON storage.file_shares(shared_by);
CREATE INDEX idx_file_shares_shared_with ON storage.file_shares(shared_with);
CREATE INDEX idx_file_shares_shared_with_email ON storage.file_shares(shared_with_email);
CREATE INDEX idx_file_shares_access_token ON storage.file_shares(access_token);
CREATE INDEX idx_file_shares_is_active ON storage.file_shares(is_active);
CREATE INDEX idx_file_shares_expires_at ON storage.file_shares(expires_at);
CREATE INDEX idx_file_shares_created_at ON storage.file_shares(created_at);
CREATE INDEX idx_file_shares_updated_at ON storage.file_shares(updated_at);

-- Trigger
CREATE TRIGGER trigger_update_file_shares_updated_at
    BEFORE UPDATE ON storage.file_shares
    FOR EACH ROW
    EXECUTE FUNCTION storage.update_updated_at();

-- Permissions  
GRANT ALL ON storage.file_shares TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON storage.file_shares TO authenticated;

-- Comments
COMMENT ON TABLE storage.file_shares IS 'File sharing configurations and access tracking';
COMMENT ON COLUMN storage.file_shares.share_id IS 'Unique share identifier';
COMMENT ON COLUMN storage.file_shares.file_id IS 'Associated file ID';
COMMENT ON COLUMN storage.file_shares.shared_by IS 'User who created the share';
COMMENT ON COLUMN storage.file_shares.shared_with IS 'User ID shared with (if specific user)';
COMMENT ON COLUMN storage.file_shares.shared_with_email IS 'Email address shared with';
COMMENT ON COLUMN storage.file_shares.access_token IS 'Access token for share authentication';
COMMENT ON COLUMN storage.file_shares.password IS 'Optional password protection';
COMMENT ON COLUMN storage.file_shares.permissions IS 'Array of permissions (read, download, etc.)';
COMMENT ON COLUMN storage.file_shares.max_downloads IS 'Maximum number of downloads allowed';
COMMENT ON COLUMN storage.file_shares.download_count IS 'Current download count';
COMMENT ON COLUMN storage.file_shares.expires_at IS 'Share expiration timestamp';
COMMENT ON COLUMN storage.file_shares.is_active IS 'Whether share is currently active';
COMMENT ON COLUMN storage.file_shares.accessed_at IS 'Last access timestamp';