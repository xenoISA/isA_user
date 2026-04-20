"""
Project Service Component Tests (Golden Tests)

Tests ProjectService business logic with mocked repository and event bus.
No real I/O — uses dependency injection.
"""
import pytest

from microservices.project_service.project_service import ProjectService, MAX_PROJECTS_PER_USER
from microservices.project_service.protocols import (
    ProjectNotFoundError,
    ProjectPermissionError,
    ProjectLimitExceeded,
    InvalidProjectUpdate,
)
from tests.component.golden.project_service.mocks import MockProjectRepository
from tests.component.mocks.nats_mock import MockEventBus


class TestProjectServiceCRUD:
    """Happy-path CRUD operations."""

    @pytest.fixture
    def repository(self):
        return MockProjectRepository()

    @pytest.fixture
    def event_bus(self):
        return MockEventBus()

    @pytest.fixture
    def service(self, repository, event_bus):
        return ProjectService(repository=repository, event_bus=event_bus)

    @pytest.mark.asyncio
    async def test_create_project(self, service, event_bus):
        result = await service.create_project("user1", "My Project", "desc", "do X")
        assert result["name"] == "My Project"
        assert result["user_id"] == "user1"
        assert result["id"]
        event_bus.assert_event_published("project.create", {"user_id": "user1", "success": True})

    @pytest.mark.asyncio
    async def test_get_project(self, service, repository):
        repository.seed_project("proj1", "user1", "Test")
        result = await service.get_project("proj1", "user1")
        assert result["name"] == "Test"

    @pytest.mark.asyncio
    async def test_list_projects(self, service, repository):
        repository.seed_project("p1", "user1", "A")
        repository.seed_project("p2", "user1", "B")
        repository.seed_project("p3", "user2", "C")
        results = await service.list_projects("user1")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_update_project(self, service, repository, event_bus):
        repository.seed_project("proj1", "user1", "Old")
        result = await service.update_project("proj1", "user1", name="New")
        assert result["name"] == "New"
        event_bus.assert_event_published("project.update")

    @pytest.mark.asyncio
    async def test_delete_project(self, service, repository, event_bus):
        repository.seed_project("proj1", "user1", "Doomed")
        deleted = await service.delete_project("proj1", "user1")
        assert deleted is True
        event_bus.assert_event_published("project.delete")

    @pytest.mark.asyncio
    async def test_set_instructions(self, service, repository, event_bus):
        repository.seed_project("proj1", "user1", "Test")
        result = await service.set_instructions("proj1", "user1", "new instructions")
        assert result is True
        event_bus.assert_event_published("project.set_instructions")


class TestProjectServiceOwnership:
    """Ownership validation — 403 on cross-user access."""

    @pytest.fixture
    def repository(self):
        repo = MockProjectRepository()
        repo.seed_project("proj1", "user1", "User1 Project")
        return repo

    @pytest.fixture
    def service(self, repository):
        return ProjectService(repository=repository)

    @pytest.mark.asyncio
    async def test_get_other_users_project_raises_permission_error(self, service):
        with pytest.raises(ProjectPermissionError):
            await service.get_project("proj1", "user2")

    @pytest.mark.asyncio
    async def test_update_other_users_project_raises_permission_error(self, service):
        with pytest.raises(ProjectPermissionError):
            await service.update_project("proj1", "user2", name="Hack")

    @pytest.mark.asyncio
    async def test_delete_other_users_project_raises_permission_error(self, service):
        with pytest.raises(ProjectPermissionError):
            await service.delete_project("proj1", "user2")

    @pytest.mark.asyncio
    async def test_set_instructions_other_users_project_raises_permission_error(self, service):
        with pytest.raises(ProjectPermissionError):
            await service.set_instructions("proj1", "user2", "hack")


class TestProjectServiceNotFound:
    """404 on missing projects."""

    @pytest.fixture
    def service(self):
        return ProjectService(repository=MockProjectRepository())

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, service):
        with pytest.raises(ProjectNotFoundError):
            await service.get_project("ghost", "user1")

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, service):
        with pytest.raises(ProjectNotFoundError):
            await service.update_project("ghost", "user1", name="X")

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, service):
        with pytest.raises(ProjectNotFoundError):
            await service.delete_project("ghost", "user1")


class TestProjectServiceLimits:
    """Business rule: max projects per user."""

    @pytest.fixture
    def repository(self):
        repo = MockProjectRepository()
        for i in range(MAX_PROJECTS_PER_USER):
            repo.seed_project(f"proj_{i}", "user1", f"Project {i}")
        return repo

    @pytest.fixture
    def service(self, repository):
        return ProjectService(repository=repository)

    @pytest.mark.asyncio
    async def test_create_exceeds_limit(self, service):
        with pytest.raises(ProjectLimitExceeded):
            await service.create_project("user1", "One too many")


class TestProjectServiceEmptyUpdate:
    """Edge case: empty update payload."""

    @pytest.fixture
    def service(self):
        repo = MockProjectRepository()
        repo.seed_project("proj1", "user1", "Test")
        return ProjectService(repository=repo)

    @pytest.mark.asyncio
    async def test_empty_update_raises_invalid(self, service):
        with pytest.raises(InvalidProjectUpdate):
            await service.update_project("proj1", "user1")


class TestProjectServiceWithoutEventBus:
    """Service works fine without event bus (graceful degradation)."""

    @pytest.fixture
    def service(self):
        return ProjectService(repository=MockProjectRepository(), event_bus=None)

    @pytest.mark.asyncio
    async def test_create_without_event_bus(self, service):
        result = await service.create_project("user1", "No Events")
        assert result["name"] == "No Events"
