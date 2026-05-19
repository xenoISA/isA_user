"""L1 Unit — Project GDPR export adapter behavior."""

import pytest

from microservices.project_service.project_repository import ProjectRepository
from microservices.project_service.project_service import ProjectService
from tests.unit.project_service.test_repository import _make_mock_db, _make_repo

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeProjectExportRepository:
    def __init__(self):
        self.export_calls = []
        self.file_calls = []
        self.projects = [
            {
                "id": "project-1",
                "user_id": "user-1",
                "org_id": "org-1",
                "organization_id": "org-1",
                "owner_id": "user-1",
                "name": "Launch Project",
                "description": "Private project notes",
                "custom_instructions": "Prefer project knowledge.",
            }
        ]
        self.files_by_project = {
            "project-1": [
                {
                    "id": "file-1",
                    "project_id": "project-1",
                    "filename": "guide.md",
                    "file_type": "text/markdown",
                    "file_size": 42,
                    "storage_path": "storage/project-1/guide.md",
                }
            ]
        }

    async def list_projects_for_export(
        self, user_id, limit=100, offset=0, organization_id=None
    ):
        self.export_calls.append(
            {
                "user_id": user_id,
                "limit": limit,
                "offset": offset,
                "organization_id": organization_id,
            }
        )
        return self.projects if offset == 0 else []

    async def list_project_files(self, project_id, limit=100, offset=0):
        self.file_calls.append(
            {
                "project_id": project_id,
                "limit": limit,
                "offset": offset,
            }
        )
        return self.files_by_project.get(project_id, []) if offset == 0 else []


async def test_export_user_data_collects_subject_projects_and_file_metadata():
    repository = FakeProjectExportRepository()
    service = ProjectService(repository=repository)

    result = await service.export_user_data(
        user_id="user-1",
        organization_id="org-1",
        request_id="gdpr_req_1",
    )

    assert result["schema_version"] == "project-export-v1"
    assert result["service"] == "project_service"
    assert result["user_id"] == "user-1"
    assert result["organization_id"] == "org-1"
    assert result["gdpr_request_id"] == "gdpr_req_1"
    assert result["projects"][0]["id"] == "project-1"
    assert result["project_files"]["project-1"][0]["id"] == "file-1"
    assert result["counts"] == {
        "records": 2,
        "sections": {
            "projects": 1,
            "project_files": 1,
        },
    }
    assert repository.export_calls == [
        {
            "user_id": "user-1",
            "limit": 100,
            "offset": 0,
            "organization_id": "org-1",
        }
    ]
    assert repository.file_calls == [
        {
            "project_id": "project-1",
            "limit": 500,
            "offset": 0,
        }
    ]


async def test_list_projects_for_export_filters_by_subject_and_org_without_hiding_archived():
    mock_db = _make_mock_db(
        query_result=[
            {
                "id": "project-1",
                "user_id": "user-1",
                "owner_id": "user-1",
                "org_id": "org-1",
            }
        ]
    )
    repository = _make_repo(mock_db)
    repository._tables_initialized = True

    results = await ProjectRepository.list_projects_for_export(
        repository,
        "user-1",
        limit=25,
        offset=5,
        organization_id="org-1",
    )

    sql = mock_db.query.await_args.args[0]
    params = mock_db.query.await_args.kwargs["params"]
    assert "(user_id = $1 OR owner_id = $1)" in sql
    assert "org_id = $2" in sql
    assert "archived_at IS NULL" not in sql
    assert params == ["user-1", "org-1", 25, 5]
    assert results[0]["organization_id"] == "org-1"
