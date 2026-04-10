-- Billing Service Migration: add canonical payer fields
-- Version: 004
-- Date: 2026-04-09
-- Description: separates payer identity from actor attribution on billing records/events

ALTER TABLE billing.billing_records
    ADD COLUMN IF NOT EXISTS actor_user_id VARCHAR(100);

ALTER TABLE billing.billing_records
    ADD COLUMN IF NOT EXISTS billing_account_type VARCHAR(50);

ALTER TABLE billing.billing_records
    ADD COLUMN IF NOT EXISTS billing_account_id VARCHAR(100);

ALTER TABLE billing.billing_events
    ADD COLUMN IF NOT EXISTS actor_user_id VARCHAR(100);

ALTER TABLE billing.billing_events
    ADD COLUMN IF NOT EXISTS billing_account_type VARCHAR(50);

ALTER TABLE billing.billing_events
    ADD COLUMN IF NOT EXISTS billing_account_id VARCHAR(100);

UPDATE billing.billing_records
SET actor_user_id = COALESCE(actor_user_id, user_id)
WHERE actor_user_id IS NULL;

UPDATE billing.billing_records
SET billing_account_type = CASE
    WHEN organization_id IS NOT NULL THEN 'organization'
    ELSE 'user'
END
WHERE billing_account_type IS NULL;

UPDATE billing.billing_records
SET billing_account_id = CASE
    WHEN organization_id IS NOT NULL THEN organization_id
    ELSE user_id
END
WHERE billing_account_id IS NULL;

UPDATE billing.billing_events
SET actor_user_id = COALESCE(actor_user_id, user_id)
WHERE actor_user_id IS NULL;

UPDATE billing.billing_events
SET billing_account_type = CASE
    WHEN organization_id IS NOT NULL THEN 'organization'
    ELSE 'user'
END
WHERE billing_account_type IS NULL;

UPDATE billing.billing_events
SET billing_account_id = CASE
    WHEN organization_id IS NOT NULL THEN organization_id
    ELSE user_id
END
WHERE billing_account_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_billing_records_billing_account
    ON billing.billing_records(billing_account_type, billing_account_id);

CREATE INDEX IF NOT EXISTS idx_billing_records_actor_user_id
    ON billing.billing_records(actor_user_id);

CREATE INDEX IF NOT EXISTS idx_billing_events_billing_account
    ON billing.billing_events(billing_account_type, billing_account_id);

CREATE INDEX IF NOT EXISTS idx_billing_events_actor_user_id
    ON billing.billing_events(actor_user_id);

COMMENT ON COLUMN billing.billing_records.actor_user_id IS
    'Human actor responsible for the billed usage';

COMMENT ON COLUMN billing.billing_records.billing_account_type IS
    'Canonical payer type for the billing record: user or organization';

COMMENT ON COLUMN billing.billing_records.billing_account_id IS
    'Canonical payer identifier for the billing record';

COMMENT ON COLUMN billing.billing_events.actor_user_id IS
    'Human actor responsible for the billed event';

COMMENT ON COLUMN billing.billing_events.billing_account_type IS
    'Canonical payer type for the billing event: user or organization';

COMMENT ON COLUMN billing.billing_events.billing_account_id IS
    'Canonical payer identifier for the billing event';
