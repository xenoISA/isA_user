"""
Payment Service Event Models

Pydantic models for events published by payment service
"""

from pydantic import BaseModel, Field
from enum import Enum

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class PaymentEventType(str, Enum):
    """
    Events published by payment_service.

    Stream: payment-stream
    Subjects: payment.>
    """
    PAYMENT_INITIATED = "payment.initiated"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_REFUNDED = "payment.refunded"


class PaymentSubscribedEventType(str, Enum):
    """Events that payment_service subscribes to from other services."""
    ORDER_CREATED = "order.created"


class PaymentStreamConfig:
    """Stream configuration for payment_service"""
    STREAM_NAME = "payment-stream"
    SUBJECTS = ["payment.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "payment"

from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal


class PaymentCompletedEvent(BaseModel):
    """Event published when payment is successfully completed"""
    payment_intent_id: str
    payment_id: Optional[str] = None
    user_id: str
    amount: float
    currency: str = "USD"
    payment_method: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaymentFailedEvent(BaseModel):
    """Event published when payment fails"""
    payment_intent_id: str
    user_id: str
    amount: float
    currency: str = "USD"
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaymentRefundedEvent(BaseModel):
    """Event published when payment is refunded"""
    payment_id: str
    refund_id: str
    user_id: str
    amount: float
    currency: str = "USD"
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaymentIntentCreatedEvent(BaseModel):
    """Event published when payment intent is created"""
    payment_intent_id: str
    user_id: str
    amount: float
    currency: str = "USD"
    order_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SubscriptionCreatedEvent(BaseModel):
    """Event published when subscription is created"""
    subscription_id: str
    user_id: str
    plan_id: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    trial_end: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SubscriptionCanceledEvent(BaseModel):
    """Event published when subscription is canceled"""
    subscription_id: str
    user_id: str
    plan_id: Optional[str] = None
    canceled_at: datetime
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SubscriptionUpdatedEvent(BaseModel):
    """Event published when subscription is updated"""
    subscription_id: str
    user_id: str
    old_plan_id: Optional[str] = None
    new_plan_id: Optional[str] = None
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SubscriptionExpiredEvent(BaseModel):
    """Event published when subscription expires"""
    subscription_id: str
    user_id: str
    plan_id: str
    expired_at: datetime
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class InvoiceCreatedEvent(BaseModel):
    """Event published when invoice is created"""
    invoice_id: str
    user_id: str
    subscription_id: Optional[str] = None
    amount_due: float
    currency: str = "USD"
    due_date: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class InvoicePaidEvent(BaseModel):
    """Event published when invoice is paid"""
    invoice_id: str
    payment_id: str
    user_id: str
    amount_paid: float
    currency: str = "USD"
    paid_at: datetime
    timestamp: datetime = Field(default_factory=datetime.utcnow)
