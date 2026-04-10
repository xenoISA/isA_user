-- Billing Service Migration: Add durable event processing claims
-- Version: 005
-- Date: 2026-04-09
-- Description: Replace in-memory billing event deduplication with durable DB-backed claims

CREATE TABLE IF NOT EXISTS billing.event_processing_claims (
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

CREATE INDEX IF NOT EXISTS idx_event_processing_claims_status
    ON billing.event_processing_claims(processing_status);

CREATE INDEX IF NOT EXISTS idx_event_processing_claims_source_event
    ON billing.event_processing_claims(source_event_id);

CREATE INDEX IF NOT EXISTS idx_event_processing_claims_updated_at
    ON billing.event_processing_claims(updated_at);

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
            WHERE tgname = 'update_event_processing_claims_updated_at'
        ) THEN
            CREATE TRIGGER update_event_processing_claims_updated_at
                BEFORE UPDATE ON billing.event_processing_claims
                FOR EACH ROW
                EXECUTE FUNCTION public.update_updated_at_column();
        END IF;
    END IF;
END $$;

COMMENT ON TABLE billing.event_processing_claims IS
    'Durable idempotency claims for billing event processing';
