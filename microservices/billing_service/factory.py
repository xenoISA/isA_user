"""
Billing Service Factory

Factory for creating BillingService with real dependencies.
This is the ONLY module that imports concrete implementations.
"""

import logging
from typing import Optional

from core.config_manager import ConfigManager

from .billing_repository import BillingRepository
from .billing_service import BillingService

logger = logging.getLogger(__name__)


def create_billing_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> BillingService:
    """
    Create BillingService with all real dependencies

    Args:
        config: Optional config manager (creates default if not provided)
        event_bus: Optional event bus for event publishing

    Returns:
        Fully initialized BillingService instance
    """
    # Initialize config if not provided
    if config is None:
        config = ConfigManager("billing_service")

    # Create repository
    repository = BillingRepository(config=config)

    # Initialize service clients (with fallback)
    product_client = None
    wallet_client = None
    subscription_client = None

    try:
        from .clients import ProductClient, WalletClient, SubscriptionClient

        wallet_client = WalletClient()
        product_client = ProductClient()
        subscription_client = SubscriptionClient()
        logger.info(
            "✅ Service clients initialized for billing service (including SubscriptionClient)"
        )

    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize service clients: {e}")
        logger.warning("Billing service will fall back to HTTP calls")

    # Create and return service
    return BillingService(
        repository=repository,
        event_bus=event_bus,
        product_client=product_client,
        wallet_client=wallet_client,
        subscription_client=subscription_client,
    )


__all__ = ["create_billing_service"]
