"""L5 Smoke — Project org-scope service contract import and happy path."""

import pytest

from microservices.project_service.project_service import ProjectService
from tests.component.golden.project_service.mocks import MockProjectRepository

pytestmark = [pytest.mark.smoke, pytest.mark.tdd, pytest.mark.asyncio]


class MockOrganizationAccess:
    async def check_user_access(self, organization_id: str, user_id: str) -> bool:
        return (organization_id, user_id) == ("org-1", "member-1")

    async def check_admin_access(self, organization_id: str, user_id: str) -> bool:
        return False


async def test_org_scoped_project_happy_path_smoke():
    repository = MockProjectRepository()
    service = ProjectService(
        repository=repository,
        organization_access=MockOrganizationAccess(),
    )

    created = await service.create_project(
        "member-1",
        "Team Project",
        organization_id="org-1",
    )
    fetched = await service.get_project(created["id"], "member-1")

    assert fetched["organization_id"] == "org-1"
