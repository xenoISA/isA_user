"""
Connector Repository

Data access for the two tables this service owns (schema ``connector``):

  * ``connector`` — per-user install state for built-in catalog connectors.
  * ``custom_mcp_connector`` — user-added remote MCP servers.

Mirrors the AsyncPostgresClient + gRPC-proxy pattern used by
project_sharing_service.project_share_repository.
"""

from __future__ import annotations

import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from core.config_manager import ConfigManager
from core.postgres_client import compute_pool_size as _pg_compute_pool
from isa_common import AsyncPostgresClient

from .models import (
    ConnectorInstallState,
    CustomMcpConnector,
)


logger = logging.getLogger(__name__)


def _pg_max_pool() -> int:
    """Per-pod Postgres max pool size; scales with replica count (epic #345/#346)."""
    return _pg_compute_pool()


def _pg_min_pool() -> int:
    """Per-pod Postgres min pool size — at least 1, ideally 2 once max>=4."""
    return 2 if _pg_max_pool() >= 4 else 1


class ConnectorRepository:
    """Data access layer for connector + custom_mcp_connector tables."""

    SCHEMA = "connector"

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("connector_service")

        host, port = config.discover_service(
            service_name="postgres_service",
            default_host="localhost",
            default_port=5432,
            env_host_key="POSTGRES_HOST",
            env_port_key="POSTGRES_PORT",
        )
        logger.info("ConnectorRepository connecting to PostgreSQL at %s:%s", host, port)

        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            database=os.getenv("POSTGRES_DB", "isa_platform"),
            username=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            user_id="connector_service",
            min_pool_size=_pg_min_pool(),
            max_pool_size=_pg_max_pool(),
        )

    # ========================================================================
    # connector table — per-user install state for built-in catalog
    # ========================================================================

    async def list_installed_for_user(
        self, user_id: str
    ) -> List[ConnectorInstallState]:
        """List built-in install-state rows for one user."""
        try:
            query = f"""
                SELECT id, user_id, connector_id, status, scopes, installed_at,
                       last_synced_at, metadata, created_at, updated_at,
                       error_code, error_message, auth_url
                FROM {self.SCHEMA}.connector
                WHERE user_id = $1
                ORDER BY installed_at DESC NULLS LAST, created_at DESC NULLS LAST
            """
            async with self.db:
                rows = await self.db.query(query, [user_id], schema=self.SCHEMA)
            if not rows:
                return []
            return [self._connector_row_to_model(dict(r)) for r in rows]
        except Exception as e:
            logger.error(
                "Error listing installed connectors for %s: %s",
                user_id,
                e,
                exc_info=True,
            )
            return []

    # ========================================================================
    # custom_mcp_connector table
    # ========================================================================

    async def list_custom_for_user(self, user_id: str) -> List[CustomMcpConnector]:
        """List custom remote MCP rows for one user (including revoked)."""
        try:
            query = f"""
                SELECT id, user_id, label, url, auth_kind, auth_secret_ref, status,
                       last_error, created_at, last_validated_at, last_handshake_at,
                       tools_count
                FROM {self.SCHEMA}.custom_mcp_connector
                WHERE user_id = $1
                ORDER BY created_at DESC
            """
            async with self.db:
                rows = await self.db.query(query, [user_id], schema=self.SCHEMA)
            if not rows:
                return []
            return [self._custom_row_to_model(dict(r)) for r in rows]
        except Exception as e:
            logger.error(
                "Error listing custom MCP connectors for %s: %s",
                user_id,
                e,
                exc_info=True,
            )
            return []

    async def get_custom_by_id(
        self, user_id: str, connector_id: str
    ) -> Optional[CustomMcpConnector]:
        """Fetch one custom MCP row by id, scoped to user (ownership check)."""
        try:
            query = f"""
                SELECT id, user_id, label, url, auth_kind, auth_secret_ref, status,
                       last_error, created_at, last_validated_at, last_handshake_at,
                       tools_count
                FROM {self.SCHEMA}.custom_mcp_connector
                WHERE id = $1::uuid AND user_id = $2
            """
            async with self.db:
                row = await self.db.query_row(
                    query, [connector_id, user_id], schema=self.SCHEMA
                )
            if not row:
                return None
            return self._custom_row_to_model(dict(row))
        except Exception as e:
            logger.error(
                "Error fetching custom connector %s: %s", connector_id, e, exc_info=True
            )
            return None

    async def get_custom_by_user_and_url(
        self, user_id: str, url: str
    ) -> Optional[CustomMcpConnector]:
        """Look up a custom row by (user_id, url) — backs the idempotency guard."""
        try:
            query = f"""
                SELECT id, user_id, label, url, auth_kind, auth_secret_ref, status,
                       last_error, created_at, last_validated_at, last_handshake_at,
                       tools_count
                FROM {self.SCHEMA}.custom_mcp_connector
                WHERE user_id = $1 AND url = $2
            """
            async with self.db:
                row = await self.db.query_row(query, [user_id, url], schema=self.SCHEMA)
            if not row:
                return None
            return self._custom_row_to_model(dict(row))
        except Exception as e:
            logger.error("Error fetching custom connector by url: %s", e, exc_info=True)
            return None

    async def insert_custom(
        self,
        *,
        user_id: str,
        label: str,
        url: str,
        auth_kind: str,
        auth_secret_ref: Optional[str],
        status: str,
        tools_count: Optional[int] = None,
        last_error: Optional[str] = None,
    ) -> Optional[CustomMcpConnector]:
        """Insert a new custom MCP row (status=active when handshake passed)."""
        try:
            row_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            data = {
                "id": row_id,
                "user_id": user_id,
                "label": label,
                "url": url,
                "auth_kind": auth_kind,
                "auth_secret_ref": auth_secret_ref,
                "status": status,
                "last_error": last_error,
                "created_at": now,
                "last_validated_at": now if status == "active" else None,
                "last_handshake_at": now if status == "active" else None,
                "tools_count": tools_count,
            }
            async with self.db:
                await self.db.insert_into(
                    "custom_mcp_connector", [data], schema=self.SCHEMA
                )
            return await self.get_custom_by_id(user_id, row_id)
        except Exception as e:
            logger.error("Error inserting custom connector: %s", e, exc_info=True)
            raise

    async def update_custom_after_handshake(
        self,
        *,
        user_id: str,
        connector_id: str,
        status: str,
        tools_count: Optional[int] = None,
        last_error: Optional[str] = None,
    ) -> Optional[CustomMcpConnector]:
        """Re-validate flow — bump timestamps + status."""
        try:
            now = datetime.now(timezone.utc)
            query = f"""
                UPDATE {self.SCHEMA}.custom_mcp_connector
                   SET status = $1,
                       tools_count = $2,
                       last_error = $3,
                       last_validated_at = $4,
                       last_handshake_at = CASE WHEN $1 = 'active' THEN $4 ELSE last_handshake_at END
                 WHERE id = $5::uuid AND user_id = $6
            """
            async with self.db:
                await self.db.execute(
                    query,
                    [status, tools_count, last_error, now, connector_id, user_id],
                    schema=self.SCHEMA,
                )
            return await self.get_custom_by_id(user_id, connector_id)
        except Exception as e:
            logger.error(
                "Error updating custom connector %s: %s", connector_id, e, exc_info=True
            )
            return None

    async def delete_custom(self, user_id: str, connector_id: str) -> bool:
        """Hard-delete a custom MCP row, scoped to the owner."""
        try:
            query = f"""
                DELETE FROM {self.SCHEMA}.custom_mcp_connector
                WHERE id = $1::uuid AND user_id = $2
            """
            async with self.db:
                await self.db.execute(
                    query, [connector_id, user_id], schema=self.SCHEMA
                )
            # We rely on get_custom_by_id afterwards in the route to verify
            # the row is gone; execute() on asyncpg doesn't always return
            # a count via the gRPC proxy.
            return True
        except Exception as e:
            logger.error(
                "Error deleting custom connector %s: %s", connector_id, e, exc_info=True
            )
            return False

    # ========================================================================
    # Row -> model helpers
    # ========================================================================

    @staticmethod
    def _connector_row_to_model(row: Dict[str, Any]) -> ConnectorInstallState:
        """Map a ``connector.connector`` row to ConnectorInstallState."""
        return ConnectorInstallState(
            id=str(row["id"]),
            owner_user_id=row["user_id"],
            connector_id=row["connector_id"],
            status=row["status"],
            auth_url=row.get("auth_url"),
            last_synced_at=row.get("last_synced_at"),
            error_code=row.get("error_code"),
            error_message=row.get("error_message"),
            scopes=row.get("scopes") or [],
            metadata=row.get("metadata") or {},
            created_at=row.get("created_at") or row.get("installed_at"),
            updated_at=row.get("updated_at") or row.get("installed_at"),
        )

    @staticmethod
    def _custom_row_to_model(row: Dict[str, Any]) -> CustomMcpConnector:
        """Map a ``connector.custom_mcp_connector`` row to CustomMcpConnector.

        Note: ``auth_secret_ref`` is intentionally NOT exposed on the API
        model — it's only used internally to look up the secret in the
        vault.
        """
        return CustomMcpConnector(
            id=str(row["id"]),
            user_id=row["user_id"],
            label=row["label"],
            url=row["url"],
            auth_kind=row["auth_kind"],
            status=row["status"],
            last_error=row.get("last_error"),
            created_at=row.get("created_at"),
            last_validated_at=row.get("last_validated_at"),
            last_handshake_at=row.get("last_handshake_at"),
            tools_count=row.get("tools_count"),
        )
