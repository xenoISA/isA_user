"""
Subscription Event Models

Defines event types and structures for subscription service events.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class SubscriptionEventType(str, Enum):
    """Subscription event types"""
    # Subscription Lifecycle
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    SUBSCRIPTION_CANCELED = "subscription.canceled"
    SUBSCRIPTION_PAUSED = "subscription.paused"
    SUBSCRIPTION_RESUMED = "subscription.resumed"
    SUBSCRIPTION_RENEWED = "subscription.renewed"
    SUBSCRIPTION_EXPIRED = "subscription.expired"

    # Tier Changes
    SUBSCRIPTION_UPGRADED = "subscription.upgraded"
    SUBSCRIPTION_DOWNGRADED = "subscription.downgraded"

    # Trial
    TRIAL_STARTED = "subscription.trial.started"
    TRIAL_ENDING_SOON = "subscription.trial.ending_soon"
    TRIAL_ENDED = "subscription.trial.ended"

    # Credits
    CREDITS_ALLOCATED = "subscription.credits.allocated"
    CREDITS_CONSUMED = "subscription.credits.consumed"
    CREDITS_LOW = "subscription.credits.low"
    CREDITS_DEPLETED = "subscription.credits.depleted"
    CREDITS_ROLLED_OVER = "subscription.credits.rolled_over"

    # Payment
    PAYMENT_SUCCEEDED = "subscription.payment.succeeded"
    PAYMENT_FAILED = "subscription.payment.failed"
    PAYMENT_REFUNDED = "subscription.payment.refunded"


class SubscriptionEvent(BaseModel):
    """Base subscription event model"""
    event_id: str = Field(..., description="Unique event identifier")
    event_type: SubscriptionEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())

    # Subscription Reference
    subscription_id: str
    user_id: str
    organization_id: Optional[str] = None

    # Event Data
    tier_code: Optional[str] = None
    previous_tier_code: Optional[str] = None
    credits_change: Optional[int] = None
    credits_remaining: Optional[int] = None
    amount: Optional[float] = None

    # Additional Data
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SubscriptionCreatedEvent(SubscriptionEvent):
    """Event when a new subscription is created"""
    event_type: SubscriptionEventType = SubscriptionEventType.SUBSCRIPTION_CREATED
    billing_cycle: str
    is_trial: bool = False
    trial_end: Optional[datetime] = None


class SubscriptionCanceledEvent(SubscriptionEvent):
    """Event when a subscription is canceled"""
    event_type: SubscriptionEventType = SubscriptionEventType.SUBSCRIPTION_CANCELED
    immediate: bool = False
    effective_date: datetime
    reason: Optional[str] = None


class CreditsConsumedEvent(SubscriptionEvent):
    """Event when credits are consumed"""
    event_type: SubscriptionEventType = SubscriptionEventType.CREDITS_CONSUMED
    service_type: str
    usage_record_id: Optional[str] = None
    credits_consumed: int
