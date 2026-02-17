"""
Account Service Event Models

Event data models for account lifecycle and profile management events.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class AccountEventType(str, Enum):
    """
    Events published by account_service.

    Stream: account-stream
    Subjects: account.>
    """
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_PROFILE_UPDATED = "user.profile_updated"
    USER_LOGGED_IN = "user.logged_in"
    USER_LOGGED_OUT = "user.logged_out"


class AccountSubscribedEventType(str, Enum):
    """Events that account_service subscribes to from other services."""
    pass  # No subscribed events


class AccountStreamConfig:
    """Stream configuration for account_service"""
    STREAM_NAME = "account-stream"
    SUBJECTS = ["account.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "account"


# ============================================================================
# User Account Event Models
# ============================================================================


class UserCreatedEventData(BaseModel):
    """
    Event: user.created
    Triggered when a new user account is created
    """

    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User display name")
    subscription_plan: str = Field(..., description="Initial subscription plan")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "email": "user@example.com",
                "name": "John Doe",
                "subscription_plan": "free",
                "created_at": "2025-11-14T10:00:00Z",
            }
        }


class UserProfileUpdatedEventData(BaseModel):
    """
    Event: user.profile_updated
    Triggered when user profile is updated
    """

    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="Updated email")
    name: str = Field(..., description="Updated name")
    updated_fields: List[str] = Field(
        ..., description="List of fields that were updated"
    )
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "email": "newemail@example.com",
                "name": "John Smith",
                "updated_fields": ["name", "email"],
                "updated_at": "2025-11-14T10:05:00Z",
            }
        }


class UserDeletedEventData(BaseModel):
    """
    Event: user.deleted
    Triggered when user account is deleted (soft delete)
    """

    user_id: str = Field(..., description="User ID")
    email: Optional[str] = Field(None, description="User email (if available)")
    reason: Optional[str] = Field(None, description="Deletion reason")
    deleted_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "email": "user@example.com",
                "reason": "User requested account deletion",
                "deleted_at": "2025-11-14T10:10:00Z",
            }
        }


class UserSubscriptionChangedEventData(BaseModel):
    """
    Event: user.subscription_changed
    Triggered when user subscription plan is changed
    """

    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    old_plan: str = Field(..., description="Previous subscription plan")
    new_plan: str = Field(..., description="New subscription plan")
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    changed_by: Optional[str] = Field(
        None, description="Who changed the subscription (user/admin/system)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "email": "user@example.com",
                "old_plan": "free",
                "new_plan": "pro",
                "changed_at": "2025-11-14T10:15:00Z",
                "changed_by": "user",
            }
        }


class UserStatusChangedEventData(BaseModel):
    """
    Event: user.status_changed
    Triggered when user account status is changed (activated/deactivated)
    """

    user_id: str = Field(..., description="User ID")
    email: Optional[str] = Field(None, description="User email")
    is_active: bool = Field(..., description="New active status")
    reason: Optional[str] = Field(None, description="Reason for status change")
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    changed_by: Optional[str] = Field(
        None, description="Who changed the status (admin/system)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "email": "user@example.com",
                "is_active": False,
                "reason": "Suspected fraudulent activity",
                "changed_at": "2025-11-14T10:20:00Z",
                "changed_by": "admin",
            }
        }


# ============================================================================
# Helper Functions
# ============================================================================


def create_user_created_event_data(
    user_id: str, email: str, name: str, subscription_plan: str
) -> UserCreatedEventData:
    """Create user created event data"""
    return UserCreatedEventData(
        user_id=user_id, email=email, name=name, subscription_plan=subscription_plan
    )


def create_user_profile_updated_event_data(
    user_id: str, email: str, name: str, updated_fields: List[str]
) -> UserProfileUpdatedEventData:
    """Create user profile updated event data"""
    return UserProfileUpdatedEventData(
        user_id=user_id, email=email, name=name, updated_fields=updated_fields
    )


def create_user_deleted_event_data(
    user_id: str, email: Optional[str] = None, reason: Optional[str] = None
) -> UserDeletedEventData:
    """Create user deleted event data"""
    return UserDeletedEventData(user_id=user_id, email=email, reason=reason)


def create_user_subscription_changed_event_data(
    user_id: str,
    email: str,
    old_plan: str,
    new_plan: str,
    changed_by: Optional[str] = None,
) -> UserSubscriptionChangedEventData:
    """Create user subscription changed event data"""
    return UserSubscriptionChangedEventData(
        user_id=user_id,
        email=email,
        old_plan=old_plan,
        new_plan=new_plan,
        changed_by=changed_by,
    )


def create_user_status_changed_event_data(
    user_id: str,
    is_active: bool,
    email: Optional[str] = None,
    reason: Optional[str] = None,
    changed_by: Optional[str] = None,
) -> UserStatusChangedEventData:
    """Create user status changed event data"""
    return UserStatusChangedEventData(
        user_id=user_id,
        email=email,
        is_active=is_active,
        reason=reason,
        changed_by=changed_by,
    )
