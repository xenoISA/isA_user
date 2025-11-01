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
from isa_common.qdrant_client import QdrantClient

from .models import WorkingMemory, MemoryOperationResult
from .working_repository import WorkingMemoryRepository

logger = logging.getLogger(__name__)


class WorkingMemoryService:
    """Working memory service for temporary task-related memories"""

    def __init__(self, repository: Optional[WorkingMemoryRepository] = None, consul_registry=None):
        """Initialize working memory service"""
        self.repository = repository or WorkingMemoryRepository()
        self.consul_registry = consul_registry
        self.model_url = self._get_model_url()

        # Initialize Qdrant client for vector storage
        self.qdrant = QdrantClient(
            host=os.getenv('QDRANT_HOST', 'isa-qdrant-grpc'),
            port=int(os.getenv('QDRANT_PORT', 50062)),
            user_id='memory_service'
        )
        self._ensure_collection()

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

    def _ensure_collection(self):
        """Ensure Qdrant collection exists for working memories"""
        collection_name = 'working_memories'
        try:
            if not self.qdrant.get_collection_info(collection_name):
                self.qdrant.create_collection(collection_name, vector_size=1536, distance='Cosine')
                logger.info(f"Created Qdrant collection: {collection_name}")
                self.qdrant.create_field_index(collection_name, 'user_id', 'keyword')
                self.qdrant.create_field_index(collection_name, 'task_id', 'keyword')
                logger.info(f"Created indexes on {collection_name}")
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
                # Store embedding to Qdrant
                try:
                    self.qdrant.upsert_points('working_memories', [{
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
