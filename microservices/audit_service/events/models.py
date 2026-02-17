"""
Audit Service Event Models

Event data models for audit-related events.
Note: Audit service primarily consumes events from other services.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class AuditEventType(str, Enum):
    """
    Events published by audit_service.

    Stream: audit-stream
    Subjects: audit.>
    """
    AUDIT_LOG_CREATED = "audit.log.created"
    AUDIT_QUERY_EXECUTED = "audit.query.executed"


class AuditSubscribedEventType(str, Enum):
    """Events that audit_service subscribes to from other services."""
    USER_CREATED = "user.created"
    USER_DELETED = "user.deleted"


class AuditStreamConfig:
    """Stream configuration for audit_service"""
    STREAM_NAME = "audit-stream"
    SUBJECTS = ["audit.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "audit"



class AuditEventRecordedEventData(BaseModel):
    """
    Event: audit.event_recorded
    Triggered when a critical audit event is recorded
    """

    event_id: str = Field(..., description="Audit event ID")
    event_type: str = Field(..., description="Event type")
    category: str = Field(..., description="Audit category")
    severity: str = Field(..., description="Event severity")
    user_id: Optional[str] = Field(None, description="User ID if applicable")
    action: str = Field(..., description="Action performed")
    success: bool = Field(..., description="Whether action succeeded")
    recorded_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "audit_12345",
                "event_type": "security_violation",
                "category": "security",
                "severity": "high",
                "user_id": "user_001",
                "action": "unauthorized_access",
                "success": False,
                "recorded_at": "2025-11-16T10:00:00Z",
            }
        }


def create_audit_event_recorded_event_data(
    event_id: str,
    event_type: str,
    category: str,
    severity: str,
    action: str,
    success: bool,
    user_id: Optional[str] = None,
) -> AuditEventRecordedEventData:
    """Create AuditEventRecordedEventData instance"""
    return AuditEventRecordedEventData(
        event_id=event_id,
        event_type=event_type,
        category=category,
        severity=severity,
        action=action,
        success=success,
        user_id=user_id,
    )
