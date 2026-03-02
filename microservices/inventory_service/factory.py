"""
Inventory Service Factory

Factory functions for creating repository instances with real dependencies.
"""
from typing import Optional

from core.config_manager import ConfigManager

from .inventory_repository import InventoryRepository


def create_inventory_repository(
    config: Optional[ConfigManager] = None,
) -> InventoryRepository:
    """
    Create InventoryRepository with real dependencies.

    Args:
        config: Optional ConfigManager instance

    Returns:
        InventoryRepository: Configured repository instance
    """
    return InventoryRepository(config=config)
