-- Payment Service Migration: Add durable event processing claims
-- Version: 003
-- Date: 2026-05-04
-- Description: DB-level second-line idempotency for payment event handlers.
--              Mirrors billing_service migration 005 so handlers crashing
--              between the DB commit and the distributed-lock release cannot
--              be replayed by NATS after the lock TTL expires (issue #378,
--              follow-up to #348 / PR #374).

CREATE TABLE IF NOT EXISTS payment.event_processing_claims (
    id SERIAL PRIMARY KEY,
    claim_key VARCHAR(255) UNIQUE NOT NULL,
    source_event_id VARCHAR(100) NOT NULL,
    processing_status VARCHAR(20) NOT NULL DEFAULT 'processing',
    processor_id VARCHAR(255),
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payment_event_processing_claims_status
    ON payment.event_processing_claims(processing_status);

CREATE INDEX IF NOT EXISTS idx_payment_event_processing_claims_source_event
    ON payment.event_processing_claims(source_event_id);

CREATE INDEX IF NOT EXISTS idx_payment_event_processing_claims_updated_at
    ON payment.event_processing_claims(updated_at);

-- Wire up the shared updated_at trigger if the helper function exists.
-- The function is defined in the platform's shared migrations; payment
-- service does not redefine it locally, so we guard the trigger creation.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_proc
        WHERE proname = 'update_updated_at_column'
    ) THEN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_trigger
            WHERE tgname = 'update_payment_event_processing_claims_updated_at'
        ) THEN
            CREATE TRIGGER update_payment_event_processing_claims_updated_at
                BEFORE UPDATE ON payment.event_processing_claims
                FOR EACH ROW
                EXECUTE FUNCTION public.update_updated_at_column();
        END IF;
    END IF;
END $$;

COMMENT ON TABLE payment.event_processing_claims IS
    'Durable idempotency claims for payment event processing (#378).';
