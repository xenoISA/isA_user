"""
Compliance Service Event Handlers

Handles events from other services that require compliance checks
"""

import logging
from typing import Dict, Callable

from core.nats_client import Event

logger = logging.getLogger(__name__)


async def handle_content_created(event: Event, compliance_service, event_bus):
    """
    Handle content.created event from other services
    Automatically trigger compliance check for new content

    Args:
        event: The content.created event
        compliance_service: ComplianceService instance
        event_bus: NATS event bus instance
    """
    try:
        user_id = event.data.get("user_id")
        content = event.data.get("content")
        content_type = event.data.get("content_type", "text")

        if not user_id or not content:
            logger.warning(f"Missing required fields in content.created event: {event.id}")
            return

        logger.info(
            f"Triggering compliance check for content.created event "
            f"(user: {user_id}, type: {content_type})"
        )

        # Perform compliance check
        # Note: This would call the actual compliance check method
        # For now, just logging the event
        logger.debug(f"Would check content for user {user_id}: {content[:100]}...")

    except Exception as e:
        logger.error(f"Error handling content.created event: {e}", exc_info=True)


async def handle_user_content_uploaded(event: Event, compliance_service, event_bus):
    """
    Handle user content upload events
    Check uploaded content for compliance

    Args:
        event: The upload event
        compliance_service: ComplianceService instance
        event_bus: NATS event bus instance
    """
    try:
        user_id = event.data.get("user_id")
        file_path = event.data.get("file_path")
        file_type = event.data.get("file_type")

        if not user_id or not file_path:
            logger.warning(f"Missing required fields in upload event: {event.id}")
            return

        logger.info(
            f"Triggering compliance check for uploaded content "
            f"(user: {user_id}, type: {file_type})"
        )

        # Perform compliance check on uploaded file
        # Note: This would call the actual compliance check method
        logger.debug(f"Would check uploaded file for user {user_id}: {file_path}")

    except Exception as e:
        logger.error(f"Error handling user content upload event: {e}", exc_info=True)


def get_event_handlers(compliance_service, event_bus) -> Dict[str, Callable]:
    """
    Get all event handlers for compliance service

    Args:
        compliance_service: ComplianceService instance
        event_bus: NATS event bus instance

    Returns:
        Dictionary mapping event patterns to handler functions
    """
    return {
        # Handle content creation events from other services
        "content.created": lambda event: handle_content_created(
            event, compliance_service, event_bus
        ),
        # Handle file upload events
        "storage.file_uploaded": lambda event: handle_user_content_uploaded(
            event, compliance_service, event_bus
        ),
    }
