"""
Memory Service - Business Logic Orchestration Layer

Orchestrates memory operations across different memory types with AI-powered extraction.

Uses dependency injection for testability:
- Sub-services are injected, not created at import time
- Event publishers are lazily loaded
"""

import logging
import uuid
from typing import TYPE_CHECKING, Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

# Import only models (no I/O dependencies)
from .models import (
    MemoryType, MemoryModel, MemoryOperationResult,
    FactualMemory, ProceduralMemory, EpisodicMemory,
    SemanticMemory, WorkingMemory, SessionMemory,
    MemoryCreateRequest, MemoryUpdateRequest, MemoryListParams
)

# Type checking imports (not executed at runtime)
if TYPE_CHECKING:
    from .factual_service import FactualMemoryService
    from .procedural_service import ProceduralMemoryService
    from .episodic_service import EpisodicMemoryService
    from .semantic_service import SemanticMemoryService
    from .working_service import WorkingMemoryService
    from .session_service import SessionMemoryService

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Memory Service Orchestration Layer

    Coordinates memory operations across different memory type services with AI capabilities
    """

    def __init__(
        self,
        consul_registry=None,
        event_bus=None,
        factual_service=None,
        procedural_service=None,
        episodic_service=None,
        semantic_service=None,
        working_service=None,
        session_service=None,
    ):
        """
        Initialize memory service with all service instances

        Args:
            consul_registry: Optional ConsulRegistry for service discovery (deprecated - not used)
            event_bus: Optional NATS event bus for publishing events
            factual_service: Optional FactualMemoryService (for DI/testing)
            procedural_service: Optional ProceduralMemoryService (for DI/testing)
            episodic_service: Optional EpisodicMemoryService (for DI/testing)
            semantic_service: Optional SemanticMemoryService (for DI/testing)
            working_service: Optional WorkingMemoryService (for DI/testing)
            session_service: Optional SessionMemoryService (for DI/testing)
        """
        self.consul_registry = consul_registry
        self.event_bus = event_bus
        self._event_publishers_loaded = False

        # Support dependency injection - lazy import real services only if not provided
        if factual_service is not None:
            self.factual_service = factual_service
        else:
            from .factual_service import FactualMemoryService
            self.factual_service = FactualMemoryService()

        if procedural_service is not None:
            self.procedural_service = procedural_service
        else:
            from .procedural_service import ProceduralMemoryService
            self.procedural_service = ProceduralMemoryService()

        if episodic_service is not None:
            self.episodic_service = episodic_service
        else:
            from .episodic_service import EpisodicMemoryService
            self.episodic_service = EpisodicMemoryService()

        if semantic_service is not None:
            self.semantic_service = semantic_service
        else:
            from .semantic_service import SemanticMemoryService
            self.semantic_service = SemanticMemoryService()

        if working_service is not None:
            self.working_service = working_service
        else:
            from .working_service import WorkingMemoryService
            self.working_service = WorkingMemoryService()

        if session_service is not None:
            self.session_service = session_service
        else:
            from .session_service import SessionMemoryService
            self.session_service = SessionMemoryService()

        logger.info("Memory service initialized with AI capabilities")

    def _lazy_load_event_publishers(self):
        """Lazy load event publishers to avoid import-time I/O"""
        if not self._event_publishers_loaded:
            try:
                from .events.publishers import (
                    publish_memory_created,
                    publish_memory_updated,
                    publish_memory_deleted,
                    publish_factual_memory_stored,
                    publish_episodic_memory_stored,
                    publish_procedural_memory_stored,
                    publish_semantic_memory_stored,
                    publish_session_memory_deactivated
                )
                self._publish_memory_created = publish_memory_created
                self._publish_memory_updated = publish_memory_updated
                self._publish_memory_deleted = publish_memory_deleted
                self._publish_factual_memory_stored = publish_factual_memory_stored
                self._publish_episodic_memory_stored = publish_episodic_memory_stored
                self._publish_procedural_memory_stored = publish_procedural_memory_stored
                self._publish_semantic_memory_stored = publish_semantic_memory_stored
                self._publish_session_memory_deactivated = publish_session_memory_deactivated
            except ImportError:
                logger.warning("Event publishers not available")
                self._publish_memory_created = None
                self._publish_memory_updated = None
                self._publish_memory_deleted = None
                self._publish_factual_memory_stored = None
                self._publish_episodic_memory_stored = None
                self._publish_procedural_memory_stored = None
                self._publish_semantic_memory_stored = None
                self._publish_session_memory_deactivated = None
            self._event_publishers_loaded = True

    def _get_service(self, memory_type: MemoryType):
        """Get service for specified memory type"""
        service_map = {
            MemoryType.FACTUAL: self.factual_service,
            MemoryType.PROCEDURAL: self.procedural_service,
            MemoryType.EPISODIC: self.episodic_service,
            MemoryType.SEMANTIC: self.semantic_service,
            MemoryType.WORKING: self.working_service,
            MemoryType.SESSION: self.session_service
        }
        return service_map.get(memory_type)

    def _get_repository(self, memory_type: MemoryType):
        """Get repository for specified memory type"""
        service = self._get_service(memory_type)
        return service.repository if service else None

    def _memory_to_dict(self, memory: MemoryModel) -> Dict[str, Any]:
        """Convert memory model to dictionary for storage"""
        data = memory.model_dump()
        # Ensure id is set
        if not data.get('id'):
            data['id'] = str(uuid.uuid4())
        return data

    # ==================== General Memory Operations ====================

    async def create_memory(
        self,
        request: MemoryCreateRequest
    ) -> MemoryOperationResult:
        """
        Create a new memory

        Args:
            request: Memory creation request

        Returns:
            MemoryOperationResult with created memory details
        """
        try:
            repo = self._get_repository(request.memory_type)
            if not repo:
                return MemoryOperationResult(
                    success=False,
                    operation="create",
                    message=f"Invalid memory type: {request.memory_type}"
                )

            # Create base memory data (don't include embedding - it's stored in Qdrant)
            memory_data = {
                "id": str(uuid.uuid4()),
                "user_id": request.user_id,
                "memory_type": request.memory_type.value,
                "content": request.content,
                "importance_score": request.importance_score,
                "confidence": request.confidence,
                "access_count": 0,
                "tags": request.tags,
                "context": request.context,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }

            # Add memory-type-specific fields
            if request.memory_type == MemoryType.SESSION:
                # Session memory requires session_id and interaction_sequence
                memory_data["session_id"] = getattr(request, "session_id", None) or request.context.get("session_id", str(uuid.uuid4()))
                memory_data["interaction_sequence"] = getattr(request, "interaction_sequence", None) or request.context.get("interaction_sequence", 1)
                memory_data["conversation_state"] = request.context.get("conversation_state", {})
                memory_data["session_type"] = request.context.get("session_type", "chat")
                memory_data["active"] = request.context.get("active", True)
            elif request.memory_type == MemoryType.WORKING:
                # Working memory requires task_id, task_context, ttl_seconds, and expires_at
                task_id = getattr(request, "task_id", None)
                if not task_id:
                    task_id = request.context.get("task_id") if request.context else None
                if not task_id:
                    task_id = str(uuid.uuid4())
                memory_data["task_id"] = task_id

                task_context = getattr(request, "task_context", None)
                if not task_context:
                    task_context = request.context.get("task_context") if request.context else None
                if not task_context:
                    # Use the entire context as task_context if nothing else is available
                    task_context = request.context if request.context else {}
                # Ensure task_context is never None
                if task_context is None:
                    task_context = {}
                logger.info(f"task_context type: {type(task_context)}, value: {task_context}")
                memory_data["task_context"] = task_context

                # Calculate TTL and expiry
                ttl_minutes = getattr(request, "ttl_minutes", None) or request.context.get("ttl_minutes")
                ttl_seconds = getattr(request, "ttl_seconds", None) or request.context.get("ttl_seconds")
                if ttl_minutes:
                    memory_data["ttl_seconds"] = ttl_minutes * 60
                elif ttl_seconds:
                    memory_data["ttl_seconds"] = ttl_seconds
                else:
                    memory_data["ttl_seconds"] = 3600  # Default 1 hour

                # Set expires_at
                memory_data["expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=memory_data["ttl_seconds"])
                memory_data["priority"] = request.context.get("priority", 1)

            # Create memory
            logger.info(f"Creating {request.memory_type} memory with data keys: {list(memory_data.keys())}")
            logger.debug(f"Memory data: {memory_data}")
            result = await repo.create(memory_data)

            if result:
                # Publish memory.created event
                if self.event_bus:
                    try:
                        self._lazy_load_event_publishers()
                        if self._publish_memory_created:
                            await self._publish_memory_created(
                                event_bus=self.event_bus,
                                memory_id=result['id'],
                                memory_type=request.memory_type.value,
                                user_id=request.user_id,
                                content=memory_data.get('content', ''),
                                importance_score=request.importance_score,
                                tags=memory_data.get('tags'),
                                metadata=memory_data.get('metadata')
                            )
                    except Exception as e:
                        logger.error(f"Failed to publish memory.created event: {e}")

                return MemoryOperationResult(
                    success=True,
                    memory_id=result['id'],
                    operation="create",
                    message="Memory created successfully",
                    data=result
                )
            else:
                return MemoryOperationResult(
                    success=False,
                    operation="create",
                    message="Failed to create memory"
                )

        except Exception as e:
            logger.error(f"Error creating memory: {e}")
            return MemoryOperationResult(
                success=False,
                operation="create",
                message=f"Error: {str(e)}"
            )

    async def get_memory(
        self,
        memory_id: str,
        memory_type: MemoryType,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get memory by ID and type

        Args:
            memory_id: Memory ID
            memory_type: Type of memory
            user_id: Optional user ID for filtering

        Returns:
            Memory data or None
        """
        try:
            repo = self._get_repository(memory_type)
            if not repo:
                return None

            result = await repo.get_by_id(memory_id, user_id)

            # Increment access count if found
            if result and user_id:
                await repo.increment_access_count(memory_id, user_id)

            return result

        except Exception as e:
            logger.error(f"Error getting memory: {e}")
            return None

    async def list_memories(
        self,
        params: MemoryListParams
    ) -> List[Dict[str, Any]]:
        """
        List memories for a user

        Args:
            params: List parameters

        Returns:
            List of memories
        """
        try:
            if params.memory_type:
                # List specific memory type
                repo = self._get_repository(params.memory_type)
                if not repo:
                    return []

                filters = {}
                if params.importance_min is not None:
                    filters['importance_score'] = params.importance_min

                return await repo.list_by_user(
                    user_id=params.user_id,
                    limit=params.limit,
                    offset=params.offset,
                    filters=filters
                )
            else:
                # List all memory types
                all_memories = []
                for memory_type in MemoryType:
                    repo = self._get_repository(memory_type)
                    if repo:
                        memories = await repo.list_by_user(
                            user_id=params.user_id,
                            limit=params.limit,
                            offset=params.offset
                        )
                        all_memories.extend(memories)

                # Sort by created_at
                all_memories.sort(
                    key=lambda x: x.get('created_at', datetime.min),
                    reverse=True
                )

                return all_memories[:params.limit]

        except Exception as e:
            logger.error(f"Error listing memories: {e}")
            return []

    async def update_memory(
        self,
        memory_id: str,
        memory_type: MemoryType,
        request: MemoryUpdateRequest,
        user_id: str
    ) -> MemoryOperationResult:
        """
        Update a memory

        Args:
            memory_id: Memory ID
            memory_type: Type of memory
            request: Update request
            user_id: User ID

        Returns:
            MemoryOperationResult
        """
        try:
            repo = self._get_repository(memory_type)
            if not repo:
                return MemoryOperationResult(
                    success=False,
                    memory_id=memory_id,
                    operation="update",
                    message=f"Invalid memory type: {memory_type}"
                )

            # Build updates dict
            updates = {}
            if request.content is not None:
                updates['content'] = request.content
            if request.importance_score is not None:
                updates['importance_score'] = request.importance_score
            if request.confidence is not None:
                updates['confidence'] = request.confidence
            if request.tags is not None:
                updates['tags'] = request.tags
            if request.context is not None:
                updates['context'] = request.context

            if not updates:
                return MemoryOperationResult(
                    success=False,
                    memory_id=memory_id,
                    operation="update",
                    message="No fields to update"
                )

            success = await repo.update(memory_id, updates, user_id)

            if success:
                # Publish memory.updated event
                if self.event_bus:
                    try:
                        self._lazy_load_event_publishers()
                        if self._publish_memory_updated:
                            await self._publish_memory_updated(
                                event_bus=self.event_bus,
                                memory_id=memory_id,
                                memory_type=memory_type.value,
                                user_id=user_id,
                                updated_fields=list(updates.keys())
                            )
                    except Exception as e:
                        logger.error(f"Failed to publish memory.updated event: {e}")

                return MemoryOperationResult(
                    success=True,
                    memory_id=memory_id,
                    operation="update",
                    message="Memory updated successfully"
                )
            else:
                return MemoryOperationResult(
                    success=False,
                    memory_id=memory_id,
                    operation="update",
                    message="Memory not found or update failed"
                )

        except Exception as e:
            logger.error(f"Error updating memory: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=memory_id,
                operation="update",
                message=f"Error: {str(e)}"
            )

    async def delete_memory(
        self,
        memory_id: str,
        memory_type: MemoryType,
        user_id: str
    ) -> MemoryOperationResult:
        """
        Delete a memory

        Args:
            memory_id: Memory ID
            memory_type: Type of memory
            user_id: User ID

        Returns:
            MemoryOperationResult
        """
        try:
            repo = self._get_repository(memory_type)
            if not repo:
                return MemoryOperationResult(
                    success=False,
                    memory_id=memory_id,
                    operation="delete",
                    message=f"Invalid memory type: {memory_type}"
                )

            success = await repo.delete(memory_id, user_id)

            if success:
                # Publish memory.deleted event
                if self.event_bus:
                    try:
                        self._lazy_load_event_publishers()
                        if self._publish_memory_deleted:
                            await self._publish_memory_deleted(
                                event_bus=self.event_bus,
                                memory_id=memory_id,
                                memory_type=memory_type.value,
                                user_id=user_id
                            )
                    except Exception as e:
                        logger.error(f"Failed to publish memory.deleted event: {e}")

                return MemoryOperationResult(
                    success=True,
                    memory_id=memory_id,
                    operation="delete",
                    message="Memory deleted successfully"
                )
            else:
                return MemoryOperationResult(
                    success=False,
                    memory_id=memory_id,
                    operation="delete",
                    message="Memory not found or delete failed"
                )

        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=memory_id,
                operation="delete",
                message=f"Error: {str(e)}"
            )

    # ==================== AI-Powered Memory Storage ====================

    async def store_factual_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """Extract and store factual memories from dialog using AI"""
        result = await self.factual_service.store_factual_memory(
            user_id, dialog_content, importance_score
        )

        # Publish memory.factual.stored event
        if result.success and self.event_bus:
            try:
                self._lazy_load_event_publishers()
                if self._publish_factual_memory_stored:
                    await self._publish_factual_memory_stored(
                        event_bus=self.event_bus,
                        user_id=user_id,
                        count=result.count,
                        importance_score=importance_score,
                        source="dialog"
                    )
            except Exception as e:
                logger.error(f"Failed to publish memory.factual.stored event: {e}")

        return result

    async def store_episodic_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """Extract and store episodic memories from dialog using AI"""
        result = await self.episodic_service.store_episodic_memory(
            user_id, dialog_content, importance_score
        )

        # Publish memory.episodic.stored event
        if result.success and self.event_bus:
            try:
                self._lazy_load_event_publishers()
                if self._publish_episodic_memory_stored:
                    await self._publish_episodic_memory_stored(
                        event_bus=self.event_bus,
                        user_id=user_id,
                        count=result.count,
                        importance_score=importance_score,
                        source="dialog"
                    )
            except Exception as e:
                logger.error(f"Failed to publish memory.episodic.stored event: {e}")

        return result

    async def store_procedural_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """Extract and store procedural memories from dialog using AI"""
        result = await self.procedural_service.store_procedural_memory(
            user_id, dialog_content, importance_score
        )

        # Publish memory.procedural.stored event
        if result.success and self.event_bus:
            try:
                self._lazy_load_event_publishers()
                if self._publish_procedural_memory_stored:
                    await self._publish_procedural_memory_stored(
                        event_bus=self.event_bus,
                        user_id=user_id,
                        count=result.count,
                        importance_score=importance_score,
                        source="dialog"
                    )
            except Exception as e:
                logger.error(f"Failed to publish memory.procedural.stored event: {e}")

        return result

    async def store_semantic_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """Extract and store semantic memories from dialog using AI"""
        result = await self.semantic_service.store_semantic_memory(
            user_id, dialog_content, importance_score
        )

        # Publish memory.semantic.stored event
        if result.success and self.event_bus:
            try:
                self._lazy_load_event_publishers()
                if self._publish_semantic_memory_stored:
                    await self._publish_semantic_memory_stored(
                        event_bus=self.event_bus,
                        user_id=user_id,
                        count=result.count,
                        importance_score=importance_score,
                        source="dialog"
                    )
            except Exception as e:
                logger.error(f"Failed to publish memory.semantic.stored event: {e}")

        return result

    # ==================== Factual Memory Operations ====================

    async def search_facts_by_subject(
        self,
        user_id: str,
        subject: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search factual memories by subject"""
        return await self.factual_service.repository.search_by_subject(user_id, subject, limit)

    async def search_facts_by_type(
        self,
        user_id: str,
        fact_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search factual memories by type"""
        return await self.factual_service.repository.search_by_fact_type(user_id, fact_type, limit)

    async def vector_search_factual(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.4
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search for factual memories using Qdrant

        Args:
            user_id: User identifier
            query: Search query text
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of matching memories with similarity scores
        """
        return await self.factual_service.vector_search(user_id, query, limit, score_threshold)

    async def vector_search_episodic(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.15
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search for episodic memories using Qdrant

        Args:
            user_id: User identifier
            query: Search query text
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of matching memories with similarity scores
        """
        return await self.episodic_service.vector_search(user_id, query, limit, score_threshold)

    async def vector_search_procedural(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.15
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search for procedural memories using Qdrant

        Args:
            user_id: User identifier
            query: Search query text
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of matching memories with similarity scores
        """
        return await self.procedural_service.vector_search(user_id, query, limit, score_threshold)

    async def vector_search_semantic(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.15
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search for semantic memories using Qdrant

        Args:
            user_id: User identifier
            query: Search query text
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of matching memories with similarity scores
        """
        return await self.semantic_service.vector_search(user_id, query, limit, score_threshold)

    async def vector_search_working(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.15,
        include_expired: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search for working memories using Qdrant

        Args:
            user_id: User identifier
            query: Search query text
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            include_expired: Whether to include expired memories

        Returns:
            List of matching memories with similarity scores
        """
        return await self.working_service.vector_search(user_id, query, limit, score_threshold, include_expired)

    async def vector_search_session(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.15,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search for session memories using Qdrant

        Args:
            user_id: User identifier
            query: Search query text
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            session_id: Optional session ID to filter by

        Returns:
            List of matching memories with similarity scores
        """
        return await self.session_service.vector_search(user_id, query, limit, score_threshold, session_id)

    # ==================== Procedural Memory Operations ====================

    async def search_procedures_by_domain(
        self,
        user_id: str,
        domain: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search procedural memories by domain"""
        return await self.procedural_service.repository.search_by_domain(user_id, domain, limit)

    async def search_procedures_by_skill_type(
        self,
        user_id: str,
        skill_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search procedural memories by skill type"""
        return await self.procedural_service.repository.search_by_skill_type(user_id, skill_type, limit)

    # ==================== Episodic Memory Operations ====================

    async def search_episodes_by_timeframe(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search episodic memories by timeframe"""
        return await self.episodic_service.repository.search_by_timeframe(
            user_id, start_date, end_date, limit
        )

    async def search_episodes_by_event_type(
        self,
        user_id: str,
        event_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search episodic memories by event type"""
        return await self.episodic_service.repository.search_by_event_type(user_id, event_type, limit)

    # ==================== Semantic Memory Operations ====================

    async def search_concepts_by_category(
        self,
        user_id: str,
        category: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search semantic memories by category"""
        return await self.semantic_service.repository.search_by_category(user_id, category, limit)

    async def search_concepts_by_type(
        self,
        user_id: str,
        concept_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search semantic memories by concept type"""
        return await self.semantic_service.repository.search_by_concept_type(user_id, concept_type, limit)

    # ==================== Working Memory Operations ====================

    async def get_active_working_memories(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Get active working memories"""
        return await self.working_service.repository.get_active_memories(user_id)

    async def cleanup_expired_memories(
        self,
        user_id: Optional[str] = None
    ) -> MemoryOperationResult:
        """Clean up expired working memories"""
        try:
            count = await self.working_service.repository.cleanup_expired_memories(user_id)
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

    # ==================== Session Memory Operations ====================

    async def get_session_memories(
        self,
        user_id: str,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """Get memories for a specific session"""
        return await self.session_service.repository.get_session_memories(user_id, session_id)

    async def get_session_summary(
        self,
        user_id: str,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get session summary"""
        return await self.session_service.repository.get_session_summary(user_id, session_id)

    async def deactivate_session(
        self,
        user_id: str,
        session_id: str
    ) -> MemoryOperationResult:
        """Deactivate a session"""
        try:
            success = await self.session_service.repository.deactivate_session(user_id, session_id)
            if success:
                # Publish memory.session.deactivated event
                if self.event_bus:
                    try:
                        self._lazy_load_event_publishers()
                        if self._publish_session_memory_deactivated:
                            await self._publish_session_memory_deactivated(
                                event_bus=self.event_bus,
                                user_id=user_id,
                                session_id=session_id
                            )
                    except Exception as e:
                        logger.error(f"Failed to publish memory.session.deactivated event: {e}")

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

    # ==================== Statistics and Utility ====================

    async def get_memory_statistics(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get memory statistics for a user"""
        try:
            stats = {
                'user_id': user_id,
                'total_memories': 0,
                'by_type': {},
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Count each memory type
            for memory_type in MemoryType:
                repo = self._get_repository(memory_type)
                if repo:
                    count = await repo.get_count(user_id)
                    stats['by_type'][memory_type.value] = count
                    stats['total_memories'] += count

            return stats

        except Exception as e:
            logger.error(f"Error getting memory statistics: {e}")
            return {'error': str(e), 'user_id': user_id}

    async def check_connection(self) -> bool:
        """Check database connection"""
        try:
            return await self.factual_service.repository.check_connection()
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
