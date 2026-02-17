"""
Location Service - Event Definitions

Event types emitted by the location service
"""

from enum import Enum


class LocationEventType(str, Enum):
    """Location service event types"""

    # Location events
    LOCATION_UPDATED = "location.updated"
    LOCATION_BATCH_UPDATED = "location.batch.updated"

    # Geofence events
    GEOFENCE_CREATED = "location.geofence.created"
    GEOFENCE_UPDATED = "location.geofence.updated"
    GEOFENCE_DELETED = "location.geofence.deleted"
    GEOFENCE_ACTIVATED = "location.geofence.activated"
    GEOFENCE_DEACTIVATED = "location.geofence.deactivated"

    # Geofence trigger events
    GEOFENCE_ENTERED = "location.geofence.entered"
    GEOFENCE_EXITED = "location.geofence.exited"
    GEOFENCE_DWELL = "location.geofence.dwell"

    # Movement events
    DEVICE_STARTED_MOVING = "location.device.started_moving"
    DEVICE_STOPPED = "location.device.stopped"
    SIGNIFICANT_MOVEMENT = "location.significant_movement"

    # Place events
    PLACE_CREATED = "location.place.created"
    PLACE_UPDATED = "location.place.updated"
    PLACE_DELETED = "location.place.deleted"
    PLACE_VISITED = "location.place.visited"
    PLACE_LEFT = "location.place.left"

    # Route events
    ROUTE_STARTED = "location.route.started"
    ROUTE_UPDATED = "location.route.updated"
    ROUTE_ENDED = "location.route.ended"

    # Alert events
    LOW_BATTERY_AT_LOCATION = "location.low_battery"
    DEVICE_OUT_OF_BOUNDS = "location.device.out_of_bounds"
