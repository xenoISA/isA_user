"""Initial auth service schema

Revision ID: auth_001
Revises: None
Create Date: 2025-01-20

Wraps existing SQL migrations:
  - 001_create_users_table.sql
  - 002_create_organizations_table.sql
  - 003_create_devices_table.sql
  - 004_create_pairing_tokens_table.sql
  - 005_add_password_hash.sql
  - 006_create_oauth_clients_table.sql
"""
from typing import Sequence, Union

from alembic import op

revision: str = "auth_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS auth")

    # 001: users table
    op.execute("""
        CREATE TABLE IF NOT EXISTS auth.users (
            user_id VARCHAR(255) PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            password_hash VARCHAR(255),
            email_verified BOOLEAN DEFAULT FALSE,
            last_login TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON auth.users(email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_is_active ON auth.users(is_active)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email_verified ON auth.users(email, email_verified)")

    # 002: organizations table
    op.execute("""
        CREATE TABLE IF NOT EXISTS auth.organizations (
            organization_id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            api_keys JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_organizations_name ON auth.organizations(name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_organizations_api_keys ON auth.organizations USING GIN(api_keys)")

    # 003: devices and device_logs tables
    op.execute("""
        CREATE TABLE IF NOT EXISTS auth.devices (
            device_id VARCHAR(255) PRIMARY KEY,
            device_secret VARCHAR(255) NOT NULL,
            organization_id VARCHAR(255) NOT NULL,
            device_name VARCHAR(255),
            device_type VARCHAR(50),
            status VARCHAR(20) DEFAULT 'active',
            last_authenticated_at TIMESTAMPTZ,
            authentication_count INTEGER DEFAULT 0,
            metadata JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            expires_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_devices_org ON auth.devices(organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_devices_status ON auth.devices(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_devices_type ON auth.devices(device_type)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS auth.device_logs (
            id SERIAL PRIMARY KEY,
            device_id VARCHAR(255) NOT NULL,
            auth_status VARCHAR(20) NOT NULL,
            ip_address VARCHAR(45),
            user_agent TEXT,
            error_message TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_device_logs_device ON auth.device_logs(device_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_device_logs_created ON auth.device_logs(created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_device_logs_status ON auth.device_logs(auth_status)")

    # 004: device_pairing_tokens table
    op.execute("""
        CREATE TABLE IF NOT EXISTS auth.device_pairing_tokens (
            id SERIAL PRIMARY KEY,
            device_id VARCHAR(255) NOT NULL,
            pairing_token VARCHAR(255) NOT NULL UNIQUE,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used BOOLEAN DEFAULT FALSE,
            used_at TIMESTAMP,
            user_id VARCHAR(255)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_pairing_token ON auth.device_pairing_tokens(pairing_token)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_device_id ON auth.device_pairing_tokens(device_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON auth.device_pairing_tokens(expires_at)")

    # 006: oauth_clients table
    op.execute("""
        CREATE TABLE IF NOT EXISTS auth.oauth_clients (
            client_id TEXT PRIMARY KEY,
            client_secret_hash TEXT NOT NULL,
            client_name TEXT NOT NULL,
            organization_id TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            allowed_scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
            token_ttl_seconds INTEGER NOT NULL DEFAULT 3600,
            created_by TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_used_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_oauth_clients_org ON auth.oauth_clients(organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_oauth_clients_active ON auth.oauth_clients(is_active)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS auth.oauth_clients CASCADE")
    op.execute("DROP TABLE IF EXISTS auth.device_pairing_tokens CASCADE")
    op.execute("DROP TABLE IF EXISTS auth.device_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS auth.devices CASCADE")
    op.execute("DROP TABLE IF EXISTS auth.organizations CASCADE")
    op.execute("DROP TABLE IF EXISTS auth.users CASCADE")
    op.execute("DROP SCHEMA IF EXISTS auth CASCADE")
