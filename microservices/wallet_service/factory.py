"""
Wallet Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_wallet_service
    service = create_wallet_service(config, event_bus)
"""
from typing import Optional

from core.config_manager import ConfigManager

from .wallet_service import WalletService


def create_wallet_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
    account_client=None,
) -> WalletService:
    """
    Create WalletService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Configuration manager
        event_bus: Event bus for publishing events
        account_client: Account service client for user validation

    Returns:
        Configured WalletService instance
    """
    # Import real repository here (not at module level)
    from .wallet_repository import WalletRepository

    repository = WalletRepository(config=config)

    # Import real account client if not provided
    if account_client is None:
        from .clients.account_client import AccountClient
        account_client = AccountClient()

    return WalletService(
        repository=repository,
        event_bus=event_bus,
        account_client=account_client,
    )


def create_wallet_repository(
    config: Optional[ConfigManager] = None,
):
    """
    Create WalletRepository with real dependencies.

    Args:
        config: Configuration manager

    Returns:
        Configured WalletRepository instance
    """
    from .wallet_repository import WalletRepository

    return WalletRepository(config=config)


__all__ = [
    "create_wallet_service",
    "create_wallet_repository",
]
