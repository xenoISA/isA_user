-- Media Service Migration: Create media processing tables
-- Version: 001
-- Date: 2025-01-24
--
-- IMPORTANT: Microservices Best Practices
-- - No Foreign Keys: user_id, organization_id, photo_id, file_id, version_id have NO FK constraints
-- - Application-level validation:
--   * Validate user/org via account_service/auth_service APIs
--   * Validate photo_id/file_id via storage_service API
--   * Validate version_id internally before referencing
-- - Cross-service relationships managed in application layer

-- Create media schema
CREATE SCHEMA IF NOT EXISTS media;

-- Create helper function
CREATE OR REPLACE FUNCTION media.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ====================
-- Photo Versions Table (AI-processed versions)
-- ====================
CREATE TABLE IF NOT EXISTS media.photo_versions (
    id SERIAL PRIMARY KEY,
    version_id VARCHAR(255) UNIQUE NOT NULL,
    photo_id VARCHAR(255) NOT NULL, -- References storage.storage_files.file_id (no FK)
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255), -- For organization-owned photos (no FK)

    -- Version details
    version_name VARCHAR(255) NOT NULL,
    version_type VARCHAR(50) NOT NULL, -- original, ai_enhanced, ai_styled, ai_background_removed, user_edited
    processing_mode VARCHAR(100), -- enhance_quality, artistic_style, background_remove, etc.

    -- Storage information (references storage service)
    file_id VARCHAR(255) NOT NULL, -- References storage.storage_files.file_id (no FK)
    cloud_url TEXT, -- Presigned URL to access the version
    local_path TEXT, -- Local path on smart frame device
    file_size BIGINT,

    -- Processing metadata
    processing_params JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Version control
    is_current BOOLEAN DEFAULT false,
    version_number INTEGER DEFAULT 1,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_photo_versions_version_id ON media.photo_versions(version_id);
CREATE INDEX idx_photo_versions_photo_id ON media.photo_versions(photo_id);
CREATE INDEX idx_photo_versions_user_id ON media.photo_versions(user_id);
CREATE INDEX idx_photo_versions_organization_id ON media.photo_versions(organization_id);
CREATE INDEX idx_photo_versions_file_id ON media.photo_versions(file_id);
CREATE INDEX idx_photo_versions_type ON media.photo_versions(version_type);
CREATE INDEX idx_photo_versions_is_current ON media.photo_versions(photo_id, is_current) WHERE is_current = true;
CREATE INDEX idx_photo_versions_created_at ON media.photo_versions(created_at DESC);

-- Trigger
CREATE TRIGGER trigger_update_photo_versions_updated_at
    BEFORE UPDATE ON media.photo_versions
    FOR EACH ROW
    EXECUTE FUNCTION media.update_updated_at();

-- ====================
-- Photo Metadata Table (EXIF, AI analysis)
-- ====================
CREATE TABLE IF NOT EXISTS media.photo_metadata (
    id SERIAL PRIMARY KEY,
    file_id VARCHAR(255) UNIQUE NOT NULL, -- References storage.storage_files.file_id (no FK)
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255), -- For organization-owned photos (no FK)

    -- EXIF data
    camera_make VARCHAR(100),
    camera_model VARCHAR(100),
    lens_model VARCHAR(100),
    focal_length VARCHAR(50),
    aperture VARCHAR(50),
    shutter_speed VARCHAR(50),
    iso INTEGER,
    flash_used BOOLEAN,

    -- Location
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    location_name VARCHAR(255),

    -- Timestamps from photo
    photo_taken_at TIMESTAMPTZ,

    -- AI analysis results
    ai_labels JSONB DEFAULT '[]'::jsonb,
    ai_objects JSONB DEFAULT '[]'::jsonb,
    ai_scenes JSONB DEFAULT '[]'::jsonb,
    ai_colors JSONB DEFAULT '[]'::jsonb,
    face_detection JSONB DEFAULT '[]'::jsonb,
    text_detection JSONB DEFAULT '[]'::jsonb,

    -- Image quality metrics
    quality_score DECIMAL(3, 2),
    blur_score DECIMAL(3, 2),
    brightness DECIMAL(3, 2),
    contrast DECIMAL(3, 2),

    -- Full metadata
    full_metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_photo_metadata_file_id ON media.photo_metadata(file_id);
CREATE INDEX idx_photo_metadata_user_id ON media.photo_metadata(user_id);
CREATE INDEX idx_photo_metadata_organization_id ON media.photo_metadata(organization_id);
CREATE INDEX idx_photo_metadata_photo_taken_at ON media.photo_metadata(photo_taken_at DESC);
CREATE INDEX idx_photo_metadata_ai_labels ON media.photo_metadata USING GIN(ai_labels);
CREATE INDEX idx_photo_metadata_location ON media.photo_metadata(latitude, longitude) WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- Trigger
CREATE TRIGGER trigger_update_photo_metadata_updated_at
    BEFORE UPDATE ON media.photo_metadata
    FOR EACH ROW
    EXECUTE FUNCTION media.update_updated_at();

-- ====================
-- Slideshow Playlists Table
-- ====================
CREATE TABLE IF NOT EXISTS media.playlists (
    id SERIAL PRIMARY KEY,
    playlist_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255), -- For organization-shared playlists (no FK)

    -- Playlist type
    playlist_type VARCHAR(50) DEFAULT 'manual', -- manual, smart, ai_curated

    -- Smart playlist criteria
    smart_criteria JSONB DEFAULT '{}'::jsonb,

    -- Photo list (for manual playlists)
    photo_ids JSONB DEFAULT '[]'::jsonb,

    -- Playback settings
    shuffle BOOLEAN DEFAULT false,
    loop BOOLEAN DEFAULT true,
    transition_duration INTEGER DEFAULT 5, -- seconds

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_playlists_playlist_id ON media.playlists(playlist_id);
CREATE INDEX idx_playlists_user_id ON media.playlists(user_id);
CREATE INDEX idx_playlists_organization_id ON media.playlists(organization_id);
CREATE INDEX idx_playlists_type ON media.playlists(playlist_type);

-- Trigger
CREATE TRIGGER trigger_update_playlists_updated_at
    BEFORE UPDATE ON media.playlists
    FOR EACH ROW
    EXECUTE FUNCTION media.update_updated_at();

-- ====================
-- Photo Rotation Schedules Table
-- ====================
CREATE TABLE IF NOT EXISTS media.rotation_schedules (
    id SERIAL PRIMARY KEY,
    schedule_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL, -- Owner for permission validation (no FK)
    frame_id VARCHAR(255) NOT NULL, -- Smart frame device ID (no FK)
    playlist_id VARCHAR(255), -- References media.playlists.playlist_id (no FK)

    -- Schedule timing
    schedule_type VARCHAR(50) DEFAULT 'continuous', -- continuous, time_based, event_based
    start_time TIME,
    end_time TIME,
    days_of_week INTEGER[], -- 0-6 (Sunday-Saturday)

    -- Rotation settings
    rotation_interval INTEGER DEFAULT 10, -- seconds
    shuffle BOOLEAN DEFAULT false,

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_rotation_schedules_schedule_id ON media.rotation_schedules(schedule_id);
CREATE INDEX idx_rotation_schedules_user_id ON media.rotation_schedules(user_id);
CREATE INDEX idx_rotation_schedules_frame_id ON media.rotation_schedules(frame_id);
CREATE INDEX idx_rotation_schedules_playlist_id ON media.rotation_schedules(playlist_id);
CREATE INDEX idx_rotation_schedules_is_active ON media.rotation_schedules(is_active) WHERE is_active = true;

-- Trigger
CREATE TRIGGER trigger_update_rotation_schedules_updated_at
    BEFORE UPDATE ON media.rotation_schedules
    FOR EACH ROW
    EXECUTE FUNCTION media.update_updated_at();

-- ====================
-- Photo Cache Table (for smart frames)
-- ====================
CREATE TABLE IF NOT EXISTS media.photo_cache (
    id SERIAL PRIMARY KEY,
    cache_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL, -- Owner for permission validation (no FK)
    frame_id VARCHAR(255) NOT NULL, -- Smart frame device ID (no FK)
    photo_id VARCHAR(255) NOT NULL, -- References storage.storage_files.file_id (no FK)
    version_id VARCHAR(255), -- References media.photo_versions.version_id (no FK)

    -- Cache status
    cache_status VARCHAR(50) DEFAULT 'pending', -- pending, downloading, cached, failed
    cached_url TEXT,
    local_path TEXT,

    -- Cache metadata
    cache_size BIGINT,
    cache_format VARCHAR(50),
    cache_quality VARCHAR(50),

    -- Usage tracking
    hit_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,

    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_photo_cache_cache_id ON media.photo_cache(cache_id);
CREATE INDEX idx_photo_cache_user_id ON media.photo_cache(user_id);
CREATE INDEX idx_photo_cache_frame_id ON media.photo_cache(frame_id);
CREATE INDEX idx_photo_cache_photo_id ON media.photo_cache(photo_id);
CREATE INDEX idx_photo_cache_status ON media.photo_cache(cache_status);
CREATE INDEX idx_photo_cache_expires_at ON media.photo_cache(expires_at) WHERE expires_at IS NOT NULL;

-- Trigger
CREATE TRIGGER trigger_update_photo_cache_updated_at
    BEFORE UPDATE ON media.photo_cache
    FOR EACH ROW
    EXECUTE FUNCTION media.update_updated_at();

-- Comments
COMMENT ON SCHEMA media IS 'Media service schema for photo/video processing and management';
COMMENT ON TABLE media.photo_versions IS 'AI-processed photo versions (enhanced, styled, etc.)';
COMMENT ON TABLE media.photo_metadata IS 'Photo EXIF data and AI analysis results';
COMMENT ON TABLE media.playlists IS 'Photo slideshow playlists';
COMMENT ON TABLE media.rotation_schedules IS 'Smart frame photo rotation schedules';
COMMENT ON TABLE media.photo_cache IS 'Smart frame photo cache management';
