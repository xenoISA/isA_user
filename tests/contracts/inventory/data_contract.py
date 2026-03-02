"""
Inventory Service Data Contract

Defines canonical data structures for inventory service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for inventory service test data.
"""

import uuid
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================================
# Enums (matching production models)
# ============================================================================

class InventoryPolicy(str, Enum):
    """Inventory tracking policy"""
    INFINITE = "infinite"
    FINITE = "finite"


class ReservationStatus(str, Enum):
    """Reservation lifecycle states"""
    ACTIVE = "active"
    COMMITTED = "committed"
    RELEASED = "released"
    EXPIRED = "expired"


# ============================================================================
# Data Models (matching production Pydantic models)
# ============================================================================

class InventoryItem(BaseModel):
    """Inventory stock level for a SKU"""
    sku_id: str
    location_id: Optional[str] = None
    inventory_policy: InventoryPolicy = InventoryPolicy.FINITE
    on_hand: int = Field(default=0, ge=0)
    reserved: int = Field(default=0, ge=0)
    available: int = Field(default=0, ge=0)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InventoryReservation(BaseModel):
    """Stock reservation for an order"""
    reservation_id: str
    order_id: str
    sku_id: str
    quantity: int = Field(..., gt=0)
    status: ReservationStatus = ReservationStatus.ACTIVE
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReservedItem(BaseModel):
    """Item within a reservation"""
    sku_id: str
    quantity: int
    unit_price: Optional[float] = None


# ============================================================================
# Factory Functions
# ============================================================================

class InventoryFactory:
    """Factory for generating test data"""

    @staticmethod
    def reservation_id() -> str:
        return f"res_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def order_id() -> str:
        return f"ord_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def sku_id() -> str:
        return f"sku_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def user_id() -> str:
        return f"user_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def items(count: int = 2) -> List[Dict[str, Any]]:
        return [
            {
                "sku_id": InventoryFactory.sku_id(),
                "quantity": random.randint(1, 10),
                "unit_price": round(random.uniform(5.0, 100.0), 2),
            }
            for _ in range(count)
        ]

    @staticmethod
    def reserve_request(
        order_id: Optional[str] = None,
        items: Optional[List[Dict]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "order_id": order_id or InventoryFactory.order_id(),
            "items": items or InventoryFactory.items(),
            "user_id": user_id or InventoryFactory.user_id(),
        }

    @staticmethod
    def commit_request(
        order_id: Optional[str] = None,
        reservation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "order_id": order_id or InventoryFactory.order_id(),
            "reservation_id": reservation_id or InventoryFactory.reservation_id(),
        }

    @staticmethod
    def release_request(
        order_id: Optional[str] = None,
        reservation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "order_id": order_id or InventoryFactory.order_id(),
            "reservation_id": reservation_id or InventoryFactory.reservation_id(),
        }

    @staticmethod
    def reservation(
        status: ReservationStatus = ReservationStatus.ACTIVE,
        **overrides,
    ) -> InventoryReservation:
        defaults = {
            "reservation_id": InventoryFactory.reservation_id(),
            "order_id": InventoryFactory.order_id(),
            "sku_id": InventoryFactory.sku_id(),
            "quantity": random.randint(1, 10),
            "status": status,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
            "created_at": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return InventoryReservation(**defaults)

    @staticmethod
    def inventory_item(**overrides) -> InventoryItem:
        on_hand = overrides.pop("on_hand", random.randint(10, 1000))
        reserved = overrides.pop("reserved", random.randint(0, on_hand // 2))
        defaults = {
            "sku_id": InventoryFactory.sku_id(),
            "on_hand": on_hand,
            "reserved": reserved,
            "available": on_hand - reserved,
            "updated_at": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return InventoryItem(**defaults)
