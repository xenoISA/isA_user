from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from microservices.developer_service.developer_service import DeveloperOverviewService
from microservices.developer_service.models import SetupStepStatus

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
    def __init__(self, api_keys):
        self.api_keys = api_keys

    async def health(self):
        return True

    async def list_api_keys(self, **kwargs):
        return {"success": True, "api_keys": self.api_keys, "total": len(self.api_keys)}


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


def _service(
    *,
    organization_client=None,
    project_client=None,
    credential_client=None,
    billing_client=None,
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
