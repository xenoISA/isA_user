"""TDD component tests for project knowledge file service behavior."""

from io import BytesIO

import pytest
from starlette.datastructures import UploadFile

from microservices.project_service.project_service import ProjectService
from microservices.project_service.protocols import (
    ProjectNotFoundError,
    ProjectServiceException,
)
from tests.component.golden.project_service.mocks import (
    MockProjectRepository,
    MockStorageServiceClient,
)

pytestmark = [pytest.mark.component, pytest.mark.tdd, pytest.mark.asyncio]


@pytest.fixture
def repository():
    repo = MockProjectRepository()
    repo.seed_project("proj1", "user1", "Knowledge Project")
    return repo


@pytest.fixture
def storage_client():
    return MockStorageServiceClient()


@pytest.fixture
def service(repository, storage_client):
    return ProjectService(
        repository=repository,
        storage_client=storage_client,
        event_bus=None,
    )


class TestProjectKnowledgeFiles:
    async def test_upload_project_file_creates_storage_backed_association(
        self, service, repository
    ):
        upload = UploadFile(
            filename="knowledge.md",
            file=BytesIO(b"# project knowledge"),
            headers={"content-type": "text/markdown"},
        )

        result = await service.upload_project_file("proj1", "user1", upload)

        assert result["project_id"] == "proj1"
        assert result["filename"] == "knowledge.md"
        assert result["file_type"] == "text/markdown"
        assert result["file_size"] == len(b"# project knowledge")

        persisted = await repository.get_project_file("proj1", result["id"])
        assert persisted == result

    async def test_list_project_files_returns_associated_files(
        self, service, repository
    ):
        await repository.create_project_file(
            "proj1",
            "file_1",
            "guide.md",
            "storage/guide.md",
            "text/markdown",
            42,
        )

        files = await service.list_project_files("proj1", "user1")

        assert len(files) == 1
        assert files[0]["id"] == "file_1"
        assert files[0]["filename"] == "guide.md"

    async def test_remove_project_file_deletes_storage_and_association(
        self, service, repository, storage_client
    ):
        await repository.create_project_file(
            "proj1",
            "file_1",
            "guide.md",
            "storage/guide.md",
            "text/markdown",
            42,
        )

        deleted = await service.delete_project_file("proj1", "file_1", "user1")

        assert deleted is True
        assert await repository.get_project_file("proj1", "file_1") is None
        assert storage_client.delete_result is True

    async def test_delete_missing_project_file_raises_not_found(self, service):
        with pytest.raises(ProjectNotFoundError):
            await service.delete_project_file("proj1", "missing", "user1")

    async def test_upload_failure_raises_service_exception(
        self, service, storage_client
    ):
        storage_client.should_fail_upload = True
        upload = UploadFile(
            filename="knowledge.md",
            file=BytesIO(b"# project knowledge"),
            headers={"content-type": "text/markdown"},
        )

        with pytest.raises(ProjectServiceException):
            await service.upload_project_file("proj1", "user1", upload)
