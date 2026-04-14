"""E2E smoke test: storage -> media -> album lifecycle.

Validates the complete asset lifecycle across three services:
  1. Upload file -> storage_service (port 8209)
  2. Create media version -> media_service (port 8222)
  3. Update AI metadata -> media_service
  4. Create album -> album_service (port 8219)
  5. Add photo to album -> album_service
  6. Verify album photos include our file

Requires services running via deployment/local-dev.sh.

Usage:
    pytest tests/smoke/test_media_album_storage_e2e.py -v
"""

import io
import os
import uuid

import httpx
import pytest

from tests.smoke.conftest import base_url_for

pytestmark = pytest.mark.smoke

STORAGE_URL = os.getenv("STORAGE_SERVICE_URL") or base_url_for("storage_service")
MEDIA_URL = os.getenv("MEDIA_SERVICE_URL") or base_url_for("media_service")
ALBUM_URL = os.getenv("ALBUM_SERVICE_URL") or base_url_for("album_service")

TEST_USER = f"smoke_e2e_{uuid.uuid4().hex[:8]}"
TIMEOUT = 15.0

# Internal service header used to bypass auth in dev/test mode
INTERNAL_HEADERS = {
    "X-Internal-Call": "true",
    "X-Internal-Service": "true",
    "X-Internal-Service-Secret": "dev-internal-secret-change-in-production",
}


async def _service_available(url: str) -> bool:
    """Check whether a service is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url}/health", headers=INTERNAL_HEADERS)
            return resp.status_code in (200, 204)
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


@pytest.mark.asyncio
class TestMediaAlbumStorageE2E:
    """End-to-end smoke test for the media/album/storage pipeline."""

    # ------------------------------------------------------------------
    # Lifecycle state shared across ordered test methods
    # ------------------------------------------------------------------
    _file_id: str | None = None
    _version_id: str | None = None
    _album_id: str | None = None

    # ------------------------------------------------------------------
    # Pre-flight: skip entire class if any service is down
    # ------------------------------------------------------------------

    @pytest.fixture(autouse=True, scope="class")
    async def require_services(self):
        """Skip all tests if the required services are not running."""
        for name, url in [
            ("storage_service", STORAGE_URL),
            ("media_service", MEDIA_URL),
            ("album_service", ALBUM_URL),
        ]:
            if not await _service_available(url):
                pytest.skip(
                    f"{name} not reachable at {url}. "
                    "Start services with deployment/local-dev.sh --run"
                )

    # ------------------------------------------------------------------
    # Step 1: Upload a file to storage_service
    # ------------------------------------------------------------------

    async def test_01_upload_file(self):
        """Upload a small test image to storage_service."""
        # Create a minimal 1x1 PNG (67 bytes)
        png_bytes = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
            b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00"
            b"\x00\x00\x00IEND\xaeB`\x82"
        )

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{STORAGE_URL}/api/v1/storage/files/upload",
                headers=INTERNAL_HEADERS,
                data={
                    "user_id": TEST_USER,
                    "access_level": "private",
                    "tags": '["smoke-test", "e2e"]',
                    "enable_indexing": "false",
                },
                files={"file": ("smoke_test.png", io.BytesIO(png_bytes), "image/png")},
            )

        assert resp.status_code == 200, (
            f"Upload failed ({resp.status_code}): {resp.text}"
        )
        data = resp.json()
        assert "file_id" in data, f"Response missing file_id: {data}"
        TestMediaAlbumStorageE2E._file_id = data["file_id"]

    # ------------------------------------------------------------------
    # Step 2: Create a media version referencing that file
    # ------------------------------------------------------------------

    async def test_02_create_media_version(self):
        """Create a photo version in media_service for the uploaded file."""
        file_id = TestMediaAlbumStorageE2E._file_id
        assert file_id, "No file_id from step 1"

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{MEDIA_URL}/api/v1/media/versions",
                headers=INTERNAL_HEADERS,
                params={"user_id": TEST_USER},
                json={
                    "photo_id": file_id,
                    "version_name": "smoke-test-original",
                    "version_type": "original",
                    "file_id": file_id,
                },
            )

        assert resp.status_code == 200, (
            f"Create version failed ({resp.status_code}): {resp.text}"
        )
        data = resp.json()
        assert "version_id" in data, f"Response missing version_id: {data}"
        TestMediaAlbumStorageE2E._version_id = data["version_id"]

    # ------------------------------------------------------------------
    # Step 3: Update AI metadata for the file
    # ------------------------------------------------------------------

    async def test_03_update_ai_metadata(self):
        """Attach AI metadata to the uploaded file via media_service."""
        file_id = TestMediaAlbumStorageE2E._file_id
        assert file_id, "No file_id from step 1"

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.put(
                f"{MEDIA_URL}/api/v1/media/metadata/{file_id}",
                headers=INTERNAL_HEADERS,
                params={"user_id": TEST_USER},
                json={
                    "ai_labels": ["smoke-test", "automated"],
                    "ai_objects": ["test-object"],
                    "ai_scenes": ["test-scene"],
                    "ai_colors": ["#FF0000"],
                    "quality_score": 0.95,
                },
            )

        assert resp.status_code == 200, (
            f"Update metadata failed ({resp.status_code}): {resp.text}"
        )
        data = resp.json()
        assert data.get("ai_labels") == ["smoke-test", "automated"], (
            f"AI labels mismatch: {data}"
        )

    # ------------------------------------------------------------------
    # Step 4: Create an album in album_service
    # ------------------------------------------------------------------

    async def test_04_create_album(self):
        """Create a test album in album_service."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{ALBUM_URL}/api/v1/albums",
                headers=INTERNAL_HEADERS,
                params={"user_id": TEST_USER},
                json={
                    "name": f"Smoke Test Album {uuid.uuid4().hex[:6]}",
                    "description": "E2E smoke test album - safe to delete",
                    "auto_sync": False,
                    "tags": ["smoke-test", "e2e"],
                },
            )

        assert resp.status_code == 201, (
            f"Create album failed ({resp.status_code}): {resp.text}"
        )
        data = resp.json()
        assert "album_id" in data, f"Response missing album_id: {data}"
        TestMediaAlbumStorageE2E._album_id = data["album_id"]

    # ------------------------------------------------------------------
    # Step 5: Add the photo to the album
    # ------------------------------------------------------------------

    async def test_05_add_photo_to_album(self):
        """Add the uploaded photo to the album."""
        album_id = TestMediaAlbumStorageE2E._album_id
        file_id = TestMediaAlbumStorageE2E._file_id
        assert album_id, "No album_id from step 4"
        assert file_id, "No file_id from step 1"

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{ALBUM_URL}/api/v1/albums/{album_id}/photos",
                headers=INTERNAL_HEADERS,
                params={"user_id": TEST_USER},
                json={"photo_ids": [file_id]},
            )

        assert resp.status_code == 200, (
            f"Add photo failed ({resp.status_code}): {resp.text}"
        )

    # ------------------------------------------------------------------
    # Step 6: Verify the album contains our photo
    # ------------------------------------------------------------------

    async def test_06_verify_album_photos(self):
        """Verify the album lists the photo we added."""
        album_id = TestMediaAlbumStorageE2E._album_id
        file_id = TestMediaAlbumStorageE2E._file_id
        assert album_id, "No album_id from step 4"
        assert file_id, "No file_id from step 1"

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{ALBUM_URL}/api/v1/albums/{album_id}/photos",
                headers=INTERNAL_HEADERS,
                params={"user_id": TEST_USER},
            )

        assert resp.status_code == 200, (
            f"Get album photos failed ({resp.status_code}): {resp.text}"
        )
        data = resp.json()
        photo_ids = [p.get("file_id") or p.get("photo_id") for p in data.get("photos", [])]
        assert file_id in photo_ids, (
            f"Uploaded file {file_id} not found in album photos: {photo_ids}"
        )

    # ------------------------------------------------------------------
    # Cleanup: best-effort removal of test data
    # ------------------------------------------------------------------

    async def test_99_cleanup(self):
        """Clean up test resources (best-effort, failures are warnings)."""
        warnings = []

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Delete album
            if TestMediaAlbumStorageE2E._album_id:
                resp = await client.delete(
                    f"{ALBUM_URL}/api/v1/albums/{TestMediaAlbumStorageE2E._album_id}",
                    headers=INTERNAL_HEADERS,
                    params={"user_id": TEST_USER},
                )
                if resp.status_code not in (200, 204, 404):
                    warnings.append(f"Album delete: {resp.status_code}")

            # Delete media version
            if TestMediaAlbumStorageE2E._version_id:
                resp = await client.delete(
                    f"{MEDIA_URL}/api/v1/media/versions/{TestMediaAlbumStorageE2E._version_id}",
                    headers=INTERNAL_HEADERS,
                    params={"user_id": TEST_USER},
                )
                if resp.status_code not in (200, 204, 404):
                    warnings.append(f"Version delete: {resp.status_code}")

            # Delete file from storage
            if TestMediaAlbumStorageE2E._file_id:
                resp = await client.delete(
                    f"{STORAGE_URL}/api/v1/storage/files/{TestMediaAlbumStorageE2E._file_id}",
                    headers=INTERNAL_HEADERS,
                    params={"user_id": TEST_USER, "permanent": "true"},
                )
                if resp.status_code not in (200, 204, 404):
                    warnings.append(f"File delete: {resp.status_code}")

        if warnings:
            pytest.warns(UserWarning, match="|".join(warnings)) if False else None
            print(f"  Cleanup warnings: {warnings}")
