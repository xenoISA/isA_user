"""
Payment Service Factory

Factory for creating PaymentService with real dependencies.
This is the ONLY module that imports concrete implementations.
"""

import logging
import os
from typing import Optional

from core.config_manager import ConfigManager

from .payment_repository import PaymentRepository
from .payment_service import PaymentService

logger = logging.getLogger(__name__)


def create_payment_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
    stripe_secret_key: Optional[str] = None,
) -> PaymentService:
    """
    Create PaymentService with all real dependencies

    Args:
        config: Optional config manager (creates default if not provided)
        event_bus: Optional event bus for event publishing
        stripe_secret_key: Optional Stripe secret key (falls back to env var)

    Returns:
        Fully initialized PaymentService instance
    """
    # Initialize config if not provided
    if config is None:
        config = ConfigManager("payment_service")

    # Create repository
    repository = PaymentRepository(config=config)

    # Get Stripe secret key from parameter or environment
    if stripe_secret_key is None:
        stripe_secret_key = os.getenv("STRIPE_SECRET_KEY") or os.getenv(
            "PAYMENT_SERVICE_STRIPE_SECRET_KEY"
        )

    # Initialize service clients (with fallback)
    account_client = None
    wallet_client = None
    billing_client = None
    product_client = None

    try:
        from .clients import AccountClient, WalletClient, BillingClient, ProductClient

        account_client = AccountClient()
        wallet_client = WalletClient()
        billing_client = BillingClient()
        product_client = ProductClient()
        logger.info(
            "✅ Service clients initialized for payment service "
            "(AccountClient, WalletClient, BillingClient, ProductClient)"
        )

    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize service clients: {e}")
        logger.warning("Payment service will operate with limited inter-service communication")

    # Create and return service
    return PaymentService(
        repository=repository,
        stripe_secret_key=stripe_secret_key,
        event_bus=event_bus,
        account_client=account_client,
        wallet_client=wallet_client,
        billing_client=billing_client,
        product_client=product_client,
        config=config,
    )


__all__ = ["create_payment_service"]
