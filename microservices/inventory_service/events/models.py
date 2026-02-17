"""
Inventory Service Event Models

Pydantic models for events published by inventory service
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime


# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class InventoryEventType(str, Enum):
    """
    Events published by inventory_service.

    Stream: inventory-stream
    Subjects: inventory.>
    """
    STOCK_RESERVED = "inventory.reserved"
    STOCK_COMMITTED = "inventory.committed"
    STOCK_RELEASED = "inventory.released"
    STOCK_FAILED = "inventory.failed"


class InventorySubscribedEventType(str, Enum):
    """Events that inventory_service subscribes to from other services."""
    ORDER_CREATED = "order.created"
    PAYMENT_COMPLETED = "payment.completed"
    ORDER_CANCELED = "order.canceled"


class InventoryStreamConfig:
    """Stream configuration for inventory_service"""
    STREAM_NAME = "inventory-stream"
    SUBJECTS = ["inventory.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "inventory"


# =============================================================================
# Event Data Models
# =============================================================================

class ReservedItem(BaseModel):
    """Item reservation details"""
    sku_id: str
    quantity: int
    unit_price: Optional[float] = None


class StockReservedEvent(BaseModel):
    """Event published when stock is successfully reserved for an order"""
    order_id: str
    reservation_id: str
    user_id: str
    items: List[ReservedItem]
    expires_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StockCommittedEvent(BaseModel):
    """Event published when reservation is committed (after payment)"""
    order_id: str
    reservation_id: str
    user_id: str
    items: List[ReservedItem]
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StockReleasedEvent(BaseModel):
    """Event published when stock reservation is released (order canceled)"""
    order_id: str
    reservation_id: Optional[str] = None
    user_id: str
    items: List[ReservedItem]
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StockFailedEvent(BaseModel):
    """Event published when stock reservation fails"""
    order_id: str
    user_id: str
    items: List[Dict[str, Any]]
    error_code: Optional[str] = None
    error_message: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
