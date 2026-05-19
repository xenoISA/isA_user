"""Create artifact.artifact_kv table

Revision ID: art_004
Revises: art_003
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 004_create_artifact_kv.sql

Phase 3 of xenoISA/isA_user#441. Per-artifact namespaced KV with
two scopes:
  - personal — per-user namespace; user_id required, persisted verbatim.
  - shared   — single namespace per artifact; user_id MUST be the
               '_shared' sentinel so a single PK column list covers both
               scopes (Postgres disallows expressions like COALESCE in
               PRIMARY KEY columns).

CHECK constraint pins the sentinel to scope='shared'; the service layer
rewrites user_id <-> '_shared' on the boundary so the HTTP contract
stays clean.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "art_004"
down_revision: Union[str, None] = "art_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS artifact.artifact_kv (
            artifact_id VARCHAR(255) NOT NULL
                        REFERENCES artifact.artifacts(id) ON DELETE CASCADE,
            scope       VARCHAR(16)  NOT NULL CHECK (scope IN ('personal', 'shared')),
            user_id     VARCHAR(255) NOT NULL,
            key         VARCHAR(500) NOT NULL,
            value       JSONB        NOT NULL,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            PRIMARY KEY (artifact_id, scope, user_id, key),
            CHECK (
                (scope = 'personal' AND user_id <> '_shared')
                OR
                (scope = 'shared'   AND user_id =  '_shared')
            )
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_artifact_kv_lookup ON artifact.artifact_kv (artifact_id, scope)")

    op.execute(
        "COMMENT ON TABLE artifact.artifact_kv IS "
        "'Per-artifact namespaced key/value storage (#441 Phase 3) - "
        "personal scope is per-user, shared scope uses ''_shared'' sentinel'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS artifact.artifact_kv CASCADE")
