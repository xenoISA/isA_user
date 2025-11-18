"""
Location Service Event Handlers

Handles incoming events from other services via NATS
"""

import logging
from typing import Callable, Dict

from core.nats_client import Event

from .models import parse_device_deleted_event, parse_user_deleted_event

logger = logging.getLogger(__name__)


# =============================================================================
# Event Handlers (Async Functions)
# =============================================================================


async def handle_device_deleted(event: Event, location_repository):
    """
    Handle device.deleted event

    When a device is deleted, clean up all location data for that device

    Args:
        event: NATS event object
        location_repository: LocationRepository instance

    Event Data:
        - device_id: str
        - user_id: str (optional)
        - timestamp: str (optional)
        - reason: str (optional)

    Workflow:
        1. Parse event data
        2. Delete all location history for the device
        3. Remove device from geofences
        4. Log completion
    """
    try:
        # Parse event data
        event_data = parse_device_deleted_event(event.data)
        device_id = event_data.device_id

        if not device_id:
            logger.warning("device.deleted event missing device_id")
            return

        logger.info(f"Handling device.deleted event for device {device_id}")

        # Delete location history for this device
        deleted_count = await location_repository.delete_device_locations(device_id)

        logger.info(
            f"Deleted {deleted_count} location records for device {device_id}"
        )

    except Exception as e:
        logger.error(
            f"Failed to handle device.deleted event: {e}", exc_info=True
        )
        # Don't raise - we don't want to break the event processing chain


async def handle_user_deleted(event: Event, location_repository):
    """
    Handle user.deleted event

    When a user is deleted, clean up all location data for all their devices

    Args:
        event: NATS event object
        location_repository: LocationRepository instance

    Event Data:
        - user_id: str
        - timestamp: str (optional)
        - reason: str (optional)

    Workflow:
        1. Parse event data
        2. Delete all location history for user's devices
        3. Delete all places for the user
        4. Delete all geofences for the user
        5. Log completion
    """
    try:
        # Parse event data
        event_data = parse_user_deleted_event(event.data)
        user_id = event_data.user_id

        if not user_id:
            logger.warning("user.deleted event missing user_id")
            return

        logger.info(f"Handling user.deleted event for user {user_id}")

        # Delete location data for all user's devices
        locations_deleted = await location_repository.delete_user_locations(user_id)

        # Delete user's places
        places_deleted = await location_repository.delete_user_places(user_id)

        # Delete user's geofences
        geofences_deleted = await location_repository.delete_user_geofences(user_id)

        logger.info(
            f"Cleaned up data for deleted user {user_id}: "
            f"{locations_deleted} locations, {places_deleted} places, "
            f"{geofences_deleted} geofences"
        )

    except Exception as e:
        logger.error(
            f"Failed to handle user.deleted event: {e}", exc_info=True
        )
        # Don't raise - we don't want to break the event processing chain


# =============================================================================
# Event Handler Registry
# =============================================================================


def get_event_handlers(location_repository) -> Dict[str, Callable]:
    """
    Get all event handlers for location service.

    Returns a dict mapping event patterns to handler functions.
    This is used by main.py to register all event subscriptions.

    Args:
        location_repository: LocationRepository instance

    Returns:
        Dict[str, callable]: Event pattern -> handler function mapping
    """
    return {
        "device_service.device.deleted": lambda event: handle_device_deleted(
            event, location_repository
        ),
        "*.device.deleted": lambda event: handle_device_deleted(
            event, location_repository
        ),
        "account_service.user.deleted": lambda event: handle_user_deleted(
            event, location_repository
        ),
        "*.user.deleted": lambda event: handle_user_deleted(
            event, location_repository
        ),
    }


__all__ = [
    "handle_device_deleted",
    "handle_user_deleted",
    "get_event_handlers",
]
