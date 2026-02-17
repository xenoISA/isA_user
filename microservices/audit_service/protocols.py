"""
Audit Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime

# Import only models (no I/O dependencies)
from .models import (
    AuditEvent, SecurityEvent, EventType, EventSeverity
)


# Custom exceptions - defined here to avoid importing repository
class AuditNotFoundError(Exception):
    """Audit event not found error"""
    pass


class AuditValidationError(Exception):
    """Audit validation error"""
    pass


class AuditServiceError(Exception):
    """Base exception for audit service errors"""
    pass


@runtime_checkable
class AuditRepositoryProtocol(Protocol):
    """
    Interface for Audit Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    async def check_connection(self) -> bool:
        """Check database connection"""
        ...

    async def create_audit_event(self, event: AuditEvent) -> Optional[AuditEvent]:
        """Create audit event"""
        ...

    async def get_audit_events(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditEvent]:
        """Get audit events list"""
        ...

    async def query_audit_events(self, query: Dict[str, Any]) -> List[AuditEvent]:
        """Query audit events"""
        ...

    async def get_user_activities(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get user activities"""
        ...

    async def get_user_activity_summary(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get user activity summary"""
        ...

    async def create_security_event(self, security_event: SecurityEvent) -> Optional[SecurityEvent]:
        """Create security event"""
        ...

    async def get_security_events(
        self,
        days: int = 7,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get security events"""
        ...

    async def get_event_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get event statistics"""
        ...

    async def get_statistics(
        self,
        organization_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get audit statistics"""
        ...

    async def cleanup_old_events(self, retention_days: int = 365) -> int:
        """Cleanup old events"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...
