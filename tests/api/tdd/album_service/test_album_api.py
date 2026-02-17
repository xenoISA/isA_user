"""
Album Service API Contract Tests

Tests for album service HTTP endpoints.
These tests verify API contracts against the live service.

Usage:
    pytest tests/api/services/album/test_album_api.py -v
"""
import pytest
import pytest_asyncio
import uuid

pytestmark = [pytest.mark.api, pytest.mark.album, pytest.mark.asyncio]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_user_id():
    """Generate unique test user ID"""
    return f"test_user_{uuid.uuid4().hex[:12]}"


@pytest_asyncio.fixture
async def cleanup_album(album_api, test_user_id):
    """Track and cleanup created albums"""
    album_ids = []

    def track(album_id):
        album_ids.append(album_id)
        return album_id

    yield track

    # Cleanup
    for album_id in album_ids:
        try:
            await album_api.delete(f"/{album_id}?user_id={test_user_id}")
        except Exception:
            pass


# ============================================================================
# List Albums Tests
# ============================================================================

class TestAlbumListEndpoint:
    """
    GET /api/v1/albums?user_id={user_id}

    List user's albums with pagination.
    """

    async def test_list_albums_returns_paginated_response(self, album_api, api_assert):
        """RED: List should return paginated response structure"""
        response = await album_api.get("?user_id=test_user_001")

        api_assert.assert_success(response)
        data = response.json()
        assert "albums" in data
        assert "total_count" in data
        assert "page" in data
        assert "page_size" in data
        assert "has_next" in data
        assert isinstance(data["albums"], list)

    async def test_list_albums_pagination_params(self, album_api, api_assert):
        """RED: List should respect pagination parameters"""
        response = await album_api.get("?user_id=test_user_001&page=1&page_size=5")

        api_assert.assert_success(response)
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    async def test_list_albums_summary_fields(self, album_api, api_assert):
        """RED: Album summaries should have required fields"""
        response = await album_api.get("?user_id=test_user_001")

        api_assert.assert_success(response)
        albums = response.json()["albums"]

        if albums:
            album = albums[0]
            assert "album_id" in album
            assert "name" in album
            assert "user_id" in album
            assert "photo_count" in album
            assert "is_family_shared" in album


# ============================================================================
# Create Album Tests
# ============================================================================

class TestAlbumCreateEndpoint:
    """
    POST /api/v1/albums?user_id={user_id}

    Create a new album.
    """

    async def test_create_album_success(self, album_api, api_assert, test_user_id, cleanup_album):
        """RED: Should create album with valid data"""
        album_name = f"Test Album {uuid.uuid4().hex[:8]}"
        response = await album_api.post(f"?user_id={test_user_id}", json={
            "name": album_name,
            "description": "Test album description",
        })

        api_assert.assert_created(response)
        data = response.json()
        assert data["name"] == album_name
        assert "album_id" in data
        cleanup_album(data["album_id"])

    async def test_create_album_validates_name(self, album_api, api_assert, test_user_id):
        """RED: Should reject empty album name"""
        response = await album_api.post(f"?user_id={test_user_id}", json={
            "name": "",
        })

        api_assert.assert_validation_error(response)

    async def test_create_album_with_options(self, album_api, api_assert, test_user_id, cleanup_album):
        """RED: Should create album with optional fields"""
        album_name = f"Options Album {uuid.uuid4().hex[:8]}"
        response = await album_api.post(f"?user_id={test_user_id}", json={
            "name": album_name,
            "description": "Album with options",
            "auto_sync": False,
            "is_family_shared": True,
            "tags": ["vacation", "family"],
        })

        api_assert.assert_created(response)
        data = response.json()
        assert data["auto_sync"] is False
        assert data["is_family_shared"] is True
        cleanup_album(data["album_id"])


# ============================================================================
# Get Album Tests
# ============================================================================

class TestAlbumGetEndpoint:
    """
    GET /api/v1/albums/{album_id}?user_id={user_id}

    Get album details.
    """

    async def test_get_album_returns_full_details(self, album_api, api_assert, test_user_id, cleanup_album):
        """RED: Should return full album details"""
        # Create album first
        album_name = f"Get Test {uuid.uuid4().hex[:8]}"
        create_response = await album_api.post(f"?user_id={test_user_id}", json={
            "name": album_name,
        })
        album_id = create_response.json()["album_id"]
        cleanup_album(album_id)

        # Get album
        response = await album_api.get(f"/{album_id}?user_id={test_user_id}")

        api_assert.assert_success(response)
        data = response.json()
        assert data["album_id"] == album_id
        assert data["name"] == album_name
        assert "photo_count" in data
        assert "auto_sync" in data
        assert "is_family_shared" in data
        assert "created_at" in data

    async def test_get_album_not_found(self, album_api, api_assert, test_user_id):
        """RED: Should return 404 for non-existent album"""
        response = await album_api.get(f"/nonexistent_album_12345?user_id={test_user_id}")

        api_assert.assert_not_found(response)


# ============================================================================
# Update Album Tests
# ============================================================================

class TestAlbumUpdateEndpoint:
    """
    PUT /api/v1/albums/{album_id}?user_id={user_id}

    Update album details.
    """

    async def test_update_album_name(self, album_api, api_assert, test_user_id, cleanup_album):
        """RED: Should update album name"""
        # Create album
        create_response = await album_api.post(f"?user_id={test_user_id}", json={
            "name": f"Original {uuid.uuid4().hex[:8]}",
        })
        album_id = create_response.json()["album_id"]
        cleanup_album(album_id)

        # Update name
        new_name = f"Updated {uuid.uuid4().hex[:8]}"
        response = await album_api.put(f"/{album_id}?user_id={test_user_id}", json={
            "name": new_name,
        })

        api_assert.assert_success(response)
        assert response.json()["name"] == new_name

    async def test_update_album_not_found(self, album_api, api_assert, test_user_id):
        """RED: Should return 404 for non-existent album"""
        response = await album_api.put(f"/nonexistent_album_12345?user_id={test_user_id}", json={
            "name": "New Name",
        })

        api_assert.assert_not_found(response)


# ============================================================================
# Delete Album Tests
# ============================================================================

class TestAlbumDeleteEndpoint:
    """
    DELETE /api/v1/albums/{album_id}?user_id={user_id}

    Delete an album.
    """

    async def test_delete_album_success(self, album_api, api_assert, test_user_id):
        """RED: Should delete existing album"""
        # Create album
        create_response = await album_api.post(f"?user_id={test_user_id}", json={
            "name": f"To Delete {uuid.uuid4().hex[:8]}",
        })
        album_id = create_response.json()["album_id"]

        # Delete it
        response = await album_api.delete(f"/{album_id}?user_id={test_user_id}")

        api_assert.assert_success(response)
        assert "deleted" in response.json().get("message", "").lower() or response.json().get("success", False)

    async def test_delete_album_not_found(self, album_api, api_assert, test_user_id):
        """RED: Should return 404 for non-existent album"""
        response = await album_api.delete(f"/nonexistent_album_12345?user_id={test_user_id}")

        api_assert.assert_not_found(response)


# ============================================================================
# Add Photos Tests
# ============================================================================

class TestAlbumAddPhotosEndpoint:
    """
    POST /api/v1/albums/{album_id}/photos?user_id={user_id}

    Add photos to album.
    """

    async def test_add_photos_success(self, album_api, api_assert, test_user_id, cleanup_album):
        """RED: Should add photos to album"""
        # Create album
        create_response = await album_api.post(f"?user_id={test_user_id}", json={
            "name": f"Photos Test {uuid.uuid4().hex[:8]}",
        })
        album_id = create_response.json()["album_id"]
        cleanup_album(album_id)

        # Add photos
        response = await album_api.post(f"/{album_id}/photos?user_id={test_user_id}", json={
            "photo_ids": ["photo_1", "photo_2"],
        })

        api_assert.assert_success(response)
        data = response.json()
        assert data["added_count"] == 2

    async def test_add_photos_to_nonexistent_album(self, album_api, api_assert, test_user_id):
        """RED: Should return 404 for non-existent album"""
        response = await album_api.post("/nonexistent_12345/photos?user_id={test_user_id}", json={
            "photo_ids": ["photo_1"],
        })

        api_assert.assert_not_found(response)


# ============================================================================
# Get Album Photos Tests
# ============================================================================

class TestAlbumPhotosEndpoint:
    """
    GET /api/v1/albums/{album_id}/photos?user_id={user_id}

    Get photos in album.
    """

    async def test_get_album_photos(self, album_api, api_assert, test_user_id, cleanup_album):
        """RED: Should return album photos"""
        # Create album with photos
        create_response = await album_api.post(f"?user_id={test_user_id}", json={
            "name": f"Photos List {uuid.uuid4().hex[:8]}",
        })
        album_id = create_response.json()["album_id"]
        cleanup_album(album_id)

        await album_api.post(f"/{album_id}/photos?user_id={test_user_id}", json={
            "photo_ids": ["photo_1"],
        })

        # Get photos
        response = await album_api.get(f"/{album_id}/photos?user_id={test_user_id}")

        api_assert.assert_success(response)
        data = response.json()
        assert "photos" in data
        assert isinstance(data["photos"], list)


# ============================================================================
# Remove Photos Tests
# ============================================================================

class TestAlbumRemovePhotosEndpoint:
    """
    DELETE /api/v1/albums/{album_id}/photos?user_id={user_id}

    Remove photos from album.
    """

    async def test_remove_photos_success(self, album_api, api_assert, test_user_id, cleanup_album):
        """RED: Should remove photos from album"""
        # Create album with photos
        create_response = await album_api.post(f"?user_id={test_user_id}", json={
            "name": f"Remove Test {uuid.uuid4().hex[:8]}",
        })
        album_id = create_response.json()["album_id"]
        cleanup_album(album_id)

        await album_api.post(f"/{album_id}/photos?user_id={test_user_id}", json={
            "photo_ids": ["photo_to_remove"],
        })

        # Remove photos - using custom delete with body
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.request(
                "DELETE",
                f"http://localhost:8219/api/v1/albums/{album_id}/photos?user_id={test_user_id}",
                json={"photo_ids": ["photo_to_remove"]},
            )

        assert response.status_code == 200
        data = response.json()
        assert "removed_count" in data


# ============================================================================
# Health Check Tests
# ============================================================================

class TestAlbumHealthEndpoints:
    """
    Health check endpoints
    """

    async def test_health_check(self, album_api, api_assert):
        """RED: Health endpoint should return healthy"""
        response = await album_api.get_raw("/health")

        api_assert.assert_success(response)
        data = response.json()
        assert data["status"] == "healthy"
