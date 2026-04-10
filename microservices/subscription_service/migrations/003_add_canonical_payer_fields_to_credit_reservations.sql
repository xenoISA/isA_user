-- Subscription Service Migration: add canonical payer fields to credit reservations
-- Version: 003
-- Date: 2026-04-09
-- Description: makes reservation ownership explicit for user-vs-organization billing

ALTER TABLE subscription.credit_reservations
    ADD COLUMN IF NOT EXISTS actor_user_id VARCHAR(100);

ALTER TABLE subscription.credit_reservations
    ADD COLUMN IF NOT EXISTS billing_account_type VARCHAR(50);

ALTER TABLE subscription.credit_reservations
    ADD COLUMN IF NOT EXISTS billing_account_id VARCHAR(100);

UPDATE subscription.credit_reservations
SET actor_user_id = COALESCE(actor_user_id, user_id)
WHERE actor_user_id IS NULL;

UPDATE subscription.credit_reservations
SET billing_account_type = CASE
    WHEN organization_id IS NOT NULL THEN 'organization'
    ELSE 'user'
END
WHERE billing_account_type IS NULL;

UPDATE subscription.credit_reservations
SET billing_account_id = CASE
    WHEN organization_id IS NOT NULL THEN organization_id
    ELSE user_id
END
WHERE billing_account_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_credit_reservation_billing_account
    ON subscription.credit_reservations(billing_account_type, billing_account_id);

COMMENT ON COLUMN subscription.credit_reservations.actor_user_id IS
    'Human actor that triggered the reservation';

COMMENT ON COLUMN subscription.credit_reservations.billing_account_type IS
    'Canonical payer type for the reservation: user or organization';

COMMENT ON COLUMN subscription.credit_reservations.billing_account_id IS
    'Canonical payer identifier for the reservation';
