import pytest

from tests.smoke._crud_api_smoke import CrudApiSmokeBase

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestMediaSmoke(CrudApiSmokeBase):
    service_name = "media_service"
    env_var_name = "MEDIA_BASE_URL"
    create_path = "/api/v1/media/gallery/playlists"
    list_path = "/api/v1/media/gallery/playlists"
    get_path = "/api/v1/media/gallery/playlists/{playlist_id}"
    update_path = "/api/v1/media/gallery/playlists/{playlist_id}"
    delete_path = "/api/v1/media/gallery/playlists/{playlist_id}"
    create_success_statuses = (201,)
    id_keys = ("playlist_id", "id")

    def build_payload(self, suffix: str) -> dict:
        return {
            "user_id": f"media_user_{suffix}",
            "name": f"Smoke Playlist {suffix}",
            "description": "Playlist created by smoke test",
            "playlist_type": "manual",
            "photo_ids": [],
            "album_ids": [],
            "rotation_type": "sequential",
            "transition_duration": 5,
        }

    def list_params(self, state: dict) -> dict:
        return {"user_id": state.get("user_id", f"media_user_{state['suffix']}")}

    def get_params(self, state: dict) -> dict:
        return {"user_id": state["user_id"]}

    def update_params(self, state: dict) -> dict:
        return {"user_id": state["user_id"]}

    def build_update_payload(self, suffix: str, state: dict) -> dict:
        return {
            "name": f"Updated Playlist {suffix}",
            "description": "Updated by smoke test",
        }
