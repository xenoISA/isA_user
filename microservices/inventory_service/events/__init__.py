"""
Inventory Service Events Module

Exports all event-related functionality for inventory service
"""

from .models import (
    InventoryEventType,
    InventorySubscribedEventType,
    InventoryStreamConfig,
    ReservedItem,
    StockReservedEvent,
    StockCommittedEvent,
    StockReleasedEvent,
    StockFailedEvent
)

from .publishers import (
    publish_stock_reserved,
    publish_stock_committed,
    publish_stock_released,
    publish_stock_failed
)

from .handlers import get_event_handlers

__all__ = [
    # Event Types
    "InventoryEventType",
    "InventorySubscribedEventType",
    "InventoryStreamConfig",
    # Event Models
    "ReservedItem",
    "StockReservedEvent",
    "StockCommittedEvent",
    "StockReleasedEvent",
    "StockFailedEvent",
    # Publishers
    "publish_stock_reserved",
    "publish_stock_committed",
    "publish_stock_released",
    "publish_stock_failed",
    # Handlers
    "get_event_handlers"
]
