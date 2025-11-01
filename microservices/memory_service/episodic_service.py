"""
Episodic Memory Service
Business logic layer for episodic memory operations with AI extraction
"""

import logging
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import os

from isa_model.inference_client import AsyncISAModel
from isa_common.qdrant_client import QdrantClient

from .models import EpisodicMemory, MemoryOperationResult
from .episodic_repository import EpisodicMemoryRepository

logger = logging.getLogger(__name__)


class EpisodicMemoryService:
    """Episodic memory service with AI-powered episode extraction"""

    def __init__(self, repository: Optional[EpisodicMemoryRepository] = None, consul_registry=None):
        """Initialize episodic memory service"""
        self.repository = repository or EpisodicMemoryRepository()
        self.consul_registry = consul_registry
        self.model_url = self._get_model_url()

        # Initialize Qdrant client for vector storage
        self.qdrant = QdrantClient(
            host=os.getenv('QDRANT_HOST', 'isa-qdrant-grpc'),
            port=int(os.getenv('QDRANT_PORT', 50062)),
            user_id='memory_service'
        )
        self._ensure_collection()

        logger.info(f"Episodic Memory Service initialized with ISA Model URL: {self.model_url}")

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
        """Ensure Qdrant collection exists for episodic memories"""
        collection_name = 'episodic_memories'
        try:
            # Check if collection exists
            if not self.qdrant.get_collection_info(collection_name):
                # Create collection with text-embedding-3-small dimension (1536)
                self.qdrant.create_collection(
                    collection_name,
                    vector_size=1536,
                    distance='Cosine'
                )
                logger.info(f"Created Qdrant collection: {collection_name}")

                # Create index on user_id for faster filtering
                self.qdrant.create_field_index(collection_name, 'user_id', 'keyword')
                logger.info(f"Created user_id index on {collection_name}")
        except Exception as e:
            logger.warning(f"Error ensuring Qdrant collection: {e}")

    async def store_episodic_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """
        Extract and store episodic memories from dialog content using AI

        Args:
            user_id: User ID
            dialog_content: Dialog content to analyze
            importance_score: Importance score

        Returns:
            MemoryOperationResult
        """
        try:
            # Extract episodes using LLM
            extraction_result = await self._extract_episodes(dialog_content)

            if not extraction_result['success']:
                return MemoryOperationResult(
                    success=False,
                    operation="store_episodic_memory",
                    message=f"Failed to extract episodes: {extraction_result.get('error')}"
                )

            episodes_data = extraction_result['data']
            stored_count = 0
            stored_ids = []

            for episode in episodes_data.get('episodes', []):
                if self._is_valid_episode(episode):
                    memory_id = str(uuid.uuid4())
                    content = episode.get('content', '')

                    # Generate embedding
                    embedding = await self._generate_embedding(content)

                    # Parse episode date if provided
                    episode_date = None
                    if episode.get('episode_date'):
                        try:
                            episode_date = datetime.fromisoformat(episode['episode_date'])
                        except:
                            episode_date = None

                    # PostgreSQL data (no embedding)
                    memory_data = {
                        "id": memory_id,
                        "user_id": user_id,
                        "memory_type": "episodic",
                        "content": content,
                        "event_type": episode.get('event_type', 'general'),
                        "location": episode.get('location'),
                        "participants": episode.get('participants', []),
                        "emotional_valence": float(episode.get('emotional_valence', 0.0)),
                        "vividness": float(episode.get('vividness', 0.5)),
                        "episode_date": episode_date,
                        "importance_score": importance_score,
                        "confidence": float(episode.get('confidence', 0.8)),
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
                            self.qdrant.upsert_points('episodic_memories', [{
                                'id': memory_id,
                                'vector': embedding,
                                'payload': {
                                    'user_id': user_id,
                                    'event_type': episode.get('event_type', 'general'),
                                    'location': episode.get('location', ''),
                                    'episode_date': episode.get('episode_date', ''),
                                    'emotional_valence': float(episode.get('emotional_valence', 0.0)),
                                    'created_at': datetime.now(timezone.utc).isoformat()
                                }
                            }])
                            logger.info(f"Stored embedding to Qdrant for memory {memory_id}")
                        except Exception as e:
                            logger.error(f"Failed to store embedding to Qdrant: {e}")

                        stored_count += 1
                        stored_ids.append(memory_id)

            if stored_count > 0:
                return MemoryOperationResult(
                    success=True,
                    operation="store_episodic_memory",
                    message=f"Successfully stored {stored_count} episodic memories",
                    affected_count=stored_count,
                    data={"memory_ids": stored_ids}
                )
            else:
                return MemoryOperationResult(
                    success=False,
                    operation="store_episodic_memory",
                    message="No valid episodes extracted"
                )

        except Exception as e:
            logger.error(f"Error storing episodic memory: {e}")
            return MemoryOperationResult(
                success=False,
                operation="store_episodic_memory",
                message=f"Error: {str(e)}"
            )

    async def _extract_episodes(self, dialog_content: str) -> Dict[str, Any]:
        """Extract episodes using ISA Model LLM"""
        try:
            system_prompt = """You are an episodic memory extraction system. Extract personal experiences and events from the conversation and return them in JSON format.
For each episode, identify:
- event_type: Type of event (meeting, travel, celebration, work, etc.)
- content: Description of the episode
- location: Where it happened (if mentioned)
- participants: People involved (as array)
- emotional_valence: Emotional tone from -1 (negative) to 1 (positive)
- vividness: How vivid/detailed the memory is (0.0-1.0)
- episode_date: When it happened (if mentioned, ISO format YYYY-MM-DD)
- confidence: Confidence score (0.0-1.0)

Return ONLY valid JSON with an "episodes" array."""

            prompt = f"Extract episodic memories from this conversation and return as JSON:\n\n{dialog_content}"

            async with AsyncISAModel(base_url=self.model_url) as client:
                response = await client.chat.completions.create(
                    model="gpt-4.1-nano",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    provider="openai"  # Use OpenAI gpt-4.1-nano (compatible with PyPI version)
                )

                result = json.loads(response.choices[0].message.content)
                return {'success': True, 'data': result}

        except Exception as e:
            logger.error(f"Error extracting episodes: {e}")
            return {'success': False, 'error': str(e), 'data': {'episodes': []}}

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using ISA Model"""
        try:
            async with AsyncISAModel(base_url=self.model_url) as client:
                embedding = await client.embeddings.create(
                    input=text,
                    model="text-embedding-3-small",
                    provider="openai"  # Explicitly specify provider
                )
                return embedding.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    def _is_valid_episode(self, episode: Dict[str, Any]) -> bool:
        """Check if extracted episode is valid"""
        return bool(episode.get('content') and episode.get('event_type'))

    # Search methods
    async def search_episodes_by_timeframe(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search episodes by timeframe"""
        return await self.repository.search_by_timeframe(user_id, start_date, end_date, limit)

    async def search_episodes_by_event_type(
        self,
        user_id: str,
        event_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search episodes by event type"""
        return await self.repository.search_by_event_type(user_id, event_type, limit)

    async def search_episodes_by_location(
        self,
        user_id: str,
        location: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search episodes by location"""
        return await self.repository.search_by_location(user_id, location, limit)
