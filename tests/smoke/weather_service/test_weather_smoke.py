import pytest

from tests.smoke._crud_api_smoke import CrudApiSmokeBase

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestWeatherSmoke(CrudApiSmokeBase):
    service_name = "weather_service"
    env_var_name = "WEATHER_BASE_URL"
    create_path = "/api/v1/weather/locations"
    list_path = "/api/v1/weather/locations/{user_id}"
    delete_path = "/api/v1/weather/locations/{location_id}"
    create_success_statuses = (201,)
    id_keys = ("location_id", "id")

    def build_payload(self, suffix: str) -> dict:
        return {
            "user_id": f"weather_user_{suffix}",
            "location": "San Francisco",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "is_default": True,
            "nickname": f"Smoke Home {suffix}",
        }
