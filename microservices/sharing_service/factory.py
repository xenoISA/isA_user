"""
Sharing Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.
"""

from typing import Optional

from core.config_manager import ConfigManager

from .sharing_service import SharingService


def create_sharing_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
    session_client=None,
) -> SharingService:
    """
    Create SharingService with real dependencies.

    Args:
        config: Configuration manager
        event_bus: Event bus for publishing events
        session_client: Session service client

    Returns:
        Configured SharingService instance
    """
    from .sharing_repository import ShareRepository
    from .clients.session_client import SessionServiceClient

    share_repository = ShareRepository(config=config)

    if session_client is None:
        session_client = SessionServiceClient()

    return SharingService(
        share_repo=share_repository,
        event_bus=event_bus,
        session_client=session_client,
    )


def create_sharing_service_for_testing(
    share_repo=None,
    event_bus=None,
    session_client=None,
) -> SharingService:
    """
    Create SharingService with injected dependencies for testing.

    All dependencies are optional - pass mocks for unit/component testing.
    """
    return SharingService(
        share_repo=share_repo,
        event_bus=event_bus,
        session_client=session_client,
    )
