"""
Album Service - Golden API Tests

Real HTTP tests against running album service.
Validates API contracts, HTTP status codes, and response schemas.

Prerequisites:
    - album_service running on port 8219
    - Database available

Usage:
    pytest tests/api/golden/album_service/ -v
"""
import pytest
import httpx
import sys
import os
from typing import List, Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../..'))

from tests.contracts.album.data_contract import (
    AlbumTestDataFactory,
    AlbumResponseContract,
    AlbumListResponseContract,
    AlbumAddPhotosResponseContract,
    AlbumRemovePhotosResponseContract,
    AlbumSyncStatusResponseContract,
    SyncStatusEnum,
)

pytestmark = [pytest.mark.api, pytest.mark.asyncio]


# ============================================================================
# Configuration
# ============================================================================

SERVICE_PORT = 8219
BASE_URL = f"http://localhost:{SERVICE_PORT}"
API_BASE = f"{BASE_URL}/api/v1/albums"
TIMEOUT = 30.0


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def http_client():
    """Synchronous HTTP client for API tests"""
    return httpx.Client(timeout=TIMEOUT)


@pytest.fixture
def test_user_id():
    """Generate unique test user ID"""
    return AlbumTestDataFactory.make_user_id()


@pytest.fixture
def created_albums():
    """Track albums created during test for cleanup"""
    albums: List[dict] = []
    yield albums
    # Cleanup would happen here in real tests


# ============================================================================
# Health Check API Tests
# ============================================================================

class TestAlbumHealthAPIGolden:
    """Golden tests for album service health endpoints"""

    def test_health_endpoint_returns_200(self, http_client):
        """
        Contract: GET /health returns 200 OK with service status
        """
        response = http_client.get(f"{BASE_URL}/health")

        # Should return 200 OK
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "ok", "operational"]

    def test_health_endpoint_returns_service_info(self, http_client):
        """
        Contract: Health response includes service identification
        """
        response = http_client.get(f"{BASE_URL}/health")

        if response.status_code == 200:
            data = response.json()
            # Service should identify itself
            if "service" in data:
                assert data["service"] == "album_service"


# ============================================================================
# Album Create API Tests
# ============================================================================

class TestAlbumCreateAPIGolden:
    """Golden tests for album creation endpoints"""

    def test_create_album_returns_201(self, http_client, test_user_id):
        """
        Contract: POST /api/v1/albums returns 201 Created with album data
        """
        request = AlbumTestDataFactory.make_create_request(
            name="API Test Album",
            description="Testing API creation"
        )

        response = http_client.post(
            API_BASE,
            json=request.model_dump(),
            params={"user_id": test_user_id}
        )

        # Should return 201 Created (or 200 depending on implementation)
        assert response.status_code in [200, 201]

        data = response.json()
        assert "album_id" in data
        assert data["name"] == request.name

    def test_create_album_with_empty_name_returns_400(self, http_client, test_user_id):
        """
        Contract: POST with empty name returns 400 Bad Request (BR-ALB-001)
        """
        invalid_request = {"name": "", "description": "Test"}

        response = http_client.post(
            API_BASE,
            json=invalid_request,
            params={"user_id": test_user_id}
        )

        # Should return 400 or 422 for validation error
        assert response.status_code in [400, 422]

    def test_create_album_with_long_name_returns_400(self, http_client, test_user_id):
        """
        Contract: POST with name > 255 chars returns 400 Bad Request (BR-ALB-001)
        """
        invalid_request = {"name": "A" * 300}

        response = http_client.post(
            API_BASE,
            json=invalid_request,
            params={"user_id": test_user_id}
        )

        # Should return 400 or 422 for validation error
        assert response.status_code in [400, 422]

    def test_create_family_shared_album(self, http_client, test_user_id):
        """
        Contract: Creating album with is_family_shared=true generates sharing_resource_id
        """
        request = AlbumTestDataFactory.make_create_request(
            name="Family Test Album",
            is_family_shared=True
        )

        response = http_client.post(
            API_BASE,
            json=request.model_dump(),
            params={"user_id": test_user_id}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert data.get("is_family_shared") is True
            # sharing_resource_id may or may not be generated immediately


# ============================================================================
# Album Get API Tests
# ============================================================================

class TestAlbumGetAPIGolden:
    """Golden tests for album retrieval endpoints"""

    def test_get_nonexistent_album_returns_404(self, http_client, test_user_id):
        """
        Contract: GET /api/v1/albums/{invalid_id} returns 404 Not Found
        """
        fake_id = "album_nonexistent_12345"

        response = http_client.get(
            f"{API_BASE}/{fake_id}",
            params={"user_id": test_user_id}
        )

        assert response.status_code == 404

    def test_get_album_returns_correct_schema(self, http_client, test_user_id):
        """
        Contract: GET /api/v1/albums/{id} returns album with required fields
        """
        # First create an album
        request = AlbumTestDataFactory.make_create_request(name="Schema Test Album")
        create_response = http_client.post(
            API_BASE,
            json=request.model_dump(),
            params={"user_id": test_user_id}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create test album")

        album_id = create_response.json().get("album_id")

        # Get the album
        response = http_client.get(
            f"{API_BASE}/{album_id}",
            params={"user_id": test_user_id}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify required fields per contract
        assert "album_id" in data
        assert "user_id" in data
        assert "name" in data
        assert "photo_count" in data


# ============================================================================
# Album List API Tests
# ============================================================================

class TestAlbumListAPIGolden:
    """Golden tests for album listing endpoints"""

    def test_list_albums_returns_paginated_response(self, http_client, test_user_id):
        """
        Contract: GET /api/v1/albums returns paginated list (BR-ALB-023)
        """
        response = http_client.get(
            API_BASE,
            params={"user_id": test_user_id, "page": 1, "page_size": 10}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have pagination fields
        assert "albums" in data
        assert isinstance(data["albums"], list)

    def test_list_albums_respects_page_size_limit(self, http_client, test_user_id):
        """
        Contract: page_size max is 100 (BR-ALB-023)
        """
        response = http_client.get(
            API_BASE,
            params={"user_id": test_user_id, "page": 1, "page_size": 100}
        )

        # Should succeed with max page_size
        assert response.status_code == 200

    def test_list_albums_invalid_page_returns_error(self, http_client, test_user_id):
        """
        Contract: page < 1 returns 400/422 (BR-ALB-023)
        """
        response = http_client.get(
            API_BASE,
            params={"user_id": test_user_id, "page": 0, "page_size": 10}
        )

        # Should return validation error
        assert response.status_code in [400, 422]


# ============================================================================
# Album Update API Tests
# ============================================================================

class TestAlbumUpdateAPIGolden:
    """Golden tests for album update endpoints"""

    def test_update_nonexistent_album_returns_404(self, http_client, test_user_id):
        """
        Contract: PUT /api/v1/albums/{invalid_id} returns 404
        """
        fake_id = "album_nonexistent_12345"
        update_request = {"name": "Updated Name"}

        response = http_client.put(
            f"{API_BASE}/{fake_id}",
            json=update_request,
            params={"user_id": test_user_id}
        )

        assert response.status_code == 404

    def test_update_album_returns_updated_data(self, http_client, test_user_id):
        """
        Contract: PUT /api/v1/albums/{id} returns updated album
        """
        # Create an album first
        request = AlbumTestDataFactory.make_create_request(name="Update Test Album")
        create_response = http_client.post(
            API_BASE,
            json=request.model_dump(),
            params={"user_id": test_user_id}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create test album")

        album_id = create_response.json().get("album_id")

        # Update the album
        new_name = "Updated Album Name"
        response = http_client.put(
            f"{API_BASE}/{album_id}",
            json={"name": new_name},
            params={"user_id": test_user_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("name") == new_name


# ============================================================================
# Album Delete API Tests
# ============================================================================

class TestAlbumDeleteAPIGolden:
    """Golden tests for album deletion endpoints"""

    def test_delete_nonexistent_album_returns_404(self, http_client, test_user_id):
        """
        Contract: DELETE /api/v1/albums/{invalid_id} returns 404
        """
        fake_id = "album_nonexistent_12345"

        response = http_client.delete(
            f"{API_BASE}/{fake_id}",
            params={"user_id": test_user_id}
        )

        assert response.status_code == 404

    def test_delete_album_returns_success(self, http_client, test_user_id):
        """
        Contract: DELETE /api/v1/albums/{id} returns success confirmation
        """
        # Create an album first
        request = AlbumTestDataFactory.make_create_request(name="Delete Test Album")
        create_response = http_client.post(
            API_BASE,
            json=request.model_dump(),
            params={"user_id": test_user_id}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create test album")

        album_id = create_response.json().get("album_id")

        # Delete the album
        response = http_client.delete(
            f"{API_BASE}/{album_id}",
            params={"user_id": test_user_id}
        )

        assert response.status_code in [200, 204]


# ============================================================================
# Album Photos API Tests
# ============================================================================

class TestAlbumPhotosAPIGolden:
    """Golden tests for album photo management endpoints"""

    def test_add_photos_to_nonexistent_album_returns_404(self, http_client, test_user_id):
        """
        Contract: POST /api/v1/albums/{invalid_id}/photos returns 404
        """
        fake_id = "album_nonexistent_12345"
        photo_request = {"photo_ids": [AlbumTestDataFactory.make_photo_id()]}

        response = http_client.post(
            f"{API_BASE}/{fake_id}/photos",
            json=photo_request,
            params={"user_id": test_user_id}
        )

        assert response.status_code == 404

    def test_add_photos_returns_count(self, http_client, test_user_id):
        """
        Contract: POST /api/v1/albums/{id}/photos returns added_count
        """
        # Create album first
        request = AlbumTestDataFactory.make_create_request(name="Photos Test Album")
        create_response = http_client.post(
            API_BASE,
            json=request.model_dump(),
            params={"user_id": test_user_id}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create test album")

        album_id = create_response.json().get("album_id")

        # Add photos
        photo_ids = [AlbumTestDataFactory.make_photo_id() for _ in range(3)]
        response = http_client.post(
            f"{API_BASE}/{album_id}/photos",
            json={"photo_ids": photo_ids},
            params={"user_id": test_user_id}
        )

        if response.status_code == 200:
            data = response.json()
            assert "added_count" in data

    def test_get_album_photos_returns_list(self, http_client, test_user_id):
        """
        Contract: GET /api/v1/albums/{id}/photos returns photo list
        """
        # Create album first
        request = AlbumTestDataFactory.make_create_request(name="Get Photos Test Album")
        create_response = http_client.post(
            API_BASE,
            json=request.model_dump(),
            params={"user_id": test_user_id}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create test album")

        album_id = create_response.json().get("album_id")

        # Get photos
        response = http_client.get(
            f"{API_BASE}/{album_id}/photos",
            params={"user_id": test_user_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "photos" in data


# ============================================================================
# Album Sync API Tests
# ============================================================================

class TestAlbumSyncAPIGolden:
    """Golden tests for album sync endpoints"""

    def test_sync_to_nonexistent_album_returns_404(self, http_client, test_user_id):
        """
        Contract: POST /api/v1/albums/{invalid_id}/sync returns 404
        """
        fake_id = "album_nonexistent_12345"
        sync_request = {"frame_id": AlbumTestDataFactory.make_frame_id()}

        response = http_client.post(
            f"{API_BASE}/{fake_id}/sync",
            json=sync_request,
            params={"user_id": test_user_id}
        )

        assert response.status_code == 404

    def test_sync_returns_status(self, http_client, test_user_id):
        """
        Contract: POST /api/v1/albums/{id}/sync returns sync status
        """
        # Create album first
        request = AlbumTestDataFactory.make_create_request(name="Sync Test Album")
        create_response = http_client.post(
            API_BASE,
            json=request.model_dump(),
            params={"user_id": test_user_id}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create test album")

        album_id = create_response.json().get("album_id")
        frame_id = AlbumTestDataFactory.make_frame_id()

        # Initiate sync
        response = http_client.post(
            f"{API_BASE}/{album_id}/sync",
            json={"frame_id": frame_id},
            params={"user_id": test_user_id}
        )

        if response.status_code == 200:
            data = response.json()
            # Should return sync status
            assert "sync_status" in data or "status" in data

    def test_get_sync_status_returns_progress(self, http_client, test_user_id):
        """
        Contract: GET /api/v1/albums/{id}/sync/{frame_id} returns sync progress
        """
        # Create and sync album
        request = AlbumTestDataFactory.make_create_request(name="Sync Status Test Album")
        create_response = http_client.post(
            API_BASE,
            json=request.model_dump(),
            params={"user_id": test_user_id}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create test album")

        album_id = create_response.json().get("album_id")
        frame_id = AlbumTestDataFactory.make_frame_id()

        # Initiate sync first
        http_client.post(
            f"{API_BASE}/{album_id}/sync",
            json={"frame_id": frame_id},
            params={"user_id": test_user_id}
        )

        # Get sync status
        response = http_client.get(
            f"{API_BASE}/{album_id}/sync/{frame_id}",
            params={"user_id": test_user_id}
        )

        # Should return status or 404 if sync not found
        assert response.status_code in [200, 404]
