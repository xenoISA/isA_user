-- OTA Service Migration: Create OTA update management tables
-- Version: 001
-- Date: 2025-01-21
-- Description: Core tables for firmware management, update campaigns, and rollback tracking

-- Drop existing tables if needed (be careful in production!)
DROP TABLE IF EXISTS dev.firmware_downloads CASCADE;
DROP TABLE IF EXISTS dev.rollback_logs CASCADE;
DROP TABLE IF EXISTS dev.update_history CASCADE;
DROP TABLE IF EXISTS dev.device_updates CASCADE;
DROP TABLE IF EXISTS dev.update_campaigns CASCADE;
DROP TABLE IF EXISTS dev.firmware CASCADE;

-- Create firmware table
CREATE TABLE dev.firmware (
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
    success_rate DECIMAL(5,2) DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL,
    
    CONSTRAINT unique_firmware_version UNIQUE(device_model, version)
);

-- Create update_campaigns table
CREATE TABLE dev.update_campaigns (
    id SERIAL PRIMARY KEY,
    campaign_id VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    description VARCHAR(1000),
    firmware_id VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'created',
    deployment_strategy VARCHAR(20) NOT NULL DEFAULT 'staged',
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    
    -- Target configuration
    target_device_count INTEGER DEFAULT 0,
    targeted_devices TEXT[],
    targeted_groups TEXT[],
    target_filters JSONB DEFAULT '{}'::jsonb,
    
    -- Deployment configuration
    rollout_percentage INTEGER DEFAULT 100,
    max_concurrent_updates INTEGER DEFAULT 10,
    batch_size INTEGER DEFAULT 50,
    
    -- Progress tracking
    total_devices INTEGER DEFAULT 0,
    pending_devices INTEGER DEFAULT 0,
    in_progress_devices INTEGER DEFAULT 0,
    completed_devices INTEGER DEFAULT 0,
    failed_devices INTEGER DEFAULT 0,
    cancelled_devices INTEGER DEFAULT 0,
    
    -- Time configuration
    scheduled_start TIMESTAMPTZ,
    scheduled_end TIMESTAMPTZ,
    actual_start TIMESTAMPTZ,
    actual_end TIMESTAMPTZ,
    timeout_minutes INTEGER DEFAULT 60,
    
    -- Rollback configuration
    auto_rollback BOOLEAN DEFAULT TRUE,
    failure_threshold_percent INTEGER DEFAULT 20,
    rollback_triggers TEXT[],
    
    -- Approval
    requires_approval BOOLEAN DEFAULT FALSE,
    approved BOOLEAN,
    approved_by VARCHAR(100),
    approval_comment VARCHAR(500),
    approved_at TIMESTAMPTZ,
    
    -- Notification
    notify_on_start BOOLEAN DEFAULT TRUE,
    notify_on_complete BOOLEAN DEFAULT TRUE,
    notify_on_failure BOOLEAN DEFAULT TRUE,
    notification_channels TEXT[],
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL,
    
    CONSTRAINT fk_campaign_firmware FOREIGN KEY (firmware_id) 
        REFERENCES dev.firmware(firmware_id),
    CONSTRAINT check_campaign_status CHECK (status IN ('created', 'scheduled', 'in_progress', 'downloading', 'verifying', 'installing', 'rebooting', 'completed', 'failed', 'cancelled', 'rollback')),
    CONSTRAINT check_deployment_strategy CHECK (deployment_strategy IN ('immediate', 'scheduled', 'staged', 'canary', 'blue_green')),
    CONSTRAINT check_priority CHECK (priority IN ('low', 'normal', 'high', 'critical', 'emergency')),
    CONSTRAINT check_rollout_percentage CHECK (rollout_percentage BETWEEN 1 AND 100),
    CONSTRAINT check_failure_threshold CHECK (failure_threshold_percent BETWEEN 1 AND 100)
);

-- Create device_updates table
CREATE TABLE dev.device_updates (
    id SERIAL PRIMARY KEY,
    update_id VARCHAR(64) NOT NULL UNIQUE,
    device_id VARCHAR(64) NOT NULL,
    campaign_id VARCHAR(64),
    firmware_id VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    
    -- Progress tracking
    progress_percentage DECIMAL(5,2) DEFAULT 0.0,
    current_phase VARCHAR(50),
    
    -- Version tracking
    from_version VARCHAR(50),
    to_version VARCHAR(50) NOT NULL,
    
    -- Time tracking
    scheduled_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    timeout_at TIMESTAMPTZ,
    
    -- Error tracking
    error_code VARCHAR(50),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Download tracking
    download_size BIGINT,
    download_progress DECIMAL(5,2) DEFAULT 0.0,
    download_speed DECIMAL(10,2), -- bytes per second
    
    -- Verification
    signature_verified BOOLEAN,
    checksum_verified BOOLEAN,
    
    -- Commands
    pre_update_commands TEXT[],
    post_update_commands TEXT[],
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_update_campaign FOREIGN KEY (campaign_id) 
        REFERENCES dev.update_campaigns(campaign_id) ON DELETE SET NULL,
    CONSTRAINT fk_update_firmware FOREIGN KEY (firmware_id) 
        REFERENCES dev.firmware(firmware_id),
    CONSTRAINT fk_update_device FOREIGN KEY (device_id) 
        REFERENCES dev.devices(device_id) ON DELETE CASCADE,
    CONSTRAINT check_update_status CHECK (status IN ('created', 'scheduled', 'in_progress', 'downloading', 'verifying', 'installing', 'rebooting', 'completed', 'failed', 'cancelled', 'rollback')),
    CONSTRAINT check_update_priority CHECK (priority IN ('low', 'normal', 'high', 'critical', 'emergency'))
);

-- Create update_history table
CREATE TABLE dev.update_history (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    update_id VARCHAR(64) NOT NULL,
    firmware_id VARCHAR(64) NOT NULL,
    campaign_id VARCHAR(64),
    from_version VARCHAR(50),
    to_version VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    error_message TEXT,
    rollback_performed BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT fk_history_device FOREIGN KEY (device_id) 
        REFERENCES dev.devices(device_id) ON DELETE CASCADE,
    CONSTRAINT fk_history_firmware FOREIGN KEY (firmware_id) 
        REFERENCES dev.firmware(firmware_id)
);

-- Create rollback_logs table
CREATE TABLE dev.rollback_logs (
    id SERIAL PRIMARY KEY,
    rollback_id VARCHAR(64) NOT NULL UNIQUE,
    campaign_id VARCHAR(64),
    device_id VARCHAR(64),
    trigger VARCHAR(50) NOT NULL,
    reason TEXT NOT NULL,
    from_version VARCHAR(50) NOT NULL,
    to_version VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    success BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    
    CONSTRAINT fk_rollback_campaign FOREIGN KEY (campaign_id) 
        REFERENCES dev.update_campaigns(campaign_id) ON DELETE SET NULL,
    CONSTRAINT fk_rollback_device FOREIGN KEY (device_id) 
        REFERENCES dev.devices(device_id) ON DELETE CASCADE,
    CONSTRAINT check_rollback_trigger CHECK (trigger IN ('manual', 'failure_rate', 'health_check', 'timeout', 'error_threshold')),
    CONSTRAINT check_rollback_status CHECK (status IN ('created', 'in_progress', 'completed', 'failed'))
);

-- Create firmware_downloads table for tracking
CREATE TABLE dev.firmware_downloads (
    id SERIAL PRIMARY KEY,
    firmware_id VARCHAR(64) NOT NULL,
    device_id VARCHAR(64) NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    bytes_downloaded BIGINT DEFAULT 0,
    total_bytes BIGINT NOT NULL,
    download_speed DECIMAL(10,2),
    success BOOLEAN,
    error_message TEXT,
    
    CONSTRAINT fk_download_firmware FOREIGN KEY (firmware_id) 
        REFERENCES dev.firmware(firmware_id),
    CONSTRAINT fk_download_device FOREIGN KEY (device_id) 
        REFERENCES dev.devices(device_id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX idx_firmware_device_model ON dev.firmware(device_model);
CREATE INDEX idx_firmware_version ON dev.firmware(version);
CREATE INDEX idx_firmware_manufacturer ON dev.firmware(manufacturer);
CREATE INDEX idx_firmware_created_by ON dev.firmware(created_by);
CREATE INDEX idx_firmware_beta ON dev.firmware(is_beta) WHERE is_beta = TRUE;
CREATE INDEX idx_firmware_security ON dev.firmware(is_security_update) WHERE is_security_update = TRUE;

CREATE INDEX idx_update_campaigns_status ON dev.update_campaigns(status);
CREATE INDEX idx_update_campaigns_firmware_id ON dev.update_campaigns(firmware_id);
CREATE INDEX idx_update_campaigns_created_by ON dev.update_campaigns(created_by);
CREATE INDEX idx_update_campaigns_scheduled ON dev.update_campaigns(scheduled_start);

CREATE INDEX idx_device_updates_device_id ON dev.device_updates(device_id);
CREATE INDEX idx_device_updates_campaign_id ON dev.device_updates(campaign_id);
CREATE INDEX idx_device_updates_firmware_id ON dev.device_updates(firmware_id);
CREATE INDEX idx_device_updates_status ON dev.device_updates(status);
CREATE INDEX idx_device_updates_priority ON dev.device_updates(priority);
CREATE INDEX idx_device_updates_scheduled ON dev.device_updates(scheduled_at);

CREATE INDEX idx_update_history_device_id ON dev.update_history(device_id);
CREATE INDEX idx_update_history_campaign_id ON dev.update_history(campaign_id);
CREATE INDEX idx_update_history_completed_at ON dev.update_history(completed_at DESC);

CREATE INDEX idx_rollback_logs_campaign_id ON dev.rollback_logs(campaign_id);
CREATE INDEX idx_rollback_logs_device_id ON dev.rollback_logs(device_id);
CREATE INDEX idx_rollback_logs_started_at ON dev.rollback_logs(started_at DESC);

CREATE INDEX idx_firmware_downloads_firmware_id ON dev.firmware_downloads(firmware_id);
CREATE INDEX idx_firmware_downloads_device_id ON dev.firmware_downloads(device_id);

-- Create composite indexes for common queries
CREATE INDEX idx_device_updates_device_status ON dev.device_updates(device_id, status);
CREATE INDEX idx_update_history_device_time ON dev.update_history(device_id, completed_at DESC);

-- Create update triggers
CREATE TRIGGER trigger_update_firmware_updated_at
    BEFORE UPDATE ON dev.firmware
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_campaigns_updated_at
    BEFORE UPDATE ON dev.update_campaigns
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_device_updates_updated_at
    BEFORE UPDATE ON dev.device_updates
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Grant permissions
GRANT ALL ON dev.firmware TO postgres;
GRANT SELECT ON dev.firmware TO authenticated;
GRANT ALL ON SEQUENCE dev.firmware_id_seq TO authenticated;

GRANT ALL ON dev.update_campaigns TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.update_campaigns TO authenticated;
GRANT ALL ON SEQUENCE dev.update_campaigns_id_seq TO authenticated;

GRANT ALL ON dev.device_updates TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.device_updates TO authenticated;
GRANT ALL ON SEQUENCE dev.device_updates_id_seq TO authenticated;

GRANT ALL ON dev.update_history TO postgres;
GRANT SELECT, INSERT ON dev.update_history TO authenticated;
GRANT ALL ON SEQUENCE dev.update_history_id_seq TO authenticated;

GRANT ALL ON dev.rollback_logs TO postgres;
GRANT SELECT, INSERT ON dev.rollback_logs TO authenticated;
GRANT ALL ON SEQUENCE dev.rollback_logs_id_seq TO authenticated;

GRANT ALL ON dev.firmware_downloads TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.firmware_downloads TO authenticated;
GRANT ALL ON SEQUENCE dev.firmware_downloads_id_seq TO authenticated;

-- Add comments for documentation
COMMENT ON TABLE dev.firmware IS 'Firmware files and metadata for OTA updates';
COMMENT ON TABLE dev.update_campaigns IS 'OTA update campaigns for device fleet management';
COMMENT ON TABLE dev.device_updates IS 'Individual device update tracking';
COMMENT ON TABLE dev.update_history IS 'Historical record of all device updates';
COMMENT ON TABLE dev.rollback_logs IS 'Rollback operations and their outcomes';
COMMENT ON TABLE dev.firmware_downloads IS 'Firmware download tracking for bandwidth monitoring';

COMMENT ON COLUMN dev.firmware.checksum_md5 IS 'MD5 checksum for file integrity verification';
COMMENT ON COLUMN dev.firmware.checksum_sha256 IS 'SHA256 checksum for file integrity verification';
COMMENT ON COLUMN dev.firmware.success_rate IS 'Percentage of successful installations (0-100)';

COMMENT ON COLUMN dev.update_campaigns.deployment_strategy IS 'Update deployment strategy (immediate, scheduled, staged, canary, blue_green)';
COMMENT ON COLUMN dev.update_campaigns.rollout_percentage IS 'Percentage of devices to update (1-100)';
COMMENT ON COLUMN dev.update_campaigns.failure_threshold_percent IS 'Failure rate to trigger automatic rollback (1-100)';

COMMENT ON COLUMN dev.device_updates.progress_percentage IS 'Update progress percentage (0-100)';
COMMENT ON COLUMN dev.device_updates.download_speed IS 'Download speed in bytes per second';