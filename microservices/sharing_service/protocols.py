"""
Sharing Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from .models import Share


# ============================================================================
# Custom Exceptions
# ============================================================================


class ShareNotFoundError(Exception):
    """Share not found"""
    pass


class ShareExpiredError(Exception):
    """Share link has expired"""
    pass


class ShareServiceError(Exception):
    """Base exception for sharing service errors"""
    pass


class ShareValidationError(ShareServiceError):
    """Validation error"""
    pass


class SharePermissionError(ShareServiceError):
    """Permission denied"""
    pass


# ============================================================================
# Repository Protocols
# ============================================================================


@runtime_checkable
class ShareRepositoryProtocol(Protocol):
    """Interface for Share Repository"""

    async def create_share(self, share_data: Dict[str, Any]) -> Optional[Share]:
        """Create a new share record"""
        ...

    async def get_by_token(self, share_token: str) -> Optional[Share]:
        """Get share by token"""
        ...

    async def get_by_id(self, share_id: str) -> Optional[Share]:
        """Get share by ID"""
        ...

    async def get_session_shares(
        self, session_id: str, owner_id: str
    ) -> List[Share]:
        """Get all active shares for a session owned by a user"""
        ...

    async def delete_by_token(self, share_token: str) -> bool:
        """Delete (revoke) a share by token"""
        ...

    async def increment_access_count(self, share_id: str) -> bool:
        """Increment access count for a share"""
        ...


# ============================================================================
# Service Client Protocols
# ============================================================================


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...


@runtime_checkable
class SessionClientProtocol(Protocol):
    """Interface for Session Service Client"""

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session details"""
        ...

    async def get_session_messages(
        self, session_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get session messages"""
        ...
