"""
Episodic Memory Repository
Data access layer for episodic memory operations
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base_repository import BaseMemoryRepository
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class EpisodicMemoryRepository(BaseMemoryRepository):
    """Repository for episodic memory operations"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize episodic memory repository"""
        super().__init__(schema="memory", table_name="episodic_memories", config=config)

    async def search_by_timeframe(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search episodic memories by timeframe

        Args:
            user_id: User ID
            start_date: Start date
            end_date: End date
            limit: Maximum number of results

        Returns:
            List of matching episodic memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1
                    AND episode_date >= $2
                    AND episode_date <= $3
                ORDER BY episode_date DESC
                LIMIT {limit}
            """
            params = [user_id, start_date, end_date]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching episodes by timeframe: {e}")
            return []

    async def search_by_event_type(
        self,
        user_id: str,
        event_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search episodic memories by event type

        Args:
            user_id: User ID
            event_type: Type of event
            limit: Maximum number of results

        Returns:
            List of matching episodic memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND event_type = $2
                ORDER BY episode_date DESC
                LIMIT {limit}
            """
            params = [user_id, event_type]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            # Deserialize all rows
            return [self._deserialize_row(row) for row in (results or [])]

        except Exception as e:
            logger.error(f"Error searching episodes by event type: {e}")
            return []

    async def search_by_location(
        self,
        user_id: str,
        location: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search episodic memories by location

        Args:
            user_id: User ID
            location: Location to search for
            limit: Maximum number of results

        Returns:
            List of matching episodic memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND location ILIKE $2
                ORDER BY episode_date DESC
                LIMIT {limit}
            """
            params = [user_id, f"%{location}%"]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching episodes by location: {e}")
            return []

    async def search_by_participant(
        self,
        user_id: str,
        participant: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search episodic memories by participant

        Args:
            user_id: User ID
            participant: Participant name to search for
            limit: Maximum number of results

        Returns:
            List of matching episodic memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1
                    AND $2 = ANY(participants)
                ORDER BY episode_date DESC
                LIMIT {limit}
            """
            params = [user_id, participant]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching episodes by participant: {e}")
            return []

    async def search_by_emotional_valence(
        self,
        user_id: str,
        min_valence: float,
        max_valence: float,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search episodic memories by emotional valence range

        Args:
            user_id: User ID
            min_valence: Minimum emotional valence
            max_valence: Maximum emotional valence
            limit: Maximum number of results

        Returns:
            List of matching episodic memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1
                    AND emotional_valence >= $2
                    AND emotional_valence <= $3
                ORDER BY episode_date DESC
                LIMIT {limit}
            """
            params = [user_id, min_valence, max_valence]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching episodes by emotional valence: {e}")
            return []
