-- Project Sharing Service Migration: Create project_shares table
-- Version: 001
-- Date: 2026-05-18
-- Issue: xenoISA/isA_user#442 (paired with xenoISA/isA_#429)
--
-- Schema design per isA_/docs/design/429-project-sharing.md §3.
--
-- Notes:
--   * No FK to projects(id) — the projects table is owned by project_service
--     in a different schema/service, so cross-service FKs are intentionally
--     avoided. We index project_id instead.
--   * The partial unique index on (project_id, lower(invitee_email))
--     WHERE status='pending' enforces invite idempotency: re-inviting the
--     same email while one is already pending returns the existing row
--     rather than creating duplicates. Revoked/accepted rows can coexist.

CREATE SCHEMA IF NOT EXISTS project_sharing;

-- ENUM types for role and status.
-- Idempotent CREATE via DO blocks (Postgres has no IF NOT EXISTS for CREATE TYPE).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'project_share_role') THEN
        CREATE TYPE project_sharing.project_share_role AS ENUM ('viewer', 'editor', 'owner');
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'project_share_status') THEN
        CREATE TYPE project_sharing.project_share_status AS ENUM ('pending', 'accepted', 'revoked');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS project_sharing.project_shares (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        UUID NOT NULL,
    invitee_user_id   VARCHAR(255) NULL,
    invitee_email     VARCHAR(320) NOT NULL,
    role              project_sharing.project_share_role NOT NULL DEFAULT 'viewer',
    invite_token      VARCHAR(32) UNIQUE,
    status            project_sharing.project_share_status NOT NULL DEFAULT 'pending',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_at       TIMESTAMPTZ NULL,
    revoked_at        TIMESTAMPTZ NULL
);

-- Hot path: list members for a project.
CREATE INDEX IF NOT EXISTS idx_project_shares_project_id
    ON project_sharing.project_shares(project_id);

-- Lookup by invite token for accept flow (covered by UNIQUE but explicit for clarity).
CREATE INDEX IF NOT EXISTS idx_project_shares_invite_token
    ON project_sharing.project_shares(invite_token)
    WHERE invite_token IS NOT NULL;

-- Find shares for a user once accepted (for "projects shared with me" queries).
CREATE INDEX IF NOT EXISTS idx_project_shares_invitee_user_id
    ON project_sharing.project_shares(invitee_user_id)
    WHERE invitee_user_id IS NOT NULL;

-- Idempotency: at most ONE pending invite per (project, email).
-- lower() makes the constraint case-insensitive for email matching.
CREATE UNIQUE INDEX IF NOT EXISTS uq_project_shares_pending_email
    ON project_sharing.project_shares(project_id, lower(invitee_email))
    WHERE status = 'pending';

COMMENT ON TABLE project_sharing.project_shares IS
    'Project-level invitations and memberships. Token-based accept flow.';
COMMENT ON COLUMN project_sharing.project_shares.id IS 'Share record UUID (server-assigned)';
COMMENT ON COLUMN project_sharing.project_shares.project_id IS 'Project being shared (FK enforced by project_service, not DB-level)';
COMMENT ON COLUMN project_sharing.project_shares.invitee_user_id IS 'User id once the invitee accepts; NULL before accept';
COMMENT ON COLUMN project_sharing.project_shares.invitee_email IS 'Invitee email address (case-insensitive matched via lower() in pending unique idx)';
COMMENT ON COLUMN project_sharing.project_shares.role IS 'Permission level: viewer | editor | owner';
COMMENT ON COLUMN project_sharing.project_shares.invite_token IS 'URL-safe 22-char base62 token (128 bits entropy). Nulled on revoke.';
COMMENT ON COLUMN project_sharing.project_shares.status IS 'Lifecycle: pending → accepted | revoked';
COMMENT ON COLUMN project_sharing.project_shares.accepted_at IS 'Set when status flips to accepted';
COMMENT ON COLUMN project_sharing.project_shares.revoked_at IS 'Set when status flips to revoked';
