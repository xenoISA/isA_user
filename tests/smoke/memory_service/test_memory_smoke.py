import pytest

from tests.smoke._crud_api_smoke import CrudApiSmokeBase

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestMemorySmoke(CrudApiSmokeBase):
    service_name = "memory_service"
    env_var_name = "MEMORY_BASE_URL"
    create_path = "/api/v1/memories"
    list_path = "/api/v1/memories"
    get_path = "/api/v1/memories/{memory_type}/{memory_id}"
    update_path = "/api/v1/memories/{memory_type}/{memory_id}"
    delete_path = "/api/v1/memories/{memory_type}/{memory_id}"
    id_keys = ("memory_id", "id")

    def build_payload(self, suffix: str) -> dict:
        return {
            "memory_type": "factual",
            "user_id": f"memory_user_{suffix}",
            "content": f"Smoke memory content {suffix}",
            "metadata": {"smoke": True},
        }

    def list_params(self, state: dict) -> dict:
        return {
            "user_id": state.get("user_id", f"memory_user_{state['suffix']}"),
            "limit": 5,
        }

    def get_params(self, state: dict) -> dict:
        return {"user_id": state["user_id"]}

    def update_params(self, state: dict) -> dict:
        return {"user_id": state["user_id"]}

    def delete_params(self, state: dict) -> dict:
        return {"user_id": state["user_id"]}

    def build_update_payload(self, suffix: str, state: dict) -> dict:
        return {
            "content": f"Updated smoke memory content {suffix}",
            "tags": ["smoke", "updated"],
        }
