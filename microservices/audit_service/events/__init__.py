"""
Audit Service Events Module

Event-driven architecture for audit service.
Follows the standard event-driven architecture pattern.
"""

from .handlers import AuditEventHandlers
from .models import (
    AuditEventRecordedEventData,
    create_audit_event_recorded_event_data,
)
from .publishers import publish_audit_event_recorded

__all__ = [
    # Handlers
    "AuditEventHandlers",
    # Models
    "AuditEventRecordedEventData",
    "create_audit_event_recorded_event_data",
    # Publishers
    "publish_audit_event_recorded",
]
