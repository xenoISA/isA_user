-- Artifact Service Migration: bootstrap artifact_library tables
-- Version: 001
-- Date: 2026-05-18
--
-- Phase 1 (xenoISA/isA_user#441 / xenoISA/isA_#427). Three tables:
-- artifacts  — top-level row per artifact, soft-delete via deleted_at
-- artifact_versions — append-only immutable version chain per artifact
-- artifact_shares — token-based share links + visibility scope
--
-- Phase 3+ adds artifact_mcp_grants / artifact_kv / artifact_runtime_usage
-- in a follow-up migration.

CREATE SCHEMA IF NOT EXISTS artifact;

-- ==========================================================================
-- artifacts
-- ==========================================================================
CREATE TABLE IF NOT EXISTS artifact.artifacts (
    id                  VARCHAR(255) PRIMARY KEY,
    owner_user_id       VARCHAR(255) NOT NULL,
    owner_org_id        VARCHAR(255) NOT NULL DEFAULT '',
    title               VARCHAR(500) NOT NULL,
    content_type        VARCHAR(64)  NOT NULL,
    current_version_id  VARCHAR(255) NOT NULL DEFAULT '',
    source_session_id   VARCHAR(255) NOT NULL DEFAULT '',
    source_message_id   VARCHAR(255) NOT NULL DEFAULT '',
    parent_artifact_id  VARCHAR(255) NOT NULL DEFAULT '',
    visibility          VARCHAR(16)  NOT NULL DEFAULT 'private'
        CHECK (visibility IN ('private', 'unlisted', 'org', 'public')),
    ai_runtime_enabled  BOOLEAN      NOT NULL DEFAULT false,
    storage_scope       VARCHAR(16)  NOT NULL DEFAULT 'none'
        CHECK (storage_scope IN ('personal', 'shared', 'none')),
    metadata            JSONB        NOT NULL DEFAULT '{}'::jsonb,
    deleted_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_artifacts_owner_live
    ON artifact.artifacts (owner_user_id, updated_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_artifacts_org_live
    ON artifact.artifacts (owner_org_id, updated_at DESC)
    WHERE deleted_at IS NULL AND owner_org_id <> '';

CREATE INDEX IF NOT EXISTS idx_artifacts_parent
    ON artifact.artifacts (parent_artifact_id)
    WHERE parent_artifact_id <> '';

-- ==========================================================================
-- artifact_versions — append-only immutable version chain
-- ==========================================================================
CREATE TABLE IF NOT EXISTS artifact.artifact_versions (
    id                  VARCHAR(255) PRIMARY KEY,
    artifact_id         VARCHAR(255) NOT NULL REFERENCES artifact.artifacts(id) ON DELETE CASCADE,
    number              INTEGER      NOT NULL CHECK (number >= 1),
    content             TEXT         NOT NULL,
    language            VARCHAR(64),
    filename            VARCHAR(500),
    blob_url            TEXT,                 -- Phase 1: plain url; Phase 3 plumbs Vercel Blob
    a2ui_state_json     JSONB,
    instruction         TEXT,
    created_by          VARCHAR(255),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (artifact_id, number)
);

CREATE INDEX IF NOT EXISTS idx_artifact_versions_lookup
    ON artifact.artifact_versions (artifact_id, number DESC);

-- ==========================================================================
-- artifact_shares — token-based share links (Phase 2 backend; Phase 1 table
-- ships so the publish/revoke routes can be added without a follow-up
-- migration)
-- ==========================================================================
CREATE TABLE IF NOT EXISTS artifact.artifact_shares (
    token               VARCHAR(32)  PRIMARY KEY,
    artifact_id         VARCHAR(255) NOT NULL REFERENCES artifact.artifacts(id) ON DELETE CASCADE,
    version_pin         INTEGER,
    visibility          VARCHAR(16)  NOT NULL CHECK (visibility IN ('public', 'org')),
    org_id              VARCHAR(255),
    created_by          VARCHAR(255) NOT NULL,
    expires_at          TIMESTAMPTZ,
    revoked_at          TIMESTAMPTZ,
    view_count          BIGINT       NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_artifact_shares_artifact
    ON artifact.artifact_shares (artifact_id);

CREATE INDEX IF NOT EXISTS idx_artifact_shares_active
    ON artifact.artifact_shares (artifact_id) WHERE revoked_at IS NULL;

COMMENT ON SCHEMA artifact IS
    'Artifact library backend (xenoISA/isA_user#441 / xenoISA/isA_#427)';
