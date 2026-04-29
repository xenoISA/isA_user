import pytest

from tests.smoke._crud_api_smoke import CrudApiSmokeBase

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestAccountSmoke(CrudApiSmokeBase):
    service_name = "account_service"
    env_var_name = "ACCOUNT_BASE_URL"
    create_path = "/api/v1/accounts/ensure"
    list_path = "/api/v1/accounts"
    get_path = "/api/v1/accounts/profile/{user_id}"
    update_path = "/api/v1/accounts/profile/{user_id}"
    delete_path = "/api/v1/accounts/profile/{user_id}"
    id_keys = ("user_id",)

    def build_payload(self, suffix: str) -> dict:
        return {
            "user_id": f"acct_smoke_{suffix}",
            "email": f"acct_smoke_{suffix}@example.com",
            "name": f"Account Smoke {suffix}",
            "subscription_plan": "free",
        }

    def build_update_payload(self, suffix: str, state: dict) -> dict:
        return {
            "name": f"Updated Account {suffix}",
            "email": f"updated_acct_{suffix}@example.com",
        }

    def list_params(self, state: dict) -> dict:
        return {"page": 1, "page_size": 5}
