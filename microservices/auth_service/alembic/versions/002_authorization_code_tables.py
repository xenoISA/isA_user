"""Add authorization_codes and client_metadata tables

Revision ID: auth_002
Revises: auth_001
Create Date: 2026-03-26

New tables:
  - auth.oauth_authorization_codes — Authorization code flow (PKCE, TTL, single-use)
  - auth.oauth_client_metadata — CIMD cache for dynamic client registration

Altered tables:
  - auth.oauth_clients — Add client_type, redirect_uris, require_pkce, metadata_document_url
"""
from typing import Sequence, Union

from alembic import op

revision: str = "auth_002"
down_revision: Union[str, None] = "auth_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- oauth_authorization_codes table ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS auth.oauth_authorization_codes (
            code_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id TEXT NOT NULL,
            redirect_uri TEXT NOT NULL,
            state TEXT NOT NULL,
            resource TEXT,
            scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
            approved_scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
            user_id TEXT NOT NULL,
            organization_id TEXT,
            code_challenge TEXT,
            code_challenge_method VARCHAR(10),
            code_value TEXT NOT NULL UNIQUE,
            is_used BOOLEAN DEFAULT FALSE,
            used_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT chk_code_expiry CHECK (expires_at > created_at)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_oauth_codes_client ON auth.oauth_authorization_codes(client_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_oauth_codes_user ON auth.oauth_authorization_codes(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_oauth_codes_expires ON auth.oauth_authorization_codes(expires_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_oauth_codes_value ON auth.oauth_authorization_codes(code_value)")

    # --- oauth_client_metadata table (CIMD cache) ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS auth.oauth_client_metadata (
            client_id TEXT PRIMARY KEY,
            metadata_document_url TEXT UNIQUE NOT NULL,
            metadata JSONB NOT NULL,
            client_type VARCHAR(20),
            redirect_uris JSONB,
            client_name TEXT,
            cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ,
            etag TEXT,
            is_valid BOOLEAN DEFAULT TRUE,
            validation_error TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_client_metadata_url ON auth.oauth_client_metadata(metadata_document_url)")

    # --- ALTER existing oauth_clients table ---
    op.execute("ALTER TABLE auth.oauth_clients ADD COLUMN IF NOT EXISTS client_type VARCHAR(20) DEFAULT 'confidential'")
    op.execute("ALTER TABLE auth.oauth_clients ADD COLUMN IF NOT EXISTS redirect_uris JSONB DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE auth.oauth_clients ADD COLUMN IF NOT EXISTS require_pkce BOOLEAN DEFAULT TRUE")
    op.execute("ALTER TABLE auth.oauth_clients ADD COLUMN IF NOT EXISTS metadata_document_url TEXT")


def downgrade() -> None:
    # Remove added columns from oauth_clients
    op.execute("ALTER TABLE auth.oauth_clients DROP COLUMN IF EXISTS metadata_document_url")
    op.execute("ALTER TABLE auth.oauth_clients DROP COLUMN IF EXISTS require_pkce")
    op.execute("ALTER TABLE auth.oauth_clients DROP COLUMN IF EXISTS redirect_uris")
    op.execute("ALTER TABLE auth.oauth_clients DROP COLUMN IF EXISTS client_type")

    # Drop new tables
    op.execute("DROP TABLE IF EXISTS auth.oauth_client_metadata CASCADE")
    op.execute("DROP TABLE IF EXISTS auth.oauth_authorization_codes CASCADE")
