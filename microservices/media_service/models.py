"""
Media Service Models

Independent models for media processing and management microservice.
Handles photo versions, metadata, playlists, rotation schedules, and caching.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum
import json


# ==================== Enumerations ====================

class PhotoVersionType(str, Enum):
    """Photo version type"""
    ORIGINAL = "original"
    AI_ENHANCED = "ai_enhanced"
    AI_STYLED = "ai_styled"
    AI_BACKGROUND_REMOVED = "ai_background_removed"
    USER_EDITED = "user_edited"


class PlaylistType(str, Enum):
    """Playlist type"""
    MANUAL = "manual"
    SMART = "smart"
    AI_CURATED = "ai_curated"


class CacheStatus(str, Enum):
    """Cache status"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    CACHED = "cached"
    FAILED = "failed"
    EXPIRED = "expired"


class ScheduleType(str, Enum):
    """Schedule type"""
    CONTINUOUS = "continuous"
    TIME_BASED = "time_based"
    EVENT_BASED = "event_based"


# ==================== Core Models ====================

class PhotoVersion(BaseModel):
    """Photo version model"""
    version_id: str
    photo_id: str
    user_id: str
    organization_id: Optional[str] = None
    version_name: str
    version_type: PhotoVersionType
    processing_mode: Optional[str] = None
    file_id: str
    cloud_url: Optional[str] = None
    local_path: Optional[str] = None
    file_size: Optional[int] = None
    processing_params: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_current: bool = False
    version_number: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator('processing_params', 'metadata', mode='before')
    @classmethod
    def parse_json_dict(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v) if v else {}
            except json.JSONDecodeError:
                return {}
        return v if v is not None else {}

    class Config:
        from_attributes = True


class PhotoMetadata(BaseModel):
    """Photo metadata model with EXIF and AI analysis"""
    file_id: str
    user_id: str
    organization_id: Optional[str] = None

    # EXIF data
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    lens_model: Optional[str] = None
    focal_length: Optional[str] = None
    aperture: Optional[str] = None
    shutter_speed: Optional[str] = None
    iso: Optional[int] = None
    flash_used: Optional[bool] = None

    # Location
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None
    photo_taken_at: Optional[datetime] = None

    # AI analysis
    ai_labels: List[str] = Field(default_factory=list)
    ai_objects: List[str] = Field(default_factory=list)
    ai_scenes: List[str] = Field(default_factory=list)
    ai_colors: List[str] = Field(default_factory=list)
    face_detection: Optional[Dict[str, Any]] = None
    text_detection: Optional[Dict[str, Any]] = None

    # Quality metrics
    quality_score: Optional[float] = None
    blur_score: Optional[float] = None
    brightness: Optional[float] = None
    contrast: Optional[float] = None

    full_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator('ai_labels', 'ai_objects', 'ai_scenes', 'ai_colors', mode='before')
    @classmethod
    def parse_json_array(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v) if v else []
            except json.JSONDecodeError:
                return []
        return v if v is not None else []

    @field_validator('face_detection', 'text_detection', 'full_metadata', mode='before')
    @classmethod
    def parse_json_dict(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v) if v else {}
            except json.JSONDecodeError:
                return {}
        return v if v is not None else {}

    class Config:
        from_attributes = True


class Playlist(BaseModel):
    """Slideshow playlist model"""
    playlist_id: str
    name: str
    description: Optional[str] = None
    user_id: str
    organization_id: Optional[str] = None
    playlist_type: PlaylistType = PlaylistType.MANUAL
    smart_criteria: Optional[Dict[str, Any]] = None
    photo_ids: List[str] = Field(default_factory=list)
    shuffle: bool = False
    loop: bool = True
    transition_duration: int = 5  # seconds
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator('smart_criteria', mode='before')
    @classmethod
    def parse_smart_criteria(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v) if v else {}
            except json.JSONDecodeError:
                return {}
        return v

    @field_validator('photo_ids', mode='before')
    @classmethod
    def parse_photo_ids(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v) if v else []
            except json.JSONDecodeError:
                return []
        return v if v is not None else []

    class Config:
        from_attributes = True


class RotationSchedule(BaseModel):
    """Photo rotation schedule model"""
    schedule_id: str
    user_id: str
    frame_id: str
    playlist_id: Optional[str] = None
    schedule_type: ScheduleType = ScheduleType.CONTINUOUS
    start_time: Optional[str] = None  # HH:MM format
    end_time: Optional[str] = None    # HH:MM format
    days_of_week: List[int] = Field(default_factory=list)  # 0-6
    rotation_interval: int = 10  # seconds
    shuffle: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator('days_of_week', mode='before')
    @classmethod
    def parse_days_of_week(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v) if v else []
            except json.JSONDecodeError:
                return []
        return v if v is not None else []

    class Config:
        from_attributes = True


class PhotoCache(BaseModel):
    """Photo cache model for smart frames"""
    cache_id: str
    user_id: str
    frame_id: str
    photo_id: str
    version_id: Optional[str] = None
    cache_status: CacheStatus = CacheStatus.PENDING
    cached_url: Optional[str] = None
    local_path: Optional[str] = None
    cache_size: Optional[int] = None
    cache_format: Optional[str] = None
    cache_quality: Optional[str] = None
    hit_count: int = 0
    last_accessed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== Request Models ====================

class PhotoVersionCreateRequest(BaseModel):
    """Photo version creation request"""
    photo_id: str = Field(..., description="Original photo ID")
    version_name: str = Field(..., description="Version name", max_length=255)
    version_type: PhotoVersionType = Field(..., description="Version type")
    processing_mode: Optional[str] = Field(None, description="Processing mode", max_length=100)
    file_id: str = Field(..., description="File ID for this version")
    processing_params: Optional[Dict[str, Any]] = Field(None, description="Processing parameters")


class PlaylistCreateRequest(BaseModel):
    """Playlist creation request"""
    name: str = Field(..., description="Playlist name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Description", max_length=1000)
    playlist_type: PlaylistType = Field(PlaylistType.MANUAL, description="Playlist type")
    photo_ids: List[str] = Field(default_factory=list, description="Photo IDs (for manual playlists)")
    smart_criteria: Optional[Dict[str, Any]] = Field(None, description="Smart selection criteria")
    shuffle: bool = Field(False, description="Shuffle photos")
    loop: bool = Field(True, description="Loop playback")
    transition_duration: int = Field(5, ge=1, le=60, description="Transition duration in seconds")


class PlaylistUpdateRequest(BaseModel):
    """Playlist update request"""
    name: Optional[str] = Field(None, description="Playlist name", max_length=255)
    description: Optional[str] = Field(None, description="Description", max_length=1000)
    photo_ids: Optional[List[str]] = Field(None, description="Photo IDs")
    smart_criteria: Optional[Dict[str, Any]] = Field(None, description="Smart criteria")
    shuffle: Optional[bool] = Field(None, description="Shuffle")
    loop: Optional[bool] = Field(None, description="Loop")
    transition_duration: Optional[int] = Field(None, ge=1, le=60, description="Transition duration")


class RotationScheduleCreateRequest(BaseModel):
    """Rotation schedule creation request"""
    frame_id: str = Field(..., description="Smart frame device ID")
    playlist_id: str = Field(..., description="Playlist ID")
    schedule_type: ScheduleType = Field(ScheduleType.CONTINUOUS, description="Schedule type")
    start_time: Optional[str] = Field(None, description="Start time (HH:MM)")
    end_time: Optional[str] = Field(None, description="End time (HH:MM)")
    days_of_week: List[int] = Field(default_factory=list, description="Days of week (0-6)")
    rotation_interval: int = Field(10, ge=1, description="Rotation interval in seconds")
    shuffle: bool = Field(False, description="Shuffle photos")


class PhotoMetadataUpdateRequest(BaseModel):
    """Photo metadata update request"""
    ai_labels: Optional[List[str]] = None
    ai_objects: Optional[List[str]] = None
    ai_scenes: Optional[List[str]] = None
    ai_colors: Optional[List[str]] = None
    face_detection: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = None


# ==================== Response Models ====================

class PhotoVersionResponse(BaseModel):
    """Photo version response"""
    version_id: str
    photo_id: str
    user_id: str
    version_name: str
    version_type: PhotoVersionType
    file_id: str
    cloud_url: Optional[str]
    file_size: Optional[int]
    is_current: bool
    version_number: int
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class PhotoMetadataResponse(BaseModel):
    """Photo metadata response"""
    file_id: str
    camera_model: Optional[str]
    location_name: Optional[str]
    photo_taken_at: Optional[datetime]
    ai_labels: List[str]
    ai_objects: List[str]
    ai_scenes: List[str]
    quality_score: Optional[float]

    class Config:
        from_attributes = True


class PlaylistResponse(BaseModel):
    """Playlist response"""
    playlist_id: str
    name: str
    description: Optional[str]
    user_id: str
    playlist_type: PlaylistType
    photo_ids: List[str]
    shuffle: bool
    loop: bool
    transition_duration: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RotationScheduleResponse(BaseModel):
    """Rotation schedule response"""
    schedule_id: str
    frame_id: str
    playlist_id: Optional[str]
    schedule_type: ScheduleType
    rotation_interval: int
    is_active: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class PhotoCacheResponse(BaseModel):
    """Photo cache response"""
    cache_id: str
    frame_id: str
    photo_id: str
    cache_status: CacheStatus
    hit_count: int
    last_accessed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ==================== Service Status Models ====================

class MediaServiceStatus(BaseModel):
    """Media service status response"""
    service: str = "media_service"
    status: str = "operational"
    port: int = 8222
    version: str = "1.0.0"
    database_connected: bool
    timestamp: datetime


# ==================== Query Parameter Models ====================

class PlaylistListParams(BaseModel):
    """Playlist list query parameters"""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=100, description="Items per page")
    playlist_type: Optional[PlaylistType] = Field(None, description="Filter by type")


# ==================== Export Models ====================

__all__ = [
    # Enums
    'PhotoVersionType', 'PlaylistType', 'CacheStatus', 'ScheduleType',
    # Core Models
    'PhotoVersion', 'PhotoMetadata', 'Playlist', 'RotationSchedule', 'PhotoCache',
    # Request Models
    'PhotoVersionCreateRequest', 'PlaylistCreateRequest', 'PlaylistUpdateRequest',
    'RotationScheduleCreateRequest', 'PhotoMetadataUpdateRequest',
    # Response Models
    'PhotoVersionResponse', 'PhotoMetadataResponse', 'PlaylistResponse',
    'RotationScheduleResponse', 'PhotoCacheResponse',
    # Service Models
    'MediaServiceStatus',
    # Query Models
    'PlaylistListParams'
]
