"""L1 Unit — Project organization-scope request and response models."""

import pytest

from microservices.project_service.models import CreateProjectRequest, ProjectResponse

pytestmark = [pytest.mark.unit, pytest.mark.tdd]


def test_create_project_request_accepts_organization_id():
    request = CreateProjectRequest(
        name="Team Project",
        organization_id="org-1",
    )

    assert request.organization_id == "org-1"


def test_project_response_exposes_org_id_and_organization_id_alias():
    response = ProjectResponse(
        id="project-1",
        user_id="owner-1",
        org_id="org-1",
        organization_id="org-1",
        name="Team Project",
    )

    payload = response.model_dump()

    assert payload["org_id"] == "org-1"
    assert payload["organization_id"] == "org-1"
