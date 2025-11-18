"""
Audit Service Event Publishers

Publish events for critical audit actions.
Note: Audit service primarily consumes events from other services.
"""

import logging

from core.nats_client import Event, EventType, ServiceSource

from .models import create_audit_event_recorded_event_data

logger = logging.getLogger(__name__)


async def publish_audit_event_recorded(
    event_bus,
    event_id: str,
    event_type: str,
    category: str,
    severity: str,
    action: str,
    success: bool,
    user_id: str = None,
):
    """
    Publish audit.event_recorded event
    
    Args:
        event_bus: NATS event bus instance
        event_id: Audit event ID
        event_type: Event type
        category: Audit category
        severity: Event severity
        action: Action performed
        success: Whether action succeeded
        user_id: User ID if applicable
    """
    try:
        event_data = create_audit_event_recorded_event_data(
            event_id=event_id,
            event_type=event_type,
            category=category,
            severity=severity,
            action=action,
            success=success,
            user_id=user_id,
        )

        event = Event(
            event_type=EventType.AUDIT_EVENT_RECORDED,
            source=ServiceSource.AUDIT_SERVICE,
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(f"Published audit.event_recorded for event {event_id}")

    except Exception as e:
        logger.error(f"Failed to publish audit.event_recorded: {e}")
