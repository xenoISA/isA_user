"""
Memory Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime


class MemoryServiceError(Exception):
    """Base exception for memory service errors"""
    pass


class MemoryNotFoundError(MemoryServiceError):
    """Memory resource not found"""
    pass


class MemoryValidationError(MemoryServiceError):
    """Memory data validation error"""
    pass


class MemoryPermissionError(MemoryServiceError):
    """Memory permission error"""
    pass


@runtime_checkable
class MemoryRepositoryProtocol(Protocol):
    """
    Interface for Memory Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    async def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new memory"""
        ...

    async def get_by_id(self, memory_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get memory by ID"""
        ...

    async def update(self, memory_id: str, updates: Dict[str, Any], user_id: str) -> bool:
        """Update a memory"""
        ...

    async def delete(self, memory_id: str, user_id: str) -> bool:
        """Delete a memory"""
        ...

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """List memories for a user"""
        ...

    async def increment_access_count(self, memory_id: str, user_id: str) -> bool:
        """Increment memory access count"""
        ...

    async def get_count(self, user_id: str) -> int:
        """Get count of memories for a user"""
        ...

    async def check_connection(self) -> bool:
        """Check database connection"""
        ...


@runtime_checkable
class MemoryTypeServiceProtocol(Protocol):
    """
    Interface for Memory Type Services (Factual, Episodic, etc.)

    Each memory type service must have a repository attribute.
    """

    repository: MemoryRepositoryProtocol


@runtime_checkable
class FactualServiceProtocol(MemoryTypeServiceProtocol):
    """Interface for Factual Memory Service"""

    async def store_factual_memory(
        self, user_id: str, dialog_content: str, importance_score: float
    ) -> Any:
        """Extract and store factual memories from dialog"""
        ...


@runtime_checkable
class EpisodicServiceProtocol(MemoryTypeServiceProtocol):
    """Interface for Episodic Memory Service"""

    async def store_episodic_memory(
        self, user_id: str, dialog_content: str, importance_score: float
    ) -> Any:
        """Extract and store episodic memories from dialog"""
        ...


@runtime_checkable
class ProceduralServiceProtocol(MemoryTypeServiceProtocol):
    """Interface for Procedural Memory Service"""

    async def store_procedural_memory(
        self, user_id: str, dialog_content: str, importance_score: float
    ) -> Any:
        """Extract and store procedural memories from dialog"""
        ...


@runtime_checkable
class SemanticServiceProtocol(MemoryTypeServiceProtocol):
    """Interface for Semantic Memory Service"""

    async def store_semantic_memory(
        self, user_id: str, dialog_content: str, importance_score: float
    ) -> Any:
        """Extract and store semantic memories from dialog"""
        ...


@runtime_checkable
class WorkingServiceProtocol(MemoryTypeServiceProtocol):
    """Interface for Working Memory Service"""
    pass


@runtime_checkable
class SessionServiceProtocol(MemoryTypeServiceProtocol):
    """Interface for Session Memory Service"""

    async def get_session_memories(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """Get memories for a session"""
        ...

    async def get_session_summary(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session summary"""
        ...

    async def deactivate_session(self, user_id: str, session_id: str) -> bool:
        """Deactivate a session"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...
