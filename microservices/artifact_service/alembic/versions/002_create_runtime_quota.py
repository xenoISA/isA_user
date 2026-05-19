"""Create artifact.artifact_runtime_usage table

Revision ID: art_002
Revises: art_001
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 002_create_runtime_quota.sql

Phase 3 of xenoISA/isA_user#441. One row per
(artifact, user, UTC day_bucket) — incremented by the runtime invoke
path and read by the quota check (counts `calls` for today's bucket).
"""

from typing import Sequence, Union

from alembic import op

revision: str = "art_002"
down_revision: Union[str, None] = "art_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS artifact.artifact_runtime_usage (
            artifact_id VARCHAR(255) NOT NULL
                        REFERENCES artifact.artifacts(id) ON DELETE CASCADE,
            user_id     VARCHAR(255) NOT NULL,
            day_bucket  DATE         NOT NULL,
            tokens_in   BIGINT       NOT NULL DEFAULT 0,
            tokens_out  BIGINT       NOT NULL DEFAULT 0,
            calls       INTEGER      NOT NULL DEFAULT 0,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            PRIMARY KEY (artifact_id, user_id, day_bucket)
        )
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_artifact_runtime_usage_user_day "
        "ON artifact.artifact_runtime_usage (user_id, day_bucket DESC)"
    )

    op.execute(
        "COMMENT ON TABLE artifact.artifact_runtime_usage IS "
        "'Per-(artifact,user,UTC-day) AI runtime usage counter - drives quota 429s (#441 Phase 3)'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS artifact.artifact_runtime_usage CASCADE")
