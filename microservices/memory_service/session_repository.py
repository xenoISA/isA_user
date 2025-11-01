"""
Session Memory Repository
Data access layer for session memory operations
"""

import logging
from typing import List, Optional, Dict, Any

from .base_repository import BaseMemoryRepository

logger = logging.getLogger(__name__)


class SessionMemoryRepository(BaseMemoryRepository):
    """Repository for session memory operations"""

    def __init__(self):
        """Initialize session memory repository"""
        super().__init__(schema="memory", table_name="session_memories")

    async def get_session_memories(
        self,
        user_id: str,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all memories for a specific session

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            List of session memories ordered by interaction sequence
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND session_id = $2 AND active = true
                ORDER BY interaction_sequence ASC
            """
            params = [user_id, session_id]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            # Deserialize all rows
            return [self._deserialize_row(row) for row in (results or [])]

        except Exception as e:
            logger.error(f"Error getting session memories: {e}")
            return []

    async def get_session_summary(
        self,
        user_id: str,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get session summary

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            Session summary if exists
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.session_summaries
                WHERE user_id = $1 AND session_id = $2
                ORDER BY created_at DESC
                LIMIT 1
            """
            params = [user_id, session_id]

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            return self._deserialize_row(result) if result else None

        except Exception as e:
            logger.error(f"Error getting session summary: {e}")
            return None

    async def store_session_summary(
        self,
        user_id: str,
        session_id: str,
        summary_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Store or update session summary

        Args:
            user_id: User ID
            session_id: Session ID
            summary_data: Summary data

        Returns:
            Created summary record
        """
        try:
            data = {
                "id": summary_data.get("id"),
                "user_id": user_id,
                "session_id": session_id,
                "summary": summary_data.get("summary", ""),
                "key_points": summary_data.get("key_points", []),
                "message_count": summary_data.get("message_count", 0),
                "created_at": summary_data.get("created_at")
            }

            with self.db:
                count = self.db.insert_into(
                    "session_summaries",
                    [data],
                    schema=self.schema
                )

            if count > 0:
                return await self.get_session_summary(user_id, session_id)
            return None

        except Exception as e:
            logger.error(f"Error storing session summary: {e}")
            raise

    async def deactivate_session(
        self,
        user_id: str,
        session_id: str
    ) -> bool:
        """
        Deactivate all memories in a session

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            True if successful
        """
        try:
            query = f"""
                UPDATE {self.schema}.{self.table_name}
                SET active = false
                WHERE user_id = $1 AND session_id = $2
            """
            params = [user_id, session_id]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count > 0

        except Exception as e:
            logger.error(f"Error deactivating session: {e}")
            return False

    async def search_by_session_type(
        self,
        user_id: str,
        session_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search session memories by session type

        Args:
            user_id: User ID
            session_type: Type of session
            limit: Maximum number of results

        Returns:
            List of matching session memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND session_type = $2 AND active = true
                ORDER BY created_at DESC
                LIMIT {limit}
            """
            params = [user_id, session_type]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching sessions by type: {e}")
            return []

    async def get_active_sessions(
        self,
        user_id: str
    ) -> List[str]:
        """
        Get list of active session IDs for a user

        Args:
            user_id: User ID

        Returns:
            List of active session IDs
        """
        try:
            query = f"""
                SELECT DISTINCT session_id FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND active = true
                ORDER BY session_id
            """
            params = [user_id]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [row['session_id'] for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []
