-- OTA Service Migration: Fix schema constraints
-- Version: 004
-- Date: 2025-10-27
-- Description: Make campaign_id nullable in device_updates for single-device updates

-- Make campaign_id nullable in device_updates table
ALTER TABLE ota.device_updates
ALTER COLUMN campaign_id DROP NOT NULL;

COMMENT ON COLUMN ota.device_updates.campaign_id IS 'Campaign ID (nullable for single-device updates)';
