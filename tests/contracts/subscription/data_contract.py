"""
Subscription Service - Data Contract

Pydantic schemas, test data factory, and request builders for subscription_service.
Zero hardcoded data - all test data generated through factory methods.

Reference: docs/CDD_GUIDE.md
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
import secrets
import uuid


# ============================================================================
# Enum Contracts
# ============================================================================

class SubscriptionStatusContract(str, Enum):
    """Valid subscription statuses"""
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    PAUSED = "paused"
    EXPIRED = "expired"
    INCOMPLETE = "incomplete"


class BillingCycleContract(str, Enum):
    """Valid billing cycles"""
    MONTHLY = "monthly"
    YEARLY = "yearly"
    QUARTERLY = "quarterly"


class SubscriptionActionContract(str, Enum):
    """Valid subscription actions"""
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


class InitiatedByContract(str, Enum):
    """Who initiated the action"""
    USER = "user"
    SYSTEM = "system"
    ADMIN = "admin"
    PAYMENT_PROVIDER = "payment_provider"


# ============================================================================
# Request Contracts (10 schemas)
# ============================================================================

class CreateSubscriptionRequestContract(BaseModel):
    """Contract for subscription creation request"""
    user_id: str = Field(..., min_length=1, description="User ID")
    organization_id: Optional[str] = Field(default=None, description="Organization ID")
    tier_code: str = Field(..., min_length=1, description="Tier code")
    billing_cycle: BillingCycleContract = Field(default=BillingCycleContract.MONTHLY)
    payment_method_id: Optional[str] = Field(default=None)
    seats: int = Field(default=1, ge=1, le=1000)
    use_trial: bool = Field(default=False)
    promo_code: Optional[str] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()

    @field_validator('tier_code')
    @classmethod
    def validate_tier_code(cls, v):
        valid_tiers = ['free', 'pro', 'max', 'team', 'enterprise']
        if v.lower() not in valid_tiers:
            raise ValueError(f"tier_code must be one of {valid_tiers}")
        return v.lower()


class CancelSubscriptionRequestContract(BaseModel):
    """Contract for subscription cancellation request"""
    immediate: bool = Field(default=False, description="Cancel immediately or at period end")
    reason: Optional[str] = Field(default=None, max_length=500)
    feedback: Optional[str] = Field(default=None, max_length=1000)


class ConsumeCreditsRequestContract(BaseModel):
    """Contract for credit consumption request"""
    user_id: str = Field(..., min_length=1)
    organization_id: Optional[str] = Field(default=None)
    credits_to_consume: int = Field(..., gt=0, le=1_000_000_000)
    service_type: str = Field(..., min_length=1)
    usage_record_id: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None, max_length=500)
    metadata: Optional[Dict[str, Any]] = Field(default=None)

    @field_validator('service_type')
    @classmethod
    def validate_service_type(cls, v):
        if not v or not v.strip():
            raise ValueError("service_type cannot be empty")
        return v.strip()


class UpdateSubscriptionRequestContract(BaseModel):
    """Contract for subscription update request"""
    tier_code: Optional[str] = Field(default=None)
    billing_cycle: Optional[BillingCycleContract] = Field(default=None)
    seats: Optional[int] = Field(default=None, ge=1)
    auto_renew: Optional[bool] = Field(default=None)
    payment_method_id: Optional[str] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class GetSubscriptionsRequestContract(BaseModel):
    """Contract for list subscriptions request"""
    user_id: Optional[str] = Field(default=None)
    organization_id: Optional[str] = Field(default=None)
    status: Optional[SubscriptionStatusContract] = Field(default=None)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


class GetCreditBalanceRequestContract(BaseModel):
    """Contract for credit balance request"""
    user_id: str = Field(..., min_length=1)
    organization_id: Optional[str] = Field(default=None)


class GetSubscriptionHistoryRequestContract(BaseModel):
    """Contract for subscription history request"""
    subscription_id: str = Field(..., min_length=1)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


# ============================================================================
# Response Contracts (10 schemas)
# ============================================================================

class UserSubscriptionContract(BaseModel):
    """Contract for subscription data"""
    subscription_id: str
    user_id: str
    organization_id: Optional[str] = None
    tier_id: str
    tier_code: str
    status: SubscriptionStatusContract
    billing_cycle: BillingCycleContract
    price_paid: Decimal = Field(default=Decimal("0"))
    currency: str = "USD"
    credits_allocated: int = Field(ge=0)
    credits_used: int = Field(ge=0)
    credits_remaining: int = Field(ge=0)
    credits_rolled_over: int = Field(default=0, ge=0)
    current_period_start: datetime
    current_period_end: datetime
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    is_trial: bool = False
    seats_purchased: int = Field(default=1, ge=1)
    seats_used: int = Field(default=1, ge=0)
    cancel_at_period_end: bool = False
    canceled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    payment_method_id: Optional[str] = None
    external_subscription_id: Optional[str] = None
    auto_renew: bool = True
    next_billing_date: Optional[datetime] = None
    last_billing_date: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SubscriptionHistoryContract(BaseModel):
    """Contract for subscription history entry"""
    history_id: str
    subscription_id: str
    user_id: str
    organization_id: Optional[str] = None
    action: SubscriptionActionContract
    previous_tier_code: Optional[str] = None
    new_tier_code: Optional[str] = None
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    credits_change: int = 0
    credits_balance_after: Optional[int] = None
    price_change: Decimal = Field(default=Decimal("0"))
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    reason: Optional[str] = None
    initiated_by: InitiatedByContract = InitiatedByContract.SYSTEM
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class SubscriptionResponseContract(BaseModel):
    """Contract for single subscription response"""
    success: bool
    message: str
    subscription: Optional[UserSubscriptionContract] = None


class CreateSubscriptionResponseContract(BaseModel):
    """Contract for create subscription response"""
    success: bool
    message: str
    subscription: Optional[UserSubscriptionContract] = None
    credits_allocated: Optional[int] = None
    next_billing_date: Optional[datetime] = None


class CancelSubscriptionResponseContract(BaseModel):
    """Contract for cancel subscription response"""
    success: bool
    message: str
    canceled_at: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    credits_remaining: Optional[int] = None


class ConsumeCreditsResponseContract(BaseModel):
    """Contract for consume credits response"""
    success: bool
    message: str
    credits_consumed: int = 0
    credits_remaining: int = 0
    subscription_id: Optional[str] = None
    consumed_from: Optional[str] = None


class CreditBalanceResponseContract(BaseModel):
    """Contract for credit balance response"""
    success: bool
    message: str
    user_id: str
    organization_id: Optional[str] = None
    subscription_credits_remaining: int = 0
    subscription_credits_total: int = 0
    subscription_period_end: Optional[datetime] = None
    total_credits_available: int = 0
    subscription_id: Optional[str] = None
    tier_code: Optional[str] = None
    tier_name: Optional[str] = None


class SubscriptionListResponseContract(BaseModel):
    """Contract for subscription list response"""
    success: bool
    message: str
    subscriptions: List[UserSubscriptionContract] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class SubscriptionHistoryResponseContract(BaseModel):
    """Contract for subscription history response"""
    success: bool
    message: str
    history: List[SubscriptionHistoryContract] = Field(default_factory=list)
    total: int = 0


class ErrorResponseContract(BaseModel):
    """Contract for error response"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# SubscriptionTestDataFactory - 40+ methods (25 valid + 15 invalid)
# ============================================================================

class SubscriptionTestDataFactory:
    """Test data factory for subscription_service - zero hardcoded data"""

    # ========================================
    # Valid ID Generators
    # ========================================

    @staticmethod
    def make_subscription_id() -> str:
        """Generate valid subscription ID"""
        return f"sub_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate valid user ID"""
        return f"user_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_organization_id() -> str:
        """Generate valid organization ID"""
        return f"org_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_tier_id() -> str:
        """Generate valid tier ID"""
        return f"tier_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_history_id() -> str:
        """Generate valid history ID"""
        return f"hist_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_payment_method_id() -> str:
        """Generate valid payment method ID"""
        return f"pm_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_usage_record_id() -> str:
        """Generate valid usage record ID"""
        return f"usage_{uuid.uuid4().hex[:16]}"

    # ========================================
    # Valid Value Generators
    # ========================================

    @staticmethod
    def make_tier_code() -> str:
        """Generate random valid tier code"""
        tiers = ['free', 'pro', 'max', 'team', 'enterprise']
        return secrets.choice(tiers)

    @staticmethod
    def make_paid_tier_code() -> str:
        """Generate random paid tier code"""
        tiers = ['pro', 'max', 'team', 'enterprise']
        return secrets.choice(tiers)

    @staticmethod
    def make_billing_cycle() -> BillingCycleContract:
        """Generate random billing cycle"""
        cycles = [BillingCycleContract.MONTHLY, BillingCycleContract.QUARTERLY, BillingCycleContract.YEARLY]
        return secrets.choice(cycles)

    @staticmethod
    def make_status() -> SubscriptionStatusContract:
        """Generate random subscription status"""
        statuses = list(SubscriptionStatusContract)
        return secrets.choice(statuses)

    @staticmethod
    def make_active_status() -> SubscriptionStatusContract:
        """Generate active or trialing status"""
        return secrets.choice([SubscriptionStatusContract.ACTIVE, SubscriptionStatusContract.TRIALING])

    @staticmethod
    def make_credits_amount() -> int:
        """Generate random credit amount (1K to 100M)"""
        return secrets.randbelow(100_000_000) + 1000

    @staticmethod
    def make_small_credits_amount() -> int:
        """Generate small credit amount (100 to 10K)"""
        return secrets.randbelow(10_000) + 100

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_period_start() -> datetime:
        """Generate period start (today)"""
        return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def make_period_end() -> datetime:
        """Generate period end (30 days from now)"""
        return datetime.now(timezone.utc).replace(hour=23, minute=59, second=59) + timedelta(days=30)

    @staticmethod
    def make_trial_end() -> datetime:
        """Generate trial end (14 days from now)"""
        return datetime.now(timezone.utc) + timedelta(days=14)

    @staticmethod
    def make_service_type() -> str:
        """Generate random service type"""
        types = ['model_inference', 'storage_minio', 'mcp_service', 'api_call', 'media_processing']
        return secrets.choice(types)

    @staticmethod
    def make_cancellation_reason() -> str:
        """Generate cancellation reason"""
        reasons = ['Too expensive', 'Found alternative', 'No longer needed', 'Missing features', 'Other']
        return secrets.choice(reasons)

    @staticmethod
    def make_price(tier_code: str = 'pro') -> Decimal:
        """Generate price based on tier"""
        prices = {'free': 0, 'pro': 20, 'max': 50, 'team': 25, 'enterprise': 100}
        return Decimal(str(prices.get(tier_code, 20)))

    @staticmethod
    def make_seats_count() -> int:
        """Generate seat count (1 to 50)"""
        return secrets.randbelow(50) + 1

    @staticmethod
    def make_metadata() -> Dict[str, Any]:
        """Generate sample metadata"""
        return {
            "source": "api",
            "campaign": f"camp_{secrets.token_hex(4)}",
            "ref_code": secrets.token_hex(8)
        }

    # ========================================
    # Valid Request Generators
    # ========================================

    @staticmethod
    def make_create_subscription_request() -> CreateSubscriptionRequestContract:
        """Generate valid create subscription request"""
        return CreateSubscriptionRequestContract(
            user_id=SubscriptionTestDataFactory.make_user_id(),
            tier_code=SubscriptionTestDataFactory.make_tier_code(),
            billing_cycle=SubscriptionTestDataFactory.make_billing_cycle(),
            seats=1,
            use_trial=False
        )

    @staticmethod
    def make_create_trial_subscription_request() -> CreateSubscriptionRequestContract:
        """Generate valid create subscription request with trial"""
        return CreateSubscriptionRequestContract(
            user_id=SubscriptionTestDataFactory.make_user_id(),
            tier_code=SubscriptionTestDataFactory.make_paid_tier_code(),
            billing_cycle=BillingCycleContract.MONTHLY,
            use_trial=True
        )

    @staticmethod
    def make_create_team_subscription_request() -> CreateSubscriptionRequestContract:
        """Generate valid team subscription request"""
        return CreateSubscriptionRequestContract(
            user_id=SubscriptionTestDataFactory.make_user_id(),
            organization_id=SubscriptionTestDataFactory.make_organization_id(),
            tier_code='team',
            billing_cycle=BillingCycleContract.MONTHLY,
            seats=SubscriptionTestDataFactory.make_seats_count()
        )

    @staticmethod
    def make_cancel_subscription_request() -> CancelSubscriptionRequestContract:
        """Generate valid cancel subscription request"""
        return CancelSubscriptionRequestContract(
            immediate=False,
            reason=SubscriptionTestDataFactory.make_cancellation_reason()
        )

    @staticmethod
    def make_immediate_cancel_request() -> CancelSubscriptionRequestContract:
        """Generate immediate cancel request"""
        return CancelSubscriptionRequestContract(
            immediate=True,
            reason="Immediate cancellation requested"
        )

    @staticmethod
    def make_consume_credits_request() -> ConsumeCreditsRequestContract:
        """Generate valid consume credits request"""
        return ConsumeCreditsRequestContract(
            user_id=SubscriptionTestDataFactory.make_user_id(),
            credits_to_consume=SubscriptionTestDataFactory.make_small_credits_amount(),
            service_type=SubscriptionTestDataFactory.make_service_type(),
            usage_record_id=SubscriptionTestDataFactory.make_usage_record_id()
        )

    # ========================================
    # Valid Response/Entity Generators
    # ========================================

    @staticmethod
    def make_subscription() -> UserSubscriptionContract:
        """Generate valid subscription entity"""
        now = SubscriptionTestDataFactory.make_timestamp()
        credits = SubscriptionTestDataFactory.make_credits_amount()
        return UserSubscriptionContract(
            subscription_id=SubscriptionTestDataFactory.make_subscription_id(),
            user_id=SubscriptionTestDataFactory.make_user_id(),
            tier_id=SubscriptionTestDataFactory.make_tier_id(),
            tier_code=SubscriptionTestDataFactory.make_tier_code(),
            status=SubscriptionStatusContract.ACTIVE,
            billing_cycle=BillingCycleContract.MONTHLY,
            credits_allocated=credits,
            credits_used=0,
            credits_remaining=credits,
            current_period_start=SubscriptionTestDataFactory.make_period_start(),
            current_period_end=SubscriptionTestDataFactory.make_period_end(),
            created_at=now,
            updated_at=now
        )

    @staticmethod
    def make_trial_subscription() -> UserSubscriptionContract:
        """Generate subscription in trial"""
        sub = SubscriptionTestDataFactory.make_subscription()
        sub.status = SubscriptionStatusContract.TRIALING
        sub.is_trial = True
        sub.trial_start = SubscriptionTestDataFactory.make_timestamp()
        sub.trial_end = SubscriptionTestDataFactory.make_trial_end()
        return sub

    @staticmethod
    def make_subscription_history() -> SubscriptionHistoryContract:
        """Generate subscription history entry"""
        return SubscriptionHistoryContract(
            history_id=SubscriptionTestDataFactory.make_history_id(),
            subscription_id=SubscriptionTestDataFactory.make_subscription_id(),
            user_id=SubscriptionTestDataFactory.make_user_id(),
            action=SubscriptionActionContract.CREATED,
            new_tier_code=SubscriptionTestDataFactory.make_tier_code(),
            new_status='active',
            credits_change=SubscriptionTestDataFactory.make_credits_amount(),
            initiated_by=InitiatedByContract.USER,
            created_at=SubscriptionTestDataFactory.make_timestamp()
        )

    @staticmethod
    def make_success_response() -> SubscriptionResponseContract:
        """Generate success response"""
        return SubscriptionResponseContract(
            success=True,
            message="Operation successful",
            subscription=SubscriptionTestDataFactory.make_subscription()
        )

    @staticmethod
    def make_credit_balance_response() -> CreditBalanceResponseContract:
        """Generate credit balance response"""
        credits = SubscriptionTestDataFactory.make_credits_amount()
        return CreditBalanceResponseContract(
            success=True,
            message="Credit balance retrieved",
            user_id=SubscriptionTestDataFactory.make_user_id(),
            subscription_credits_remaining=credits,
            subscription_credits_total=credits * 2,
            total_credits_available=credits,
            subscription_id=SubscriptionTestDataFactory.make_subscription_id(),
            tier_code='pro',
            tier_name='Pro'
        )

    # ========================================
    # Invalid Data Generators (15+ methods)
    # ========================================

    @staticmethod
    def make_empty_user_id() -> str:
        """Generate empty user ID (invalid)"""
        return ""

    @staticmethod
    def make_whitespace_user_id() -> str:
        """Generate whitespace user ID (invalid)"""
        return "   "

    @staticmethod
    def make_invalid_tier_code() -> str:
        """Generate invalid tier code"""
        return f"invalid_tier_{secrets.token_hex(4)}"

    @staticmethod
    def make_negative_credits() -> int:
        """Generate negative credit amount (invalid)"""
        return -1000

    @staticmethod
    def make_zero_credits() -> int:
        """Generate zero credits (invalid for consumption)"""
        return 0

    @staticmethod
    def make_excessive_credits() -> int:
        """Generate excessive credit amount (invalid)"""
        return 10_000_000_000  # 10 billion

    @staticmethod
    def make_invalid_billing_cycle() -> str:
        """Generate invalid billing cycle"""
        return "biweekly"

    @staticmethod
    def make_invalid_status() -> str:
        """Generate invalid subscription status"""
        return "invalid_status"

    @staticmethod
    def make_negative_seats() -> int:
        """Generate negative seats (invalid)"""
        return -1

    @staticmethod
    def make_zero_seats() -> int:
        """Generate zero seats (invalid)"""
        return 0

    @staticmethod
    def make_excessive_seats() -> int:
        """Generate excessive seats (invalid)"""
        return 10000

    @staticmethod
    def make_empty_service_type() -> str:
        """Generate empty service type (invalid)"""
        return ""

    @staticmethod
    def make_nonexistent_subscription_id() -> str:
        """Generate subscription ID that doesn't exist"""
        return f"sub_nonexistent_{secrets.token_hex(8)}"

    @staticmethod
    def make_malformed_subscription_id() -> str:
        """Generate malformed subscription ID"""
        return "not_a_valid_id"

    @staticmethod
    def make_invalid_page() -> int:
        """Generate invalid page number"""
        return 0

    @staticmethod
    def make_invalid_page_size() -> int:
        """Generate invalid page size"""
        return 1000


# ============================================================================
# Request Builders (3 builders)
# ============================================================================

class CreateSubscriptionRequestBuilder:
    """Builder for create subscription requests"""

    def __init__(self):
        self._user_id = SubscriptionTestDataFactory.make_user_id()
        self._organization_id: Optional[str] = None
        self._tier_code = 'pro'
        self._billing_cycle = BillingCycleContract.MONTHLY
        self._payment_method_id: Optional[str] = None
        self._seats = 1
        self._use_trial = False
        self._promo_code: Optional[str] = None
        self._metadata: Optional[Dict[str, Any]] = None

    def with_user_id(self, user_id: str) -> 'CreateSubscriptionRequestBuilder':
        self._user_id = user_id
        return self

    def with_organization_id(self, org_id: str) -> 'CreateSubscriptionRequestBuilder':
        self._organization_id = org_id
        return self

    def with_tier_code(self, tier_code: str) -> 'CreateSubscriptionRequestBuilder':
        self._tier_code = tier_code
        return self

    def with_billing_cycle(self, cycle: BillingCycleContract) -> 'CreateSubscriptionRequestBuilder':
        self._billing_cycle = cycle
        return self

    def with_payment_method_id(self, pm_id: str) -> 'CreateSubscriptionRequestBuilder':
        self._payment_method_id = pm_id
        return self

    def with_seats(self, seats: int) -> 'CreateSubscriptionRequestBuilder':
        self._seats = seats
        return self

    def with_trial(self, use_trial: bool = True) -> 'CreateSubscriptionRequestBuilder':
        self._use_trial = use_trial
        return self

    def with_promo_code(self, code: str) -> 'CreateSubscriptionRequestBuilder':
        self._promo_code = code
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> 'CreateSubscriptionRequestBuilder':
        self._metadata = metadata
        return self

    def build(self) -> CreateSubscriptionRequestContract:
        return CreateSubscriptionRequestContract(
            user_id=self._user_id,
            organization_id=self._organization_id,
            tier_code=self._tier_code,
            billing_cycle=self._billing_cycle,
            payment_method_id=self._payment_method_id,
            seats=self._seats,
            use_trial=self._use_trial,
            promo_code=self._promo_code,
            metadata=self._metadata
        )


class ConsumeCreditsRequestBuilder:
    """Builder for consume credits requests"""

    def __init__(self):
        self._user_id = SubscriptionTestDataFactory.make_user_id()
        self._organization_id: Optional[str] = None
        self._credits_to_consume = SubscriptionTestDataFactory.make_small_credits_amount()
        self._service_type = 'model_inference'
        self._usage_record_id: Optional[str] = None
        self._description: Optional[str] = None
        self._metadata: Optional[Dict[str, Any]] = None

    def with_user_id(self, user_id: str) -> 'ConsumeCreditsRequestBuilder':
        self._user_id = user_id
        return self

    def with_organization_id(self, org_id: str) -> 'ConsumeCreditsRequestBuilder':
        self._organization_id = org_id
        return self

    def with_credits(self, credits: int) -> 'ConsumeCreditsRequestBuilder':
        self._credits_to_consume = credits
        return self

    def with_service_type(self, service_type: str) -> 'ConsumeCreditsRequestBuilder':
        self._service_type = service_type
        return self

    def with_usage_record_id(self, record_id: str) -> 'ConsumeCreditsRequestBuilder':
        self._usage_record_id = record_id
        return self

    def with_description(self, desc: str) -> 'ConsumeCreditsRequestBuilder':
        self._description = desc
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> 'ConsumeCreditsRequestBuilder':
        self._metadata = metadata
        return self

    def build(self) -> ConsumeCreditsRequestContract:
        return ConsumeCreditsRequestContract(
            user_id=self._user_id,
            organization_id=self._organization_id,
            credits_to_consume=self._credits_to_consume,
            service_type=self._service_type,
            usage_record_id=self._usage_record_id,
            description=self._description,
            metadata=self._metadata
        )


class CancelSubscriptionRequestBuilder:
    """Builder for cancel subscription requests"""

    def __init__(self):
        self._immediate = False
        self._reason: Optional[str] = None
        self._feedback: Optional[str] = None

    def immediate(self, is_immediate: bool = True) -> 'CancelSubscriptionRequestBuilder':
        self._immediate = is_immediate
        return self

    def with_reason(self, reason: str) -> 'CancelSubscriptionRequestBuilder':
        self._reason = reason
        return self

    def with_feedback(self, feedback: str) -> 'CancelSubscriptionRequestBuilder':
        self._feedback = feedback
        return self

    def build(self) -> CancelSubscriptionRequestContract:
        return CancelSubscriptionRequestContract(
            immediate=self._immediate,
            reason=self._reason,
            feedback=self._feedback
        )


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "SubscriptionStatusContract",
    "BillingCycleContract",
    "SubscriptionActionContract",
    "InitiatedByContract",
    # Request Contracts
    "CreateSubscriptionRequestContract",
    "CancelSubscriptionRequestContract",
    "ConsumeCreditsRequestContract",
    "UpdateSubscriptionRequestContract",
    "GetSubscriptionsRequestContract",
    "GetCreditBalanceRequestContract",
    "GetSubscriptionHistoryRequestContract",
    # Response/Entity Contracts
    "UserSubscriptionContract",
    "SubscriptionHistoryContract",
    "SubscriptionResponseContract",
    "CreateSubscriptionResponseContract",
    "CancelSubscriptionResponseContract",
    "ConsumeCreditsResponseContract",
    "CreditBalanceResponseContract",
    "SubscriptionListResponseContract",
    "SubscriptionHistoryResponseContract",
    "ErrorResponseContract",
    # Factory
    "SubscriptionTestDataFactory",
    # Builders
    "CreateSubscriptionRequestBuilder",
    "ConsumeCreditsRequestBuilder",
    "CancelSubscriptionRequestBuilder",
]
