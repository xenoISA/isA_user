import pytest

from tests.smoke._crud_api_smoke import CrudApiSmokeBase

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestDeviceSmoke(CrudApiSmokeBase):
    service_name = "device_service"
    env_var_name = "DEVICE_BASE_URL"
    create_path = "/api/v1/devices"
    list_path = "/api/v1/devices"
    get_path = "/api/v1/devices/{device_id}"
    update_path = "/api/v1/devices/{device_id}"
    delete_path = "/api/v1/devices/{device_id}"
    id_keys = ("device_id", "id")

    def build_payload(self, suffix: str) -> dict:
        return {
            "device_name": f"Smoke Frame {suffix}",
            "device_type": "smart_frame",
            "manufacturer": "SmokeCorp",
            "model": "SF-2026",
            "serial_number": f"SN_SMOKE_{suffix}",
            "firmware_version": "1.0.0",
            "hardware_version": "1.0",
            "mac_address": f"AA:BB:CC:DD:{suffix[:2]}:{suffix[2:4]}",
            "connectivity_type": "wifi",
            "security_level": "standard",
            "owner_user_id": f"device_owner_{suffix}",
            "location": {
                "latitude": 39.9042,
                "longitude": 116.4074,
                "address": "Smoke Test Location",
            },
            "metadata": {"smoke": True},
            "tags": ["smoke", "device"],
        }

    def build_update_payload(self, suffix: str, state: dict) -> dict:
        return {
            "device_name": f"Updated Smoke Frame {suffix}",
            "firmware_version": "1.1.0",
            "tags": ["smoke", "updated"],
        }
