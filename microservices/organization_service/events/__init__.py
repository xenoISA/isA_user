"""
Organization Service Events Module

Event-driven architecture for organization lifecycle and member management.
Follows the standard event-driven architecture pattern.
"""

from .handlers import get_event_handlers
from .models import (
    OrganizationCreatedEventData,
    OrganizationDeletedEventData,
    OrganizationMemberAddedEventData,
    OrganizationMemberRemovedEventData,
    OrganizationMemberUpdatedEventData,
    OrganizationUpdatedEventData,
    SharingResourceCreatedEventData,
    SharingResourceDeletedEventData,
    create_organization_created_event_data,
    create_organization_deleted_event_data,
    create_organization_member_added_event_data,
    create_organization_member_removed_event_data,
    create_organization_member_updated_event_data,
    create_organization_updated_event_data,
    create_sharing_resource_created_event_data,
    create_sharing_resource_deleted_event_data,
)
from .publishers import (
    publish_organization_created,
    publish_organization_deleted,
    publish_organization_member_added,
    publish_organization_member_removed,
    publish_organization_member_updated,
    publish_organization_updated,
    publish_sharing_resource_created,
    publish_sharing_resource_deleted,
)

# Import the event handler class from the root events.py
# This is for backward compatibility with main.py
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from events import OrganizationEventHandler
except ImportError:
    # If the old events.py doesn't exist, create a placeholder
    class OrganizationEventHandler:
        """Placeholder for backward compatibility"""
        def __init__(self, repository):
            self.repository = repository

        async def handle_event(self, msg):
            """Handle incoming events"""
            import json
            import logging
            logger = logging.getLogger(__name__)

            try:
                data = json.loads(msg.data.decode())
                event_type = data.get("event_type") or data.get("type")

                logger.info(f"Received event: {event_type}")

                if event_type == "user.deleted" or event_type == "USER_DELETED":
                    await self.handle_user_deleted(data)
                else:
                    logger.warning(f"Unknown event type: {event_type}")

            except Exception as e:
                logger.error(f"Error handling event: {e}", exc_info=True)

        async def handle_user_deleted(self, event_data):
            """Handle user.deleted event"""
            import logging
            logger = logging.getLogger(__name__)

            try:
                user_id = event_data.get("user_id")
                if not user_id:
                    logger.warning("user.deleted event missing user_id")
                    return

                logger.info(f"Handling user.deleted event for user_id={user_id}")

                try:
                    removed_count = await self.repository.remove_user_from_all_organizations(user_id)
                    logger.info(f"Removed user {user_id} from {removed_count} organizations")
                except AttributeError:
                    logger.warning(
                        f"Method remove_user_from_all_organizations not implemented. "
                        f"Manual cleanup required for user {user_id}"
                    )

            except Exception as e:
                logger.error(f"Error handling user.deleted event: {e}", exc_info=True)

__all__ = [
    # Handlers
    "get_event_handlers",
    "OrganizationEventHandler",
    # Models
    "OrganizationCreatedEventData",
    "OrganizationUpdatedEventData",
    "OrganizationDeletedEventData",
    "OrganizationMemberAddedEventData",
    "OrganizationMemberRemovedEventData",
    "OrganizationMemberUpdatedEventData",
    "SharingResourceCreatedEventData",
    "SharingResourceDeletedEventData",
    "create_organization_created_event_data",
    "create_organization_updated_event_data",
    "create_organization_deleted_event_data",
    "create_organization_member_added_event_data",
    "create_organization_member_removed_event_data",
    "create_organization_member_updated_event_data",
    "create_sharing_resource_created_event_data",
    "create_sharing_resource_deleted_event_data",
    # Publishers
    "publish_organization_created",
    "publish_organization_updated",
    "publish_organization_deleted",
    "publish_organization_member_added",
    "publish_organization_member_removed",
    "publish_organization_member_updated",
    "publish_sharing_resource_created",
    "publish_sharing_resource_deleted",
]
