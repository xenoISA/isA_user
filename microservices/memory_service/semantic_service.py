"""
Semantic Memory Service
Business logic layer for semantic memory operations with AI extraction
"""

import logging
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import os

from isa_model.inference_client import AsyncISAModel
from isa_common import AsyncQdrantClient

from .models import SemanticMemory, MemoryOperationResult
from .semantic_repository import SemanticMemoryRepository

logger = logging.getLogger(__name__)


class SemanticMemoryService:
    """Semantic memory service with AI-powered concept extraction"""

    def __init__(self, repository: Optional[SemanticMemoryRepository] = None):
        """Initialize semantic memory service"""
        self.repository = repository or SemanticMemoryRepository()
        self.model_url = self._get_model_url()

        # Initialize Qdrant client (async) - lazy connection
        self.qdrant = AsyncQdrantClient(
            host=os.getenv('QDRANT_HOST', 'isa-qdrant-grpc'),
            port=int(os.getenv('QDRANT_PORT', 50062)),
            user_id='memory_service'
        )
        self._collection_initialized = False  # Track if collection is ready

        logger.info(f"Semantic Memory Service initialized with ISA Model URL: {self.model_url}")

    def _get_model_url(self) -> str:
        """Get ISA Model service URL from environment variable"""
        env_url = os.getenv('ISA_MODEL_URL')
        if env_url:
            return env_url
        return "http://localhost:8082"

    async def _ensure_collection(self):
        """Ensure Qdrant collection exists (lazy async init)"""
        if self._collection_initialized:
            return

        collection_name = 'semantic_memories'
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
                    logger.info(f"Created Qdrant collection: {collection_name}")
            self._collection_initialized = True
        except Exception as e:
            logger.warning(f"Error ensuring Qdrant collection: {e}")

    async def store_semantic_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """
        Extract and store semantic memories from dialog content using AI

        Args:
            user_id: User ID
            dialog_content: Dialog content to analyze
            importance_score: Importance score

        Returns:
            MemoryOperationResult
        """
        try:
            # Ensure collection exists (lazy init)
            await self._ensure_collection()

            # Extract concepts using LLM
            extraction_result = await self._extract_concepts(dialog_content)

            if not extraction_result['success']:
                return MemoryOperationResult(
                    success=False,
                    operation="store_semantic_memory",
                    message=f"Failed to extract concepts: {extraction_result.get('error')}"
                )

            concepts_data = extraction_result['data']
            stored_count = 0
            stored_ids = []

            for concept in concepts_data.get('concepts', []):
                if self._is_valid_concept(concept):
                    memory_id = str(uuid.uuid4())
                    content = concept.get('content', '')

                    # Generate embedding
                    embedding = await self._generate_embedding(content)

                    # PostgreSQL data (no embedding)
                    memory_data = {
                        "id": memory_id,
                        "user_id": user_id,
                        "memory_type": "semantic",
                        "content": content,
                        "concept_type": concept.get('concept_type', 'general'),
                        "definition": concept.get('definition', ''),
                        "properties": concept.get('properties', {}),
                        "abstraction_level": concept.get('abstraction_level', 'medium'),
                        "related_concepts": concept.get('related_concepts', []),
                        "category": concept.get('category', 'general'),
                        "importance_score": importance_score,
                        "confidence": float(concept.get('confidence', 0.8)),
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
                                await self.qdrant.upsert_points('semantic_memories', [{
                                    'id': memory_id,
                                    'vector': embedding,
                                    'payload': {
                                        'user_id': user_id,
                                        'concept_type': concept.get('concept_type', 'general'),
                                        'category': concept.get('category', 'general'),
                                        'abstraction_level': concept.get('abstraction_level', 'medium'),
                                        'created_at': datetime.now(timezone.utc).isoformat()
                                    }
                                }])
                            logger.info(f"Stored embedding to Qdrant for semantic memory {memory_id}")
                        except Exception as e:
                            logger.error(f"Failed to store embedding to Qdrant: {e}")

                        stored_count += 1
                        stored_ids.append(memory_id)

            if stored_count > 0:
                return MemoryOperationResult(
                    success=True,
                    operation="store_semantic_memory",
                    message=f"Successfully stored {stored_count} semantic memories",
                    affected_count=stored_count,
                    data={"memory_ids": stored_ids}
                )
            else:
                return MemoryOperationResult(
                    success=False,
                    operation="store_semantic_memory",
                    message="No valid concepts extracted"
                )

        except Exception as e:
            logger.error(f"Error storing semantic memory: {e}")
            return MemoryOperationResult(
                success=False,
                operation="store_semantic_memory",
                message=f"Error: {str(e)}"
            )

    async def _extract_concepts(self, dialog_content: str) -> Dict[str, Any]:
        """Extract concepts using ISA Model LLM"""
        try:
            system_prompt = """You are a semantic concept extraction system. Extract abstract concepts and definitions from the conversation and return them in JSON format.
For each concept, identify:
- concept_type: Type of concept (definition, principle, theory, rule, etc.)
- content: Main content describing the concept
- definition: Clear, concise definition
- category: Concept category (science, philosophy, technology, business, etc.)
- properties: Key properties as object {key: value}
- abstraction_level: "low", "medium", or "high"
- related_concepts: Related concept names (as array of strings)
- confidence: Confidence score (0.0-1.0)

Return ONLY valid JSON with a "concepts" array."""

            prompt = f"Extract semantic concepts from this conversation and return as JSON:\n\n{dialog_content}"

            async with AsyncISAModel(base_url=self.model_url) as client:
                response = await client.chat.completions.create(
                    model="gpt-4.1-nano",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    provider="openai"
                )

                content = response.choices[0].message.content
                if not content or content.strip() == "":
                    logger.error("Empty response from LLM")
                    return {'success': False, 'error': "Empty response from LLM", 'data': {'concepts': []}}

                result = json.loads(content)
                return {'success': True, 'data': result}

        except Exception as e:
            logger.error(f"Error extracting concepts: {e}")
            return {'success': False, 'error': str(e), 'data': {'concepts': []}}

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

    def _is_valid_concept(self, concept: Dict[str, Any]) -> bool:
        """Check if extracted concept is valid"""
        return bool(concept.get('content') and concept.get('definition') and concept.get('category'))

    # Search methods
    async def search_concepts_by_category(
        self,
        user_id: str,
        category: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search concepts by category"""
        return await self.repository.search_by_category(user_id, category, limit)

    async def search_concepts_by_type(
        self,
        user_id: str,
        concept_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search concepts by concept type"""
        return await self.repository.search_by_concept_type(user_id, concept_type, limit)
