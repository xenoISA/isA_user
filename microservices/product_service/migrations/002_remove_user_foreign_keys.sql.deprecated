-- Migration: Remove user foreign key constraints from product service tables
-- Date: 2025-10-15
-- Purpose: Allow product service to operate independently without database-level FK to users table

-- Remove FK constraint from product_usage_records
ALTER TABLE IF EXISTS dev.product_usage_records
DROP CONSTRAINT IF EXISTS fk_product_usage_user;

-- Remove FK constraint from product_usage_records for organization
ALTER TABLE IF EXISTS dev.product_usage_records
DROP CONSTRAINT IF EXISTS fk_product_usage_organization;

-- Remove FK constraint from user_subscriptions
ALTER TABLE IF EXISTS dev.user_subscriptions
DROP CONSTRAINT IF EXISTS fk_user_subscription_user;

-- Remove FK constraint from user_subscriptions for organization
ALTER TABLE IF EXISTS dev.user_subscriptions
DROP CONSTRAINT IF EXISTS fk_user_subscription_organization;

-- Add indexes for performance (to replace FK indexes)
CREATE INDEX IF NOT EXISTS idx_product_usage_records_user_id
ON dev.product_usage_records(user_id);

CREATE INDEX IF NOT EXISTS idx_product_usage_records_organization_id
ON dev.product_usage_records(organization_id);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id
ON dev.user_subscriptions(user_id);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_organization_id
ON dev.user_subscriptions(organization_id);
