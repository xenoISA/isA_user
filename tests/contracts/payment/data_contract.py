"""
Payment Service - Data Contract

Pydantic schemas, test data factory, and request builders for payment_service.
Zero hardcoded data - all test data generated through factory methods.

This module defines:
1. Request Contracts - Pydantic schemas for API requests
2. Response Contracts - Pydantic schemas for API responses
3. PaymentTestDataFactory - Test data generation (40+ methods)
4. Request Builders - Fluent API for building test requests
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
import secrets
import uuid


# ============================================================================
# Enumerations
# ============================================================================


class PaymentStatusEnum(str, Enum):
    """Valid payment status values"""
    PENDING = "pending"
    REQUIRES_ACTION = "requires_action"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    PARTIAL_REFUND = "partial_refund"


class PaymentMethodEnum(str, Enum):
    """Valid payment method values"""
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    WALLET = "wallet"
    STRIPE = "stripe"


class SubscriptionStatusEnum(str, Enum):
    """Valid subscription status values"""
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"


class SubscriptionTierEnum(str, Enum):
    """Valid subscription tier values"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class BillingCycleEnum(str, Enum):
    """Valid billing cycle values"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ONE_TIME = "one_time"


class InvoiceStatusEnum(str, Enum):
    """Valid invoice status values"""
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class RefundStatusEnum(str, Enum):
    """Valid refund status values"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class CurrencyEnum(str, Enum):
    """Valid currency values"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CNY = "CNY"


# ============================================================================
# Request Contracts (15 schemas)
# ============================================================================


class CreatePlanRequestContract(BaseModel):
    """Contract for subscription plan creation requests"""
    plan_id: str = Field(..., min_length=1, max_length=50, description="Plan ID")
    name: str = Field(..., min_length=1, max_length=100, description="Plan name")
    description: Optional[str] = Field(None, max_length=500, description="Plan description")
    tier: str = Field(..., description="Subscription tier")
    price: Decimal = Field(..., ge=0, description="Plan price")
    currency: str = Field(default="USD", description="Currency")
    billing_cycle: str = Field(..., description="Billing cycle")
    features: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Plan features")
    credits_included: int = Field(default=0, ge=0, description="Credits included")
    max_users: Optional[int] = Field(None, ge=1, description="Max users")
    max_storage_gb: Optional[int] = Field(None, ge=1, description="Max storage GB")
    trial_days: int = Field(default=0, ge=0, description="Trial days")
    is_active: bool = Field(default=True, description="Is active")
    is_public: bool = Field(default=True, description="Is public")

    @field_validator('tier')
    @classmethod
    def validate_tier(cls, v):
        if v not in [e.value for e in SubscriptionTierEnum]:
            raise ValueError(f"tier must be one of: {[e.value for e in SubscriptionTierEnum]}")
        return v

    @field_validator('billing_cycle')
    @classmethod
    def validate_billing_cycle(cls, v):
        if v not in [e.value for e in BillingCycleEnum]:
            raise ValueError(f"billing_cycle must be one of: {[e.value for e in BillingCycleEnum]}")
        return v


class CreateSubscriptionRequestContract(BaseModel):
    """Contract for subscription creation requests"""
    user_id: str = Field(..., min_length=1, max_length=50, description="User ID")
    plan_id: str = Field(..., min_length=1, max_length=50, description="Plan ID")
    organization_id: Optional[str] = Field(None, max_length=50, description="Organization ID")
    payment_method_id: Optional[str] = Field(None, max_length=100, description="Payment method ID")
    trial_days: Optional[int] = Field(None, ge=0, description="Override trial days")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()

    @field_validator('plan_id')
    @classmethod
    def validate_plan_id(cls, v):
        if not v or not v.strip():
            raise ValueError("plan_id cannot be empty")
        return v.strip()


class UpdateSubscriptionRequestContract(BaseModel):
    """Contract for subscription update requests"""
    plan_id: Optional[str] = Field(None, max_length=50, description="New plan ID")
    cancel_at_period_end: Optional[bool] = Field(None, description="Cancel at period end")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")


class CancelSubscriptionRequestContract(BaseModel):
    """Contract for subscription cancellation requests"""
    immediate: bool = Field(default=False, description="Cancel immediately")
    reason: Optional[str] = Field(None, max_length=500, description="Cancellation reason")


class CreatePaymentIntentRequestContract(BaseModel):
    """Contract for payment intent creation requests"""
    user_id: str = Field(..., min_length=1, max_length=50, description="User ID")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="USD", max_length=10, description="Currency")
    description: Optional[str] = Field(None, max_length=500, description="Payment description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v):
        if v not in [e.value for e in CurrencyEnum]:
            raise ValueError(f"currency must be one of: {[e.value for e in CurrencyEnum]}")
        return v


class ConfirmPaymentRequestContract(BaseModel):
    """Contract for payment confirmation requests"""
    processor_response: Optional[Dict[str, Any]] = Field(None, description="Processor response")


class FailPaymentRequestContract(BaseModel):
    """Contract for payment failure requests"""
    failure_reason: str = Field(..., min_length=1, max_length=500, description="Failure reason")
    failure_code: Optional[str] = Field(None, max_length=50, description="Failure code")


class CreateInvoiceRequestContract(BaseModel):
    """Contract for invoice creation requests"""
    user_id: str = Field(..., min_length=1, max_length=50, description="User ID")
    organization_id: Optional[str] = Field(None, max_length=50, description="Organization ID")
    subscription_id: Optional[str] = Field(None, max_length=50, description="Subscription ID")
    amount_due: Decimal = Field(..., gt=0, description="Amount due")
    currency: str = Field(default="USD", max_length=10, description="Currency")
    due_date: Optional[datetime] = Field(None, description="Due date")
    billing_period_start: Optional[datetime] = Field(None, description="Billing period start")
    billing_period_end: Optional[datetime] = Field(None, description="Billing period end")
    line_items: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Line items")


class PayInvoiceRequestContract(BaseModel):
    """Contract for invoice payment requests"""
    payment_method_id: str = Field(..., min_length=1, max_length=100, description="Payment method ID")


class CreateRefundRequestContract(BaseModel):
    """Contract for refund creation requests"""
    payment_id: str = Field(..., min_length=1, max_length=50, description="Payment ID")
    amount: Optional[Decimal] = Field(None, gt=0, description="Refund amount (defaults to full)")
    reason: Optional[str] = Field(None, max_length=500, description="Refund reason")
    requested_by: str = Field(..., min_length=1, max_length=50, description="Requester ID")

    @field_validator('payment_id')
    @classmethod
    def validate_payment_id(cls, v):
        if not v or not v.strip():
            raise ValueError("payment_id cannot be empty")
        return v.strip()


class ProcessRefundRequestContract(BaseModel):
    """Contract for refund processing requests"""
    approved_by: Optional[str] = Field(None, max_length=50, description="Approver ID")


class PaymentHistoryQueryRequestContract(BaseModel):
    """Contract for payment history query parameters"""
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    status: Optional[str] = Field(None, description="Filter by status")
    start_date: Optional[datetime] = Field(None, description="Filter start date")
    end_date: Optional[datetime] = Field(None, description="Filter end date")
    limit: int = Field(default=100, ge=1, le=500, description="Max results")


class SubscriptionPlansQueryRequestContract(BaseModel):
    """Contract for subscription plans query parameters"""
    tier: Optional[str] = Field(None, description="Filter by tier")
    is_public: bool = Field(default=True, description="Filter by visibility")


class RevenueStatsQueryRequestContract(BaseModel):
    """Contract for revenue statistics query parameters"""
    start_date: Optional[datetime] = Field(None, description="Filter start date")
    end_date: Optional[datetime] = Field(None, description="Filter end date")
    days: int = Field(default=30, ge=1, le=365, description="Days to analyze")


class HealthCheckRequestContract(BaseModel):
    """Contract for health check requests (no body)"""
    pass


# ============================================================================
# Response Contracts (18 schemas)
# ============================================================================


class SubscriptionPlanResponseContract(BaseModel):
    """Contract for subscription plan response"""
    plan_id: str = Field(..., description="Plan ID")
    name: str = Field(..., description="Plan name")
    description: Optional[str] = Field(None, description="Plan description")
    tier: str = Field(..., description="Subscription tier")
    price: Decimal = Field(..., ge=0, description="Plan price")
    currency: str = Field(..., description="Currency")
    billing_cycle: str = Field(..., description="Billing cycle")
    features: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Plan features")
    credits_included: int = Field(default=0, description="Credits included")
    max_users: Optional[int] = Field(None, description="Max users")
    max_storage_gb: Optional[int] = Field(None, description="Max storage GB")
    trial_days: int = Field(default=0, description="Trial days")
    stripe_product_id: Optional[str] = Field(None, description="Stripe product ID")
    stripe_price_id: Optional[str] = Field(None, description="Stripe price ID")
    is_active: bool = Field(..., description="Is active")
    is_public: bool = Field(..., description="Is public")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")

    class Config:
        from_attributes = True


class SubscriptionResponseContract(BaseModel):
    """Contract for subscription response"""
    subscription_id: str = Field(..., description="Subscription ID")
    user_id: str = Field(..., description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    plan_id: str = Field(..., description="Plan ID")
    status: str = Field(..., description="Subscription status")
    tier: str = Field(..., description="Subscription tier")
    current_period_start: datetime = Field(..., description="Current period start")
    current_period_end: datetime = Field(..., description="Current period end")
    billing_cycle: str = Field(..., description="Billing cycle")
    trial_start: Optional[datetime] = Field(None, description="Trial start")
    trial_end: Optional[datetime] = Field(None, description="Trial end")
    cancel_at_period_end: bool = Field(default=False, description="Cancel at period end")
    canceled_at: Optional[datetime] = Field(None, description="Cancellation timestamp")
    cancellation_reason: Optional[str] = Field(None, description="Cancellation reason")
    stripe_subscription_id: Optional[str] = Field(None, description="Stripe subscription ID")
    stripe_customer_id: Optional[str] = Field(None, description="Stripe customer ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")

    class Config:
        from_attributes = True


class SubscriptionWithPlanResponseContract(BaseModel):
    """Contract for subscription with plan response"""
    subscription: SubscriptionResponseContract = Field(..., description="Subscription")
    plan: Optional[SubscriptionPlanResponseContract] = Field(None, description="Plan")


class PaymentResponseContract(BaseModel):
    """Contract for payment response"""
    payment_id: str = Field(..., description="Payment ID")
    user_id: str = Field(..., description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    amount: Decimal = Field(..., ge=0, description="Payment amount")
    currency: str = Field(..., description="Currency")
    description: Optional[str] = Field(None, description="Payment description")
    status: str = Field(..., description="Payment status")
    payment_method: str = Field(..., description="Payment method")
    subscription_id: Optional[str] = Field(None, description="Subscription ID")
    invoice_id: Optional[str] = Field(None, description="Invoice ID")
    processor: str = Field(default="stripe", description="Payment processor")
    processor_payment_id: Optional[str] = Field(None, description="Processor payment ID")
    processor_response: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Processor response")
    failure_reason: Optional[str] = Field(None, description="Failure reason")
    failure_code: Optional[str] = Field(None, description="Failure code")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    paid_at: Optional[datetime] = Field(None, description="Payment timestamp")
    failed_at: Optional[datetime] = Field(None, description="Failure timestamp")

    class Config:
        from_attributes = True


class PaymentIntentResponseContract(BaseModel):
    """Contract for payment intent response"""
    payment_intent_id: str = Field(..., description="Payment intent ID")
    client_secret: Optional[str] = Field(None, description="Client secret for Stripe.js")
    amount: Decimal = Field(..., ge=0, description="Payment amount")
    currency: str = Field(..., description="Currency")
    status: str = Field(..., description="Payment status")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata")


class PaymentHistoryResponseContract(BaseModel):
    """Contract for payment history response"""
    payments: List[PaymentResponseContract] = Field(..., description="Payments list")
    total_count: int = Field(..., ge=0, description="Total count")
    total_amount: Decimal = Field(..., ge=0, description="Total amount")
    filters_applied: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Filters applied")


class InvoiceResponseContract(BaseModel):
    """Contract for invoice response"""
    invoice_id: str = Field(..., description="Invoice ID")
    invoice_number: str = Field(..., description="Invoice number")
    user_id: str = Field(..., description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    subscription_id: Optional[str] = Field(None, description="Subscription ID")
    status: str = Field(..., description="Invoice status")
    amount_total: Decimal = Field(..., ge=0, description="Total amount")
    amount_paid: Decimal = Field(default=Decimal("0"), ge=0, description="Amount paid")
    amount_due: Decimal = Field(..., ge=0, description="Amount due")
    currency: str = Field(..., description="Currency")
    billing_period_start: datetime = Field(..., description="Billing period start")
    billing_period_end: datetime = Field(..., description="Billing period end")
    payment_intent_id: Optional[str] = Field(None, description="Payment intent ID")
    line_items: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Line items")
    stripe_invoice_id: Optional[str] = Field(None, description="Stripe invoice ID")
    due_date: Optional[datetime] = Field(None, description="Due date")
    paid_at: Optional[datetime] = Field(None, description="Payment timestamp")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")

    class Config:
        from_attributes = True


class InvoiceWithPaymentResponseContract(BaseModel):
    """Contract for invoice with payment response"""
    invoice: InvoiceResponseContract = Field(..., description="Invoice")
    payment: Optional[PaymentResponseContract] = Field(None, description="Payment")


class RefundResponseContract(BaseModel):
    """Contract for refund response"""
    refund_id: str = Field(..., description="Refund ID")
    payment_id: str = Field(..., description="Payment ID")
    user_id: str = Field(..., description="User ID")
    amount: Decimal = Field(..., ge=0, description="Refund amount")
    currency: str = Field(..., description="Currency")
    reason: Optional[str] = Field(None, description="Refund reason")
    status: str = Field(..., description="Refund status")
    processor: str = Field(default="stripe", description="Processor")
    processor_refund_id: Optional[str] = Field(None, description="Processor refund ID")
    processor_response: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Processor response")
    requested_by: Optional[str] = Field(None, description="Requester ID")
    approved_by: Optional[str] = Field(None, description="Approver ID")
    requested_at: Optional[datetime] = Field(None, description="Request timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    class Config:
        from_attributes = True


class RevenueStatsResponseContract(BaseModel):
    """Contract for revenue statistics response"""
    total_revenue: Decimal = Field(..., ge=0, description="Total revenue")
    payment_count: int = Field(..., ge=0, description="Payment count")
    average_payment: Decimal = Field(..., ge=0, description="Average payment")
    daily_revenue: Optional[Dict[str, Decimal]] = Field(default_factory=dict, description="Daily revenue")
    period_days: int = Field(..., ge=1, description="Period days")


class SubscriptionStatsResponseContract(BaseModel):
    """Contract for subscription statistics response"""
    active_subscriptions: int = Field(..., ge=0, description="Active subscriptions")
    tier_distribution: Dict[str, int] = Field(..., description="Tier distribution")
    churn_rate: Decimal = Field(..., ge=0, description="Churn rate")
    canceled_last_30_days: int = Field(..., ge=0, description="Canceled in last 30 days")


class HealthCheckResponseContract(BaseModel):
    """Contract for health check response"""
    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    port: int = Field(..., description="Service port")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="Timestamp ISO format")


class DetailedHealthCheckResponseContract(BaseModel):
    """Contract for detailed health check response"""
    service: str = Field(default="payment_service")
    status: str = Field(default="operational")
    port: int = Field(default=8207)
    version: str = Field(default="1.0.0")
    stripe_test_mode: Optional[bool] = Field(None, description="Stripe test mode")
    database_connected: bool = Field(..., description="Database connected")
    account_client_available: bool = Field(..., description="Account client available")
    wallet_client_available: bool = Field(..., description="Wallet client available")
    timestamp: Optional[datetime] = Field(None, description="Timestamp")


class ErrorResponseContract(BaseModel):
    """Contract for error responses"""
    error: Optional[str] = Field(None, description="Error type")
    detail: str = Field(..., description="Error detail")
    timestamp: Optional[datetime] = Field(None, description="Error timestamp")


class SuccessResponseContract(BaseModel):
    """Contract for success message responses"""
    message: str = Field(..., description="Success message")


class WebhookResponseContract(BaseModel):
    """Contract for webhook response"""
    success: bool = Field(..., description="Success status")
    event: str = Field(..., description="Event type processed")


# ============================================================================
# PaymentTestDataFactory - 40+ methods (25+ valid + 15+ invalid)
# ============================================================================


class PaymentTestDataFactory:
    """
    Test data factory for payment_service - zero hardcoded data.

    All methods generate unique, valid test data suitable for testing.
    Factory methods are prefixed with make_ for valid data and
    make_invalid_ for invalid data scenarios.
    """

    # ========================================================================
    # Valid Data Generators (25+ methods)
    # ========================================================================

    @staticmethod
    def make_payment_id() -> str:
        """Generate valid payment ID"""
        return f"pi_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_subscription_id() -> str:
        """Generate valid subscription ID"""
        return f"sub_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_plan_id() -> str:
        """Generate valid plan ID"""
        return f"plan_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_invoice_id() -> str:
        """Generate valid invoice ID"""
        return f"inv_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_refund_id() -> str:
        """Generate valid refund ID"""
        return f"re_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate valid user ID"""
        return f"user_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_organization_id() -> str:
        """Generate valid organization ID"""
        return f"org_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_payment_method_id() -> str:
        """Generate valid payment method ID"""
        return f"pm_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_stripe_customer_id() -> str:
        """Generate valid Stripe customer ID"""
        return f"cus_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_stripe_subscription_id() -> str:
        """Generate valid Stripe subscription ID"""
        return f"sub_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_stripe_product_id() -> str:
        """Generate valid Stripe product ID"""
        return f"prod_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_stripe_price_id() -> str:
        """Generate valid Stripe price ID"""
        return f"price_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_stripe_refund_id() -> str:
        """Generate valid Stripe refund ID"""
        return f"re_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_client_secret() -> str:
        """Generate valid client secret"""
        return f"pi_{uuid.uuid4().hex[:24]}_secret_{secrets.token_hex(24)}"

    @staticmethod
    def make_invoice_number() -> str:
        """Generate valid invoice number"""
        return f"INV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_past_timestamp(days_ago: int = 1) -> datetime:
        """Generate timestamp in the past"""
        return datetime.now(timezone.utc) - timedelta(days=days_ago)

    @staticmethod
    def make_future_timestamp(days_ahead: int = 30) -> datetime:
        """Generate timestamp in the future"""
        return datetime.now(timezone.utc) + timedelta(days=days_ahead)

    @staticmethod
    def make_subscription_tier() -> str:
        """Generate valid subscription tier"""
        return secrets.choice([e.value for e in SubscriptionTierEnum])

    @staticmethod
    def make_billing_cycle() -> str:
        """Generate valid billing cycle"""
        return secrets.choice([BillingCycleEnum.MONTHLY.value, BillingCycleEnum.YEARLY.value])

    @staticmethod
    def make_payment_status() -> str:
        """Generate valid payment status"""
        return PaymentStatusEnum.PENDING.value

    @staticmethod
    def make_subscription_status() -> str:
        """Generate valid subscription status"""
        return SubscriptionStatusEnum.ACTIVE.value

    @staticmethod
    def make_invoice_status() -> str:
        """Generate valid invoice status"""
        return InvoiceStatusEnum.OPEN.value

    @staticmethod
    def make_refund_status() -> str:
        """Generate valid refund status"""
        return RefundStatusEnum.PENDING.value

    @staticmethod
    def make_currency() -> str:
        """Generate valid currency"""
        return CurrencyEnum.USD.value

    @staticmethod
    def make_payment_method() -> str:
        """Generate valid payment method"""
        return PaymentMethodEnum.CREDIT_CARD.value

    @staticmethod
    def make_amount() -> Decimal:
        """Generate valid payment amount"""
        return Decimal(str(round(secrets.randbelow(10000) / 100 + 9.99, 2)))  # 9.99 - 109.99

    @staticmethod
    def make_plan_price() -> Decimal:
        """Generate valid plan price"""
        return Decimal(str(secrets.choice([9.99, 19.99, 29.99, 49.99, 99.99, 199.99])))

    @staticmethod
    def make_refund_amount(payment_amount: Optional[Decimal] = None) -> Decimal:
        """Generate valid refund amount"""
        if payment_amount:
            return payment_amount
        return Decimal(str(round(secrets.randbelow(5000) / 100 + 1.00, 2)))  # 1.00 - 51.00

    @staticmethod
    def make_plan_name() -> str:
        """Generate valid plan name"""
        tier = secrets.choice(["Basic", "Pro", "Enterprise", "Premium"])
        cycle = secrets.choice(["Monthly", "Yearly", "Quarterly"])
        return f"{tier} {cycle}"

    @staticmethod
    def make_plan_features() -> Dict[str, Any]:
        """Generate valid plan features"""
        return {
            "api_calls": secrets.randbelow(100000) + 1000,
            "storage_gb": secrets.randbelow(100) + 10,
            "team_members": secrets.randbelow(50) + 1,
            "support_level": secrets.choice(["email", "chat", "phone", "dedicated"]),
        }

    @staticmethod
    def make_line_items() -> List[Dict[str, Any]]:
        """Generate valid invoice line items"""
        return [
            {
                "description": f"Subscription - {PaymentTestDataFactory.make_plan_name()}",
                "amount": float(PaymentTestDataFactory.make_plan_price()),
                "quantity": 1,
            }
        ]

    @staticmethod
    def make_metadata() -> Dict[str, Any]:
        """Generate valid metadata"""
        return {
            "source": secrets.choice(["web", "mobile", "api"]),
            "version": f"1.{secrets.randbelow(10)}.{secrets.randbelow(10)}",
        }

    @staticmethod
    def make_create_plan_request(**overrides) -> CreatePlanRequestContract:
        """Generate valid create plan request"""
        tier = PaymentTestDataFactory.make_subscription_tier()
        defaults = {
            "plan_id": PaymentTestDataFactory.make_plan_id(),
            "name": PaymentTestDataFactory.make_plan_name(),
            "description": f"Description for {tier} plan",
            "tier": tier,
            "price": PaymentTestDataFactory.make_plan_price(),
            "currency": CurrencyEnum.USD.value,
            "billing_cycle": BillingCycleEnum.MONTHLY.value,
            "features": PaymentTestDataFactory.make_plan_features(),
            "credits_included": secrets.randbelow(1000),
            "max_users": secrets.randbelow(50) + 1,
            "max_storage_gb": secrets.randbelow(100) + 10,
            "trial_days": 14,
            "is_active": True,
            "is_public": True,
        }
        defaults.update(overrides)
        return CreatePlanRequestContract(**defaults)

    @staticmethod
    def make_create_subscription_request(**overrides) -> CreateSubscriptionRequestContract:
        """Generate valid create subscription request"""
        defaults = {
            "user_id": PaymentTestDataFactory.make_user_id(),
            "plan_id": PaymentTestDataFactory.make_plan_id(),
            "organization_id": None,
            "payment_method_id": PaymentTestDataFactory.make_payment_method_id(),
            "trial_days": None,
            "metadata": PaymentTestDataFactory.make_metadata(),
        }
        defaults.update(overrides)
        return CreateSubscriptionRequestContract(**defaults)

    @staticmethod
    def make_create_payment_intent_request(**overrides) -> CreatePaymentIntentRequestContract:
        """Generate valid create payment intent request"""
        defaults = {
            "user_id": PaymentTestDataFactory.make_user_id(),
            "amount": PaymentTestDataFactory.make_amount(),
            "currency": CurrencyEnum.USD.value,
            "description": "Payment for services",
            "metadata": PaymentTestDataFactory.make_metadata(),
        }
        defaults.update(overrides)
        return CreatePaymentIntentRequestContract(**defaults)

    @staticmethod
    def make_create_refund_request(**overrides) -> CreateRefundRequestContract:
        """Generate valid create refund request"""
        defaults = {
            "payment_id": PaymentTestDataFactory.make_payment_id(),
            "amount": None,  # Full refund by default
            "reason": "Customer request",
            "requested_by": PaymentTestDataFactory.make_user_id(),
        }
        defaults.update(overrides)
        return CreateRefundRequestContract(**defaults)

    @staticmethod
    def make_subscription_plan_response(**overrides) -> SubscriptionPlanResponseContract:
        """Generate valid subscription plan response"""
        now = PaymentTestDataFactory.make_timestamp()
        tier = PaymentTestDataFactory.make_subscription_tier()
        defaults = {
            "plan_id": PaymentTestDataFactory.make_plan_id(),
            "name": PaymentTestDataFactory.make_plan_name(),
            "description": f"Description for {tier} plan",
            "tier": tier,
            "price": PaymentTestDataFactory.make_plan_price(),
            "currency": CurrencyEnum.USD.value,
            "billing_cycle": BillingCycleEnum.MONTHLY.value,
            "features": PaymentTestDataFactory.make_plan_features(),
            "credits_included": secrets.randbelow(1000),
            "max_users": secrets.randbelow(50) + 1,
            "max_storage_gb": secrets.randbelow(100) + 10,
            "trial_days": 14,
            "stripe_product_id": PaymentTestDataFactory.make_stripe_product_id(),
            "stripe_price_id": PaymentTestDataFactory.make_stripe_price_id(),
            "is_active": True,
            "is_public": True,
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return SubscriptionPlanResponseContract(**defaults)

    @staticmethod
    def make_subscription_response(**overrides) -> SubscriptionResponseContract:
        """Generate valid subscription response"""
        now = PaymentTestDataFactory.make_timestamp()
        period_end = PaymentTestDataFactory.make_future_timestamp(days_ahead=30)
        defaults = {
            "subscription_id": PaymentTestDataFactory.make_subscription_id(),
            "user_id": PaymentTestDataFactory.make_user_id(),
            "organization_id": None,
            "plan_id": PaymentTestDataFactory.make_plan_id(),
            "status": SubscriptionStatusEnum.ACTIVE.value,
            "tier": PaymentTestDataFactory.make_subscription_tier(),
            "current_period_start": now,
            "current_period_end": period_end,
            "billing_cycle": BillingCycleEnum.MONTHLY.value,
            "trial_start": None,
            "trial_end": None,
            "cancel_at_period_end": False,
            "canceled_at": None,
            "cancellation_reason": None,
            "stripe_subscription_id": PaymentTestDataFactory.make_stripe_subscription_id(),
            "stripe_customer_id": PaymentTestDataFactory.make_stripe_customer_id(),
            "metadata": {},
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return SubscriptionResponseContract(**defaults)

    @staticmethod
    def make_payment_response(**overrides) -> PaymentResponseContract:
        """Generate valid payment response"""
        now = PaymentTestDataFactory.make_timestamp()
        defaults = {
            "payment_id": PaymentTestDataFactory.make_payment_id(),
            "user_id": PaymentTestDataFactory.make_user_id(),
            "organization_id": None,
            "amount": PaymentTestDataFactory.make_amount(),
            "currency": CurrencyEnum.USD.value,
            "description": "Payment for services",
            "status": PaymentStatusEnum.SUCCEEDED.value,
            "payment_method": PaymentMethodEnum.CREDIT_CARD.value,
            "subscription_id": None,
            "invoice_id": None,
            "processor": "stripe",
            "processor_payment_id": PaymentTestDataFactory.make_payment_id(),
            "processor_response": {},
            "failure_reason": None,
            "failure_code": None,
            "created_at": now,
            "paid_at": now,
            "failed_at": None,
        }
        defaults.update(overrides)
        return PaymentResponseContract(**defaults)

    @staticmethod
    def make_payment_intent_response(**overrides) -> PaymentIntentResponseContract:
        """Generate valid payment intent response"""
        defaults = {
            "payment_intent_id": PaymentTestDataFactory.make_payment_id(),
            "client_secret": PaymentTestDataFactory.make_client_secret(),
            "amount": PaymentTestDataFactory.make_amount(),
            "currency": CurrencyEnum.USD.value,
            "status": PaymentStatusEnum.PENDING.value,
            "metadata": {},
        }
        defaults.update(overrides)
        return PaymentIntentResponseContract(**defaults)

    @staticmethod
    def make_invoice_response(**overrides) -> InvoiceResponseContract:
        """Generate valid invoice response"""
        now = PaymentTestDataFactory.make_timestamp()
        period_end = PaymentTestDataFactory.make_future_timestamp(days_ahead=30)
        amount = PaymentTestDataFactory.make_plan_price()
        defaults = {
            "invoice_id": PaymentTestDataFactory.make_invoice_id(),
            "invoice_number": PaymentTestDataFactory.make_invoice_number(),
            "user_id": PaymentTestDataFactory.make_user_id(),
            "organization_id": None,
            "subscription_id": PaymentTestDataFactory.make_subscription_id(),
            "status": InvoiceStatusEnum.OPEN.value,
            "amount_total": amount,
            "amount_paid": Decimal("0"),
            "amount_due": amount,
            "currency": CurrencyEnum.USD.value,
            "billing_period_start": now,
            "billing_period_end": period_end,
            "payment_intent_id": None,
            "line_items": PaymentTestDataFactory.make_line_items(),
            "stripe_invoice_id": None,
            "due_date": PaymentTestDataFactory.make_future_timestamp(days_ahead=7),
            "paid_at": None,
            "created_at": now,
        }
        defaults.update(overrides)
        return InvoiceResponseContract(**defaults)

    @staticmethod
    def make_refund_response(**overrides) -> RefundResponseContract:
        """Generate valid refund response"""
        now = PaymentTestDataFactory.make_timestamp()
        defaults = {
            "refund_id": PaymentTestDataFactory.make_refund_id(),
            "payment_id": PaymentTestDataFactory.make_payment_id(),
            "user_id": PaymentTestDataFactory.make_user_id(),
            "amount": PaymentTestDataFactory.make_refund_amount(),
            "currency": CurrencyEnum.USD.value,
            "reason": "Customer request",
            "status": RefundStatusEnum.SUCCEEDED.value,
            "processor": "stripe",
            "processor_refund_id": PaymentTestDataFactory.make_stripe_refund_id(),
            "processor_response": {},
            "requested_by": PaymentTestDataFactory.make_user_id(),
            "approved_by": None,
            "requested_at": now,
            "processed_at": now,
            "completed_at": now,
        }
        defaults.update(overrides)
        return RefundResponseContract(**defaults)

    # ========================================================================
    # Invalid Data Generators (15+ methods)
    # ========================================================================

    @staticmethod
    def make_invalid_user_id_empty() -> str:
        """Generate invalid user ID (empty string)"""
        return ""

    @staticmethod
    def make_invalid_user_id_whitespace() -> str:
        """Generate invalid user ID (whitespace only)"""
        return "   "

    @staticmethod
    def make_invalid_user_id_too_long() -> str:
        """Generate invalid user ID (too long)"""
        return "user_" + "x" * 100

    @staticmethod
    def make_invalid_plan_id_empty() -> str:
        """Generate invalid plan ID (empty string)"""
        return ""

    @staticmethod
    def make_invalid_payment_id_empty() -> str:
        """Generate invalid payment ID (empty string)"""
        return ""

    @staticmethod
    def make_invalid_subscription_tier() -> str:
        """Generate invalid subscription tier"""
        return "invalid_tier"

    @staticmethod
    def make_invalid_billing_cycle() -> str:
        """Generate invalid billing cycle"""
        return "invalid_cycle"

    @staticmethod
    def make_invalid_payment_status() -> str:
        """Generate invalid payment status"""
        return "invalid_status"

    @staticmethod
    def make_invalid_currency() -> str:
        """Generate invalid currency"""
        return "INVALID"

    @staticmethod
    def make_invalid_amount_negative() -> Decimal:
        """Generate invalid amount (negative)"""
        return Decimal("-29.99")

    @staticmethod
    def make_invalid_amount_zero() -> Decimal:
        """Generate invalid amount (zero)"""
        return Decimal("0")

    @staticmethod
    def make_invalid_price_negative() -> Decimal:
        """Generate invalid price (negative)"""
        return Decimal("-9.99")

    @staticmethod
    def make_invalid_limit_zero() -> int:
        """Generate invalid limit (zero)"""
        return 0

    @staticmethod
    def make_invalid_limit_too_large() -> int:
        """Generate invalid limit (too large)"""
        return 1000

    @staticmethod
    def make_nonexistent_payment_id() -> str:
        """Generate a payment ID that doesn't exist"""
        return f"pi_nonexistent_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_nonexistent_user_id() -> str:
        """Generate a user ID that doesn't exist"""
        return f"user_nonexistent_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_nonexistent_subscription_id() -> str:
        """Generate a subscription ID that doesn't exist"""
        return f"sub_nonexistent_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_nonexistent_plan_id() -> str:
        """Generate a plan ID that doesn't exist"""
        return f"plan_nonexistent_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_nonexistent_invoice_id() -> str:
        """Generate an invoice ID that doesn't exist"""
        return f"inv_nonexistent_{uuid.uuid4().hex[:8]}"

    # ================================================================
    # Convenience Methods (return dicts for easy test use)
    # ================================================================

    @staticmethod
    def make_valid_create_plan_request() -> Dict[str, Any]:
        """Generate a valid create plan request as dict"""
        return {
            "plan_id": PaymentTestDataFactory.make_plan_id(),
            "name": PaymentTestDataFactory.make_plan_name(),
            "tier": SubscriptionTierEnum.PRO.value,
            "price": float(PaymentTestDataFactory.make_plan_price()),
            "billing_cycle": BillingCycleEnum.MONTHLY.value,
            "features": PaymentTestDataFactory.make_plan_features(),
            "trial_days": 14,
        }

    @staticmethod
    def make_valid_enterprise_plan() -> Dict[str, Any]:
        """Generate a valid enterprise plan request as dict"""
        return {
            "plan_id": f"plan_enterprise_{uuid.uuid4().hex[:8]}",
            "name": "Enterprise Plan",
            "tier": SubscriptionTierEnum.ENTERPRISE.value,
            "price": 99.99,
            "billing_cycle": BillingCycleEnum.MONTHLY.value,
            "features": {"api_calls": 100000, "storage_gb": 1000, "priority_support": True},
            "trial_days": 30,
        }

    @staticmethod
    def make_valid_create_subscription_request() -> Dict[str, Any]:
        """Generate a valid create subscription request as dict"""
        return {
            "user_id": PaymentTestDataFactory.make_user_id(),
            "plan_id": PaymentTestDataFactory.make_plan_id(),
            "trial_days": 14,
            "metadata": {"source": "api_test"},
        }

    @staticmethod
    def make_valid_create_payment_intent_request() -> Dict[str, Any]:
        """Generate a valid create payment intent request as dict"""
        return {
            "user_id": PaymentTestDataFactory.make_user_id(),
            "amount": float(PaymentTestDataFactory.make_amount()),
            "currency": CurrencyEnum.USD.value,
            "description": "Test payment",
            "metadata": {"source": "api_test"},
        }

    @staticmethod
    def make_valid_create_refund_request() -> Dict[str, Any]:
        """Generate a valid create refund request as dict"""
        return {
            "payment_id": PaymentTestDataFactory.make_payment_id(),
            "amount": float(PaymentTestDataFactory.make_amount()),
            "reason": "Customer request",
            "requested_by": PaymentTestDataFactory.make_user_id(),
        }

    @staticmethod
    def make_valid_create_invoice_request() -> Dict[str, Any]:
        """Generate a valid create invoice request as dict"""
        return {
            "user_id": PaymentTestDataFactory.make_user_id(),
            "subscription_id": PaymentTestDataFactory.make_subscription_id(),
            "amount_due": float(PaymentTestDataFactory.make_amount()),
            "due_date": PaymentTestDataFactory.make_future_timestamp(14).isoformat(),
            "line_items": PaymentTestDataFactory.make_line_items(),
        }

    # ================================================================
    # Invalid Data Factory Methods (for validation testing)
    # ================================================================

    @staticmethod
    def make_invalid_empty_plan_name() -> Dict[str, Any]:
        """Generate plan request with empty name"""
        return {
            "plan_id": PaymentTestDataFactory.make_plan_id(),
            "name": "",
            "tier": SubscriptionTierEnum.BASIC.value,
            "price": 9.99,
            "billing_cycle": BillingCycleEnum.MONTHLY.value,
        }

    @staticmethod
    def make_invalid_negative_price() -> Dict[str, Any]:
        """Generate plan request with negative price"""
        return {
            "plan_id": PaymentTestDataFactory.make_plan_id(),
            "name": "Invalid Plan",
            "tier": SubscriptionTierEnum.BASIC.value,
            "price": -10.00,
            "billing_cycle": BillingCycleEnum.MONTHLY.value,
        }

    @staticmethod
    def make_invalid_empty_user_id_subscription() -> Dict[str, Any]:
        """Generate subscription request with empty user_id"""
        return {
            "user_id": "",
            "plan_id": PaymentTestDataFactory.make_plan_id(),
        }

    @staticmethod
    def make_invalid_empty_plan_id_subscription() -> Dict[str, Any]:
        """Generate subscription request with empty plan_id"""
        return {
            "user_id": PaymentTestDataFactory.make_user_id(),
            "plan_id": "",
        }

    @staticmethod
    def make_invalid_zero_amount() -> Dict[str, Any]:
        """Generate payment intent with zero amount"""
        return {
            "user_id": PaymentTestDataFactory.make_user_id(),
            "amount": 0,
            "currency": CurrencyEnum.USD.value,
        }

    @staticmethod
    def make_invalid_negative_amount() -> Dict[str, Any]:
        """Generate payment intent with negative amount"""
        return {
            "user_id": PaymentTestDataFactory.make_user_id(),
            "amount": -50.00,
            "currency": CurrencyEnum.USD.value,
        }

    @staticmethod
    def make_invalid_currency() -> Dict[str, Any]:
        """Generate payment intent with invalid currency"""
        return {
            "user_id": PaymentTestDataFactory.make_user_id(),
            "amount": 29.99,
            "currency": "INVALID",
        }

    @staticmethod
    def make_invalid_refund_exceeds_payment() -> Dict[str, Any]:
        """Generate refund request that exceeds payment amount"""
        return {
            "payment_id": PaymentTestDataFactory.make_payment_id(),
            "amount": 999999.99,  # Exceeds any reasonable payment
            "reason": "Over refund",
            "requested_by": PaymentTestDataFactory.make_user_id(),
        }


# ============================================================================
# Request Builders (6 builders)
# ============================================================================


class CreatePlanRequestBuilder:
    """Builder for create plan requests with fluent API"""

    def __init__(self):
        self._plan_id = PaymentTestDataFactory.make_plan_id()
        self._name = PaymentTestDataFactory.make_plan_name()
        self._description = None
        self._tier = SubscriptionTierEnum.BASIC.value
        self._price = Decimal("9.99")
        self._currency = CurrencyEnum.USD.value
        self._billing_cycle = BillingCycleEnum.MONTHLY.value
        self._features = {}
        self._credits_included = 0
        self._max_users = None
        self._max_storage_gb = None
        self._trial_days = 0
        self._is_active = True
        self._is_public = True

    def with_plan_id(self, value: str) -> 'CreatePlanRequestBuilder':
        self._plan_id = value
        return self

    def with_name(self, value: str) -> 'CreatePlanRequestBuilder':
        self._name = value
        return self

    def with_tier(self, value: str) -> 'CreatePlanRequestBuilder':
        self._tier = value
        return self

    def free_tier(self) -> 'CreatePlanRequestBuilder':
        self._tier = SubscriptionTierEnum.FREE.value
        self._price = Decimal("0")
        return self

    def basic_tier(self) -> 'CreatePlanRequestBuilder':
        self._tier = SubscriptionTierEnum.BASIC.value
        self._price = Decimal("9.99")
        return self

    def pro_tier(self) -> 'CreatePlanRequestBuilder':
        self._tier = SubscriptionTierEnum.PRO.value
        self._price = Decimal("29.99")
        return self

    def enterprise_tier(self) -> 'CreatePlanRequestBuilder':
        self._tier = SubscriptionTierEnum.ENTERPRISE.value
        self._price = Decimal("99.99")
        return self

    def with_price(self, value: Decimal) -> 'CreatePlanRequestBuilder':
        self._price = value
        return self

    def monthly(self) -> 'CreatePlanRequestBuilder':
        self._billing_cycle = BillingCycleEnum.MONTHLY.value
        return self

    def yearly(self) -> 'CreatePlanRequestBuilder':
        self._billing_cycle = BillingCycleEnum.YEARLY.value
        return self

    def with_trial_days(self, days: int) -> 'CreatePlanRequestBuilder':
        self._trial_days = days
        return self

    def with_features(self, features: Dict[str, Any]) -> 'CreatePlanRequestBuilder':
        self._features = features
        return self

    def build(self) -> CreatePlanRequestContract:
        return CreatePlanRequestContract(
            plan_id=self._plan_id,
            name=self._name,
            description=self._description,
            tier=self._tier,
            price=self._price,
            currency=self._currency,
            billing_cycle=self._billing_cycle,
            features=self._features,
            credits_included=self._credits_included,
            max_users=self._max_users,
            max_storage_gb=self._max_storage_gb,
            trial_days=self._trial_days,
            is_active=self._is_active,
            is_public=self._is_public,
        )


class CreateSubscriptionRequestBuilder:
    """Builder for create subscription requests with fluent API"""

    def __init__(self):
        self._user_id = PaymentTestDataFactory.make_user_id()
        self._plan_id = PaymentTestDataFactory.make_plan_id()
        self._organization_id = None
        self._payment_method_id = None
        self._trial_days = None
        self._metadata = {}

    def with_user_id(self, value: str) -> 'CreateSubscriptionRequestBuilder':
        self._user_id = value
        return self

    def with_plan_id(self, value: str) -> 'CreateSubscriptionRequestBuilder':
        self._plan_id = value
        return self

    def with_organization_id(self, value: str) -> 'CreateSubscriptionRequestBuilder':
        self._organization_id = value
        return self

    def with_payment_method_id(self, value: str) -> 'CreateSubscriptionRequestBuilder':
        self._payment_method_id = value
        return self

    def with_trial_days(self, days: int) -> 'CreateSubscriptionRequestBuilder':
        self._trial_days = days
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> 'CreateSubscriptionRequestBuilder':
        self._metadata = metadata
        return self

    def build(self) -> CreateSubscriptionRequestContract:
        return CreateSubscriptionRequestContract(
            user_id=self._user_id,
            plan_id=self._plan_id,
            organization_id=self._organization_id,
            payment_method_id=self._payment_method_id,
            trial_days=self._trial_days,
            metadata=self._metadata,
        )


class CreatePaymentIntentRequestBuilder:
    """Builder for create payment intent requests with fluent API"""

    def __init__(self):
        self._user_id = PaymentTestDataFactory.make_user_id()
        self._amount = Decimal("29.99")
        self._currency = CurrencyEnum.USD.value
        self._description = "Payment for services"
        self._metadata = {}

    def with_user_id(self, value: str) -> 'CreatePaymentIntentRequestBuilder':
        self._user_id = value
        return self

    def with_amount(self, value: Decimal) -> 'CreatePaymentIntentRequestBuilder':
        self._amount = value
        return self

    def with_currency(self, value: str) -> 'CreatePaymentIntentRequestBuilder':
        self._currency = value
        return self

    def with_description(self, value: str) -> 'CreatePaymentIntentRequestBuilder':
        self._description = value
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> 'CreatePaymentIntentRequestBuilder':
        self._metadata = metadata
        return self

    def build(self) -> CreatePaymentIntentRequestContract:
        return CreatePaymentIntentRequestContract(
            user_id=self._user_id,
            amount=self._amount,
            currency=self._currency,
            description=self._description,
            metadata=self._metadata,
        )


class CreateRefundRequestBuilder:
    """Builder for create refund requests with fluent API"""

    def __init__(self):
        self._payment_id = PaymentTestDataFactory.make_payment_id()
        self._amount = None
        self._reason = "Customer request"
        self._requested_by = PaymentTestDataFactory.make_user_id()

    def with_payment_id(self, value: str) -> 'CreateRefundRequestBuilder':
        self._payment_id = value
        return self

    def with_amount(self, value: Decimal) -> 'CreateRefundRequestBuilder':
        self._amount = value
        return self

    def full_refund(self) -> 'CreateRefundRequestBuilder':
        self._amount = None
        return self

    def partial_refund(self, amount: Decimal) -> 'CreateRefundRequestBuilder':
        self._amount = amount
        return self

    def with_reason(self, value: str) -> 'CreateRefundRequestBuilder':
        self._reason = value
        return self

    def with_requested_by(self, value: str) -> 'CreateRefundRequestBuilder':
        self._requested_by = value
        return self

    def build(self) -> CreateRefundRequestContract:
        return CreateRefundRequestContract(
            payment_id=self._payment_id,
            amount=self._amount,
            reason=self._reason,
            requested_by=self._requested_by,
        )


class CreateInvoiceRequestBuilder:
    """Builder for create invoice requests with fluent API"""

    def __init__(self):
        self._user_id = PaymentTestDataFactory.make_user_id()
        self._organization_id = None
        self._subscription_id = None
        self._amount_due = Decimal("29.99")
        self._currency = CurrencyEnum.USD.value
        self._due_date = None
        self._billing_period_start = None
        self._billing_period_end = None
        self._line_items = []

    def with_user_id(self, value: str) -> 'CreateInvoiceRequestBuilder':
        self._user_id = value
        return self

    def with_subscription_id(self, value: str) -> 'CreateInvoiceRequestBuilder':
        self._subscription_id = value
        return self

    def with_amount_due(self, value: Decimal) -> 'CreateInvoiceRequestBuilder':
        self._amount_due = value
        return self

    def with_due_date(self, value: datetime) -> 'CreateInvoiceRequestBuilder':
        self._due_date = value
        return self

    def with_line_items(self, items: List[Dict[str, Any]]) -> 'CreateInvoiceRequestBuilder':
        self._line_items = items
        return self

    def build(self) -> CreateInvoiceRequestContract:
        return CreateInvoiceRequestContract(
            user_id=self._user_id,
            organization_id=self._organization_id,
            subscription_id=self._subscription_id,
            amount_due=self._amount_due,
            currency=self._currency,
            due_date=self._due_date,
            billing_period_start=self._billing_period_start,
            billing_period_end=self._billing_period_end,
            line_items=self._line_items,
        )


class PaymentHistoryQueryBuilder:
    """Builder for payment history query with fluent API"""

    def __init__(self):
        self._user_id = None
        self._status = None
        self._start_date = None
        self._end_date = None
        self._limit = 100

    def with_user_id(self, value: str) -> 'PaymentHistoryQueryBuilder':
        self._user_id = value
        return self

    def with_status(self, value: str) -> 'PaymentHistoryQueryBuilder':
        self._status = value
        return self

    def succeeded_only(self) -> 'PaymentHistoryQueryBuilder':
        self._status = PaymentStatusEnum.SUCCEEDED.value
        return self

    def failed_only(self) -> 'PaymentHistoryQueryBuilder':
        self._status = PaymentStatusEnum.FAILED.value
        return self

    def with_date_range(self, start: datetime, end: datetime) -> 'PaymentHistoryQueryBuilder':
        self._start_date = start
        self._end_date = end
        return self

    def with_limit(self, value: int) -> 'PaymentHistoryQueryBuilder':
        self._limit = value
        return self

    def build(self) -> PaymentHistoryQueryRequestContract:
        return PaymentHistoryQueryRequestContract(
            user_id=self._user_id,
            status=self._status,
            start_date=self._start_date,
            end_date=self._end_date,
            limit=self._limit,
        )
