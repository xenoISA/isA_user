"""L2 Component — Project API forwards organization scope to service layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = [pytest.mark.component, pytest.mark.tdd, pytest.mark.asyncio]


@pytest.fixture
def mock_service():
    service = MagicMock()
    service.create_project = AsyncMock(
        return_value={
            "id": "project-1",
            "user_id": "member-1",
            "org_id": "org-1",
            "organization_id": "org-1",
            "name": "Team Project",
            "description": None,
            "custom_instructions": None,
            "created_at": None,
            "updated_at": None,
        }
    )
    service.list_projects = AsyncMock(
        return_value=[
            {
                "id": "project-1",
                "user_id": "owner-1",
                "org_id": "org-1",
                "organization_id": "org-1",
                "name": "Team Project",
                "description": None,
                "custom_instructions": None,
                "created_at": None,
                "updated_at": None,
            }
        ]
    )
    service.get_project = AsyncMock(return_value=service.list_projects.return_value[0])
    return service


@pytest.fixture
async def client(mock_service):
    from microservices.project_service.main import (
        app,
        get_authenticated_caller,
        get_service,
    )

    app.dependency_overrides[get_service] = lambda: mock_service
    app.dependency_overrides[get_authenticated_caller] = lambda: "member-1"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_create_project_forwards_organization_id(client, mock_service):
    response = await client.post(
        "/api/v1/projects",
        json={"name": "Team Project", "organization_id": "org-1"},
    )

    assert response.status_code == 201
    assert response.json()["organization_id"] == "org-1"
    mock_service.create_project.assert_awaited_once_with(
        "member-1",
        "Team Project",
        None,
        None,
        organization_id="org-1",
    )


async def test_list_projects_forwards_organization_filter(client, mock_service):
    response = await client.get("/api/v1/projects?organization_id=org-1")

    assert response.status_code == 200
    assert response.json()["projects"][0]["organization_id"] == "org-1"
    mock_service.list_projects.assert_awaited_once_with(
        "member-1",
        50,
        0,
        include_archived=False,
        starred_only=False,
        organization_id="org-1",
    )


async def test_get_project_forwards_organization_context(client, mock_service):
    response = await client.get("/api/v1/projects/project-1?organization_id=org-1")

    assert response.status_code == 200
    assert response.json()["organization_id"] == "org-1"
    mock_service.get_project.assert_awaited_once_with(
        "project-1",
        "member-1",
        organization_id="org-1",
    )
