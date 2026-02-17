"""
Fulfillment Service Event Models

Pydantic models for events published by fulfillment service
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime


# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class FulfillmentEventType(str, Enum):
    """
    Events published by fulfillment_service.

    Stream: fulfillment-stream
    Subjects: fulfillment.>
    """
    SHIPMENT_PREPARED = "fulfillment.shipment.prepared"
    LABEL_CREATED = "fulfillment.label.created"
    SHIPMENT_CANCELED = "fulfillment.shipment.canceled"
    SHIPMENT_FAILED = "fulfillment.shipment.failed"


class FulfillmentSubscribedEventType(str, Enum):
    """Events that fulfillment_service subscribes to from other services."""
    TAX_CALCULATED = "tax.calculated"
    PAYMENT_COMPLETED = "payment.completed"
    ORDER_CANCELED = "order.canceled"


class FulfillmentStreamConfig:
    """Stream configuration for fulfillment_service"""
    STREAM_NAME = "fulfillment-stream"
    SUBJECTS = ["fulfillment.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "fulfillment"


# =============================================================================
# Event Data Models
# =============================================================================

class ShipmentItem(BaseModel):
    """Item in a shipment"""
    sku_id: str
    quantity: int
    weight_grams: Optional[int] = None


class ShipmentPreparedEvent(BaseModel):
    """Event published when shipment is prepared and ready for label"""
    order_id: str
    shipment_id: str
    user_id: str
    items: List[ShipmentItem]
    shipping_address: Dict[str, Any]
    estimated_weight_grams: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LabelCreatedEvent(BaseModel):
    """Event published when shipping label is created (after payment)"""
    order_id: str
    shipment_id: str
    user_id: str
    carrier: str
    tracking_number: str
    label_url: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    shipping_cost: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ShipmentCanceledEvent(BaseModel):
    """Event published when shipment is canceled"""
    order_id: str
    shipment_id: str
    user_id: str
    reason: Optional[str] = None
    refund_shipping: bool = False
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ShipmentFailedEvent(BaseModel):
    """Event published when shipment creation fails"""
    order_id: str
    user_id: str
    error_code: Optional[str] = None
    error_message: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
