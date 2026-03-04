"""
Fulfillment Service Factory

Factory functions for creating service and repository instances with real dependencies.
"""
from typing import Optional

from core.config_manager import ConfigManager

from .fulfillment_repository import FulfillmentRepository
from .fulfillment_service import FulfillmentService
from .providers.mock import MockFulfillmentProvider


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


def create_fulfillment_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
    provider=None,
) -> FulfillmentService:
    """
    Create FulfillmentService with all dependencies.

    Args:
        config: Optional ConfigManager instance
        event_bus: Optional event bus for publishing events
        provider: Optional fulfillment provider (defaults to MockFulfillmentProvider)

    Returns:
        FulfillmentService: Configured service instance
    """
    repository = create_fulfillment_repository(config=config)
    if provider is None:
        provider = MockFulfillmentProvider()
    return FulfillmentService(
        repository=repository, event_bus=event_bus, provider=provider
    )
