"""
Session Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_session_service
    service = create_session_service(config, event_bus)
"""
from typing import Optional

from core.config_manager import ConfigManager

from .session_service import SessionService


def create_session_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
    account_client=None,
) -> SessionService:
    """
    Create SessionService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Configuration manager
        event_bus: Event bus for publishing events
        account_client: Account service client for user validation

    Returns:
        Configured SessionService instance
    """
    # Import real repositories here (not at module level)
    from .session_repository import SessionRepository, SessionMessageRepository

    # Create repositories with config for service discovery
    session_repository = SessionRepository(config=config)
    message_repository = SessionMessageRepository(config=config)

    # Import account client if not provided
    if account_client is None:
        from microservices.account_service.client import AccountServiceClient
        account_client = AccountServiceClient()

    return SessionService(
        session_repo=session_repository,
        message_repo=message_repository,
        event_bus=event_bus,
        account_client=account_client,
    )


def create_session_service_for_testing(
    session_repo=None,
    message_repo=None,
    event_bus=None,
    account_client=None,
) -> SessionService:
    """
    Create SessionService with injected dependencies for testing.

    All dependencies are optional - pass mocks for unit/component testing.

    Args:
        session_repo: Mock session repository
        message_repo: Mock message repository
        event_bus: Mock event bus
        account_client: Mock account client

    Returns:
        SessionService instance with injected dependencies
    """
    return SessionService(
        session_repo=session_repo,
        message_repo=message_repo,
        event_bus=event_bus,
        account_client=account_client,
    )
