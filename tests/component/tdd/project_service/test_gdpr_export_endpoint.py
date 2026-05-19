"""L2 Component — Project GDPR export endpoint is internal-service only."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from core.auth_dependencies import INTERNAL_SERVICE_SECRET

pytestmark = [pytest.mark.component, pytest.mark.tdd, pytest.mark.asyncio]


@pytest.fixture
def mock_service():
    service = MagicMock()
    service.export_user_data = AsyncMock(
        return_value={
            "schema_version": "project-export-v1",
            "service": "project_service",
            "user_id": "user-1",
            "organization_id": "org-1",
            "gdpr_request_id": "gdpr_req_1",
            "exported_at": "2026-05-19T00:00:00Z",
            "projects": [
                {
                    "id": "project-1",
                    "user_id": "user-1",
                    "org_id": "org-1",
                    "organization_id": "org-1",
                    "owner_id": "user-1",
                    "name": "Launch Project",
                    "description": None,
                    "custom_instructions": None,
                    "created_at": None,
                    "updated_at": None,
                    "starred_at": None,
                    "archived_at": None,
                }
            ],
            "project_files": {
                "project-1": [
                    {
                        "id": "file-1",
                        "project_id": "project-1",
                        "filename": "guide.md",
                        "file_type": "text/markdown",
                        "file_size": 42,
                        "storage_path": "storage/project-1/guide.md",
                        "created_at": None,
                    }
                ]
            },
            "counts": {"records": 2, "sections": {"projects": 1, "project_files": 1}},
        }
    )
    return service


@pytest.fixture
async def client(mock_service):
    from microservices.project_service.main import app, get_service

    app.dependency_overrides[get_service] = lambda: mock_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_export_project_data_requires_internal_service_headers(
    client, mock_service
):
    response = await client.get("/api/v1/projects/export?user_id=user-1")

    assert response.status_code == 403
    mock_service.export_user_data.assert_not_called()


async def test_export_project_data_forwards_subject_to_service(client, mock_service):
    response = await client.get(
        "/api/v1/projects/export",
        params={
            "user_id": "user-1",
            "organization_id": "org-1",
            "request_id": "gdpr_req_1",
        },
        headers={
            "X-Internal-Service": "true",
            "X-Internal-Service-Secret": INTERNAL_SERVICE_SECRET,
        },
    )

    assert response.status_code == 200
    assert response.json()["projects"][0]["id"] == "project-1"
    assert response.json()["project_files"]["project-1"][0]["id"] == "file-1"
    mock_service.export_user_data.assert_awaited_once_with(
        user_id="user-1",
        organization_id="org-1",
        request_id="gdpr_req_1",
    )
