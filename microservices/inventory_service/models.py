"""
Inventory Service Data Models

Supports real-time stock for physical SKUs and infinite stock for digital items.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class InventoryPolicy(str, Enum):
    """Inventory policy"""
    INFINITE = "infinite"
    FINITE = "finite"


class ReservationStatus(str, Enum):
    """Reservation status"""
    ACTIVE = "active"
    COMMITTED = "committed"
    RELEASED = "released"
    EXPIRED = "expired"


class InventoryItem(BaseModel):
    """Stock record for a SKU"""
    sku_id: str
    location_id: Optional[str] = None
    inventory_policy: InventoryPolicy = InventoryPolicy.FINITE
    on_hand: int = Field(default=0, ge=0)
    reserved: int = Field(default=0, ge=0)
    available: int = Field(default=0, ge=0)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InventoryReservation(BaseModel):
    """Reservation record for an order"""
    reservation_id: str
    order_id: str
    sku_id: str
    quantity: int = Field(..., gt=0)
    status: ReservationStatus = ReservationStatus.ACTIVE
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
