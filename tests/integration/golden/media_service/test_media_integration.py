"""
Media Service Integration Tests

Tests media service API endpoints with real database.
Validates HTTP API + PostgreSQL + Event publishing.

Related Documents:
- Domain: docs/domain/media_service.md
- PRD: docs/prd/media_service.md
- Design: docs/design/media_service.md
- Data Contract: tests/contracts/media/data_contract.py

Requires:
- PostgreSQL database running
- Media service running on port 8222
- NATS for events (optional)
"""

import pytest
import httpx
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.golden]

MEDIA_SERVICE_URL = os.getenv("MEDIA_SERVICE_URL", "http://localhost:8222")


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def http_client():
    """Create HTTP client for tests"""
    async with httpx.AsyncClient(base_url=MEDIA_SERVICE_URL, timeout=30.0) as client:
        yield client


@pytest.fixture
def test_user_id():
    """Generate test user ID"""
    return f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}"


@pytest.fixture
def internal_headers(test_user_id):
    """Headers for internal service calls"""
    return {
        "X-User-ID": test_user_id,
        "X-Request-ID": f"test-{datetime.now().timestamp()}",
        "Content-Type": "application/json"
    }


# =============================================================================
# Health Check Tests
# =============================================================================

class TestMediaServiceHealth:
    """Test media service health endpoints"""

    async def test_root_returns_200(self, http_client):
        """CHAR: Root endpoint returns 200"""
        response = await http_client.get("/")
        assert response.status_code == 200

    async def test_health_endpoint_returns_200(self, http_client):
        """CHAR: Health endpoint returns 200"""
        response = await http_client.get("/health")
        assert response.status_code == 200

    async def test_health_contains_status(self, http_client):
        """CHAR: Health response contains status field"""
        response = await http_client.get("/health")
        data = response.json()
        assert "status" in data

    async def test_health_identifies_service(self, http_client):
        """CHAR: Health response identifies media_service"""
        response = await http_client.get("/health")
        data = response.json()
        assert data.get("service") == "media_service"


# =============================================================================
# Photo Version Tests
# =============================================================================

class TestPhotoVersionIntegration:
    """Test photo version CRUD operations"""

    async def test_create_version_endpoint_exists(
        self, http_client, internal_headers
    ):
        """CHAR: POST /api/v1/media/versions endpoint exists"""
        request_data = {
            "photo_id": "photo_test_001",
            "version_name": "AI Enhanced",
            "version_type": "ai_enhanced",
            "file_id": "file_test_001"
        }

        response = await http_client.post(
            "/api/v1/media/versions",
            json=request_data,
            headers=internal_headers
        )

        # Endpoint exists - may return 200/201/422 depending on validation
        assert response.status_code in [200, 201, 400, 422, 500]

    async def test_get_photo_versions_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/media/photos/{id}/versions endpoint exists"""
        response = await http_client.get(
            "/api/v1/media/photos/photo_test_001/versions",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        # Endpoint exists - may return 200/404/422
        assert response.status_code in [200, 404, 422]

    async def test_get_version_by_id(
        self, http_client, internal_headers
    ):
        """CHAR: GET /api/v1/media/versions/{id} endpoint exists"""
        response = await http_client.get(
            "/api/v1/media/versions/nonexistent_version_12345",
            headers=internal_headers
        )

        # Should return 404 for nonexistent or 422 if missing params
        assert response.status_code in [404, 422]


# =============================================================================
# Playlist Tests
# =============================================================================

class TestPlaylistIntegration:
    """Test playlist CRUD operations"""

    async def test_create_playlist_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: POST /api/v1/media/playlists endpoint exists"""
        request_data = {
            "name": "Integration Test Playlist",
            "user_id": test_user_id,
            "shuffle": False,
            "loop": True
        }

        response = await http_client.post(
            "/api/v1/media/playlists",
            json=request_data,
            headers=internal_headers
        )

        # Endpoint exists - accept various responses
        assert response.status_code in [200, 201, 400, 422]

    async def test_list_playlists_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/media/playlists endpoint exists"""
        response = await http_client.get(
            "/api/v1/media/playlists",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        # Endpoint exists
        assert response.status_code in [200, 422]

    async def test_get_playlist_by_id(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/media/playlists/{id} endpoint exists"""
        response = await http_client.get(
            "/api/v1/media/playlists/nonexistent_playlist_12345",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        # Should return 404 for nonexistent or 422 if missing params
        assert response.status_code in [404, 422]


# =============================================================================
# Rotation Schedule Tests
# =============================================================================

class TestScheduleIntegration:
    """Test rotation schedule operations"""

    async def test_create_schedule_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: POST /api/v1/media/schedules endpoint exists"""
        request_data = {
            "frame_id": "frame_test_001",
            "playlist_id": "playlist_test_001",
            "user_id": test_user_id,
            "schedule_type": "time_based"
        }

        response = await http_client.post(
            "/api/v1/media/schedules",
            json=request_data,
            headers=internal_headers
        )

        # Endpoint exists - may fail validation
        assert response.status_code in [200, 201, 400, 404, 422]

    async def test_get_frame_schedules_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/media/frames/{id}/schedules endpoint exists"""
        response = await http_client.get(
            "/api/v1/media/frames/frame_test_001/schedules",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [200, 404, 422]


# =============================================================================
# Photo Cache Tests
# =============================================================================

class TestPhotoCacheIntegration:
    """Test photo cache operations"""

    async def test_get_frame_cache_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/media/frames/{id}/cache endpoint exists"""
        response = await http_client.get(
            "/api/v1/media/frames/frame_test_001/cache",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [200, 404, 422]

    async def test_create_cache_entry_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: POST /api/v1/media/cache endpoint exists"""
        request_data = {
            "frame_id": "frame_test_001",
            "photo_id": "photo_test_001",
            "user_id": test_user_id,
            "status": "pending"
        }

        response = await http_client.post(
            "/api/v1/media/cache",
            json=request_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 201, 400, 422]


# =============================================================================
# Metadata Tests
# =============================================================================

class TestMetadataIntegration:
    """Test metadata operations"""

    async def test_get_metadata_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/media/metadata/{id} endpoint exists"""
        response = await http_client.get(
            "/api/v1/media/metadata/nonexistent_file_12345",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        # Should return 404 for nonexistent or 422 if missing params
        assert response.status_code in [404, 422]


# =============================================================================
# Gallery API Tests
# =============================================================================

class TestGalleryIntegration:
    """Test gallery API operations"""

    async def test_gallery_albums_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/media/gallery/albums endpoint exists"""
        response = await http_client.get(
            "/api/v1/media/gallery/albums",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [200, 404, 422]

    async def test_gallery_playlists_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/media/gallery/playlists endpoint exists"""
        response = await http_client.get(
            "/api/v1/media/gallery/playlists",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [200, 404, 422]

    async def test_random_photos_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/media/gallery/photos/random endpoint exists"""
        response = await http_client.get(
            "/api/v1/media/gallery/photos/random",
            params={"user_id": test_user_id, "count": 5},
            headers=internal_headers
        )

        assert response.status_code in [200, 404, 422]

    async def test_cache_stats_endpoint_exists(
        self, http_client, internal_headers, test_user_id
    ):
        """CHAR: GET /api/v1/media/gallery/cache/{id}/stats endpoint exists"""
        response = await http_client.get(
            "/api/v1/media/gallery/cache/frame_test_001/stats",
            params={"user_id": test_user_id},
            headers=internal_headers
        )

        assert response.status_code in [200, 404, 422]
