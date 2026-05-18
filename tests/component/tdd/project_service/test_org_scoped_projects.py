"""L2 Component — ProjectService organization-scoped access behavior."""

import pytest

from microservices.project_service.project_service import ProjectService
from microservices.project_service.protocols import ProjectPermissionError
from tests.component.golden.project_service.mocks import MockProjectRepository

pytestmark = [pytest.mark.component, pytest.mark.tdd, pytest.mark.asyncio]


class MockOrganizationAccess:
    def __init__(self, readers=None, admins=None):
        self.readers = set(readers or [])
        self.admins = set(admins or [])

    async def check_user_access(self, organization_id: str, user_id: str) -> bool:
        return (organization_id, user_id) in self.readers or (
            organization_id,
            user_id,
        ) in self.admins

    async def check_admin_access(self, organization_id: str, user_id: str) -> bool:
        return (organization_id, user_id) in self.admins


@pytest.fixture
def repository():
    repo = MockProjectRepository()
    repo.seed_project(
        "org-project",
        "owner-1",
        "Org Project",
        organization_id="org-1",
    )
    repo.seed_project("solo-project", "owner-1", "Solo Project")
    return repo


async def test_create_org_project_requires_org_membership(repository):
    access = MockOrganizationAccess(readers={("org-1", "member-1")})
    service = ProjectService(repository=repository, organization_access=access)

    result = await service.create_project(
        "member-1",
        "Team Project",
        organization_id="org-1",
    )

    assert result["organization_id"] == "org-1"
    assert result["org_id"] == "org-1"


async def test_create_org_project_rejects_non_member(repository):
    service = ProjectService(
        repository=repository,
        organization_access=MockOrganizationAccess(),
    )

    with pytest.raises(ProjectPermissionError):
        await service.create_project("outsider-1", "Blocked", organization_id="org-1")


async def test_org_member_can_read_org_project_without_owning(repository):
    access = MockOrganizationAccess(readers={("org-1", "member-1")})
    service = ProjectService(repository=repository, organization_access=access)

    result = await service.get_project("org-project", "member-1")

    assert result["id"] == "org-project"
    assert result["organization_id"] == "org-1"


async def test_non_member_cannot_read_org_project(repository):
    service = ProjectService(
        repository=repository,
        organization_access=MockOrganizationAccess(),
    )

    with pytest.raises(ProjectPermissionError):
        await service.get_project("org-project", "outsider-1")


async def test_org_admin_can_update_org_project(repository):
    access = MockOrganizationAccess(admins={("org-1", "admin-1")})
    service = ProjectService(repository=repository, organization_access=access)

    result = await service.update_project("org-project", "admin-1", name="Updated")

    assert result["name"] == "Updated"
    assert result["organization_id"] == "org-1"


async def test_org_member_without_admin_cannot_update_org_project(repository):
    access = MockOrganizationAccess(readers={("org-1", "member-1")})
    service = ProjectService(repository=repository, organization_access=access)

    with pytest.raises(ProjectPermissionError):
        await service.update_project("org-project", "member-1", name="Blocked")


async def test_list_org_projects_requires_membership(repository):
    access = MockOrganizationAccess(readers={("org-1", "member-1")})
    service = ProjectService(repository=repository, organization_access=access)

    projects = await service.list_projects("member-1", organization_id="org-1")

    assert [project["id"] for project in projects] == ["org-project"]


async def test_user_owned_projects_keep_existing_owner_rule(repository):
    service = ProjectService(repository=repository, organization_access=None)

    with pytest.raises(ProjectPermissionError):
        await service.get_project("solo-project", "outsider-1")
