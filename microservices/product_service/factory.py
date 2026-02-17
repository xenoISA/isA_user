"""
Product Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_product_service
    service = await create_product_service(config, event_bus)
"""
from typing import Optional

from core.config_manager import ConfigManager

from .product_service import ProductService


async def create_product_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
    account_client=None,
    organization_client=None,
) -> ProductService:
    """
    Create ProductService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Configuration manager
        event_bus: Event bus for publishing events
        account_client: Account service client
        organization_client: Organization service client

    Returns:
        Configured ProductService instance
    """
    # Import real repository here (not at module level)
    from .product_repository import ProductRepository

    repository = ProductRepository(config=config)
    await repository.initialize()

    return ProductService(
        repository=repository,
        event_bus=event_bus,
        account_client=account_client,
        organization_client=organization_client,
    )


def create_product_service_sync(
    config: Optional[ConfigManager] = None,
    event_bus=None,
    account_client=None,
    organization_client=None,
) -> ProductService:
    """
    Create ProductService with real dependencies (sync version).

    This version does NOT initialize the repository async.
    Useful when you need to create the service synchronously and
    initialize later.

    Args:
        config: Configuration manager
        event_bus: Event bus for publishing events
        account_client: Account service client
        organization_client: Organization service client

    Returns:
        Configured ProductService instance (not initialized)
    """
    # Import real repository here (not at module level)
    from .product_repository import ProductRepository

    repository = ProductRepository(config=config)

    return ProductService(
        repository=repository,
        event_bus=event_bus,
        account_client=account_client,
        organization_client=organization_client,
    )
