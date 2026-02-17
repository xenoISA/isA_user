"""
Calendar Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_calendar_service
    service = create_calendar_service(config, event_bus)
"""
from typing import Optional

from core.config_manager import ConfigManager

from .calendar_service import CalendarService


def create_calendar_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> CalendarService:
    """
    Create CalendarService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Configuration manager for service discovery
        event_bus: Event bus for publishing events

    Returns:
        CalendarService instance with real dependencies
    """
    # Import real repository here (not at module level)
    from .calendar_repository import CalendarRepository

    repository = CalendarRepository(config=config)

    return CalendarService(
        repository=repository,
        event_bus=event_bus,
    )
