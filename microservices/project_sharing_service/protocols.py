"""
Project Sharing Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from .models import ProjectShare


# ============================================================================
# Custom Exceptions
# ============================================================================


class ProjectShareServiceError(Exception):
    """Base exception for project sharing service errors."""

    pass


class ProjectShareValidationError(ProjectShareServiceError):
    """Validation error (bad input)."""

    pass


class ProjectShareNotFoundError(ProjectShareServiceError):
    """Share not found by id or token."""

    pass


class ProjectSharePermissionError(ProjectShareServiceError):
    """Permission denied (e.g., revoked token)."""

    pass


class ProjectShareConflictError(ProjectShareServiceError):
    """Conflict (e.g., cannot accept a revoked invite)."""

    pass


# ============================================================================
# Repository Protocol
# ============================================================================


@runtime_checkable
class ProjectShareRepositoryProtocol(Protocol):
    """Interface for ProjectShare Repository."""

    async def find_pending_by_email(self, project_id: str, invitee_email: str) -> Optional[ProjectShare]:
        """Find a pending share for (project_id, lower(email))."""
        ...

    async def create_share(self, share_data: Dict[str, Any]) -> Optional[ProjectShare]:
        """Insert a new pending share row."""
        ...

    async def get_by_id(self, share_id: str) -> Optional[ProjectShare]:
        """Get a share by its UUID id."""
        ...

    async def get_by_token(self, invite_token: str) -> Optional[ProjectShare]:
        """Get a share by its invite_token (returns None if revoked/null)."""
        ...

    async def list_for_project(self, project_id: str, status: Optional[str] = None) -> List[ProjectShare]:
        """List shares for a project, optionally filtered by status."""
        ...

    async def update_role(self, share_id: str, role: str) -> Optional[ProjectShare]:
        """Update the role on a share row."""
        ...

    async def revoke(self, share_id: str) -> Optional[ProjectShare]:
        """Mark a share as revoked: status='revoked', revoked_at=now, invite_token=NULL."""
        ...

    async def mark_accepted(self, share_id: str, invitee_user_id: str) -> Optional[ProjectShare]:
        """Mark a share as accepted: status='accepted', invitee_user_id, accepted_at=now."""
        ...


# ============================================================================
# Event Bus Protocol
# ============================================================================


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for the event bus (NATS)."""

    async def publish_event(self, event: Any) -> None: ...
