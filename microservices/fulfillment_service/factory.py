"""
Fulfillment Service Factory

Factory functions for creating repository instances with real dependencies.
"""
from typing import Optional

from core.config_manager import ConfigManager

from .fulfillment_repository import FulfillmentRepository


def create_fulfillment_repository(
    config: Optional[ConfigManager] = None,
) -> FulfillmentRepository:
    """
    Create FulfillmentRepository with real dependencies.

    Args:
        config: Optional ConfigManager instance

    Returns:
        FulfillmentRepository: Configured repository instance
    """
    return FulfillmentRepository(config=config)
