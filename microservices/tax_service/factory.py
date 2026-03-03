"""
Tax Service Factory

Factory functions for creating repository instances with real dependencies.
"""
from typing import Optional

from core.config_manager import ConfigManager

from .tax_repository import TaxRepository


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
