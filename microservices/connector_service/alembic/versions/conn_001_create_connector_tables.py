"""Create connector schema + connector / custom_mcp_connector tables.

Revision ID: conn_001
Revises: None
Create Date: 2026-05-19

Backend slice of xenoISA/isA_#464 — owns the marketplace connector
state plus the user-added remote MCP rows.

Schema layout
-------------
``connector`` (schema)
  - ``connector`` (table) — built-in catalog install state per user
  - ``custom_mcp_connector`` (table) — user-added remote MCP servers

Notes
-----
* No FK to ``users`` — user_id lives in account_service in another
  schema, so cross-service FKs are deliberately avoided. user_id is
  text (matching account_service) and indexed.
* Both tables use ``CREATE TABLE IF NOT EXISTS`` so re-applying the
  revision is a no-op on healthy databases (PR #476 pattern).
* ``custom_mcp_connector.auth_kind`` and ``.status`` are plain VARCHAR
  with CHECK constraints rather than Postgres ENUMs — adding new
  variants later (e.g. ``oauth_pkce``) is a simple CHECK swap; ENUM
  evolution is much fussier.
* ``unique(user_id, url)`` enforces idempotent re-registration: posting
  the same URL twice returns the existing row instead of duplicating.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "conn_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS connector")

    # ------------------------------------------------------------------
    # connector.connector — per-user install state for built-in catalog
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS connector.connector (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         VARCHAR(128) NOT NULL,
            connector_id    VARCHAR(100) NOT NULL,
            status          VARCHAR(30)  NOT NULL DEFAULT 'disconnected',
            scopes          JSONB        NOT NULL DEFAULT '[]'::jsonb,
            installed_at    TIMESTAMPTZ  NULL,
            last_synced_at  TIMESTAMPTZ  NULL,
            metadata        JSONB        NOT NULL DEFAULT '{}'::jsonb,
            error_code      VARCHAR(100) NULL,
            error_message   TEXT         NULL,
            auth_url        TEXT         NULL,
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                 WHERE conname = 'uq_connector_user_connector'
            ) THEN
                ALTER TABLE connector.connector
                  ADD CONSTRAINT uq_connector_user_connector
                  UNIQUE (user_id, connector_id);
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                 WHERE conname = 'ck_connector_status'
            ) THEN
                ALTER TABLE connector.connector
                  ADD CONSTRAINT ck_connector_status
                  CHECK (status IN ('connected', 'pending_auth', 'error', 'disconnected'));
            END IF;
        END$$;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_connector_user_status ON connector.connector(user_id, status)"
    )

    # ------------------------------------------------------------------
    # connector.custom_mcp_connector — user-added remote MCP servers
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS connector.custom_mcp_connector (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id             VARCHAR(128) NOT NULL,
            label               VARCHAR(120) NOT NULL,
            url                 TEXT         NOT NULL,
            auth_kind           VARCHAR(30)  NOT NULL DEFAULT 'none',
            auth_secret_ref     TEXT         NULL,
            status              VARCHAR(30)  NOT NULL DEFAULT 'pending',
            last_error          TEXT         NULL,
            tools_count         INTEGER      NULL,
            created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            last_validated_at   TIMESTAMPTZ  NULL,
            last_handshake_at   TIMESTAMPTZ  NULL
        )
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                 WHERE conname = 'uq_custom_mcp_user_url'
            ) THEN
                ALTER TABLE connector.custom_mcp_connector
                  ADD CONSTRAINT uq_custom_mcp_user_url
                  UNIQUE (user_id, url);
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                 WHERE conname = 'ck_custom_mcp_auth_kind'
            ) THEN
                ALTER TABLE connector.custom_mcp_connector
                  ADD CONSTRAINT ck_custom_mcp_auth_kind
                  CHECK (auth_kind IN ('none', 'pat', 'oauth_oob'));
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                 WHERE conname = 'ck_custom_mcp_status'
            ) THEN
                ALTER TABLE connector.custom_mcp_connector
                  ADD CONSTRAINT ck_custom_mcp_status
                  CHECK (status IN ('pending', 'active', 'error', 'revoked'));
            END IF;
        END$$;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_custom_mcp_user_status ON connector.custom_mcp_connector(user_id, status)"
    )

    # ------------------------------------------------------------------
    # Comments — schema documentation that survives in pg_catalog.
    # ------------------------------------------------------------------
    op.execute(
        "COMMENT ON TABLE connector.connector IS "
        "'Per-user install state for built-in catalog connectors (xenoISA/isA_#464).'"
    )
    op.execute(
        "COMMENT ON TABLE connector.custom_mcp_connector IS "
        "'User-added remote MCP servers (BYO MCP). Auth secrets live in vault, "
        "only the opaque ref is stored here.'"
    )
    op.execute(
        "COMMENT ON COLUMN connector.custom_mcp_connector.auth_secret_ref IS "
        "'Opaque ref returned by the vault. dev_vault stub uses devvault:<user>:<rand>.'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS connector.custom_mcp_connector CASCADE")
    op.execute("DROP TABLE IF EXISTS connector.connector CASCADE")
    op.execute("DROP SCHEMA IF EXISTS connector CASCADE")
