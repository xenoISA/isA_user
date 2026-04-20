-- Sharing Service Migration: Create shares table
-- Version: 001
-- Date: 2026-04-20

-- Create sharing schema if not exists
CREATE SCHEMA IF NOT EXISTS sharing;

-- Create shares table
CREATE TABLE IF NOT EXISTS sharing.shares (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    owner_id VARCHAR(255) NOT NULL,
    share_token VARCHAR(255) NOT NULL UNIQUE,
    permissions VARCHAR(50) DEFAULT 'view_only',
    expires_at TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_shares_session_id ON sharing.shares(session_id);
CREATE INDEX IF NOT EXISTS idx_shares_owner_id ON sharing.shares(owner_id);
CREATE INDEX IF NOT EXISTS idx_shares_token ON sharing.shares(share_token);
CREATE INDEX IF NOT EXISTS idx_shares_session_owner ON sharing.shares(session_id, owner_id);
CREATE INDEX IF NOT EXISTS idx_shares_expires_at ON sharing.shares(expires_at) WHERE expires_at IS NOT NULL;

-- Comments
COMMENT ON TABLE sharing.shares IS 'Share links for session collaboration';
COMMENT ON COLUMN sharing.shares.id IS 'Share record UUID';
COMMENT ON COLUMN sharing.shares.session_id IS 'Session being shared';
COMMENT ON COLUMN sharing.shares.owner_id IS 'User who created the share';
COMMENT ON COLUMN sharing.shares.share_token IS 'URL-safe token for access (128 bits entropy)';
COMMENT ON COLUMN sharing.shares.permissions IS 'Permission level: view_only, can_comment, can_edit';
COMMENT ON COLUMN sharing.shares.expires_at IS 'Expiry timestamp (null = never expires)';
COMMENT ON COLUMN sharing.shares.access_count IS 'Number of times this share has been accessed';
