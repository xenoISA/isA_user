"""
Credit Service Factory

Factory for creating CreditService with real dependencies.
This is the ONLY module that imports concrete implementations.
"""

import logging
from typing import Optional

from core.config_manager import ConfigManager

from .credit_repository import CreditRepository
from .credit_service import CreditService

logger = logging.getLogger(__name__)


def create_credit_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
    account_client=None,
    subscription_client=None,
) -> CreditService:
    """
    Create CreditService with all real dependencies

    Args:
        config: Optional config manager (creates default if not provided)
        event_bus: Optional event bus for event publishing
        account_client: Optional account client (creates default if not provided)
        subscription_client: Optional subscription client (creates default if not provided)

    Returns:
        Fully initialized CreditService instance
    """
    # Initialize config if not provided
    if config is None:
        config = ConfigManager("credit_service")

    # Create repository
    repository = CreditRepository(config=config)

    # Initialize service clients if not provided
    if account_client is None:
        try:
            from .clients.account_client import AccountClient

            account_client = AccountClient(config=config)
            logger.info("✅ AccountClient initialized for credit service")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize AccountClient: {e}")
            logger.warning("Credit service will operate without account client")

    if subscription_client is None:
        try:
            from .clients.subscription_client import SubscriptionClient

            subscription_client = SubscriptionClient(config=config)
            logger.info("✅ SubscriptionClient initialized for credit service")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize SubscriptionClient: {e}")
            logger.warning("Credit service will operate without subscription client")

    # Create and return service
    return CreditService(
        repository=repository,
        event_bus=event_bus,
        account_client=account_client,
        subscription_client=subscription_client,
    )


__all__ = ["create_credit_service"]
