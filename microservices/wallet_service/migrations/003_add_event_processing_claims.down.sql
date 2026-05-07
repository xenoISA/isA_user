-- Wallet Service Migration: Reverse 003_add_event_processing_claims
-- Version: 003 (downgrade)
-- Date: 2026-05-04
-- Description: Drop the durable event-processing claim table for wallet_service.

DROP TRIGGER IF EXISTS update_wallet_event_processing_claims_updated_at
    ON wallet.event_processing_claims;

DROP INDEX IF EXISTS wallet.idx_wallet_event_processing_claims_updated_at;
DROP INDEX IF EXISTS wallet.idx_wallet_event_processing_claims_source_event;
DROP INDEX IF EXISTS wallet.idx_wallet_event_processing_claims_status;

DROP TABLE IF EXISTS wallet.event_processing_claims;
