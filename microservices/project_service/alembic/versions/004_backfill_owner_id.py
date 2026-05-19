"""Backfill owner_id from user_id and tighten constraint

Revision ID: proj_004
Revises: proj_003
Create Date: 2026-05-19

Wraps SQL migration:
  - 004_backfill_owner_id.sql

Closes the data gap left by migration 003 which added owner_id with
DEFAULT '' so existing rows could satisfy NOT NULL. This revision:

  1. Backfills owner_id from user_id wherever owner_id is empty.
     The project_service treats user_id as the creator column
     (see project_repository.create_project:
       effective_owner = owner_id or user_id).
  2. Drops the legacy DEFAULT '' so future inserts must specify owner_id.
  3. Adds a CHECK constraint rejecting empty owner_id values.

Idempotent: only updates empty rows; constraint creation is guarded.

Closes xenoISA/isA_user#463 (paired with isA_#452 epic).
"""

from typing import Sequence, Union

from alembic import op

revision: str = "proj_004"
down_revision: Union[str, None] = "proj_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Backfill from user_id (the project_service creator column).
    #    Only touches rows where owner_id is empty/null, so it's a no-op
    #    on environments that have no legacy rows.
    op.execute("""
        UPDATE project.projects
           SET owner_id = COALESCE(NULLIF(user_id, ''), '')
         WHERE owner_id = '' OR owner_id IS NULL
    """)

    # 2. Drop the legacy default — new rows must specify owner_id explicitly.
    op.execute("ALTER TABLE project.projects ALTER COLUMN owner_id DROP DEFAULT")

    # 3. CHECK constraint: reject empty owner_id going forward.
    #    Guarded so re-running the migration is a no-op.
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                 WHERE conname = 'chk_project_projects_owner_id_nonempty'
            ) THEN
                ALTER TABLE project.projects
                    ADD CONSTRAINT chk_project_projects_owner_id_nonempty
                    CHECK (owner_id <> '');
            END IF;
        END$$;
    """)


def downgrade() -> None:
    # Drop the CHECK constraint.
    op.execute("ALTER TABLE project.projects DROP CONSTRAINT IF EXISTS chk_project_projects_owner_id_nonempty")
    # Restore the legacy default so the schema matches the post-003 state.
    op.execute("ALTER TABLE project.projects ALTER COLUMN owner_id SET DEFAULT ''")
    # We intentionally do NOT un-backfill owner_id — the backfilled values
    # remain valid and there is no signal to distinguish backfilled rows.
