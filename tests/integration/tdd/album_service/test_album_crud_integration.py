"""
Album Service CRUD Integration Tests

Tests album lifecycle operations with real database persistence.
These tests verify data flows through the service and persists correctly.

Usage:
    pytest tests/integration/services/album/test_album_crud_integration.py -v
"""
import pytest
import pytest_asyncio
import httpx
import uuid
from typing import List

from tests.fixtures import (
    make_user_id,
    make_album_create_request,
    make_album_update_request,
    make_add_photos_request,
    make_photo_id,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Configuration
# ============================================================================

ALBUM_SERVICE_URL = "http://localhost:8219"
API_BASE = f"{ALBUM_SERVICE_URL}/api/v1/albums"
TIMEOUT = 30.0


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def http_client():
    """HTTP client for integration tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


@pytest.fixture
def test_user_id():
    """Generate unique user ID for test isolation"""
    return make_user_id()


@pytest_asyncio.fixture
async def cleanup_albums(http_client, test_user_id):
    """Track and cleanup albums created during tests"""
    created_album_ids: List[str] = []

    def track(album_id: str):
        created_album_ids.append(album_id)
        return album_id

    yield track

    # Cleanup after test
    for album_id in created_album_ids:
        try:
            await http_client.delete(
                f"{API_BASE}/{album_id}",
                params={"user_id": test_user_id}
            )
        except Exception:
            pass


# ============================================================================
# Album Lifecycle Integration Tests
# ============================================================================

class TestAlbumLifecycleIntegration:
    """
    Integration tests for album CRUD lifecycle.
    Tests data persistence across create/read/update/delete operations.
    """

    async def test_full_album_lifecycle(self, http_client, test_user_id, cleanup_albums):
        """
        Integration: Full album lifecycle - create, read, update, delete

        This test verifies the complete lifecycle of an album:
        1. Create album and verify it's persisted
        2. Read album back and verify data matches
        3. Update album and verify changes persist
        4. Delete album and verify it's removed
        """
        # 1. CREATE
        create_request = make_album_create_request(
            name="Integration Test Album",
            description="Testing full lifecycle",
            is_family_shared=False,
            tags=["integration", "test"],
        )

        create_response = await http_client.post(
            API_BASE,
            params={"user_id": test_user_id},
            json=create_request,
        )
        assert create_response.status_code == 201, f"Create failed: {create_response.text}"

        album_data = create_response.json()
        album_id = album_data["album_id"]
        cleanup_albums(album_id)

        assert album_data["name"] == create_request["name"]
        assert album_data["description"] == create_request["description"]
        assert album_data["user_id"] == test_user_id

        # 2. READ - verify persisted
        get_response = await http_client.get(
            f"{API_BASE}/{album_id}",
            params={"user_id": test_user_id},
        )
        assert get_response.status_code == 200

        read_data = get_response.json()
        assert read_data["album_id"] == album_id
        assert read_data["name"] == create_request["name"]
        assert read_data["tags"] == create_request["tags"]

        # 3. UPDATE
        update_request = make_album_update_request(
            name="Updated Integration Album",
            description="Updated description",
            is_family_shared=True,
        )

        update_response = await http_client.put(
            f"{API_BASE}/{album_id}",
            params={"user_id": test_user_id},
            json=update_request,
        )
        assert update_response.status_code == 200

        updated_data = update_response.json()
        assert updated_data["name"] == update_request["name"]
        assert updated_data["is_family_shared"] == True

        # Verify update persisted
        verify_response = await http_client.get(
            f"{API_BASE}/{album_id}",
            params={"user_id": test_user_id},
        )
        verify_data = verify_response.json()
        assert verify_data["name"] == update_request["name"]

        # 4. DELETE
        delete_response = await http_client.delete(
            f"{API_BASE}/{album_id}",
            params={"user_id": test_user_id},
        )
        assert delete_response.status_code == 200

        # Verify deleted
        get_deleted_response = await http_client.get(
            f"{API_BASE}/{album_id}",
            params={"user_id": test_user_id},
        )
        assert get_deleted_response.status_code == 404


class TestAlbumPhotosIntegration:
    """
    Integration tests for album photo management.
    Tests photo add/remove operations and photo count updates.
    """

    async def test_photo_management_lifecycle(self, http_client, test_user_id, cleanup_albums):
        """
        Integration: Photo add/remove lifecycle

        1. Create album with 0 photos
        2. Add photos and verify count updates
        3. Get photos list and verify
        4. Remove photos and verify count updates
        """
        # 1. Create album
        create_response = await http_client.post(
            API_BASE,
            params={"user_id": test_user_id},
            json=make_album_create_request(name="Photo Test Album"),
        )
        assert create_response.status_code == 201

        album_id = create_response.json()["album_id"]
        cleanup_albums(album_id)

        initial_count = create_response.json()["photo_count"]
        assert initial_count == 0

        # 2. Add photos
        photo_ids = [make_photo_id() for _ in range(3)]
        add_response = await http_client.post(
            f"{API_BASE}/{album_id}/photos",
            params={"user_id": test_user_id},
            json={"photo_ids": photo_ids},
        )
        assert add_response.status_code == 200
        assert add_response.json()["added_count"] == 3

        # Verify photo count updated
        get_response = await http_client.get(
            f"{API_BASE}/{album_id}",
            params={"user_id": test_user_id},
        )
        assert get_response.json()["photo_count"] == 3

        # 3. Get photos list
        photos_response = await http_client.get(
            f"{API_BASE}/{album_id}/photos",
            params={"user_id": test_user_id},
        )
        assert photos_response.status_code == 200
        photos_data = photos_response.json()
        assert len(photos_data.get("photos", [])) == 3

        # 4. Remove one photo
        remove_response = await http_client.request(
            "DELETE",
            f"{API_BASE}/{album_id}/photos",
            params={"user_id": test_user_id},
            json={"photo_ids": [photo_ids[0]]},
        )
        assert remove_response.status_code == 200

        # Verify count updated
        final_response = await http_client.get(
            f"{API_BASE}/{album_id}",
            params={"user_id": test_user_id},
        )
        assert final_response.json()["photo_count"] == 2


class TestAlbumListingIntegration:
    """
    Integration tests for album listing and pagination.
    """

    async def test_user_albums_listing_and_pagination(self, http_client, test_user_id, cleanup_albums):
        """
        Integration: List user albums with pagination

        1. Create multiple albums
        2. List with default pagination
        3. List with custom page size
        4. Verify pagination metadata
        """
        # 1. Create 5 albums
        album_ids = []
        for i in range(5):
            response = await http_client.post(
                API_BASE,
                params={"user_id": test_user_id},
                json=make_album_create_request(name=f"List Test Album {i}"),
            )
            assert response.status_code == 201
            album_ids.append(response.json()["album_id"])
            cleanup_albums(album_ids[-1])

        # 2. List all
        list_response = await http_client.get(
            API_BASE,
            params={"user_id": test_user_id},
        )
        assert list_response.status_code == 200

        list_data = list_response.json()
        assert "albums" in list_data
        assert "total_count" in list_data
        assert list_data["total_count"] >= 5

        # 3. List with page_size=2
        paginated_response = await http_client.get(
            API_BASE,
            params={"user_id": test_user_id, "page": 1, "page_size": 2},
        )
        assert paginated_response.status_code == 200

        paginated_data = paginated_response.json()
        assert len(paginated_data["albums"]) == 2
        assert paginated_data["page_size"] == 2
        assert paginated_data["has_next"] == True  # More albums available


class TestAlbumFamilySharingIntegration:
    """
    Integration tests for family sharing functionality.
    """

    async def test_family_shared_album_creation(self, http_client, test_user_id, cleanup_albums):
        """
        Integration: Create and update family-shared album

        1. Create album with is_family_shared=true
        2. Verify sharing status persisted
        3. Update to not shared
        4. Verify change persisted
        """
        # 1. Create shared album
        create_response = await http_client.post(
            API_BASE,
            params={"user_id": test_user_id},
            json=make_album_create_request(
                name="Family Album",
                is_family_shared=True,
            ),
        )
        assert create_response.status_code == 201

        album_id = create_response.json()["album_id"]
        cleanup_albums(album_id)

        assert create_response.json()["is_family_shared"] == True

        # 2. Verify persisted
        get_response = await http_client.get(
            f"{API_BASE}/{album_id}",
            params={"user_id": test_user_id},
        )
        assert get_response.json()["is_family_shared"] == True

        # 3. Update to not shared
        update_response = await http_client.put(
            f"{API_BASE}/{album_id}",
            params={"user_id": test_user_id},
            json={"is_family_shared": False},
        )
        assert update_response.status_code == 200
        assert update_response.json()["is_family_shared"] == False

        # 4. Verify change persisted
        verify_response = await http_client.get(
            f"{API_BASE}/{album_id}",
            params={"user_id": test_user_id},
        )
        assert verify_response.json()["is_family_shared"] == False


class TestAlbumSyncSettingsIntegration:
    """
    Integration tests for album sync settings.
    """

    async def test_sync_settings_persistence(self, http_client, test_user_id, cleanup_albums):
        """
        Integration: Album sync settings persist correctly

        1. Create album with auto_sync=false and sync_frames
        2. Verify settings persisted
        3. Update sync settings
        4. Verify changes
        """
        frame_ids = [f"frame_{uuid.uuid4().hex[:8]}" for _ in range(2)]

        # 1. Create with sync settings
        create_response = await http_client.post(
            API_BASE,
            params={"user_id": test_user_id},
            json=make_album_create_request(
                name="Sync Test Album",
                auto_sync=False,
                sync_frames=frame_ids,
            ),
        )
        assert create_response.status_code == 201

        album_id = create_response.json()["album_id"]
        cleanup_albums(album_id)

        # 2. Verify settings
        get_response = await http_client.get(
            f"{API_BASE}/{album_id}",
            params={"user_id": test_user_id},
        )
        album_data = get_response.json()
        assert album_data["auto_sync"] == False
        assert album_data["sync_frames"] == frame_ids

        # 3. Update to enable auto_sync
        update_response = await http_client.put(
            f"{API_BASE}/{album_id}",
            params={"user_id": test_user_id},
            json={"auto_sync": True, "sync_frames": []},
        )
        assert update_response.status_code == 200

        # 4. Verify changes
        verify_response = await http_client.get(
            f"{API_BASE}/{album_id}",
            params={"user_id": test_user_id},
        )
        verify_data = verify_response.json()
        assert verify_data["auto_sync"] == True
        assert verify_data["sync_frames"] == []
