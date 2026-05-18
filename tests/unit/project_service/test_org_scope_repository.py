"""L1 Unit — Project repository organization-scope SQL contracts."""

import pytest

from microservices.project_service.project_repository import ProjectRepository
from tests.unit.project_service.test_repository import _make_mock_db, _make_repo

pytestmark = [pytest.mark.unit, pytest.mark.tdd, pytest.mark.asyncio]


async def test_create_project_persists_org_scope_and_response_aliases():
    mock_db = _make_mock_db()
    repository = _make_repo(mock_db)
    repository._tables_initialized = True

    result = await ProjectRepository.create_project(
        repository,
        "owner-1",
        "Team Project",
        organization_id="org-1",
    )

    sql = mock_db.execute.await_args.args[0]
    params = mock_db.execute.await_args.kwargs["params"]
    assert "org_id" in sql
    assert "org-1" in params
    assert result["org_id"] == "org-1"
    assert result["organization_id"] == "org-1"


async def test_list_projects_can_filter_by_org_scope():
    mock_db = _make_mock_db(query_result=[{"id": "project-1", "org_id": "org-1"}])
    repository = _make_repo(mock_db)
    repository._tables_initialized = True

    results = await ProjectRepository.list_projects(
        repository,
        "member-1",
        organization_id="org-1",
    )

    sql = mock_db.query.await_args.args[0]
    params = mock_db.query.await_args.kwargs["params"]
    assert "org_id = $1" in sql
    assert params[:3] == ["org-1", 50, 0]
    assert results[0]["organization_id"] == "org-1"


async def test_count_projects_keeps_user_owned_compatibility_by_default():
    mock_db = _make_mock_db(query_result=[{"cnt": 3}])
    repository = _make_repo(mock_db)
    repository._tables_initialized = True

    count = await ProjectRepository.count_projects(repository, "owner-1")

    sql = mock_db.query.await_args.args[0]
    assert "WHERE user_id = $1" in sql
    assert "org_id" not in sql
    assert count == 3
