"""Component endpoint tests for project knowledge file routes."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = [pytest.mark.component, pytest.mark.tdd, pytest.mark.asyncio]


@pytest.fixture
def mock_service():
    service = MagicMock()
    service.list_project_files = AsyncMock(
        return_value=[
            {
                "id": "file_1",
                "project_id": "proj1",
                "filename": "guide.md",
                "file_type": "text/markdown",
                "file_size": 42,
                "storage_path": "storage/guide.md",
                "created_at": "2026-04-24T00:00:00Z",
            }
        ]
    )
    service.upload_project_file = AsyncMock(
        return_value={
            "id": "file_1",
            "project_id": "proj1",
            "filename": "guide.md",
            "file_type": "text/markdown",
            "file_size": 42,
            "storage_path": "storage/guide.md",
            "created_at": "2026-04-24T00:00:00Z",
        }
    )
    service.delete_project_file = AsyncMock(return_value=True)
    return service


@pytest.fixture
async def client(mock_service):
    from microservices.project_service.main import (
        app,
        get_authenticated_caller,
        get_service,
    )

    app.dependency_overrides[get_service] = lambda: mock_service
    app.dependency_overrides[get_authenticated_caller] = lambda: "user1"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


class TestProjectFileEndpoints:
    async def test_list_project_files_returns_files_and_total(
        self, client, mock_service
    ):
        response = await client.get("/api/v1/projects/proj1/files")

        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["files"][0]["filename"] == "guide.md"
        mock_service.list_project_files.assert_awaited_once_with(
            "proj1", "user1", 100, 0
        )

    async def test_upload_project_file_accepts_multipart_file(
        self, client, mock_service
    ):
        response = await client.post(
            "/api/v1/projects/proj1/files",
            files={"file": ("guide.md", b"# knowledge", "text/markdown")},
        )

        assert response.status_code == 201
        assert response.json()["filename"] == "guide.md"
        mock_service.upload_project_file.assert_awaited_once()
        call = mock_service.upload_project_file.await_args
        assert call.args[0] == "proj1"
        assert call.args[1] == "user1"
        assert call.args[2].filename == "guide.md"

    async def test_delete_project_file_returns_204(self, client, mock_service):
        response = await client.delete("/api/v1/projects/proj1/files/file_1")

        assert response.status_code == 204
        mock_service.delete_project_file.assert_awaited_once_with(
            "proj1",
            "file_1",
            "user1",
        )
