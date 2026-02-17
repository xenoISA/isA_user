"""
Membership Service Event Models

Event data models for membership_service.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field



# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class MembershipEventType(str, Enum):
    """
    Events published by membership_service.

    Stream: membership-stream
    Subjects: membership.>
    """
    MEMBERSHIP_CREATED = "membership.created"
    MEMBERSHIP_UPDATED = "membership.updated"
    MEMBERSHIP_CANCELLED = "membership.cancelled"
    MEMBERSHIP_EXPIRED = "membership.expired"


class MembershipSubscribedEventType(str, Enum):
    """Events that membership_service subscribes to from other services."""
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_CANCELLED = "subscription.canceled"


class MembershipStreamConfig:
    """Stream configuration for membership_service"""
    STREAM_NAME = "membership-stream"
    SUBJECTS = ["membership.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "membership"



# =============================================================================
# Event Data Models
# =============================================================================

class MembershipBaseEventData(BaseModel):
    """Base event data for membership_service events."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
