"""Create artifact.artifact_mcp_grants table

Revision ID: art_003
Revises: art_002
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 003_create_mcp_grants.sql

Phase 3 of xenoISA/isA_user#441. Persists per-(artifact, user, tool,
server, scope) MCP approvals. Only `always`-scoped allow grants are
de-duped via partial unique index; `once`/`session` may repeat across
sessions; `deny` rows are advisory.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "art_003"
down_revision: Union[str, None] = "art_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS artifact.artifact_mcp_grants (
            id           VARCHAR(255) PRIMARY KEY,
            artifact_id  VARCHAR(255) NOT NULL
                         REFERENCES artifact.artifacts(id) ON DELETE CASCADE,
            user_id      VARCHAR(255) NOT NULL,
            tool_name    VARCHAR(255) NOT NULL,
            server_id    VARCHAR(255) NOT NULL,
            decision     VARCHAR(8)   NOT NULL CHECK (decision IN ('allow', 'deny')),
            scope        VARCHAR(8)   NOT NULL CHECK (scope IN ('once', 'session', 'always')),
            approved_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            expires_at   TIMESTAMPTZ,
            last_used_at TIMESTAMPTZ,
            created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """
    )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_artifact_mcp_grants_always "
        "ON artifact.artifact_mcp_grants "
        "(artifact_id, user_id, tool_name, server_id) "
        "WHERE decision = 'allow' AND scope = 'always'"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_artifact_mcp_grants_lookup "
        "ON artifact.artifact_mcp_grants "
        "(artifact_id, user_id, tool_name, server_id)"
    )

    op.execute(
        "COMMENT ON TABLE artifact.artifact_mcp_grants IS "
        "'Per-(artifact,user,tool) MCP approval persistence - gates artifact MCP calls (#441 Phase 3)'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS artifact.artifact_mcp_grants CASCADE")
