import pytest

from tests.smoke._crud_api_smoke import CrudApiSmokeBase

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestAlbumSmoke(CrudApiSmokeBase):
    service_name = "album_service"
    env_var_name = "ALBUM_BASE_URL"
    create_path = "/api/v1/albums"
    list_path = "/api/v1/albums"
    get_path = "/api/v1/albums/{album_id}"
    update_path = "/api/v1/albums/{album_id}"
    delete_path = "/api/v1/albums/{album_id}"
    create_success_statuses = (201,)
    id_keys = ("album_id",)

    def build_payload(self, suffix: str) -> dict:
        return {
            "user_id": f"album_user_{suffix}",
            "name": f"Smoke Album {suffix}",
            "description": "Album created by smoke test",
            "auto_sync": False,
            "tags": ["smoke", "album"],
        }

    def request_json(self, state: dict) -> dict:
        return {
            "name": state["name"],
            "description": state["description"],
            "auto_sync": state["auto_sync"],
            "tags": state["tags"],
        }

    def create_params(self, payload: dict) -> dict:
        return {"user_id": payload["user_id"]}

    def list_params(self, state: dict) -> dict:
        return {
            "user_id": state.get("user_id", f"album_user_{state['suffix']}"),
            "limit": 5,
        }

    def get_params(self, state: dict) -> dict:
        return {"user_id": state["user_id"]}

    def update_params(self, state: dict) -> dict:
        return {"user_id": state["user_id"]}

    def delete_params(self, state: dict) -> dict:
        return {"user_id": state["user_id"]}

    def build_update_payload(self, suffix: str, state: dict) -> dict:
        return {"name": f"Updated Album {suffix}", "tags": ["smoke", "updated"]}
