"""Assert NOT NULL on project.projects.owner_id (defensive backfill + declarative constraint)

Revision ID: proj_005
Revises: proj_004
Create Date: 2026-05-19

Closes item #5 of xenoISA/isA_#452 epic — the production-readiness story
asked for a backfill migration that makes a future NOT NULL constraint on
``projects.owner_id`` possible.

History
-------
- ``proj_003`` added ``owner_id TEXT NOT NULL DEFAULT ''`` so existing rows
  satisfied NOT NULL at column-add time via the empty-string sentinel.
- ``proj_004`` backfilled ``owner_id`` from ``user_id`` (project_service's
  creator column — see ``project_repository.create_project``: effective
  owner = ``owner_id or user_id``), dropped the legacy ``DEFAULT ''``,
  and added ``CHECK (owner_id <> '')`` to reject empty owners going
  forward.

What this revision adds
-----------------------
1. **Defensive re-backfill**: copy ``user_id`` into ``owner_id`` wherever
   ``owner_id`` is empty or NULL. Idempotent — only touches rows that
   need it. Catches the edge case where a row could in theory slip in
   between ``proj_004`` and the CHECK constraint becoming visible to
   long-running connections (zero rows in practice; this is belt-and-
   braces).

2. **Declarative NOT NULL via** ``op.alter_column``: the column is
   already NOT NULL at the DB level (since ``proj_003``), but until now
   the Alembic revision history declared it only implicitly through
   raw DDL. Re-asserting via ``op.alter_column(..., nullable=False)``
   makes the invariant explicit in the migration registry and is a
   no-op on databases where the column is already NOT NULL.

Why no column-type change
-------------------------
The column is ``TEXT`` (from ``proj_003``). The empty-string sentinel
is fully neutralised by ``proj_004``'s CHECK constraint, so converting
to ``VARCHAR(255)`` or to a different NULL semantic would be a behaviour
change, not a backfill, and is intentionally out of scope.

Why downgrade is a no-op
------------------------
The backfilled values are correct — there is no way to distinguish a
``user_id``-backfilled ``owner_id`` from one that was set explicitly.
The NOT NULL constraint was already present before this revision, so
flipping ``nullable=True`` on downgrade would *weaken* the schema
relative to the post-``proj_003`` shape — explicitly the wrong thing
to do. Downgrade is therefore intentionally empty (with a comment).
"""

from typing import Sequence, Union

from alembic import op

revision: str = "proj_005"
down_revision: Union[str, None] = "proj_004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Defensive re-backfill from user_id. Idempotent — only updates
    #    rows where owner_id is empty/NULL. The CHECK constraint from
    #    proj_004 means this is a no-op on properly-migrated databases,
    #    but we run it anyway in case a row slipped in (e.g. via a
    #    long-lived connection that beat the CHECK to the table).
    op.execute(
        """
        UPDATE project.projects
           SET owner_id = COALESCE(NULLIF(user_id, ''), owner_id)
         WHERE owner_id = '' OR owner_id IS NULL
        """
    )

    # 2. Declarative NOT NULL. The column has been NOT NULL since
    #    proj_003 (via "TEXT NOT NULL DEFAULT ''"), but stating it
    #    here via op.alter_column documents the invariant in the
    #    Alembic registry. Idempotent — Postgres treats a SET NOT NULL
    #    on an already-NOT-NULL column as a no-op (modulo a table-
    #    scan validation pass which is cheap on this table).
    op.alter_column(
        "projects",
        "owner_id",
        nullable=False,
        schema="project",
    )


def downgrade() -> None:
    # Intentional no-op.
    #
    # - The backfill is not reversible: there is no signal to
    #   distinguish backfilled owner_id values from ones that were
    #   set explicitly at insert time.
    # - The NOT NULL constraint pre-dates this revision (it was set
    #   in proj_003). Dropping it here would weaken the schema below
    #   the post-proj_003 baseline, which is the wrong direction
    #   for a downgrade of THIS revision.
    pass
