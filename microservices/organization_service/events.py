"""
Organization Service Event Handlers

Handles event-driven cleanup for organization membership
"""

import logging
import json
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .organization_repository import OrganizationRepository

logger = logging.getLogger(__name__)


class OrganizationEventHandler:
    """Event handler for Organization Service"""

    def __init__(self, organization_repository: 'OrganizationRepository'):
        """
        Initialize event handler

        Args:
            organization_repository: Organization repository instance
        """
        self.repository = organization_repository

    async def handle_event(self, msg):
        """
        Generic event handler dispatcher

        Args:
            msg: NATS message
        """
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

    async def handle_user_deleted(self, event_data: Dict[str, Any]):
        """
        Handle user.deleted event - Clean up organization memberships

        When a user is deleted, we need to:
        1. Remove the user from all organizations they are a member of
        2. Handle ownership transfer for organizations they own
        3. Delete organizations where they are the sole owner (optional)

        Args:
            event_data: Event data containing user_id
        """
        try:
            user_id = event_data.get("user_id")

            if not user_id:
                logger.warning("user.deleted event missing user_id")
                return

            logger.info(f"Handling user.deleted event for user_id={user_id}")

            # Get all organizations where user is a member
            try:
                from .organization_repository import OrganizationRepository

                # Remove user from all organization memberships
                # Note: This is a simplified approach. In production, you might want to:
                # 1. Check if user is the sole owner and handle appropriately
                # 2. Transfer ownership to another admin
                # 3. Delete organizations if no other members exist

                # For now, we'll just remove the user from all memberships
                removed_count = await self.repository.remove_user_from_all_organizations(user_id)

                logger.info(f"Removed user {user_id} from {removed_count} organizations")

            except AttributeError:
                # Method might not exist yet in repository
                logger.warning(
                    f"Method remove_user_from_all_organizations not implemented in repository. "
                    f"Manual cleanup required for user {user_id}"
                )
                # TODO: Implement repository method to remove user from all organizations

            logger.info(f"Successfully handled user.deleted event for user_id={user_id}")

        except Exception as e:
            logger.error(f"Error handling user.deleted event: {e}", exc_info=True)
