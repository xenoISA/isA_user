"""
Event Data Models for Media Service

Defines Pydantic models for events published and consumed by media_service
"""

from pydantic import BaseModel, Field
from enum import Enum

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class MediaEventType(str, Enum):
    """
    Events published by media_service.

    Stream: media-stream
    Subjects: media.>
    """
    PHOTO_VERSION_CREATED = "media.photo_version.created"
    PHOTO_METADATA_UPDATED = "media.photo_metadata.updated"
    PLAYLIST_CREATED = "media.playlist.created"
    PLAYLIST_UPDATED = "media.playlist.updated"
    PLAYLIST_DELETED = "media.playlist.deleted"
    PHOTO_CACHED = "media.photo.cached"


class MediaSubscribedEventType(str, Enum):
    """Events that media_service subscribes to from other services."""
    FILE_UPLOADED = "file.uploaded"
    FILE_UPLOADED_WITH_AI = "file.uploaded.with_ai"


class MediaStreamConfig:
    """Stream configuration for media_service"""
    STREAM_NAME = "media-stream"
    SUBJECTS = ["media.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "media"

from typing import Optional, List, Dict, Any
from datetime import datetime


# ====================
# Outbound Event Models (Published by media_service)
# ====================

class MediaVersionCreatedEventData(BaseModel):
    """Data for media.version_created event"""
    file_id: str = Field(..., description="Original file ID")
    version_id: str = Field(..., description="Version ID")
    size_variant: str = Field(..., description="Size: thumbnail, hd, original")
    width: int = Field(..., description="Width in pixels")
    height: int = Field(..., description="Height in pixels")
    file_size: int = Field(..., description="File size in bytes")
    storage_path: str = Field(..., description="Storage path")
    timestamp: str = Field(..., description="ISO timestamp")


class MediaCacheReadyEventData(BaseModel):
    """Data for media.cache_ready event"""
    file_id: str = Field(..., description="File ID")
    frame_id: str = Field(..., description="Frame/device ID")
    cached_versions: List[str] = Field(..., description="List of cached size variants")
    cache_size: int = Field(..., description="Total cache size in bytes")
    timestamp: str = Field(..., description="ISO timestamp")


class MediaMetadataUpdatedEventData(BaseModel):
    """Data for media.metadata_updated event"""
    file_id: str = Field(..., description="File ID")
    user_id: str = Field(..., description="User ID")
    ai_labels: List[str] = Field(default_factory=list, description="AI detected labels")
    ai_scenes: List[str] = Field(default_factory=list, description="AI detected scenes")
    quality_score: Optional[float] = Field(None, description="Quality score 0-1")
    timestamp: str = Field(..., description="ISO timestamp")


class PlaylistCreatedEventData(BaseModel):
    """Data for media.playlist_created event"""
    playlist_id: str = Field(..., description="Playlist ID")
    playlist_name: str = Field(..., description="Playlist name")
    user_id: str = Field(..., description="User ID")
    photo_count: int = Field(..., description="Number of photos")
    frame_id: Optional[str] = Field(None, description="Assigned frame ID")
    timestamp: str = Field(..., description="ISO timestamp")


# ====================
# Inbound Event Models (Consumed by media_service)
# ====================

class FileUploadedEventData(BaseModel):
    """Data from file.uploaded event"""
    file_id: str
    user_id: str
    file_name: str
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    file_type: Optional[str] = None
    storage_path: Optional[str] = None
    organization_id: Optional[str] = None
    timestamp: Optional[str] = None


class FileUploadedWithAIEventData(BaseModel):
    """Data from file.uploaded.with_ai event"""
    file_id: str
    user_id: str
    file_name: str
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    chunk_id: Optional[str] = None  # Qdrant vector ID
    ai_metadata: Optional[Dict[str, Any]] = None
    download_url: Optional[str] = None
    bucket_name: Optional[str] = None
    object_name: Optional[str] = None
    storage_path: Optional[str] = None
    organization_id: Optional[str] = None
    timestamp: Optional[str] = None


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
