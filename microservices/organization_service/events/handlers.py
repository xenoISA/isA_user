"""
Organization Service Event Handlers

Handle events from other services that affect organization management.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


# ============================================================================
# Event Handlers
# ============================================================================


async def handle_user_deleted(event_data: Dict[str, Any]):
    """
    Handle user.deleted event from account_service

    When a user is deleted, we need to:
    1. Remove the user from all organizations they are a member of
    2. Handle ownership transfer for organizations they own
    3. Delete organizations where they are the sole owner (optional)

    Event data:
        - user_id: User ID
        - email: User email (optional)
        - reason: Deletion reason (optional)
    """
    try:
        user_id = event_data.get("user_id")

        logger.info(f"Received user.deleted for user {user_id}")

        # Note: The actual cleanup logic is handled in the OrganizationEventHandler
        # class in events.py which is instantiated in main.py with the repository
        # This handler is just a placeholder for the registry

    except Exception as e:
        logger.error(f"Error handling user.deleted event: {e}")


async def handle_album_deleted(event_data: Dict[str, Any]):
    """
    Handle album.deleted event from album_service

    When an album is deleted, remove any sharing references to it

    Event data:
        - album_id: Album ID
        - user_id: Owner user ID
    """
    try:
        album_id = event_data.get("album_id")
        resource_id = event_data.get("resource_id") or album_id

        logger.info(f"Received album.deleted for album {resource_id}")

        # TODO: Remove sharing references for this album
        # This would require accessing the FamilySharingRepository
        # For now, just log it

    except Exception as e:
        logger.error(f"Error handling album.deleted event: {e}")


async def handle_billing_subscription_changed(event_data: Dict[str, Any]):
    """
    Handle billing.subscription_changed event from billing_service

    When an organization's subscription changes, update organization plan

    Event data:
        - organization_id: Organization ID
        - old_plan: Previous plan
        - new_plan: New plan
    """
    try:
        organization_id = event_data.get("organization_id")
        new_plan = event_data.get("new_plan")

        logger.info(
            f"Received billing.subscription_changed for organization {organization_id}, new plan: {new_plan}"
        )

        # TODO: Update organization plan in database
        # This would require accessing the OrganizationRepository
        # For now, just log it

    except Exception as e:
        logger.error(f"Error handling billing.subscription_changed event: {e}")


# ============================================================================
# Event Handler Registry
# ============================================================================


def get_event_handlers() -> Dict[str, callable]:
    """
    Return a mapping of event types to handler functions

    This will be used in main.py to register event subscriptions
    """
    return {
        "user.deleted": handle_user_deleted,
        "album.deleted": handle_album_deleted,
        "billing.subscription_changed": handle_billing_subscription_changed,
    }
