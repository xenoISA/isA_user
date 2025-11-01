-- Album Service Migration: Create album tables
-- Version: 001
-- Date: 2025-01-24
--
-- IMPORTANT: Microservices Best Practices
-- - No Foreign Keys: user_id, organization_id, photo_id have NO FK constraints
-- - Application-level validation:
--   * Validate user/org via account_service/auth_service APIs
--   * Validate photo_id via storage_service API before adding to album
-- - Cross-service relationships managed in application layer

-- Create album schema
CREATE SCHEMA IF NOT EXISTS album;

-- Create helper function
CREATE OR REPLACE FUNCTION album.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ====================
-- Albums Table
-- ====================
CREATE TABLE IF NOT EXISTS album.albums (
    id SERIAL PRIMARY KEY,
    album_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),

    -- Media properties
    cover_photo_id VARCHAR(255),
    photo_count INTEGER DEFAULT 0,

    -- Smart frame features
    auto_sync BOOLEAN DEFAULT true,
    sync_frames JSONB DEFAULT '[]'::jsonb,

    -- Family sharing (no FK - managed by organization_service)
    is_family_shared BOOLEAN DEFAULT FALSE,
    sharing_resource_id VARCHAR(255),

    -- Metadata
    tags JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_synced_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_albums_album_id ON album.albums(album_id);
CREATE INDEX idx_albums_user_id ON album.albums(user_id);
CREATE INDEX idx_albums_organization_id ON album.albums(organization_id);
CREATE INDEX idx_albums_sharing_resource_id ON album.albums(sharing_resource_id);
CREATE INDEX idx_albums_updated_at ON album.albums(updated_at DESC);
CREATE INDEX idx_albums_family_shared ON album.albums(is_family_shared) WHERE is_family_shared = true;

-- Trigger
CREATE TRIGGER trigger_update_albums_updated_at
    BEFORE UPDATE ON album.albums
    FOR EACH ROW
    EXECUTE FUNCTION album.update_updated_at();

-- ====================
-- Album Photos Junction Table
-- ====================
CREATE TABLE IF NOT EXISTS album.album_photos (
    id SERIAL PRIMARY KEY,
    album_id VARCHAR(255) NOT NULL,
    photo_id VARCHAR(255) NOT NULL, -- References storage.storage_files.file_id (no FK)

    -- Management
    added_by VARCHAR(255) NOT NULL,
    added_at TIMESTAMPTZ DEFAULT NOW(),

    -- Display properties
    is_featured BOOLEAN DEFAULT false,
    display_order INTEGER DEFAULT 0,

    -- AI features
    ai_tags JSONB DEFAULT '[]'::jsonb,
    ai_objects JSONB DEFAULT '[]'::jsonb,
    ai_scenes JSONB DEFAULT '[]'::jsonb,
    face_detection_results JSONB,

    -- Constraints
    CONSTRAINT album_photos_unique_pair UNIQUE (album_id, photo_id)
    -- No FK - microservices independence
);

-- Indexes
CREATE INDEX idx_album_photos_album_id ON album.album_photos(album_id);
CREATE INDEX idx_album_photos_photo_id ON album.album_photos(photo_id);
CREATE INDEX idx_album_photos_added_by ON album.album_photos(added_by);
CREATE INDEX idx_album_photos_featured ON album.album_photos(is_featured) WHERE is_featured = true;
CREATE INDEX idx_album_photos_display_order ON album.album_photos(album_id, display_order);

-- ====================
-- Album Sync Status Table (for smart frame synchronization)
-- ====================
CREATE TABLE IF NOT EXISTS album.album_sync_status (
    id SERIAL PRIMARY KEY,
    album_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL, -- Owner for permission validation (no FK)
    frame_id VARCHAR(255) NOT NULL, -- Smart frame device ID (no FK)

    -- Sync timing
    last_sync_timestamp TIMESTAMPTZ,
    sync_version INTEGER DEFAULT 0,

    -- Sync statistics
    total_photos INTEGER DEFAULT 0,
    synced_photos INTEGER DEFAULT 0,
    pending_photos INTEGER DEFAULT 0,
    failed_photos INTEGER DEFAULT 0,

    -- Status
    sync_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT album_sync_unique_pair UNIQUE (album_id, frame_id)
    -- No FK - microservices independence (validate user_id in application layer)
);

-- Indexes
CREATE INDEX idx_album_sync_album_id ON album.album_sync_status(album_id);
CREATE INDEX idx_album_sync_user_id ON album.album_sync_status(user_id);
CREATE INDEX idx_album_sync_frame_id ON album.album_sync_status(frame_id);
CREATE INDEX idx_album_sync_status ON album.album_sync_status(sync_status);
CREATE INDEX idx_album_sync_updated_at ON album.album_sync_status(updated_at DESC);

-- Trigger
CREATE TRIGGER trigger_update_album_sync_updated_at
    BEFORE UPDATE ON album.album_sync_status
    FOR EACH ROW
    EXECUTE FUNCTION album.update_updated_at();

-- Comments
COMMENT ON SCHEMA album IS 'Album service schema for photo album management';
COMMENT ON TABLE album.albums IS 'Photo albums with smart frame support';
COMMENT ON TABLE album.album_photos IS 'Photos in albums junction table';
COMMENT ON TABLE album.album_sync_status IS 'Smart frame synchronization status';
