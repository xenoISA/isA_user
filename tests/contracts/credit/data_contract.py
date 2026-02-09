"""
Credit Service - Data Contract

Pydantic schemas, test data factory, and request builders for credit_service.
Zero hardcoded data - all test data generated through factory methods.

This module defines:
1. Request Contracts - Pydantic schemas for API requests
2. Response Contracts - Pydantic schemas for API responses
3. CreditTestDataFactory - Test data generation (35+ methods)
4. Request Builders - Fluent API for building test requests
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone, timedelta
from enum import Enum
import secrets
import uuid


# ============================================================================
# Enumerations
# ============================================================================


class CreditTypeEnum(str, Enum):
    """Valid credit type values"""
    PROMOTIONAL = "promotional"
    BONUS = "bonus"
    REFERRAL = "referral"
    SUBSCRIPTION = "subscription"
    COMPENSATION = "compensation"


class TransactionTypeEnum(str, Enum):
    """Valid transaction type values"""
    ALLOCATE = "allocate"
    CONSUME = "consume"
    EXPIRE = "expire"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    ADJUST = "adjust"


class AllocationStatusEnum(str, Enum):
    """Valid allocation status values"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ExpirationPolicyEnum(str, Enum):
    """Valid expiration policy values"""
    FIXED_DAYS = "fixed_days"
    END_OF_MONTH = "end_of_month"
    END_OF_YEAR = "end_of_year"
    SUBSCRIPTION_PERIOD = "subscription_period"
    NEVER = "never"


class ReferenceTypeEnum(str, Enum):
    """Valid reference type values"""
    CAMPAIGN = "campaign"
    BILLING = "billing"
    REFUND = "refund"
    SUBSCRIPTION = "subscription"
    MANUAL = "manual"
    TRANSFER = "transfer"


# ============================================================================
# Request Contracts (10 schemas)
# ============================================================================


class CreateAccountRequestContract(BaseModel):
    """Contract for credit account creation requests"""
    user_id: str = Field(..., min_length=1, max_length=50, description="User ID")
    organization_id: Optional[str] = Field(None, max_length=50, description="Organization ID")
    credit_type: str = Field(..., description="Credit type")
    expiration_policy: str = Field(default="fixed_days", description="Expiration policy")
    expiration_days: int = Field(default=90, ge=1, le=365, description="Days until expiration")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()

    @field_validator('credit_type')
    @classmethod
    def validate_credit_type(cls, v):
        if v not in [e.value for e in CreditTypeEnum]:
            raise ValueError(f"credit_type must be one of: {[e.value for e in CreditTypeEnum]}")
        return v

    @field_validator('expiration_policy')
    @classmethod
    def validate_expiration_policy(cls, v):
        if v not in [e.value for e in ExpirationPolicyEnum]:
            raise ValueError(f"expiration_policy must be one of: {[e.value for e in ExpirationPolicyEnum]}")
        return v


class AllocateCreditsRequestContract(BaseModel):
    """Contract for credit allocation requests"""
    user_id: str = Field(..., min_length=1, max_length=50, description="User ID")
    credit_type: str = Field(..., description="Credit type")
    amount: int = Field(..., gt=0, description="Amount to allocate")
    campaign_id: Optional[str] = Field(None, max_length=50, description="Campaign ID")
    description: Optional[str] = Field(None, max_length=500, description="Allocation description")
    expires_at: Optional[datetime] = Field(None, description="Expiration datetime")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()

    @field_validator('credit_type')
    @classmethod
    def validate_credit_type(cls, v):
        if v not in [e.value for e in CreditTypeEnum]:
            raise ValueError(f"credit_type must be one of: {[e.value for e in CreditTypeEnum]}")
        return v


class ConsumeCreditsRequestContract(BaseModel):
    """Contract for credit consumption requests"""
    user_id: str = Field(..., min_length=1, max_length=50, description="User ID")
    amount: int = Field(..., gt=0, description="Amount to consume")
    billing_record_id: Optional[str] = Field(None, max_length=50, description="Billing record ID")
    description: Optional[str] = Field(None, max_length=500, description="Consumption description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()


class CheckAvailabilityRequestContract(BaseModel):
    """Contract for credit availability check requests"""
    user_id: str = Field(..., min_length=1, max_length=50, description="User ID")
    amount: int = Field(..., gt=0, description="Amount to check")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()


class TransferCreditsRequestContract(BaseModel):
    """Contract for credit transfer requests"""
    from_user_id: str = Field(..., min_length=1, max_length=50, description="Sender user ID")
    to_user_id: str = Field(..., min_length=1, max_length=50, description="Recipient user ID")
    credit_type: str = Field(..., description="Credit type to transfer")
    amount: int = Field(..., gt=0, description="Amount to transfer")
    description: Optional[str] = Field(None, max_length=500, description="Transfer description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('from_user_id', 'to_user_id')
    @classmethod
    def validate_user_ids(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()

    @field_validator('credit_type')
    @classmethod
    def validate_credit_type(cls, v):
        if v not in [e.value for e in CreditTypeEnum]:
            raise ValueError(f"credit_type must be one of: {[e.value for e in CreditTypeEnum]}")
        return v


class CreateCampaignRequestContract(BaseModel):
    """Contract for campaign creation requests"""
    name: str = Field(..., min_length=1, max_length=100, description="Campaign name")
    description: Optional[str] = Field(None, max_length=1000, description="Campaign description")
    credit_type: str = Field(..., description="Credit type to allocate")
    credit_amount: int = Field(..., gt=0, description="Credits per allocation")
    total_budget: int = Field(..., gt=0, description="Total campaign budget")
    eligibility_rules: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Eligibility rules")
    allocation_rules: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Allocation rules")
    start_date: datetime = Field(..., description="Campaign start date")
    end_date: datetime = Field(..., description="Campaign end date")
    expiration_days: int = Field(default=90, ge=1, le=365, description="Days until credits expire")
    max_allocations_per_user: int = Field(default=1, ge=1, description="Max allocations per user")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    @field_validator('credit_type')
    @classmethod
    def validate_credit_type(cls, v):
        if v not in [e.value for e in CreditTypeEnum]:
            raise ValueError(f"credit_type must be one of: {[e.value for e in CreditTypeEnum]}")
        return v


class TransactionQueryRequestContract(BaseModel):
    """Contract for transaction query parameters"""
    user_id: str = Field(..., min_length=1, description="User ID")
    account_id: Optional[str] = Field(None, description="Filter by account ID")
    transaction_type: Optional[str] = Field(None, description="Filter by transaction type")
    start_date: Optional[datetime] = Field(None, description="Filter start date")
    end_date: Optional[datetime] = Field(None, description="Filter end date")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=50, ge=1, le=100, description="Items per page")


class BalanceQueryRequestContract(BaseModel):
    """Contract for balance query parameters"""
    user_id: str = Field(..., min_length=1, description="User ID")


class AccountQueryRequestContract(BaseModel):
    """Contract for account query parameters"""
    user_id: str = Field(..., min_length=1, description="User ID")
    credit_type: Optional[str] = Field(None, description="Filter by credit type")
    is_active: Optional[bool] = Field(None, description="Filter by active status")


class HealthCheckRequestContract(BaseModel):
    """Contract for health check requests (no body)"""
    pass


# ============================================================================
# Response Contracts (15 schemas)
# ============================================================================


class CreditAccountResponseContract(BaseModel):
    """Contract for credit account response"""
    account_id: str = Field(..., description="Account ID")
    user_id: str = Field(..., description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    credit_type: str = Field(..., description="Credit type")
    balance: int = Field(..., ge=0, description="Current balance")
    total_allocated: int = Field(..., ge=0, description="Lifetime allocated")
    total_consumed: int = Field(..., ge=0, description="Lifetime consumed")
    total_expired: int = Field(..., ge=0, description="Lifetime expired")
    currency: str = Field(default="CREDIT", description="Currency")
    expiration_policy: str = Field(..., description="Expiration policy")
    expiration_days: int = Field(..., description="Default expiration days")
    is_active: bool = Field(..., description="Account active status")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")

    class Config:
        from_attributes = True


class CreditAccountListResponseContract(BaseModel):
    """Contract for credit account list response"""
    accounts: List[CreditAccountResponseContract] = Field(..., description="Account list")
    total: int = Field(..., ge=0, description="Total count")


class NextExpirationContract(BaseModel):
    """Contract for next expiration info"""
    amount: int = Field(..., ge=0, description="Amount expiring")
    expires_at: datetime = Field(..., description="Expiration date")


class CreditBalanceSummaryContract(BaseModel):
    """Contract for credit balance summary response"""
    user_id: str = Field(..., description="User ID")
    total_balance: int = Field(..., ge=0, description="Total balance across all accounts")
    available_balance: int = Field(..., ge=0, description="Available (non-expired) balance")
    expiring_soon: int = Field(..., ge=0, description="Credits expiring in 7 days")
    by_type: Dict[str, int] = Field(..., description="Balance breakdown by credit type")
    next_expiration: Optional[NextExpirationContract] = Field(None, description="Next expiration info")


class AllocationResponseContract(BaseModel):
    """Contract for credit allocation response"""
    success: bool = Field(..., description="Allocation success")
    message: str = Field(..., description="Result message")
    allocation_id: Optional[str] = Field(None, description="Allocation ID")
    account_id: Optional[str] = Field(None, description="Account ID")
    amount: int = Field(..., ge=0, description="Amount allocated")
    balance_after: int = Field(..., ge=0, description="Balance after allocation")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")


class ConsumptionTransactionContract(BaseModel):
    """Contract for individual consumption transaction"""
    transaction_id: str = Field(..., description="Transaction ID")
    account_id: str = Field(..., description="Account ID")
    amount: int = Field(..., ge=0, description="Amount consumed from this account")
    credit_type: str = Field(..., description="Credit type")


class ConsumptionResponseContract(BaseModel):
    """Contract for credit consumption response"""
    success: bool = Field(..., description="Consumption success")
    message: str = Field(..., description="Result message")
    amount_consumed: int = Field(..., ge=0, description="Total amount consumed")
    balance_before: int = Field(..., ge=0, description="Balance before consumption")
    balance_after: int = Field(..., ge=0, description="Balance after consumption")
    transactions: List[ConsumptionTransactionContract] = Field(..., description="Individual transactions")


class ConsumptionPlanItemContract(BaseModel):
    """Contract for consumption plan item"""
    account_id: str = Field(..., description="Account ID")
    credit_type: str = Field(..., description="Credit type")
    amount: int = Field(..., ge=0, description="Amount to consume from this account")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")


class AvailabilityResponseContract(BaseModel):
    """Contract for credit availability check response"""
    available: bool = Field(..., description="Whether sufficient credits available")
    total_balance: int = Field(..., ge=0, description="Total balance")
    requested_amount: int = Field(..., ge=0, description="Requested amount")
    deficit: int = Field(..., ge=0, description="Shortfall if insufficient")
    consumption_plan: List[ConsumptionPlanItemContract] = Field(..., description="Planned consumption")


class TransferResponseContract(BaseModel):
    """Contract for credit transfer response"""
    success: bool = Field(..., description="Transfer success")
    message: str = Field(..., description="Result message")
    transfer_id: Optional[str] = Field(None, description="Transfer ID")
    from_transaction_id: Optional[str] = Field(None, description="Sender transaction ID")
    to_transaction_id: Optional[str] = Field(None, description="Recipient transaction ID")
    amount: int = Field(..., ge=0, description="Amount transferred")
    from_balance_after: int = Field(..., ge=0, description="Sender balance after")
    to_balance_after: int = Field(..., ge=0, description="Recipient balance after")


class CreditTransactionResponseContract(BaseModel):
    """Contract for credit transaction response"""
    transaction_id: str = Field(..., description="Transaction ID")
    account_id: str = Field(..., description="Account ID")
    user_id: str = Field(..., description="User ID")
    transaction_type: str = Field(..., description="Transaction type")
    amount: int = Field(..., description="Transaction amount")
    balance_before: int = Field(..., ge=0, description="Balance before")
    balance_after: int = Field(..., ge=0, description="Balance after")
    reference_id: Optional[str] = Field(None, description="External reference ID")
    reference_type: Optional[str] = Field(None, description="Reference type")
    description: Optional[str] = Field(None, description="Description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    expires_at: Optional[datetime] = Field(None, description="Credit expiration")
    created_at: Optional[datetime] = Field(None, description="Transaction timestamp")

    class Config:
        from_attributes = True


class TransactionListResponseContract(BaseModel):
    """Contract for transaction list response"""
    transactions: List[CreditTransactionResponseContract] = Field(..., description="Transaction list")
    total: int = Field(..., ge=0, description="Total count")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, le=100, description="Page size")


class CreditCampaignResponseContract(BaseModel):
    """Contract for credit campaign response"""
    campaign_id: str = Field(..., description="Campaign ID")
    name: str = Field(..., description="Campaign name")
    description: Optional[str] = Field(None, description="Campaign description")
    credit_type: str = Field(..., description="Credit type")
    credit_amount: int = Field(..., ge=0, description="Credits per allocation")
    total_budget: int = Field(..., ge=0, description="Total budget")
    allocated_amount: int = Field(..., ge=0, description="Allocated so far")
    remaining_budget: int = Field(..., ge=0, description="Remaining budget")
    allocation_count: int = Field(..., ge=0, description="Number of allocations")
    eligibility_rules: Optional[Dict[str, Any]] = Field(default_factory=dict)
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")
    expiration_days: int = Field(..., description="Credit expiration days")
    max_allocations_per_user: int = Field(..., description="Max allocations per user")
    is_active: bool = Field(..., description="Campaign active status")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")

    class Config:
        from_attributes = True


class CreditTypeBreakdownContract(BaseModel):
    """Contract for credit type breakdown in statistics"""
    allocated: int = Field(..., ge=0)
    consumed: int = Field(..., ge=0)
    expired: int = Field(..., ge=0)


class CreditStatisticsResponseContract(BaseModel):
    """Contract for credit statistics response"""
    period_start: datetime = Field(..., description="Period start")
    period_end: datetime = Field(..., description="Period end")
    total_allocated: int = Field(..., ge=0, description="Total allocated")
    total_consumed: int = Field(..., ge=0, description="Total consumed")
    total_expired: int = Field(..., ge=0, description="Total expired")
    utilization_rate: float = Field(..., ge=0, le=1, description="Utilization rate")
    expiration_rate: float = Field(..., ge=0, le=1, description="Expiration rate")
    by_credit_type: Dict[str, CreditTypeBreakdownContract] = Field(..., description="By type breakdown")
    active_campaigns: int = Field(..., ge=0, description="Active campaigns")
    active_accounts: int = Field(..., ge=0, description="Active accounts")


class HealthCheckResponseContract(BaseModel):
    """Contract for health check response"""
    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    port: int = Field(..., description="Service port")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="Timestamp ISO format")


class DetailedHealthCheckResponseContract(BaseModel):
    """Contract for detailed health check response"""
    service: str = Field(default="credit_service")
    status: str = Field(default="operational")
    port: int = Field(default=8229)
    version: str = Field(default="1.0.0")
    database_connected: bool
    account_client_available: bool
    subscription_client_available: bool
    expiration_job_healthy: bool
    timestamp: Optional[datetime]


class ErrorResponseContract(BaseModel):
    """Contract for error responses"""
    error: Optional[str] = Field(None, description="Error type")
    detail: str = Field(..., description="Error detail")
    timestamp: Optional[datetime] = Field(None, description="Error timestamp")


class SuccessResponseContract(BaseModel):
    """Contract for success message responses"""
    success: bool = Field(default=True)
    message: str = Field(..., description="Success message")


# ============================================================================
# CreditTestDataFactory - 35+ methods (20+ valid + 15+ invalid)
# ============================================================================


class CreditTestDataFactory:
    """
    Test data factory for credit_service - zero hardcoded data.

    All methods generate unique, valid test data suitable for testing.
    Factory methods are prefixed with make_ for valid data and
    make_invalid_ for invalid data scenarios.
    """

    # ========================================================================
    # Valid Data Generators (20+ methods)
    # ========================================================================

    @staticmethod
    def make_account_id() -> str:
        """Generate valid credit account ID"""
        return f"cred_acc_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_transaction_id() -> str:
        """Generate valid transaction ID"""
        return f"cred_txn_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_allocation_id() -> str:
        """Generate valid allocation ID"""
        return f"cred_alloc_{uuid.uuid4().hex[:20]}"

    @staticmethod
    def make_campaign_id() -> str:
        """Generate valid campaign ID"""
        return f"camp_{uuid.uuid4().hex[:20]}"

    @staticmethod
    def make_transfer_id() -> str:
        """Generate valid transfer ID"""
        return f"trf_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate valid user ID"""
        return f"user_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_organization_id() -> str:
        """Generate valid organization ID"""
        return f"org_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_billing_record_id() -> str:
        """Generate valid billing record ID"""
        return f"bill_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_past_timestamp(days_ago: int = 30) -> datetime:
        """Generate timestamp in the past"""
        return datetime.now(timezone.utc) - timedelta(days=days_ago)

    @staticmethod
    def make_future_timestamp(days_ahead: int = 90) -> datetime:
        """Generate timestamp in the future"""
        return datetime.now(timezone.utc) + timedelta(days=days_ahead)

    @staticmethod
    def make_credit_type() -> str:
        """Generate valid credit type"""
        return secrets.choice([e.value for e in CreditTypeEnum])

    @staticmethod
    def make_transaction_type() -> str:
        """Generate valid transaction type"""
        return secrets.choice([e.value for e in TransactionTypeEnum])

    @staticmethod
    def make_expiration_policy() -> str:
        """Generate valid expiration policy"""
        return ExpirationPolicyEnum.FIXED_DAYS.value

    @staticmethod
    def make_credit_amount() -> int:
        """Generate valid credit amount"""
        return secrets.randbelow(9000) + 1000  # 1000-9999

    @staticmethod
    def make_balance() -> int:
        """Generate valid balance"""
        return secrets.randbelow(50000) + 1000  # 1000-50999

    @staticmethod
    def make_campaign_budget() -> int:
        """Generate valid campaign budget"""
        return (secrets.randbelow(100) + 10) * 10000  # 100K - 1.1M

    @staticmethod
    def make_expiration_days() -> int:
        """Generate valid expiration days"""
        return secrets.choice([30, 60, 90, 180, 365])

    @staticmethod
    def make_campaign_name() -> str:
        """Generate valid campaign name"""
        prefixes = ["Holiday", "Summer", "Winter", "Spring", "New Year", "Anniversary"]
        suffixes = ["Promotion", "Bonus", "Special", "Offer", "Campaign"]
        year = 2025
        return f"{secrets.choice(prefixes)} {secrets.choice(suffixes)} {year}"

    @staticmethod
    def make_description() -> str:
        """Generate valid description"""
        descriptions = [
            "Sign-up bonus credits",
            "Referral reward",
            "Monthly subscription credits",
            "Promotional campaign allocation",
            "Customer compensation",
            "Loyalty reward",
        ]
        return secrets.choice(descriptions)

    @staticmethod
    def make_metadata() -> Dict[str, Any]:
        """Generate valid metadata"""
        return {
            "source": secrets.choice(["api", "event", "admin", "campaign"]),
            "ip_address": f"192.168.1.{secrets.randbelow(255)}",
            "user_agent": f"TestClient/1.{secrets.randbelow(10)}.{secrets.randbelow(10)}",
        }

    @staticmethod
    def make_eligibility_rules() -> Dict[str, Any]:
        """Generate valid eligibility rules"""
        return {
            "min_account_age_days": secrets.randbelow(90),
            "user_tiers": ["basic", "premium"],
            "new_users_only": secrets.choice([True, False]),
        }

    @staticmethod
    def make_allocation_rules() -> Dict[str, Any]:
        """Generate valid allocation rules"""
        return {
            "trigger": secrets.choice(["signup", "referral", "purchase", "manual"]),
            "require_verification": secrets.choice([True, False]),
        }

    @staticmethod
    def make_create_account_request(**overrides) -> CreateAccountRequestContract:
        """Generate valid create account request"""
        defaults = {
            "user_id": CreditTestDataFactory.make_user_id(),
            "organization_id": None,
            "credit_type": CreditTestDataFactory.make_credit_type(),
            "expiration_policy": CreditTestDataFactory.make_expiration_policy(),
            "expiration_days": CreditTestDataFactory.make_expiration_days(),
            "metadata": {},
        }
        defaults.update(overrides)
        return CreateAccountRequestContract(**defaults)

    @staticmethod
    def make_allocate_credits_request(**overrides) -> AllocateCreditsRequestContract:
        """Generate valid allocate credits request"""
        defaults = {
            "user_id": CreditTestDataFactory.make_user_id(),
            "credit_type": CreditTypeEnum.BONUS.value,
            "amount": CreditTestDataFactory.make_credit_amount(),
            "campaign_id": None,
            "description": CreditTestDataFactory.make_description(),
            "expires_at": CreditTestDataFactory.make_future_timestamp(90),
            "metadata": {},
        }
        defaults.update(overrides)
        return AllocateCreditsRequestContract(**defaults)

    @staticmethod
    def make_consume_credits_request(**overrides) -> ConsumeCreditsRequestContract:
        """Generate valid consume credits request"""
        defaults = {
            "user_id": CreditTestDataFactory.make_user_id(),
            "amount": CreditTestDataFactory.make_credit_amount(),
            "billing_record_id": CreditTestDataFactory.make_billing_record_id(),
            "description": "Usage billing consumption",
            "metadata": {},
        }
        defaults.update(overrides)
        return ConsumeCreditsRequestContract(**defaults)

    @staticmethod
    def make_check_availability_request(**overrides) -> CheckAvailabilityRequestContract:
        """Generate valid check availability request"""
        defaults = {
            "user_id": CreditTestDataFactory.make_user_id(),
            "amount": CreditTestDataFactory.make_credit_amount(),
        }
        defaults.update(overrides)
        return CheckAvailabilityRequestContract(**defaults)

    @staticmethod
    def make_transfer_credits_request(**overrides) -> TransferCreditsRequestContract:
        """Generate valid transfer credits request"""
        defaults = {
            "from_user_id": CreditTestDataFactory.make_user_id(),
            "to_user_id": CreditTestDataFactory.make_user_id(),
            "credit_type": CreditTypeEnum.BONUS.value,
            "amount": CreditTestDataFactory.make_credit_amount(),
            "description": "Credit transfer",
            "metadata": {},
        }
        defaults.update(overrides)
        return TransferCreditsRequestContract(**defaults)

    @staticmethod
    def make_create_campaign_request(**overrides) -> CreateCampaignRequestContract:
        """Generate valid create campaign request"""
        now = CreditTestDataFactory.make_timestamp()
        defaults = {
            "name": CreditTestDataFactory.make_campaign_name(),
            "description": "Promotional campaign for testing",
            "credit_type": CreditTypeEnum.PROMOTIONAL.value,
            "credit_amount": 1000,
            "total_budget": CreditTestDataFactory.make_campaign_budget(),
            "eligibility_rules": CreditTestDataFactory.make_eligibility_rules(),
            "allocation_rules": CreditTestDataFactory.make_allocation_rules(),
            "start_date": now,
            "end_date": now + timedelta(days=30),
            "expiration_days": 90,
            "max_allocations_per_user": 1,
            "metadata": {},
        }
        defaults.update(overrides)
        return CreateCampaignRequestContract(**defaults)

    @staticmethod
    def make_credit_account_response(**overrides) -> CreditAccountResponseContract:
        """Generate valid credit account response"""
        now = CreditTestDataFactory.make_timestamp()
        total_allocated = CreditTestDataFactory.make_balance()
        total_consumed = int(total_allocated * 0.4)
        total_expired = int(total_allocated * 0.1)
        defaults = {
            "account_id": CreditTestDataFactory.make_account_id(),
            "user_id": CreditTestDataFactory.make_user_id(),
            "organization_id": None,
            "credit_type": CreditTestDataFactory.make_credit_type(),
            "balance": total_allocated - total_consumed - total_expired,
            "total_allocated": total_allocated,
            "total_consumed": total_consumed,
            "total_expired": total_expired,
            "currency": "CREDIT",
            "expiration_policy": ExpirationPolicyEnum.FIXED_DAYS.value,
            "expiration_days": 90,
            "is_active": True,
            "metadata": {},
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return CreditAccountResponseContract(**defaults)

    @staticmethod
    def make_credit_balance_summary(**overrides) -> CreditBalanceSummaryContract:
        """Generate valid credit balance summary"""
        total_balance = CreditTestDataFactory.make_balance()
        expiring_soon = int(total_balance * 0.2)
        defaults = {
            "user_id": CreditTestDataFactory.make_user_id(),
            "total_balance": total_balance,
            "available_balance": total_balance,
            "expiring_soon": expiring_soon,
            "by_type": {
                "promotional": int(total_balance * 0.4),
                "bonus": int(total_balance * 0.3),
                "referral": int(total_balance * 0.2),
                "subscription": int(total_balance * 0.1),
            },
            "next_expiration": NextExpirationContract(
                amount=expiring_soon,
                expires_at=CreditTestDataFactory.make_future_timestamp(7)
            ),
        }
        defaults.update(overrides)
        return CreditBalanceSummaryContract(**defaults)

    @staticmethod
    def make_allocation_response(**overrides) -> AllocationResponseContract:
        """Generate valid allocation response"""
        amount = CreditTestDataFactory.make_credit_amount()
        defaults = {
            "success": True,
            "message": "Credits allocated successfully",
            "allocation_id": CreditTestDataFactory.make_allocation_id(),
            "account_id": CreditTestDataFactory.make_account_id(),
            "amount": amount,
            "balance_after": amount + 5000,
            "expires_at": CreditTestDataFactory.make_future_timestamp(90),
        }
        defaults.update(overrides)
        return AllocationResponseContract(**defaults)

    @staticmethod
    def make_consumption_response(**overrides) -> ConsumptionResponseContract:
        """Generate valid consumption response"""
        amount = CreditTestDataFactory.make_credit_amount()
        balance_before = amount + 5000
        defaults = {
            "success": True,
            "message": "Credits consumed successfully",
            "amount_consumed": amount,
            "balance_before": balance_before,
            "balance_after": balance_before - amount,
            "transactions": [
                ConsumptionTransactionContract(
                    transaction_id=CreditTestDataFactory.make_transaction_id(),
                    account_id=CreditTestDataFactory.make_account_id(),
                    amount=amount,
                    credit_type=CreditTypeEnum.PROMOTIONAL.value
                )
            ],
        }
        defaults.update(overrides)
        return ConsumptionResponseContract(**defaults)

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
    def make_invalid_credit_type() -> str:
        """Generate invalid credit type"""
        return "invalid_credit_type"

    @staticmethod
    def make_invalid_transaction_type() -> str:
        """Generate invalid transaction type"""
        return "invalid_transaction_type"

    @staticmethod
    def make_invalid_expiration_policy() -> str:
        """Generate invalid expiration policy"""
        return "invalid_policy"

    @staticmethod
    def make_invalid_amount_zero() -> int:
        """Generate invalid amount (zero)"""
        return 0

    @staticmethod
    def make_invalid_amount_negative() -> int:
        """Generate invalid amount (negative)"""
        return -100

    @staticmethod
    def make_invalid_expiration_days_zero() -> int:
        """Generate invalid expiration days (zero)"""
        return 0

    @staticmethod
    def make_invalid_expiration_days_too_large() -> int:
        """Generate invalid expiration days (too large)"""
        return 1000

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
    def make_nonexistent_account_id() -> str:
        """Generate account ID that doesn't exist"""
        return f"cred_acc_nonexistent_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_nonexistent_user_id() -> str:
        """Generate user ID that doesn't exist"""
        return f"user_nonexistent_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_nonexistent_campaign_id() -> str:
        """Generate campaign ID that doesn't exist"""
        return f"camp_nonexistent_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_invalid_date_range() -> tuple:
        """Generate invalid date range (end before start)"""
        now = datetime.now(timezone.utc)
        return (now, now - timedelta(days=30))


# ============================================================================
# Request Builders (4 builders)
# ============================================================================


class AllocateCreditsRequestBuilder:
    """Builder for allocate credits requests with fluent API"""

    def __init__(self):
        self._user_id = CreditTestDataFactory.make_user_id()
        self._credit_type = CreditTypeEnum.BONUS.value
        self._amount = CreditTestDataFactory.make_credit_amount()
        self._campaign_id = None
        self._description = None
        self._expires_at = None
        self._metadata = {}

    def with_user_id(self, value: str) -> 'AllocateCreditsRequestBuilder':
        """Set user ID"""
        self._user_id = value
        return self

    def with_credit_type(self, value: str) -> 'AllocateCreditsRequestBuilder':
        """Set credit type"""
        self._credit_type = value
        return self

    def as_promotional(self) -> 'AllocateCreditsRequestBuilder':
        """Set credit type to promotional"""
        self._credit_type = CreditTypeEnum.PROMOTIONAL.value
        return self

    def as_bonus(self) -> 'AllocateCreditsRequestBuilder':
        """Set credit type to bonus"""
        self._credit_type = CreditTypeEnum.BONUS.value
        return self

    def as_referral(self) -> 'AllocateCreditsRequestBuilder':
        """Set credit type to referral"""
        self._credit_type = CreditTypeEnum.REFERRAL.value
        return self

    def as_subscription(self) -> 'AllocateCreditsRequestBuilder':
        """Set credit type to subscription"""
        self._credit_type = CreditTypeEnum.SUBSCRIPTION.value
        return self

    def with_amount(self, value: int) -> 'AllocateCreditsRequestBuilder':
        """Set amount"""
        self._amount = value
        return self

    def with_campaign_id(self, value: str) -> 'AllocateCreditsRequestBuilder':
        """Set campaign ID"""
        self._campaign_id = value
        return self

    def with_description(self, value: str) -> 'AllocateCreditsRequestBuilder':
        """Set description"""
        self._description = value
        return self

    def expires_in_days(self, days: int) -> 'AllocateCreditsRequestBuilder':
        """Set expiration in days from now"""
        self._expires_at = CreditTestDataFactory.make_future_timestamp(days)
        return self

    def with_metadata(self, value: Dict[str, Any]) -> 'AllocateCreditsRequestBuilder':
        """Set metadata"""
        self._metadata = value
        return self

    def build(self) -> AllocateCreditsRequestContract:
        """Build the request"""
        return AllocateCreditsRequestContract(
            user_id=self._user_id,
            credit_type=self._credit_type,
            amount=self._amount,
            campaign_id=self._campaign_id,
            description=self._description,
            expires_at=self._expires_at,
            metadata=self._metadata,
        )


class ConsumeCreditsRequestBuilder:
    """Builder for consume credits requests with fluent API"""

    def __init__(self):
        self._user_id = CreditTestDataFactory.make_user_id()
        self._amount = CreditTestDataFactory.make_credit_amount()
        self._billing_record_id = None
        self._description = None
        self._metadata = {}

    def with_user_id(self, value: str) -> 'ConsumeCreditsRequestBuilder':
        """Set user ID"""
        self._user_id = value
        return self

    def with_amount(self, value: int) -> 'ConsumeCreditsRequestBuilder':
        """Set amount"""
        self._amount = value
        return self

    def with_billing_record_id(self, value: str) -> 'ConsumeCreditsRequestBuilder':
        """Set billing record ID"""
        self._billing_record_id = value
        return self

    def with_description(self, value: str) -> 'ConsumeCreditsRequestBuilder':
        """Set description"""
        self._description = value
        return self

    def with_metadata(self, value: Dict[str, Any]) -> 'ConsumeCreditsRequestBuilder':
        """Set metadata"""
        self._metadata = value
        return self

    def build(self) -> ConsumeCreditsRequestContract:
        """Build the request"""
        return ConsumeCreditsRequestContract(
            user_id=self._user_id,
            amount=self._amount,
            billing_record_id=self._billing_record_id,
            description=self._description,
            metadata=self._metadata,
        )


class CreateCampaignRequestBuilder:
    """Builder for create campaign requests with fluent API"""

    def __init__(self):
        now = CreditTestDataFactory.make_timestamp()
        self._name = CreditTestDataFactory.make_campaign_name()
        self._description = "Campaign description"
        self._credit_type = CreditTypeEnum.PROMOTIONAL.value
        self._credit_amount = 1000
        self._total_budget = 1000000
        self._eligibility_rules = {}
        self._allocation_rules = {}
        self._start_date = now
        self._end_date = now + timedelta(days=30)
        self._expiration_days = 90
        self._max_allocations_per_user = 1
        self._metadata = {}

    def with_name(self, value: str) -> 'CreateCampaignRequestBuilder':
        """Set campaign name"""
        self._name = value
        return self

    def with_description(self, value: str) -> 'CreateCampaignRequestBuilder':
        """Set description"""
        self._description = value
        return self

    def with_credit_type(self, value: str) -> 'CreateCampaignRequestBuilder':
        """Set credit type"""
        self._credit_type = value
        return self

    def with_credit_amount(self, value: int) -> 'CreateCampaignRequestBuilder':
        """Set credits per allocation"""
        self._credit_amount = value
        return self

    def with_total_budget(self, value: int) -> 'CreateCampaignRequestBuilder':
        """Set total budget"""
        self._total_budget = value
        return self

    def with_eligibility_rules(self, value: Dict[str, Any]) -> 'CreateCampaignRequestBuilder':
        """Set eligibility rules"""
        self._eligibility_rules = value
        return self

    def with_date_range(self, start: datetime, end: datetime) -> 'CreateCampaignRequestBuilder':
        """Set campaign date range"""
        self._start_date = start
        self._end_date = end
        return self

    def with_expiration_days(self, value: int) -> 'CreateCampaignRequestBuilder':
        """Set credit expiration days"""
        self._expiration_days = value
        return self

    def with_max_allocations(self, value: int) -> 'CreateCampaignRequestBuilder':
        """Set max allocations per user"""
        self._max_allocations_per_user = value
        return self

    def build(self) -> CreateCampaignRequestContract:
        """Build the request"""
        return CreateCampaignRequestContract(
            name=self._name,
            description=self._description,
            credit_type=self._credit_type,
            credit_amount=self._credit_amount,
            total_budget=self._total_budget,
            eligibility_rules=self._eligibility_rules,
            allocation_rules=self._allocation_rules,
            start_date=self._start_date,
            end_date=self._end_date,
            expiration_days=self._expiration_days,
            max_allocations_per_user=self._max_allocations_per_user,
            metadata=self._metadata,
        )


class TransferCreditsRequestBuilder:
    """Builder for transfer credits requests with fluent API"""

    def __init__(self):
        self._from_user_id = CreditTestDataFactory.make_user_id()
        self._to_user_id = CreditTestDataFactory.make_user_id()
        self._credit_type = CreditTypeEnum.BONUS.value
        self._amount = CreditTestDataFactory.make_credit_amount()
        self._description = None
        self._metadata = {}

    def from_user(self, value: str) -> 'TransferCreditsRequestBuilder':
        """Set sender user ID"""
        self._from_user_id = value
        return self

    def to_user(self, value: str) -> 'TransferCreditsRequestBuilder':
        """Set recipient user ID"""
        self._to_user_id = value
        return self

    def with_credit_type(self, value: str) -> 'TransferCreditsRequestBuilder':
        """Set credit type"""
        self._credit_type = value
        return self

    def with_amount(self, value: int) -> 'TransferCreditsRequestBuilder':
        """Set amount"""
        self._amount = value
        return self

    def with_description(self, value: str) -> 'TransferCreditsRequestBuilder':
        """Set description"""
        self._description = value
        return self

    def build(self) -> TransferCreditsRequestContract:
        """Build the request"""
        return TransferCreditsRequestContract(
            from_user_id=self._from_user_id,
            to_user_id=self._to_user_id,
            credit_type=self._credit_type,
            amount=self._amount,
            description=self._description,
            metadata=self._metadata,
        )
