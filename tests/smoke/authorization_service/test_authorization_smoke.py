import pytest

from tests.smoke._crud_api_smoke import CrudApiSmokeBase

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestAuthorizationSmoke(CrudApiSmokeBase):
    service_name = "authorization_service"
    env_var_name = "AUTHORIZATION_BASE_URL"
    create_path = "/api/v1/authorization/grant"
    list_path = "/api/v1/authorization/user-resources/{user_id}"
    update_path = "/api/v1/authorization/revoke"
    update_method = "post"
    id_keys = ("user_id",)

    def build_payload(self, suffix: str) -> dict:
        return {
            "user_id": f"authz_user_{suffix}",
            "resource_type": "api_endpoint",
            "resource_name": f"smoke_resource_{suffix}",
            "access_level": "read_write",
            "permission_source": "smoke_test",
            "granted_by_user_id": "system_smoke",
        }

    def build_update_payload(self, suffix: str, state: dict) -> dict:
        return {
            "user_id": state["user_id"],
            "resource_type": state["resource_type"],
            "resource_name": state["resource_name"],
            "revoked_by_user_id": "system_smoke",
        }
