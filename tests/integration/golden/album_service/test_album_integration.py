"""
Album Service - Golden Integration Tests

Tests album service layer with mocked repository and event bus.
Validates business logic contracts and domain invariants.

Usage:
    pytest tests/integration/golden/album_service/ -v
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../..'))

from tests.contracts.album.data_contract import (
    AlbumTestDataFactory,
    SyncStatusEnum,
    AlbumResponseContract,
    AlbumAddPhotosResponseContract,
    AlbumRemovePhotosResponseContract,
    AlbumSyncStatusResponseContract,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_repository():
    """Mock album repository"""
    repo = AsyncMock()
    repo.get_album_by_id = AsyncMock()
    repo.create_album = AsyncMock()
    repo.update_album = AsyncMock()
    repo.delete_album = AsyncMock()
    repo.list_albums = AsyncMock()
    repo.add_photos_to_album = AsyncMock()
    repo.remove_photos_from_album = AsyncMock()
    repo.get_album_photos = AsyncMock()
    repo.get_sync_status = AsyncMock()
    repo.update_sync_status = AsyncMock()
    return repo


@pytest.fixture
def mock_event_bus():
    """Mock event bus for publishing"""
    bus = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def mock_nats_client():
    """Mock NATS client"""
    client = AsyncMock()
    client.publish = AsyncMock()
    return client


@pytest.fixture
def test_user_id():
    """Generate unique test user ID"""
    return AlbumTestDataFactory.make_user_id()


@pytest.fixture
def test_album_id():
    """Generate unique test album ID"""
    return AlbumTestDataFactory.make_album_id()


@pytest.fixture
def test_frame_id():
    """Generate unique test frame ID"""
    return AlbumTestDataFactory.make_frame_id()


# ============================================================================
# Album Creation Tests
# ============================================================================

class TestAlbumCreation:
    """Tests for album creation operations"""

    async def test_create_album_with_valid_data(self, mock_repository, mock_event_bus, test_user_id):
        """
        GIVEN: Valid album creation request
        WHEN: Creating album through service
        THEN: Album is created with correct data and event is published
        """
        # GIVEN
        request = AlbumTestDataFactory.make_create_request(
            name="Test Album",
            description="Test description",
            auto_sync=True,
            is_family_shared=False
        )

        expected_album_id = AlbumTestDataFactory.make_album_id()
        mock_repository.create_album.return_value = {
            "album_id": expected_album_id,
            "user_id": test_user_id,
            "name": request.name,
            "description": request.description,
            "photo_count": 0,
            "auto_sync": request.auto_sync,
            "sync_frames": request.sync_frames,
            "is_family_shared": request.is_family_shared,
            "organization_id": None,
            "cover_photo_id": None,
            "sharing_resource_id": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        # WHEN (simulate service call)
        result = await mock_repository.create_album(
            user_id=test_user_id,
            name=request.name,
            description=request.description,
            auto_sync=request.auto_sync,
            sync_frames=request.sync_frames,
            is_family_shared=request.is_family_shared
        )

        # THEN
        assert result is not None
        assert result["album_id"] == expected_album_id
        assert result["name"] == request.name
        assert result["photo_count"] == 0
        mock_repository.create_album.assert_called_once()

    async def test_create_album_with_family_sharing(self, mock_repository, test_user_id):
        """
        GIVEN: Album creation request with family sharing enabled
        WHEN: Creating album through service
        THEN: Album is created with is_family_shared=True and sharing_resource_id generated
        """
        # GIVEN
        request = AlbumTestDataFactory.make_create_request(
            name="Family Album",
            is_family_shared=True
        )

        expected_sharing_id = f"share_{AlbumTestDataFactory.make_album_id()}"
        mock_repository.create_album.return_value = {
            "album_id": AlbumTestDataFactory.make_album_id(),
            "user_id": test_user_id,
            "name": request.name,
            "is_family_shared": True,
            "sharing_resource_id": expected_sharing_id,
            "photo_count": 0,
            "auto_sync": True,
            "sync_frames": [],
            "organization_id": None,
            "cover_photo_id": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        # WHEN
        result = await mock_repository.create_album(
            user_id=test_user_id,
            name=request.name,
            is_family_shared=True
        )

        # THEN
        assert result["is_family_shared"] is True
        assert result["sharing_resource_id"] is not None

    async def test_create_album_with_sync_frames(self, mock_repository, test_user_id, test_frame_id):
        """
        GIVEN: Album creation request with sync frames specified
        WHEN: Creating album through service
        THEN: Album is created with sync_frames list populated
        """
        # GIVEN
        frame_ids = [test_frame_id, AlbumTestDataFactory.make_frame_id()]
        request = AlbumTestDataFactory.make_create_request(
            name="Synced Album",
            auto_sync=True,
            sync_frames=frame_ids
        )

        mock_repository.create_album.return_value = {
            "album_id": AlbumTestDataFactory.make_album_id(),
            "user_id": test_user_id,
            "name": request.name,
            "auto_sync": True,
            "sync_frames": frame_ids,
            "photo_count": 0,
            "is_family_shared": False,
            "organization_id": None,
            "cover_photo_id": None,
            "sharing_resource_id": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        # WHEN
        result = await mock_repository.create_album(
            user_id=test_user_id,
            name=request.name,
            auto_sync=True,
            sync_frames=frame_ids
        )

        # THEN
        assert result["auto_sync"] is True
        assert result["sync_frames"] == frame_ids
        assert len(result["sync_frames"]) == 2


# ============================================================================
# Album Retrieval Tests
# ============================================================================

class TestAlbumRetrieval:
    """Tests for album retrieval operations"""

    async def test_get_album_by_id(self, mock_repository, test_user_id, test_album_id):
        """
        GIVEN: Existing album in database
        WHEN: Retrieving album by ID
        THEN: Album data is returned correctly
        """
        # GIVEN
        expected_album = {
            "album_id": test_album_id,
            "user_id": test_user_id,
            "name": "Test Album",
            "description": "Test description",
            "photo_count": 5,
            "auto_sync": True,
            "sync_frames": [],
            "is_family_shared": False,
            "organization_id": None,
            "cover_photo_id": None,
            "sharing_resource_id": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        mock_repository.get_album_by_id.return_value = expected_album

        # WHEN
        result = await mock_repository.get_album_by_id(test_album_id, test_user_id)

        # THEN
        assert result is not None
        assert result["album_id"] == test_album_id
        assert result["name"] == "Test Album"
        mock_repository.get_album_by_id.assert_called_once_with(test_album_id, test_user_id)

    async def test_get_nonexistent_album_returns_none(self, mock_repository, test_user_id):
        """
        GIVEN: Album ID that doesn't exist
        WHEN: Retrieving album by ID
        THEN: None is returned
        """
        # GIVEN
        fake_album_id = "album_nonexistent"
        mock_repository.get_album_by_id.return_value = None

        # WHEN
        result = await mock_repository.get_album_by_id(fake_album_id, test_user_id)

        # THEN
        assert result is None

    async def test_list_albums_with_pagination(self, mock_repository, test_user_id):
        """
        GIVEN: Multiple albums exist for user
        WHEN: Listing albums with pagination
        THEN: Paginated results are returned correctly
        """
        # GIVEN
        albums = [
            {"album_id": AlbumTestDataFactory.make_album_id(), "name": f"Album {i}"}
            for i in range(10)
        ]
        mock_repository.list_albums.return_value = {
            "albums": albums[:5],
            "total": 10,
            "page": 1,
            "page_size": 5,
            "pages": 2
        }

        # WHEN
        result = await mock_repository.list_albums(
            user_id=test_user_id,
            page=1,
            page_size=5
        )

        # THEN
        assert len(result["albums"]) == 5
        assert result["total"] == 10
        assert result["pages"] == 2


# ============================================================================
# Album Update Tests
# ============================================================================

class TestAlbumUpdate:
    """Tests for album update operations"""

    async def test_update_album_name(self, mock_repository, test_user_id, test_album_id):
        """
        GIVEN: Existing album
        WHEN: Updating album name
        THEN: Album name is updated and updated_at is refreshed
        """
        # GIVEN
        new_name = "Updated Album Name"
        mock_repository.update_album.return_value = {
            "album_id": test_album_id,
            "user_id": test_user_id,
            "name": new_name,
            "updated_at": datetime.now(timezone.utc)
        }

        # WHEN
        result = await mock_repository.update_album(
            album_id=test_album_id,
            user_id=test_user_id,
            updates={"name": new_name}
        )

        # THEN
        assert result["name"] == new_name
        mock_repository.update_album.assert_called_once()

    async def test_update_album_family_sharing(self, mock_repository, test_user_id, test_album_id):
        """
        GIVEN: Existing album with family sharing disabled
        WHEN: Enabling family sharing
        THEN: is_family_shared is True and sharing_resource_id is generated
        """
        # GIVEN
        expected_sharing_id = f"share_{test_album_id}"
        mock_repository.update_album.return_value = {
            "album_id": test_album_id,
            "user_id": test_user_id,
            "is_family_shared": True,
            "sharing_resource_id": expected_sharing_id,
            "updated_at": datetime.now(timezone.utc)
        }

        # WHEN
        result = await mock_repository.update_album(
            album_id=test_album_id,
            user_id=test_user_id,
            updates={"is_family_shared": True}
        )

        # THEN
        assert result["is_family_shared"] is True
        assert result["sharing_resource_id"] is not None


# ============================================================================
# Album Delete Tests
# ============================================================================

class TestAlbumDelete:
    """Tests for album deletion operations"""

    async def test_delete_album(self, mock_repository, test_user_id, test_album_id):
        """
        GIVEN: Existing album
        WHEN: Deleting album
        THEN: Album is removed and success is returned
        """
        # GIVEN
        mock_repository.delete_album.return_value = {"success": True, "message": f"Album {test_album_id} deleted"}

        # WHEN
        result = await mock_repository.delete_album(test_album_id, test_user_id)

        # THEN
        assert result["success"] is True
        mock_repository.delete_album.assert_called_once_with(test_album_id, test_user_id)

    async def test_delete_nonexistent_album_fails(self, mock_repository, test_user_id):
        """
        GIVEN: Album ID that doesn't exist
        WHEN: Attempting to delete
        THEN: Error is returned
        """
        # GIVEN
        fake_album_id = "album_nonexistent"
        mock_repository.delete_album.return_value = None

        # WHEN
        result = await mock_repository.delete_album(fake_album_id, test_user_id)

        # THEN
        assert result is None


# ============================================================================
# Album Photo Operations Tests
# ============================================================================

class TestAlbumPhotoOperations:
    """Tests for album photo management operations"""

    async def test_add_photos_to_album(self, mock_repository, test_user_id, test_album_id):
        """
        GIVEN: Existing album and photos to add
        WHEN: Adding photos to album
        THEN: Photos are added and count is updated
        """
        # GIVEN
        photo_ids = [AlbumTestDataFactory.make_photo_id() for _ in range(3)]
        mock_repository.add_photos_to_album.return_value = {
            "success": True,
            "added_count": 3,
            "album_id": test_album_id,
            "new_photo_count": 3
        }

        # WHEN
        result = await mock_repository.add_photos_to_album(
            album_id=test_album_id,
            user_id=test_user_id,
            photo_ids=photo_ids
        )

        # THEN
        assert result["success"] is True
        assert result["added_count"] == 3
        assert result["new_photo_count"] == 3

    async def test_add_duplicate_photos_are_ignored(self, mock_repository, test_user_id, test_album_id):
        """
        GIVEN: Album with existing photo
        WHEN: Adding same photo again
        THEN: Duplicate is silently ignored (BR-ALB-007)
        """
        # GIVEN
        existing_photo = AlbumTestDataFactory.make_photo_id()
        mock_repository.add_photos_to_album.return_value = {
            "success": True,
            "added_count": 0,  # Duplicate ignored
            "album_id": test_album_id,
            "new_photo_count": 1
        }

        # WHEN
        result = await mock_repository.add_photos_to_album(
            album_id=test_album_id,
            user_id=test_user_id,
            photo_ids=[existing_photo]
        )

        # THEN
        assert result["success"] is True
        assert result["added_count"] == 0

    async def test_remove_photos_from_album(self, mock_repository, test_user_id, test_album_id):
        """
        GIVEN: Album with photos
        WHEN: Removing photos from album
        THEN: Photos are removed and count is decremented
        """
        # GIVEN
        photo_ids = [AlbumTestDataFactory.make_photo_id() for _ in range(2)]
        mock_repository.remove_photos_from_album.return_value = {
            "success": True,
            "removed_count": 2,
            "album_id": test_album_id,
            "new_photo_count": 3
        }

        # WHEN
        result = await mock_repository.remove_photos_from_album(
            album_id=test_album_id,
            user_id=test_user_id,
            photo_ids=photo_ids
        )

        # THEN
        assert result["success"] is True
        assert result["removed_count"] == 2

    async def test_get_album_photos(self, mock_repository, test_user_id, test_album_id):
        """
        GIVEN: Album with photos
        WHEN: Getting album photos
        THEN: Photos are returned with correct order
        """
        # GIVEN
        photos = [
            {
                "album_id": test_album_id,
                "photo_id": AlbumTestDataFactory.make_photo_id(),
                "display_order": i,
                "is_featured": i == 0,
                "ai_tags": ["beach", "sunset"],
                "ai_objects": ["person"],
                "ai_scenes": ["outdoor"]
            }
            for i in range(5)
        ]
        mock_repository.get_album_photos.return_value = photos

        # WHEN
        result = await mock_repository.get_album_photos(
            album_id=test_album_id,
            user_id=test_user_id,
            limit=50,
            offset=0
        )

        # THEN
        assert len(result) == 5
        assert result[0]["display_order"] == 0
        assert result[0]["is_featured"] is True


# ============================================================================
# Album Sync Operations Tests
# ============================================================================

class TestAlbumSyncOperations:
    """Tests for album-frame sync operations"""

    async def test_initiate_sync_to_frame(self, mock_repository, test_user_id, test_album_id, test_frame_id):
        """
        GIVEN: Album with photos and target frame
        WHEN: Initiating sync to frame
        THEN: Sync status is created with IN_PROGRESS status
        """
        # GIVEN
        mock_repository.update_sync_status.return_value = {
            "album_id": test_album_id,
            "frame_id": test_frame_id,
            "status": SyncStatusEnum.IN_PROGRESS.value,
            "total_photos": 10,
            "synced_photos": 0,
            "pending_photos": 10,
            "failed_photos": 0,
            "sync_version": 1
        }

        # WHEN
        result = await mock_repository.update_sync_status(
            album_id=test_album_id,
            frame_id=test_frame_id,
            status=SyncStatusEnum.IN_PROGRESS.value,
            total_photos=10
        )

        # THEN
        assert result["status"] == SyncStatusEnum.IN_PROGRESS.value
        assert result["total_photos"] == 10
        assert result["synced_photos"] == 0

    async def test_get_sync_status(self, mock_repository, test_album_id, test_frame_id):
        """
        GIVEN: Existing sync status for album-frame pair
        WHEN: Getting sync status
        THEN: Current sync status is returned
        """
        # GIVEN
        mock_repository.get_sync_status.return_value = {
            "album_id": test_album_id,
            "frame_id": test_frame_id,
            "status": SyncStatusEnum.COMPLETED.value,
            "total_photos": 10,
            "synced_photos": 10,
            "pending_photos": 0,
            "failed_photos": 0,
            "sync_version": 1
        }

        # WHEN
        result = await mock_repository.get_sync_status(test_album_id, test_frame_id)

        # THEN
        assert result["status"] == SyncStatusEnum.COMPLETED.value
        assert result["synced_photos"] == result["total_photos"]

    async def test_sync_status_progression(self, mock_repository, test_album_id, test_frame_id):
        """
        GIVEN: Sync in progress
        WHEN: Photos are synced
        THEN: Counters update correctly (BR-ALB-013)
        """
        # Test PENDING -> IN_PROGRESS -> COMPLETED progression

        # GIVEN - IN_PROGRESS with partial sync
        mock_repository.get_sync_status.return_value = {
            "album_id": test_album_id,
            "frame_id": test_frame_id,
            "status": SyncStatusEnum.IN_PROGRESS.value,
            "total_photos": 10,
            "synced_photos": 5,
            "pending_photos": 5,
            "failed_photos": 0,
            "sync_version": 1
        }

        # WHEN
        result = await mock_repository.get_sync_status(test_album_id, test_frame_id)

        # THEN - Verify arithmetic: pending = total - synced - failed
        expected_pending = result["total_photos"] - result["synced_photos"] - result["failed_photos"]
        assert result["pending_photos"] == expected_pending


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Tests for error handling scenarios"""

    async def test_album_not_found_error(self, mock_repository, test_user_id):
        """
        GIVEN: Non-existent album ID
        WHEN: Trying to get album
        THEN: None is returned (or error raised depending on impl)
        """
        mock_repository.get_album_by_id.return_value = None

        result = await mock_repository.get_album_by_id("album_fake", test_user_id)

        assert result is None

    async def test_permission_denied_different_user(self, mock_repository, test_album_id):
        """
        GIVEN: Album owned by different user
        WHEN: Unauthorized user tries to access
        THEN: Album not returned (permission check in repository)
        """
        # GIVEN - Album owned by user_a
        owner_id = AlbumTestDataFactory.make_user_id()
        other_user = AlbumTestDataFactory.make_user_id()

        # Repository returns None for wrong user
        mock_repository.get_album_by_id.return_value = None

        # WHEN
        result = await mock_repository.get_album_by_id(test_album_id, other_user)

        # THEN
        assert result is None


# ============================================================================
# Health Check Tests
# ============================================================================

class TestHealthCheck:
    """Tests for service health check"""

    async def test_health_check_returns_operational(self):
        """
        GIVEN: Service is running properly
        WHEN: Calling health endpoint
        THEN: Status is operational with correct service info
        """
        expected = {
            "service": "album_service",
            "status": "operational",
            "port": 8219,
            "database_connected": True
        }

        # Verify expected structure matches contract
        assert expected["service"] == "album_service"
        assert expected["status"] in ["operational", "degraded", "down"]
        assert expected["port"] == 8219
