"""
Auth Service Event Models

Event data models for authentication and device pairing events.
Following wallet_service pattern.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class AuthEventType(str, Enum):
    """
    Events published by auth_service.

    Stream: auth-stream
    Subjects: auth.>
    """
    DEVICE_AUTHENTICATED = "device.authenticated"
    TOKEN_GENERATED = "auth.token.generated"
    TOKEN_REFRESHED = "auth.token.refreshed"
    TOKEN_REVOKED = "auth.token.revoked"


class AuthSubscribedEventType(str, Enum):
    """Events that auth_service subscribes to from other services."""
    USER_DELETED = "user.deleted"


class AuthStreamConfig:
    """Stream configuration for auth_service"""
    STREAM_NAME = "auth-stream"
    SUBJECTS = ["auth.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "auth"



# ============================================================================
# Device Pairing Event Models
# ============================================================================

class DevicePairingTokenGeneratedEventData(BaseModel):
    """
    Event: device.pairing_token.generated
    Triggered when a pairing token is generated for a device
    """
    device_id: str = Field(..., description="Device ID")
    pairing_token: str = Field(..., description="Temporary pairing token")
    expires_at: datetime = Field(..., description="Token expiration time")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "frame_12345",
                "pairing_token": "abc123xyz789",
                "expires_at": "2025-11-11T12:05:00Z",
                "generated_at": "2025-11-11T12:00:00Z"
            }
        }


class DevicePairingTokenVerifiedEventData(BaseModel):
    """
    Event: device.pairing_token.verified
    Triggered when a pairing token is successfully verified
    """
    device_id: str = Field(..., description="Device ID")
    user_id: str = Field(..., description="User ID attempting to pair")
    pairing_token: str = Field(..., description="Verified pairing token")
    verified_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "frame_12345",
                "user_id": "user_67890",
                "pairing_token": "abc123xyz789",
                "verified_at": "2025-11-11T12:03:00Z"
            }
        }


class DevicePairingCompletedEventData(BaseModel):
    """
    Event: device.pairing.completed
    Triggered when device pairing is completed successfully
    """
    device_id: str = Field(..., description="Device ID")
    user_id: str = Field(..., description="User ID who paired the device")
    device_name: Optional[str] = Field(None, description="Device name")
    device_type: Optional[str] = Field(None, description="Device type (frame/mobile/tablet)")
    paired_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "frame_12345",
                "user_id": "user_67890",
                "device_name": "Living Room Frame",
                "device_type": "frame",
                "paired_at": "2025-11-11T12:04:00Z"
            }
        }


# ============================================================================
# Helper Functions
# ============================================================================

def create_pairing_token_generated_event_data(
    device_id: str,
    pairing_token: str,
    expires_at: datetime
) -> DevicePairingTokenGeneratedEventData:
    """Create pairing token generated event data"""
    return DevicePairingTokenGeneratedEventData(
        device_id=device_id,
        pairing_token=pairing_token,
        expires_at=expires_at
    )


def create_pairing_token_verified_event_data(
    device_id: str,
    user_id: str,
    pairing_token: str
) -> DevicePairingTokenVerifiedEventData:
    """Create pairing token verified event data"""
    return DevicePairingTokenVerifiedEventData(
        device_id=device_id,
        user_id=user_id,
        pairing_token=pairing_token
    )


def create_pairing_completed_event_data(
    device_id: str,
    user_id: str,
    device_name: Optional[str] = None,
    device_type: Optional[str] = None
) -> DevicePairingCompletedEventData:
    """Create pairing completed event data"""
    return DevicePairingCompletedEventData(
        device_id=device_id,
        user_id=user_id,
        device_name=device_name,
        device_type=device_type
    )
