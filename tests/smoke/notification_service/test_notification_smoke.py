import os

import httpx
import pytest

from tests.smoke._crud_api_smoke import CrudApiSmokeBase, internal_headers
from tests.smoke.conftest import resolve_base_url

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


def _info_url() -> str:
    base_url = resolve_base_url("notification_service", "NOTIFICATION_BASE_URL")
    if os.getenv("NOTIFICATION_BASE_URL"):
        return f"{base_url}/info"
    return (
        f"{resolve_base_url('notification_service', 'NOTIFICATION_BASE_URL', mode='direct')}"
        "/info"
    )


def _info_requires_direct_mode() -> bool:
    return os.getenv("SMOKE_MODE", "direct") == "gateway" and not os.getenv(
        "NOTIFICATION_BASE_URL"
    )


class TestNotificationSystemSmoke:
    async def test_service_info(self):
        if _info_requires_direct_mode():
            pytest.skip(
                "notification_service /info is not exposed through APISIX; "
                "use direct mode or set NOTIFICATION_BASE_URL explicitly"
            )

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(_info_url())
        assert response.status_code in [200, 503]


class TestNotificationTemplateSmoke(CrudApiSmokeBase):
    service_name = "notification_service"
    env_var_name = "NOTIFICATION_BASE_URL"
    create_path = "/api/v1/notifications/templates"
    list_path = "/api/v1/notifications/templates"
    get_path = "/api/v1/notifications/templates/{template_id}"
    update_path = "/api/v1/notifications/templates/{template_id}"
    delete_path = "/api/v1/notifications/templates/{template_id}"
    response_container_key = "template"
    id_keys = ("template_id", "id")

    def build_payload(self, suffix: str) -> dict:
        return {
            "name": f"Smoke Template {suffix}",
            "description": "Notification template created by smoke test",
            "type": "email",
            "subject": f"Smoke Subject {suffix}",
            "content": "Hello {{name}} from notification smoke",
            "variables": ["name"],
            "metadata": {"smoke": True},
        }

    def build_update_payload(self, suffix: str, state: dict) -> dict:
        return {
            "description": f"Updated notification smoke template {suffix}",
            "content": "Updated hello {{name}} from notification smoke",
            "status": "active",
            "metadata": {"smoke": True, "updated": True},
        }

    def request_headers(self, state: dict) -> dict[str, str]:
        return internal_headers("notification_smoke_user")
