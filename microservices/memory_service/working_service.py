"""
Working Memory Service
Business logic layer for working memory operations
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
import os

from isa_model.inference_client import AsyncISAModel
from isa_common import AsyncQdrantClient

from .models import WorkingMemory, MemoryOperationResult
from .working_repository import WorkingMemoryRepository

logger = logging.getLogger(__name__)


class WorkingMemoryService:
    """Working memory service for temporary task-related memories"""

    def __init__(self, repository: Optional[WorkingMemoryRepository] = None):
        """Initialize working memory service"""
        self.repository = repository or WorkingMemoryRepository()
        self.consul_registry = None  # Service discovery handled by ConfigManager now
        self.model_url = self._get_model_url()

        # Initialize Qdrant client (async) - lazy connection
        self.qdrant = AsyncQdrantClient(
            host=os.getenv('QDRANT_HOST', 'localhost'),
            port=int(os.getenv('QDRANT_PORT', 6333)),
            user_id='memory_service'
        )
        self._collection_initialized = False  # Track if collection is ready

        logger.info(f"Working Memory Service initialized with ISA Model URL: {self.model_url}")

    def _get_model_url(self) -> str:
        """Get ISA Model service URL via Consul or environment variable"""
        env_url = os.getenv('ISA_MODEL_URL')
        if env_url:
            return env_url
        if self.consul_registry:
            try:
                service_url = self.consul_registry.get_service_endpoint("model_service")
                if service_url:
                    logger.info(f"Discovered model_service via Consul: {service_url}")
                    return service_url
            except Exception as e:
                logger.warning(f"Failed to discover model_service via Consul: {e}")
        return "http://localhost:8082"

    async def _ensure_collection(self):
        """Ensure Qdrant collection exists (lazy async init)"""
        if self._collection_initialized:
            return

        collection_name = 'working_memories'
        try:
            async with self.qdrant:
                info = await self.qdrant.get_collection_info(collection_name)
                if not info:
                    await self.qdrant.create_collection(
                        collection_name=collection_name,
                        vector_size=1536,
                        distance='Cosine'
                    )
                    await self.qdrant.create_field_index(
                        collection_name=collection_name,
                        field_name='user_id',
                        field_type='keyword'
                    )
                    await self.qdrant.create_field_index(
                        collection_name=collection_name,
                        field_name='task_id',
                        field_type='keyword'
                    )
                    logger.info(f"Created Qdrant collection: {collection_name}")
            self._collection_initialized = True
        except Exception as e:
            logger.warning(f"Error ensuring Qdrant collection: {e}")

    async def store_working_memory(
        self,
        user_id: str,
        content: str,
        task_id: str,
        task_context: Dict[str, Any],
        priority: int = 5,
        ttl_seconds: int = 3600
    ) -> MemoryOperationResult:
        """
        Store working memory for current task

        Args:
            user_id: User ID
            content: Memory content
            task_id: Associated task ID
            task_context: Task context data
            priority: Priority level (1-10)
            ttl_seconds: Time to live in seconds

        Returns:
            MemoryOperationResult
        """
        try:
            # Ensure collection exists (lazy init)
            await self._ensure_collection()

            memory_id = str(uuid.uuid4())

            # Generate embedding
            embedding = await self._generate_embedding(content)

            # Calculate expiration time
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

            # PostgreSQL data (no embedding)
            memory_data = {
                "id": memory_id,
                "user_id": user_id,
                "memory_type": "working",
                "content": content,
                "task_id": task_id,
                "task_context": task_context,
                "ttl_seconds": ttl_seconds,
                "priority": priority,
                "expires_at": expires_at,
                "importance_score": 0.5,
                "confidence": 0.8,
                "access_count": 0,
                "tags": [],
                "context": {},
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }

            # Store to PostgreSQL
            result = await self.repository.create(memory_data)

            if result:
                # Store embedding to Qdrant - ASYNC
                try:
                    async with self.qdrant:
                        await self.qdrant.upsert_points('working_memories', [{
                            'id': memory_id,
                            'vector': embedding,
                            'payload': {
                                'user_id': user_id,
                                'task_id': task_id,
                                'priority': priority,
                                'expires_at': expires_at.isoformat(),
                                'created_at': datetime.now(timezone.utc).isoformat()
                            }
                        }])
                    logger.info(f"Stored embedding to Qdrant for working memory {memory_id}")
                except Exception as e:
                    logger.error(f"Failed to store embedding to Qdrant: {e}")

                return MemoryOperationResult(
                    success=True,
                    memory_id=memory_id,
                    operation="store_working_memory",
                    message="Working memory stored successfully",
                    data=result
                )
            else:
                return MemoryOperationResult(
                    success=False,
                    operation="store_working_memory",
                    message="Failed to store working memory"
                )

        except Exception as e:
            logger.error(f"Error storing working memory: {e}")
            return MemoryOperationResult(
                success=False,
                operation="store_working_memory",
                message=f"Error: {str(e)}"
            )

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using ISA Model"""
        try:
            async with AsyncISAModel(base_url=self.model_url) as client:
                embedding = await client.embeddings.create(
                    input=text,
                    model="text-embedding-3-small"
                )
                return embedding.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    async def get_active_working_memories(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Get active (non-expired) working memories"""
        return await self.repository.get_active_memories(user_id)

    async def cleanup_expired_memories(
        self,
        user_id: Optional[str] = None
    ) -> MemoryOperationResult:
        """Clean up expired working memories"""
        try:
            count = await self.repository.cleanup_expired_memories(user_id)
            return MemoryOperationResult(
                success=True,
                operation="cleanup",
                message=f"Cleaned up {count} expired memories",
                affected_count=count
            )
        except Exception as e:
            logger.error(f"Error cleaning up expired memories: {e}")
            return MemoryOperationResult(
                success=False,
                operation="cleanup",
                message=f"Error: {str(e)}"
            )

    async def search_by_task_id(
        self,
        user_id: str,
        task_id: str,
        include_expired: bool = False
    ) -> List[Dict[str, Any]]:
        """Search working memories by task ID"""
        return await self.repository.search_by_task_id(user_id, task_id, include_expired)

    async def vector_search(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.15,
        include_expired: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search working memories using vector similarity (Qdrant)

        Args:
            user_id: User identifier
            query: Search query text
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0.0-1.0)
            include_expired: Whether to include expired memories

        Returns:
            List of matching memories with similarity scores
        """
        try:
            # Ensure collection exists
            await self._ensure_collection()

            # Generate embedding for query
            query_embedding = await self._generate_embedding(query)
            if not query_embedding:
                logger.warning("Failed to generate query embedding for working memory")
                return []

            logger.info(f"Generated query embedding with {len(query_embedding)} dimensions for working memory search: {query[:50]}...")

            # Search Qdrant for similar vectors with user_id filter
            filter_conditions = {
                "must": [
                    {"field": "user_id", "match": {"keyword": user_id}}
                ]
            }

            async with self.qdrant:
                search_results = await self.qdrant.search_with_filter(
                    collection_name='working_memories',
                    vector=query_embedding,
                    filter_conditions=filter_conditions,
                    limit=limit,
                    score_threshold=score_threshold,
                    with_payload=True
                )

            if not search_results:
                logger.info(f"No vector search results for user {user_id} with threshold {score_threshold}")
                return []

            # Get memory IDs and scores from results
            memory_ids = [str(result['id']) for result in search_results]
            scores = {str(result['id']): result.get('score', 0.0) for result in search_results}

            logger.info(f"Vector search found {len(memory_ids)} working memory matches for user {user_id}")

            # Fetch full memory data from PostgreSQL
            memories = await self.repository.get_by_ids(memory_ids)

            # Filter expired if needed
            if not include_expired:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                memories = [m for m in memories if m.get('expires_at') and m['expires_at'] > now]

            # Add similarity scores to results
            for memory in memories:
                memory_id = memory.get('id')
                memory['similarity_score'] = scores.get(memory_id, 0.0)

            # Sort by score descending
            memories.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)

            return memories

        except Exception as e:
            logger.error(f"Working memory vector search failed: {e}")
            return []
