-- Memory Service Migration: Create user_memory_state table
-- Version: 010
-- Date: 2026-05-18
--
-- Tracks per-user "memory plumbing" state for #428 Phase 2:
-- - paused / paused_at: when set, the frontend hides the memory write
--   confirmations and (optionally) the chat path skips synthesis.
-- - last_synthesis_at: timestamp of the last summary regeneration, used by
--   the summary panel to badge stale summaries.
-- - last_reset_at: audit trail for the destructive RESET action.
--
-- Single row per user — INSERT ... ON CONFLICT DO UPDATE upserts.

-- ====================
-- User Memory State Table
-- ====================
CREATE TABLE IF NOT EXISTS memory.user_memory_state (
    user_id VARCHAR(255) PRIMARY KEY,
    paused BOOLEAN NOT NULL DEFAULT false,
    paused_at TIMESTAMPTZ,
    last_synthesis_at TIMESTAMPTZ,
    last_reset_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_memory_state_paused
    ON memory.user_memory_state (paused) WHERE paused = true;

COMMENT ON TABLE memory.user_memory_state IS
    'Per-user toggles for memory pipeline: pause/resume + reset audit + synthesis freshness (xenoISA/isA_#428 / xenoISA/isA_user#439)';
