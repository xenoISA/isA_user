"""
Subscription Service Data Models

Defines data models for subscription management and credit allocation.
Reference: /docs/design/billing-credit-subscription-design.md
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


# ====================
# Enum Types
# ====================

class SubscriptionStatus(str, Enum):
    """Subscription status"""
    ACTIVE = "active"                    # Active subscription
    TRIALING = "trialing"               # In trial period
    PAST_DUE = "past_due"               # Payment overdue
    CANCELED = "canceled"               # Canceled (may still be active until period end)
    PAUSED = "paused"                   # Temporarily paused
    EXPIRED = "expired"                 # Subscription has ended
    INCOMPLETE = "incomplete"           # Payment not completed


class BillingCycle(str, Enum):
    """Billing cycle"""
    MONTHLY = "monthly"
    YEARLY = "yearly"
    QUARTERLY = "quarterly"


class SubscriptionAction(str, Enum):
    """Subscription history action types"""
    CREATED = "created"
    UPGRADED = "upgraded"
    DOWNGRADED = "downgraded"
    RENEWED = "renewed"
    CANCELED = "canceled"
    PAUSED = "paused"
    RESUMED = "resumed"
    EXPIRED = "expired"
    CREDITS_ALLOCATED = "credits_allocated"
    CREDITS_CONSUMED = "credits_consumed"
    CREDITS_REFUNDED = "credits_refunded"
    CREDITS_ROLLED_OVER = "credits_rolled_over"
    TRIAL_STARTED = "trial_started"
    TRIAL_ENDED = "trial_ended"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_SUCCEEDED = "payment_succeeded"


class InitiatedBy(str, Enum):
    """Who initiated the action"""
    USER = "user"
    SYSTEM = "system"
    ADMIN = "admin"
    PAYMENT_PROVIDER = "payment_provider"


# ====================
# Core Data Models
# ====================

class UserSubscription(BaseModel):
    """User subscription model"""
    id: Optional[int] = None
    subscription_id: str = Field(..., description="Unique subscription identifier")

    # Owner Information
    user_id: str = Field(..., description="User ID")
    organization_id: Optional[str] = None

    # Subscription Plan
    tier_id: str = Field(..., description="Reference to subscription tier")
    tier_code: str = Field(..., description="Tier code (free, pro, max, team, enterprise)")

    # Status
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE

    # Billing
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    price_paid: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = "USD"

    # Credits (1 Credit = $0.00001 USD)
    credits_allocated: int = Field(default=0, ge=0, description="Credits allocated for this period")
    credits_used: int = Field(default=0, ge=0, description="Credits used this period")
    credits_remaining: int = Field(default=0, ge=0, description="Remaining credits")
    credits_rolled_over: int = Field(default=0, ge=0, description="Credits from previous period")

    # Period
    current_period_start: datetime
    current_period_end: datetime

    # Trial
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    is_trial: bool = False

    # Seats (for team/enterprise)
    seats_purchased: int = Field(default=1, ge=1)
    seats_used: int = Field(default=1, ge=0)

    # Cancellation
    cancel_at_period_end: bool = False
    canceled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None

    # Payment
    payment_method_id: Optional[str] = None
    external_subscription_id: Optional[str] = None

    # Renewal
    auto_renew: bool = True
    next_billing_date: Optional[datetime] = None
    last_billing_date: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SubscriptionHistory(BaseModel):
    """Subscription history/audit model"""
    id: Optional[int] = None
    history_id: str = Field(..., description="Unique history entry identifier")

    # References
    subscription_id: str
    user_id: str
    organization_id: Optional[str] = None

    # Action
    action: SubscriptionAction

    # State Changes
    previous_tier_code: Optional[str] = None
    new_tier_code: Optional[str] = None
    previous_status: Optional[str] = None
    new_status: Optional[str] = None

    # Credit Changes
    credits_change: int = 0  # Positive for additions, negative for deductions
    credits_balance_after: Optional[int] = None

    # Price
    price_change: Decimal = Field(default=Decimal("0"))

    # Period
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    # Details
    reason: Optional[str] = None
    initiated_by: InitiatedBy = InitiatedBy.SYSTEM
    metadata: Dict[str, Any] = Field(default_factory=dict)

    created_at: Optional[datetime] = None


# ====================
# Request/Response Models
# ====================

class CreateSubscriptionRequest(BaseModel):
    """Request to create a new subscription"""
    user_id: str
    organization_id: Optional[str] = None
    tier_code: str = Field(..., description="Tier code: free, pro, max, team, enterprise")
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    payment_method_id: Optional[str] = None
    seats: int = Field(default=1, ge=1)
    use_trial: bool = False
    promo_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CreateSubscriptionResponse(BaseModel):
    """Response after creating a subscription"""
    success: bool
    message: str
    subscription: Optional[UserSubscription] = None
    credits_allocated: Optional[int] = None
    next_billing_date: Optional[datetime] = None


class UpdateSubscriptionRequest(BaseModel):
    """Request to update a subscription"""
    tier_code: Optional[str] = None
    billing_cycle: Optional[BillingCycle] = None
    seats: Optional[int] = Field(default=None, ge=1)
    auto_renew: Optional[bool] = None
    payment_method_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CancelSubscriptionRequest(BaseModel):
    """Request to cancel a subscription"""
    immediate: bool = False  # If True, cancel now; if False, cancel at period end
    reason: Optional[str] = None
    feedback: Optional[str] = None


class CancelSubscriptionResponse(BaseModel):
    """Response after canceling a subscription"""
    success: bool
    message: str
    canceled_at: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    credits_remaining: Optional[int] = None


class ConsumeCreditsRequest(BaseModel):
    """Request to consume credits from a subscription"""
    user_id: str
    organization_id: Optional[str] = None
    credits_to_consume: int = Field(..., gt=0)
    service_type: str  # model_inference, storage_minio, mcp_service, etc.
    usage_record_id: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ConsumeCreditsResponse(BaseModel):
    """Response after consuming credits"""
    success: bool
    message: str
    credits_consumed: int = 0
    credits_remaining: int = 0
    subscription_id: Optional[str] = None
    consumed_from: Optional[str] = None  # subscription, purchased, bonus


class CreditBalanceResponse(BaseModel):
    """Response with credit balance information"""
    success: bool
    message: str
    user_id: str
    organization_id: Optional[str] = None

    # Subscription Credits
    subscription_credits_remaining: int = 0
    subscription_credits_total: int = 0
    subscription_period_end: Optional[datetime] = None

    # Total Available
    total_credits_available: int = 0

    # Subscription Info
    subscription_id: Optional[str] = None
    tier_code: Optional[str] = None
    tier_name: Optional[str] = None


class SubscriptionResponse(BaseModel):
    """Standard subscription response"""
    success: bool
    message: str
    subscription: Optional[UserSubscription] = None


class SubscriptionListResponse(BaseModel):
    """List of subscriptions response"""
    success: bool
    message: str
    subscriptions: List[UserSubscription] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class SubscriptionHistoryResponse(BaseModel):
    """Subscription history response"""
    success: bool
    message: str
    history: List[SubscriptionHistory] = Field(default_factory=list)
    total: int = 0


class SubscriptionStatsResponse(BaseModel):
    """Subscription statistics response"""
    total_subscriptions: int
    active_subscriptions: int
    trialing_subscriptions: int
    canceled_subscriptions: int
    subscriptions_by_tier: Dict[str, int]
    monthly_recurring_revenue: Decimal
    annual_recurring_revenue: Decimal
    total_credits_allocated: int
    total_credits_consumed: int
    average_credit_usage_percentage: float


# ====================
# System Models
# ====================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    port: int
    version: str
    timestamp: str
    database_connected: bool = False


class SubscriptionServiceInfo(BaseModel):
    """Service information"""
    service: str
    version: str
    description: str
    capabilities: List[str]
    supported_tiers: List[str]
    supported_billing_cycles: List[str]


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
