import pytest

from tests.smoke._crud_api_smoke import CrudApiSmokeBase

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestSharingSmoke(CrudApiSmokeBase):
    service_name = "sharing_service"
    env_var_name = "SHARING_BASE_URL"
    create_path = "/api/v1/sessions/{session_id}/shares"
    list_path = "/api/v1/sessions/{session_id}/shares"
    get_path = "/api/v1/shares/{share_token}"
    delete_path = "/api/v1/shares/{share_token}"
    id_keys = ("share_token", "token")

    def build_payload(self, suffix: str) -> dict:
        return {
            "session_id": f"session_smoke_{suffix}",
            "user_id": f"sharing_user_{suffix}",
            "permissions": "view_only",
            "expires_in_hours": 24,
        }

    def request_json(self, state: dict) -> dict:
        return {
            "permissions": state["permissions"],
            "expires_in_hours": state["expires_in_hours"],
        }

    def create_path_context(self, payload: dict) -> dict:
        return {"session_id": payload["session_id"]}
