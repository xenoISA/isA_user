"""
Admin Audit Event Publisher

Reusable function for publishing admin action events to NATS.
Import this from any service that needs to log admin operations.

Usage:
    from core.admin_audit import publish_admin_action

    await publish_admin_action(
        event_bus=event_bus,
        admin_user_id="admin_123",
        action="create_product",
        resource_type="product",
        resource_id="prod_abc",
        changes={"after": {"name": "New Product", "price": 9.99}},
    )

The function publishes to NATS subject: admin.action.{resource_type}.{action}
The audit_service subscribes to admin.action.* and persists entries.

IMPORTANT: This function is fail-open. Failures to publish do NOT raise
exceptions and do NOT block the calling admin operation.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from core.nats_client import Event

logger = logging.getLogger(__name__)


async def publish_admin_action(
    event_bus,
    admin_user_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None,
    admin_email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Publish an admin action event to NATS for audit logging.

    This is a fire-and-forget operation. Failures are logged but never
    propagated to the caller — admin operations must not be blocked by
    audit logging failures.

    Args:
        event_bus: NATS event bus instance (may be None)
        admin_user_id: ID of the admin performing the action
        action: Action name (e.g. create_product, update_pricing, rotate_costs)
        resource_type: Resource type (e.g. product, pricing, cost_definition)
        resource_id: ID of the affected resource (optional)
        changes: Before/after diff dict (optional)
        admin_email: Admin email if available (optional)
        ip_address: Client IP (optional)
        user_agent: Client user-agent (optional)
        metadata: Extra context (optional)

    Returns:
        True if published successfully, False otherwise (never raises)
    """
    if not event_bus:
        logger.warning("Event bus not available, skipping admin audit event")
        return False

    try:
        event_data = {
            "admin_user_id": admin_user_id,
            "admin_email": admin_email,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "changes": changes or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        subject = f"admin.action.{resource_type}.{action}"

        event = Event(
            event_type=f"admin.action.{resource_type}.{action}",
            source="admin_audit",
            data=event_data,
        )

        await event_bus.publish_event(event, subject=subject)
        logger.info(
            f"Published admin audit event: {action} on {resource_type}"
            f" (resource_id={resource_id}, admin={admin_user_id})"
        )
        return True

    except Exception as e:
        # Fail-open: log the error but never raise
        logger.error(f"Failed to publish admin audit event: {e}")
        return False
