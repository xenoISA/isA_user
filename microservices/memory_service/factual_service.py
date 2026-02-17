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
from isa_common import AsyncQdrantClient

from .models import FactualMemory, MemoryOperationResult
from .factual_repository import FactualMemoryRepository

logger = logging.getLogger(__name__)


class FactualMemoryService:
    """Factual memory service with AI-powered fact extraction"""

    def __init__(self, repository: Optional[FactualMemoryRepository] = None):
        """
        Initialize factual memory service

        Args:
            repository: Optional repository instance for dependency injection
        """
        self.repository = repository or FactualMemoryRepository()
        self.consul_registry = None  # Service discovery handled by ConfigManager now

        # Get ISA Model URL via Consul service discovery or fallback
        self.model_url = self._get_model_url()

        # Initialize Qdrant client (async) - lazy connection
        # Use HTTP mode on localhost:6333 (not gRPC)
        self.qdrant = AsyncQdrantClient(
            host=os.getenv('QDRANT_HOST', 'localhost'),
            port=int(os.getenv('QDRANT_PORT', 6333)),
            user_id='memory_service'
        )
        self._collection_initialized = False  # Track if collection is ready

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

    async def _ensure_collection(self):
        """Ensure Qdrant collection exists (lazy async init)"""
        if self._collection_initialized:
            return

        collection_name = 'factual_memories'
        try:
            async with self.qdrant:
                # List collections to see what exists
                collections = await self.qdrant.list_collections()
                logger.info(f"Existing Qdrant collections: {collections}")

                if collection_name not in collections:
                    logger.info(f"Creating Qdrant collection: {collection_name}")
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
                    logger.info(f"Created Qdrant collection: {collection_name} with user_id index")
                else:
                    # Collection exists, log its info
                    info = await self.qdrant.get_collection_info(collection_name)
                    logger.info(f"Qdrant collection '{collection_name}' already exists: {info}")

            self._collection_initialized = True
        except Exception as e:
            logger.error(f"Error ensuring Qdrant collection: {e}", exc_info=True)

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
            # Ensure collection exists (lazy init)
            await self._ensure_collection()

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
                    # Handle object_value first (might be list or string)
                    object_value = fact.get('object_value', '')
                    if isinstance(object_value, list):
                        object_value = ', '.join(str(item) for item in object_value)
                    else:
                        object_value = str(object_value)

                    # Check for duplicate with object_value included
                    existing = await self.repository.find_duplicate_fact(
                        user_id=user_id,
                        subject=str(fact.get('subject', '')),
                        predicate=str(fact.get('predicate', '')),
                        object_value=object_value
                    )

                    if existing:
                        logger.info(f"Duplicate fact found, skipping: {fact.get('subject')} {fact.get('predicate')} {object_value}")
                        continue

                    # Create fact memory
                    memory_id = str(uuid.uuid4())

                    # Generate embedding for the fact content
                    fact_content = self._create_fact_content(fact)
                    logger.info(f"Generating embedding for fact: {fact_content[:100]}...")
                    embedding = await self._generate_embedding(fact_content)

                    if not embedding:
                        logger.warning(f"Failed to generate embedding for fact: {fact_content[:50]}")
                    else:
                        logger.info(f"Generated embedding with {len(embedding)} dimensions")

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
                        # Store embedding to Qdrant - ASYNC (only if embedding exists)
                        if embedding:
                            try:
                                async with self.qdrant:
                                    upsert_result = await self.qdrant.upsert_points('factual_memories', [{
                                        'id': memory_id,
                                        'vector': embedding,
                                        'payload': {
                                            'user_id': user_id,
                                            'fact_type': fact.get('fact_type', 'general'),
                                            'subject': str(fact.get('subject', '')),
                                            'created_at': datetime.now(timezone.utc).isoformat()
                                        }
                                    }])
                                logger.info(f"Stored embedding to Qdrant for memory {memory_id}, user_id={user_id}, result={upsert_result}")
                            except Exception as e:
                                logger.error(f"Failed to store embedding to Qdrant: {e}", exc_info=True)
                        else:
                            logger.warning(f"Skipping Qdrant storage for {memory_id} - no embedding")

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
        """Create readable content from fact structure with user context for better semantic search"""
        subject = fact.get('subject', '')
        predicate = fact.get('predicate', '')
        obj_value = fact.get('object_value', '')
        fact_type = fact.get('fact_type', 'general')

        if isinstance(obj_value, list):
            obj_value = ', '.join(str(item) for item in obj_value)

        # Include "user" context for better semantic matching with queries like "what is the user's name?"
        # This significantly improves similarity scores for user-centric queries
        if fact_type == 'person' and predicate in ['is named', 'name is', 'is called', 'named']:
            return f"The user's name is {subject}. {subject} {predicate} {obj_value}"
        elif fact_type in ['organization', 'workplace', 'employment']:
            return f"The user {subject} works at {obj_value}. {subject} {predicate} {obj_value}"
        elif fact_type in ['location', 'place', 'residence']:
            return f"The user {subject} lives in {obj_value}. {subject} {predicate} {obj_value}"
        elif fact_type == 'preference':
            return f"The user {subject} prefers {obj_value}. {subject} {predicate} {obj_value}"
        else:
            # Default: include "user" prefix for general facts
            return f"User fact: {subject} {predicate} {obj_value}"

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

    async def vector_search(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.15
    ) -> List[Dict[str, Any]]:
        """
        Search factual memories using vector similarity (Qdrant)

        Args:
            user_id: User identifier
            query: Search query text
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of matching memories with similarity scores
        """
        try:
            # Ensure collection exists
            await self._ensure_collection()

            # Generate embedding for query
            query_embedding = await self._generate_embedding(query)
            if not query_embedding:
                logger.warning("Failed to generate query embedding, falling back to text search")
                return await self.search_facts_by_subject(user_id, query, limit)

            logger.info(f"Generated query embedding with {len(query_embedding)} dimensions for: {query[:50]}...")

            # Debug: Check collection status
            async with self.qdrant:
                # Count total points in collection
                try:
                    point_count = await self.qdrant.count_points('factual_memories')
                    logger.info(f"Collection 'factual_memories' has {point_count} total points")
                except Exception as e:
                    logger.warning(f"Could not count points: {e}")

                # First try search without filter to see if embeddings exist at all
                try:
                    unfiltered_results = await self.qdrant.search(
                        collection_name='factual_memories',
                        vector=query_embedding,
                        limit=5,
                        score_threshold=None,  # No threshold
                        with_payload=True
                    )
                    if unfiltered_results:
                        logger.info(f"Unfiltered search found {len(unfiltered_results)} results, top scores: {[r.get('score') for r in unfiltered_results[:3]]}")
                        # Log user_ids in results
                        for r in unfiltered_results[:3]:
                            payload = r.get('payload', {})
                            logger.info(f"  - Point {r.get('id')}: user_id={payload.get('user_id')}, score={r.get('score')}")
                    else:
                        logger.warning("Unfiltered search returned no results - collection may be empty or embeddings not matching")
                except Exception as e:
                    logger.warning(f"Unfiltered search failed: {e}")

            # Search Qdrant for similar vectors using isa_common wrapper
            # The wrapper expects filter_conditions as a dict with 'must', 'should', 'must_not' keys
            filter_conditions = {
                "must": [
                    {"field": "user_id", "match": {"keyword": user_id}}
                ]
            }
            logger.info(f"Searching with filter for user_id={user_id}")

            async with self.qdrant:
                search_results = await self.qdrant.search_with_filter(
                    collection_name='factual_memories',
                    vector=query_embedding,
                    filter_conditions=filter_conditions,
                    limit=limit,
                    score_threshold=score_threshold,
                    with_payload=True
                )

            if not search_results:
                logger.info(f"No vector search results for user {user_id} with threshold {score_threshold}")
                return []

            # Get memory IDs and scores from results (returns list of dicts)
            memory_ids = [str(result['id']) for result in search_results]
            scores = {str(result['id']): result.get('score', 0.0) for result in search_results}

            logger.info(f"Vector search found {len(memory_ids)} matches in Qdrant for user {user_id}")

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
            logger.error(f"Vector search failed: {e}")
            # Fallback to text search
            return await self.search_facts_by_subject(user_id, query, limit)
