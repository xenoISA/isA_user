from unittest.mock import AsyncMock

import pytest

from microservices.developer_service.developer_service import DeveloperOverviewService

pytestmark = [pytest.mark.component, pytest.mark.tdd, pytest.mark.asyncio]


async def test_overview_service_returns_backend_backed_contract_shape():
    service = DeveloperOverviewService()

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
    assert {warning.source for warning in overview.warnings} >= {
        "project_service",
        "auth_service",
        "billing_service",
    }


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
