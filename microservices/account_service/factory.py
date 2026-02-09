"""
Account Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_account_service
    service = create_account_service(config, event_bus)
"""
from typing import Optional

from core.config_manager import ConfigManager

from .account_service import AccountService


def create_account_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
    subscription_client=None,
) -> AccountService:
    """
    Create AccountService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Configuration manager
        event_bus: Event bus for publishing events
        subscription_client: Subscription service client

    Returns:
        Configured AccountService instance
    """
    # Import real repository here (not at module level)
    from .account_repository import AccountRepository

    repository = AccountRepository(config=config)

    return AccountService(
        repository=repository,
        event_bus=event_bus,
        subscription_client=subscription_client,
    )
