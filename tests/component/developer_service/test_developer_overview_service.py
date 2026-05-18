from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from microservices.developer_service.developer_service import DeveloperOverviewService
from microservices.developer_service.models import FirstCallRequest, SetupStepStatus

pytestmark = [pytest.mark.component, pytest.mark.tdd, pytest.mark.asyncio]


class FakeOrganizationClient:
    def __init__(self, *, role="admin", permissions=None, found=True):
        self.role = role
        self.permissions = permissions or ["auth.api_keys.create"]
        self.found = found

    async def health(self):
        return True

    async def get_organization_context(self, *, user_id, organization_id):
        if not self.found:
            return None
        return {
            "organization": {
                "organization_id": organization_id,
                "name": "Acme",
                "status": "active",
            },
            "member": {
                "user_id": user_id,
                "role": self.role,
                "permissions": self.permissions,
                "status": "active",
            },
        }


class FakeProjectClient:
    def __init__(self, projects):
        self.projects = projects

    async def health(self):
        return True

    async def list_projects(self, **kwargs):
        return {"projects": self.projects, "total": len(self.projects)}


class FakeCredentialClient:
    def __init__(self, api_keys, verify_result=None):
        self.api_keys = api_keys
        self.verify_result = verify_result or {
            "valid": True,
            "key_id": "key-1",
            "project_id": "project-1",
        }

    async def health(self):
        return True

    async def list_api_keys(self, **kwargs):
        return {"success": True, "api_keys": self.api_keys, "total": len(self.api_keys)}

    async def verify_api_key(self, **kwargs):
        return self.verify_result


class FakeBillingClient:
    def __init__(self, payload=None):
        self.payload = payload or {
            "period": {
                "start": "2026-05-11T00:00:00+00:00",
                "end": "2026-05-18T00:00:00+00:00",
                "days": 7,
            },
            "totals": {"requests": 0, "tokens": 0, "cost": 0.0, "currency": "USD"},
            "daily": [],
            "warnings": [],
        }

    async def health(self):
        return True

    async def get_usage_overview(self, **kwargs):
        return self.payload


class TimeoutProjectClient:
    async def health(self):
        return False

    async def list_projects(self, **kwargs):
        raise TimeoutError("project service timed out")


class FakeModelClient:
    async def health(self):
        return True

    async def run_first_call(self, **kwargs):
        return {
            "request_id": "req-1",
            "trace_id": "trace-1",
            "trace_href": "/traces/trace-1",
            "latency_ms": 128,
            "usage": {
                "input_tokens": 8,
                "output_tokens": 4,
                "total_tokens": 12,
                "cost_usd": 0.002,
                "currency": "USD",
            },
            "timestamp": "2026-05-18T02:00:00+00:00",
        }


class FailingModelClient:
    async def health(self):
        return False

    async def run_first_call(self, **kwargs):
        raise RuntimeError("model failed")


class FailingTraceClient:
    async def health(self):
        return False

    async def get_trace(self, trace_id):
        raise TimeoutError("trace lookup timed out")


def _service(
    *,
    organization_client=None,
    project_client=None,
    credential_client=None,
    billing_client=None,
    model_client=None,
    trace_client=None,
):
    return DeveloperOverviewService(
        organization_client=organization_client or FakeOrganizationClient(),
        project_client=project_client
        or FakeProjectClient(
            [
                {
                    "project_id": "project-1",
                    "name": "Default Project",
                    "is_default": True,
                }
            ]
        ),
        credential_client=credential_client or FakeCredentialClient([]),
        billing_client=billing_client or FakeBillingClient(),
        model_client=model_client,
        trace_client=trace_client,
    )


async def test_overview_service_returns_backend_backed_contract_shape():
    service = _service()

    overview = await service.get_overview(
        user_id="user-1",
        organization_id="org-1",
        project_id="project-1",
        period_days=7,
    )

    assert overview.user_id == "user-1"
    assert overview.organization.id == "org-1"
    assert overview.selected_project.id == "project-1"
    assert overview.usage.period.days == 7
    assert overview.next_action.id == "create_credential"
    assert overview.organization.role == "admin"
    assert overview.projects[0].id == "project-1"


async def test_overview_service_uses_injected_dependency_statuses():
    project_client = AsyncMock()
    project_client.health.return_value = True
    auth_client = AsyncMock()
    auth_client.health.return_value = False

    service = DeveloperOverviewService(
        project_client=project_client,
        credential_client=auth_client,
    )

    health = await service.get_dependency_health()

    assert health["project_service"] == "healthy"
    assert health["auth_service"] == "unhealthy"
    assert health["billing_service"] == "not_configured"
    project_client.health.assert_awaited_once()
    auth_client.health.assert_awaited_once()


async def test_overview_marks_no_org_as_first_setup_action():
    service = _service(organization_client=FakeOrganizationClient(found=False))

    overview = await service.get_overview(
        user_id="user-1",
        organization_id="org-missing",
        period_days=7,
    )

    steps = {step.id: step for step in overview.setup.steps}
    assert steps["organization"].status == SetupStepStatus.TODO
    assert steps["project"].status == SetupStepStatus.BLOCKED
    assert overview.next_action.id == "select_organization"


async def test_overview_marks_no_project_before_credentials():
    service = _service(project_client=FakeProjectClient([]))

    overview = await service.get_overview(
        user_id="user-1",
        organization_id="org-1",
        period_days=7,
    )

    steps = {step.id: step for step in overview.setup.steps}
    assert steps["project"].status == SetupStepStatus.TODO
    assert steps["credential"].status == SetupStepStatus.BLOCKED
    assert overview.next_action.id == "create_project"


async def test_overview_marks_no_key_as_credential_todo():
    service = _service(credential_client=FakeCredentialClient([]))

    overview = await service.get_overview(
        user_id="user-1",
        organization_id="org-1",
        project_id="project-1",
        period_days=7,
    )

    steps = {step.id: step for step in overview.setup.steps}
    assert steps["credential"].status == SetupStepStatus.TODO
    assert steps["first_call"].status == SetupStepStatus.BLOCKED
    assert overview.next_action.id == "create_credential"


async def test_overview_marks_read_only_user_without_key():
    service = _service(
        organization_client=FakeOrganizationClient(role="viewer", permissions=[]),
        credential_client=FakeCredentialClient([]),
    )

    overview = await service.get_overview(
        user_id="user-1",
        organization_id="org-1",
        project_id="project-1",
        period_days=7,
    )

    steps = {step.id: step for step in overview.setup.steps}
    assert steps["credential"].status == SetupStepStatus.READ_ONLY
    assert overview.credentials.can_create is False
    assert overview.next_action.id == "request_api_key_access"


async def test_overview_marks_first_call_todo_after_active_key():
    service = _service(
        credential_client=FakeCredentialClient(
            [
                {
                    "key_id": "key-1",
                    "name": "Project key",
                    "project_id": "project-1",
                    "owner_type": "project",
                    "is_active": True,
                    "last_used_at": None,
                }
            ]
        )
    )

    overview = await service.get_overview(
        user_id="user-1",
        organization_id="org-1",
        project_id="project-1",
        period_days=7,
    )

    steps = {step.id: step for step in overview.setup.steps}
    assert steps["credential"].status == SetupStepStatus.COMPLETE
    assert steps["first_call"].status == SetupStepStatus.TODO
    assert overview.next_action.id == "run_first_call"


async def test_overview_marks_complete_when_usage_exists():
    service = _service(
        credential_client=FakeCredentialClient(
            [
                {
                    "key_id": "key-1",
                    "project_id": "project-1",
                    "owner_type": "project",
                    "is_active": True,
                    "last_used_at": datetime.now(tz=timezone.utc).isoformat(),
                }
            ]
        ),
        billing_client=FakeBillingClient(
            {
                "period": {
                    "start": "2026-05-11T00:00:00+00:00",
                    "end": "2026-05-18T00:00:00+00:00",
                    "days": 7,
                },
                "totals": {
                    "requests": 3,
                    "tokens": 1200,
                    "cost": 0.42,
                    "currency": "USD",
                },
                "daily": [
                    {
                        "date": "2026-05-18",
                        "requests": 3,
                        "tokens": 1200,
                        "cost": 0.42,
                    }
                ],
            }
        ),
    )

    overview = await service.get_overview(
        user_id="user-1",
        organization_id="org-1",
        project_id="project-1",
        period_days=7,
    )

    steps = {step.id: step for step in overview.setup.steps}
    assert steps["first_call"].status == SetupStepStatus.COMPLETE
    assert overview.first_call.tokens == 1200
    assert overview.next_action.id == "view_usage"


async def test_overview_returns_partial_data_on_dependency_timeout():
    service = _service(project_client=TimeoutProjectClient())

    overview = await service.get_overview(
        user_id="user-1",
        organization_id="org-1",
        period_days=7,
    )

    assert overview.organization.id == "org-1"
    assert overview.projects == []
    assert any(
        warning.source == "project_service" and warning.code == "dependency_timeout"
        for warning in overview.warnings
    )


async def test_first_call_success_returns_trace_usage_and_cost_without_secret():
    service = _service(
        credential_client=FakeCredentialClient(
            [
                {
                    "key_id": "key-1",
                    "project_id": "project-1",
                    "owner_type": "project",
                    "is_active": True,
                }
            ]
        ),
        model_client=FakeModelClient(),
    )

    response = await service.run_first_call(
        user_id="user-1",
        request=FirstCallRequest(
            organization_id="org-1",
            project_id="project-1",
            model="gpt-4.1-nano",
            api_key="isa_secret",
        ),
        auth_token="Bearer user-token",
    )

    payload = response.model_dump()
    assert response.success is True
    assert response.request_id == "req-1"
    assert response.trace_id == "trace-1"
    assert response.latency_ms == 128
    assert response.tokens == 12
    assert response.cost_usd == 0.002
    assert "isa_secret" not in str(payload)


async def test_first_call_invalid_key_returns_remediation():
    service = _service(
        credential_client=FakeCredentialClient(
            [],
            verify_result={
                "valid": False,
                "error": "invalid",
            },
        ),
        model_client=FakeModelClient(),
    )

    response = await service.run_first_call(
        user_id="user-1",
        request=FirstCallRequest(
            organization_id="org-1",
            project_id="project-1",
            model="gpt-4.1-nano",
            api_key="bad-key",
        ),
    )

    assert response.success is False
    assert response.status == "invalid_key"
    assert response.remediation.href == "/dashboard/developer/api-keys"


async def test_first_call_missing_project_returns_project_remediation():
    service = _service(
        project_client=FakeProjectClient([]),
        credential_client=FakeCredentialClient([]),
        model_client=FakeModelClient(),
    )

    response = await service.run_first_call(
        user_id="user-1",
        request=FirstCallRequest(
            organization_id="org-1",
            project_id="missing-project",
            model="gpt-4.1-nano",
        ),
    )

    assert response.success is False
    assert response.status == "missing_project"
    assert response.remediation.field == "project_id"


async def test_first_call_model_failure_returns_model_remediation():
    service = _service(
        credential_client=FakeCredentialClient(
            [
                {
                    "key_id": "key-1",
                    "project_id": "project-1",
                    "owner_type": "project",
                    "is_active": True,
                }
            ]
        ),
        model_client=FailingModelClient(),
    )

    response = await service.run_first_call(
        user_id="user-1",
        request=FirstCallRequest(
            organization_id="org-1",
            project_id="project-1",
            model="missing-model",
            api_key_id="key-1",
        ),
    )

    assert response.success is False
    assert response.status == "model_failed"
    assert response.remediation.field == "model"


async def test_first_call_success_survives_degraded_trace_lookup():
    service = _service(
        credential_client=FakeCredentialClient(
            [
                {
                    "key_id": "key-1",
                    "project_id": "project-1",
                    "owner_type": "project",
                    "is_active": True,
                }
            ]
        ),
        model_client=FakeModelClient(),
        trace_client=FailingTraceClient(),
    )

    response = await service.run_first_call(
        user_id="user-1",
        request=FirstCallRequest(
            organization_id="org-1",
            project_id="project-1",
            model="gpt-4.1-nano",
            api_key_id="key-1",
        ),
    )

    assert response.success is True
    assert any(
        warning.source == "trace_service" and warning.code == "trace_lookup_unavailable"
        for warning in response.warnings
    )
