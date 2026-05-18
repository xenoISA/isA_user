-- Artifact Service Migration: per-user daily runtime usage / quota
-- Version: 002
-- Date: 2026-05-18
--
-- Phase 3 of xenoISA/isA_user#441 (paired with isA_/docs/design/427-artifact-flows.md §9).
-- Backs POST /api/v1/artifacts/{id}/runtime/invoke + GET .../runtime/usage.
-- One row per (artifact, user, day_bucket) — increments on each invoke; the
-- service-layer quota check counts `calls` for the current UTC day.

CREATE TABLE IF NOT EXISTS artifact.artifact_runtime_usage (
    artifact_id   VARCHAR(255) NOT NULL REFERENCES artifact.artifacts(id) ON DELETE CASCADE,
    user_id       VARCHAR(255) NOT NULL,
    day_bucket    DATE         NOT NULL,
    tokens_in     BIGINT       NOT NULL DEFAULT 0,
    tokens_out    BIGINT       NOT NULL DEFAULT 0,
    calls         INTEGER      NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (artifact_id, user_id, day_bucket)
);

CREATE INDEX IF NOT EXISTS idx_artifact_runtime_usage_user_day
    ON artifact.artifact_runtime_usage (user_id, day_bucket DESC);

COMMENT ON TABLE artifact.artifact_runtime_usage IS
    'Per-(artifact,user,UTC-day) AI runtime usage counter — drives quota 429s (#441 Phase 3)';
