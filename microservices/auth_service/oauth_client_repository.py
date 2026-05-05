"""
OAuth Client Repository

Persistence layer for OAuth2 client credentials used by A2A integrations.
"""

import logging
import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import bcrypt

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class OAuthClientRepository:
    """Data access for OAuth2 clients (client-credentials grant)."""

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

        logger.info(f"Connecting to PostgreSQL at {host}:{port} for OAuth clients")
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
        self.table = "oauth_clients"
        self._table_initialized = False

    async def _ensure_table(self) -> None:
        """Create OAuth clients table if missing."""
        if self._table_initialized:
            return

        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.schema}.{self.table} (
                client_id TEXT PRIMARY KEY,
                client_secret_hash TEXT NOT NULL,
                client_name TEXT NOT NULL,
                organization_id TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                allowed_scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
                token_ttl_seconds INTEGER NOT NULL DEFAULT 3600,
                client_type VARCHAR(20) DEFAULT 'confidential',
                redirect_uris JSONB NOT NULL DEFAULT '[]'::jsonb,
                require_pkce BOOLEAN NOT NULL DEFAULT TRUE,
                metadata_document_url TEXT,
                created_by TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_used_at TIMESTAMPTZ
            )
        """
        index_org_sql = f"CREATE INDEX IF NOT EXISTS idx_{self.table}_org ON {self.schema}.{self.table}(organization_id)"
        index_active_sql = f"CREATE INDEX IF NOT EXISTS idx_{self.table}_active ON {self.schema}.{self.table}(is_active)"
        alter_sql = [
            f"ALTER TABLE {self.schema}.{self.table} ADD COLUMN IF NOT EXISTS client_type VARCHAR(20) DEFAULT 'confidential'",
            f"ALTER TABLE {self.schema}.{self.table} ADD COLUMN IF NOT EXISTS redirect_uris JSONB NOT NULL DEFAULT '[]'::jsonb",
            f"ALTER TABLE {self.schema}.{self.table} ADD COLUMN IF NOT EXISTS require_pkce BOOLEAN NOT NULL DEFAULT TRUE",
            f"ALTER TABLE {self.schema}.{self.table} ADD COLUMN IF NOT EXISTS metadata_document_url TEXT",
        ]

        async with self.db:
            await self.db.execute(create_sql)
            for statement in alter_sql:
                await self.db.execute(statement)
            await self.db.execute(index_org_sql)
            await self.db.execute(index_active_sql)

        self._table_initialized = True

    @staticmethod
    def _hash_secret(secret: str) -> str:
        return bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def _verify_secret(secret: str, secret_hash: str) -> bool:
        try:
            return bcrypt.checkpw(secret.encode("utf-8"), secret_hash.encode("utf-8"))
        except Exception:
            return False

    @staticmethod
    def _generate_client_id() -> str:
        return f"a2a_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def _generate_client_secret() -> str:
        return secrets.token_urlsafe(48)

    async def create_client(
        self,
        *,
        client_name: str,
        organization_id: Optional[str],
        allowed_scopes: List[str],
        token_ttl_seconds: int = 3600,
        client_type: str = "confidential",
        redirect_uris: Optional[List[str]] = None,
        require_pkce: bool = True,
        metadata_document_url: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        await self._ensure_table()

        now = datetime.now(timezone.utc)
        client_id = self._generate_client_id()
        client_secret = self._generate_client_secret()
        client_secret_hash = self._hash_secret(client_secret)

        query = f"""
            INSERT INTO {self.schema}.{self.table}
            (client_id, client_secret_hash, client_name, organization_id, allowed_scopes,
             token_ttl_seconds, client_type, redirect_uris, require_pkce,
             metadata_document_url, created_by, is_active, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8::jsonb, $9, $10, $11, TRUE, $12, $12)
        """
        clamped_ttl = max(300, min(token_ttl_seconds, 86400))
        effective_redirect_uris = redirect_uris or []

        async with self.db:
            await self.db.execute(
                query,
                params=[
                    client_id,
                    client_secret_hash,
                    client_name,
                    organization_id,
                    allowed_scopes,
                    clamped_ttl,
                    client_type,
                    effective_redirect_uris,
                    require_pkce,
                    metadata_document_url,
                    created_by,
                    now,
                ],
            )

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_name": client_name,
            "organization_id": organization_id,
            "allowed_scopes": allowed_scopes,
            "token_ttl_seconds": clamped_ttl,
            "client_type": client_type,
            "redirect_uris": effective_redirect_uris,
            "require_pkce": require_pkce,
            "metadata_document_url": metadata_document_url,
            "created_at": now,
        }

    async def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        await self._ensure_table()

        query = f"""
            SELECT client_id, client_name, organization_id, is_active, allowed_scopes,
                   token_ttl_seconds, client_type, redirect_uris, require_pkce,
                   metadata_document_url, created_by, created_at, updated_at, last_used_at
            FROM {self.schema}.{self.table}
            WHERE client_id = $1
        """

        async with self.db:
            row = await self.db.query_row(query, params=[client_id])

        if not row:
            return None

        return {
            "client_id": row.get("client_id"),
            "client_name": row.get("client_name"),
            "organization_id": row.get("organization_id"),
            "is_active": row.get("is_active", False),
            "allowed_scopes": row.get("allowed_scopes") or [],
            "token_ttl_seconds": row.get("token_ttl_seconds", 3600),
            "client_type": row.get("client_type") or "confidential",
            "redirect_uris": row.get("redirect_uris") or [],
            "require_pkce": row.get("require_pkce", True),
            "metadata_document_url": row.get("metadata_document_url"),
            "created_by": row.get("created_by"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "last_used_at": row.get("last_used_at"),
        }

    async def list_clients(self, organization_id: Optional[str] = None) -> List[Dict[str, Any]]:
        await self._ensure_table()

        if organization_id:
            query = f"""
                SELECT client_id, client_name, organization_id, is_active, allowed_scopes,
                       token_ttl_seconds, client_type, redirect_uris, require_pkce,
                       metadata_document_url, created_by, created_at, updated_at, last_used_at
                FROM {self.schema}.{self.table}
                WHERE organization_id = $1
                ORDER BY created_at DESC
            """
            params = [organization_id]
        else:
            query = f"""
                SELECT client_id, client_name, organization_id, is_active, allowed_scopes,
                       token_ttl_seconds, client_type, redirect_uris, require_pkce,
                       metadata_document_url, created_by, created_at, updated_at, last_used_at
                FROM {self.schema}.{self.table}
                ORDER BY created_at DESC
            """
            params = []

        async with self.db:
            rows = await self.db.query(query, params=params)

        clients: List[Dict[str, Any]] = []
        for row in rows or []:
            clients.append(
                {
                    "client_id": row.get("client_id"),
                    "client_name": row.get("client_name"),
                    "organization_id": row.get("organization_id"),
                    "is_active": row.get("is_active", False),
                    "allowed_scopes": row.get("allowed_scopes") or [],
                    "token_ttl_seconds": row.get("token_ttl_seconds", 3600),
                    "client_type": row.get("client_type") or "confidential",
                    "redirect_uris": row.get("redirect_uris") or [],
                    "require_pkce": row.get("require_pkce", True),
                    "metadata_document_url": row.get("metadata_document_url"),
                    "created_by": row.get("created_by"),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                    "last_used_at": row.get("last_used_at"),
                }
            )

        return clients

    async def verify_client_credentials(self, client_id: str, client_secret: str) -> Optional[Dict[str, Any]]:
        await self._ensure_table()

        query = f"""
            SELECT client_id, client_secret_hash, client_name, organization_id,
                   is_active, allowed_scopes, token_ttl_seconds, client_type,
                   redirect_uris, require_pkce, metadata_document_url
            FROM {self.schema}.{self.table}
            WHERE client_id = $1
        """

        async with self.db:
            row = await self.db.query_row(query, params=[client_id])

        if not row or not row.get("is_active", False):
            return None

        if not self._verify_secret(client_secret, row.get("client_secret_hash", "")):
            return None

        now = datetime.now(timezone.utc)
        update_query = f"""
            UPDATE {self.schema}.{self.table}
            SET last_used_at = $1, updated_at = $1
            WHERE client_id = $2
        """
        async with self.db:
            await self.db.execute(update_query, params=[now, client_id])

        return {
            "client_id": row.get("client_id"),
            "client_name": row.get("client_name"),
            "organization_id": row.get("organization_id"),
            "allowed_scopes": row.get("allowed_scopes") or [],
            "token_ttl_seconds": row.get("token_ttl_seconds", 3600),
            "client_type": row.get("client_type") or "confidential",
            "redirect_uris": row.get("redirect_uris") or [],
            "require_pkce": row.get("require_pkce", True),
            "metadata_document_url": row.get("metadata_document_url"),
        }

    async def rotate_client_secret(self, client_id: str) -> Optional[Dict[str, Any]]:
        await self._ensure_table()

        client_secret = self._generate_client_secret()
        secret_hash = self._hash_secret(client_secret)
        now = datetime.now(timezone.utc)

        query = f"""
            UPDATE {self.schema}.{self.table}
            SET client_secret_hash = $1, updated_at = $2
            WHERE client_id = $3 AND is_active = TRUE
        """

        async with self.db:
            count = await self.db.execute(query, params=[secret_hash, now, client_id])

        if not count:
            return None

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "rotated_at": now,
        }

    async def deactivate_client(self, client_id: str) -> bool:
        await self._ensure_table()

        now = datetime.now(timezone.utc)
        query = f"""
            UPDATE {self.schema}.{self.table}
            SET is_active = FALSE, updated_at = $1
            WHERE client_id = $2
        """

        async with self.db:
            count = await self.db.execute(query, params=[now, client_id])

        return bool(count)
