"""
OTA Service Factory

Factory functions for creating service instances with real dependencies.
"""
from typing import Optional

from core.config_manager import ConfigManager

from .ota_service import OTAService


def create_ota_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
    device_client=None,
    storage_client=None,
    notification_client=None,
) -> OTAService:
    """
    Create OTAService with real dependencies.

    Args:
        config: Optional ConfigManager instance
        event_bus: Optional event bus for publishing events
        device_client: Optional device client for device operations
        storage_client: Optional storage client for firmware storage
        notification_client: Optional notification client for alerts

    Returns:
        OTAService: Configured service instance
    """
    service = OTAService(
        event_bus=event_bus,
        config=config,
        device_client=device_client,
        storage_client=storage_client,
        notification_client=notification_client,
    )
    return service
