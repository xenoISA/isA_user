import pytest
from fastapi.testclient import TestClient

from microservices.developer_service import main as developer_main
from microservices.developer_service.developer_service import DeveloperOverviewService

pytestmark = [pytest.mark.api, pytest.mark.tdd]


class CapturingOverviewService(DeveloperOverviewService):
    def __init__(self):
        super().__init__()
        self.last_auth_token = None

    async def get_overview(self, **kwargs):
        self.last_auth_token = kwargs.get("auth_token")
        return await super().get_overview(**kwargs)


def _client_with_user(
    user_id: str = "user-1", service: DeveloperOverviewService = None
) -> TestClient:
    developer_main.app.dependency_overrides[
        developer_main.get_authenticated_caller
    ] = lambda: user_id
    developer_main.app.dependency_overrides[developer_main.get_developer_service] = (
        lambda: service or DeveloperOverviewService()
    )
    return TestClient(developer_main.app)


def test_overview_requires_authentication():
    client = TestClient(developer_main.app)

    response = client.get("/api/v1/developer/overview?organization_id=org-1")

    assert response.status_code == 401


def test_overview_requires_organization_context():
    client = _client_with_user()
    try:
        response = client.get("/api/v1/developer/overview")
    finally:
        developer_main.app.dependency_overrides.clear()

    assert response.status_code == 422


def test_overview_returns_typed_contract_for_authenticated_user():
    client = _client_with_user("user-1")
    try:
        response = client.get(
            "/api/v1/developer/overview",
            params={
                "organization_id": "org-1",
                "project_id": "project-1",
                "period_days": 7,
            },
        )
    finally:
        developer_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == "user-1"
    assert payload["organization"]["id"] == "org-1"
    assert payload["selected_project"]["id"] == "project-1"
    assert payload["setup"]["steps"]
    assert payload["warnings"]


def test_overview_forwards_bearer_token_to_service():
    service = CapturingOverviewService()
    client = _client_with_user("user-1", service=service)
    try:
        response = client.get(
            "/api/v1/developer/overview",
            params={"organization_id": "org-1"},
            headers={"Authorization": "Bearer token-123"},
        )
    finally:
        developer_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert service.last_auth_token == "Bearer token-123"


def test_health_endpoint_reports_dependency_statuses():
    developer_main.app.dependency_overrides[
        developer_main.get_developer_service
    ] = lambda: DeveloperOverviewService()
    client = TestClient(developer_main.app)

    try:
        response = client.get("/api/v1/developer/health")
    finally:
        developer_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "developer_service"
    assert payload["dependencies"]["project_service"] == "not_configured"
