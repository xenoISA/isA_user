-- Subscription Service Migration: add durable credit reservations
-- Version: 002
-- Date: 2026-04-08
-- Description: Stores reservation state for reserve/reconcile/release billing flow

CREATE TABLE IF NOT EXISTS subscription.credit_reservations (
    id SERIAL PRIMARY KEY,
    reservation_id VARCHAR(100) UNIQUE NOT NULL,
    request_id VARCHAR(100) UNIQUE,
    subscription_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),
    model VARCHAR(255),
    estimated_credits BIGINT NOT NULL,
    actual_credits BIGINT,
    credits_refunded BIGINT NOT NULL DEFAULT 0,
    extra_credits_consumed BIGINT NOT NULL DEFAULT 0,
    credits_remaining_after_reserve BIGINT,
    credits_remaining_after_finalize BIGINT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    metadata JSONB DEFAULT '{}'::jsonb,
    reconciled_at TIMESTAMPTZ,
    released_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT credit_reservations_status_valid
        CHECK (status IN ('pending', 'reconciled', 'released'))
);

CREATE INDEX IF NOT EXISTS idx_credit_reservation_reservation_id
    ON subscription.credit_reservations(reservation_id);
CREATE INDEX IF NOT EXISTS idx_credit_reservation_request_id
    ON subscription.credit_reservations(request_id);
CREATE INDEX IF NOT EXISTS idx_credit_reservation_subscription_id
    ON subscription.credit_reservations(subscription_id);
CREATE INDEX IF NOT EXISTS idx_credit_reservation_user_id
    ON subscription.credit_reservations(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_reservation_org_id
    ON subscription.credit_reservations(organization_id);
CREATE INDEX IF NOT EXISTS idx_credit_reservation_status
    ON subscription.credit_reservations(status);
CREATE INDEX IF NOT EXISTS idx_credit_reservation_created_at
    ON subscription.credit_reservations(created_at DESC);

DROP TRIGGER IF EXISTS update_credit_reservations_updated_at
    ON subscription.credit_reservations;

CREATE TRIGGER update_credit_reservations_updated_at
    BEFORE UPDATE ON subscription.credit_reservations
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

COMMENT ON TABLE subscription.credit_reservations IS
    'Durable reservation records for pre-inference credit holds and reconciliation';
