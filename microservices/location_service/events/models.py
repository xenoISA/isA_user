"""
Location Service Event Data Models

Event models for location service event-driven architecture
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class LocationEventType(str, Enum):
    """
    Events published by location_service.

    Stream: location-stream
    Subjects: location.>
    """
    LOCATION_UPDATED = "location.updated"
    LOCATION_BATCH_UPDATED = "location.batch.updated"
    GEOFENCE_CREATED = "location.geofence.created"
    GEOFENCE_ENTERED = "location.geofence.entered"
    GEOFENCE_EXITED = "location.geofence.exited"


class LocationSubscribedEventType(str, Enum):
    """Events that location_service subscribes to from other services."""
    USER_DELETED = "user.deleted"
    DEVICE_REGISTERED = "device.registered"


class LocationStreamConfig:
    """Stream configuration for location_service"""
    STREAM_NAME = "location-stream"
    SUBJECTS = ["location.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "location"



class DeviceDeletedEventData(BaseModel):
    """
    Device deleted event (subscribed by location_service)

    When a device is deleted, clean up all location data

    NATS Subject: *.device.deleted
    Publisher: device_service
    """

    device_id: str = Field(..., description="Device ID")
    user_id: Optional[str] = Field(None, description="User ID")
    timestamp: Optional[datetime] = Field(None, description="Deletion timestamp")
    reason: Optional[str] = Field(None, description="Deletion reason")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class UserDeletedEventData(BaseModel):
    """
    User deleted event (subscribed by location_service)

    When a user is deleted, clean up all location data for their devices

    NATS Subject: *.user.deleted
    Publisher: account_service
    """

    user_id: str = Field(..., description="User ID")
    timestamp: Optional[datetime] = Field(None, description="Deletion timestamp")
    reason: Optional[str] = Field(None, description="Deletion reason")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class LocationUpdatedEventData(BaseModel):
    """
    Location updated event (published by location_service)

    Notifies when a device location is updated

    NATS Subject: location.updated
    Subscribers: notification_service, analytics_service
    """

    device_id: str = Field(..., description="Device ID")
    user_id: str = Field(..., description="User ID")
    location_id: str = Field(..., description="Location record ID")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")
    accuracy: Optional[float] = Field(None, description="Accuracy in meters")
    altitude: Optional[float] = Field(None, description="Altitude in meters")
    speed: Optional[float] = Field(None, description="Speed in m/s")
    heading: Optional[float] = Field(None, description="Heading in degrees")
    location_method: str = Field(default="gps", description="Location method")
    timestamp: Optional[datetime] = Field(None, description="Location timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class GeofenceEnteredEventData(BaseModel):
    """
    Geofence entered event (published by location_service)

    Notifies when a device enters a geofence

    NATS Subject: location.geofence.entered
    Subscribers: notification_service, automation_service
    """

    device_id: str = Field(..., description="Device ID")
    user_id: str = Field(..., description="User ID")
    geofence_id: str = Field(..., description="Geofence ID")
    geofence_name: str = Field(..., description="Geofence name")
    latitude: float = Field(..., description="Entry latitude")
    longitude: float = Field(..., description="Entry longitude")
    timestamp: Optional[datetime] = Field(None, description="Entry timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class GeofenceExitedEventData(BaseModel):
    """
    Geofence exited event (published by location_service)

    Notifies when a device exits a geofence

    NATS Subject: location.geofence.exited
    Subscribers: notification_service, automation_service
    """

    device_id: str = Field(..., description="Device ID")
    user_id: str = Field(..., description="User ID")
    geofence_id: str = Field(..., description="Geofence ID")
    geofence_name: str = Field(..., description="Geofence name")
    latitude: float = Field(..., description="Exit latitude")
    longitude: float = Field(..., description="Exit longitude")
    timestamp: Optional[datetime] = Field(None, description="Exit timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class GeofenceCreatedEventData(BaseModel):
    """
    Geofence created event (published by location_service)

    Notifies when a new geofence is created

    NATS Subject: location.geofence.created
    Subscribers: notification_service
    """

    geofence_id: str = Field(..., description="Geofence ID")
    user_id: Optional[str] = Field(None, description="User ID")
    name: str = Field(..., description="Geofence name")
    shape_type: str = Field(..., description="Shape type (circle, polygon)")
    center_lat: float = Field(..., description="Center latitude")
    center_lon: float = Field(..., description="Center longitude")
    timestamp: Optional[datetime] = Field(None, description="Creation timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class PlaceCreatedEventData(BaseModel):
    """
    Place created event (published by location_service)

    Notifies when a user creates a new place

    NATS Subject: location.place.created
    Subscribers: calendar_service, notification_service
    """

    place_id: str = Field(..., description="Place ID")
    user_id: str = Field(..., description="User ID")
    name: str = Field(..., description="Place name")
    category: str = Field(..., description="Place category")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")
    timestamp: Optional[datetime] = Field(None, description="Creation timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Helper functions for parsing incoming events


def parse_device_deleted_event(event_data: dict) -> DeviceDeletedEventData:
    """Parse device.deleted event"""
    return DeviceDeletedEventData(**event_data)


def parse_user_deleted_event(event_data: dict) -> UserDeletedEventData:
    """Parse user.deleted event"""
    return UserDeletedEventData(**event_data)


# Helper functions for creating outgoing events


def create_location_updated_event_data(
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
) -> LocationUpdatedEventData:
    """Create location.updated event data"""
    return LocationUpdatedEventData(
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
        timestamp=datetime.utcnow(),
    )


def create_geofence_entered_event_data(
    device_id: str,
    user_id: str,
    geofence_id: str,
    geofence_name: str,
    latitude: float,
    longitude: float,
) -> GeofenceEnteredEventData:
    """Create geofence.entered event data"""
    return GeofenceEnteredEventData(
        device_id=device_id,
        user_id=user_id,
        geofence_id=geofence_id,
        geofence_name=geofence_name,
        latitude=latitude,
        longitude=longitude,
        timestamp=datetime.utcnow(),
    )


def create_geofence_exited_event_data(
    device_id: str,
    user_id: str,
    geofence_id: str,
    geofence_name: str,
    latitude: float,
    longitude: float,
) -> GeofenceExitedEventData:
    """Create geofence.exited event data"""
    return GeofenceExitedEventData(
        device_id=device_id,
        user_id=user_id,
        geofence_id=geofence_id,
        geofence_name=geofence_name,
        latitude=latitude,
        longitude=longitude,
        timestamp=datetime.utcnow(),
    )


def create_geofence_created_event_data(
    geofence_id: str,
    name: str,
    shape_type: str,
    center_lat: float,
    center_lon: float,
    user_id: Optional[str] = None,
) -> GeofenceCreatedEventData:
    """Create geofence.created event data"""
    return GeofenceCreatedEventData(
        geofence_id=geofence_id,
        user_id=user_id,
        name=name,
        shape_type=shape_type,
        center_lat=center_lat,
        center_lon=center_lon,
        timestamp=datetime.utcnow(),
    )


def create_place_created_event_data(
    place_id: str,
    user_id: str,
    name: str,
    category: str,
    latitude: float,
    longitude: float,
) -> PlaceCreatedEventData:
    """Create place.created event data"""
    return PlaceCreatedEventData(
        place_id=place_id,
        user_id=user_id,
        name=name,
        category=category,
        latitude=latitude,
        longitude=longitude,
        timestamp=datetime.utcnow(),
    )


__all__ = [
    # Incoming event models
    "DeviceDeletedEventData",
    "UserDeletedEventData",
    # Outgoing event models
    "LocationUpdatedEventData",
    "GeofenceEnteredEventData",
    "GeofenceExitedEventData",
    "GeofenceCreatedEventData",
    "PlaceCreatedEventData",
    # Parsing helpers
    "parse_device_deleted_event",
    "parse_user_deleted_event",
    # Creation helpers
    "create_location_updated_event_data",
    "create_geofence_entered_event_data",
    "create_geofence_exited_event_data",
    "create_geofence_created_event_data",
    "create_place_created_event_data",
]
