"""
Account Service Event Publishers

Publish events for account lifecycle and profile management.
Following the standard event-driven architecture pattern.
"""

import logging
from typing import List, Optional

from core.nats_client import Event, EventType, ServiceSource

from .models import (
    create_user_created_event_data,
    create_user_deleted_event_data,
    create_user_profile_updated_event_data,
    create_user_status_changed_event_data,
    create_user_subscription_changed_event_data,
)

logger = logging.getLogger(__name__)


# ============================================================================
# User Account Event Publishers
# ============================================================================


async def publish_user_created(
    event_bus, user_id: str, email: str, name: str, subscription_plan: str
):
    """
    Publish user.created event

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        email: User email
        name: User display name
        subscription_plan: Initial subscription plan
    """
    try:
        event_data = create_user_created_event_data(
            user_id=user_id, email=email, name=name, subscription_plan=subscription_plan
        )

        event = Event(
            event_type=EventType.USER_CREATED,
            source=ServiceSource.ACCOUNT_SERVICE,
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(f"Published user.created for user {user_id}")

    except Exception as e:
        logger.error(f"Failed to publish user.created: {e}")
        # Don't raise - event publishing failures shouldn't break the main flow
        # But log for monitoring


async def publish_user_profile_updated(
    event_bus, user_id: str, email: str, name: str, updated_fields: List[str]
):
    """
    Publish user.profile_updated event

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        email: Updated email
        name: Updated name
        updated_fields: List of fields that were updated
    """
    try:
        event_data = create_user_profile_updated_event_data(
            user_id=user_id, email=email, name=name, updated_fields=updated_fields
        )

        event = Event(
            event_type=EventType.USER_PROFILE_UPDATED,
            source=ServiceSource.ACCOUNT_SERVICE,
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published user.profile_updated for user {user_id}, fields: {updated_fields}"
        )

    except Exception as e:
        logger.error(f"Failed to publish user.profile_updated: {e}")


async def publish_user_deleted(
    event_bus, user_id: str, email: Optional[str] = None, reason: Optional[str] = None
):
    """
    Publish user.deleted event

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        email: User email (if available)
        reason: Deletion reason
    """
    try:
        event_data = create_user_deleted_event_data(
            user_id=user_id, email=email, reason=reason
        )

        event = Event(
            event_type=EventType.USER_DELETED,
            source=ServiceSource.ACCOUNT_SERVICE,
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(f"Published user.deleted for user {user_id}")

    except Exception as e:
        logger.error(f"Failed to publish user.deleted: {e}")


async def publish_user_subscription_changed(
    event_bus,
    user_id: str,
    email: str,
    old_plan: str,
    new_plan: str,
    changed_by: Optional[str] = None,
):
    """
    Publish user.subscription_changed event

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        email: User email
        old_plan: Previous subscription plan
        new_plan: New subscription plan
        changed_by: Who changed the subscription
    """
    try:
        event_data = create_user_subscription_changed_event_data(
            user_id=user_id,
            email=email,
            old_plan=old_plan,
            new_plan=new_plan,
            changed_by=changed_by,
        )

        event = Event(
            event_type=EventType.SUBSCRIPTION_UPDATED,
            source=ServiceSource.ACCOUNT_SERVICE,
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published user.subscription_changed for user {user_id}: {old_plan} -> {new_plan}"
        )

    except Exception as e:
        logger.error(f"Failed to publish user.subscription_changed: {e}")


async def publish_user_status_changed(
    event_bus,
    user_id: str,
    is_active: bool,
    email: Optional[str] = None,
    reason: Optional[str] = None,
    changed_by: Optional[str] = None,
):
    """
    Publish user.status_changed event

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        is_active: New active status
        email: User email
        reason: Reason for status change
        changed_by: Who changed the status
    """
    try:
        event_data = create_user_status_changed_event_data(
            user_id=user_id,
            is_active=is_active,
            email=email,
            reason=reason,
            changed_by=changed_by,
        )

        event = Event(
            event_type=EventType.USER_UPDATED,
            source=ServiceSource.ACCOUNT_SERVICE,
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        status_text = "activated" if is_active else "deactivated"
        logger.info(f"Published user.status_changed for user {user_id}: {status_text}")

    except Exception as e:
        logger.error(f"Failed to publish user.status_changed: {e}")
