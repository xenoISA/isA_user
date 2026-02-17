"""
Event Data Models for Album Service

Defines Pydantic models for events published and consumed by album_service
"""

from pydantic import BaseModel, Field
from enum import Enum

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class AlbumEventType(str, Enum):
    """
    Events published by album_service.

    Stream: album-stream
    Subjects: album.>
    """
    ALBUM_CREATED = "album.created"
    ALBUM_UPDATED = "album.updated"
    ALBUM_DELETED = "album.deleted"
    ALBUM_PHOTO_ADDED = "album.photo.added"
    ALBUM_PHOTO_REMOVED = "album.photo.removed"
    ALBUM_SYNCED = "album.synced"


class AlbumSubscribedEventType(str, Enum):
    """Events that album_service subscribes to from other services."""
    USER_DELETED = "user.deleted"
    PHOTO_VERSION_CREATED = "media.photo_version.created"


class AlbumStreamConfig:
    """Stream configuration for album_service"""
    STREAM_NAME = "album-stream"
    SUBJECTS = ["album.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "album"

from typing import Optional, List, Dict, Any
from datetime import datetime


# ====================
# Outbound Event Models (Published by album_service)
# ====================

class AlbumCreatedEventData(BaseModel):
    """Data for album.created event"""
    album_id: str = Field(..., description="Album ID")
    album_name: str = Field(..., description="Album name")
    owner_id: str = Field(..., description="Album owner user ID")
    shared_with: List[str] = Field(default_factory=list, description="List of user IDs with access")
    album_type: str = Field(default="personal", description="Album type: personal, family, shared")
    timestamp: str = Field(..., description="ISO timestamp of creation")


class AlbumPhotoAddedEventData(BaseModel):
    """Data for album.photo_added event"""
    album_id: str = Field(..., description="Album ID")
    file_id: str = Field(..., description="Photo file ID")
    added_by: str = Field(..., description="User ID who added the photo")
    photo_metadata: Optional[Dict[str, Any]] = Field(None, description="Photo metadata")
    timestamp: str = Field(..., description="ISO timestamp")


class AlbumPhotoRemovedEventData(BaseModel):
    """Data for album.photo_removed event"""
    album_id: str = Field(..., description="Album ID")
    file_id: str = Field(..., description="Photo file ID")
    removed_by: str = Field(..., description="User ID who removed the photo")
    timestamp: str = Field(..., description="ISO timestamp")


class AlbumSharedEventData(BaseModel):
    """Data for album.shared event"""
    album_id: str = Field(..., description="Album ID")
    album_name: str = Field(..., description="Album name")
    shared_by: str = Field(..., description="User ID who shared")
    shared_with: List[str] = Field(..., description="List of user IDs granted access")
    permission: str = Field(default="view", description="Permission level: view, edit, admin")
    timestamp: str = Field(..., description="ISO timestamp")


class AlbumDeletedEventData(BaseModel):
    """Data for album.deleted event"""
    album_id: str = Field(..., description="Album ID")
    deleted_by: str = Field(..., description="User ID who deleted the album")
    photo_count: int = Field(..., description="Number of photos that were in album")
    timestamp: str = Field(..., description="ISO timestamp")


class AlbumSyncedEventData(BaseModel):
    """Data for album.synced event (to frame)"""
    album_id: str = Field(..., description="Album ID")
    frame_id: str = Field(..., description="Frame/device ID")
    photo_count: int = Field(..., description="Number of photos synced")
    sync_status: str = Field(..., description="Sync status: pending, completed, failed")
    timestamp: str = Field(..., description="ISO timestamp")


# ====================
# Inbound Event Models (Consumed by album_service)
# ====================

class FileUploadedEventData(BaseModel):
    """Data from file.uploaded event"""
    file_id: str
    user_id: str
    file_name: str
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    storage_path: Optional[str] = None
    timestamp: Optional[str] = None


class FileUploadedWithAIEventData(BaseModel):
    """Data from file.uploaded.with_ai event"""
    file_id: str
    user_id: str
    file_name: str
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    ai_metadata: Optional[Dict[str, Any]] = None  # labels, faces, objects
    storage_path: Optional[str] = None
    timestamp: Optional[str] = None
    # Upload metadata may contain album_id
    metadata: Optional[Dict[str, Any]] = None


class FileDeletedEventData(BaseModel):
    """Data from file.deleted event"""
    file_id: str
    user_id: str
    file_name: Optional[str] = None
    deleted_by: Optional[str] = None
    timestamp: Optional[str] = None


class DeviceDeletedEventData(BaseModel):
    """Data from device.deleted event"""
    device_id: str
    device_name: Optional[str] = None
    user_id: Optional[str] = None
    deleted_by: Optional[str] = None
    timestamp: Optional[str] = None


class DeviceOfflineEventData(BaseModel):
    """Data from device.offline event"""
    device_id: str
    device_name: Optional[str] = None
    user_id: Optional[str] = None
    last_seen: Optional[str] = None
    timestamp: Optional[str] = None


# ====================
# MQTT Message Models (for smart frames)
# ====================

class MQTTPhotoAddedMessage(BaseModel):
    """MQTT message for photo added to album"""
    event_type: str = "photo_added"
    album_id: str
    file_id: str
    photo_metadata: Dict[str, Any]
    media_service_url: str
    download_url: Optional[str] = None
    timestamp: str


class MQTTAlbumSyncMessage(BaseModel):
    """MQTT message for full album sync to frame"""
    event_type: str = "album_sync"
    album_id: str
    frame_id: str
    photos: List[Dict[str, Any]]  # List of photo metadata
    total_photos: int
    timestamp: str


class MQTTFrameCommandMessage(BaseModel):
    """MQTT message for frame commands"""
    event_type: str = "frame_command"
    frame_id: str
    command: str  # refresh, restart, update_config
    parameters: Optional[Dict[str, Any]] = None
    timestamp: str
