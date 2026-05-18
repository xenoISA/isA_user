-- Artifact Service Migration: MCP tool grants per (artifact, user)
-- Version: 003
-- Date: 2026-05-18
--
-- Phase 3 of xenoISA/isA_user#441 (paired with isA_/docs/design/427-artifact-flows.md §10).
-- Powers POST /api/v1/artifacts/{id}/mcp/approve + .../mcp/call gates.
-- One row per (artifact, user, tool, server, scope) — `always` grants are the
-- only ones uniquely de-duped so users can hold multiple `once`-scoped
-- approvals across sessions. Decision/scope are bounded by CHECK constraints
-- so the API layer can trust whatever it reads back.

CREATE TABLE IF NOT EXISTS artifact.artifact_mcp_grants (
    id            VARCHAR(255) PRIMARY KEY,
    artifact_id   VARCHAR(255) NOT NULL REFERENCES artifact.artifacts(id) ON DELETE CASCADE,
    user_id       VARCHAR(255) NOT NULL,
    tool_name     VARCHAR(255) NOT NULL,
    server_id     VARCHAR(255) NOT NULL,
    decision      VARCHAR(8)   NOT NULL
        CHECK (decision IN ('allow', 'deny')),
    scope         VARCHAR(8)   NOT NULL
        CHECK (scope IN ('once', 'session', 'always')),
    approved_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at    TIMESTAMPTZ,
    last_used_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Only `always`-scoped allow grants are unique per (artifact, user, tool,
-- server). `once`/`session` grants may exist as many times as the user
-- approves them, and `deny` rows are advisory.
CREATE UNIQUE INDEX IF NOT EXISTS uq_artifact_mcp_grants_always
    ON artifact.artifact_mcp_grants (artifact_id, user_id, tool_name, server_id)
    WHERE decision = 'allow' AND scope = 'always';

CREATE INDEX IF NOT EXISTS idx_artifact_mcp_grants_lookup
    ON artifact.artifact_mcp_grants (artifact_id, user_id, tool_name, server_id);

COMMENT ON TABLE artifact.artifact_mcp_grants IS
    'Per-(artifact,user,tool) MCP approval persistence — gates artifact MCP calls (#441 Phase 3)';
