"""
Storage Service Factory

Factory functions for creating service instances with real dependencies.
"""
from typing import Optional

from core.config_manager import ConfigManager

from .storage_service import StorageService


def create_storage_service(
    config=None,
    config_manager: Optional[ConfigManager] = None,
    event_bus=None,
    event_publisher=None,
) -> StorageService:
    """
    Create StorageService with real dependencies.

    Args:
        config: Service configuration
        config_manager: Optional ConfigManager instance
        event_bus: Optional event bus for publishing events
        event_publisher: Optional event publisher

    Returns:
        StorageService: Configured service instance
    """
    service = StorageService(
        config=config,
        config_manager=config_manager,
        event_bus=event_bus,
        event_publisher=event_publisher,
    )
    return service
