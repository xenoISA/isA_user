"""
Procedural Memory Service
Business logic layer for procedural memory operations with AI extraction
"""

import logging
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import os

from isa_model.inference_client import AsyncISAModel
from isa_common import AsyncQdrantClient

from .models import ProceduralMemory, MemoryOperationResult
from .procedural_repository import ProceduralMemoryRepository

logger = logging.getLogger(__name__)


class ProceduralMemoryService:
    """Procedural memory service with AI-powered procedure extraction"""

    def __init__(self, repository: Optional[ProceduralMemoryRepository] = None):
        """Initialize procedural memory service"""
        self.repository = repository or ProceduralMemoryRepository()
        self.consul_registry = None  # Service discovery handled by ConfigManager now
        self.model_url = self._get_model_url()

        # Initialize Qdrant client (async) - lazy connection
        self.qdrant = AsyncQdrantClient(
            host=os.getenv('QDRANT_HOST', 'isa-qdrant-grpc'),
            port=int(os.getenv('QDRANT_PORT', 50062)),
            user_id='memory_service'
        )
        self._collection_initialized = False  # Track if collection is ready

        logger.info(f"Procedural Memory Service initialized with ISA Model URL: {self.model_url}")

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

        collection_name = 'procedural_memories'
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

    async def store_procedural_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """
        Extract and store procedural memories from dialog content using AI

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

            # Extract procedures using LLM
            extraction_result = await self._extract_procedures(dialog_content)

            if not extraction_result['success']:
                return MemoryOperationResult(
                    success=False,
                    operation="store_procedural_memory",
                    message=f"Failed to extract procedures: {extraction_result.get('error')}"
                )

            procedures_data = extraction_result['data']
            stored_count = 0
            stored_ids = []

            for procedure in procedures_data.get('procedures', []):
                if self._is_valid_procedure(procedure):
                    memory_id = str(uuid.uuid4())
                    content = procedure.get('content', '')

                    # Generate embedding
                    embedding = await self._generate_embedding(content)

                    # PostgreSQL data (no embedding)
                    memory_data = {
                        "id": memory_id,
                        "user_id": user_id,
                        "memory_type": "procedural",
                        "content": content,
                        "skill_type": procedure.get('skill_type', 'general'),
                        "steps": procedure.get('steps', []),
                        "prerequisites": procedure.get('prerequisites', []),
                        "difficulty_level": procedure.get('difficulty_level', 'medium'),
                        "success_rate": float(procedure.get('success_rate', 0.0)),
                        "domain": procedure.get('domain', 'general'),
                        "importance_score": importance_score,
                        "confidence": float(procedure.get('confidence', 0.8)),
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
                                await self.qdrant.upsert_points('procedural_memories', [{
                                    'id': memory_id,
                                    'vector': embedding,
                                    'payload': {
                                        'user_id': user_id,
                                        'skill_type': procedure.get('skill_type', 'general'),
                                        'domain': procedure.get('domain', 'general'),
                                        'difficulty_level': procedure.get('difficulty_level', 'medium'),
                                        'created_at': datetime.now(timezone.utc).isoformat()
                                    }
                                }])
                            logger.info(f"Stored embedding to Qdrant for procedural memory {memory_id}")
                        except Exception as e:
                            logger.error(f"Failed to store embedding to Qdrant: {e}")

                        stored_count += 1
                        stored_ids.append(memory_id)

            if stored_count > 0:
                return MemoryOperationResult(
                    success=True,
                    operation="store_procedural_memory",
                    message=f"Successfully stored {stored_count} procedural memories",
                    affected_count=stored_count,
                    data={"memory_ids": stored_ids}
                )
            else:
                return MemoryOperationResult(
                    success=False,
                    operation="store_procedural_memory",
                    message="No valid procedures extracted"
                )

        except Exception as e:
            logger.error(f"Error storing procedural memory: {e}")
            return MemoryOperationResult(
                success=False,
                operation="store_procedural_memory",
                message=f"Error: {str(e)}"
            )

    async def _extract_procedures(self, dialog_content: str) -> Dict[str, Any]:
        """Extract procedures using ISA Model LLM"""
        try:
            system_prompt = """You are a procedural knowledge extraction system. Extract how-to knowledge and procedures from the conversation and return them in JSON format.
For each procedure, identify:
- skill_type: Type of skill or procedure
- content: Overall description
- steps: Array of steps, each with {order: number, description: string}
- domain: Domain or category (cooking, programming, sports, etc.)
- difficulty_level: "easy", "medium", or "hard"
- prerequisites: Required prior knowledge (as array of strings)
- success_rate: Estimated success rate (0.0-1.0)
- confidence: Confidence score (0.0-1.0)

Return ONLY valid JSON with a "procedures" array."""

            prompt = f"Extract procedural knowledge from this conversation and return as JSON:\n\n{dialog_content}"

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
                    return {'success': False, 'error': "Empty response from LLM", 'data': {'procedures': []}}

                result = json.loads(content)
                return {'success': True, 'data': result}

        except Exception as e:
            logger.error(f"Error extracting procedures: {e}")
            return {'success': False, 'error': str(e), 'data': {'procedures': []}}

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

    def _is_valid_procedure(self, procedure: Dict[str, Any]) -> bool:
        """Check if extracted procedure is valid"""
        return bool(procedure.get('content') and procedure.get('skill_type') and procedure.get('steps'))

    # Search methods
    async def search_procedures_by_domain(
        self,
        user_id: str,
        domain: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search procedures by domain"""
        return await self.repository.search_by_domain(user_id, domain, limit)

    async def search_procedures_by_skill_type(
        self,
        user_id: str,
        skill_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search procedures by skill type"""
        return await self.repository.search_by_skill_type(user_id, skill_type, limit)
