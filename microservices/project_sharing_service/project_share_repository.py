"""
Project Share Repository

Data access layer for project_shares.
Uses AsyncPostgresClient for database operations.
"""

import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.config_manager import ConfigManager
from core.postgres_client import compute_pool_size as _pg_compute_pool
from isa_common import AsyncPostgresClient

from .models import ProjectShare


def _pg_max_pool() -> int:
    """Per-pod Postgres max pool size; scales with replica count (epic #345/#346)."""
    return _pg_compute_pool()


def _pg_min_pool() -> int:
    """Per-pod Postgres min pool size."""
    return 2 if _pg_max_pool() >= 4 else 1


logger = logging.getLogger(__name__)


class ProjectShareRepository:
    """Data access layer for project_shares."""

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("project_sharing_service")

        host, port = config.discover_service(
            service_name="postgres_service",
            default_host="localhost",
            default_port=5432,
            env_host_key="POSTGRES_HOST",
            env_port_key="POSTGRES_PORT",
        )

        logger.info(f"ProjectShareRepository connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            database=os.getenv("POSTGRES_DB", "isa_platform"),
            username=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            user_id="project_sharing_service",
            min_pool_size=_pg_min_pool(),
            max_pool_size=_pg_max_pool(),
        )
        self.schema = "project_sharing"
        self.table = "project_shares"

    # ========================================================================
    # Lookups
    # ========================================================================

    async def find_pending_by_email(self, project_id: str, invitee_email: str) -> Optional[ProjectShare]:
        """Find a single pending share for (project_id, lower(email))."""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table}
                WHERE project_id = $1::uuid
                  AND lower(invitee_email) = lower($2)
                  AND status = 'pending'
                LIMIT 1
            """
            async with self.db:
                row = await self.db.query_row(query, [project_id, invitee_email], schema=self.schema)
            if row:
                return ProjectShare.model_validate(self._row_to_model(dict(row)))
            return None
        except Exception as e:
            logger.error(f"Error finding pending share by email: {e}", exc_info=True)
            return None

    async def get_by_id(self, share_id: str) -> Optional[ProjectShare]:
        """Get a share by id."""
        try:
            query = f"SELECT * FROM {self.schema}.{self.table} WHERE id = $1::uuid"
            async with self.db:
                row = await self.db.query_row(query, [share_id], schema=self.schema)
            if row:
                return ProjectShare.model_validate(self._row_to_model(dict(row)))
            return None
        except Exception as e:
            logger.error(f"Error getting share by id: {e}", exc_info=True)
            return None

    async def get_by_token(self, invite_token: str) -> Optional[ProjectShare]:
        """Get a share by invite_token (returns None if token has been nulled)."""
        try:
            query = f"SELECT * FROM {self.schema}.{self.table} WHERE invite_token = $1"
            async with self.db:
                row = await self.db.query_row(query, [invite_token], schema=self.schema)
            if row:
                return ProjectShare.model_validate(self._row_to_model(dict(row)))
            return None
        except Exception as e:
            logger.error(f"Error getting share by token: {e}", exc_info=True)
            return None

    async def list_for_project(self, project_id: str, status: Optional[str] = None) -> List[ProjectShare]:
        """List shares for a project. Optionally filter by status."""
        try:
            if status:
                query = f"""
                    SELECT * FROM {self.schema}.{self.table}
                    WHERE project_id = $1::uuid AND status = $2
                    ORDER BY created_at DESC
                """
                params = [project_id, status]
            else:
                query = f"""
                    SELECT * FROM {self.schema}.{self.table}
                    WHERE project_id = $1::uuid
                    ORDER BY created_at DESC
                """
                params = [project_id]

            async with self.db:
                rows = await self.db.query(query, params, schema=self.schema)
            if not rows:
                return []
            return [ProjectShare.model_validate(self._row_to_model(dict(row))) for row in rows]
        except Exception as e:
            logger.error(f"Error listing project shares: {e}", exc_info=True)
            return []

    # ========================================================================
    # Mutations
    # ========================================================================

    async def create_share(self, share_data: Dict[str, Any]) -> Optional[ProjectShare]:
        """Insert a new pending share row and return the persisted record."""
        try:
            share_id = share_data.get("id") or str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            data = {
                "id": share_id,
                "project_id": share_data["project_id"],
                "invitee_user_id": share_data.get("invitee_user_id"),
                "invitee_email": share_data["invitee_email"],
                "role": share_data.get("role", "viewer"),
                "invite_token": share_data["invite_token"],
                "status": share_data.get("status", "pending"),
                "created_at": now,
                "accepted_at": share_data.get("accepted_at"),
                "revoked_at": share_data.get("revoked_at"),
            }

            async with self.db:
                count = await self.db.insert_into(self.table, [data], schema=self.schema)

            if count is None or count <= 0:
                # Some drivers return None on success; fall through and try to fetch.
                pass
            return await self.get_by_id(share_id)
        except Exception as e:
            logger.error(f"Error creating share: {e}", exc_info=True)
            raise

    async def update_role(self, share_id: str, role: str) -> Optional[ProjectShare]:
        """Update role on a share row."""
        try:
            query = f"""
                UPDATE {self.schema}.{self.table}
                SET role = $1::{self.schema}.project_share_role
                WHERE id = $2::uuid
            """
            async with self.db:
                await self.db.execute(query, [role, share_id], schema=self.schema)
            return await self.get_by_id(share_id)
        except Exception as e:
            logger.error(f"Error updating share role: {e}", exc_info=True)
            return None

    async def revoke(self, share_id: str) -> Optional[ProjectShare]:
        """Mark a share as revoked. Null the invite_token so it can't be reused."""
        try:
            now = datetime.now(timezone.utc)
            query = f"""
                UPDATE {self.schema}.{self.table}
                SET status = 'revoked',
                    revoked_at = $1,
                    invite_token = NULL
                WHERE id = $2::uuid
            """
            async with self.db:
                await self.db.execute(query, [now, share_id], schema=self.schema)
            return await self.get_by_id(share_id)
        except Exception as e:
            logger.error(f"Error revoking share: {e}", exc_info=True)
            return None

    async def mark_accepted(self, share_id: str, invitee_user_id: str) -> Optional[ProjectShare]:
        """Mark share as accepted (record invitee_user_id + accepted_at)."""
        try:
            now = datetime.now(timezone.utc)
            query = f"""
                UPDATE {self.schema}.{self.table}
                SET status = 'accepted',
                    invitee_user_id = $1,
                    accepted_at = $2
                WHERE id = $3::uuid
            """
            async with self.db:
                await self.db.execute(query, [invitee_user_id, now, share_id], schema=self.schema)
            return await self.get_by_id(share_id)
        except Exception as e:
            logger.error(f"Error marking share accepted: {e}", exc_info=True)
            return None

    # ========================================================================
    # Helpers
    # ========================================================================

    @staticmethod
    def _row_to_model(row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert raw asyncpg row to the dict shape Pydantic expects.

        Coerces UUID/enum values to strings since the Pydantic ProjectShare
        model uses `str` for id/project_id and the enum values are already
        plain strings ('pending', 'viewer', etc.) returned by asyncpg.
        """
        out = dict(row)
        for key in ("id", "project_id"):
            if out.get(key) is not None:
                out[key] = str(out[key])
        return out
