"""
Vault Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_vault_service
    service = create_vault_service(config, event_bus, blockchain_client)
"""
from typing import Optional

from core.config_manager import ConfigManager

from .vault_service import VaultService


def create_vault_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
    blockchain_client=None,
) -> VaultService:
    """
    Create VaultService with real dependencies.

    This function imports the real repository and encryption (which have I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Configuration manager
        event_bus: Event bus for publishing events
        blockchain_client: Blockchain client for verification

    Returns:
        Configured VaultService instance
    """
    # Import real dependencies here (not at module level)
    from .vault_repository import VaultRepository
    from .encryption import VaultEncryption, BlockchainVaultIntegration

    # Create repository
    repository = VaultRepository(config=config)

    # Create encryption
    encryption = VaultEncryption()

    # Create blockchain integration
    blockchain = BlockchainVaultIntegration(blockchain_client)

    return VaultService(
        repository=repository,
        encryption=encryption,
        blockchain=blockchain,
        event_bus=event_bus,
    )


def create_vault_repository(
    config: Optional[ConfigManager] = None,
):
    """
    Create VaultRepository with real dependencies.

    Args:
        config: Configuration manager

    Returns:
        Configured VaultRepository instance
    """
    from .vault_repository import VaultRepository

    return VaultRepository(config=config)


def create_vault_encryption(master_key: Optional[str] = None):
    """
    Create VaultEncryption with real dependencies.

    Args:
        master_key: Master encryption key (base64 encoded)

    Returns:
        Configured VaultEncryption instance
    """
    from .encryption import VaultEncryption

    return VaultEncryption(master_key=master_key)


def create_blockchain_integration(blockchain_client=None):
    """
    Create BlockchainVaultIntegration with real dependencies.

    Args:
        blockchain_client: Blockchain client instance

    Returns:
        Configured BlockchainVaultIntegration instance
    """
    from .encryption import BlockchainVaultIntegration

    return BlockchainVaultIntegration(blockchain_client)


__all__ = [
    "create_vault_service",
    "create_vault_repository",
    "create_vault_encryption",
    "create_blockchain_integration",
]
