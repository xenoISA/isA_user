-- OTA Service Migration: Add deployment_strategy field
-- Version: 006
-- Date: 2025-11-04
-- Description: Add deployment_strategy column to update_campaigns table

-- Add deployment_strategy field to update_campaigns table
ALTER TABLE ota.update_campaigns
ADD COLUMN IF NOT EXISTS deployment_strategy VARCHAR(20) DEFAULT 'staged';

-- Add comment for documentation
COMMENT ON COLUMN ota.update_campaigns.deployment_strategy IS 'Deployment strategy (immediate, scheduled, staged, canary, blue_green)';

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_campaigns_deployment_strategy ON ota.update_campaigns(deployment_strategy);
