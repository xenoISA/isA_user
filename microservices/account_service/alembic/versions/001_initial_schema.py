"""Initial account service schema

Revision ID: acct_001
Revises: None
Create Date: 2025-01-24

Wraps existing SQL migrations:
  - 001_create_users_table.sql
  - 002_remove_subscription_status.sql
"""
from typing import Sequence, Union

from alembic import op

revision: str = "acct_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS account")

    op.execute("""
        CREATE TABLE IF NOT EXISTS account.users (
            user_id VARCHAR(255) PRIMARY KEY,
            email VARCHAR(255),
            name VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            preferences JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON account.users(email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_is_active ON account.users(is_active)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_preferences ON account.users USING GIN(preferences)")

    op.execute(
        "COMMENT ON TABLE account.users IS "
        "'User account profiles - identity anchor only. "
        "Subscription data managed by subscription_service.'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS account.users CASCADE")
    op.execute("DROP SCHEMA IF EXISTS account CASCADE")
