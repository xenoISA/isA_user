"""L4 API — Project organization-scope route contract."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.api, pytest.mark.tdd]


def test_project_api_accepts_and_returns_organization_scope():
    from microservices.project_service.main import (
        app,
        get_authenticated_caller,
        get_service,
    )

    service = MagicMock()
    service.create_project = AsyncMock(
        return_value={
            "id": "project-1",
            "user_id": "member-1",
            "org_id": "org-1",
            "organization_id": "org-1",
            "name": "Team Project",
            "description": None,
            "custom_instructions": None,
            "created_at": None,
            "updated_at": None,
        }
    )
    app.dependency_overrides[get_service] = lambda: service
    app.dependency_overrides[get_authenticated_caller] = lambda: "member-1"

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/projects",
            json={"name": "Team Project", "organization_id": "org-1"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["organization_id"] == "org-1"
    service.create_project.assert_awaited_once_with(
        "member-1",
        "Team Project",
        None,
        None,
        organization_id="org-1",
    )
