"""
Album Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules (repository).

Usage:
    from .factory import create_album_service
    service = create_album_service(config, event_bus)
"""
from typing import Optional

from core.config_manager import ConfigManager

from .album_service import AlbumService


def create_album_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> AlbumService:
    """
    Create AlbumService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Optional ConfigManager instance
        event_bus: Optional event bus for publishing events

    Returns:
        AlbumService: Configured service instance with real repository
    """
    # Import real repository here (not at module level)
    from .album_repository import AlbumRepository

    repository = AlbumRepository(config=config)

    return AlbumService(
        repository=repository,
        event_bus=event_bus,
    )
