-- Migration: Remove subscription foreign key constraints from product service tables
-- Date: 2025-10-15
-- Purpose: Allow product service to operate independently without database-level FK to subscriptions

-- Remove FK constraint from product_usage_records for subscription
ALTER TABLE IF EXISTS dev.product_usage_records
DROP CONSTRAINT IF EXISTS fk_product_usage_subscription;

-- Remove FK constraint from subscription_usage for subscription
ALTER TABLE IF EXISTS dev.subscription_usage
DROP CONSTRAINT IF EXISTS fk_subscription_usage_subscription;

-- Remove FK constraint from subscription_usage for user
ALTER TABLE IF EXISTS dev.subscription_usage
DROP CONSTRAINT IF EXISTS fk_subscription_usage_user;

-- Remove FK constraint from subscription_usage for organization
ALTER TABLE IF EXISTS dev.subscription_usage
DROP CONSTRAINT IF EXISTS fk_subscription_usage_organization;

-- Add indexes for performance (to replace FK indexes)
CREATE INDEX IF NOT EXISTS idx_product_usage_records_subscription_id
ON dev.product_usage_records(subscription_id);

CREATE INDEX IF NOT EXISTS idx_subscription_usage_subscription_id
ON dev.subscription_usage(subscription_id);

CREATE INDEX IF NOT EXISTS idx_subscription_usage_user_id
ON dev.subscription_usage(user_id);

CREATE INDEX IF NOT EXISTS idx_subscription_usage_organization_id
ON dev.subscription_usage(organization_id);
