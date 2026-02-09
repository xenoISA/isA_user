"""
Media Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_media_service
    service = create_media_service(config, event_bus)
"""
from typing import Optional

from core.config_manager import ConfigManager

from .media_service import MediaService


def create_media_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> MediaService:
    """
    Create MediaService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Configuration manager
        event_bus: Event bus for publishing events

    Returns:
        Configured MediaService instance
    """
    # Import real repository here (not at module level)
    from .media_repository import MediaRepository

    repository = MediaRepository(config=config)

    # Import real service clients
    storage_client = None
    device_client = None

    try:
        from microservices.storage_service.client import StorageServiceClient
        storage_client = StorageServiceClient()
    except ImportError:
        pass

    try:
        from microservices.device_service.client import DeviceServiceClient
        device_client = DeviceServiceClient()
    except ImportError:
        pass

    return MediaService(
        repository=repository,
        event_bus=event_bus,
        storage_client=storage_client,
        device_client=device_client,
    )
