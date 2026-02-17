"""
Weather Service Event Models

Event data models for weather-related events.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class WeatherEventType(str, Enum):
    """
    Events published by weather_service.

    Stream: weather-stream
    Subjects: weather.>
    """
    WEATHER_DATA_FETCHED = "weather.data.fetched"
    WEATHER_ALERT_CREATED = "weather.alert.created"


class WeatherSubscribedEventType(str, Enum):
    """Events that weather_service subscribes to from other services."""
    DEVICE_REGISTERED = "device.registered"
    LOCATION_UPDATED = "location.updated"


class WeatherStreamConfig:
    """Stream configuration for weather_service"""
    STREAM_NAME = "weather-stream"
    SUBJECTS = ["weather.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "weather"


# ============================================================================
# Weather Event Models
# ============================================================================


class WeatherLocationSavedEventData(BaseModel):
    """
    Event: weather.location_saved
    Triggered when a user saves a favorite weather location
    """

    user_id: str = Field(..., description="User ID")
    location_id: int = Field(..., description="Location ID")
    location: str = Field(..., description="Location name")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")
    is_default: bool = Field(False, description="Is default location")
    nickname: Optional[str] = Field(None, description="Location nickname")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "location_id": 1,
                "location": "New York",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "is_default": True,
                "nickname": "Home",
                "created_at": "2025-11-16T10:00:00Z",
            }
        }


class WeatherAlertEventData(BaseModel):
    """
    Event: weather.alert_issued
    Triggered when a weather alert is detected for a user's location
    """

    user_id: str = Field(..., description="User ID")
    location: str = Field(..., description="Location name")
    alert_type: str = Field(..., description="Alert type (e.g., storm, heat, cold)")
    severity: str = Field(..., description="Severity level")
    description: str = Field(..., description="Alert description")
    start_time: datetime = Field(..., description="Alert start time")
    end_time: Optional[datetime] = Field(None, description="Alert end time")
    issued_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "location": "Miami",
                "alert_type": "hurricane",
                "severity": "high",
                "description": "Hurricane warning in effect",
                "start_time": "2025-11-16T14:00:00Z",
                "end_time": "2025-11-17T06:00:00Z",
                "issued_at": "2025-11-16T10:00:00Z",
            }
        }


# ============================================================================
# Event Data Factory Functions
# ============================================================================


def create_weather_location_saved_event_data(
    user_id: str,
    location_id: int,
    location: str,
    latitude: float,
    longitude: float,
    is_default: bool = False,
    nickname: Optional[str] = None,
) -> WeatherLocationSavedEventData:
    """Create WeatherLocationSavedEventData instance"""
    return WeatherLocationSavedEventData(
        user_id=user_id,
        location_id=location_id,
        location=location,
        latitude=latitude,
        longitude=longitude,
        is_default=is_default,
        nickname=nickname,
    )


def create_weather_alert_event_data(
    user_id: str,
    location: str,
    alert_type: str,
    severity: str,
    description: str,
    start_time: datetime,
    end_time: Optional[datetime] = None,
) -> WeatherAlertEventData:
    """Create WeatherAlertEventData instance"""
    return WeatherAlertEventData(
        user_id=user_id,
        location=location,
        alert_type=alert_type,
        severity=severity,
        description=description,
        start_time=start_time,
        end_time=end_time,
    )
