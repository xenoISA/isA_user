"""
Location Service Event Publishers

Centralized event publishing functions for location service.
All events published by location service should be defined here.
"""

import logging
from typing import Optional

from core.nats_client import Event, EventType, ServiceSource

from .models import (
    create_geofence_created_event_data,
    create_geofence_entered_event_data,
    create_geofence_exited_event_data,
    create_location_updated_event_data,
    create_place_created_event_data,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Event Publishers
# =============================================================================


async def publish_location_updated(
    event_bus,
    device_id: str,
    user_id: str,
    location_id: str,
    latitude: float,
    longitude: float,
    accuracy: Optional[float] = None,
    altitude: Optional[float] = None,
    speed: Optional[float] = None,
    heading: Optional[float] = None,
    location_method: str = "gps",
) -> bool:
    """
    Publish location.updated event

    Notifies other services that a device location has been updated.

    Args:
        event_bus: NATS event bus instance
        device_id: Device ID
        user_id: User ID
        location_id: Location record ID
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        accuracy: Location accuracy in meters
        altitude: Altitude in meters
        speed: Speed in m/s
        heading: Heading in degrees
        location_method: Location method (gps, network, etc.)

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - notification_service: Send location alerts
        - analytics_service: Track location patterns
    """
    try:
        event_data = create_location_updated_event_data(
            device_id=device_id,
            user_id=user_id,
            location_id=location_id,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            altitude=altitude,
            speed=speed,
            heading=heading,
            location_method=location_method,
        )

        event = Event(
            event_type=EventType.LOCATION_UPDATED,
            source=ServiceSource.LOCATION_SERVICE,
            data=event_data.model_dump(),
        )

        # Override with specific event type
        event.type = "location.updated"

        result = await event_bus.publish_event(event)

        if result:
            logger.info(f"Published location.updated event for device {device_id}")
        else:
            logger.error(
                f"Failed to publish location.updated event for device {device_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error publishing location.updated event: {e}", exc_info=True)
        return False


async def publish_geofence_entered(
    event_bus,
    device_id: str,
    user_id: str,
    geofence_id: str,
    geofence_name: str,
    latitude: float,
    longitude: float,
) -> bool:
    """
    Publish location.geofence.entered event

    Notifies when a device enters a geofence.

    Args:
        event_bus: NATS event bus instance
        device_id: Device ID
        user_id: User ID
        geofence_id: Geofence ID
        geofence_name: Geofence name
        latitude: Entry latitude
        longitude: Entry longitude

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - notification_service: Send geofence entry alerts
        - automation_service: Trigger automation rules
    """
    try:
        event_data = create_geofence_entered_event_data(
            device_id=device_id,
            user_id=user_id,
            geofence_id=geofence_id,
            geofence_name=geofence_name,
            latitude=latitude,
            longitude=longitude,
        )

        event = Event(
            event_type=EventType.GEOFENCE_ENTERED,
            source=ServiceSource.LOCATION_SERVICE,
            data=event_data.model_dump(),
        )

        # Override with specific event type
        event.type = "location.geofence.entered"

        result = await event_bus.publish_event(event)

        if result:
            logger.info(
                f"Published geofence.entered event for device {device_id}, geofence {geofence_name}"
            )
        else:
            logger.error(
                f"Failed to publish geofence.entered event for device {device_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error publishing geofence.entered event: {e}", exc_info=True)
        return False


async def publish_geofence_exited(
    event_bus,
    device_id: str,
    user_id: str,
    geofence_id: str,
    geofence_name: str,
    latitude: float,
    longitude: float,
) -> bool:
    """
    Publish location.geofence.exited event

    Notifies when a device exits a geofence.

    Args:
        event_bus: NATS event bus instance
        device_id: Device ID
        user_id: User ID
        geofence_id: Geofence ID
        geofence_name: Geofence name
        latitude: Exit latitude
        longitude: Exit longitude

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - notification_service: Send geofence exit alerts
        - automation_service: Trigger automation rules
    """
    try:
        event_data = create_geofence_exited_event_data(
            device_id=device_id,
            user_id=user_id,
            geofence_id=geofence_id,
            geofence_name=geofence_name,
            latitude=latitude,
            longitude=longitude,
        )

        event = Event(
            event_type=EventType.GEOFENCE_EXITED,
            source=ServiceSource.LOCATION_SERVICE,
            data=event_data.model_dump(),
        )

        # Override with specific event type
        event.type = "location.geofence.exited"

        result = await event_bus.publish_event(event)

        if result:
            logger.info(
                f"Published geofence.exited event for device {device_id}, geofence {geofence_name}"
            )
        else:
            logger.error(
                f"Failed to publish geofence.exited event for device {device_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error publishing geofence.exited event: {e}", exc_info=True)
        return False


async def publish_geofence_created(
    event_bus,
    geofence_id: str,
    name: str,
    shape_type: str,
    center_lat: float,
    center_lon: float,
    user_id: Optional[str] = None,
) -> bool:
    """
    Publish location.geofence.created event

    Notifies when a new geofence is created.

    Args:
        event_bus: NATS event bus instance
        geofence_id: Geofence ID
        name: Geofence name
        shape_type: Shape type (circle, polygon)
        center_lat: Center latitude
        center_lon: Center longitude
        user_id: Optional user ID

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - notification_service: Notify about new geofence
    """
    try:
        event_data = create_geofence_created_event_data(
            geofence_id=geofence_id,
            name=name,
            shape_type=shape_type,
            center_lat=center_lat,
            center_lon=center_lon,
            user_id=user_id,
        )

        event = Event(
            event_type=EventType.GEOFENCE_CREATED,
            source=ServiceSource.LOCATION_SERVICE,
            data=event_data.model_dump(),
        )

        # Override with specific event type
        event.type = "location.geofence.created"

        result = await event_bus.publish_event(event)

        if result:
            logger.info(f"Published geofence.created event for geofence {name}")
        else:
            logger.error(f"Failed to publish geofence.created event for {name}")

        return result

    except Exception as e:
        logger.error(f"Error publishing geofence.created event: {e}", exc_info=True)
        return False


async def publish_place_created(
    event_bus,
    place_id: str,
    user_id: str,
    name: str,
    category: str,
    latitude: float,
    longitude: float,
) -> bool:
    """
    Publish location.place.created event

    Notifies when a user creates a new place.

    Args:
        event_bus: NATS event bus instance
        place_id: Place ID
        user_id: User ID
        name: Place name
        category: Place category
        latitude: Latitude
        longitude: Longitude

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - calendar_service: Create calendar entries for place visits
        - notification_service: Notify about new place
    """
    try:
        event_data = create_place_created_event_data(
            place_id=place_id,
            user_id=user_id,
            name=name,
            category=category,
            latitude=latitude,
            longitude=longitude,
        )

        event = Event(
            event_type=EventType.PLACE_CREATED,
            source=ServiceSource.LOCATION_SERVICE,
            data=event_data.model_dump(),
        )

        # Override with specific event type
        event.type = "location.place.created"

        result = await event_bus.publish_event(event)

        if result:
            logger.info(f"Published place.created event for place {name}")
        else:
            logger.error(f"Failed to publish place.created event for {name}")

        return result

    except Exception as e:
        logger.error(f"Error publishing place.created event: {e}", exc_info=True)
        return False


__all__ = [
    "publish_location_updated",
    "publish_geofence_entered",
    "publish_geofence_exited",
    "publish_geofence_created",
    "publish_place_created",
]
