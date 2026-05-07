-- Sharing Service Migration: Add immutable share snapshots
-- Version: 002
-- Date: 2026-05-07

ALTER TABLE sharing.shares
    ADD COLUMN IF NOT EXISTS session_snapshot JSONB,
    ADD COLUMN IF NOT EXISTS messages_snapshot JSONB;

COMMENT ON COLUMN sharing.shares.session_snapshot IS 'Immutable session metadata captured at share creation';
COMMENT ON COLUMN sharing.shares.messages_snapshot IS 'Immutable transcript messages captured at share creation';
