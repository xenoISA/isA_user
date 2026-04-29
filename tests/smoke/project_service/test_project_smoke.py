import pytest

from tests.smoke._crud_api_smoke import CrudApiSmokeBase

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestProjectSmoke(CrudApiSmokeBase):
    service_name = "project_service"
    env_var_name = "PROJECT_BASE_URL"
    create_path = "/api/v1/projects"
    list_path = "/api/v1/projects"
    get_path = "/api/v1/projects/{project_id}"
    update_path = "/api/v1/projects/{project_id}"
    delete_path = "/api/v1/projects/{project_id}"
    create_success_statuses = (201,)
    id_keys = ("project_id", "id")

    def build_payload(self, suffix: str) -> dict:
        return {
            "name": f"Smoke Project {suffix}",
            "description": "Project created by smoke test",
            "custom_instructions": "Keep responses concise.",
        }

    def list_params(self, state: dict) -> dict:
        return {"limit": 10, "offset": 0}

    def build_update_payload(self, suffix: str, state: dict) -> dict:
        return {
            "name": f"Updated Smoke Project {suffix}",
            "description": "Updated by smoke test",
        }
