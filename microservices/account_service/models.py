"""
Account Service Models

Independent models for account management microservice.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import datetime
import json

# Internal microservice models
from enum import Enum

class SubscriptionStatus(str, Enum):
    """Subscription status enumeration"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    PRO = "pro"
    ACTIVE = "active"

class User(BaseModel):
    """User model for account service"""
    user_id: str
    auth0_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    subscription_status: SubscriptionStatus = SubscriptionStatus.FREE
    credits_remaining: float = 1000.0
    credits_total: float = 1000.0
    is_active: bool = True
    preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @field_validator('preferences', mode='before')
    @classmethod
    def parse_preferences(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v) if v else {}
            except json.JSONDecodeError:
                return {}
        return v if v is not None else {}
    
    class Config:
        from_attributes = True

# Account Service Specific Request Models

class AccountEnsureRequest(BaseModel):
    """Account ensure request - extends UserEnsureRequest"""
    auth0_id: str = Field(..., description="Auth0 user ID")
    email: EmailStr = Field(..., description="User email")
    name: str = Field(..., description="User name")
    subscription_plan: Optional[SubscriptionStatus] = Field(
        SubscriptionStatus.FREE, 
        description="Initial subscription plan"
    )


class AccountUpdateRequest(BaseModel):
    """Account profile update request"""
    name: Optional[str] = Field(None, description="User display name", min_length=1, max_length=100)
    email: Optional[EmailStr] = Field(None, description="User email address")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")


class AccountPreferencesRequest(BaseModel):
    """Account preferences update request"""
    timezone: Optional[str] = Field(None, description="User timezone")
    language: Optional[str] = Field(None, description="Preferred language", max_length=5)
    notification_email: Optional[bool] = Field(None, description="Email notifications enabled")
    notification_push: Optional[bool] = Field(None, description="Push notifications enabled")
    theme: Optional[str] = Field(None, description="UI theme preference", pattern="^(light|dark|auto)$")


class AccountStatusChangeRequest(BaseModel):
    """Account status change request (admin operation)"""
    is_active: bool = Field(..., description="Account active status")
    reason: Optional[str] = Field(None, description="Reason for status change", max_length=255)


# Account Service Specific Response Models

class AccountProfileResponse(BaseModel):
    """Detailed account profile response"""
    user_id: str
    auth0_id: Optional[str]
    email: Optional[str] = None
    name: Optional[str] = None
    subscription_status: SubscriptionStatus
    credits_remaining: float
    credits_total: float
    is_active: bool
    preferences: Dict[str, Any] = {}
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class AccountSummaryResponse(BaseModel):
    """Account summary response (for lists)"""
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    subscription_status: SubscriptionStatus
    is_active: bool
    created_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class AccountSearchResponse(BaseModel):
    """Account search response with pagination"""
    accounts: List[AccountSummaryResponse]
    total_count: int
    page: int
    page_size: int
    has_next: bool


class AccountStatsResponse(BaseModel):
    """Account service statistics"""
    total_accounts: int
    active_accounts: int
    inactive_accounts: int
    accounts_by_subscription: Dict[str, int]
    recent_registrations_7d: int
    recent_registrations_30d: int


# Service Status Models

class AccountServiceStatus(BaseModel):
    """Account service status response"""
    service: str = "account_service"
    status: str = "operational"
    port: int = 8201
    version: str = "1.0.0"
    database_connected: bool
    timestamp: datetime


# Query Parameter Models

class AccountListParams(BaseModel):
    """Account list query parameters"""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=100, description="Items per page")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    subscription_status: Optional[SubscriptionStatus] = Field(None, description="Filter by subscription")
    search: Optional[str] = Field(None, description="Search in name/email", max_length=100)


class AccountSearchParams(BaseModel):
    """Account search query parameters"""
    query: str = Field(..., description="Search query", min_length=1, max_length=100)
    limit: int = Field(50, ge=1, le=100, description="Maximum results")
    include_inactive: bool = Field(False, description="Include inactive accounts")


# Export all models
__all__ = [
    'User', 'SubscriptionStatus',
    'AccountEnsureRequest', 'AccountUpdateRequest', 'AccountPreferencesRequest',
    'AccountStatusChangeRequest', 'AccountProfileResponse', 'AccountSummaryResponse',
    'AccountSearchResponse', 'AccountStatsResponse', 'AccountServiceStatus',
    'AccountListParams', 'AccountSearchParams'
]