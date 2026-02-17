"""
Album Models Unit Golden Tests

Tests for album model validation and serialization logic.
Unit tests verify model-level behavior without dependencies.

Usage:
    pytest tests/unit/golden/test_album_models_golden.py -v
"""
import pytest
import json
from datetime import datetime, timezone

from microservices.album_service.models import (
    Album,
    AlbumPhoto,
    AlbumCreateRequest,
    AlbumUpdateRequest,
    AlbumAddPhotosRequest,
    AlbumRemovePhotosRequest,
    AlbumResponse,
    AlbumSummaryResponse,
    AlbumPhotoResponse,
    AlbumListResponse,
    SyncStatus,
)

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# ============================================================================
# Album Model Tests
# ============================================================================

class TestAlbumModel:
    """GOLDEN: Album model tests"""

    def test_creates_album_with_required_fields(self):
        """GOLDEN: Creates album with minimum required fields"""
        album = Album(
            album_id="album_123",
            name="Test Album",
            user_id="user_123",
        )

        assert album.album_id == "album_123"
        assert album.name == "Test Album"
        assert album.user_id == "user_123"
        assert album.photo_count == 0  # Default
        assert album.auto_sync is True  # Default
        assert album.is_family_shared is False  # Default

    def test_creates_album_with_all_fields(self):
        """GOLDEN: Creates album with all optional fields"""
        now = datetime.now(timezone.utc)
        album = Album(
            album_id="album_456",
            name="Full Album",
            description="Full description",
            user_id="user_456",
            organization_id="org_123",
            cover_photo_id="photo_cover",
            photo_count=10,
            auto_sync=False,
            sync_frames=["frame_1", "frame_2"],
            is_family_shared=True,
            sharing_resource_id="share_123",
            tags=["vacation", "beach"],
            metadata={"location": "Hawaii"},
            created_at=now,
            updated_at=now,
            last_synced_at=now,
        )

        assert album.description == "Full description"
        assert album.organization_id == "org_123"
        assert album.cover_photo_id == "photo_cover"
        assert album.photo_count == 10
        assert album.auto_sync is False
        assert album.sync_frames == ["frame_1", "frame_2"]
        assert album.is_family_shared is True
        assert album.tags == ["vacation", "beach"]

    def test_parses_json_string_arrays(self):
        """GOLDEN: Parses JSON string arrays for sync_frames and tags"""
        album = Album(
            album_id="album_json",
            name="JSON Test",
            user_id="user_json",
            sync_frames='["frame_1", "frame_2"]',
            tags='["tag1", "tag2"]',
        )

        assert album.sync_frames == ["frame_1", "frame_2"]
        assert album.tags == ["tag1", "tag2"]

    def test_parses_json_string_metadata(self):
        """GOLDEN: Parses JSON string metadata"""
        album = Album(
            album_id="album_meta",
            name="Metadata Test",
            user_id="user_meta",
            metadata='{"key": "value"}',
        )

        assert album.metadata == {"key": "value"}

    def test_handles_empty_json_arrays(self):
        """GOLDEN: Handles empty JSON array strings"""
        album = Album(
            album_id="album_empty",
            name="Empty Test",
            user_id="user_empty",
            sync_frames="",
            tags="",
        )

        assert album.sync_frames == []
        assert album.tags == []

    def test_handles_none_values_for_arrays(self):
        """GOLDEN: Handles None values for array fields"""
        album = Album(
            album_id="album_none",
            name="None Test",
            user_id="user_none",
            sync_frames=None,
            tags=None,
        )

        assert album.sync_frames == []
        assert album.tags == []


# ============================================================================
# AlbumPhoto Model Tests
# ============================================================================

class TestAlbumPhotoModel:
    """GOLDEN: AlbumPhoto model tests"""

    def test_creates_album_photo_with_required_fields(self):
        """GOLDEN: Creates album photo with minimum fields"""
        photo = AlbumPhoto(
            album_id="album_123",
            photo_id="photo_123",
            added_by="user_123",
        )

        assert photo.album_id == "album_123"
        assert photo.photo_id == "photo_123"
        assert photo.added_by == "user_123"
        assert photo.is_featured is False
        assert photo.display_order == 0

    def test_creates_album_photo_with_ai_fields(self):
        """GOLDEN: Creates album photo with AI analysis fields"""
        photo = AlbumPhoto(
            album_id="album_ai",
            photo_id="photo_ai",
            added_by="user_ai",
            ai_tags=["sunset", "beach"],
            ai_objects=["person", "water"],
            ai_scenes=["outdoor", "nature"],
            face_detection_results={"faces": [{"id": 1, "confidence": 0.95}]},
        )

        assert photo.ai_tags == ["sunset", "beach"]
        assert photo.ai_objects == ["person", "water"]
        assert photo.ai_scenes == ["outdoor", "nature"]
        assert photo.face_detection_results["faces"][0]["confidence"] == 0.95

    def test_parses_json_string_ai_fields(self):
        """GOLDEN: Parses JSON string AI fields"""
        photo = AlbumPhoto(
            album_id="album_json",
            photo_id="photo_json",
            added_by="user_json",
            ai_tags='["tag1", "tag2"]',
            ai_objects='["obj1"]',
            ai_scenes='["scene1"]',
            face_detection_results='{"faces": []}',
        )

        assert photo.ai_tags == ["tag1", "tag2"]
        assert photo.ai_objects == ["obj1"]
        assert photo.ai_scenes == ["scene1"]
        assert photo.face_detection_results == {"faces": []}


# ============================================================================
# Request Model Tests
# ============================================================================

class TestAlbumCreateRequest:
    """GOLDEN: AlbumCreateRequest model tests"""

    def test_creates_request_with_name_only(self):
        """GOLDEN: Creates request with name only"""
        request = AlbumCreateRequest(name="My Album")

        assert request.name == "My Album"
        assert request.description is None
        assert request.auto_sync is True  # Default
        assert request.sync_frames == []  # Default
        assert request.is_family_shared is False  # Default

    def test_creates_request_with_all_fields(self):
        """GOLDEN: Creates request with all fields"""
        request = AlbumCreateRequest(
            name="Full Album",
            description="Test description",
            organization_id="org_123",
            auto_sync=False,
            sync_frames=["frame_1"],
            is_family_shared=True,
            tags=["vacation"],
        )

        assert request.name == "Full Album"
        assert request.description == "Test description"
        assert request.organization_id == "org_123"
        assert request.auto_sync is False
        assert request.is_family_shared is True


class TestAlbumUpdateRequest:
    """GOLDEN: AlbumUpdateRequest model tests"""

    def test_creates_partial_update_request(self):
        """GOLDEN: Creates request with partial fields"""
        request = AlbumUpdateRequest(name="New Name")

        assert request.name == "New Name"
        assert request.description is None
        assert request.cover_photo_id is None

    def test_creates_full_update_request(self):
        """GOLDEN: Creates request with all fields"""
        request = AlbumUpdateRequest(
            name="Updated",
            description="New desc",
            cover_photo_id="new_cover",
            auto_sync=False,
            sync_frames=["frame_1"],
            is_family_shared=True,
            tags=["new_tag"],
        )

        assert request.name == "Updated"
        assert request.cover_photo_id == "new_cover"
        assert request.is_family_shared is True


class TestAlbumAddPhotosRequest:
    """GOLDEN: AlbumAddPhotosRequest model tests"""

    def test_creates_request_with_photo_ids(self):
        """GOLDEN: Creates request with photo IDs list"""
        request = AlbumAddPhotosRequest(photo_ids=["photo1", "photo2", "photo3"])

        assert len(request.photo_ids) == 3
        assert "photo1" in request.photo_ids


class TestAlbumRemovePhotosRequest:
    """GOLDEN: AlbumRemovePhotosRequest model tests"""

    def test_creates_request_with_photo_ids(self):
        """GOLDEN: Creates request with photo IDs to remove"""
        request = AlbumRemovePhotosRequest(photo_ids=["photo1", "photo2"])

        assert len(request.photo_ids) == 2


# ============================================================================
# Response Model Tests
# ============================================================================

class TestAlbumResponse:
    """GOLDEN: AlbumResponse model tests"""

    def test_creates_full_response(self):
        """GOLDEN: Creates full album response"""
        now = datetime.now(timezone.utc)
        response = AlbumResponse(
            album_id="album_resp",
            name="Response Album",
            description=None,
            user_id="user_resp",
            organization_id=None,
            cover_photo_id=None,
            photo_count=5,
            auto_sync=True,
            sync_frames=[],
            is_family_shared=False,
            sharing_resource_id=None,
            tags=["test"],
            metadata={},
            created_at=now,
            updated_at=now,
            last_synced_at=None,
        )

        assert response.album_id == "album_resp"
        assert response.photo_count == 5


class TestAlbumSummaryResponse:
    """GOLDEN: AlbumSummaryResponse model tests"""

    def test_creates_summary_response(self):
        """GOLDEN: Creates album summary for list views"""
        now = datetime.now(timezone.utc)
        summary = AlbumSummaryResponse(
            album_id="album_sum",
            name="Summary Album",
            user_id="user_sum",
            cover_photo_id=None,
            photo_count=10,
            is_family_shared=True,
            created_at=now,
        )

        assert summary.album_id == "album_sum"
        assert summary.photo_count == 10
        assert summary.is_family_shared is True


class TestAlbumListResponse:
    """GOLDEN: AlbumListResponse model tests"""

    def test_creates_paginated_response(self):
        """GOLDEN: Creates paginated list response"""
        now = datetime.now(timezone.utc)
        album = AlbumSummaryResponse(
            album_id="album_1",
            name="Album 1",
            user_id="user_1",
            cover_photo_id=None,
            photo_count=5,
            is_family_shared=False,
            created_at=now,
        )

        list_response = AlbumListResponse(
            albums=[album],
            total_count=1,
            page=1,
            page_size=50,
            has_next=False,
        )

        assert len(list_response.albums) == 1
        assert list_response.page == 1
        assert list_response.has_next is False


# ============================================================================
# SyncStatus Enum Tests
# ============================================================================

class TestSyncStatusEnum:
    """GOLDEN: SyncStatus enum tests"""

    def test_sync_status_values(self):
        """GOLDEN: SyncStatus has correct values"""
        assert SyncStatus.PENDING.value == "pending"
        assert SyncStatus.IN_PROGRESS.value == "in_progress"
        assert SyncStatus.COMPLETED.value == "completed"
        assert SyncStatus.FAILED.value == "failed"
        assert SyncStatus.CANCELLED.value == "cancelled"

    def test_sync_status_is_string_enum(self):
        """GOLDEN: SyncStatus is a string enum"""
        assert isinstance(SyncStatus.PENDING, str)
        assert SyncStatus.PENDING == "pending"
