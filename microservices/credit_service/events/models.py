"""
Credit Service Event Models

Event data models for credit lifecycle and campaign management events.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class CreditEventType(str, Enum):
    """
    Events published by credit_service.

    Stream: credit-stream
    Subjects: credit.>
    """
    CREDIT_ALLOCATED = "credit.allocated"
    CREDIT_CONSUMED = "credit.consumed"
    CREDIT_EXPIRED = "credit.expired"
    CREDIT_REFUNDED = "credit.refunded"


class CreditSubscribedEventType(str, Enum):
    """Events that credit_service subscribes to from other services."""
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_RENEWED = "subscription.renewed"


class CreditStreamConfig:
    """Stream configuration for credit_service"""
    STREAM_NAME = "credit-stream"
    SUBJECTS = ["credit.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "credit"


# ============================================================================
# Credit Lifecycle Event Models
# ============================================================================


class CreditAllocatedEventData(BaseModel):
    """
    Event: credit.allocated
    Triggered when credits are allocated to a user account
    """

    allocation_id: str = Field(..., description="Allocation record ID")
    user_id: str = Field(..., description="User receiving credits")
    credit_type: str = Field(..., description="Type of credit (bonus, subscription, referral, etc.)")
    amount: int = Field(..., description="Amount of credits allocated")
    campaign_id: Optional[str] = Field(None, description="Campaign ID if from campaign")
    expires_at: datetime = Field(..., description="Credit expiration timestamp")
    balance_after: int = Field(..., description="Account balance after allocation")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "allocation_id": "cred_alloc_abc123def456",
                "user_id": "usr_xyz789",
                "credit_type": "bonus",
                "amount": 1000,
                "campaign_id": "camp_signup2025",
                "expires_at": "2026-03-18T00:00:00Z",
                "balance_after": 2500,
                "timestamp": "2025-12-18T10:00:00Z",
            }
        }


class CreditConsumedEventData(BaseModel):
    """
    Event: credit.consumed
    Triggered when credits are consumed by a user
    """

    transaction_ids: List[str] = Field(..., description="List of transaction IDs (FIFO may use multiple)")
    user_id: str = Field(..., description="User consuming credits")
    amount: int = Field(..., description="Amount of credits consumed")
    billing_record_id: Optional[str] = Field(None, description="Associated billing record")
    balance_before: int = Field(..., description="Account balance before consumption")
    balance_after: int = Field(..., description="Account balance after consumption")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_ids": ["cred_txn_abc123", "cred_txn_def456"],
                "user_id": "usr_xyz789",
                "amount": 500,
                "billing_record_id": "bill_xyz789",
                "balance_before": 2500,
                "balance_after": 2000,
                "timestamp": "2025-12-18T11:00:00Z",
            }
        }


class CreditExpiredEventData(BaseModel):
    """
    Event: credit.expired
    Triggered when credits expire and are removed from user's balance
    """

    user_id: str = Field(..., description="User whose credits expired")
    amount: int = Field(..., description="Amount of credits expired")
    credit_type: str = Field(..., description="Type of credit that expired")
    balance_after: int = Field(..., description="Account balance after expiration")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "usr_xyz789",
                "amount": 300,
                "credit_type": "bonus",
                "balance_after": 1700,
                "timestamp": "2025-12-18T12:00:00Z",
            }
        }


class CreditTransferredEventData(BaseModel):
    """
    Event: credit.transferred
    Triggered when credits are transferred between users
    """

    transfer_id: str = Field(..., description="Transfer transaction ID")
    from_user_id: str = Field(..., description="User sending credits")
    to_user_id: str = Field(..., description="User receiving credits")
    amount: int = Field(..., description="Amount of credits transferred")
    credit_type: str = Field(..., description="Type of credit transferred")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "transfer_id": "cred_transfer_abc123",
                "from_user_id": "usr_xyz789",
                "to_user_id": "usr_abc456",
                "amount": 200,
                "credit_type": "bonus",
                "timestamp": "2025-12-18T13:00:00Z",
            }
        }


class CreditExpiringSoonEventData(BaseModel):
    """
    Event: credit.expiring_soon
    Triggered 7 days before credits expire (configurable warning period)
    """

    user_id: str = Field(..., description="User whose credits are expiring")
    amount: int = Field(..., description="Amount of credits expiring")
    expires_at: datetime = Field(..., description="Expiration timestamp")
    credit_type: str = Field(..., description="Type of credit expiring")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "usr_xyz789",
                "amount": 500,
                "expires_at": "2025-12-25T00:00:00Z",
                "credit_type": "bonus",
                "timestamp": "2025-12-18T14:00:00Z",
            }
        }


# ============================================================================
# Campaign Event Models
# ============================================================================


class CampaignBudgetExhaustedEventData(BaseModel):
    """
    Event: credit.campaign.budget_exhausted
    Triggered when a campaign's budget is fully allocated
    """

    campaign_id: str = Field(..., description="Campaign ID")
    name: str = Field(..., description="Campaign name")
    total_budget: int = Field(..., description="Total budget allocated to campaign")
    allocated_amount: int = Field(..., description="Amount allocated so far")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "campaign_id": "camp_signup2025",
                "name": "Signup Bonus 2025",
                "total_budget": 1000000,
                "allocated_amount": 1000000,
                "timestamp": "2025-12-18T15:00:00Z",
            }
        }


# ============================================================================
# Helper Functions
# ============================================================================


def create_credit_allocated_event_data(
    allocation_id: str,
    user_id: str,
    credit_type: str,
    amount: int,
    expires_at: datetime,
    balance_after: int,
    campaign_id: Optional[str] = None,
) -> CreditAllocatedEventData:
    """Create credit allocated event data"""
    return CreditAllocatedEventData(
        allocation_id=allocation_id,
        user_id=user_id,
        credit_type=credit_type,
        amount=amount,
        campaign_id=campaign_id,
        expires_at=expires_at,
        balance_after=balance_after,
    )


def create_credit_consumed_event_data(
    transaction_ids: List[str],
    user_id: str,
    amount: int,
    balance_before: int,
    balance_after: int,
    billing_record_id: Optional[str] = None,
) -> CreditConsumedEventData:
    """Create credit consumed event data"""
    return CreditConsumedEventData(
        transaction_ids=transaction_ids,
        user_id=user_id,
        amount=amount,
        billing_record_id=billing_record_id,
        balance_before=balance_before,
        balance_after=balance_after,
    )


def create_credit_expired_event_data(
    user_id: str,
    amount: int,
    credit_type: str,
    balance_after: int,
) -> CreditExpiredEventData:
    """Create credit expired event data"""
    return CreditExpiredEventData(
        user_id=user_id,
        amount=amount,
        credit_type=credit_type,
        balance_after=balance_after,
    )


def create_credit_transferred_event_data(
    transfer_id: str,
    from_user_id: str,
    to_user_id: str,
    amount: int,
    credit_type: str,
) -> CreditTransferredEventData:
    """Create credit transferred event data"""
    return CreditTransferredEventData(
        transfer_id=transfer_id,
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        amount=amount,
        credit_type=credit_type,
    )


def create_credit_expiring_soon_event_data(
    user_id: str,
    amount: int,
    expires_at: datetime,
    credit_type: str,
) -> CreditExpiringSoonEventData:
    """Create credit expiring soon event data"""
    return CreditExpiringSoonEventData(
        user_id=user_id,
        amount=amount,
        expires_at=expires_at,
        credit_type=credit_type,
    )


def create_campaign_budget_exhausted_event_data(
    campaign_id: str,
    name: str,
    total_budget: int,
    allocated_amount: int,
) -> CampaignBudgetExhaustedEventData:
    """Create campaign budget exhausted event data"""
    return CampaignBudgetExhaustedEventData(
        campaign_id=campaign_id,
        name=name,
        total_budget=total_budget,
        allocated_amount=allocated_amount,
    )
