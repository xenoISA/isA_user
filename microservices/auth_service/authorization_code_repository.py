"""
Authorization Code Repository

Persistence layer for OAuth2 authorization codes used by the auth code + PKCE flow.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class AuthorizationCodeRepository:
    """Data access for OAuth2 authorization codes (authorization_code grant)."""

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("auth_service")

        host, port = config.discover_service(
            service_name='postgres_service',
            default_host='localhost',
            default_port=5432,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port} for authorization codes")
        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            database=os.getenv("POSTGRES_DB", "isa_platform"),
            username=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            user_id='auth-service',
            min_pool_size=1,
            max_pool_size=2,
        )
        self.schema = "auth"
        self.table = "oauth_authorization_codes"
        self._table_initialized = False

    async def _ensure_table(self) -> None:
        """Create authorization codes table if missing."""
        if self._table_initialized:
            return

        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.schema}.{self.table} (
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
        """

        async with self.db:
            await self.db.execute(create_sql)
            await self.db.execute(
                f"CREATE INDEX IF NOT EXISTS idx_oauth_codes_client ON {self.schema}.{self.table}(client_id)"
            )
            await self.db.execute(
                f"CREATE INDEX IF NOT EXISTS idx_oauth_codes_user ON {self.schema}.{self.table}(user_id)"
            )
            await self.db.execute(
                f"CREATE INDEX IF NOT EXISTS idx_oauth_codes_expires ON {self.schema}.{self.table}(expires_at)"
            )
            await self.db.execute(
                f"CREATE INDEX IF NOT EXISTS idx_oauth_codes_value ON {self.schema}.{self.table}(code_value)"
            )

        self._table_initialized = True

    async def create_code(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        state: str,
        resource: Optional[str],
        scopes: List[str],
        user_id: str,
        organization_id: Optional[str],
        code_challenge: Optional[str],
        code_challenge_method: Optional[str],
        code_value: str,
        expires_at: datetime,
        approved_scopes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Insert a new authorization code and return the created record."""
        await self._ensure_table()

        now = datetime.now(timezone.utc)
        if approved_scopes is None:
            approved_scopes = scopes

        query = f"""
            INSERT INTO {self.schema}.{self.table}
            (client_id, redirect_uri, state, resource, scopes, approved_scopes,
             user_id, organization_id, code_challenge, code_challenge_method,
             code_value, created_at, expires_at)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7, $8, $9, $10, $11, $12, $13)
            RETURNING code_id
        """

        async with self.db:
            row = await self.db.query_row(
                query,
                params=[
                    client_id,
                    redirect_uri,
                    state,
                    resource,
                    scopes,
                    approved_scopes,
                    user_id,
                    organization_id,
                    code_challenge,
                    code_challenge_method,
                    code_value,
                    now,
                    expires_at,
                ],
            )

        code_id = row.get("code_id") if row else None

        return {
            "code_id": str(code_id) if code_id else None,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "resource": resource,
            "scopes": scopes,
            "approved_scopes": approved_scopes,
            "user_id": user_id,
            "organization_id": organization_id,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "code_value": code_value,
            "is_used": False,
            "created_at": now,
            "expires_at": expires_at,
        }

    async def get_code(self, code_value: str) -> Optional[Dict[str, Any]]:
        """Get authorization code by its value."""
        await self._ensure_table()

        query = f"""
            SELECT code_id, client_id, redirect_uri, state, resource,
                   scopes, approved_scopes, user_id, organization_id,
                   code_challenge, code_challenge_method, code_value,
                   is_used, used_at, created_at, expires_at
            FROM {self.schema}.{self.table}
            WHERE code_value = $1
        """

        async with self.db:
            row = await self.db.query_row(query, params=[code_value])

        if not row:
            return None

        return {
            "code_id": str(row.get("code_id")),
            "client_id": row.get("client_id"),
            "redirect_uri": row.get("redirect_uri"),
            "state": row.get("state"),
            "resource": row.get("resource"),
            "scopes": row.get("scopes") or [],
            "approved_scopes": row.get("approved_scopes") or [],
            "user_id": row.get("user_id"),
            "organization_id": row.get("organization_id"),
            "code_challenge": row.get("code_challenge"),
            "code_challenge_method": row.get("code_challenge_method"),
            "code_value": row.get("code_value"),
            "is_used": row.get("is_used", False),
            "used_at": row.get("used_at"),
            "created_at": row.get("created_at"),
            "expires_at": row.get("expires_at"),
        }

    async def mark_used(self, code_id: str) -> bool:
        """Mark code as used (single-use enforcement).

        Returns True if the code was successfully marked (was not already used).
        """
        await self._ensure_table()

        now = datetime.now(timezone.utc)
        query = f"""
            UPDATE {self.schema}.{self.table}
            SET is_used = TRUE, used_at = $1
            WHERE code_id = $2::uuid AND is_used = FALSE
        """

        async with self.db:
            count = await self.db.execute(query, params=[now, code_id])

        return bool(count)

    async def delete_expired(self) -> int:
        """Clean up expired authorization codes.

        Returns the number of deleted rows.
        """
        await self._ensure_table()

        now = datetime.now(timezone.utc)
        query = f"""
            DELETE FROM {self.schema}.{self.table}
            WHERE expires_at < $1
        """

        async with self.db:
            count = await self.db.execute(query, params=[now])

        return count or 0
