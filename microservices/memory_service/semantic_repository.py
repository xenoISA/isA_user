"""
Semantic Memory Repository
Data access layer for semantic memory operations
"""

import logging
from typing import List, Optional, Dict, Any

from .base_repository import BaseMemoryRepository
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class SemanticMemoryRepository(BaseMemoryRepository):
    """Repository for semantic memory operations"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize semantic memory repository"""
        super().__init__(schema="memory", table_name="semantic_memories", config=config)

    async def search_by_category(
        self,
        user_id: str,
        category: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search semantic memories by category

        Args:
            user_id: User ID
            category: Category to search for
            limit: Maximum number of results

        Returns:
            List of matching semantic memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND category = $2
                ORDER BY importance_score DESC, created_at DESC
                LIMIT {limit}
            """
            params = [user_id, category]

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            # Deserialize each row to clean protobuf objects
            if results:
                return [self._deserialize_row(row) for row in results]
            return []

        except Exception as e:
            logger.error(f"Error searching concepts by category: {e}")
            return []

    async def search_by_concept_type(
        self,
        user_id: str,
        concept_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search semantic memories by concept type

        Args:
            user_id: User ID
            concept_type: Concept type to search for
            limit: Maximum number of results

        Returns:
            List of matching semantic memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND concept_type = $2
                ORDER BY importance_score DESC, created_at DESC
                LIMIT {limit}
            """
            params = [user_id, concept_type]

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            # Deserialize each row to clean protobuf objects
            if results:
                return [self._deserialize_row(row) for row in results]
            return []

        except Exception as e:
            logger.error(f"Error searching concepts by concept type: {e}")
            return []

    async def search_by_abstraction_level(
        self,
        user_id: str,
        abstraction_level: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search semantic memories by abstraction level

        Args:
            user_id: User ID
            abstraction_level: Abstraction level (low, medium, high)
            limit: Maximum number of results

        Returns:
            List of matching semantic memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND abstraction_level = $2
                ORDER BY importance_score DESC, created_at DESC
                LIMIT {limit}
            """
            params = [user_id, abstraction_level]

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            # Deserialize each row to clean protobuf objects
            if results:
                return [self._deserialize_row(row) for row in results]
            return []

        except Exception as e:
            logger.error(f"Error searching concepts by abstraction level: {e}")
            return []

    async def search_by_definition(
        self,
        user_id: str,
        keyword: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search semantic memories by definition keyword

        Args:
            user_id: User ID
            keyword: Keyword to search in definition
            limit: Maximum number of results

        Returns:
            List of matching semantic memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND definition ILIKE $2
                ORDER BY importance_score DESC, created_at DESC
                LIMIT {limit}
            """
            params = [user_id, f"%{keyword}%"]

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            # Deserialize each row to clean protobuf objects
            if results:
                return [self._deserialize_row(row) for row in results]
            return []

        except Exception as e:
            logger.error(f"Error searching concepts by definition: {e}")
            return []
