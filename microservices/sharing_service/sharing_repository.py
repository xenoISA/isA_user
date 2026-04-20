"""
Sharing Repository

Data access layer for share link operations.
Using AsyncPostgresClient for database operations.
"""

import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.config_manager import ConfigManager
from isa_common import AsyncPostgresClient

from .models import Share

logger = logging.getLogger(__name__)


class ShareRepository:
    """Data access layer for shares"""

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("sharing_service")

        host, port = config.discover_service(
            service_name="postgres_service",
            default_host="localhost",
            default_port=5432,
            env_host_key="POSTGRES_HOST",
            env_port_key="POSTGRES_PORT",
        )

        logger.info(f"ShareRepository connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            database=os.getenv("POSTGRES_DB", "isa_platform"),
            username=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            user_id="sharing_service",
            min_pool_size=1,
            max_pool_size=2,
        )
        self.schema = "sharing"
        self.table = "shares"

    async def create_share(self, share_data: Dict[str, Any]) -> Optional[Share]:
        """Create a new share record"""
        try:
            share_id = share_data.get("id") or str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            data = {
                "id": share_id,
                "session_id": share_data["session_id"],
                "owner_id": share_data["owner_id"],
                "share_token": share_data["share_token"],
                "permissions": share_data.get("permissions", "view_only"),
                "expires_at": share_data.get("expires_at"),
                "access_count": 0,
                "created_at": now,
                "updated_at": now,
            }

            async with self.db:
                count = await self.db.insert_into(
                    self.table, [data], schema=self.schema
                )

            if count is not None and count > 0:
                return await self.get_by_id(share_id)

            return await self.get_by_id(share_id)

        except Exception as e:
            logger.error(f"Error creating share: {e}", exc_info=True)
            raise

    async def get_by_token(self, share_token: str) -> Optional[Share]:
        """Get share by token"""
        try:
            query = f"SELECT * FROM {self.schema}.{self.table} WHERE share_token = $1"
            async with self.db:
                result = await self.db.query_row(query, [share_token], schema=self.schema)

            if result:
                return Share.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting share by token: {e}")
            return None

    async def get_by_id(self, share_id: str) -> Optional[Share]:
        """Get share by ID"""
        try:
            query = f"SELECT * FROM {self.schema}.{self.table} WHERE id = $1"
            async with self.db:
                result = await self.db.query_row(query, [share_id], schema=self.schema)

            if result:
                return Share.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting share by id: {e}")
            return None

    async def get_session_shares(
        self, session_id: str, owner_id: str
    ) -> List[Share]:
        """Get all active (non-expired) shares for a session owned by a user"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table}
                WHERE session_id = $1 AND owner_id = $2
                ORDER BY created_at DESC
            """
            async with self.db:
                rows = await self.db.query(query, [session_id, owner_id], schema=self.schema)

            if not rows:
                return []
            return [Share.model_validate(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting session shares: {e}")
            return []

    async def delete_by_token(self, share_token: str) -> bool:
        """Delete (revoke) a share by token"""
        try:
            query = f"DELETE FROM {self.schema}.{self.table} WHERE share_token = $1"
            async with self.db:
                count = await self.db.execute(query, [share_token], schema=self.schema)
            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error deleting share: {e}")
            return False

    async def increment_access_count(self, share_id: str) -> bool:
        """Increment access count for a share"""
        try:
            now = datetime.now(timezone.utc)
            query = f"""
                UPDATE {self.schema}.{self.table}
                SET access_count = access_count + 1, updated_at = $1
                WHERE id = $2
            """
            async with self.db:
                count = await self.db.execute(query, [now, share_id], schema=self.schema)
            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error incrementing access count: {e}")
            return False
