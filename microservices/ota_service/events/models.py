"""
OTA Service Event Models

Pydantic models for all events published by OTA Service
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class FirmwareUploadedEvent(BaseModel):
    """Event published when firmware is uploaded successfully"""

    firmware_id: str = Field(..., description="Unique firmware ID")
    name: str = Field(..., description="Firmware name")
    version: str = Field(..., description="Firmware version")
    device_model: str = Field(..., description="Target device model")
    file_size: int = Field(..., description="File size in bytes")
    is_security_update: bool = Field(default=False, description="Is this a security update")
    uploaded_by: str = Field(..., description="User ID who uploaded")
    timestamp: str = Field(..., description="Upload timestamp")


class CampaignCreatedEvent(BaseModel):
    """Event published when update campaign is created"""

    campaign_id: str = Field(..., description="Unique campaign ID")
    name: str = Field(..., description="Campaign name")
    firmware_id: str = Field(..., description="Firmware ID to deploy")
    firmware_version: str = Field(..., description="Firmware version")
    target_device_count: int = Field(..., description="Number of target devices")
    deployment_strategy: str = Field(..., description="Deployment strategy (staged/immediate/scheduled)")
    priority: str = Field(..., description="Campaign priority (low/normal/high/critical)")
    created_by: str = Field(..., description="User ID who created")
    timestamp: str = Field(..., description="Creation timestamp")


class CampaignStartedEvent(BaseModel):
    """Event published when update campaign is started"""

    campaign_id: str = Field(..., description="Unique campaign ID")
    name: str = Field(..., description="Campaign name")
    firmware_id: str = Field(..., description="Firmware ID being deployed")
    firmware_version: str = Field(..., description="Firmware version")
    target_device_count: int = Field(..., description="Number of target devices")
    timestamp: str = Field(..., description="Start timestamp")


class UpdateCancelledEvent(BaseModel):
    """Event published when device update is cancelled"""

    update_id: str = Field(..., description="Update ID")
    device_id: str = Field(..., description="Device ID")
    firmware_id: str = Field(..., description="Firmware ID")
    firmware_version: str = Field(..., description="Firmware version")
    campaign_id: Optional[str] = Field(None, description="Campaign ID if part of campaign")
    timestamp: str = Field(..., description="Cancellation timestamp")


class RollbackInitiatedEvent(BaseModel):
    """Event published when firmware rollback is initiated"""

    rollback_id: str = Field(..., description="Rollback ID")
    device_id: str = Field(..., description="Device ID")
    from_version: str = Field(..., description="Current firmware version")
    to_version: str = Field(..., description="Target rollback version")
    trigger: str = Field(..., description="Rollback trigger (manual/automatic)")
    timestamp: str = Field(..., description="Rollback initiation timestamp")
