"""
Order Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_order_service
    service = create_order_service(config, event_bus)
"""
from typing import Optional

from core.config_manager import ConfigManager

from .order_service import OrderService


def create_order_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
    payment_client=None,
    wallet_client=None,
    account_client=None,
    storage_client=None,
    billing_client=None,
    inventory_client=None,
    tax_client=None,
    fulfillment_client=None,
) -> OrderService:
    """
    Create OrderService with real dependencies.

    This function imports the real repository (which has I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        config: Configuration manager
        event_bus: Event bus for publishing events
        payment_client: Payment service client
        wallet_client: Wallet service client
        account_client: Account service client
        storage_client: Storage service client
        billing_client: Billing service client

    Returns:
        Configured OrderService instance
    """
    # Import real repository here (not at module level)
    from .order_repository import OrderRepository

    repository = OrderRepository(config=config)

    return OrderService(
        repository=repository,
        event_bus=event_bus,
        payment_client=payment_client,
        wallet_client=wallet_client,
        account_client=account_client,
        storage_client=storage_client,
        billing_client=billing_client,
        inventory_client=inventory_client,
        tax_client=tax_client,
        fulfillment_client=fulfillment_client,
    )
