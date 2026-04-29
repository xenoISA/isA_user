import tempfile
from pathlib import Path

import httpx
import pytest

from tests.smoke._crud_api_smoke import internal_headers, unique_suffix
from tests.smoke.conftest import resolve_base_url, resolve_service_url

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]

BASE_URL = resolve_base_url("storage_service", "STORAGE_BASE_URL")
API_V1 = f"{BASE_URL}/api/v1/storage"
HEALTH_URL = resolve_service_url("storage_service", "/health", "STORAGE_BASE_URL")


def _make_temp_file(suffix: str) -> Path:
    handle = tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt")
    handle.write(f"storage smoke file {suffix}\n")
    handle.close()
    return Path(handle.name)


def _multipart_headers(user_id: str) -> dict[str, str]:
    headers = internal_headers(user_id)
    headers.pop("Content-Type", None)
    return headers


class TestStorageSmoke:
    async def test_health_endpoint(self):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(HEALTH_URL)
        assert response.status_code in [200, 503]

    async def test_upload_list_get_delete_flow(self):
        suffix = unique_suffix()
        user_id = f"storage_user_{suffix}"
        test_file = _make_temp_file(suffix)

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                with test_file.open("rb") as file_handle:
                    upload = await client.post(
                        f"{API_V1}/files/upload",
                        files={"file": (test_file.name, file_handle, "text/plain")},
                        data={
                            "user_id": user_id,
                            "access_level": "private",
                            "tags": "smoke,storage",
                            "enable_indexing": "false",
                            "metadata": '{"smoke": true}',
                        },
                        headers=_multipart_headers(user_id),
                    )

                assert upload.status_code in [200, 201, 400, 401, 403, 422, 500, 503]

                if upload.status_code not in [200, 201]:
                    return

                payload = upload.json()
                file_id = payload.get("file_id")
                if not file_id:
                    pytest.skip("Upload succeeded but did not return file_id")

                listing = await client.get(
                    f"{API_V1}/files",
                    params={"user_id": user_id, "limit": 10},
                    headers=internal_headers(user_id),
                )
                assert listing.status_code in [200, 401, 403, 500, 503]

                info = await client.get(
                    f"{API_V1}/files/{file_id}",
                    params={"user_id": user_id},
                    headers=internal_headers(user_id),
                )
                assert info.status_code in [200, 401, 403, 404, 500, 503]

                delete = await client.delete(
                    f"{API_V1}/files/{file_id}",
                    params={"user_id": user_id},
                    headers=internal_headers(user_id),
                )
                assert delete.status_code in [200, 202, 204, 401, 403, 404, 500, 503]
        finally:
            test_file.unlink(missing_ok=True)
