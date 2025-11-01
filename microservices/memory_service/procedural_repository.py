"""
Procedural Memory Repository
Data access layer for procedural memory operations
"""

import logging
from typing import List, Optional, Dict, Any

from .base_repository import BaseMemoryRepository

logger = logging.getLogger(__name__)


class ProceduralMemoryRepository(BaseMemoryRepository):
    """Repository for procedural memory operations"""

    def __init__(self):
        """Initialize procedural memory repository"""
        super().__init__(schema="memory", table_name="procedural_memories")

    async def search_by_domain(
        self,
        user_id: str,
        domain: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search procedural memories by domain

        Args:
            user_id: User ID
            domain: Domain to search for
            limit: Maximum number of results

        Returns:
            List of matching procedural memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND domain = $2
                ORDER BY success_rate DESC, created_at DESC
                LIMIT {limit}
            """
            params = [user_id, domain]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching procedures by domain: {e}")
            return []

    async def search_by_skill_type(
        self,
        user_id: str,
        skill_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search procedural memories by skill type

        Args:
            user_id: User ID
            skill_type: Skill type to search for
            limit: Maximum number of results

        Returns:
            List of matching procedural memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND skill_type = $2
                ORDER BY success_rate DESC, created_at DESC
                LIMIT {limit}
            """
            params = [user_id, skill_type]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching procedures by skill type: {e}")
            return []

    async def search_by_difficulty(
        self,
        user_id: str,
        difficulty_level: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search procedural memories by difficulty level

        Args:
            user_id: User ID
            difficulty_level: Difficulty level (easy, medium, hard)
            limit: Maximum number of results

        Returns:
            List of matching procedural memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND difficulty_level = $2
                ORDER BY success_rate DESC, created_at DESC
                LIMIT {limit}
            """
            params = [user_id, difficulty_level]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching procedures by difficulty: {e}")
            return []

    async def search_by_success_rate(
        self,
        user_id: str,
        min_success_rate: float = 0.7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search high-success procedural memories

        Args:
            user_id: User ID
            min_success_rate: Minimum success rate threshold
            limit: Maximum number of results

        Returns:
            List of high-success procedural memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND success_rate >= $2
                ORDER BY success_rate DESC, created_at DESC
                LIMIT {limit}
            """
            params = [user_id, min_success_rate]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching procedures by success rate: {e}")
            return []
