"""
Media Service Data Contract

Defines canonical data structures for media service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for media service test data.

Architecture:
- Domain: docs/domain/media_service.md
- PRD: docs/prd/media_service.md
- Design: docs/design/media_service.md
- Logic Contract: tests/contracts/media/logic_contract.md
- System Contract: tests/TDD_CONTRACT.md
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Import from production models for type consistency
from microservices.media_service.models import (
    PhotoVersionType,
    PlaylistType,
    CacheStatus,
    ScheduleType,
)


# ============================================================================
# Request Contracts (Input Schemas)
# ============================================================================

class PhotoVersionCreateRequestContract(BaseModel):
    """
    Contract: Photo version creation request schema

    Aligns with PRD: E1-US1 "Create Photo Version"
    """
    photo_id: str = Field(..., min_length=1, description="Original photo ID")
    version_name: str = Field(..., min_length=1, max_length=255, description="Version name")
    version_type: PhotoVersionType = Field(..., description="Version type")
    processing_mode: Optional[str] = Field(None, max_length=100, description="Processing mode")
    file_id: str = Field(..., min_length=1, description="File ID for this version")
    processing_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Processing parameters")

    class Config:
        json_schema_extra = {
            "example": {
                "photo_id": "photo_abc123",
                "version_name": "AI Enhanced",
                "version_type": "ai_enhanced",
                "file_id": "file_xyz789",
                "processing_params": {"enhance_level": "high"}
            }
        }


class PlaylistCreateRequestContract(BaseModel):
    """
    Contract: Playlist creation request schema

    Aligns with PRD: E3-US1 "Create Manual Playlist", E3-US2 "Create Smart Playlist"
    """
    name: str = Field(..., min_length=1, max_length=255, description="Playlist name")
    description: Optional[str] = Field(None, max_length=1000, description="Description")
    playlist_type: PlaylistType = Field(PlaylistType.MANUAL, description="Playlist type")
    photo_ids: List[str] = Field(default_factory=list, description="Photo IDs (for manual)")
    smart_criteria: Optional[Dict[str, Any]] = Field(None, description="Smart selection criteria")
    shuffle: bool = Field(False, description="Shuffle photos")
    loop: bool = Field(True, description="Loop playback")
    transition_duration: int = Field(5, ge=1, le=60, description="Transition duration in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Beach Vacation 2024",
                "playlist_type": "smart",
                "smart_criteria": {
                    "ai_scenes_contains": ["beach", "ocean"],
                    "quality_score_min": 0.7
                },
                "transition_duration": 10
            }
        }


class PlaylistUpdateRequestContract(BaseModel):
    """
    Contract: Playlist update request schema

    Aligns with PRD: E3-US3 "Update Playlist"
    """
    name: Optional[str] = Field(None, max_length=255, description="Playlist name")
    description: Optional[str] = Field(None, max_length=1000, description="Description")
    photo_ids: Optional[List[str]] = Field(None, description="Photo IDs")
    smart_criteria: Optional[Dict[str, Any]] = Field(None, description="Smart criteria")
    shuffle: Optional[bool] = Field(None, description="Shuffle")
    loop: Optional[bool] = Field(None, description="Loop")
    transition_duration: Optional[int] = Field(None, ge=1, le=60, description="Transition duration")


class RotationScheduleCreateRequestContract(BaseModel):
    """
    Contract: Rotation schedule creation request schema

    Aligns with PRD: E4-US1 "Create Rotation Schedule"
    """
    frame_id: str = Field(..., min_length=1, description="Smart frame device ID")
    playlist_id: str = Field(..., min_length=1, description="Playlist ID")
    schedule_type: ScheduleType = Field(ScheduleType.CONTINUOUS, description="Schedule type")
    start_time: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$", description="Start time (HH:MM, 00:00-23:59)")
    end_time: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$", description="End time (HH:MM, 00:00-23:59)")
    days_of_week: List[int] = Field(default_factory=list, description="Days of week (0-6)")
    rotation_interval: int = Field(10, ge=1, description="Rotation interval in seconds")
    shuffle: bool = Field(False, description="Shuffle photos")

    class Config:
        json_schema_extra = {
            "example": {
                "frame_id": "frame_001",
                "playlist_id": "pl_abc123",
                "schedule_type": "time_based",
                "start_time": "08:00",
                "end_time": "22:00",
                "days_of_week": [1, 2, 3, 4, 5],
                "rotation_interval": 15
            }
        }


# ============================================================================
# Response Contracts (Output Schemas)
# ============================================================================

class PhotoVersionResponseContract(BaseModel):
    """
    Contract: Photo version response schema

    Validates API response structure for photo versions.
    """
    version_id: str = Field(..., pattern=r"^ver_[0-9a-f]+$", description="Version ID")
    photo_id: str = Field(..., description="Photo ID")
    user_id: str = Field(..., description="Owner user ID")
    version_name: str = Field(..., description="Version name")
    version_type: PhotoVersionType = Field(..., description="Version type")
    file_id: str = Field(..., description="File ID")
    cloud_url: Optional[str] = Field(None, description="Cloud storage URL")
    file_size: Optional[int] = Field(None, ge=0, description="File size in bytes")
    is_current: bool = Field(..., description="Is current version")
    version_number: int = Field(..., ge=1, description="Version number")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "version_id": "ver_abc123",
                "photo_id": "photo_xyz",
                "user_id": "user_001",
                "version_name": "AI Enhanced",
                "version_type": "ai_enhanced",
                "file_id": "file_789",
                "is_current": True,
                "version_number": 2,
                "created_at": "2025-12-11T12:00:00Z"
            }
        }


class PhotoMetadataResponseContract(BaseModel):
    """
    Contract: Photo metadata response schema

    Validates API response structure for photo metadata.
    """
    file_id: str = Field(..., description="File ID")
    camera_model: Optional[str] = Field(None, description="Camera model")
    location_name: Optional[str] = Field(None, description="Location name")
    photo_taken_at: Optional[datetime] = Field(None, description="Photo timestamp")
    ai_labels: List[str] = Field(default_factory=list, description="AI labels")
    ai_objects: List[str] = Field(default_factory=list, description="AI objects")
    ai_scenes: List[str] = Field(default_factory=list, description="AI scenes")
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Quality score")
    full_metadata: Dict[str, Any] = Field(default_factory=dict, description="Full metadata")


class PlaylistResponseContract(BaseModel):
    """
    Contract: Playlist response schema

    Validates API response structure for playlists.
    """
    playlist_id: str = Field(..., pattern=r"^pl_[0-9a-f]+$", description="Playlist ID")
    name: str = Field(..., description="Playlist name")
    description: Optional[str] = Field(None, description="Description")
    user_id: str = Field(..., description="Owner user ID")
    playlist_type: PlaylistType = Field(..., description="Playlist type")
    photo_ids: List[str] = Field(..., description="Photo IDs")
    shuffle: bool = Field(..., description="Shuffle enabled")
    loop: bool = Field(..., description="Loop enabled")
    transition_duration: int = Field(..., description="Transition duration")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class RotationScheduleResponseContract(BaseModel):
    """
    Contract: Rotation schedule response schema

    Validates API response structure for rotation schedules.
    """
    schedule_id: str = Field(..., pattern=r"^sched_[0-9a-f]+$", description="Schedule ID")
    frame_id: str = Field(..., description="Frame ID")
    playlist_id: Optional[str] = Field(None, description="Playlist ID")
    schedule_type: ScheduleType = Field(..., description="Schedule type")
    rotation_interval: int = Field(..., description="Rotation interval")
    is_active: bool = Field(..., description="Is active")
    created_at: datetime = Field(..., description="Creation timestamp")


class PhotoCacheResponseContract(BaseModel):
    """
    Contract: Photo cache response schema

    Validates API response structure for photo cache.
    """
    cache_id: str = Field(..., pattern=r"^cache_[0-9a-f]+$", description="Cache ID")
    frame_id: str = Field(..., description="Frame ID")
    photo_id: str = Field(..., description="Photo ID")
    cache_status: CacheStatus = Field(..., description="Cache status")
    hit_count: int = Field(..., ge=0, description="Hit count")
    last_accessed_at: Optional[datetime] = Field(None, description="Last access time")


# ============================================================================
# Test Data Factory
# ============================================================================

class MediaTestDataFactory:
    """
    Factory for creating test data conforming to contracts.

    Provides methods to generate valid/invalid test data for all scenarios.
    Aligns with PRD user stories and logic contract business rules.
    """

    @staticmethod
    def make_user_id() -> str:
        """Generate unique test user ID"""
        return f"user_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_photo_id() -> str:
        """Generate valid photo ID"""
        return f"photo_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_file_id() -> str:
        """Generate valid file ID"""
        return f"file_{uuid.uuid4().hex[:32]}"

    @staticmethod
    def make_version_id() -> str:
        """Generate valid version ID"""
        return f"ver_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_playlist_id() -> str:
        """Generate valid playlist ID"""
        return f"pl_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_schedule_id() -> str:
        """Generate valid schedule ID"""
        return f"sched_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_version_create_request(**overrides) -> PhotoVersionCreateRequestContract:
        """
        Create valid photo version create request with defaults.

        Aligns with PRD: E1-US1 "Create Photo Version"

        Args:
            **overrides: Override any default fields

        Returns:
            PhotoVersionCreateRequestContract with valid data

        Example:
            request = MediaTestDataFactory.make_version_create_request(
                version_type=PhotoVersionType.AI_ENHANCED,
            )
        """
        defaults = {
            "photo_id": MediaTestDataFactory.make_photo_id(),
            "version_name": f"Test Version {uuid.uuid4().hex[:6]}",
            "version_type": PhotoVersionType.AI_ENHANCED,
            "file_id": MediaTestDataFactory.make_file_id(),
            "processing_params": {"test": True, "enhance_level": "medium"},
        }
        defaults.update(overrides)
        return PhotoVersionCreateRequestContract(**defaults)

    @staticmethod
    def make_playlist_create_request(**overrides) -> PlaylistCreateRequestContract:
        """
        Create valid playlist create request with defaults.

        Aligns with PRD: E3-US1 "Create Manual Playlist"

        Args:
            **overrides: Override any default fields

        Returns:
            PlaylistCreateRequestContract with valid data
        """
        defaults = {
            "name": f"Test Playlist {uuid.uuid4().hex[:6]}",
            "description": "Test playlist for automated testing",
            "playlist_type": PlaylistType.MANUAL,
            "photo_ids": [],
            "shuffle": False,
            "loop": True,
            "transition_duration": 10,
        }
        defaults.update(overrides)
        return PlaylistCreateRequestContract(**defaults)

    @staticmethod
    def make_smart_playlist_request(**overrides) -> PlaylistCreateRequestContract:
        """
        Create smart playlist request with criteria.

        Aligns with PRD: E3-US2 "Create Smart Playlist"
        Aligns with Logic Contract: BR-M007 "Smart Playlist Auto-Population"
        """
        defaults = {
            "name": f"Smart Playlist {uuid.uuid4().hex[:6]}",
            "playlist_type": PlaylistType.SMART,
            "smart_criteria": {
                "ai_scenes_contains": ["beach"],
                "quality_score_min": 0.7,
            },
            "photo_ids": [],  # Auto-populated
            "transition_duration": 10,
        }
        defaults.update(overrides)
        return PlaylistCreateRequestContract(**defaults)

    @staticmethod
    def make_schedule_create_request(**overrides) -> RotationScheduleCreateRequestContract:
        """
        Create valid rotation schedule request with defaults.

        Aligns with PRD: E4-US1 "Create Rotation Schedule"
        """
        defaults = {
            "frame_id": f"frame_{uuid.uuid4().hex[:8]}",
            "playlist_id": MediaTestDataFactory.make_playlist_id(),
            "schedule_type": ScheduleType.CONTINUOUS,
            "rotation_interval": 10,
            "shuffle": False,
        }
        defaults.update(overrides)
        return RotationScheduleCreateRequestContract(**defaults)

    @staticmethod
    def make_time_based_schedule_request(**overrides) -> RotationScheduleCreateRequestContract:
        """
        Create time-based rotation schedule request.

        Aligns with PRD: E4-US1 AC2 "Create time-based schedule"
        """
        defaults = {
            "frame_id": f"frame_{uuid.uuid4().hex[:8]}",
            "playlist_id": MediaTestDataFactory.make_playlist_id(),
            "schedule_type": ScheduleType.TIME_BASED,
            "start_time": "08:00",
            "end_time": "22:00",
            "days_of_week": [1, 2, 3, 4, 5],  # Weekdays
            "rotation_interval": 15,
            "shuffle": False,
        }
        defaults.update(overrides)
        return RotationScheduleCreateRequestContract(**defaults)


# ============================================================================
# Request Builders (for complex test scenarios)
# ============================================================================

class PlaylistRequestBuilder:
    """
    Builder pattern for creating complex playlist requests.

    Useful for tests that need to gradually construct requests.

    Example:
        request = (
            PlaylistRequestBuilder()
            .with_name("Beach Memories")
            .as_smart_playlist()
            .with_criteria_scenes(["beach", "ocean"])
            .with_min_quality(0.8)
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "name": f"Playlist {uuid.uuid4().hex[:6]}",
            "playlist_type": PlaylistType.MANUAL,
            "photo_ids": [],
            "shuffle": False,
            "loop": True,
            "transition_duration": 10,
        }

    def with_name(self, name: str) -> "PlaylistRequestBuilder":
        """Set playlist name"""
        self._data["name"] = name
        return self

    def with_description(self, description: str) -> "PlaylistRequestBuilder":
        """Set description"""
        self._data["description"] = description
        return self

    def as_manual_playlist(self) -> "PlaylistRequestBuilder":
        """Set as manual playlist"""
        self._data["playlist_type"] = PlaylistType.MANUAL
        return self

    def as_smart_playlist(self) -> "PlaylistRequestBuilder":
        """Set as smart playlist"""
        self._data["playlist_type"] = PlaylistType.SMART
        self._data["smart_criteria"] = {}
        return self

    def as_ai_curated_playlist(self) -> "PlaylistRequestBuilder":
        """Set as AI-curated playlist"""
        self._data["playlist_type"] = PlaylistType.AI_CURATED
        return self

    def with_photos(self, photo_ids: List[str]) -> "PlaylistRequestBuilder":
        """Add photo IDs (for manual playlists)"""
        self._data["photo_ids"] = photo_ids
        return self

    def with_criteria_scenes(self, scenes: List[str]) -> "PlaylistRequestBuilder":
        """Add scene criteria (for smart playlists)"""
        if "smart_criteria" not in self._data:
            self._data["smart_criteria"] = {}
        self._data["smart_criteria"]["ai_scenes_contains"] = scenes
        return self

    def with_min_quality(self, score: float) -> "PlaylistRequestBuilder":
        """Add minimum quality score criteria"""
        if "smart_criteria" not in self._data:
            self._data["smart_criteria"] = {}
        self._data["smart_criteria"]["quality_score_min"] = score
        return self

    def with_location(self, location: str) -> "PlaylistRequestBuilder":
        """Add location criteria"""
        if "smart_criteria" not in self._data:
            self._data["smart_criteria"] = {}
        self._data["smart_criteria"]["location_contains"] = location
        return self

    def with_shuffle(self) -> "PlaylistRequestBuilder":
        """Enable shuffle"""
        self._data["shuffle"] = True
        return self

    def with_transition_duration(self, seconds: int) -> "PlaylistRequestBuilder":
        """Set transition duration"""
        self._data["transition_duration"] = seconds
        return self

    def build(self) -> PlaylistCreateRequestContract:
        """Build the final request"""
        return PlaylistCreateRequestContract(**self._data)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Request Contracts
    "PhotoVersionCreateRequestContract",
    "PlaylistCreateRequestContract",
    "PlaylistUpdateRequestContract",
    "RotationScheduleCreateRequestContract",

    # Response Contracts
    "PhotoVersionResponseContract",
    "PhotoMetadataResponseContract",
    "PlaylistResponseContract",
    "RotationScheduleResponseContract",
    "PhotoCacheResponseContract",

    # Factory
    "MediaTestDataFactory",

    # Builders
    "PlaylistRequestBuilder",
]
