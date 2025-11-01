-- Migration: Remove cross-service foreign key constraints from billing service tables
-- Date: 2025-10-15
-- Purpose: Allow billing service to operate independently without database-level FK to users, organizations, subscriptions

-- Remove FK constraints from billing_records
ALTER TABLE IF EXISTS dev.billing_records
DROP CONSTRAINT IF EXISTS fk_billing_record_user;

ALTER TABLE IF EXISTS dev.billing_records
DROP CONSTRAINT IF EXISTS fk_billing_record_organization;

ALTER TABLE IF EXISTS dev.billing_records
DROP CONSTRAINT IF EXISTS fk_billing_record_subscription;

-- Remove FK constraints from billing_events
ALTER TABLE IF EXISTS dev.billing_events
DROP CONSTRAINT IF EXISTS fk_billing_event_user;

ALTER TABLE IF EXISTS dev.billing_events
DROP CONSTRAINT IF EXISTS fk_billing_event_organization;

ALTER TABLE IF EXISTS dev.billing_events
DROP CONSTRAINT IF EXISTS fk_billing_event_subscription;

-- Remove FK constraints from usage_aggregations
ALTER TABLE IF EXISTS dev.usage_aggregations
DROP CONSTRAINT IF EXISTS fk_usage_agg_user;

ALTER TABLE IF EXISTS dev.usage_aggregations
DROP CONSTRAINT IF EXISTS fk_usage_agg_organization;

ALTER TABLE IF EXISTS dev.usage_aggregations
DROP CONSTRAINT IF EXISTS fk_usage_agg_subscription;

-- Remove FK constraints from billing_quotas
ALTER TABLE IF EXISTS dev.billing_quotas
DROP CONSTRAINT IF EXISTS fk_billing_quota_user;

ALTER TABLE IF EXISTS dev.billing_quotas
DROP CONSTRAINT IF EXISTS fk_billing_quota_organization;

ALTER TABLE IF EXISTS dev.billing_quotas
DROP CONSTRAINT IF EXISTS fk_billing_quota_subscription;

-- Add indexes for performance (to replace FK indexes)
CREATE INDEX IF NOT EXISTS idx_billing_records_user_id
ON dev.billing_records(user_id);

CREATE INDEX IF NOT EXISTS idx_billing_records_organization_id
ON dev.billing_records(organization_id);

CREATE INDEX IF NOT EXISTS idx_billing_records_subscription_id
ON dev.billing_records(subscription_id);

CREATE INDEX IF NOT EXISTS idx_billing_events_user_id
ON dev.billing_events(user_id);

CREATE INDEX IF NOT EXISTS idx_billing_events_organization_id
ON dev.billing_events(organization_id);

CREATE INDEX IF NOT EXISTS idx_billing_events_subscription_id
ON dev.billing_events(subscription_id);

CREATE INDEX IF NOT EXISTS idx_usage_aggregations_user_id
ON dev.usage_aggregations(user_id);

CREATE INDEX IF NOT EXISTS idx_usage_aggregations_organization_id
ON dev.usage_aggregations(organization_id);

CREATE INDEX IF NOT EXISTS idx_usage_aggregations_subscription_id
ON dev.usage_aggregations(subscription_id);

CREATE INDEX IF NOT EXISTS idx_billing_quotas_user_id
ON dev.billing_quotas(user_id);

CREATE INDEX IF NOT EXISTS idx_billing_quotas_organization_id
ON dev.billing_quotas(organization_id);

CREATE INDEX IF NOT EXISTS idx_billing_quotas_subscription_id
ON dev.billing_quotas(subscription_id);
