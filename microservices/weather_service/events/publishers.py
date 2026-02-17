"""
Weather Service Event Publishers

Publish events for weather-related activities.
Following the standard event-driven architecture pattern.
"""

import logging
from datetime import datetime
from typing import Optional

from core.nats_client import Event

from .models import (
    create_weather_alert_event_data,
    create_weather_location_saved_event_data,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Weather Event Publishers
# ============================================================================


async def publish_weather_location_saved(
    event_bus,
    user_id: str,
    location_id: int,
    location: str,
    latitude: float,
    longitude: float,
    is_default: bool = False,
    nickname: Optional[str] = None,
):
    """
    Publish weather.location_saved event

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        location_id: Location ID
        location: Location name
        latitude: Latitude
        longitude: Longitude
        is_default: Is default location
        nickname: Location nickname
    """
    try:
        event_data = create_weather_location_saved_event_data(
            user_id=user_id,
            location_id=location_id,
            location=location,
            latitude=latitude,
            longitude=longitude,
            is_default=is_default,
            nickname=nickname,
        )

        event = Event(
            event_type="weather.location.saved",
            source="weather_service",
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(f"Published weather.location_saved for user {user_id}, location {location}")

    except Exception as e:
        logger.error(f"Failed to publish weather.location_saved: {e}")
        # Don't raise - event publishing failures shouldn't break the main flow


async def publish_weather_alert(
    event_bus,
    user_id: str,
    location: str,
    alert_type: str,
    severity: str,
    description: str,
    start_time: datetime,
    end_time: Optional[datetime] = None,
):
    """
    Publish weather.alert_issued event

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        location: Location name
        alert_type: Alert type
        severity: Severity level
        description: Alert description
        start_time: Alert start time
        end_time: Alert end time
    """
    try:
        event_data = create_weather_alert_event_data(
            user_id=user_id,
            location=location,
            alert_type=alert_type,
            severity=severity,
            description=description,
            start_time=start_time,
            end_time=end_time,
        )

        event = Event(
            event_type="weather.alert.issued",
            source="weather_service",
            data=event_data.model_dump(),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published weather.alert_issued for user {user_id}, location {location}, type {alert_type}"
        )

    except Exception as e:
        logger.error(f"Failed to publish weather.alert_issued: {e}")
