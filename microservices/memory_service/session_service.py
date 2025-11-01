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
from isa_common.qdrant_client import QdrantClient

from .models import SessionMemory, MemoryOperationResult
from .session_repository import SessionMemoryRepository

logger = logging.getLogger(__name__)


class SessionMemoryService:
    """Session memory service for conversation context"""

    def __init__(self, repository: Optional[SessionMemoryRepository] = None, consul_registry=None):
        """Initialize session memory service"""
        self.repository = repository or SessionMemoryRepository()
        self.consul_registry = consul_registry
        self.model_url = self._get_model_url()

        # Initialize Qdrant client for vector storage
        self.qdrant = QdrantClient(
            host=os.getenv('QDRANT_HOST', 'isa-qdrant-grpc'),
            port=int(os.getenv('QDRANT_PORT', 50062)),
            user_id='memory_service'
        )
        self._ensure_collection()

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

    def _ensure_collection(self):
        """Ensure Qdrant collection exists for session memories"""
        collection_name = 'session_memories'
        try:
            if not self.qdrant.get_collection_info(collection_name):
                self.qdrant.create_collection(collection_name, vector_size=1536, distance='Cosine')
                logger.info(f"Created Qdrant collection: {collection_name}")
                self.qdrant.create_field_index(collection_name, 'user_id', 'keyword')
                self.qdrant.create_field_index(collection_name, 'session_id', 'keyword')
                logger.info(f"Created indexes on {collection_name}")
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
                # Store embedding to Qdrant
                try:
                    self.qdrant.upsert_points('session_memories', [{
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
