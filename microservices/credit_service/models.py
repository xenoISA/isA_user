"""
Credit Service Data Models

Manages credit accounts, allocations, transactions, campaigns, and expiration policies.
Provides flexible credit management for promotional, bonus, referral, subscription, and compensation credits.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# ====================
# Enumerations
# ====================

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


# ====================
# Core Data Models
# ====================

class CreditAccount(BaseModel):
    """
    Credit account model - tracks credit balance and metadata for a user.
    Each account is specific to a credit type and has its own expiration policy.
    """
    id: Optional[int] = None
    account_id: str = Field(..., min_length=1, description="Unique account identifier")

    # Account ownership
    user_id: str = Field(..., min_length=1, max_length=50, description="User ID")
    organization_id: Optional[str] = Field(None, max_length=50, description="Organization ID")

    # Account type and balance
    credit_type: CreditTypeEnum = Field(..., description="Type of credits")
    balance: int = Field(default=0, ge=0, description="Current available balance")

    # Lifetime statistics
    total_allocated: int = Field(default=0, ge=0, description="Total credits allocated")
    total_consumed: int = Field(default=0, ge=0, description="Total credits consumed")
    total_expired: int = Field(default=0, ge=0, description="Total credits expired")

    # Currency and policy
    currency: str = Field(default="CREDIT", description="Currency type")
    expiration_policy: ExpirationPolicyEnum = Field(..., description="Expiration policy")
    expiration_days: int = Field(..., ge=1, le=365, description="Default expiration days")

    # Account status
    is_active: bool = Field(default=True, description="Account active status")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        """Validate user_id is not empty"""
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()


class CreditTransaction(BaseModel):
    """
    Credit transaction model - records all credit movements.
    Tracks allocations, consumptions, expirations, transfers, and adjustments.
    """
    id: Optional[int] = None
    transaction_id: str = Field(..., min_length=1, description="Unique transaction identifier")

    # Transaction context
    account_id: str = Field(..., min_length=1, description="Associated account ID")
    user_id: str = Field(..., min_length=1, max_length=50, description="User ID")

    # Transaction details
    transaction_type: TransactionTypeEnum = Field(..., description="Type of transaction")
    amount: int = Field(..., description="Transaction amount (positive or negative)")

    # Balance tracking
    balance_before: int = Field(..., ge=0, description="Balance before transaction")
    balance_after: int = Field(..., ge=0, description="Balance after transaction")

    # External references
    reference_id: Optional[str] = Field(None, max_length=50, description="External reference ID")
    reference_type: Optional[ReferenceTypeEnum] = Field(None, description="Reference type")

    # Description and metadata
    description: Optional[str] = Field(None, max_length=500, description="Transaction description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Expiration tracking (for allocated credits)
    expires_at: Optional[datetime] = Field(None, description="Credit expiration datetime")

    # Timestamps
    created_at: Optional[datetime] = None


class CreditAllocation(BaseModel):
    """
    Credit allocation model - tracks individual credit allocations.
    Used for campaign tracking and allocation-specific expiration management.
    """
    id: Optional[int] = None
    allocation_id: str = Field(..., min_length=1, description="Unique allocation identifier")

    # Allocation context
    account_id: str = Field(..., min_length=1, description="Associated account ID")
    user_id: str = Field(..., min_length=1, max_length=50, description="User ID")
    campaign_id: Optional[str] = Field(None, max_length=50, description="Campaign ID if applicable")

    # Allocation details
    amount: int = Field(..., gt=0, description="Allocated amount")
    remaining_balance: int = Field(..., ge=0, description="Remaining unconsumed balance")

    # Status tracking
    status: AllocationStatusEnum = Field(..., description="Allocation status")

    # Expiration
    expires_at: Optional[datetime] = Field(None, description="Expiration datetime")
    expired_at: Optional[datetime] = Field(None, description="Actual expiration timestamp")

    # Description and metadata
    description: Optional[str] = Field(None, max_length=500, description="Allocation description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreditCampaign(BaseModel):
    """
    Credit campaign model - manages promotional credit campaigns.
    Defines rules, budgets, and eligibility for credit allocations.
    """
    id: Optional[int] = None
    campaign_id: str = Field(..., min_length=1, description="Unique campaign identifier")

    # Campaign identity
    name: str = Field(..., min_length=1, max_length=100, description="Campaign name")
    description: Optional[str] = Field(None, max_length=1000, description="Campaign description")

    # Credit configuration
    credit_type: CreditTypeEnum = Field(..., description="Type of credits to allocate")
    credit_amount: int = Field(..., gt=0, description="Credits per allocation")

    # Budget tracking
    total_budget: int = Field(..., gt=0, description="Total campaign budget")
    allocated_amount: int = Field(default=0, ge=0, description="Total allocated so far")
    remaining_budget: int = Field(..., ge=0, description="Remaining budget")
    allocation_count: int = Field(default=0, ge=0, description="Number of allocations made")

    # Rules
    eligibility_rules: Dict[str, Any] = Field(default_factory=dict, description="Eligibility rules")
    allocation_rules: Dict[str, Any] = Field(default_factory=dict, description="Allocation rules")

    # Campaign period
    start_date: datetime = Field(..., description="Campaign start date")
    end_date: datetime = Field(..., description="Campaign end date")

    # Credit expiration
    expiration_days: int = Field(..., ge=1, le=365, description="Days until allocated credits expire")
    max_allocations_per_user: int = Field(default=1, ge=1, description="Max allocations per user")

    # Campaign status
    is_active: bool = Field(default=True, description="Campaign active status")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate campaign name is not empty"""
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()


# ====================
# Request Models
# ====================

class CreateAccountRequest(BaseModel):
    """Request to create a new credit account"""
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


class AllocateCreditsRequest(BaseModel):
    """Request to allocate credits to a user"""
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


class ConsumeCreditsRequest(BaseModel):
    """Request to consume credits from a user's account"""
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


class CheckAvailabilityRequest(BaseModel):
    """Request to check credit availability"""
    user_id: str = Field(..., min_length=1, max_length=50, description="User ID")
    amount: int = Field(..., gt=0, description="Amount to check")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()


class TransferCreditsRequest(BaseModel):
    """Request to transfer credits between users"""
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


class CreateCampaignRequest(BaseModel):
    """Request to create a new credit campaign"""
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


class TransactionQueryRequest(BaseModel):
    """Request to query credit transactions"""
    user_id: str = Field(..., min_length=1, description="User ID")
    account_id: Optional[str] = Field(None, description="Filter by account ID")
    transaction_type: Optional[str] = Field(None, description="Filter by transaction type")
    start_date: Optional[datetime] = Field(None, description="Filter start date")
    end_date: Optional[datetime] = Field(None, description="Filter end date")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=50, ge=1, le=100, description="Items per page")


class BalanceQueryRequest(BaseModel):
    """Request to query credit balance"""
    user_id: str = Field(..., min_length=1, description="User ID")


class AccountQueryRequest(BaseModel):
    """Request to query credit accounts"""
    user_id: str = Field(..., min_length=1, description="User ID")
    credit_type: Optional[str] = Field(None, description="Filter by credit type")
    is_active: Optional[bool] = Field(None, description="Filter by active status")


# ====================
# Response Models
# ====================

class CreditAccountResponse(BaseModel):
    """Response containing credit account information"""
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


class CreditAccountListResponse(BaseModel):
    """Response containing list of credit accounts"""
    accounts: List[CreditAccountResponse] = Field(..., description="Account list")
    total: int = Field(..., ge=0, description="Total count")


class NextExpiration(BaseModel):
    """Information about next credit expiration"""
    amount: int = Field(..., ge=0, description="Amount expiring")
    expires_at: datetime = Field(..., description="Expiration date")


class CreditBalanceSummary(BaseModel):
    """Summary of user's credit balance across all accounts"""
    user_id: str = Field(..., description="User ID")
    total_balance: int = Field(..., ge=0, description="Total balance across all accounts")
    available_balance: int = Field(..., ge=0, description="Available (non-expired) balance")
    expiring_soon: int = Field(..., ge=0, description="Credits expiring in 7 days")
    by_type: Dict[str, int] = Field(..., description="Balance breakdown by credit type")
    next_expiration: Optional[NextExpiration] = Field(None, description="Next expiration info")


class AllocationResponse(BaseModel):
    """Response from credit allocation operation"""
    success: bool = Field(..., description="Allocation success")
    message: str = Field(..., description="Result message")
    allocation_id: Optional[str] = Field(None, description="Allocation ID")
    account_id: Optional[str] = Field(None, description="Account ID")
    amount: int = Field(..., ge=0, description="Amount allocated")
    balance_after: int = Field(..., ge=0, description="Balance after allocation")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")


class ConsumptionTransaction(BaseModel):
    """Individual consumption transaction details"""
    transaction_id: str = Field(..., description="Transaction ID")
    account_id: str = Field(..., description="Account ID")
    amount: int = Field(..., ge=0, description="Amount consumed from this account")
    credit_type: str = Field(..., description="Credit type")


class ConsumptionResponse(BaseModel):
    """Response from credit consumption operation"""
    success: bool = Field(..., description="Consumption success")
    message: str = Field(..., description="Result message")
    amount_consumed: int = Field(..., ge=0, description="Total amount consumed")
    balance_before: int = Field(..., ge=0, description="Balance before consumption")
    balance_after: int = Field(..., ge=0, description="Balance after consumption")
    transactions: List[ConsumptionTransaction] = Field(..., description="Individual transactions")


class ConsumptionPlanItem(BaseModel):
    """Item in a consumption plan"""
    account_id: str = Field(..., description="Account ID")
    credit_type: str = Field(..., description="Credit type")
    amount: int = Field(..., ge=0, description="Amount to consume from this account")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")


class AvailabilityResponse(BaseModel):
    """Response from credit availability check"""
    available: bool = Field(..., description="Whether sufficient credits available")
    total_balance: int = Field(..., ge=0, description="Total balance")
    requested_amount: int = Field(..., ge=0, description="Requested amount")
    deficit: int = Field(..., ge=0, description="Shortfall if insufficient")
    consumption_plan: List[ConsumptionPlanItem] = Field(..., description="Planned consumption")


class TransferResponse(BaseModel):
    """Response from credit transfer operation"""
    success: bool = Field(..., description="Transfer success")
    message: str = Field(..., description="Result message")
    transfer_id: Optional[str] = Field(None, description="Transfer ID")
    from_transaction_id: Optional[str] = Field(None, description="Sender transaction ID")
    to_transaction_id: Optional[str] = Field(None, description="Recipient transaction ID")
    amount: int = Field(..., ge=0, description="Amount transferred")
    from_balance_after: int = Field(..., ge=0, description="Sender balance after")
    to_balance_after: int = Field(..., ge=0, description="Recipient balance after")


class CreditTransactionResponse(BaseModel):
    """Response containing credit transaction information"""
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


class TransactionListResponse(BaseModel):
    """Response containing list of credit transactions"""
    transactions: List[CreditTransactionResponse] = Field(..., description="Transaction list")
    total: int = Field(..., ge=0, description="Total count")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, le=100, description="Page size")


class CreditCampaignResponse(BaseModel):
    """Response containing credit campaign information"""
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


class CreditTypeBreakdown(BaseModel):
    """Breakdown of credit statistics by type"""
    allocated: int = Field(..., ge=0)
    consumed: int = Field(..., ge=0)
    expired: int = Field(..., ge=0)


class CreditStatisticsResponse(BaseModel):
    """Response containing credit statistics"""
    period_start: datetime = Field(..., description="Period start")
    period_end: datetime = Field(..., description="Period end")
    total_allocated: int = Field(..., ge=0, description="Total allocated")
    total_consumed: int = Field(..., ge=0, description="Total consumed")
    total_expired: int = Field(..., ge=0, description="Total expired")
    utilization_rate: float = Field(..., ge=0, le=1, description="Utilization rate")
    expiration_rate: float = Field(..., ge=0, le=1, description="Expiration rate")
    by_credit_type: Dict[str, CreditTypeBreakdown] = Field(..., description="By type breakdown")
    active_campaigns: int = Field(..., ge=0, description="Active campaigns")
    active_accounts: int = Field(..., ge=0, description="Active accounts")


# ====================
# Health & System Models
# ====================

class HealthCheckResponse(BaseModel):
    """Standard health check response"""
    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    port: int = Field(..., description="Service port")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="Timestamp ISO format")


class DetailedHealthCheckResponse(BaseModel):
    """Detailed health check with dependency status"""
    service: str = Field(default="credit_service")
    status: str = Field(default="operational")
    port: int = Field(default=8229)
    version: str = Field(default="1.0.0")
    database_connected: bool
    account_client_available: bool
    subscription_client_available: bool
    expiration_job_healthy: bool
    timestamp: Optional[datetime]


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: Optional[str] = Field(None, description="Error type")
    detail: str = Field(..., description="Error detail")
    timestamp: Optional[datetime] = Field(None, description="Error timestamp")


class SuccessResponse(BaseModel):
    """Standard success message response"""
    success: bool = Field(default=True)
    message: str = Field(..., description="Success message")
