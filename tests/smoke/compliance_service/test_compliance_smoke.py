import pytest

from tests.smoke._crud_api_smoke import CrudApiSmokeBase

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestComplianceSmoke(CrudApiSmokeBase):
    service_name = "compliance_service"
    env_var_name = "COMPLIANCE_BASE_URL"
    create_path = "/api/v1/compliance/policies"
    list_path = "/api/v1/compliance/policies"
    get_path = "/api/v1/compliance/policies/{policy_id}"
    id_keys = ("policy_id", "id")

    def build_payload(self, suffix: str) -> dict:
        return {
            "policy_name": f"Smoke Policy {suffix}",
            "organization_id": f"org_smoke_{suffix}",
            "content_types": ["text"],
            "check_types": ["toxicity"],
            "rules": {"blocked_terms": ["forbidden"]},
            "thresholds": {"toxicity": 0.8},
            "auto_block": True,
            "require_human_review": False,
            "notification_enabled": True,
        }

    def request_json(self, state: dict) -> dict:
        return {
            "policy_name": state["policy_name"],
            "organization_id": state["organization_id"],
            "content_types": state["content_types"],
            "check_types": state["check_types"],
            "rules": state["rules"],
            "thresholds": state["thresholds"],
            "auto_block": state["auto_block"],
            "require_human_review": state["require_human_review"],
            "notification_enabled": state["notification_enabled"],
        }

    def list_params(self, state: dict) -> dict:
        return {"organization_id": state["organization_id"]}
