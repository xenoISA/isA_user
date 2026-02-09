"""
Invitation Service Event Handlers

Handles incoming events from other services via NATS
"""

import logging
import sys
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event

logger = logging.getLogger(__name__)


class InvitationEventHandler:
    """
    Handles events subscribed by Invitation Service

    Subscribes to:
    - organization.deleted: Cancel/delete all pending invitations for deleted organization
    - user.deleted: Clean up invitations sent by deleted user
    """

    def __init__(self, invitation_repository):
        """
        Initialize event handler

        Args:
            invitation_repository: InvitationRepository instance for data access
        """
        self.invitation_repo = invitation_repository

    async def handle_organization_deleted(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle organization.deleted event

        When an organization is deleted, cancel all pending invitations

        Args:
            event_data: Event data containing organization_id

        Returns:
            bool: True if handled successfully
        """
        try:
            organization_id = event_data.get('organization_id')
            if not organization_id:
                logger.warning("organization.deleted event missing organization_id")
                return False

            logger.info(f"Handling organization.deleted event for org {organization_id}")

            # Cancel all pending invitations for this organization
            cancelled_count = await self.invitation_repo.cancel_organization_invitations(organization_id)

            logger.info(f"Cancelled {cancelled_count} pending invitations for organization {organization_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to handle organization.deleted event: {e}", exc_info=True)
            return False

    async def handle_user_deleted(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle user.deleted event

        When a user is deleted, cancel invitations they sent (optional)
        and remove them from any accepted invitations

        Args:
            event_data: Event data containing user_id

        Returns:
            bool: True if handled successfully
        """
        try:
            user_id = event_data.get('user_id')
            if not user_id:
                logger.warning("user.deleted event missing user_id")
                return False

            logger.info(f"Handling user.deleted event for user {user_id}")

            # Cancel invitations sent by this user (if they were the inviter)
            cancelled_count = await self.invitation_repo.cancel_invitations_by_inviter(user_id)

            logger.info(f"Cancelled {cancelled_count} pending invitations sent by user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to handle user.deleted event: {e}", exc_info=True)
            return False

    async def handle_event(self, event: Event) -> bool:
        """
        Route event to appropriate handler

        Args:
            event: The event to handle

        Returns:
            bool: True if handled successfully
        """
        try:
            event_type = event.type

            if event_type == "organization.deleted":
                return await self.handle_organization_deleted(event.data)
            elif event_type == "user.deleted".value:
                return await self.handle_user_deleted(event.data)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return False

        except Exception as e:
            logger.error(f"Failed to handle event: {e}", exc_info=True)
            return False

    def get_subscriptions(self) -> list:
        """
        Get list of event types this handler subscribes to

        Returns:
            list: List of event type values to subscribe to
        """
        return [
            "organization.deleted",
            "user.deleted".value,
        ]
