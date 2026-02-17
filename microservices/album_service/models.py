"""
Album Service Models

Independent models for album management microservice.
Handles photo albums, album photos, and smart frame sync.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum
import json


# ==================== Enumerations ====================

class SyncStatus(str, Enum):
    """Album synchronization status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ==================== Core Models ====================

class Album(BaseModel):
    """Album model"""
    album_id: str
    name: str
    description: Optional[str] = None
    user_id: str
    organization_id: Optional[str] = None
    cover_photo_id: Optional[str] = None
    photo_count: int = 0
    auto_sync: bool = True
    sync_frames: List[str] = Field(default_factory=list)
    is_family_shared: bool = False
    sharing_resource_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None

    @field_validator('sync_frames', 'tags', mode='before')
    @classmethod
    def parse_json_array(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v) if v else []
            except json.JSONDecodeError:
                return []
        return v if v is not None else []

    @field_validator('metadata', mode='before')
    @classmethod
    def parse_metadata(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v) if v else {}
            except json.JSONDecodeError:
                return {}
        return v if v is not None else {}

    class Config:
        from_attributes = True


class AlbumPhoto(BaseModel):
    """Album photo junction model"""
    album_id: str
    photo_id: str
    added_by: str
    added_at: Optional[datetime] = None
    is_featured: bool = False
    display_order: int = 0
    ai_tags: List[str] = Field(default_factory=list)
    ai_objects: List[str] = Field(default_factory=list)
    ai_scenes: List[str] = Field(default_factory=list)
    face_detection_results: Optional[Dict[str, Any]] = None

    @field_validator('ai_tags', 'ai_objects', 'ai_scenes', mode='before')
    @classmethod
    def parse_json_array(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v) if v else []
            except json.JSONDecodeError:
                return []
        return v if v is not None else []

    @field_validator('face_detection_results', mode='before')
    @classmethod
    def parse_face_detection(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v) if v else None
            except json.JSONDecodeError:
                return None
        return v

    class Config:
        from_attributes = True


class AlbumSyncStatus(BaseModel):
    """Album sync status model"""
    album_id: str
    user_id: str
    frame_id: str
    last_sync_timestamp: Optional[datetime] = None
    sync_version: int = 0
    total_photos: int = 0
    synced_photos: int = 0
    pending_photos: int = 0
    failed_photos: int = 0
    sync_status: SyncStatus = SyncStatus.PENDING
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== Request Models ====================

class AlbumCreateRequest(BaseModel):
    """Album creation request"""
    name: str = Field(..., description="Album name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Album description", max_length=1000)
    organization_id: Optional[str] = Field(None, description="Organization ID for org albums")
    auto_sync: bool = Field(True, description="Enable auto sync to frames")
    sync_frames: List[str] = Field(default_factory=list, description="Frame IDs to sync with")
    is_family_shared: bool = Field(False, description="Enable family sharing")
    tags: List[str] = Field(default_factory=list, description="Album tags")


class AlbumUpdateRequest(BaseModel):
    """Album update request"""
    name: Optional[str] = Field(None, description="Album name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Album description", max_length=1000)
    cover_photo_id: Optional[str] = Field(None, description="Cover photo file ID")
    auto_sync: Optional[bool] = Field(None, description="Enable auto sync")
    sync_frames: Optional[List[str]] = Field(None, description="Frame IDs to sync with")
    is_family_shared: Optional[bool] = Field(None, description="Enable family sharing")
    tags: Optional[List[str]] = Field(None, description="Album tags")


class AlbumAddPhotosRequest(BaseModel):
    """Add photos to album request"""
    photo_ids: List[str] = Field(..., description="Photo file IDs to add", min_length=1)


class AlbumRemovePhotosRequest(BaseModel):
    """Remove photos from album request"""
    photo_ids: List[str] = Field(..., description="Photo file IDs to remove", min_length=1)


class AlbumSyncRequest(BaseModel):
    """Album sync request"""
    frame_id: str = Field(..., description="Smart frame device ID")


# ==================== Response Models ====================

class AlbumResponse(BaseModel):
    """Album response"""
    album_id: str
    name: str
    description: Optional[str]
    user_id: str
    organization_id: Optional[str]
    cover_photo_id: Optional[str]
    photo_count: int
    auto_sync: bool
    sync_frames: List[str]
    is_family_shared: bool
    sharing_resource_id: Optional[str]
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    last_synced_at: Optional[datetime]

    class Config:
        from_attributes = True


class AlbumSummaryResponse(BaseModel):
    """Album summary response (for lists)"""
    album_id: str
    name: str
    user_id: str
    cover_photo_id: Optional[str]
    photo_count: int
    is_family_shared: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class AlbumPhotoResponse(BaseModel):
    """Album photo response"""
    album_id: str
    photo_id: str
    added_by: str
    added_at: Optional[datetime]
    is_featured: bool
    display_order: int
    ai_tags: List[str]
    ai_objects: List[str]
    ai_scenes: List[str]
    face_detection_results: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class AlbumSyncStatusResponse(BaseModel):
    """Album sync status response"""
    album_id: str
    frame_id: str
    sync_status: SyncStatus
    total_photos: int
    synced_photos: int
    pending_photos: int
    failed_photos: int
    last_sync_timestamp: Optional[datetime]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class AlbumListResponse(BaseModel):
    """Album list response with pagination"""
    albums: List[AlbumSummaryResponse]
    total_count: int
    page: int
    page_size: int
    has_next: bool


# ==================== Service Status Models ====================

class AlbumServiceStatus(BaseModel):
    """Album service status response"""
    service: str = "album_service"
    status: str = "operational"
    port: int = 8210
    version: str = "1.0.0"
    database_connected: bool
    timestamp: datetime


# ==================== Query Parameter Models ====================

class AlbumListParams(BaseModel):
    """Album list query parameters"""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=100, description="Items per page")
    organization_id: Optional[str] = Field(None, description="Filter by organization")
    is_family_shared: Optional[bool] = Field(None, description="Filter by family sharing")
    search: Optional[str] = Field(None, description="Search in name", max_length=100)


class AlbumPhotoListParams(BaseModel):
    """Album photo list query parameters"""
    limit: int = Field(50, ge=1, le=200, description="Maximum results")
    offset: int = Field(0, ge=0, description="Result offset")
    is_featured: Optional[bool] = Field(None, description="Filter by featured status")


# ==================== Export Models ====================

__all__ = [
    # Enums
    'SyncStatus',
    # Core Models
    'Album', 'AlbumPhoto', 'AlbumSyncStatus',
    # Request Models
    'AlbumCreateRequest', 'AlbumUpdateRequest', 'AlbumAddPhotosRequest',
    'AlbumRemovePhotosRequest', 'AlbumSyncRequest',
    # Response Models
    'AlbumResponse', 'AlbumSummaryResponse', 'AlbumPhotoResponse',
    'AlbumSyncStatusResponse', 'AlbumListResponse',
    # Service Models
    'AlbumServiceStatus',
    # Query Models
    'AlbumListParams', 'AlbumPhotoListParams'
]
