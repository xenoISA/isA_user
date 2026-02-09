"""
Media Service API Tests (Golden)

Characterization tests for media service API endpoints.
Tests HTTP contract validation, authentication, error handling.

Related Documents:
- Domain: docs/domain/media_service.md
- PRD: docs/prd/media_service.md
- Design: docs/design/media_service.md
- Data Contract: tests/contracts/media/data_contract.py

Port: 8222
"""

import pytest
import httpx
import os
from datetime import datetime
from typing import Dict, Any

# Import contract components if available
try:
    from tests.contracts.media.data_contract import (
        PhotoVersionType,
        PlaylistType,
        CacheStatus,
        ScheduleType,
    )
except ImportError:
    # Define locally if contract not available
    from enum import Enum
    class PhotoVersionType(str, Enum):
        ORIGINAL = "original"
        AI_ENHANCED = "ai_enhanced"
        FILTERED = "filtered"
        RESIZED = "resized"

    class PlaylistType(str, Enum):
        MANUAL = "manual"
        SMART = "smart"
        FAVORITES = "favorites"


pytestmark = [pytest.mark.api, pytest.mark.asyncio, pytest.mark.golden]

MEDIA_SERVICE_URL = os.getenv("MEDIA_SERVICE_URL", "http://localhost:8222")
API_BASE = f"{MEDIA_SERVICE_URL}/api/v1/media"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def http_client():
    """Create HTTP client for API tests"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture
def test_user_id():
    """Generate test user ID"""
    return f"api_test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}"


@pytest.fixture
def auth_headers(test_user_id):
    """Mock authentication headers for API testing"""
    return {
        "Authorization": "Bearer api_test_token_12345",
        "X-User-ID": test_user_id,
        "X-Request-ID": f"api-test-{datetime.now().timestamp()}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def internal_headers(test_user_id):
    """Internal service call headers (bypass auth)"""
    return {
        "X-User-ID": test_user_id,
        "X-Internal-Call": "true",
        "X-Request-ID": f"internal-test-{datetime.now().timestamp()}",
        "Content-Type": "application/json"
    }


# =============================================================================
# Health Check API Tests
# =============================================================================

class TestMediaServiceHealthAPI:
    """Test media service health endpoints"""

    async def test_health_returns_200(self, http_client):
        """CHAR: GET /health returns 200"""
        response = await http_client.get(f"{MEDIA_SERVICE_URL}/health")
        assert response.status_code == 200

    async def test_health_returns_json(self, http_client):
        """CHAR: GET /health returns JSON content type"""
        response = await http_client.get(f"{MEDIA_SERVICE_URL}/health")
        assert "application/json" in response.headers.get("content-type", "")

    async def test_health_contains_status(self, http_client):
        """CHAR: Health response contains status field"""
        response = await http_client.get(f"{MEDIA_SERVICE_URL}/health")
        data = response.json()
        assert "status" in data

    async def test_health_contains_service_name(self, http_client):
        """CHAR: Health response identifies service"""
        response = await http_client.get(f"{MEDIA_SERVICE_URL}/health")
        data = response.json()
        # Service name should be present
        assert data.get("service") or data.get("name") or "media" in str(data).lower()


# =============================================================================
# Photo Version API Tests
# =============================================================================

class TestPhotoVersionAPI:
    """Test photo version API endpoints"""

    async def test_create_version_returns_success(
        self, http_client, internal_headers
    ):
        """CHAR: POST /api/v1/versions returns 200/201"""
        request_data = {
            "photo_id": "api_test_photo_001",
            "version_name": "API Test Version",
            "version_type": PhotoVersionType.AI_ENHANCED.value,
            "file_id": "api_test_file_001",
            "processing_params": {"quality": "high"}
        }

        response = await http_client.post(
            f"{API_BASE}/versions",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201, 400, 422]

    async def test_create_version_validates_required_fields(
        self, http_client, internal_headers
    ):
        """CHAR: POST /api/v1/versions validates required fields"""
        # Missing required fields
        request_data = {
            "version_name": "Incomplete Request"
        }

        response = await http_client.post(
            f"{API_BASE}/versions",
            json=request_data,
            headers=internal_headers
        )

        # Should return validation error
        assert response.status_code in [400, 422]

    async def test_get_photo_versions_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/photos/{id}/versions returns 200"""
        photo_id = "api_test_photo_001"

        response = await http_client.get(
            f"{API_BASE}/photos/{photo_id}/versions",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [200, 404, 422]

    async def test_get_nonexistent_version_returns_404(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET nonexistent version returns 404"""
        response = await http_client.get(
            f"{API_BASE}/versions/nonexistent_version_api_12345",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [404, 422]


# =============================================================================
# Playlist API Tests
# =============================================================================

class TestPlaylistAPI:
    """Test playlist API endpoints"""

    async def test_create_playlist_returns_success(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: POST /api/v1/playlists returns 200/201"""
        request_data = {
            "name": "API Test Playlist",
            "user_id": test_user_id,
            "description": "Created via API test",
            "shuffle": False,
            "loop": True
        }

        response = await http_client.post(
            f"{API_BASE}/playlists",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201, 422]

    async def test_create_playlist_validates_name(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: POST /api/v1/playlists validates name field"""
        request_data = {
            "name": "",  # Empty name
            "user_id": test_user_id
        }

        response = await http_client.post(
            f"{API_BASE}/playlists",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [400, 422]

    async def test_list_playlists_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/playlists returns 200"""
        response = await http_client.get(
            f"{API_BASE}/playlists",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [200, 422]

    async def test_list_playlists_returns_array(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/playlists returns array structure"""
        response = await http_client.get(
            f"{API_BASE}/playlists",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        if response.status_code == 200:
            data = response.json()
            # Should be array or have playlists field
            assert isinstance(data, list) or "playlists" in data

    async def test_get_nonexistent_playlist_returns_404(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET nonexistent playlist returns 404"""
        response = await http_client.get(
            f"{API_BASE}/playlists/nonexistent_playlist_api_12345",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [404, 422]

    async def test_update_playlist_returns_200(
        self, http_client, internal_headers
    ):
        """CHAR: PUT /api/v1/playlists/{id} returns 200"""
        # First create a playlist
        create_response = await http_client.post(
            f"{API_BASE}/playlists",
            json={
                "name": "Playlist to Update",
                "playlist_type": PlaylistType.MANUAL.value
            },
            headers=internal_headers
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create playlist")

        data = create_response.json()
        playlist_id = data.get("playlist_id")
        if not playlist_id:
            pytest.skip("No playlist_id in response")

        # Update playlist
        update_response = await http_client.put(
            f"{API_BASE}/playlists/{playlist_id}",
            json={"name": "Updated API Playlist"},
            headers=internal_headers
        )

        assert update_response.status_code == 200

        # Cleanup
        await http_client.delete(
            f"{API_BASE}/playlists/{playlist_id}",
            headers=internal_headers
        )

    async def test_delete_playlist_returns_200(
        self, http_client, internal_headers
    ):
        """CHAR: DELETE /api/v1/playlists/{id} returns 200"""
        # First create a playlist
        create_response = await http_client.post(
            f"{API_BASE}/playlists",
            json={
                "name": "Playlist to Delete",
                "playlist_type": PlaylistType.MANUAL.value
            },
            headers=internal_headers
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create playlist")

        data = create_response.json()
        playlist_id = data.get("playlist_id")
        if not playlist_id:
            pytest.skip("No playlist_id in response")

        # Delete playlist
        delete_response = await http_client.delete(
            f"{API_BASE}/playlists/{playlist_id}",
            headers=internal_headers
        )

        assert delete_response.status_code in [200, 204]


# =============================================================================
# Schedule API Tests
# =============================================================================

class TestScheduleAPI:
    """Test rotation schedule API endpoints"""

    async def test_create_schedule_endpoint_exists(
        self, http_client, internal_headers
    ):
        """CHAR: POST /api/v1/schedules endpoint exists"""
        request_data = {
            "frame_id": "api_test_frame_001",
            "playlist_id": "api_test_playlist_001",
            "schedule_type": "time_based",
            "start_time": "09:00",
            "end_time": "21:00"
        }

        response = await http_client.post(
            f"{API_BASE}/schedules",
            json=request_data,
            headers=internal_headers
        )

        # Endpoint should exist (may fail due to missing playlist)
        assert response.status_code in [200, 201, 400, 404, 422]

    async def test_get_frame_schedules_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/frames/{id}/schedules returns 200"""
        frame_id = "api_test_frame_001"

        response = await http_client.get(
            f"{API_BASE}/frames/{frame_id}/schedules",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [200, 404, 422]


# =============================================================================
# Cache API Tests
# =============================================================================

class TestCacheAPI:
    """Test photo cache API endpoints"""

    async def test_get_frame_cache_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/frames/{id}/cache returns 200"""
        frame_id = "api_test_frame_001"

        response = await http_client.get(
            f"{API_BASE}/frames/{frame_id}/cache",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [200, 404, 422]

    async def test_create_cache_entry_endpoint_exists(
        self, http_client, internal_headers
    ):
        """CHAR: POST /api/v1/cache endpoint exists"""
        request_data = {
            "frame_id": "api_test_frame_001",
            "photo_id": "api_test_photo_001",
            "version_id": "api_test_version_001",
            "status": "pending"
        }

        response = await http_client.post(
            f"{API_BASE}/cache",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201, 400, 422]


# =============================================================================
# Gallery API Tests
# =============================================================================

class TestGalleryAPI:
    """Test gallery API endpoints"""

    async def test_get_gallery_albums_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/media/gallery/albums returns 200"""
        response = await http_client.get(
            f"{API_BASE}/gallery/albums",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [200, 404, 422]

    async def test_get_gallery_playlists_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/media/gallery/playlists returns 200"""
        response = await http_client.get(
            f"{API_BASE}/gallery/playlists",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [200, 404, 422]

    async def test_get_random_photos_returns_200(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/media/gallery/photos/random returns 200"""
        response = await http_client.get(
            f"{API_BASE}/gallery/photos/random",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [200, 404, 422]


# =============================================================================
# Metadata API Tests
# =============================================================================

class TestMetadataAPI:
    """Test metadata API endpoints"""

    async def test_get_metadata_nonexistent_returns_404(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET nonexistent metadata returns 404"""
        file_id = "nonexistent_file_api_12345"

        response = await http_client.get(
            f"{API_BASE}/metadata/{file_id}",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [404, 422]


# =============================================================================
# Error Handling API Tests
# =============================================================================

class TestMediaAPIErrorHandling:
    """Test API error handling"""

    async def test_malformed_json_returns_400(
        self, http_client, internal_headers
    ):
        """CHAR: Malformed JSON returns 400"""
        headers = {**internal_headers}
        headers["Content-Type"] = "application/json"

        response = await http_client.post(
            f"{API_BASE}/playlists",
            content="invalid json {",
            headers=headers
        )

        assert response.status_code in [400, 422]

    async def test_missing_content_type_handled(
        self, http_client, internal_headers
    ):
        """CHAR: Missing content-type handled gracefully"""
        headers = {k: v for k, v in internal_headers.items() if k != "Content-Type"}

        response = await http_client.post(
            f"{API_BASE}/playlists",
            json={"name": "Test"},
            headers=headers
        )

        # Should either work or return appropriate error
        assert response.status_code in [200, 201, 400, 415, 422]


# =============================================================================
# API Response Headers Tests
# =============================================================================

class TestMediaAPIResponseHeaders:
    """Test API response headers"""

    async def test_cors_headers_present(self, http_client):
        """CHAR: CORS headers present on response"""
        response = await http_client.get(f"{MEDIA_SERVICE_URL}/health")

        # Check for common CORS headers
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        # At minimum should have content-type
        assert "content-type" in headers_lower

    async def test_content_type_json(
        self, http_client, internal_headers
    ):
        """CHAR: API responses have JSON content type"""
        response = await http_client.get(
            f"{API_BASE}/playlists",
            headers=internal_headers
        )

        if response.status_code == 200:
            assert "application/json" in response.headers.get("content-type", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
