"""
Session Memory Service
Business logic layer for session memory operations
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import os

from isa_model.inference_client import AsyncISAModel
from isa_common import AsyncQdrantClient

from .models import SessionMemory, MemoryOperationResult
from .session_repository import SessionMemoryRepository

logger = logging.getLogger(__name__)


class SessionMemoryService:
    """Session memory service for conversation context"""

    def __init__(self, repository: Optional[SessionMemoryRepository] = None):
        """Initialize session memory service"""
        self.repository = repository or SessionMemoryRepository()
        self.consul_registry = None  # Service discovery handled by ConfigManager now
        self.model_url = self._get_model_url()

        # Initialize Qdrant client (async) - lazy connection
        self.qdrant = AsyncQdrantClient(
            host=os.getenv('QDRANT_HOST', 'localhost'),
            port=int(os.getenv('QDRANT_PORT', 6333)),
            user_id='memory_service'
        )
        self._collection_initialized = False  # Track if collection is ready

        logger.info(f"Session Memory Service initialized with ISA Model URL: {self.model_url}")

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

        collection_name = 'session_memories'
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
                        field_name='session_id',
                        field_type='keyword'
                    )
                    logger.info(f"Created Qdrant collection: {collection_name}")
            self._collection_initialized = True
        except Exception as e:
            logger.warning(f"Error ensuring Qdrant collection: {e}")

    async def store_session_memory(
        self,
        user_id: str,
        session_id: str,
        content: str,
        interaction_sequence: int,
        conversation_state: Dict[str, Any],
        session_type: str = "chat"
    ) -> MemoryOperationResult:
        """
        Store session memory

        Args:
            user_id: User ID
            session_id: Session ID
            content: Memory content
            interaction_sequence: Sequence number in session
            conversation_state: Current conversation state
            session_type: Type of session

        Returns:
            MemoryOperationResult
        """
        try:
            # Ensure collection exists (lazy init)
            await self._ensure_collection()

            memory_id = str(uuid.uuid4())

            # Generate embedding
            embedding = await self._generate_embedding(content)

            # PostgreSQL data (no embedding)
            memory_data = {
                "id": memory_id,
                "user_id": user_id,
                "memory_type": "session",
                "content": content,
                "session_id": session_id,
                "interaction_sequence": interaction_sequence,
                "conversation_state": conversation_state,
                "session_type": session_type,
                "active": True,
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
                        await self.qdrant.upsert_points('session_memories', [{
                            'id': memory_id,
                            'vector': embedding,
                            'payload': {
                                'user_id': user_id,
                                'session_id': session_id,
                                'session_type': session_type,
                                'interaction_sequence': interaction_sequence,
                                'active': True,
                                'created_at': datetime.now(timezone.utc).isoformat()
                            }
                        }])
                    logger.info(f"Stored embedding to Qdrant for session memory {memory_id}")
                except Exception as e:
                    logger.error(f"Failed to store embedding to Qdrant: {e}")

                return MemoryOperationResult(
                    success=True,
                    memory_id=memory_id,
                    operation="store_session_memory",
                    message="Session memory stored successfully",
                    data=result
                )
            else:
                return MemoryOperationResult(
                    success=False,
                    operation="store_session_memory",
                    message="Failed to store session memory"
                )

        except Exception as e:
            logger.error(f"Error storing session memory: {e}")
            return MemoryOperationResult(
                success=False,
                operation="store_session_memory",
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

    async def get_session_memories(
        self,
        user_id: str,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """Get all memories for a session"""
        return await self.repository.get_session_memories(user_id, session_id)

    async def get_session_summary(
        self,
        user_id: str,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get session summary"""
        return await self.repository.get_session_summary(user_id, session_id)

    async def deactivate_session(
        self,
        user_id: str,
        session_id: str
    ) -> MemoryOperationResult:
        """Deactivate all memories in a session"""
        try:
            success = await self.repository.deactivate_session(user_id, session_id)
            if success:
                return MemoryOperationResult(
                    success=True,
                    operation="deactivate_session",
                    message="Session deactivated successfully"
                )
            else:
                return MemoryOperationResult(
                    success=False,
                    operation="deactivate_session",
                    message="Session not found or already deactivated"
                )
        except Exception as e:
            logger.error(f"Error deactivating session: {e}")
            return MemoryOperationResult(
                success=False,
                operation="deactivate_session",
                message=f"Error: {str(e)}"
            )

    async def get_active_sessions(
        self,
        user_id: str
    ) -> List[str]:
        """Get list of active session IDs"""
        return await self.repository.get_active_sessions(user_id)

    async def vector_search(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.15,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search session memories using vector similarity (Qdrant)

        Args:
            user_id: User identifier
            query: Search query text
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0.0-1.0)
            session_id: Optional session ID to filter by

        Returns:
            List of matching memories with similarity scores
        """
        try:
            # Ensure collection exists
            await self._ensure_collection()

            # Generate embedding for query
            query_embedding = await self._generate_embedding(query)
            if not query_embedding:
                logger.warning("Failed to generate query embedding for session memory")
                return []

            logger.info(f"Generated query embedding with {len(query_embedding)} dimensions for session search: {query[:50]}...")

            # Build filter conditions
            filter_conditions = {
                "must": [
                    {"field": "user_id", "match": {"keyword": user_id}}
                ]
            }

            # Add session_id filter if provided
            if session_id:
                filter_conditions["must"].append(
                    {"field": "session_id", "match": {"keyword": session_id}}
                )

            async with self.qdrant:
                search_results = await self.qdrant.search_with_filter(
                    collection_name='session_memories',
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

            logger.info(f"Vector search found {len(memory_ids)} session memory matches for user {user_id}")

            # Fetch full memory data from PostgreSQL
            memories = await self.repository.get_by_ids(memory_ids)

            # Add similarity scores to results
            for memory in memories:
                memory_id = memory.get('id')
                memory['similarity_score'] = scores.get(memory_id, 0.0)

            # Sort by score descending
            memories.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)

            return memories

        except Exception as e:
            logger.error(f"Session memory vector search failed: {e}")
            return []
