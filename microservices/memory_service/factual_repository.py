"""
Factual Memory Repository
Data access layer for factual memory operations
"""

import logging
from typing import List, Optional, Dict, Any

from .base_repository import BaseMemoryRepository

logger = logging.getLogger(__name__)


class FactualMemoryRepository(BaseMemoryRepository):
    """Repository for factual memory operations"""

    def __init__(self):
        """Initialize factual memory repository"""
        super().__init__(schema="memory", table_name="factual_memories")

    async def search_by_subject(
        self,
        user_id: str,
        subject: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search factual memories by subject

        Args:
            user_id: User ID
            subject: Subject to search for
            limit: Maximum number of results

        Returns:
            List of matching factual memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND subject ILIKE $2
                ORDER BY confidence DESC, created_at DESC
                LIMIT {limit}
            """
            params = [user_id, f"%{subject}%"]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching facts by subject: {e}")
            return []

    async def search_by_fact_type(
        self,
        user_id: str,
        fact_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search factual memories by fact type

        Args:
            user_id: User ID
            fact_type: Type of fact
            limit: Maximum number of results

        Returns:
            List of matching factual memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND fact_type = $2
                ORDER BY confidence DESC, created_at DESC
                LIMIT {limit}
            """
            params = [user_id, fact_type]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching facts by type: {e}")
            return []

    async def search_by_confidence(
        self,
        user_id: str,
        min_confidence: float = 0.7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search high-confidence factual memories

        Args:
            user_id: User ID
            min_confidence: Minimum confidence threshold
            limit: Maximum number of results

        Returns:
            List of high-confidence factual memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND confidence >= $2
                ORDER BY confidence DESC, created_at DESC
                LIMIT {limit}
            """
            params = [user_id, min_confidence]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching facts by confidence: {e}")
            return []

    async def search_by_source(
        self,
        user_id: str,
        source: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search factual memories by source

        Args:
            user_id: User ID
            source: Source of the fact
            limit: Maximum number of results

        Returns:
            List of matching factual memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND source ILIKE $2
                ORDER BY confidence DESC, created_at DESC
                LIMIT {limit}
            """
            params = [user_id, f"%{source}%"]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching facts by source: {e}")
            return []

    async def search_by_verification_status(
        self,
        user_id: str,
        verification_status: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search factual memories by verification status

        Args:
            user_id: User ID
            verification_status: Verification status
            limit: Maximum number of results

        Returns:
            List of matching factual memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND verification_status = $2
                ORDER BY confidence DESC, created_at DESC
                LIMIT {limit}
            """
            params = [user_id, verification_status]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching facts by verification status: {e}")
            return []

    async def find_duplicate_fact(
        self,
        user_id: str,
        subject: str,
        predicate: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find duplicate fact by subject and predicate

        Args:
            user_id: User ID
            subject: Fact subject
            predicate: Fact predicate

        Returns:
            Existing fact if found, None otherwise
        """
        try:
            # Note: query_row doesn't support LIMIT, use query instead
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND subject = $2 AND predicate = $3
                ORDER BY created_at DESC
            """
            params = [user_id, subject, predicate]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            # Return first result if any
            return results[0] if results and len(results) > 0 else None

        except Exception as e:
            logger.error(f"Error finding duplicate fact: {e}")
            return None

    async def search_by_predicate(
        self,
        user_id: str,
        predicate: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search factual memories by predicate

        Args:
            user_id: User ID
            predicate: Predicate to search for
            limit: Maximum number of results

        Returns:
            List of matching factual memories
        """
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE user_id = $1 AND predicate ILIKE $2
                ORDER BY confidence DESC, created_at DESC
                LIMIT {limit}
            """
            params = [user_id, f"%{predicate}%"]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results or []

        except Exception as e:
            logger.error(f"Error searching facts by predicate: {e}")
            return []
