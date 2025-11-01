-- OTA Service Migration: Fix priority field type
-- Version: 005
-- Date: 2025-10-27
-- Description: Change priority from INTEGER to VARCHAR to match enum values

-- Change priority field in update_campaigns table
ALTER TABLE ota.update_campaigns
ALTER COLUMN priority TYPE VARCHAR(20);

COMMENT ON COLUMN ota.update_campaigns.priority IS 'Priority level (low, normal, high, critical, emergency)';
