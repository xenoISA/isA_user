"""
Device Service Event Models

Event data models for device lifecycle and status events.
Following wallet_service pattern.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class DeviceEventType(str, Enum):
    """
    Events published by device_service.

    Stream: device-stream
    Subjects: device.>
    """
    DEVICE_REGISTERED = "device.registered"
    DEVICE_DELETED = "device.deleted"
    DEVICE_ONLINE = "device.online"
    DEVICE_OFFLINE = "device.offline"
    DEVICE_COMMAND_SENT = "device.command_sent"
    DEVICE_PAIRED = "device.paired"
    DEVICE_STATUS_CHANGED = "device.status.changed"


class DeviceSubscribedEventType(str, Enum):
    """Events that device_service subscribes to from other services."""
    USER_DELETED = "user.deleted"


class DeviceStreamConfig:
    """Stream configuration for device_service"""
    STREAM_NAME = "device-stream"
    SUBJECTS = ["device.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "device"



# ============================================================================
# Device Lifecycle Event Models
# ============================================================================

class DeviceRegisteredEventData(BaseModel):
    """
    Event: device.registered
    Triggered when a new device is registered
    """
    device_id: str = Field(..., description="Device ID")
    device_name: str = Field(..., description="Device name")
    device_type: str = Field(..., description="Device type")
    owner_id: Optional[str] = Field(None, description="Owner user ID")
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "frame_12345",
                "device_name": "Living Room Frame",
                "device_type": "SENSOR",
                "owner_id": "user_67890",
                "registered_at": "2025-11-11T12:00:00Z"
            }
        }


class DeviceStatusChangedEventData(BaseModel):
    """
    Event: device.status.changed
    Triggered when device status changes
    """
    device_id: str = Field(..., description="Device ID")
    old_status: str = Field(..., description="Previous status")
    new_status: str = Field(..., description="New status")
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    reason: Optional[str] = Field(None, description="Reason for status change")
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "frame_12345",
                "old_status": "pending",
                "new_status": "active",
                "changed_at": "2025-11-11T12:05:00Z",
                "reason": "Device pairing completed"
            }
        }


class DevicePairedEventData(BaseModel):
    """
    Event: device.paired
    Triggered when device is successfully paired with a user
    """
    device_id: str = Field(..., description="Device ID")
    user_id: str = Field(..., description="User ID")
    device_name: Optional[str] = Field(None, description="Device name")
    device_type: Optional[str] = Field(None, description="Device type")
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


class DeviceFirmwareUpdatedEventData(BaseModel):
    """
    Event: device.firmware.updated
    Triggered when device firmware is updated
    """
    device_id: str = Field(..., description="Device ID")
    old_version: str = Field(..., description="Previous firmware version")
    new_version: str = Field(..., description="New firmware version")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    update_id: Optional[str] = Field(None, description="OTA update ID")

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "frame_12345",
                "old_version": "1.0.0",
                "new_version": "1.1.0",
                "updated_at": "2025-11-11T12:10:00Z",
                "update_id": "update_abc123"
            }
        }


class DeviceDeletedEventData(BaseModel):
    """
    Event: device.deleted
    Triggered when a device is deleted/deregistered

    Subscribers:
        - location_service: Clean up device location data
        - album_service: Clean up device sync status
        - media_service: Clean up device playlists/cache
        - telemetry_service: Clean up device metrics and alert rules
        - ota_service: Cancel pending firmware updates
    """
    device_id: str = Field(..., description="Device ID")
    user_id: Optional[str] = Field(None, description="Owner user ID")
    device_type: Optional[str] = Field(None, description="Device type")
    deleted_at: datetime = Field(default_factory=datetime.utcnow)
    reason: Optional[str] = Field(None, description="Reason for deletion")

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "frame_12345",
                "user_id": "user_67890",
                "device_type": "frame",
                "deleted_at": "2025-11-11T12:15:00Z",
                "reason": "User requested removal"
            }
        }


class DeviceOfflineEventData(BaseModel):
    """
    Event: device.offline
    Triggered when a device goes offline

    Subscribers:
        - notification_service: Send offline notification to user
        - telemetry_service: Update device status metrics
    """
    device_id: str = Field(..., description="Device ID")
    user_id: Optional[str] = Field(None, description="Owner user ID")
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
    offline_duration_seconds: Optional[int] = Field(None, description="Seconds since last heartbeat")

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "frame_12345",
                "user_id": "user_67890",
                "last_seen_at": "2025-11-11T12:00:00Z",
                "offline_duration_seconds": 300
            }
        }


class DeviceOnlineEventData(BaseModel):
    """
    Event: device.online
    Triggered when a device comes back online

    Subscribers:
        - notification_service: Optionally notify user
        - telemetry_service: Update device status metrics
    """
    device_id: str = Field(..., description="Device ID")
    user_id: Optional[str] = Field(None, description="Owner user ID")
    online_at: datetime = Field(default_factory=datetime.utcnow)
    offline_duration_seconds: Optional[int] = Field(None, description="How long device was offline")

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "frame_12345",
                "user_id": "user_67890",
                "online_at": "2025-11-11T12:05:00Z",
                "offline_duration_seconds": 300
            }
        }


# ============================================================================
# Helper Functions
# ============================================================================

def create_device_registered_event_data(
    device_id: str,
    device_name: str,
    device_type: str,
    owner_id: Optional[str] = None
) -> DeviceRegisteredEventData:
    """Create device registered event data"""
    return DeviceRegisteredEventData(
        device_id=device_id,
        device_name=device_name,
        device_type=device_type,
        owner_id=owner_id
    )


def create_device_status_changed_event_data(
    device_id: str,
    old_status: str,
    new_status: str,
    reason: Optional[str] = None
) -> DeviceStatusChangedEventData:
    """Create device status changed event data"""
    return DeviceStatusChangedEventData(
        device_id=device_id,
        old_status=old_status,
        new_status=new_status,
        reason=reason
    )


def create_device_paired_event_data(
    device_id: str,
    user_id: str,
    device_name: Optional[str] = None,
    device_type: Optional[str] = None
) -> DevicePairedEventData:
    """Create device paired event data"""
    return DevicePairedEventData(
        device_id=device_id,
        user_id=user_id,
        device_name=device_name,
        device_type=device_type
    )


def create_device_firmware_updated_event_data(
    device_id: str,
    old_version: str,
    new_version: str,
    update_id: Optional[str] = None
) -> DeviceFirmwareUpdatedEventData:
    """Create device firmware updated event data"""
    return DeviceFirmwareUpdatedEventData(
        device_id=device_id,
        old_version=old_version,
        new_version=new_version,
        update_id=update_id
    )


def create_device_deleted_event_data(
    device_id: str,
    user_id: Optional[str] = None,
    device_type: Optional[str] = None,
    reason: Optional[str] = None
) -> DeviceDeletedEventData:
    """Create device deleted event data"""
    return DeviceDeletedEventData(
        device_id=device_id,
        user_id=user_id,
        device_type=device_type,
        reason=reason
    )


def create_device_offline_event_data(
    device_id: str,
    user_id: Optional[str] = None,
    offline_duration_seconds: Optional[int] = None
) -> DeviceOfflineEventData:
    """Create device offline event data"""
    return DeviceOfflineEventData(
        device_id=device_id,
        user_id=user_id,
        offline_duration_seconds=offline_duration_seconds
    )


def create_device_online_event_data(
    device_id: str,
    user_id: Optional[str] = None,
    offline_duration_seconds: Optional[int] = None
) -> DeviceOnlineEventData:
    """Create device online event data"""
    return DeviceOnlineEventData(
        device_id=device_id,
        user_id=user_id,
        offline_duration_seconds=offline_duration_seconds
    )
