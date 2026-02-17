"""
Location Service Event Handlers

Standard Structure:
- models.py: Event data models (Pydantic)
- handlers.py: Event handlers (subscribe to events from other services)
- publishers.py: Event publishers (publish events to other services)
"""

# Event Handlers
from .handlers import (
    get_event_handlers,
    handle_device_deleted,
    handle_user_deleted,
)

# Event Models
from .models import (
    DeviceDeletedEventData,
    GeofenceCreatedEventData,
    GeofenceEnteredEventData,
    GeofenceExitedEventData,
    LocationUpdatedEventData,
    PlaceCreatedEventData,
    UserDeletedEventData,
    create_geofence_created_event_data,
    create_geofence_entered_event_data,
    create_geofence_exited_event_data,
    create_location_updated_event_data,
    create_place_created_event_data,
    parse_device_deleted_event,
    parse_user_deleted_event,
)

# Event Publishers
from .publishers import (
    publish_geofence_created,
    publish_geofence_entered,
    publish_geofence_exited,
    publish_location_updated,
    publish_place_created,
)

__all__ = [
    # Event Handlers
    "get_event_handlers",
    "handle_device_deleted",
    "handle_user_deleted",
    # Event Models - Incoming
    "DeviceDeletedEventData",
    "UserDeletedEventData",
    # Event Models - Outgoing
    "LocationUpdatedEventData",
    "GeofenceEnteredEventData",
    "GeofenceExitedEventData",
    "GeofenceCreatedEventData",
    "PlaceCreatedEventData",
    # Model Parsers
    "parse_device_deleted_event",
    "parse_user_deleted_event",
    # Model Creators
    "create_location_updated_event_data",
    "create_geofence_entered_event_data",
    "create_geofence_exited_event_data",
    "create_geofence_created_event_data",
    "create_place_created_event_data",
    # Event Publishers
    "publish_location_updated",
    "publish_geofence_entered",
    "publish_geofence_exited",
    "publish_geofence_created",
    "publish_place_created",
]
