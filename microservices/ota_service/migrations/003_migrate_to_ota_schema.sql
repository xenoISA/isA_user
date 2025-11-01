-- OTA Service Migration: Migrate to dedicated ota schema
-- Version: 003
-- Date: 2025-10-27
-- Description: Move tables from dev schema to ota schema and fix DECIMAL types

-- Create ota schema
CREATE SCHEMA IF NOT EXISTS ota;

-- Drop existing tables in ota schema if they exist
DROP TABLE IF EXISTS ota.firmware_downloads CASCADE;
DROP TABLE IF EXISTS ota.rollback_logs CASCADE;
DROP TABLE IF EXISTS ota.update_history CASCADE;
DROP TABLE IF EXISTS ota.device_updates CASCADE;
DROP TABLE IF EXISTS ota.update_campaigns CASCADE;
DROP TABLE IF EXISTS ota.firmware CASCADE;

-- 1. Create firmware table
CREATE TABLE ota.firmware (
    id SERIAL PRIMARY KEY,
    firmware_id VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    version VARCHAR(50) NOT NULL,
    description VARCHAR(1000),
    device_model VARCHAR(100) NOT NULL,
    manufacturer VARCHAR(100) NOT NULL,
    min_hardware_version VARCHAR(50),
    max_hardware_version VARCHAR(50),
    file_size BIGINT NOT NULL,
    file_url TEXT NOT NULL,
    checksum_md5 VARCHAR(32) NOT NULL,
    checksum_sha256 VARCHAR(64) NOT NULL,
    tags TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    is_beta BOOLEAN DEFAULT FALSE,
    is_security_update BOOLEAN DEFAULT FALSE,
    changelog TEXT,
    download_count INTEGER DEFAULT 0,
    success_rate DOUBLE PRECISION DEFAULT 0.0,  -- Changed from DECIMAL(5,2)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL,

    CONSTRAINT unique_firmware_version UNIQUE(device_model, version)
);

-- 2. Create update_campaigns table
CREATE TABLE ota.update_campaigns (
    id SERIAL PRIMARY KEY,
    campaign_id VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    description VARCHAR(1000),
    firmware_id VARCHAR(64) NOT NULL,  -- No FK constraint
    status VARCHAR(20) NOT NULL DEFAULT 'created',
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    target_devices TEXT[],
    target_criteria JSONB DEFAULT '{}'::jsonb,
    rollout_percentage INTEGER DEFAULT 100,
    auto_rollback BOOLEAN DEFAULT TRUE,
    rollback_threshold DOUBLE PRECISION DEFAULT 10.0,  -- Changed from DECIMAL(5,2)
    force_update BOOLEAN DEFAULT FALSE,
    priority INTEGER DEFAULT 0,
    tags TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL
);

-- 3. Create device_updates table
CREATE TABLE ota.device_updates (
    id SERIAL PRIMARY KEY,
    update_id VARCHAR(64) NOT NULL UNIQUE,
    device_id VARCHAR(255) NOT NULL,  -- No FK constraint - cross-service reference
    campaign_id VARCHAR(64) NOT NULL,  -- No FK constraint
    firmware_id VARCHAR(64) NOT NULL,  -- No FK constraint
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    progress DOUBLE PRECISION DEFAULT 0.0,  -- Changed from DECIMAL(5,2)
    error_message TEXT,
    error_code VARCHAR(50),
    retry_count INTEGER DEFAULT 0,
    scheduled_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create update_history table
CREATE TABLE ota.update_history (
    id SERIAL PRIMARY KEY,
    history_id VARCHAR(64) NOT NULL UNIQUE,
    device_id VARCHAR(255) NOT NULL,  -- No FK constraint - cross-service reference
    firmware_id VARCHAR(64) NOT NULL,  -- No FK constraint
    campaign_id VARCHAR(64),
    from_version VARCHAR(50),
    to_version VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    duration_seconds INTEGER,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Create rollback_logs table
CREATE TABLE ota.rollback_logs (
    id SERIAL PRIMARY KEY,
    rollback_id VARCHAR(64) NOT NULL UNIQUE,
    device_id VARCHAR(255) NOT NULL,  -- No FK constraint - cross-service reference
    campaign_id VARCHAR(64) NOT NULL,  -- No FK constraint
    from_firmware_id VARCHAR(64) NOT NULL,
    to_firmware_id VARCHAR(64) NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    triggered_by VARCHAR(20) NOT NULL,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- 6. Create firmware_downloads table
CREATE TABLE ota.firmware_downloads (
    id SERIAL PRIMARY KEY,
    download_id VARCHAR(64) NOT NULL UNIQUE,
    firmware_id VARCHAR(64) NOT NULL,  -- No FK constraint
    device_id VARCHAR(255) NOT NULL,  -- No FK constraint - cross-service reference
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    download_url TEXT NOT NULL,
    bytes_downloaded BIGINT DEFAULT 0,
    total_bytes BIGINT NOT NULL,
    progress DOUBLE PRECISION DEFAULT 0.0,  -- Changed from DECIMAL(5,2)
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================
-- Indexes
-- ====================

-- Firmware indexes
CREATE INDEX idx_firmware_device_model ON ota.firmware(device_model);
CREATE INDEX idx_firmware_version ON ota.firmware(version);
CREATE INDEX idx_firmware_manufacturer ON ota.firmware(manufacturer);
CREATE INDEX idx_firmware_beta ON ota.firmware(is_beta);
CREATE INDEX idx_firmware_tags ON ota.firmware USING GIN (tags);
CREATE INDEX idx_firmware_created_at ON ota.firmware(created_at DESC);

-- Update campaigns indexes
CREATE INDEX idx_campaigns_firmware ON ota.update_campaigns(firmware_id);
CREATE INDEX idx_campaigns_status ON ota.update_campaigns(status);
CREATE INDEX idx_campaigns_start_time ON ota.update_campaigns(start_time);
CREATE INDEX idx_campaigns_tags ON ota.update_campaigns USING GIN (tags);
CREATE INDEX idx_campaigns_created_at ON ota.update_campaigns(created_at DESC);

-- Device updates indexes
CREATE INDEX idx_device_updates_device ON ota.device_updates(device_id);
CREATE INDEX idx_device_updates_campaign ON ota.device_updates(campaign_id);
CREATE INDEX idx_device_updates_firmware ON ota.device_updates(firmware_id);
CREATE INDEX idx_device_updates_status ON ota.device_updates(status);
CREATE INDEX idx_device_updates_scheduled ON ota.device_updates(scheduled_at);
CREATE INDEX idx_device_updates_created_at ON ota.device_updates(created_at DESC);

-- Composite indexes
CREATE INDEX idx_device_updates_device_status ON ota.device_updates(device_id, status);
CREATE INDEX idx_device_updates_campaign_status ON ota.device_updates(campaign_id, status);

-- Update history indexes
CREATE INDEX idx_update_history_device ON ota.update_history(device_id);
CREATE INDEX idx_update_history_firmware ON ota.update_history(firmware_id);
CREATE INDEX idx_update_history_campaign ON ota.update_history(campaign_id);
CREATE INDEX idx_update_history_status ON ota.update_history(status);
CREATE INDEX idx_update_history_created_at ON ota.update_history(created_at DESC);

-- Rollback logs indexes
CREATE INDEX idx_rollback_device ON ota.rollback_logs(device_id);
CREATE INDEX idx_rollback_campaign ON ota.rollback_logs(campaign_id);
CREATE INDEX idx_rollback_status ON ota.rollback_logs(status);
CREATE INDEX idx_rollback_created_at ON ota.rollback_logs(created_at DESC);

-- Firmware downloads indexes
CREATE INDEX idx_downloads_firmware ON ota.firmware_downloads(firmware_id);
CREATE INDEX idx_downloads_device ON ota.firmware_downloads(device_id);
CREATE INDEX idx_downloads_status ON ota.firmware_downloads(status);
CREATE INDEX idx_downloads_created_at ON ota.firmware_downloads(created_at DESC);

-- ====================
-- Comments
-- ====================

COMMENT ON SCHEMA ota IS 'OTA service schema - firmware updates and rollback management';
COMMENT ON TABLE ota.firmware IS 'Firmware versions and metadata';
COMMENT ON TABLE ota.update_campaigns IS 'OTA update campaigns and rollout strategies';
COMMENT ON TABLE ota.device_updates IS 'Device-specific update tracking';
COMMENT ON TABLE ota.update_history IS 'Historical record of all firmware updates';
COMMENT ON TABLE ota.rollback_logs IS 'Firmware rollback tracking and logs';
COMMENT ON TABLE ota.firmware_downloads IS 'Firmware download progress tracking';

COMMENT ON COLUMN ota.firmware.success_rate IS 'Overall success rate of this firmware (DOUBLE PRECISION)';
COMMENT ON COLUMN ota.update_campaigns.rollback_threshold IS 'Failure percentage threshold for auto-rollback';
COMMENT ON COLUMN ota.device_updates.progress IS 'Update progress percentage (0-100)';
COMMENT ON COLUMN ota.firmware_downloads.progress IS 'Download progress percentage (0-100)';
