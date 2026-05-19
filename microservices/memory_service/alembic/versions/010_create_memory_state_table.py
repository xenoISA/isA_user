"""Create memory.user_memory_state table

Revision ID: mem_010
Revises: mem_009
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 010_create_memory_state_table.sql

Per-user memory pipeline toggles for xenoISA/isA_#428 Phase 2
(paired with xenoISA/isA_user#439):
  - paused / paused_at — hide memory write confirmations / skip synth.
  - last_synthesis_at — staleness badge for summary panel.
  - last_reset_at — audit trail for the destructive RESET action.

Single row per user; upserted via INSERT ... ON CONFLICT DO UPDATE.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "mem_010"
down_revision: Union[str, None] = "mem_009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS memory.user_memory_state (
            user_id VARCHAR(255) PRIMARY KEY,
            paused BOOLEAN NOT NULL DEFAULT false,
            paused_at TIMESTAMPTZ,
            last_synthesis_at TIMESTAMPTZ,
            last_reset_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_memory_state_paused "
        "ON memory.user_memory_state (paused) WHERE paused = true"
    )

    op.execute(
        "COMMENT ON TABLE memory.user_memory_state IS "
        "'Per-user toggles for memory pipeline: pause/resume + reset audit + "
        "synthesis freshness (xenoISA/isA_#428 / xenoISA/isA_user#439)'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memory.user_memory_state CASCADE")
