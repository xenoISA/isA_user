"""
Fulfillment Service Data Models

Handles shipping and tracking for physical goods.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ShipmentStatus(str, Enum):
    """Shipment status"""
    CREATED = "created"
    LABEL_PURCHASED = "label_purchased"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"


class Parcel(BaseModel):
    """Shipment parcel"""
    weight_grams: int = Field(..., gt=0)
    dimensions_cm: Dict[str, Any]


class Shipment(BaseModel):
    """Shipment record"""
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
