"""Create project_sharing schema + project_shares table

Revision ID: psharing_001
Revises: None
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 001_create_project_shares_table.sql

Issue: xenoISA/isA_user#442 (paired with xenoISA/isA_#429 §3).

Notes:
  * No FK to projects(id) — projects live in project_service in a
    different schema/service, so cross-service FKs are deliberately
    avoided. project_id is indexed instead.
  * The partial unique index on (project_id, lower(invitee_email))
    WHERE status='pending' enforces invite idempotency: re-inviting the
    same email while one is still pending returns the existing row
    rather than creating duplicates. Revoked/accepted rows may coexist.
  * Postgres has no IF NOT EXISTS for CREATE TYPE, so the enums are
    created via DO blocks that check pg_type first — re-applying is a
    no-op.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "psharing_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS project_sharing")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'project_share_role') THEN
                CREATE TYPE project_sharing.project_share_role
                    AS ENUM ('viewer', 'editor', 'owner');
            END IF;
        END$$;
    """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'project_share_status') THEN
                CREATE TYPE project_sharing.project_share_status
                    AS ENUM ('pending', 'accepted', 'revoked');
            END IF;
        END$$;
    """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_sharing.project_shares (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id      UUID NOT NULL,
            invitee_user_id VARCHAR(255) NULL,
            invitee_email   VARCHAR(320) NOT NULL,
            role            project_sharing.project_share_role NOT NULL DEFAULT 'viewer',
            invite_token    VARCHAR(32) UNIQUE,
            status          project_sharing.project_share_status NOT NULL DEFAULT 'pending',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            accepted_at     TIMESTAMPTZ NULL,
            revoked_at      TIMESTAMPTZ NULL
        )
    """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_project_shares_project_id ON project_sharing.project_shares(project_id)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_project_shares_invite_token "
        "ON project_sharing.project_shares(invite_token) "
        "WHERE invite_token IS NOT NULL"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_project_shares_invitee_user_id "
        "ON project_sharing.project_shares(invitee_user_id) "
        "WHERE invitee_user_id IS NOT NULL"
    )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_project_shares_pending_email "
        "ON project_sharing.project_shares(project_id, lower(invitee_email)) "
        "WHERE status = 'pending'"
    )

    op.execute(
        "COMMENT ON TABLE project_sharing.project_shares IS "
        "'Project-level invitations and memberships. Token-based accept flow.'"
    )
    op.execute(
        "COMMENT ON COLUMN project_sharing.project_shares.id IS 'Share record UUID (server-assigned)'"
    )
    op.execute(
        "COMMENT ON COLUMN project_sharing.project_shares.project_id IS "
        "'Project being shared (FK enforced by project_service, not DB-level)'"
    )
    op.execute(
        "COMMENT ON COLUMN project_sharing.project_shares.invitee_user_id IS "
        "'User id once the invitee accepts; NULL before accept'"
    )
    op.execute(
        "COMMENT ON COLUMN project_sharing.project_shares.invitee_email IS "
        "'Invitee email address (case-insensitive matched via lower() in pending unique idx)'"
    )
    op.execute(
        "COMMENT ON COLUMN project_sharing.project_shares.role IS 'Permission level: viewer | editor | owner'"
    )
    op.execute(
        "COMMENT ON COLUMN project_sharing.project_shares.invite_token IS "
        "'URL-safe 22-char base62 token (128 bits entropy). Nulled on revoke.'"
    )
    op.execute(
        "COMMENT ON COLUMN project_sharing.project_shares.status IS 'Lifecycle: pending -> accepted | revoked'"
    )
    op.execute(
        "COMMENT ON COLUMN project_sharing.project_shares.accepted_at IS 'Set when status flips to accepted'"
    )
    op.execute(
        "COMMENT ON COLUMN project_sharing.project_shares.revoked_at IS 'Set when status flips to revoked'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS project_sharing.project_shares CASCADE")
    op.execute("DROP TYPE IF EXISTS project_sharing.project_share_status")
    op.execute("DROP TYPE IF EXISTS project_sharing.project_share_role")
    op.execute("DROP SCHEMA IF EXISTS project_sharing CASCADE")
