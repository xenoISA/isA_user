"""
Fulfillment Service Data Contract

Defines canonical data structures for fulfillment service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for fulfillment service test data.
"""

import uuid
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================================
# Enums (matching production models)
# ============================================================================

class ShipmentStatus(str, Enum):
    """Shipment status values"""
    CREATED = "created"
    LABEL_PURCHASED = "label_purchased"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"


# ============================================================================
# Data Models (matching production Pydantic models)
# ============================================================================

class Parcel(BaseModel):
    """Parcel dimensions and weight"""
    weight_grams: int = Field(..., gt=0)
    dimensions_cm: Dict[str, Any]


class Shipment(BaseModel):
    """Fulfillment shipment"""
    shipment_id: str
    order_id: str
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    status: ShipmentStatus = ShipmentStatus.CREATED
    label_url: Optional[str] = None
    parcels: List[Parcel] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Factory Functions
# ============================================================================

class FulfillmentFactory:
    """Factory for generating test data"""

    @staticmethod
    def shipment_id() -> str:
        return f"shp_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def order_id() -> str:
        return f"ord_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def tracking_number() -> str:
        return f"trk_{uuid.uuid4().hex[:10]}"

    @staticmethod
    def shipping_address() -> Dict[str, Any]:
        return {
            "street": "123 Test Street",
            "city": "San Francisco",
            "state": "CA",
            "zip": "94102",
            "country": "US",
        }

    @staticmethod
    def items(count: int = 2) -> List[Dict[str, Any]]:
        return [
            {
                "sku_id": f"sku_{uuid.uuid4().hex[:8]}",
                "quantity": random.randint(1, 5),
                "name": f"Test Item {i + 1}",
                "weight_grams": random.randint(100, 5000),
            }
            for i in range(count)
        ]

    @staticmethod
    def create_shipment_request(
        order_id: Optional[str] = None,
        items: Optional[List[Dict]] = None,
        address: Optional[Dict] = None,
        user_id: str = "test_user",
    ) -> Dict[str, Any]:
        return {
            "order_id": order_id or FulfillmentFactory.order_id(),
            "items": items or FulfillmentFactory.items(),
            "address": address or FulfillmentFactory.shipping_address(),
            "user_id": user_id,
        }

    @staticmethod
    def shipment(
        status: ShipmentStatus = ShipmentStatus.CREATED,
        **overrides,
    ) -> Shipment:
        defaults = {
            "shipment_id": FulfillmentFactory.shipment_id(),
            "order_id": FulfillmentFactory.order_id(),
            "status": status,
            "created_at": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return Shipment(**defaults)

    @staticmethod
    def parcel(**overrides) -> Parcel:
        defaults = {
            "weight_grams": random.randint(100, 5000),
            "dimensions_cm": {"length": 30, "width": 20, "height": 10},
        }
        defaults.update(overrides)
        return Parcel(**defaults)
