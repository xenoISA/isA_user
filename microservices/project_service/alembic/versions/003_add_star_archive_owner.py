"""Add star/archive/owner columns to project.projects

Revision ID: proj_003
Revises: proj_002
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 003_add_star_archive_owner.sql

Adds owner_id, starred_at, archived_at and supporting indexes. The
owner_id column is added with DEFAULT '' so existing rows satisfy the
NOT NULL constraint. Migration 004 backfills owner_id from user_id and
removes the empty-string default.

See story #442 (paired with xenoISA/isA_#429 §15.3 / §15.6).
"""

from typing import Sequence, Union

from alembic import op

revision: str = "proj_003"
down_revision: Union[str, None] = "proj_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # owner_id — defaults to '' so existing rows satisfy NOT NULL.
    # Migration 004 backfills from user_id and drops the default.
    op.execute("ALTER TABLE project.projects ADD COLUMN IF NOT EXISTS owner_id TEXT NOT NULL DEFAULT ''")

    # starred_at / archived_at — null by default.
    op.execute("ALTER TABLE project.projects ADD COLUMN IF NOT EXISTS starred_at TIMESTAMPTZ NULL")
    op.execute("ALTER TABLE project.projects ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ NULL")

    # Partial index — hot path: list-by-owner that hides archived rows.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_project_projects_owner_active "
        "ON project.projects (owner_id) WHERE archived_at IS NULL"
    )
    # Partial index — starred subset (most users keep a small starred set).
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_project_projects_starred "
        "ON project.projects (starred_at) WHERE starred_at IS NOT NULL"
    )
    # Helper index for include_archived=true paths.
    op.execute("CREATE INDEX IF NOT EXISTS idx_project_projects_owner_id ON project.projects (owner_id)")

    op.execute(
        "COMMENT ON COLUMN project.projects.owner_id IS "
        "'Effective owner - drives access checks and list scoping. "
        "Defaults to empty for legacy rows; back-fill from user_id.'"
    )
    op.execute(
        "COMMENT ON COLUMN project.projects.starred_at IS "
        "'Star pin timestamp. NULL = not starred. See xenoISA/isA_#429 §15.3.'"
    )
    op.execute(
        "COMMENT ON COLUMN project.projects.archived_at IS "
        "'Archive timestamp. NULL = active. Archived projects are hidden "
        "from default list and all shares are revoked. See #429 §15.6.'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS project.idx_project_projects_owner_id")
    op.execute("DROP INDEX IF EXISTS project.idx_project_projects_starred")
    op.execute("DROP INDEX IF EXISTS project.idx_project_projects_owner_active")
    op.execute("ALTER TABLE project.projects DROP COLUMN IF EXISTS archived_at")
    op.execute("ALTER TABLE project.projects DROP COLUMN IF EXISTS starred_at")
    op.execute("ALTER TABLE project.projects DROP COLUMN IF EXISTS owner_id")
