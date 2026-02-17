"""
Billing Service - Data Contract

Pydantic schemas, test data factory, and request builders for billing_service.
Zero hardcoded data - all test data generated through factory methods.

This module defines:
1. Request Contracts - Pydantic schemas for API requests
2. Response Contracts - Pydantic schemas for API responses
3. BillingTestDataFactory - Test data generation (35+ methods)
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


class BillingStatusEnum(str, Enum):
    """Valid billing status values"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class BillingMethodEnum(str, Enum):
    """Valid billing method values"""
    WALLET_DEDUCTION = "wallet_deduction"
    PAYMENT_CHARGE = "payment_charge"
    CREDIT_CONSUMPTION = "credit_consumption"
    SUBSCRIPTION_INCLUDED = "subscription_included"


class ServiceTypeEnum(str, Enum):
    """Valid service type values"""
    MODEL_INFERENCE = "model_inference"
    MCP_SERVICE = "mcp_service"
    AGENT_EXECUTION = "agent_execution"
    STORAGE_MINIO = "storage_minio"
    API_GATEWAY = "api_gateway"
    NOTIFICATION = "notification"
    OTHER = "other"


class CurrencyEnum(str, Enum):
    """Valid currency values"""
    USD = "USD"
    CNY = "CNY"
    CREDIT = "CREDIT"


class QuotaTypeEnum(str, Enum):
    """Valid quota type values"""
    SOFT_LIMIT = "soft_limit"
    HARD_LIMIT = "hard_limit"


class QuotaPeriodEnum(str, Enum):
    """Valid quota period values"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# ============================================================================
# Request Contracts (10 schemas)
# ============================================================================


class UsageRecordRequestContract(BaseModel):
    """Contract for usage recording requests"""
    user_id: str = Field(..., min_length=1, max_length=50, description="User ID")
    organization_id: Optional[str] = Field(None, max_length=50, description="Organization ID")
    subscription_id: Optional[str] = Field(None, max_length=50, description="Subscription ID")
    product_id: str = Field(..., min_length=1, max_length=50, description="Product ID")
    service_type: str = Field(..., description="Service type")
    usage_amount: Decimal = Field(..., ge=0, description="Usage amount")
    session_id: Optional[str] = Field(None, description="Related session ID")
    request_id: Optional[str] = Field(None, description="Related request ID")
    usage_details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Usage details")
    usage_timestamp: Optional[datetime] = Field(None, description="Usage timestamp")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()

    @field_validator('product_id')
    @classmethod
    def validate_product_id(cls, v):
        if not v or not v.strip():
            raise ValueError("product_id cannot be empty")
        return v.strip()

    @field_validator('service_type')
    @classmethod
    def validate_service_type(cls, v):
        if v not in [e.value for e in ServiceTypeEnum]:
            raise ValueError(f"service_type must be one of: {[e.value for e in ServiceTypeEnum]}")
        return v


class BillingCalculateRequestContract(BaseModel):
    """Contract for billing calculation requests"""
    user_id: str = Field(..., min_length=1, description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    subscription_id: Optional[str] = Field(None, description="Subscription ID")
    product_id: str = Field(..., min_length=1, description="Product ID")
    usage_amount: Decimal = Field(..., ge=0, description="Usage amount to calculate")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()


class BillingProcessRequestContract(BaseModel):
    """Contract for billing process requests"""
    usage_record_id: str = Field(..., min_length=1, description="Usage record ID")
    billing_method: str = Field(..., description="Billing method to use")
    force_process: bool = Field(default=False, description="Force process even if insufficient funds")

    @field_validator('billing_method')
    @classmethod
    def validate_billing_method(cls, v):
        if v not in [e.value for e in BillingMethodEnum]:
            raise ValueError(f"billing_method must be one of: {[e.value for e in BillingMethodEnum]}")
        return v


class QuotaCheckRequestContract(BaseModel):
    """Contract for quota check requests"""
    user_id: Optional[str] = Field(None, description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    subscription_id: Optional[str] = Field(None, description="Subscription ID")
    service_type: str = Field(..., description="Service type")
    product_id: Optional[str] = Field(None, description="Product ID")
    requested_amount: Decimal = Field(..., ge=0, description="Amount to check")

    @field_validator('service_type')
    @classmethod
    def validate_service_type(cls, v):
        if v not in [e.value for e in ServiceTypeEnum]:
            raise ValueError(f"service_type must be one of: {[e.value for e in ServiceTypeEnum]}")
        return v


class BillingRecordQueryRequestContract(BaseModel):
    """Contract for billing record query parameters"""
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    organization_id: Optional[str] = Field(None, description="Filter by organization ID")
    service_type: Optional[str] = Field(None, description="Filter by service type")
    status: Optional[str] = Field(None, description="Filter by status")
    start_date: Optional[datetime] = Field(None, description="Filter start date")
    end_date: Optional[datetime] = Field(None, description="Filter end date")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=50, ge=1, le=100, description="Items per page")


class BillingStatsRequestContract(BaseModel):
    """Contract for billing statistics query parameters"""
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    organization_id: Optional[str] = Field(None, description="Filter by organization ID")
    service_type: Optional[str] = Field(None, description="Filter by service type")
    start_date: Optional[datetime] = Field(None, description="Filter start date")
    end_date: Optional[datetime] = Field(None, description="Filter end date")
    period_type: str = Field(default="daily", description="Aggregation period")


class QuotaStatusRequestContract(BaseModel):
    """Contract for quota status requests"""
    user_id: str = Field(..., min_length=1, description="User ID")
    service_type: Optional[str] = Field(None, description="Filter by service type")


class HealthCheckRequestContract(BaseModel):
    """Contract for health check requests (no body)"""
    pass


class DetailedHealthCheckRequestContract(BaseModel):
    """Contract for detailed health check requests (no body)"""
    pass


# ============================================================================
# Response Contracts (12 schemas)
# ============================================================================


class BillingRecordResponseContract(BaseModel):
    """Contract for billing record response"""
    billing_id: str = Field(..., description="Billing record ID")
    user_id: str = Field(..., description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    subscription_id: Optional[str] = Field(None, description="Subscription ID")
    usage_record_id: str = Field(..., description="Usage record ID")
    product_id: str = Field(..., description="Product ID")
    service_type: str = Field(..., description="Service type")
    usage_amount: Decimal = Field(..., ge=0, description="Usage amount")
    unit_price: Decimal = Field(..., ge=0, description="Unit price")
    total_amount: Decimal = Field(..., ge=0, description="Total amount")
    currency: str = Field(..., description="Currency")
    billing_method: str = Field(..., description="Billing method used")
    billing_status: str = Field(..., description="Billing status")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    failure_reason: Optional[str] = Field(None, description="Failure reason if failed")
    wallet_transaction_id: Optional[str] = Field(None, description="Wallet transaction ID")
    payment_transaction_id: Optional[str] = Field(None, description="Payment transaction ID")
    billing_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")

    class Config:
        from_attributes = True


class BillingRecordListResponseContract(BaseModel):
    """Contract for billing record list response"""
    records: List[BillingRecordResponseContract] = Field(..., description="Billing records")
    total: int = Field(..., ge=0, description="Total count")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, le=100, description="Page size")


class BillingCalculateResponseContract(BaseModel):
    """Contract for billing calculation response"""
    success: bool = Field(..., description="Calculation success")
    message: str = Field(..., description="Result message")
    user_id: Optional[str] = Field(None, description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    subscription_id: Optional[str] = Field(None, description="Subscription ID")
    product_id: str = Field(..., description="Product ID")
    usage_amount: Decimal = Field(..., ge=0, description="Usage amount")
    unit_price: Decimal = Field(..., ge=0, description="Unit price")
    total_cost: Decimal = Field(..., ge=0, description="Total calculated cost")
    currency: str = Field(..., description="Currency")
    is_free_tier: bool = Field(default=False, description="Is covered by free tier")
    is_included_in_subscription: bool = Field(default=False, description="Is included in subscription")
    free_tier_remaining: Optional[Decimal] = Field(None, description="Remaining free tier")
    suggested_billing_method: str = Field(..., description="Suggested billing method")
    available_billing_methods: List[str] = Field(..., description="Available billing methods")
    wallet_balance: Optional[Decimal] = Field(None, description="Current wallet balance")
    credit_balance: Optional[Decimal] = Field(None, description="Current credit balance")


class BillingProcessResponseContract(BaseModel):
    """Contract for billing process response"""
    success: bool = Field(..., description="Processing success")
    message: str = Field(..., description="Result message")
    billing_record_id: Optional[str] = Field(None, description="Billing record ID")
    amount_charged: Optional[Decimal] = Field(None, description="Amount charged")
    billing_method_used: Optional[str] = Field(None, description="Billing method used")
    remaining_wallet_balance: Optional[Decimal] = Field(None, description="Remaining wallet balance")
    remaining_credit_balance: Optional[Decimal] = Field(None, description="Remaining credit balance")
    wallet_transaction_id: Optional[str] = Field(None, description="Wallet transaction ID")
    payment_transaction_id: Optional[str] = Field(None, description="Payment transaction ID")


class QuotaCheckResponseContract(BaseModel):
    """Contract for quota check response"""
    allowed: bool = Field(..., description="Is usage allowed")
    message: str = Field(..., description="Result message")
    quota_limit: Optional[Decimal] = Field(None, description="Quota limit")
    quota_used: Optional[Decimal] = Field(None, description="Quota used")
    quota_remaining: Optional[Decimal] = Field(None, description="Quota remaining")
    quota_period: Optional[str] = Field(None, description="Quota period type")
    next_reset_date: Optional[datetime] = Field(None, description="Next reset date")
    suggested_actions: List[str] = Field(default_factory=list, description="Suggested actions if exceeded")


class QuotaStatusResponseContract(BaseModel):
    """Contract for quota status response"""
    user_id: str = Field(..., description="User ID")
    quotas: List[Dict[str, Any]] = Field(..., description="Quota list")


class BillingStatsResponseContract(BaseModel):
    """Contract for billing statistics response"""
    period_start: datetime = Field(..., description="Period start")
    period_end: datetime = Field(..., description="Period end")
    period_type: str = Field(..., description="Period type")
    total_usage_records: int = Field(..., ge=0, description="Total usage records")
    total_cost: Decimal = Field(..., ge=0, description="Total cost")
    total_usage_amount: Decimal = Field(..., ge=0, description="Total usage amount")
    service_breakdown: Dict[str, Dict[str, Any]] = Field(..., description="Breakdown by service")
    time_series: List[Dict[str, Any]] = Field(..., description="Time series data")
    billing_method_breakdown: Dict[str, Decimal] = Field(..., description="Breakdown by billing method")


class HealthCheckResponseContract(BaseModel):
    """Contract for health check response"""
    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    port: int = Field(..., description="Service port")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="Timestamp ISO format")


class DetailedHealthCheckResponseContract(BaseModel):
    """Contract for detailed health check response"""
    service: str = Field(default="billing_service")
    status: str = Field(default="operational")
    port: int = Field(default=8208)
    version: str = Field(default="1.0.0")
    database_connected: bool
    wallet_client_available: bool
    subscription_client_available: bool
    product_client_available: bool
    timestamp: Optional[datetime]


class ErrorResponseContract(BaseModel):
    """Contract for error responses"""
    error: Optional[str] = Field(None, description="Error type")
    detail: str = Field(..., description="Error detail")
    timestamp: Optional[datetime] = Field(None, description="Error timestamp")


class SuccessResponseContract(BaseModel):
    """Contract for success message responses"""
    message: str = Field(..., description="Success message")


# ============================================================================
# BillingTestDataFactory - 35+ methods (20+ valid + 15+ invalid)
# ============================================================================


class BillingTestDataFactory:
    """
    Test data factory for billing_service - zero hardcoded data.

    All methods generate unique, valid test data suitable for testing.
    Factory methods are prefixed with make_ for valid data and
    make_invalid_ for invalid data scenarios.
    """

    # ========================================================================
    # Valid Data Generators (20+ methods)
    # ========================================================================

    @staticmethod
    def make_billing_id() -> str:
        """Generate valid billing ID"""
        return f"bill_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_usage_record_id() -> str:
        """Generate valid usage record ID"""
        return f"usage_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate valid user ID"""
        return f"user_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_organization_id() -> str:
        """Generate valid organization ID"""
        return f"org_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_subscription_id() -> str:
        """Generate valid subscription ID"""
        return f"sub_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_product_id() -> str:
        """Generate valid product ID"""
        return f"prod_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_quota_id() -> str:
        """Generate valid quota ID"""
        return f"quota_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_session_id() -> str:
        """Generate valid session ID"""
        return f"sess_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_request_id() -> str:
        """Generate valid request ID"""
        return f"req_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_transaction_id() -> str:
        """Generate valid transaction ID"""
        return f"txn_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_past_timestamp(hours_ago: int = 1) -> datetime:
        """Generate timestamp in the past"""
        return datetime.now(timezone.utc) - timedelta(hours=hours_ago)

    @staticmethod
    def make_future_timestamp(hours_ahead: int = 1) -> datetime:
        """Generate timestamp in the future"""
        return datetime.now(timezone.utc) + timedelta(hours=hours_ahead)

    @staticmethod
    def make_service_type() -> str:
        """Generate valid service type"""
        return secrets.choice([e.value for e in ServiceTypeEnum])

    @staticmethod
    def make_billing_status() -> str:
        """Generate valid billing status"""
        return BillingStatusEnum.PENDING.value

    @staticmethod
    def make_billing_method() -> str:
        """Generate valid billing method"""
        return BillingMethodEnum.WALLET_DEDUCTION.value

    @staticmethod
    def make_currency() -> str:
        """Generate valid currency"""
        return CurrencyEnum.USD.value

    @staticmethod
    def make_usage_amount() -> Decimal:
        """Generate valid usage amount"""
        return Decimal(str(secrets.randbelow(10000) + 100))  # 100-10099

    @staticmethod
    def make_unit_price() -> Decimal:
        """Generate valid unit price"""
        return Decimal(str(round(secrets.randbelow(100) / 10000 + 0.0001, 6)))  # 0.0001 - 0.0101

    @staticmethod
    def make_total_amount() -> Decimal:
        """Generate valid total amount"""
        return Decimal(str(round(secrets.randbelow(1000) / 100 + 0.01, 2)))  # 0.01 - 10.00

    @staticmethod
    def make_wallet_balance() -> Decimal:
        """Generate valid wallet balance"""
        return Decimal(str(round(secrets.randbelow(10000) / 100 + 10.0, 2)))  # 10.00 - 110.00

    @staticmethod
    def make_credit_balance() -> Decimal:
        """Generate valid credit balance"""
        return Decimal(str(secrets.randbelow(1000) + 100))  # 100-1099 credits

    @staticmethod
    def make_quota_limit() -> Decimal:
        """Generate valid quota limit"""
        return Decimal(str(secrets.randbelow(100000) + 10000))  # 10000-109999

    @staticmethod
    def make_quota_used() -> Decimal:
        """Generate valid quota used"""
        return Decimal(str(secrets.randbelow(5000) + 100))  # 100-5099

    @staticmethod
    def make_usage_details() -> Dict[str, Any]:
        """Generate valid usage details"""
        return {
            "model": f"model_{secrets.token_hex(4)}",
            "tokens_input": secrets.randbelow(1000) + 100,
            "tokens_output": secrets.randbelow(500) + 50,
            "latency_ms": secrets.randbelow(1000) + 100,
        }

    @staticmethod
    def make_billing_metadata() -> Dict[str, Any]:
        """Generate valid billing metadata"""
        return {
            "source": secrets.choice(["api", "web", "mobile"]),
            "client_version": f"1.{secrets.randbelow(10)}.{secrets.randbelow(10)}",
            "processing_time_ms": secrets.randbelow(500) + 50,
        }

    @staticmethod
    def make_usage_record_request(**overrides) -> UsageRecordRequestContract:
        """Generate valid usage record request"""
        defaults = {
            "user_id": BillingTestDataFactory.make_user_id(),
            "organization_id": None,
            "subscription_id": None,
            "product_id": BillingTestDataFactory.make_product_id(),
            "service_type": BillingTestDataFactory.make_service_type(),
            "usage_amount": BillingTestDataFactory.make_usage_amount(),
            "session_id": BillingTestDataFactory.make_session_id(),
            "request_id": BillingTestDataFactory.make_request_id(),
            "usage_details": BillingTestDataFactory.make_usage_details(),
            "usage_timestamp": BillingTestDataFactory.make_timestamp(),
        }
        defaults.update(overrides)
        return UsageRecordRequestContract(**defaults)

    @staticmethod
    def make_billing_calculate_request(**overrides) -> BillingCalculateRequestContract:
        """Generate valid billing calculation request"""
        defaults = {
            "user_id": BillingTestDataFactory.make_user_id(),
            "organization_id": None,
            "subscription_id": None,
            "product_id": BillingTestDataFactory.make_product_id(),
            "usage_amount": BillingTestDataFactory.make_usage_amount(),
        }
        defaults.update(overrides)
        return BillingCalculateRequestContract(**defaults)

    @staticmethod
    def make_billing_process_request(**overrides) -> BillingProcessRequestContract:
        """Generate valid billing process request"""
        defaults = {
            "usage_record_id": BillingTestDataFactory.make_usage_record_id(),
            "billing_method": BillingTestDataFactory.make_billing_method(),
            "force_process": False,
        }
        defaults.update(overrides)
        return BillingProcessRequestContract(**defaults)

    @staticmethod
    def make_quota_check_request(**overrides) -> QuotaCheckRequestContract:
        """Generate valid quota check request"""
        defaults = {
            "user_id": BillingTestDataFactory.make_user_id(),
            "organization_id": None,
            "subscription_id": None,
            "service_type": BillingTestDataFactory.make_service_type(),
            "product_id": None,
            "requested_amount": BillingTestDataFactory.make_usage_amount(),
        }
        defaults.update(overrides)
        return QuotaCheckRequestContract(**defaults)

    @staticmethod
    def make_billing_record_response(**overrides) -> BillingRecordResponseContract:
        """Generate valid billing record response"""
        now = BillingTestDataFactory.make_timestamp()
        usage_amount = BillingTestDataFactory.make_usage_amount()
        unit_price = BillingTestDataFactory.make_unit_price()
        defaults = {
            "billing_id": BillingTestDataFactory.make_billing_id(),
            "user_id": BillingTestDataFactory.make_user_id(),
            "organization_id": None,
            "subscription_id": None,
            "usage_record_id": BillingTestDataFactory.make_usage_record_id(),
            "product_id": BillingTestDataFactory.make_product_id(),
            "service_type": BillingTestDataFactory.make_service_type(),
            "usage_amount": usage_amount,
            "unit_price": unit_price,
            "total_amount": usage_amount * unit_price,
            "currency": CurrencyEnum.USD.value,
            "billing_method": BillingMethodEnum.WALLET_DEDUCTION.value,
            "billing_status": BillingStatusEnum.COMPLETED.value,
            "processed_at": now,
            "failure_reason": None,
            "wallet_transaction_id": BillingTestDataFactory.make_transaction_id(),
            "payment_transaction_id": None,
            "billing_metadata": {},
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return BillingRecordResponseContract(**defaults)

    @staticmethod
    def make_billing_calculate_response(**overrides) -> BillingCalculateResponseContract:
        """Generate valid billing calculation response"""
        usage_amount = BillingTestDataFactory.make_usage_amount()
        unit_price = BillingTestDataFactory.make_unit_price()
        defaults = {
            "success": True,
            "message": "Cost calculated successfully",
            "user_id": BillingTestDataFactory.make_user_id(),
            "organization_id": None,
            "subscription_id": None,
            "product_id": BillingTestDataFactory.make_product_id(),
            "usage_amount": usage_amount,
            "unit_price": unit_price,
            "total_cost": usage_amount * unit_price,
            "currency": CurrencyEnum.USD.value,
            "is_free_tier": False,
            "is_included_in_subscription": False,
            "free_tier_remaining": Decimal("0"),
            "suggested_billing_method": BillingMethodEnum.WALLET_DEDUCTION.value,
            "available_billing_methods": [
                BillingMethodEnum.WALLET_DEDUCTION.value,
                BillingMethodEnum.CREDIT_CONSUMPTION.value,
            ],
            "wallet_balance": BillingTestDataFactory.make_wallet_balance(),
            "credit_balance": BillingTestDataFactory.make_credit_balance(),
        }
        defaults.update(overrides)
        return BillingCalculateResponseContract(**defaults)

    @staticmethod
    def make_quota_check_response(**overrides) -> QuotaCheckResponseContract:
        """Generate valid quota check response"""
        quota_limit = BillingTestDataFactory.make_quota_limit()
        quota_used = BillingTestDataFactory.make_quota_used()
        defaults = {
            "allowed": True,
            "message": "Usage allowed within quota",
            "quota_limit": quota_limit,
            "quota_used": quota_used,
            "quota_remaining": quota_limit - quota_used,
            "quota_period": "monthly",
            "next_reset_date": BillingTestDataFactory.make_future_timestamp(hours_ahead=720),
            "suggested_actions": [],
        }
        defaults.update(overrides)
        return QuotaCheckResponseContract(**defaults)

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
    def make_invalid_product_id_empty() -> str:
        """Generate invalid product ID (empty string)"""
        return ""

    @staticmethod
    def make_invalid_service_type() -> str:
        """Generate invalid service type"""
        return "invalid_service_type"

    @staticmethod
    def make_invalid_billing_method() -> str:
        """Generate invalid billing method"""
        return "invalid_billing_method"

    @staticmethod
    def make_invalid_billing_status() -> str:
        """Generate invalid billing status"""
        return "invalid_status"

    @staticmethod
    def make_invalid_currency() -> str:
        """Generate invalid currency"""
        return "INVALID"

    @staticmethod
    def make_invalid_usage_amount_negative() -> Decimal:
        """Generate invalid usage amount (negative)"""
        return Decimal("-100")

    @staticmethod
    def make_invalid_unit_price_negative() -> Decimal:
        """Generate invalid unit price (negative)"""
        return Decimal("-0.01")

    @staticmethod
    def make_invalid_page_zero() -> int:
        """Generate invalid page number (zero)"""
        return 0

    @staticmethod
    def make_invalid_page_negative() -> int:
        """Generate invalid page number (negative)"""
        return -1

    @staticmethod
    def make_invalid_page_size_zero() -> int:
        """Generate invalid page size (zero)"""
        return 0

    @staticmethod
    def make_invalid_page_size_too_large() -> int:
        """Generate invalid page size (too large)"""
        return 500

    @staticmethod
    def make_nonexistent_billing_id() -> str:
        """Generate a billing ID that doesn't exist"""
        return f"bill_nonexistent_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_nonexistent_user_id() -> str:
        """Generate a user ID that doesn't exist"""
        return f"user_nonexistent_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_nonexistent_usage_record_id() -> str:
        """Generate a usage record ID that doesn't exist"""
        return f"usage_nonexistent_{uuid.uuid4().hex[:8]}"


# ============================================================================
# Request Builders (4 builders)
# ============================================================================


class UsageRecordRequestBuilder:
    """Builder for usage record requests with fluent API"""

    def __init__(self):
        self._user_id = BillingTestDataFactory.make_user_id()
        self._organization_id = None
        self._subscription_id = None
        self._product_id = BillingTestDataFactory.make_product_id()
        self._service_type = ServiceTypeEnum.MODEL_INFERENCE.value
        self._usage_amount = BillingTestDataFactory.make_usage_amount()
        self._session_id = None
        self._request_id = None
        self._usage_details = {}
        self._usage_timestamp = None

    def with_user_id(self, value: str) -> 'UsageRecordRequestBuilder':
        """Set user ID"""
        self._user_id = value
        return self

    def with_organization_id(self, value: str) -> 'UsageRecordRequestBuilder':
        """Set organization ID"""
        self._organization_id = value
        return self

    def with_subscription_id(self, value: str) -> 'UsageRecordRequestBuilder':
        """Set subscription ID"""
        self._subscription_id = value
        return self

    def with_product_id(self, value: str) -> 'UsageRecordRequestBuilder':
        """Set product ID"""
        self._product_id = value
        return self

    def with_service_type(self, value: str) -> 'UsageRecordRequestBuilder':
        """Set service type"""
        self._service_type = value
        return self

    def for_model_inference(self) -> 'UsageRecordRequestBuilder':
        """Set service type to model inference"""
        self._service_type = ServiceTypeEnum.MODEL_INFERENCE.value
        return self

    def for_storage(self) -> 'UsageRecordRequestBuilder':
        """Set service type to storage"""
        self._service_type = ServiceTypeEnum.STORAGE_MINIO.value
        return self

    def for_api_gateway(self) -> 'UsageRecordRequestBuilder':
        """Set service type to API gateway"""
        self._service_type = ServiceTypeEnum.API_GATEWAY.value
        return self

    def with_usage_amount(self, value: Decimal) -> 'UsageRecordRequestBuilder':
        """Set usage amount"""
        self._usage_amount = value
        return self

    def with_session_id(self, value: str) -> 'UsageRecordRequestBuilder':
        """Set session ID"""
        self._session_id = value
        return self

    def with_usage_details(self, value: Dict[str, Any]) -> 'UsageRecordRequestBuilder':
        """Set usage details"""
        self._usage_details = value
        return self

    def build(self) -> UsageRecordRequestContract:
        """Build the request"""
        return UsageRecordRequestContract(
            user_id=self._user_id,
            organization_id=self._organization_id,
            subscription_id=self._subscription_id,
            product_id=self._product_id,
            service_type=self._service_type,
            usage_amount=self._usage_amount,
            session_id=self._session_id,
            request_id=self._request_id,
            usage_details=self._usage_details,
            usage_timestamp=self._usage_timestamp,
        )


class BillingCalculateRequestBuilder:
    """Builder for billing calculation requests with fluent API"""

    def __init__(self):
        self._user_id = BillingTestDataFactory.make_user_id()
        self._organization_id = None
        self._subscription_id = None
        self._product_id = BillingTestDataFactory.make_product_id()
        self._usage_amount = BillingTestDataFactory.make_usage_amount()

    def with_user_id(self, value: str) -> 'BillingCalculateRequestBuilder':
        """Set user ID"""
        self._user_id = value
        return self

    def with_organization_id(self, value: str) -> 'BillingCalculateRequestBuilder':
        """Set organization ID"""
        self._organization_id = value
        return self

    def with_subscription_id(self, value: str) -> 'BillingCalculateRequestBuilder':
        """Set subscription ID"""
        self._subscription_id = value
        return self

    def with_product_id(self, value: str) -> 'BillingCalculateRequestBuilder':
        """Set product ID"""
        self._product_id = value
        return self

    def with_usage_amount(self, value: Decimal) -> 'BillingCalculateRequestBuilder':
        """Set usage amount"""
        self._usage_amount = value
        return self

    def build(self) -> BillingCalculateRequestContract:
        """Build the request"""
        return BillingCalculateRequestContract(
            user_id=self._user_id,
            organization_id=self._organization_id,
            subscription_id=self._subscription_id,
            product_id=self._product_id,
            usage_amount=self._usage_amount,
        )


class BillingProcessRequestBuilder:
    """Builder for billing process requests with fluent API"""

    def __init__(self):
        self._usage_record_id = BillingTestDataFactory.make_usage_record_id()
        self._billing_method = BillingMethodEnum.WALLET_DEDUCTION.value
        self._force_process = False

    def with_usage_record_id(self, value: str) -> 'BillingProcessRequestBuilder':
        """Set usage record ID"""
        self._usage_record_id = value
        return self

    def with_billing_method(self, value: str) -> 'BillingProcessRequestBuilder':
        """Set billing method"""
        self._billing_method = value
        return self

    def using_wallet(self) -> 'BillingProcessRequestBuilder':
        """Set billing method to wallet deduction"""
        self._billing_method = BillingMethodEnum.WALLET_DEDUCTION.value
        return self

    def using_credits(self) -> 'BillingProcessRequestBuilder':
        """Set billing method to credit consumption"""
        self._billing_method = BillingMethodEnum.CREDIT_CONSUMPTION.value
        return self

    def using_payment(self) -> 'BillingProcessRequestBuilder':
        """Set billing method to payment charge"""
        self._billing_method = BillingMethodEnum.PAYMENT_CHARGE.value
        return self

    def force(self) -> 'BillingProcessRequestBuilder':
        """Enable force processing"""
        self._force_process = True
        return self

    def build(self) -> BillingProcessRequestContract:
        """Build the request"""
        return BillingProcessRequestContract(
            usage_record_id=self._usage_record_id,
            billing_method=self._billing_method,
            force_process=self._force_process,
        )


class QuotaCheckRequestBuilder:
    """Builder for quota check requests with fluent API"""

    def __init__(self):
        self._user_id = BillingTestDataFactory.make_user_id()
        self._organization_id = None
        self._subscription_id = None
        self._service_type = ServiceTypeEnum.MODEL_INFERENCE.value
        self._product_id = None
        self._requested_amount = BillingTestDataFactory.make_usage_amount()

    def with_user_id(self, value: str) -> 'QuotaCheckRequestBuilder':
        """Set user ID"""
        self._user_id = value
        return self

    def with_organization_id(self, value: str) -> 'QuotaCheckRequestBuilder':
        """Set organization ID"""
        self._organization_id = value
        return self

    def with_service_type(self, value: str) -> 'QuotaCheckRequestBuilder':
        """Set service type"""
        self._service_type = value
        return self

    def for_model_inference(self) -> 'QuotaCheckRequestBuilder':
        """Set service type to model inference"""
        self._service_type = ServiceTypeEnum.MODEL_INFERENCE.value
        return self

    def for_storage(self) -> 'QuotaCheckRequestBuilder':
        """Set service type to storage"""
        self._service_type = ServiceTypeEnum.STORAGE_MINIO.value
        return self

    def with_product_id(self, value: str) -> 'QuotaCheckRequestBuilder':
        """Set product ID"""
        self._product_id = value
        return self

    def with_requested_amount(self, value: Decimal) -> 'QuotaCheckRequestBuilder':
        """Set requested amount"""
        self._requested_amount = value
        return self

    def build(self) -> QuotaCheckRequestContract:
        """Build the request"""
        return QuotaCheckRequestContract(
            user_id=self._user_id,
            organization_id=self._organization_id,
            subscription_id=self._subscription_id,
            service_type=self._service_type,
            product_id=self._product_id,
            requested_amount=self._requested_amount,
        )
