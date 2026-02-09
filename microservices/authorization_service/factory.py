"""
Authorization Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_authorization_service
    service = create_authorization_service(config, event_bus)
"""
from typing import Optional

from core.config_manager import ConfigManager

from .authorization_service import AuthorizationService


def create_authorization_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> AuthorizationService:
    """
    Create AuthorizationService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Configuration manager
        event_bus: Event bus for publishing events

    Returns:
        Configured AuthorizationService instance
    """
    # Import real repository here (not at module level)
    from .authorization_repository import AuthorizationRepository

    repository = AuthorizationRepository(config=config)

    return AuthorizationService(
        repository=repository,
        event_bus=event_bus,
        config=config,
    )
