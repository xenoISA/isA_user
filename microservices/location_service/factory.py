"""
Location Service Factory

Factory functions for creating service instances with real dependencies.
"""
from typing import Optional

from .location_service import LocationService


def create_location_service(
    consul_registry=None,
    event_bus=None,
) -> LocationService:
    """
    Create LocationService with real dependencies.

    Args:
        consul_registry: Optional Consul registry for service discovery
        event_bus: Optional event bus for publishing events

    Returns:
        LocationService: Configured service instance
    """
    service = LocationService(
        consul_registry=consul_registry,
        event_bus=event_bus,
    )
    return service
