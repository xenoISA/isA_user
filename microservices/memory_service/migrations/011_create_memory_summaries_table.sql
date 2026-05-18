-- Memory Service Migration: Create memory_summaries table
-- Version: 011
-- Date: 2026-05-18
--
-- Stores synthesized "narrative summary" rows for #428 Phase 2 hard slice
-- (xenoISA/isA_user#439). One row per (user_id, scope, scope_id):
--   - scope='user'    → scope_id == user_id (whole-user summary)
--   - scope='project' → scope_id == project_id (per-project summary)
--
-- `content` is the markdown narrative shown in SidePanelMemory.
-- `highlights` is a JSON array of bullet strings for the badge / preview.
-- `version` is bumped on every regenerate OR edit so the FE can detect drift.
-- `generated_at` is the LLM-synthesis timestamp; `edited_at` is set ONLY when
--   the user hand-edits via PUT /summary (regenerate clears it back to NULL).
-- `source_counts` records what the synthesis saw: {sessions, turns, memories}.

CREATE TABLE IF NOT EXISTS memory.memory_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    scope VARCHAR(32) NOT NULL CHECK (scope IN ('user', 'project')),
    scope_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    highlights JSONB NOT NULL DEFAULT '[]'::jsonb,
    version INT NOT NULL DEFAULT 1,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    edited_at TIMESTAMPTZ,
    source_counts JSONB NOT NULL DEFAULT '{"sessions":0,"turns":0,"memories":0}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_memory_summaries_scope UNIQUE (user_id, scope, scope_id)
);

CREATE INDEX IF NOT EXISTS idx_memory_summaries_user
    ON memory.memory_summaries (user_id);
CREATE INDEX IF NOT EXISTS idx_memory_summaries_scope_lookup
    ON memory.memory_summaries (user_id, scope, scope_id);

COMMENT ON TABLE memory.memory_summaries IS
    'Synthesized narrative summaries for user/project memory (xenoISA/isA_#428 / xenoISA/isA_user#439 hard slice). One row per (user_id, scope, scope_id) — bump version on regenerate or edit.';
