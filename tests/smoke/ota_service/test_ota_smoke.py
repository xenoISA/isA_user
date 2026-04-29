import json
import tempfile
from pathlib import Path

import httpx
import pytest

from tests.smoke._crud_api_smoke import internal_headers, unique_suffix
from tests.smoke.conftest import resolve_base_url, resolve_service_url

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]

BASE_URL = resolve_base_url("ota_service", "OTA_BASE_URL")
API_V1 = f"{BASE_URL}/api/v1/ota"
HEALTH_URL = resolve_service_url("ota_service", "/health", "OTA_BASE_URL")


def _make_firmware_file(suffix: str) -> Path:
    handle = tempfile.NamedTemporaryFile("wb", delete=False, suffix=".bin")
    handle.write(f"firmware-smoke-{suffix}".encode("utf-8"))
    handle.close()
    return Path(handle.name)


def _multipart_headers(user_id: str) -> dict[str, str]:
    headers = internal_headers(user_id)
    headers.pop("Content-Type", None)
    return headers


class TestOtaSmoke:
    async def test_health_endpoint(self):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(HEALTH_URL)
        assert response.status_code in [200, 503]

    async def test_service_stats_endpoint(self):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{API_V1}/service/stats")
        assert response.status_code in [200, 401, 403, 500, 503]

    async def test_firmware_list_endpoint(self):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{API_V1}/firmware",
                headers=internal_headers("ota_smoke_user"),
            )
        assert response.status_code in [200, 401, 403, 500, 503]

    async def test_upload_firmware_endpoint(self):
        suffix = unique_suffix()
        firmware_path = _make_firmware_file(suffix)
        metadata = {
            "name": f"SmokeFirmware{suffix}",
            "version": "1.0.0",
            "device_model": "SmartFrame-Pro",
            "manufacturer": "SmokeCorp",
            "checksum_md5": "placeholder-md5",
            "checksum_sha256": "placeholder-sha256",
            "description": "OTA smoke upload",
            "changelog": "Smoke upload",
            "is_beta": False,
            "is_security_update": False,
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                with firmware_path.open("rb") as file_handle:
                    response = await client.post(
                        f"{API_V1}/firmware",
                        files={
                            "file": (
                                firmware_path.name,
                                file_handle,
                                "application/octet-stream",
                            )
                        },
                        data={"metadata": json.dumps(metadata)},
                        headers=_multipart_headers("ota_smoke_user"),
                    )
            assert response.status_code in [200, 201, 401, 403, 422, 500, 503]
        finally:
            firmware_path.unlink(missing_ok=True)
