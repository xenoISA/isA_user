"""
Album Service Data Contract

Defines canonical data structures for album service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for album service test data.
"""

import uuid
import random
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================

class SyncStatusEnum(str, Enum):
    """Sync status for album-frame synchronization"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ============================================================================
# Request Contracts (Input Schemas)
# ============================================================================

class AlbumCreateRequestContract(BaseModel):
    """
    Contract: Album creation request schema

    Used for creating new albums in tests.
    Maps to album service create endpoint.
    """
    name: str = Field(..., min_length=1, max_length=255, description="Album name")
    description: Optional[str] = Field(None, max_length=1000, description="Album description")
    auto_sync: bool = Field(True, description="Enable auto-sync to frames")
    sync_frames: List[str] = Field(default_factory=list, description="Frame device IDs for auto-sync")
    is_family_shared: bool = Field(False, description="Share with family organization")
    organization_id: Optional[str] = Field(None, description="Organization ID for org albums")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Album name cannot be empty or whitespace only")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Summer Vacation 2025",
                "description": "Photos from our trip to Hawaii",
                "auto_sync": True,
                "sync_frames": ["frame_001"],
                "is_family_shared": True,
                "organization_id": None
            }
        }


class AlbumUpdateRequestContract(BaseModel):
    """
    Contract: Album update request schema

    Used for updating album properties in tests.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Album name")
    description: Optional[str] = Field(None, max_length=1000, description="Album description")
    auto_sync: Optional[bool] = Field(None, description="Enable auto-sync")
    sync_frames: Optional[List[str]] = Field(None, description="Frame device IDs")
    is_family_shared: Optional[bool] = Field(None, description="Family sharing toggle")
    cover_photo_id: Optional[str] = Field(None, description="Cover photo ID")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Album name cannot be empty or whitespace only")
        return v.strip() if v else v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Hawaii Vacation 2025",
                "is_family_shared": True
            }
        }


class PhotoInputContract(BaseModel):
    """
    Contract: Photo input for adding to album

    Contains photo reference and AI metadata.
    """
    photo_id: str = Field(..., min_length=1, description="Photo file ID from storage service")
    ai_tags: List[str] = Field(default_factory=list, description="AI-generated tags")
    ai_objects: List[str] = Field(default_factory=list, description="AI-detected objects")
    ai_scenes: List[str] = Field(default_factory=list, description="AI-classified scenes")
    face_detection_results: Optional[Dict[str, Any]] = Field(None, description="Face detection data")

    class Config:
        json_schema_extra = {
            "example": {
                "photo_id": "photo_abc123",
                "ai_tags": ["beach", "sunset", "family"],
                "ai_objects": ["palm tree", "ocean", "person"],
                "ai_scenes": ["outdoor", "landscape"]
            }
        }


class AlbumAddPhotosRequestContract(BaseModel):
    """
    Contract: Add photos to album request schema

    Used for adding multiple photos to an album.
    """
    photos: List[PhotoInputContract] = Field(..., min_length=1, max_length=100, description="Photos to add")

    class Config:
        json_schema_extra = {
            "example": {
                "photos": [
                    {
                        "photo_id": "photo_123",
                        "ai_tags": ["beach", "sunset"],
                        "ai_objects": ["ocean", "palm tree"]
                    }
                ]
            }
        }


class AlbumRemovePhotosRequestContract(BaseModel):
    """
    Contract: Remove photos from album request schema

    Used for removing multiple photos from an album.
    """
    photo_ids: List[str] = Field(..., min_length=1, max_length=100, description="Photo IDs to remove")

    class Config:
        json_schema_extra = {
            "example": {
                "photo_ids": ["photo_123", "photo_456"]
            }
        }


class AlbumSyncRequestContract(BaseModel):
    """
    Contract: Album sync request schema

    Used for initiating album sync to a smart frame.
    """
    frame_id: str = Field(..., min_length=1, description="Target frame device ID")

    class Config:
        json_schema_extra = {
            "example": {
                "frame_id": "frame_001"
            }
        }


class AlbumListParamsContract(BaseModel):
    """
    Contract: Album list query parameters schema

    Used for listing albums with pagination and filtering.
    """
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(50, ge=1, le=100, description="Items per page (max 100)")
    organization_id: Optional[str] = Field(None, description="Filter by organization")
    is_family_shared: Optional[bool] = Field(None, description="Filter by family sharing status")

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 50,
                "organization_id": None,
                "is_family_shared": True
            }
        }


class AlbumPhotoListParamsContract(BaseModel):
    """
    Contract: Album photo list query parameters schema

    Used for listing photos within an album.
    """
    limit: int = Field(50, ge=1, le=200, description="Maximum photos to return")
    offset: int = Field(0, ge=0, description="Offset for pagination")

    class Config:
        json_schema_extra = {
            "example": {
                "limit": 50,
                "offset": 0
            }
        }


# ============================================================================
# Response Contracts (Output Schemas)
# ============================================================================

class AlbumResponseContract(BaseModel):
    """
    Contract: Album response schema

    Validates API response structure for album data.
    """
    album_id: str = Field(..., description="Album ID")
    user_id: str = Field(..., description="Owner user ID")
    name: str = Field(..., description="Album name")
    description: Optional[str] = Field(None, description="Album description")
    photo_count: int = Field(..., ge=0, description="Number of photos in album")
    cover_photo_id: Optional[str] = Field(None, description="Cover photo ID")
    auto_sync: bool = Field(..., description="Auto-sync enabled")
    sync_frames: List[str] = Field(..., description="Linked frame IDs")
    is_family_shared: bool = Field(..., description="Family sharing enabled")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    sharing_resource_id: Optional[str] = Field(None, description="Sharing resource ID")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "album_id": "album_1a2b3c4d5e6f7890",
                "user_id": "usr_abc123",
                "name": "Summer Vacation 2025",
                "description": "Hawaii trip photos",
                "photo_count": 47,
                "cover_photo_id": "photo_xyz",
                "auto_sync": True,
                "sync_frames": ["frame_001"],
                "is_family_shared": True,
                "organization_id": None,
                "sharing_resource_id": "share_123",
                "created_at": "2025-12-16T10:00:00Z",
                "updated_at": "2025-12-16T10:00:00Z"
            }
        }


class AlbumListResponseContract(BaseModel):
    """
    Contract: Album list response schema

    Validates API response structure for album list with pagination.
    """
    albums: List[AlbumResponseContract] = Field(..., description="List of albums")
    total: int = Field(..., ge=0, description="Total number of albums")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")

    class Config:
        json_schema_extra = {
            "example": {
                "albums": [],
                "total": 15,
                "page": 1,
                "page_size": 50,
                "pages": 1
            }
        }


class AlbumPhotoResponseContract(BaseModel):
    """
    Contract: Album photo response schema

    Validates API response structure for photos in album.
    """
    album_id: str = Field(..., description="Album ID")
    photo_id: str = Field(..., description="Photo file ID")
    display_order: int = Field(..., ge=0, description="Display order in album")
    is_featured: bool = Field(..., description="Featured photo flag")
    ai_tags: List[str] = Field(default_factory=list, description="AI tags")
    ai_objects: List[str] = Field(default_factory=list, description="AI detected objects")
    ai_scenes: List[str] = Field(default_factory=list, description="AI classified scenes")
    face_detection_results: Optional[Dict[str, Any]] = Field(None, description="Face detection data")
    added_at: Optional[datetime] = Field(None, description="When photo was added")
    added_by: Optional[str] = Field(None, description="User who added the photo")

    class Config:
        json_schema_extra = {
            "example": {
                "album_id": "album_1a2b3c4d5e6f7890",
                "photo_id": "photo_abc123",
                "display_order": 0,
                "is_featured": False,
                "ai_tags": ["beach", "sunset"],
                "ai_objects": ["ocean", "palm tree"],
                "ai_scenes": ["outdoor", "landscape"],
                "face_detection_results": None,
                "added_at": "2025-12-16T10:30:00Z",
                "added_by": "usr_abc123"
            }
        }


class AlbumAddPhotosResponseContract(BaseModel):
    """
    Contract: Add photos response schema

    Validates API response for photo addition operation.
    """
    success: bool = Field(..., description="Operation success")
    added_count: int = Field(..., ge=0, description="Number of photos added")
    album_id: str = Field(..., description="Album ID")
    new_photo_count: int = Field(..., ge=0, description="New total photo count")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "added_count": 2,
                "album_id": "album_1a2b3c4d5e6f7890",
                "new_photo_count": 49
            }
        }


class AlbumRemovePhotosResponseContract(BaseModel):
    """
    Contract: Remove photos response schema

    Validates API response for photo removal operation.
    """
    success: bool = Field(..., description="Operation success")
    removed_count: int = Field(..., ge=0, description="Number of photos removed")
    album_id: str = Field(..., description="Album ID")
    new_photo_count: int = Field(..., ge=0, description="New total photo count")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "removed_count": 2,
                "album_id": "album_1a2b3c4d5e6f7890",
                "new_photo_count": 47
            }
        }


class AlbumDeleteResponseContract(BaseModel):
    """
    Contract: Delete album response schema

    Validates API response for album deletion.
    """
    success: bool = Field(..., description="Operation success")
    message: str = Field(..., description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Album album_1a2b3c4d5e6f7890 deleted"
            }
        }


class AlbumSyncStatusResponseContract(BaseModel):
    """
    Contract: Album sync status response schema

    Validates API response for sync status.
    """
    album_id: str = Field(..., description="Album ID")
    frame_id: str = Field(..., description="Frame device ID")
    status: SyncStatusEnum = Field(..., description="Sync status")
    total_photos: int = Field(..., ge=0, description="Total photos to sync")
    synced_photos: int = Field(..., ge=0, description="Photos synced successfully")
    pending_photos: int = Field(..., ge=0, description="Photos pending sync")
    failed_photos: int = Field(..., ge=0, description="Photos failed to sync")
    sync_version: int = Field(..., ge=1, description="Sync version number")
    started_at: Optional[datetime] = Field(None, description="Sync start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Sync completion timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "album_id": "album_1a2b3c4d5e6f7890",
                "frame_id": "frame_001",
                "status": "IN_PROGRESS",
                "total_photos": 47,
                "synced_photos": 10,
                "pending_photos": 37,
                "failed_photos": 0,
                "sync_version": 1,
                "started_at": "2025-12-16T11:00:00Z",
                "completed_at": None
            }
        }


class AlbumServiceHealthResponseContract(BaseModel):
    """
    Contract: Album service health response schema

    Validates API response for health check.
    """
    service: str = Field(default="album_service", description="Service name")
    status: str = Field(..., pattern="^(operational|degraded|down)$", description="Service status")
    port: int = Field(..., ge=1024, le=65535, description="Service port")
    database_connected: bool = Field(..., description="Database connection status")
    timestamp: datetime = Field(..., description="Health check timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "service": "album_service",
                "status": "operational",
                "port": 8219,
                "database_connected": True,
                "timestamp": "2025-12-16T10:00:00Z"
            }
        }


# ============================================================================
# Test Data Factory
# ============================================================================

class AlbumTestDataFactory:
    """
    Factory for creating test data conforming to contracts.

    Provides methods to generate valid/invalid test data for all scenarios.
    """

    @staticmethod
    def make_album_id() -> str:
        """Generate unique test album ID"""
        return f"album_{secrets.token_hex(8)}"

    @staticmethod
    def make_user_id() -> str:
        """Generate unique test user ID"""
        return f"usr_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_photo_id() -> str:
        """Generate unique test photo ID"""
        return f"photo_{secrets.token_hex(8)}"

    @staticmethod
    def make_frame_id() -> str:
        """Generate unique test frame ID"""
        return f"frame_{secrets.token_hex(6)}"

    @staticmethod
    def make_organization_id() -> str:
        """Generate unique test organization ID"""
        return f"org_{secrets.token_hex(8)}"

    @staticmethod
    def make_album_name() -> str:
        """Generate random album name"""
        themes = ["Vacation", "Birthday", "Wedding", "Holiday", "Summer", "Trip", "Memories"]
        years = ["2024", "2025"]
        locations = ["Hawaii", "Paris", "Tokyo", "Beach", "Mountains", "City"]
        return f"{random.choice(themes)} {random.choice(locations)} {random.choice(years)}"

    @staticmethod
    def make_album_description() -> str:
        """Generate random album description"""
        descriptions = [
            "Photos from our amazing trip",
            "Memorable moments with family",
            "Beautiful scenery and landscapes",
            "Special occasions and celebrations",
            "Adventures and explorations"
        ]
        return random.choice(descriptions)

    @staticmethod
    def make_ai_tags() -> List[str]:
        """Generate random AI tags"""
        all_tags = ["beach", "sunset", "family", "nature", "city", "food", "portrait",
                    "landscape", "travel", "celebration", "outdoor", "indoor", "night", "day"]
        return random.sample(all_tags, random.randint(2, 5))

    @staticmethod
    def make_ai_objects() -> List[str]:
        """Generate random AI detected objects"""
        all_objects = ["person", "car", "tree", "building", "dog", "cat", "mountain",
                       "ocean", "sky", "flower", "bird", "bicycle", "boat"]
        return random.sample(all_objects, random.randint(1, 4))

    @staticmethod
    def make_ai_scenes() -> List[str]:
        """Generate random AI scenes"""
        all_scenes = ["outdoor", "indoor", "landscape", "portrait", "urban", "rural",
                      "beach", "mountain", "forest", "cityscape"]
        return random.sample(all_scenes, random.randint(1, 3))

    @staticmethod
    def make_create_request(**overrides) -> AlbumCreateRequestContract:
        """
        Create valid album create request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            AlbumCreateRequestContract with valid data
        """
        defaults = {
            "name": AlbumTestDataFactory.make_album_name(),
            "description": AlbumTestDataFactory.make_album_description(),
            "auto_sync": True,
            "sync_frames": [],
            "is_family_shared": False,
            "organization_id": None
        }
        defaults.update(overrides)
        return AlbumCreateRequestContract(**defaults)

    @staticmethod
    def make_update_request(**overrides) -> AlbumUpdateRequestContract:
        """
        Create valid album update request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            AlbumUpdateRequestContract with valid data
        """
        defaults = {
            "name": AlbumTestDataFactory.make_album_name(),
            "description": AlbumTestDataFactory.make_album_description()
        }
        defaults.update(overrides)
        return AlbumUpdateRequestContract(**defaults)

    @staticmethod
    def make_photo_input(**overrides) -> PhotoInputContract:
        """
        Create valid photo input with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            PhotoInputContract with valid data
        """
        defaults = {
            "photo_id": AlbumTestDataFactory.make_photo_id(),
            "ai_tags": AlbumTestDataFactory.make_ai_tags(),
            "ai_objects": AlbumTestDataFactory.make_ai_objects(),
            "ai_scenes": AlbumTestDataFactory.make_ai_scenes(),
            "face_detection_results": None
        }
        defaults.update(overrides)
        return PhotoInputContract(**defaults)

    @staticmethod
    def make_add_photos_request(count: int = 1, **overrides) -> AlbumAddPhotosRequestContract:
        """
        Create valid add photos request with defaults.

        Args:
            count: Number of photos to include
            **overrides: Override any default fields

        Returns:
            AlbumAddPhotosRequestContract with valid data
        """
        photos = [AlbumTestDataFactory.make_photo_input() for _ in range(count)]
        defaults = {"photos": photos}
        defaults.update(overrides)
        return AlbumAddPhotosRequestContract(**defaults)

    @staticmethod
    def make_remove_photos_request(photo_ids: Optional[List[str]] = None) -> AlbumRemovePhotosRequestContract:
        """
        Create valid remove photos request.

        Args:
            photo_ids: List of photo IDs to remove (generates if None)

        Returns:
            AlbumRemovePhotosRequestContract with valid data
        """
        if photo_ids is None:
            photo_ids = [AlbumTestDataFactory.make_photo_id() for _ in range(2)]
        return AlbumRemovePhotosRequestContract(photo_ids=photo_ids)

    @staticmethod
    def make_sync_request(**overrides) -> AlbumSyncRequestContract:
        """
        Create valid sync request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            AlbumSyncRequestContract with valid data
        """
        defaults = {"frame_id": AlbumTestDataFactory.make_frame_id()}
        defaults.update(overrides)
        return AlbumSyncRequestContract(**defaults)

    @staticmethod
    def make_list_params(**overrides) -> AlbumListParamsContract:
        """
        Create valid list parameters with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            AlbumListParamsContract with valid data
        """
        defaults = {
            "page": 1,
            "page_size": 50,
            "organization_id": None,
            "is_family_shared": None
        }
        defaults.update(overrides)
        return AlbumListParamsContract(**defaults)

    @staticmethod
    def make_album_response(**overrides) -> AlbumResponseContract:
        """
        Create expected album response for assertions.

        Used in tests to validate API responses match contract.
        """
        defaults = {
            "album_id": AlbumTestDataFactory.make_album_id(),
            "user_id": AlbumTestDataFactory.make_user_id(),
            "name": AlbumTestDataFactory.make_album_name(),
            "description": AlbumTestDataFactory.make_album_description(),
            "photo_count": random.randint(0, 100),
            "cover_photo_id": None,
            "auto_sync": True,
            "sync_frames": [],
            "is_family_shared": False,
            "organization_id": None,
            "sharing_resource_id": None,
            "created_at": datetime.now(timezone.utc) - timedelta(days=30),
            "updated_at": datetime.now(timezone.utc)
        }
        defaults.update(overrides)
        return AlbumResponseContract(**defaults)

    @staticmethod
    def make_album_photo_response(**overrides) -> AlbumPhotoResponseContract:
        """
        Create expected album photo response for assertions.
        """
        defaults = {
            "album_id": AlbumTestDataFactory.make_album_id(),
            "photo_id": AlbumTestDataFactory.make_photo_id(),
            "display_order": 0,
            "is_featured": False,
            "ai_tags": AlbumTestDataFactory.make_ai_tags(),
            "ai_objects": AlbumTestDataFactory.make_ai_objects(),
            "ai_scenes": AlbumTestDataFactory.make_ai_scenes(),
            "face_detection_results": None,
            "added_at": datetime.now(timezone.utc),
            "added_by": AlbumTestDataFactory.make_user_id()
        }
        defaults.update(overrides)
        return AlbumPhotoResponseContract(**defaults)

    @staticmethod
    def make_sync_status_response(**overrides) -> AlbumSyncStatusResponseContract:
        """
        Create expected sync status response for assertions.
        """
        total = random.randint(10, 100)
        synced = random.randint(0, total)
        failed = random.randint(0, min(5, total - synced))
        defaults = {
            "album_id": AlbumTestDataFactory.make_album_id(),
            "frame_id": AlbumTestDataFactory.make_frame_id(),
            "status": SyncStatusEnum.IN_PROGRESS,
            "total_photos": total,
            "synced_photos": synced,
            "pending_photos": total - synced - failed,
            "failed_photos": failed,
            "sync_version": 1,
            "started_at": datetime.now(timezone.utc),
            "completed_at": None
        }
        defaults.update(overrides)
        return AlbumSyncStatusResponseContract(**defaults)

    @staticmethod
    def make_health_response(**overrides) -> AlbumServiceHealthResponseContract:
        """
        Create expected health response for assertions.
        """
        defaults = {
            "service": "album_service",
            "status": "operational",
            "port": 8219,
            "database_connected": True,
            "timestamp": datetime.now(timezone.utc)
        }
        defaults.update(overrides)
        return AlbumServiceHealthResponseContract(**defaults)

    # ========================================================================
    # Invalid Data Generators (for negative testing)
    # ========================================================================

    @staticmethod
    def make_invalid_create_request_empty_name() -> dict:
        """Generate create request with empty name"""
        return {
            "name": "",
            "description": "Test album"
        }

    @staticmethod
    def make_invalid_create_request_whitespace_name() -> dict:
        """Generate create request with whitespace-only name"""
        return {
            "name": "   ",
            "description": "Test album"
        }

    @staticmethod
    def make_invalid_create_request_long_name() -> dict:
        """Generate create request with name exceeding max length"""
        return {
            "name": "A" * 300,  # Exceeds 255 limit
            "description": "Test album"
        }

    @staticmethod
    def make_invalid_create_request_long_description() -> dict:
        """Generate create request with description exceeding max length"""
        return {
            "name": "Valid Album Name",
            "description": "A" * 1500  # Exceeds 1000 limit
        }

    @staticmethod
    def make_invalid_add_photos_empty() -> dict:
        """Generate add photos request with empty array"""
        return {"photos": []}

    @staticmethod
    def make_invalid_add_photos_missing_photo_id() -> dict:
        """Generate add photos request with missing photo_id"""
        return {
            "photos": [
                {"ai_tags": ["beach"]}  # Missing photo_id
            ]
        }

    @staticmethod
    def make_invalid_sync_request_empty_frame_id() -> dict:
        """Generate sync request with empty frame_id"""
        return {"frame_id": ""}

    @staticmethod
    def make_invalid_list_params_invalid_page() -> dict:
        """Generate list params with invalid page number"""
        return {
            "page": 0,  # Invalid - must be >= 1
            "page_size": 50
        }

    @staticmethod
    def make_invalid_list_params_excessive_page_size() -> dict:
        """Generate list params with excessive page size"""
        return {
            "page": 1,
            "page_size": 500  # Invalid - max is 100
        }


# ============================================================================
# Request Builders (for complex test scenarios)
# ============================================================================

class AlbumCreateRequestBuilder:
    """
    Builder pattern for creating complex album create requests.

    Example:
        request = (
            AlbumCreateRequestBuilder()
            .with_name("My Album")
            .with_description("Test description")
            .with_family_sharing(True)
            .with_frames(["frame_001", "frame_002"])
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "name": AlbumTestDataFactory.make_album_name(),
            "description": None,
            "auto_sync": True,
            "sync_frames": [],
            "is_family_shared": False,
            "organization_id": None
        }

    def with_name(self, name: str) -> "AlbumCreateRequestBuilder":
        """Set album name"""
        self._data["name"] = name
        return self

    def with_description(self, description: str) -> "AlbumCreateRequestBuilder":
        """Set album description"""
        self._data["description"] = description
        return self

    def with_auto_sync(self, enabled: bool) -> "AlbumCreateRequestBuilder":
        """Set auto-sync setting"""
        self._data["auto_sync"] = enabled
        return self

    def with_frames(self, frame_ids: List[str]) -> "AlbumCreateRequestBuilder":
        """Set sync frames"""
        self._data["sync_frames"] = frame_ids
        return self

    def with_family_sharing(self, enabled: bool) -> "AlbumCreateRequestBuilder":
        """Set family sharing"""
        self._data["is_family_shared"] = enabled
        return self

    def with_organization(self, org_id: str) -> "AlbumCreateRequestBuilder":
        """Set organization ID"""
        self._data["organization_id"] = org_id
        return self

    def build(self) -> AlbumCreateRequestContract:
        """Build the final request"""
        return AlbumCreateRequestContract(**self._data)


class AlbumAddPhotosRequestBuilder:
    """
    Builder pattern for creating add photos requests.

    Example:
        request = (
            AlbumAddPhotosRequestBuilder()
            .add_photo("photo_123", tags=["beach", "sunset"])
            .add_photo("photo_456", objects=["person", "dog"])
            .build()
        )
    """

    def __init__(self):
        self._photos: List[PhotoInputContract] = []

    def add_photo(
        self,
        photo_id: str,
        tags: Optional[List[str]] = None,
        objects: Optional[List[str]] = None,
        scenes: Optional[List[str]] = None,
        faces: Optional[Dict[str, Any]] = None
    ) -> "AlbumAddPhotosRequestBuilder":
        """Add a photo with metadata"""
        photo = PhotoInputContract(
            photo_id=photo_id,
            ai_tags=tags or [],
            ai_objects=objects or [],
            ai_scenes=scenes or [],
            face_detection_results=faces
        )
        self._photos.append(photo)
        return self

    def add_random_photos(self, count: int) -> "AlbumAddPhotosRequestBuilder":
        """Add random photos"""
        for _ in range(count):
            self._photos.append(AlbumTestDataFactory.make_photo_input())
        return self

    def build(self) -> AlbumAddPhotosRequestContract:
        """Build the final request"""
        return AlbumAddPhotosRequestContract(photos=self._photos)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "SyncStatusEnum",

    # Request Contracts
    "AlbumCreateRequestContract",
    "AlbumUpdateRequestContract",
    "PhotoInputContract",
    "AlbumAddPhotosRequestContract",
    "AlbumRemovePhotosRequestContract",
    "AlbumSyncRequestContract",
    "AlbumListParamsContract",
    "AlbumPhotoListParamsContract",

    # Response Contracts
    "AlbumResponseContract",
    "AlbumListResponseContract",
    "AlbumPhotoResponseContract",
    "AlbumAddPhotosResponseContract",
    "AlbumRemovePhotosResponseContract",
    "AlbumDeleteResponseContract",
    "AlbumSyncStatusResponseContract",
    "AlbumServiceHealthResponseContract",

    # Factory
    "AlbumTestDataFactory",

    # Builders
    "AlbumCreateRequestBuilder",
    "AlbumAddPhotosRequestBuilder",
]
