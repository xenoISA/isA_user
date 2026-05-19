"""Initialize memory schema and shared trigger function

Revision ID: mem_000
Revises: None
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 000_init_schema.sql

Creates the `memory` schema and the shared `memory.update_updated_at()`
trigger helper that every subsequent table-creation revision attaches.

Architecture note (per the original SQL header):
  - PostgreSQL stores structured memory data only.
  - Vector embeddings live in Qdrant.
  - user_id has no FK to any other service — this is intentional under
    the microservices "no cross-service FKs" rule.

Safe to apply on environments where the schema already exists.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "mem_000"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS memory")

    op.execute("""
        CREATE OR REPLACE FUNCTION memory.update_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    op.execute(
        "COMMENT ON SCHEMA memory IS "
        "'Memory service schema for AI-powered intelligent memory storage "
        "(PostgreSQL + Qdrant architecture)'"
    )
    op.execute(
        "COMMENT ON FUNCTION memory.update_updated_at() IS "
        "'Trigger function to automatically update updated_at timestamp'"
    )


def downgrade() -> None:
    # Drop the schema with CASCADE — this also removes the trigger fn.
    # Tables created by later revisions are removed by their own downgrade,
    # but CASCADE keeps the downgrade robust if state has drifted.
    op.execute("DROP SCHEMA IF EXISTS memory CASCADE")
