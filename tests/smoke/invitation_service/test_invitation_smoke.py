import pytest

from tests.smoke._crud_api_smoke import CrudApiSmokeBase

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestInvitationSmoke(CrudApiSmokeBase):
    service_name = "invitation_service"
    env_var_name = "INVITATION_BASE_URL"
    create_path = "/api/v1/invitations/organizations/{organization_id}"
    list_path = "/api/v1/invitations/organizations/{organization_id}"
    get_path = "/api/v1/invitations/{invitation_token}"
    update_path = "/api/v1/invitations/{invitation_id}/resend"
    update_method = "post"
    delete_path = "/api/v1/invitations/{invitation_id}"
    id_keys = ("invitation_id", "invitation_token", "id")

    def build_payload(self, suffix: str) -> dict:
        return {
            "organization_id": f"org_smoke_{suffix}",
            "email": f"invite_{suffix}@example.com",
            "role": "member",
            "message": "Invitation created by smoke test",
            "inviter_user_id": f"inviter_{suffix}",
        }

    def request_json(self, state: dict) -> dict:
        return {
            "email": state["email"],
            "role": state["role"],
            "message": state["message"],
        }

    def create_path_context(self, payload: dict) -> dict:
        return {"organization_id": payload["organization_id"]}

    def list_path_context(self, state: dict) -> dict:
        return {"organization_id": state["organization_id"]}

    def get_path_context(self, state: dict) -> dict:
        return {"invitation_token": state["invitation_token"]}

    def list_params(self, state: dict) -> dict:
        return {"limit": 5, "offset": 0}

    def build_update_payload(self, suffix: str, state: dict) -> dict | None:
        return {}
