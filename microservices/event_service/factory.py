"""
Event Service Factory

Factory functions for creating service instances with real dependencies.
"""
from typing import Optional

from core.config_manager import ConfigManager

from .event_service import EventService


def create_event_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> EventService:
    """
    Create EventService with real dependencies.

    Args:
        config: Optional ConfigManager instance
        event_bus: Optional event bus for publishing events

    Returns:
        EventService: Configured service instance
    """
    service = EventService(event_bus=event_bus, config_manager=config)
    return service
