"""L1 Unit — Project repository initialization and persistence safeguards."""

import os
from unittest.mock import AsyncMock, MagicMock
from unittest.mock import patch

import pytest

from microservices.project_service.project_repository import ProjectRepository
from microservices.project_service.protocols import RepositoryError


_UNSET = object()


def _make_mock_db(*, execute_result=1, query_result=_UNSET):
    mock_db = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.execute = AsyncMock(return_value=execute_result)
    mock_db.query = AsyncMock(
        return_value=[] if query_result is _UNSET else query_result
    )
    return mock_db


def _make_repo(mock_db):
    repository = object.__new__(ProjectRepository)
    repository.schema = "project"
    repository.table = "projects"
    repository.files_table = "project_files"
    repository._tables_initialized = False
    repository.db = mock_db
    return repository


def test_repository_constructor_uses_discovery_and_asyncpg_signature():
    config_manager = MagicMock()
    config_manager.discover_service.return_value = ("db.internal", 15432)

    with patch(
        "microservices.project_service.project_repository.AsyncPostgresClient"
    ) as mock_client:
        ProjectRepository(config_manager)

    config_manager.discover_service.assert_called_once_with(
        service_name="postgres_service",
        default_host="localhost",
        default_port=5432,
        env_host_key="POSTGRES_HOST",
        env_port_key="POSTGRES_PORT",
    )
    kwargs = mock_client.call_args.kwargs
    assert kwargs["host"] == "db.internal"
    assert kwargs["port"] == 15432
    assert kwargs["database"] == os.getenv("POSTGRES_DB", "isa_platform")
    assert kwargs["username"] == os.getenv("POSTGRES_USER", "postgres")
    assert kwargs["password"] == os.getenv("POSTGRES_PASSWORD", "")
    assert kwargs["user_id"] == "project_service"
    assert kwargs["min_pool_size"] == 1
    assert kwargs["max_pool_size"] == 2
    assert "user" not in kwargs


@pytest.mark.asyncio
async def test_initialize_bootstraps_schema_once():
    repository = _make_repo(_make_mock_db())

    await ProjectRepository.initialize(repository)
    await ProjectRepository.initialize(repository)

    assert repository._tables_initialized is True
    assert repository.db.execute.await_count == 7


@pytest.mark.asyncio
async def test_create_project_raises_when_db_does_not_acknowledge_insert():
    repository = _make_repo(_make_mock_db(execute_result=None))
    repository._tables_initialized = True

    with pytest.raises(RepositoryError, match="Failed to create project"):
        await ProjectRepository.create_project(repository, "user_1", "Broken Project")


@pytest.mark.asyncio
async def test_list_projects_raises_when_db_query_returns_none():
    repository = _make_repo(_make_mock_db(query_result=None))
    repository._tables_initialized = True

    with pytest.raises(RepositoryError, match="Failed to list projects"):
        await ProjectRepository.list_projects(repository, "user_1")
