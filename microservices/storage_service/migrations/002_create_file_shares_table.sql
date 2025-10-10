-- Storage Service Migration: Create file_shares table
-- Version: 002 
-- Date: 2025-01-20

CREATE TABLE IF NOT EXISTS dev.file_shares (
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
    accessed_at TIMESTAMPTZ,
    FOREIGN KEY (file_id) REFERENCES dev.storage_files(file_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_file_shares_share_id ON dev.file_shares(share_id);
CREATE INDEX idx_file_shares_file_id ON dev.file_shares(file_id);
CREATE INDEX idx_file_shares_shared_by ON dev.file_shares(shared_by);
CREATE INDEX idx_file_shares_shared_with ON dev.file_shares(shared_with);
CREATE INDEX idx_file_shares_shared_with_email ON dev.file_shares(shared_with_email);
CREATE INDEX idx_file_shares_access_token ON dev.file_shares(access_token);
CREATE INDEX idx_file_shares_is_active ON dev.file_shares(is_active);
CREATE INDEX idx_file_shares_expires_at ON dev.file_shares(expires_at);
CREATE INDEX idx_file_shares_created_at ON dev.file_shares(created_at);

-- Permissions  
GRANT ALL ON dev.file_shares TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.file_shares TO authenticated;

-- Comments
COMMENT ON TABLE dev.file_shares IS 'File sharing configurations and access tracking';
COMMENT ON COLUMN dev.file_shares.share_id IS 'Unique share identifier';
COMMENT ON COLUMN dev.file_shares.file_id IS 'Associated file ID';
COMMENT ON COLUMN dev.file_shares.shared_by IS 'User who created the share';
COMMENT ON COLUMN dev.file_shares.shared_with IS 'User ID shared with (if specific user)';
COMMENT ON COLUMN dev.file_shares.shared_with_email IS 'Email address shared with';
COMMENT ON COLUMN dev.file_shares.access_token IS 'Access token for share authentication';
COMMENT ON COLUMN dev.file_shares.password IS 'Optional password protection';
COMMENT ON COLUMN dev.file_shares.permissions IS 'Array of permissions (read, download, etc.)';
COMMENT ON COLUMN dev.file_shares.max_downloads IS 'Maximum number of downloads allowed';
COMMENT ON COLUMN dev.file_shares.download_count IS 'Current download count';
COMMENT ON COLUMN dev.file_shares.expires_at IS 'Share expiration timestamp';
COMMENT ON COLUMN dev.file_shares.is_active IS 'Whether share is currently active';
COMMENT ON COLUMN dev.file_shares.accessed_at IS 'Last access timestamp';