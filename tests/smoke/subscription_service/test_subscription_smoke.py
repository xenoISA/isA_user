import pytest

from tests.smoke._crud_api_smoke import CrudApiSmokeBase

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestSubscriptionSmoke(CrudApiSmokeBase):
    service_name = "subscription_service"
    env_var_name = "SUBSCRIPTION_BASE_URL"
    create_path = "/api/v1/subscriptions"
    list_path = "/api/v1/subscriptions"
    get_path = "/api/v1/subscriptions/{subscription_id}"
    update_path = "/api/v1/subscriptions/admin/{subscription_id}/tier"
    id_keys = ("subscription_id",)
    response_container_key = "subscription"

    def build_payload(self, suffix: str) -> dict:
        return {
            "user_id": f"sub_user_{suffix}",
            "tier_code": "free",
            "billing_cycle": "monthly",
            "metadata": {"smoke": True},
        }

    def list_params(self, state: dict) -> dict:
        return {"user_id": state.get("user_id", f"sub_user_{state['suffix']}")}

    def build_update_payload(self, suffix: str, state: dict) -> dict:
        return {"tier_code": "pro"}
