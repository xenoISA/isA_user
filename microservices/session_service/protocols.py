"""
Session Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

# Import only models (no I/O dependencies)
from .models import Session, SessionMessage


# ============================================================================
# Custom Exceptions - defined here to avoid importing repository
# ============================================================================


class SessionNotFoundError(Exception):
    """Session not found error - defined here to avoid importing repository"""
    pass


class MessageNotFoundError(Exception):
    """Message not found error - defined here to avoid importing repository"""
    pass


class MemoryNotFoundError(Exception):
    """Memory not found error - defined here to avoid importing repository"""
    pass


class SessionServiceError(Exception):
    """Base exception for session service errors"""
    pass


class SessionValidationError(SessionServiceError):
    """Session validation error"""
    pass


class DuplicateSessionError(SessionServiceError):
    """Duplicate session error"""
    pass


# ============================================================================
# Repository Protocols
# ============================================================================


@runtime_checkable
class SessionRepositoryProtocol(Protocol):
    """
    Interface for Session Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    async def create_session(self, session_data: Dict[str, Any]) -> Optional[Session]:
        """Create a new session"""
        ...

    async def get_by_session_id(self, session_id: str) -> Optional[Session]:
        """Get session by session ID"""
        ...

    async def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Session]:
        """Get sessions for a user with pagination"""
        ...

    async def update_session_status(self, session_id: str, status: str) -> bool:
        """Update session status"""
        ...

    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp"""
        ...

    async def increment_message_count(
        self,
        session_id: str,
        tokens_used: int = 0,
        cost_usd: float = 0.0
    ) -> bool:
        """Increment message count and update metrics"""
        ...

    async def expire_old_sessions(self, hours_old: int = 24) -> int:
        """Expire sessions older than specified hours"""
        ...


@runtime_checkable
class SessionMessageRepositoryProtocol(Protocol):
    """
    Interface for Session Message Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    async def create_message(self, message_data: Dict[str, Any]) -> Optional[SessionMessage]:
        """Create a new message"""
        ...

    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[SessionMessage]:
        """Get messages for a session with pagination"""
        ...

    async def get_message_by_id(self, message_id: str) -> Optional[SessionMessage]:
        """Get message by ID"""
        ...

    async def delete_session_messages(self, session_id: str) -> int:
        """Delete all messages for a session"""
        ...


# ============================================================================
# Service Client Protocols
# ============================================================================


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...


@runtime_checkable
class AccountClientProtocol(Protocol):
    """Interface for Account Service Client"""

    async def get_account_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user account profile"""
        ...

    async def check_user_exists(self, user_id: str) -> bool:
        """Check if user exists"""
        ...


@runtime_checkable
class MemoryClientProtocol(Protocol):
    """Interface for Memory Service Client"""

    async def create_session_memory(
        self,
        session_id: str,
        user_id: str,
        content: str,
        memory_type: str
    ) -> Optional[Dict[str, Any]]:
        """Create session memory"""
        ...

    async def get_session_memory(
        self,
        session_id: str,
        memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get session memory"""
        ...
