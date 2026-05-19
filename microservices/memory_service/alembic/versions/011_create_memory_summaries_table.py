"""Create memory.memory_summaries table

Revision ID: mem_011
Revises: mem_010
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 011_create_memory_summaries_table.sql

Synthesized narrative summaries for xenoISA/isA_#428 Phase 2 hard slice
(xenoISA/isA_user#439). One row per (user_id, scope, scope_id) with
scope ∈ {'user', 'project'}. version bumps on regenerate or edit so the
frontend can detect drift; edited_at is set ONLY on user PUT.
"""

from typing import Sequence, Union

import sqlalchemy as sa  # noqa: F401  used by op.execute(sa.text(...)) below
from alembic import op

revision: str = "mem_011"
down_revision: Union[str, None] = "mem_010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # sa.text(...) is used here because the JSON default literal contains
    # un-quoted colons (`"sessions":0`) and alembic's op.execute compiles
    # bare strings through SQLAlchemy's bind-parameter machinery — which
    # would otherwise reinterpret `:0` as a positional bind and crash with
    # "A value is required for bind parameter '0'". Wrapping in sa.text
    # plus the literal `\:` escape disables that pass.
    op.execute(
        sa.text(
            r"""
        CREATE TABLE IF NOT EXISTS memory.memory_summaries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id VARCHAR(255) NOT NULL,
            scope VARCHAR(32) NOT NULL CHECK (scope IN ('user', 'project')),
            scope_id VARCHAR(255) NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            highlights JSONB NOT NULL DEFAULT '[]'::jsonb,
            version INT NOT NULL DEFAULT 1,
            generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            edited_at TIMESTAMPTZ,
            source_counts JSONB NOT NULL DEFAULT
                '{"sessions"\:0,"turns"\:0,"memories"\:0}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_memory_summaries_scope UNIQUE (user_id, scope, scope_id)
        )
    """
        )
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_memory_summaries_user ON memory.memory_summaries (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_memory_summaries_scope_lookup "
        "ON memory.memory_summaries (user_id, scope, scope_id)"
    )

    op.execute(
        "COMMENT ON TABLE memory.memory_summaries IS "
        "'Synthesized narrative summaries for user/project memory "
        "(xenoISA/isA_#428 / xenoISA/isA_user#439 hard slice). One row per "
        "(user_id, scope, scope_id) - bump version on regenerate or edit.'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memory.memory_summaries CASCADE")
