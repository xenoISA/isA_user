"""
Factual Memory Service
Business logic layer for factual memory operations with AI extraction
"""

import logging
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import os

from isa_model.inference_client import AsyncISAModel
from isa_common.qdrant_client import QdrantClient

from .models import FactualMemory, MemoryOperationResult
from .factual_repository import FactualMemoryRepository

logger = logging.getLogger(__name__)


class FactualMemoryService:
    """Factual memory service with AI-powered fact extraction"""

    def __init__(self, repository: Optional[FactualMemoryRepository] = None, consul_registry=None):
        """
        Initialize factual memory service

        Args:
            repository: Optional repository instance for dependency injection
            consul_registry: Optional ConsulRegistry for service discovery
        """
        self.repository = repository or FactualMemoryRepository()
        self.consul_registry = consul_registry

        # Get ISA Model URL via Consul service discovery or fallback
        self.model_url = self._get_model_url()

        # Initialize Qdrant client for vector storage
        self.qdrant = QdrantClient(
            host=os.getenv('QDRANT_HOST', 'isa-qdrant-grpc'),
            port=int(os.getenv('QDRANT_PORT', 50062)),
            user_id='memory_service'
        )
        self._ensure_collection()

        logger.info(f"Factual Memory Service initialized with ISA Model URL: {self.model_url}")

    def _get_model_url(self) -> str:
        """Get ISA Model service URL via Consul or environment variable"""
        # Priority 1: Environment variable override
        env_url = os.getenv('ISA_MODEL_URL')
        if env_url:
            return env_url

        # Priority 2: Consul service discovery
        if self.consul_registry:
            try:
                service_url = self.consul_registry.get_service_endpoint("model_service")
                if service_url:
                    logger.info(f"Discovered model_service via Consul: {service_url}")
                    return service_url
            except Exception as e:
                logger.warning(f"Failed to discover model_service via Consul: {e}")

        # Priority 3: Default fallback
        return "http://localhost:8082"

    def _ensure_collection(self):
        """Ensure Qdrant collection exists for factual memories"""
        collection_name = 'factual_memories'
        try:
            if not self.qdrant.get_collection_info(collection_name):
                self.qdrant.create_collection(collection_name, vector_size=1536, distance='Cosine')
                logger.info(f"Created Qdrant collection: {collection_name}")
                self.qdrant.create_field_index(collection_name, 'user_id', 'keyword')
                logger.info(f"Created user_id index on {collection_name}")
        except Exception as e:
            logger.warning(f"Error ensuring Qdrant collection: {e}")

    async def store_factual_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """
        Extract and store factual memories from dialog content using AI

        Args:
            user_id: User ID
            dialog_content: Dialog content to analyze
            importance_score: Importance score for the memory

        Returns:
            MemoryOperationResult with operation details
        """
        try:
            # Extract facts using LLM
            extraction_result = await self._extract_facts(dialog_content)

            if not extraction_result['success']:
                return MemoryOperationResult(
                    success=False,
                    operation="store_factual_memory",
                    message=f"Failed to extract facts: {extraction_result.get('error')}"
                )

            facts_data = extraction_result['data']
            stored_count = 0
            stored_ids = []

            # Store each extracted fact
            for fact in facts_data.get('facts', []):
                if self._is_valid_fact(fact):
                    # Check for duplicate
                    existing = await self.repository.find_duplicate_fact(
                        user_id=user_id,
                        subject=str(fact.get('subject', '')),
                        predicate=str(fact.get('predicate', ''))
                    )

                    if existing:
                        logger.info(f"Duplicate fact found, skipping: {fact.get('subject')}")
                        continue

                    # Create fact memory
                    memory_id = str(uuid.uuid4())

                    # Handle object_value (might be list or string)
                    object_value = fact.get('object_value', '')
                    if isinstance(object_value, list):
                        object_value = ', '.join(str(item) for item in object_value)
                    else:
                        object_value = str(object_value)

                    # Generate embedding for the fact content
                    fact_content = self._create_fact_content(fact)
                    embedding = await self._generate_embedding(fact_content)

                    # PostgreSQL data (no embedding)
                    memory_data = {
                        "id": memory_id,
                        "user_id": user_id,
                        "memory_type": "factual",
                        "content": fact_content,
                        "fact_type": fact.get('fact_type', 'general'),
                        "subject": str(fact.get('subject', '')),
                        "predicate": str(fact.get('predicate', '')),
                        "object_value": object_value,
                        "fact_context": str(fact.get('context', '')) if fact.get('context') else None,
                        "source": "dialog",
                        "verification_status": "unverified",
                        "related_facts": [],
                        "importance_score": importance_score,
                        "confidence": float(fact.get('confidence', 0.8)),
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
                            self.qdrant.upsert_points('factual_memories', [{
                                'id': memory_id,
                                'vector': embedding,
                                'payload': {
                                    'user_id': user_id,
                                    'fact_type': fact.get('fact_type', 'general'),
                                    'subject': str(fact.get('subject', '')),
                                    'created_at': datetime.now(timezone.utc).isoformat()
                                }
                            }])
                            logger.info(f"Stored embedding to Qdrant for factual memory {memory_id}")
                        except Exception as e:
                            logger.error(f"Failed to store embedding to Qdrant: {e}")

                        stored_count += 1
                        stored_ids.append(memory_id)

            if stored_count > 0:
                return MemoryOperationResult(
                    success=True,
                    operation="store_factual_memory",
                    message=f"Successfully stored {stored_count} factual memories",
                    affected_count=stored_count,
                    data={"memory_ids": stored_ids}
                )
            else:
                return MemoryOperationResult(
                    success=False,
                    operation="store_factual_memory",
                    message="No valid facts extracted or all were duplicates"
                )

        except Exception as e:
            logger.error(f"Error storing factual memory: {e}")
            return MemoryOperationResult(
                success=False,
                operation="store_factual_memory",
                message=f"Error: {str(e)}"
            )

    async def _extract_facts(self, dialog_content: str) -> Dict[str, Any]:
        """
        Extract facts from dialog using ISA Model LLM

        Args:
            dialog_content: Dialog content to analyze

        Returns:
            Dictionary with extraction results
        """
        try:
            system_prompt = """You are a fact extraction system. Extract factual statements from the conversation and return them in JSON format.
For each fact, identify:
- fact_type: The category (person, place, event, preference, skill, etc.)
- subject: What the fact is about
- predicate: The relationship or property
- object_value: The value or related entity
- confidence: Confidence score (0.0-1.0)
- context: Additional context if relevant

Return ONLY valid JSON with a "facts" array. Example:
{"facts": [{"fact_type": "person", "subject": "John", "predicate": "lives in", "object_value": "Tokyo", "confidence": 0.9, "context": "mentioned in conversation"}]}"""

            prompt = f"Extract facts from this conversation and return as JSON:\n\n{dialog_content}"

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
                    return {
                        'success': False,
                        'error': "Empty response from LLM",
                        'data': {'facts': []}
                    }

                result = json.loads(content)
                return {
                    'success': True,
                    'data': result
                }

        except Exception as e:
            logger.error(f"Error extracting facts: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {'facts': []}
            }

    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using ISA Model

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
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

    def _is_valid_fact(self, fact: Dict[str, Any]) -> bool:
        """Check if extracted fact is valid"""
        required_fields = ['subject', 'predicate', 'object_value']
        return all(fact.get(field) for field in required_fields)

    def _create_fact_content(self, fact: Dict[str, Any]) -> str:
        """Create readable content from fact structure"""
        subject = fact.get('subject', '')
        predicate = fact.get('predicate', '')
        obj_value = fact.get('object_value', '')

        if isinstance(obj_value, list):
            obj_value = ', '.join(str(item) for item in obj_value)

        return f"{subject} {predicate} {obj_value}"

    # Search methods
    async def search_facts_by_subject(
        self,
        user_id: str,
        subject: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search factual memories by subject"""
        return await self.repository.search_by_subject(user_id, subject, limit)

    async def search_facts_by_type(
        self,
        user_id: str,
        fact_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search factual memories by type"""
        return await self.repository.search_by_fact_type(user_id, fact_type, limit)

    async def search_facts_by_confidence(
        self,
        user_id: str,
        min_confidence: float = 0.7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search high-confidence facts"""
        return await self.repository.search_by_confidence(user_id, min_confidence, limit)
