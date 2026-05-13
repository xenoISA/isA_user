-- Calendar Service Migration: External sync idempotency
-- Version: 003
-- Date: 2026-05-13
-- Description: Ensure repeated provider syncs upsert by stable external ids.

CREATE UNIQUE INDEX IF NOT EXISTS idx_events_user_provider_external_unique
    ON calendar.calendar_events(user_id, sync_provider, external_event_id)
    WHERE external_event_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_sync_status_user_provider_token
    ON calendar.calendar_sync_status(user_id, provider)
    WHERE sync_token IS NOT NULL;
