-- Device Service Migration: Create smart frame configs table
-- Version: 004
-- Date: 2025-10-25

-- Create frame_configs table for smart frame devices
CREATE TABLE IF NOT EXISTS device.frame_configs (
    device_id VARCHAR(255) PRIMARY KEY,

    -- Display settings
    brightness INTEGER DEFAULT 80 CHECK (brightness BETWEEN 0 AND 100),
    contrast INTEGER DEFAULT 100 CHECK (contrast BETWEEN 0 AND 200),
    auto_brightness BOOLEAN DEFAULT true,
    orientation VARCHAR(20) DEFAULT 'auto',

    -- Slideshow settings
    slideshow_interval INTEGER DEFAULT 30 CHECK (slideshow_interval BETWEEN 5 AND 3600),
    slideshow_transition VARCHAR(50) DEFAULT 'fade',
    shuffle_photos BOOLEAN DEFAULT true,
    show_metadata BOOLEAN DEFAULT false,

    -- Power management
    sleep_schedule JSONB DEFAULT '{"start": "23:00", "end": "07:00"}',
    auto_sleep BOOLEAN DEFAULT true,
    motion_detection BOOLEAN DEFAULT true,

    -- Sync settings
    auto_sync_albums TEXT[] DEFAULT '{}',
    sync_frequency VARCHAR(20) DEFAULT 'hourly',
    wifi_only_sync BOOLEAN DEFAULT true,

    -- Display mode
    display_mode VARCHAR(50) DEFAULT 'photo_slideshow',

    -- Location and environment
    location JSONB,
    timezone VARCHAR(50) DEFAULT 'UTC',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_frame_configs_mode ON device.frame_configs(display_mode);

-- Comments
COMMENT ON TABLE device.frame_configs IS 'Smart frame device configurations';
COMMENT ON COLUMN device.frame_configs.orientation IS 'Display orientation: landscape, portrait, auto';
COMMENT ON COLUMN device.frame_configs.display_mode IS 'Display mode: photo_slideshow, video_playback, clock_display, etc.';
