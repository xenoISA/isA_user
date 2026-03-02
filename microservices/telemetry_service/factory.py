"""
Telemetry Service Factory

Factory functions for creating service instances with real dependencies.
"""
from typing import Optional

from core.config_manager import ConfigManager

from .telemetry_service import TelemetryService


def create_telemetry_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> TelemetryService:
    """
    Create TelemetryService with real dependencies.

    Args:
        config: Optional ConfigManager instance
        event_bus: Optional event bus for publishing events

    Returns:
        TelemetryService: Configured service instance
    """
    service = TelemetryService(event_bus=event_bus, config=config)
    return service
