import pytest

from tests.smoke._crud_api_smoke import CrudApiSmokeBase

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestLocationSmoke(CrudApiSmokeBase):
    service_name = "location_service"
    env_var_name = "LOCATION_BASE_URL"
    create_path = "/api/v1/places"
    list_path = "/api/v1/places/user/{user_id}"
    get_path = "/api/v1/places/{place_id}"
    update_path = "/api/v1/places/{place_id}"
    delete_path = "/api/v1/places/{place_id}"
    id_keys = ("place_id", "id")

    def build_payload(self, suffix: str) -> dict:
        return {
            "user_id": f"location_user_{suffix}",
            "name": f"Smoke Place {suffix}",
            "category": "home",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "address": "123 Smoke Street",
        }

    def build_update_payload(self, suffix: str, state: dict) -> dict:
        return {"name": f"Updated Place {suffix}", "category": "work"}
