"""
Authorization Service Event Publishers

Publish events for authorization and permission management.
Following the standard event-driven architecture pattern.
"""

import logging
from typing import List, Optional

from core.nats_client import Event, EventType, ServiceSource

from .models import (
    create_bulk_permissions_granted_event_data,
    create_bulk_permissions_revoked_event_data,
    create_permission_granted_event_data,
    create_permission_revoked_event_data,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Permission Event Publishers
# ============================================================================


async def publish_permission_granted(
    event_bus,
    user_id: str,
    resource_type: str,
    resource_name: str,
    access_level: str,
    permission_source: str,
    granted_by_user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
):
    """
    Publish permission.granted event

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        resource_type: Resource type
        resource_name: Resource name
        access_level: Access level granted
        permission_source: Permission source
        granted_by_user_id: ID of user who granted the permission
        organization_id: Organization ID if applicable
    """
    try:
        event_data = create_permission_granted_event_data(
            user_id=user_id,
            resource_type=resource_type,
            resource_name=resource_name,
            access_level=access_level,
            permission_source=permission_source,
            granted_by_user_id=granted_by_user_id,
            organization_id=organization_id,
        )

        event = Event(
            event_type=EventType.PERMISSION_GRANTED,
            source=ServiceSource.AUTHORIZATION_SERVICE,
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published permission.granted for user {user_id}, resource {resource_type}:{resource_name}"
        )

    except Exception as e:
        logger.error(f"Failed to publish permission.granted: {e}")
        # Don't raise - event publishing failures shouldn't break the main flow


async def publish_permission_revoked(
    event_bus,
    user_id: str,
    resource_type: str,
    resource_name: str,
    revoked_by_user_id: Optional[str] = None,
    reason: Optional[str] = None,
):
    """
    Publish permission.revoked event

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        resource_type: Resource type
        resource_name: Resource name
        revoked_by_user_id: ID of user who revoked the permission
        reason: Reason for revocation
    """
    try:
        event_data = create_permission_revoked_event_data(
            user_id=user_id,
            resource_type=resource_type,
            resource_name=resource_name,
            revoked_by_user_id=revoked_by_user_id,
            reason=reason,
        )

        event = Event(
            event_type=EventType.PERMISSION_REVOKED,
            source=ServiceSource.AUTHORIZATION_SERVICE,
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published permission.revoked for user {user_id}, resource {resource_type}:{resource_name}"
        )

    except Exception as e:
        logger.error(f"Failed to publish permission.revoked: {e}")


async def publish_bulk_permissions_granted(
    event_bus,
    user_ids: List[str],
    permission_count: int,
    granted_by_user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
):
    """
    Publish permissions.bulk_granted event

    Args:
        event_bus: NATS event bus instance
        user_ids: List of user IDs
        permission_count: Number of permissions granted
        granted_by_user_id: ID of user who granted permissions
        organization_id: Organization ID if applicable
    """
    try:
        event_data = create_bulk_permissions_granted_event_data(
            user_ids=user_ids,
            permission_count=permission_count,
            granted_by_user_id=granted_by_user_id,
            organization_id=organization_id,
        )

        event = Event(
            event_type=EventType.BULK_PERMISSIONS_GRANTED,
            source=ServiceSource.AUTHORIZATION_SERVICE,
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published permissions.bulk_granted for {len(user_ids)} users, {permission_count} permissions"
        )

    except Exception as e:
        logger.error(f"Failed to publish permissions.bulk_granted: {e}")


async def publish_bulk_permissions_revoked(
    event_bus,
    user_ids: List[str],
    permission_count: int,
    revoked_by_user_id: Optional[str] = None,
    reason: Optional[str] = None,
):
    """
    Publish permissions.bulk_revoked event

    Args:
        event_bus: NATS event bus instance
        user_ids: List of user IDs
        permission_count: Number of permissions revoked
        revoked_by_user_id: ID of user who revoked permissions
        reason: Reason for bulk revocation
    """
    try:
        event_data = create_bulk_permissions_revoked_event_data(
            user_ids=user_ids,
            permission_count=permission_count,
            revoked_by_user_id=revoked_by_user_id,
            reason=reason,
        )

        event = Event(
            event_type=EventType.BULK_PERMISSIONS_REVOKED,
            source=ServiceSource.AUTHORIZATION_SERVICE,
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published permissions.bulk_revoked for {len(user_ids)} users, {permission_count} permissions"
        )

    except Exception as e:
        logger.error(f"Failed to publish permissions.bulk_revoked: {e}")
