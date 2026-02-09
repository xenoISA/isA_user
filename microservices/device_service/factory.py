"""
Device Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_device_service
    service = create_device_service(config, event_bus)
"""
import logging
from typing import Optional

from core.config_manager import ConfigManager

from .device_service import DeviceService

logger = logging.getLogger(__name__)


def create_device_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> DeviceService:
    """
    Create DeviceService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: ConfigManager for service discovery
        event_bus: Event bus for publishing events

    Returns:
        DeviceService instance with real dependencies
    """
    # Import real repository here (not at module level)
    from .device_repository import DeviceRepository

    # Create repository with config
    repository = DeviceRepository(config=config)

    # Initialize MQTT client if available (lazy loading)
    mqtt_client = None
    try:
        from core.mqtt_client import DeviceCommandClient
        # Don't create immediately, will be lazy loaded by service
        mqtt_client = None
    except ImportError:
        logger.warning("MQTT client not available - commands will be simulated")
        mqtt_client = None

    return DeviceService(
        repository=repository,
        event_bus=event_bus,
        mqtt_client=mqtt_client,
    )
