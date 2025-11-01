"""
Working Memory Repository
Data access layer for working memory operations
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from .base_repository import BaseMemoryRepository

logger = logging.getLogger(__name__)


class WorkingMemoryRepository(BaseMemoryRepository):
    """Repository for working memory operations"""

    def __init__(self):
        """Initialize working memory repository"""
        super().__init__(schema="memory", table_name="working_memories")

    async def get_active_memories(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get active (non-expired) working memories

        Args:
            user_id: User ID

        Returns:
            List of active working memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND expires_at > $2
                ORDER BY priority DESC, created_at DESC
            """
            params = [user_id, datetime.now(timezone.utc)]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error getting active working memories: {e}")
            return []

    async def cleanup_expired_memories(
        self,
        user_id: Optional[str] = None
    ) -> int:
        """
        Clean up expired working memories

        Args:
            user_id: Optional user ID to limit cleanup

        Returns:
            Number of memories cleaned up
        """
        try:
            if user_id:
                query = f"""
                    DELETE FROM {self.schema}.{self.table_name}
                    WHERE user_id = $1 AND expires_at <= $2
                """
                params = [user_id, datetime.now(timezone.utc)]
            else:
                query = f"""
                    DELETE FROM {self.schema}.{self.table_name}
                    WHERE expires_at <= $1
                """
                params = [datetime.now(timezone.utc)]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            logger.info(f"Cleaned up {count} expired working memories")
            return count

        except Exception as e:
            logger.error(f"Error cleaning up expired working memories: {e}")
            return 0

    async def search_by_task_id(
        self,
        user_id: str,
        task_id: str,
        include_expired: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search working memories by task ID

        Args:
            user_id: User ID
            task_id: Task ID to search for
            include_expired: Whether to include expired memories

        Returns:
            List of matching working memories
        """
        try:
            if include_expired:
                query = f"""
                    SELECT * FROM {self.schema}.{self.table_name}
                    WHERE user_id = $1 AND task_id = $2
                    ORDER BY created_at DESC
                """
                params = [user_id, task_id]
            else:
                query = f"""
                    SELECT * FROM {self.schema}.{self.table_name}
                    WHERE user_id = $1 AND task_id = $2 AND expires_at > $3
                    ORDER BY created_at DESC
                """
                params = [user_id, task_id, datetime.now(timezone.utc)]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching working memories by task_id: {e}")
            return []

    async def search_by_priority(
        self,
        user_id: str,
        min_priority: int = 5,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search working memories by minimum priority level

        Args:
            user_id: User ID
            min_priority: Minimum priority level
            limit: Maximum number of results

        Returns:
            List of high-priority working memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1
                    AND priority >= $2
                    AND expires_at > $3
                ORDER BY priority DESC, created_at DESC
                LIMIT {limit}
            """
            params = [user_id, min_priority, datetime.now(timezone.utc)]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching working memories by priority: {e}")
            return []
