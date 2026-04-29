import pytest

from tests.smoke._crud_api_smoke import CrudApiSmokeBase

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestAuditSmoke(CrudApiSmokeBase):
    service_name = "audit_service"
    env_var_name = "AUDIT_BASE_URL"
    create_path = "/api/v1/audit/events"
    list_path = "/api/v1/audit/events"
    id_keys = ("event_id", "audit_id", "id")

    def build_payload(self, suffix: str) -> dict:
        return {
            "event_type": "smoke.audit.event",
            "user_id": f"audit_user_{suffix}",
            "resource_type": "smoke_resource",
            "resource_id": f"res_{suffix}",
            "action": "created",
            "result": "success",
            "metadata": {"smoke": True},
        }

    def list_params(self, state: dict) -> dict:
        return {"limit": 10}
