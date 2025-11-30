-- OTA Service Migration: Remove cross-service foreign keys
-- Version: 002
-- Date: 2025-01-21
-- Description: Remove foreign key constraints to devices table (managed by Device Service)
--              In microservices architecture, each service owns its database
--              Device validation should be done via Device Service API, not DB FK

-- Remove foreign key constraints that reference dev.devices table
-- (dev.devices is managed by Device Service, not OTA Service)

ALTER TABLE dev.device_updates
    DROP CONSTRAINT IF EXISTS fk_update_device;

ALTER TABLE dev.update_history
    DROP CONSTRAINT IF EXISTS fk_history_device;

ALTER TABLE dev.rollback_logs
    DROP CONSTRAINT IF EXISTS fk_rollback_device;

ALTER TABLE dev.firmware_downloads
    DROP CONSTRAINT IF EXISTS fk_download_device;

-- Add comments to document the architectural decision
COMMENT ON COLUMN dev.device_updates.device_id IS 'Device ID (validated via Device Service API, not DB FK)';
COMMENT ON COLUMN dev.update_history.device_id IS 'Device ID (validated via Device Service API, not DB FK)';
COMMENT ON COLUMN dev.rollback_logs.device_id IS 'Device ID (validated via Device Service API, not DB FK)';
COMMENT ON COLUMN dev.firmware_downloads.device_id IS 'Device ID (validated via Device Service API, not DB FK)';

-- Note: Indexes on device_id columns are kept for performance
-- They don't enforce referential integrity, just improve query speed
