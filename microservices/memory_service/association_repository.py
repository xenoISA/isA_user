"""
Association Repository
Data access layer for memory_associations table (migration 008)
"""

import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from .base_repository import BaseMemoryRepository
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class AssociationRepository(BaseMemoryRepository):
    """Repository for memory association operations"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize association repository"""
        super().__init__(schema="memory", table_name="memory_associations", config=config)

    async def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new association record.

        Args:
            data: Association data dict with source/target info

        Returns:
            Created association record or None
        """
        try:
            if "id" not in data:
                data["id"] = str(uuid.uuid4())
            if "created_at" not in data:
                data["created_at"] = datetime.now(timezone.utc)

            serialized = self._serialize_data(data)

            async with self.db:
                count = await self.db.insert_into(
                    self.table_name, [serialized], schema=self.schema
                )

            if count is not None and count > 0:
                return data
            return None

        except Exception as e:
            # Handle unique constraint violation gracefully
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                logger.info(
                    f"Association already exists: {data.get('source_memory_id')} -> "
                    f"{data.get('target_memory_id')} ({data.get('association_type')})"
                )
                return data
            logger.error(f"Error creating association: {e}")
            raise

    async def get_associations_for_memory(
        self,
        memory_id: str,
        memory_type: str,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get associations where this memory is the source.

        Args:
            memory_id: Memory ID
            memory_type: Memory type string
            user_id: User ID

        Returns:
            List of association records
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1
                  AND source_memory_type = $2
                  AND source_memory_id = $3
                ORDER BY strength DESC, created_at DESC
            """
            params = [user_id, memory_type, memory_id]

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            return [self._deserialize_row(r) for r in (results or [])]

        except Exception as e:
            logger.error(f"Error getting associations for memory: {e}")
            return []

    async def get_bidirectional_associations(
        self,
        memory_id: str,
        memory_type: str,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get all associations where this memory is either source or target.

        Args:
            memory_id: Memory ID
            memory_type: Memory type string
            user_id: User ID

        Returns:
            List of association records (both directions)
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1
                  AND (
                    (source_memory_type = $2 AND source_memory_id = $3)
                    OR
                    (target_memory_type = $2 AND target_memory_id = $3)
                  )
                ORDER BY strength DESC, created_at DESC
            """
            params = [user_id, memory_type, memory_id]

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            return [self._deserialize_row(r) for r in (results or [])]

        except Exception as e:
            logger.error(f"Error getting bidirectional associations: {e}")
            return []

    async def delete_associations_for_memory(
        self,
        memory_id: str,
        memory_type: str,
        user_id: str,
    ) -> int:
        """
        Delete all associations for a memory (both directions).

        Args:
            memory_id: Memory ID
            memory_type: Memory type string
            user_id: User ID

        Returns:
            Number of deleted associations
        """
        try:
            query = f"""
                DELETE FROM {self.schema}.{self.table_name}
                WHERE user_id = $1
                  AND (
                    (source_memory_type = $2 AND source_memory_id = $3)
                    OR
                    (target_memory_type = $2 AND target_memory_id = $3)
                  )
            """
            params = [user_id, memory_type, memory_id]

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            return count or 0

        except Exception as e:
            logger.error(f"Error deleting associations: {e}")
            return 0
