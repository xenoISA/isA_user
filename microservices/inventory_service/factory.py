"""
Inventory Service Factory

Factory functions for creating service and repository instances with real dependencies.
"""
from typing import Optional

from core.config_manager import ConfigManager

from .inventory_repository import InventoryRepository
from .inventory_service import InventoryService


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


def create_inventory_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> InventoryService:
    """
    Create InventoryService with all dependencies.

    Args:
        config: Optional ConfigManager instance
        event_bus: Optional event bus for publishing events

    Returns:
        InventoryService: Configured service instance
    """
    repository = create_inventory_repository(config=config)
    return InventoryService(repository=repository, event_bus=event_bus)
