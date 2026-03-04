"""
Tax Service Factory

Factory functions for creating service and repository instances with real dependencies.
"""
from typing import Optional

from core.config_manager import ConfigManager

from .tax_repository import TaxRepository
from .tax_service import TaxService
from .providers.mock import MockTaxProvider


def create_tax_repository(
    config: Optional[ConfigManager] = None,
) -> TaxRepository:
    """
    Create TaxRepository with real dependencies.

    Args:
        config: Optional ConfigManager instance

    Returns:
        TaxRepository: Configured repository instance
    """
    return TaxRepository(config=config)


def create_tax_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
    provider=None,
) -> TaxService:
    """
    Create TaxService with all dependencies.

    Args:
        config: Optional ConfigManager instance
        event_bus: Optional event bus for publishing events
        provider: Optional tax provider (defaults to MockTaxProvider)

    Returns:
        TaxService: Configured service instance
    """
    repository = create_tax_repository(config=config)
    if provider is None:
        provider = MockTaxProvider()
    return TaxService(repository=repository, event_bus=event_bus, provider=provider)
