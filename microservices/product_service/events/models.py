"""
Product Service Event Models

Pydantic models for events published by product service
"""

from pydantic import BaseModel, Field
from enum import Enum

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class ProductEventType(str, Enum):
    """
    Events published by product_service.

    Stream: product-stream
    Subjects: product.>
    """
    PRODUCT_CREATED = "product.created"
    PRODUCT_UPDATED = "product.updated"
    PRODUCT_AVAILABILITY_CHANGED = "product.availability.changed"
    USAGE_RECORDED = "product.usage.recorded"


class ProductSubscribedEventType(str, Enum):
    """Events that product_service subscribes to from other services."""
    pass  # No subscribed events


class ProductStreamConfig:
    """Stream configuration for product_service"""
    STREAM_NAME = "product-stream"
    SUBJECTS = ["product.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "product"

from typing import Optional, Dict, Any
from datetime import datetime


class SubscriptionCreatedEvent(BaseModel):
    """Event published when a new subscription is created"""
    subscription_id: str
    user_id: str
    organization_id: Optional[str] = None
    plan_id: str
    plan_tier: str
    billing_cycle: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class SubscriptionStatusChangedEvent(BaseModel):
    """Event published when subscription status changes"""
    subscription_id: str
    user_id: str
    organization_id: Optional[str] = None
    plan_id: str
    old_status: str
    new_status: str
    reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class SubscriptionActivatedEvent(BaseModel):
    """Event published when subscription is activated"""
    subscription_id: str
    user_id: str
    organization_id: Optional[str] = None
    plan_id: str
    plan_tier: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SubscriptionCanceledEvent(BaseModel):
    """Event published when subscription is canceled"""
    subscription_id: str
    user_id: str
    organization_id: Optional[str] = None
    plan_id: str
    cancellation_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SubscriptionExpiredEvent(BaseModel):
    """Event published when subscription expires"""
    subscription_id: str
    user_id: str
    organization_id: Optional[str] = None
    plan_id: str
    expiration_date: datetime
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ProductUsageRecordedEvent(BaseModel):
    """Event published when product usage is recorded"""
    usage_record_id: str
    user_id: str
    organization_id: Optional[str] = None
    subscription_id: Optional[str] = None
    product_id: str
    usage_amount: float
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    usage_details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
