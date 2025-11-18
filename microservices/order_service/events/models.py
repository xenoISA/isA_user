"""
Order Service Event Models

Pydantic models for events published by order service
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal


class OrderCreatedEvent(BaseModel):
    """Event published when order is created"""
    order_id: str
    user_id: str
    order_type: str
    total_amount: float
    currency: str = "USD"
    payment_intent_id: Optional[str] = None
    subscription_id: Optional[str] = None
    wallet_id: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OrderUpdatedEvent(BaseModel):
    """Event published when order is updated"""
    order_id: str
    user_id: str
    updated_fields: Dict[str, Any]
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OrderCanceledEvent(BaseModel):
    """Event published when order is canceled"""
    order_id: str
    user_id: str
    order_type: str
    total_amount: float
    currency: str = "USD"
    cancellation_reason: Optional[str] = None
    refund_amount: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OrderCompletedEvent(BaseModel):
    """Event published when order is completed"""
    order_id: str
    user_id: str
    order_type: str
    total_amount: float
    currency: str = "USD"
    payment_id: Optional[str] = None
    transaction_id: Optional[str] = None
    credits_added: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OrderExpiredEvent(BaseModel):
    """Event published when order expires (unpaid)"""
    order_id: str
    user_id: str
    order_type: str
    total_amount: float
    expired_at: datetime
    payment_intent_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OrderPaymentPendingEvent(BaseModel):
    """Event published when order is awaiting payment"""
    order_id: str
    user_id: str
    payment_intent_id: str
    total_amount: float
    currency: str = "USD"
    expires_at: Optional[datetime] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OrderRefundedEvent(BaseModel):
    """Event published when order is refunded"""
    order_id: str
    user_id: str
    refund_id: str
    refund_amount: float
    currency: str = "USD"
    refund_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OrderFulfilledEvent(BaseModel):
    """Event published when order items are delivered/fulfilled"""
    order_id: str
    user_id: str
    fulfillment_details: Optional[Dict[str, Any]] = None
    fulfilled_at: datetime = Field(default_factory=datetime.utcnow)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
