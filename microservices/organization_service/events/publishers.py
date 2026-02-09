"""
Organization Service Event Publishers

Publish events for organization lifecycle and member management.
Following the standard event-driven architecture pattern.
"""

import logging
from typing import List, Optional

from core.nats_client import Event

from .models import (
    create_organization_created_event_data,
    create_organization_deleted_event_data,
    create_organization_member_added_event_data,
    create_organization_member_removed_event_data,
    create_organization_member_updated_event_data,
    create_organization_updated_event_data,
    create_sharing_resource_created_event_data,
    create_sharing_resource_deleted_event_data,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Organization Event Publishers
# ============================================================================


async def publish_organization_created(
    event_bus,
    organization_id: str,
    name: str,
    billing_email: str,
    plan: str,
    created_by: str,
):
    """
    Publish organization.created event

    Args:
        event_bus: NATS event bus instance
        organization_id: Organization ID
        name: Organization name
        billing_email: Billing email
        plan: Subscription plan
        created_by: Creator user ID
    """
    try:
        event_data = create_organization_created_event_data(
            organization_id=organization_id,
            name=name,
            billing_email=billing_email,
            plan=plan,
            created_by=created_by,
        )

        event = Event(
            event_type="organization.created",
            source="organization_service",
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(f"Published organization.created for organization {organization_id}")

    except Exception as e:
        logger.error(f"Failed to publish organization.created: {e}")


async def publish_organization_updated(
    event_bus,
    organization_id: str,
    name: str,
    updated_fields: List[str],
    updated_by: str,
):
    """
    Publish organization.updated event

    Args:
        event_bus: NATS event bus instance
        organization_id: Organization ID
        name: Updated organization name
        updated_fields: List of fields that were updated
        updated_by: User ID who made the update
    """
    try:
        event_data = create_organization_updated_event_data(
            organization_id=organization_id,
            name=name,
            updated_fields=updated_fields,
            updated_by=updated_by,
        )

        event = Event(
            event_type="organization.updated",
            source="organization_service",
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published organization.updated for organization {organization_id}, fields: {updated_fields}"
        )

    except Exception as e:
        logger.error(f"Failed to publish organization.updated: {e}")


async def publish_organization_deleted(
    event_bus,
    organization_id: str,
    name: str,
    deleted_by: str,
    reason: Optional[str] = None,
):
    """
    Publish organization.deleted event

    Args:
        event_bus: NATS event bus instance
        organization_id: Organization ID
        name: Organization name
        deleted_by: User ID who deleted the organization
        reason: Deletion reason
    """
    try:
        event_data = create_organization_deleted_event_data(
            organization_id=organization_id,
            name=name,
            deleted_by=deleted_by,
            reason=reason,
        )

        event = Event(
            event_type="organization.deleted",
            source="organization_service",
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(f"Published organization.deleted for organization {organization_id}")

    except Exception as e:
        logger.error(f"Failed to publish organization.deleted: {e}")


async def publish_organization_member_added(
    event_bus,
    organization_id: str,
    user_id: str,
    role: str,
    added_by: str,
):
    """
    Publish organization.member_added event

    Args:
        event_bus: NATS event bus instance
        organization_id: Organization ID
        user_id: Member user ID
        role: Member role
        added_by: User ID who added the member
    """
    try:
        event_data = create_organization_member_added_event_data(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            added_by=added_by,
        )

        event = Event(
            event_type="organization.member_added",
            source="organization_service",
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published organization.member_added for user {user_id} in organization {organization_id}"
        )

    except Exception as e:
        logger.error(f"Failed to publish organization.member_added: {e}")


async def publish_organization_member_removed(
    event_bus,
    organization_id: str,
    user_id: str,
    removed_by: str,
    reason: Optional[str] = None,
):
    """
    Publish organization.member_removed event

    Args:
        event_bus: NATS event bus instance
        organization_id: Organization ID
        user_id: Member user ID
        removed_by: User ID who removed the member
        reason: Removal reason
    """
    try:
        event_data = create_organization_member_removed_event_data(
            organization_id=organization_id,
            user_id=user_id,
            removed_by=removed_by,
            reason=reason,
        )

        event = Event(
            event_type="organization.member_removed",
            source="organization_service",
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published organization.member_removed for user {user_id} in organization {organization_id}"
        )

    except Exception as e:
        logger.error(f"Failed to publish organization.member_removed: {e}")


async def publish_organization_member_updated(
    event_bus,
    organization_id: str,
    user_id: str,
    old_role: str,
    new_role: str,
    updated_by: str,
):
    """
    Publish organization.member_updated event

    Args:
        event_bus: NATS event bus instance
        organization_id: Organization ID
        user_id: Member user ID
        old_role: Previous role
        new_role: New role
        updated_by: User ID who made the update
    """
    try:
        event_data = create_organization_member_updated_event_data(
            organization_id=organization_id,
            user_id=user_id,
            old_role=old_role,
            new_role=new_role,
            updated_by=updated_by,
        )

        event = Event(
            event_type="organization.member_updated",
            source="organization_service",
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published organization.member_updated for user {user_id}: {old_role} -> {new_role}"
        )

    except Exception as e:
        logger.error(f"Failed to publish organization.member_updated: {e}")


async def publish_sharing_resource_created(
    event_bus,
    organization_id: str,
    sharing_id: str,
    resource_type: str,
    resource_id: str,
    resource_name: str,
    created_by: str,
):
    """
    Publish organization.sharing_created event

    Args:
        event_bus: NATS event bus instance
        organization_id: Organization ID
        sharing_id: Sharing resource ID
        resource_type: Resource type (album, file, etc.)
        resource_id: Resource identifier
        resource_name: Resource name
        created_by: User ID who created the sharing
    """
    try:
        event_data = create_sharing_resource_created_event_data(
            organization_id=organization_id,
            sharing_id=sharing_id,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            created_by=created_by,
        )

        event = Event(
            event_type="organization.sharing.created",
            source="organization_service",
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published organization.sharing_created for sharing {sharing_id} in organization {organization_id}"
        )

    except Exception as e:
        logger.error(f"Failed to publish organization.sharing_created: {e}")


async def publish_sharing_resource_deleted(
    event_bus,
    organization_id: str,
    sharing_id: str,
    resource_type: str,
    resource_id: str,
    deleted_by: str,
):
    """
    Publish organization.sharing_deleted event

    Args:
        event_bus: NATS event bus instance
        organization_id: Organization ID
        sharing_id: Sharing resource ID
        resource_type: Resource type
        resource_id: Resource identifier
        deleted_by: User ID who deleted the sharing
    """
    try:
        event_data = create_sharing_resource_deleted_event_data(
            organization_id=organization_id,
            sharing_id=sharing_id,
            resource_type=resource_type,
            resource_id=resource_id,
            deleted_by=deleted_by,
        )

        event = Event(
            event_type="organization.sharing.deleted",
            source="organization_service",
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published organization.sharing_deleted for sharing {sharing_id} in organization {organization_id}"
        )

    except Exception as e:
        logger.error(f"Failed to publish organization.sharing_deleted: {e}")
