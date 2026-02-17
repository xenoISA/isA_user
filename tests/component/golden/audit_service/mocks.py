"""
Mock Audit Repository for Component Testing

Implements AuditRepositoryProtocol for testing AuditService without database.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from microservices.audit_service.models import (
    AuditEvent, SecurityEvent, EventType, EventSeverity, EventStatus, AuditCategory
)
from microservices.audit_service.protocols import AuditRepositoryProtocol


class MockAuditRepository(AuditRepositoryProtocol):
    """
    Mock implementation of AuditRepositoryProtocol for testing.

    Provides in-memory storage and configurable behavior for testing
    AuditService without a real database.
    """

    def __init__(self):
        self._events: Dict[str, AuditEvent] = {}
        self._security_events: Dict[str, SecurityEvent] = {}
        self._call_history: List[Dict[str, Any]] = []
        self._should_raise: Optional[Exception] = None
        self._connection_healthy: bool = True
        self._stats: Dict[str, Any] = {
            "total_events": 0,
            "critical_events": 0,
            "error_events": 0,
            "failed_events": 0,
            "success_rate": 100.0,
            "security_alerts": 0,
        }

    def _record_call(self, method: str, **kwargs):
        """Record method call for verification"""
        self._call_history.append({
            "method": method,
            "timestamp": datetime.now(timezone.utc),
            **kwargs
        })

    def _check_error(self):
        """Check if should raise configured error"""
        if self._should_raise:
            error = self._should_raise
            self._should_raise = None
            raise error

    # Test helper methods

    def set_event(
        self,
        event_id: str,
        event_type: EventType = EventType.USER_LOGIN,
        category: AuditCategory = AuditCategory.AUTHENTICATION,
        severity: EventSeverity = EventSeverity.LOW,
        action: str = "test_action",
        user_id: Optional[str] = None,
        **kwargs
    ) -> AuditEvent:
        """Add an audit event to mock storage"""
        event = AuditEvent(
            id=event_id,
            event_type=event_type,
            category=category,
            severity=severity,
            action=action,
            user_id=user_id,
            timestamp=kwargs.get('timestamp', datetime.now(timezone.utc)),
            **{k: v for k, v in kwargs.items() if k != 'timestamp'}
        )
        self._events[event_id] = event
        self._update_stats()
        return event

    def set_security_event(
        self,
        event_id: str,
        event_type: EventType = EventType.SECURITY_ALERT,
        severity: EventSeverity = EventSeverity.HIGH,
        threat_level: str = "high",
        **kwargs
    ) -> SecurityEvent:
        """Add a security event to mock storage"""
        event = SecurityEvent(
            id=event_id,
            event_type=event_type,
            severity=severity,
            threat_level=threat_level,
            **kwargs
        )
        self._security_events[event_id] = event
        return event

    def set_stats(self, **stats):
        """Set custom stats values"""
        self._stats.update(stats)

    def set_error(self, error: Exception):
        """Configure an error to be raised on next call"""
        self._should_raise = error

    def set_connection_healthy(self, healthy: bool):
        """Configure connection health status"""
        self._connection_healthy = healthy

    def get_calls(self, method: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recorded calls, optionally filtered by method"""
        if method:
            return [c for c in self._call_history if c["method"] == method]
        return self._call_history

    def get_last_call(self, method: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the last recorded call"""
        calls = self.get_calls(method)
        return calls[-1] if calls else None

    def assert_called(self, method: str):
        """Assert that a method was called"""
        calls = self.get_calls(method)
        assert len(calls) > 0, f"Expected {method} to be called, but it wasn't"

    def assert_called_with(self, method: str, **expected_kwargs):
        """Assert that a method was called with specific arguments"""
        calls = self.get_calls(method)
        assert len(calls) > 0, f"Expected {method} to be called, but it wasn't"

        last_call = calls[-1]
        for key, value in expected_kwargs.items():
            assert key in last_call, f"Expected {key} in call args"
            assert last_call[key] == value, f"Expected {key}={value}, got {last_call[key]}"

    def clear(self):
        """Clear all stored data and call history"""
        self._events.clear()
        self._security_events.clear()
        self._call_history.clear()
        self._should_raise = None

    def _update_stats(self):
        """Update stats based on current events"""
        total = len(self._events)
        critical = sum(1 for e in self._events.values() if e.severity == EventSeverity.CRITICAL)
        errors = sum(1 for e in self._events.values() if e.severity == EventSeverity.HIGH)
        failed = sum(1 for e in self._events.values() if e.status == EventStatus.FAILURE)

        self._stats["total_events"] = total
        self._stats["critical_events"] = critical
        self._stats["error_events"] = errors
        self._stats["failed_events"] = failed

    # Protocol implementation

    async def check_connection(self) -> bool:
        """Check database connection"""
        self._record_call("check_connection")
        self._check_error()
        return self._connection_healthy

    async def create_audit_event(self, event: AuditEvent) -> Optional[AuditEvent]:
        """Create audit event"""
        self._record_call("create_audit_event", event_id=event.id, event_type=event.event_type)
        self._check_error()

        if event.id:
            self._events[event.id] = event
        self._update_stats()
        return event

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
        self._record_call(
            "get_audit_events",
            user_id=user_id,
            organization_id=organization_id,
            event_type=event_type,
            limit=limit,
            offset=offset
        )
        self._check_error()

        events = list(self._events.values())

        # Apply filters
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        if organization_id:
            events = [e for e in events if e.organization_id == organization_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]

        # Sort and paginate
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[offset:offset + limit]

    async def query_audit_events(self, query: Dict[str, Any]) -> List[AuditEvent]:
        """Query audit events"""
        self._record_call("query_audit_events", query=query)
        self._check_error()

        # Handle both dict and Pydantic model
        if hasattr(query, 'model_dump'):
            query_dict = query.model_dump()
        elif hasattr(query, 'dict'):
            query_dict = query.dict()
        elif isinstance(query, dict):
            query_dict = query
        else:
            query_dict = {}

        return await self.get_audit_events(
            user_id=query_dict.get('user_id'),
            organization_id=query_dict.get('organization_id'),
            event_type=query_dict.get('event_type'),
            start_time=query_dict.get('start_time'),
            end_time=query_dict.get('end_time'),
            limit=query_dict.get('limit', 100),
            offset=query_dict.get('offset', 0)
        )

    async def get_user_activities(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get user activities"""
        self._record_call("get_user_activities", user_id=user_id, days=days, limit=limit)
        self._check_error()

        events = [e for e in self._events.values() if e.user_id == user_id]
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return [e.model_dump() for e in events[:limit]]

    async def get_user_activity_summary(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get user activity summary"""
        self._record_call("get_user_activity_summary", user_id=user_id, days=days)
        self._check_error()

        events = [e for e in self._events.values() if e.user_id == user_id]
        success_count = sum(1 for e in events if e.success)
        failure_count = len(events) - success_count

        return {
            "total_activities": len(events),
            "success_count": success_count,
            "failure_count": failure_count,
            "last_activity": events[0].timestamp.isoformat() if events else None,
            "most_common_activities": [],
            "risk_score": 0.0
        }

    async def create_security_event(self, security_event: SecurityEvent) -> Optional[SecurityEvent]:
        """Create security event"""
        self._record_call("create_security_event", event_id=security_event.id)
        self._check_error()

        if security_event.id:
            self._security_events[security_event.id] = security_event
        return security_event

    async def get_security_events(
        self,
        days: int = 7,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get security events"""
        self._record_call("get_security_events", days=days, severity=severity)
        self._check_error()

        events = list(self._security_events.values())
        if severity:
            events = [e for e in events if e.severity.value == severity]
        return [e.model_dump() for e in events]

    async def get_event_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get event statistics"""
        self._record_call("get_event_statistics", days=days)
        self._check_error()
        return self._stats.copy()

    async def get_statistics(
        self,
        organization_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get audit statistics"""
        self._record_call(
            "get_statistics",
            organization_id=organization_id,
            start_time=start_time,
            end_time=end_time
        )
        self._check_error()
        return self._stats.copy()

    async def cleanup_old_events(self, retention_days: int = 365) -> int:
        """Cleanup old events"""
        self._record_call("cleanup_old_events", retention_days=retention_days)
        self._check_error()
        # Mock: return 0 cleaned events
        return 0
