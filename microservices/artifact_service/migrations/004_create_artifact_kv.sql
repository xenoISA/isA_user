-- Artifact Service Migration: per-artifact key/value storage
-- Version: 004
-- Date: 2026-05-18
--
-- Phase 3 of xenoISA/isA_user#441 (paired with isA_/docs/design/427-artifact-flows.md §11).
-- Powers GET/PUT/DELETE /api/v1/artifacts/{id}/kv/{key}.
--
-- Scope semantics:
--   personal — per-user namespace; cross-user reads return 404.
--              user_id is required; persisted verbatim.
--   shared   — single namespace per artifact; user_id is the sentinel
--              '_shared' (NOT NULL so it can ride the PK column directly,
--              keeping a single uniqueness rule across both scopes).
--
-- Note: PostgreSQL does not allow expressions like COALESCE(user_id,…) in
-- a PRIMARY KEY column list, so we materialise the sentinel inline. The
-- service layer rewrites user_id <-> '_shared' on the way in/out so the
-- HTTP contract (user_id only required for scope=personal) stays clean.

CREATE TABLE IF NOT EXISTS artifact.artifact_kv (
    artifact_id   VARCHAR(255) NOT NULL REFERENCES artifact.artifacts(id) ON DELETE CASCADE,
    scope         VARCHAR(16)  NOT NULL
        CHECK (scope IN ('personal', 'shared')),
    user_id       VARCHAR(255) NOT NULL,
    key           VARCHAR(500) NOT NULL,
    value         JSONB        NOT NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (artifact_id, scope, user_id, key),
    -- shared scope MUST use the '_shared' sentinel; personal MUST NOT.
    CHECK (
        (scope = 'personal' AND user_id <> '_shared')
        OR
        (scope = 'shared'   AND user_id =  '_shared')
    )
);

CREATE INDEX IF NOT EXISTS idx_artifact_kv_lookup
    ON artifact.artifact_kv (artifact_id, scope);

COMMENT ON TABLE artifact.artifact_kv IS
    'Per-artifact namespaced key/value storage (#441 Phase 3) — personal scope is per-user, shared scope uses ''_shared'' sentinel';
