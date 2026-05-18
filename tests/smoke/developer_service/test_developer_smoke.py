import pytest
from fastapi.testclient import TestClient

from microservices.developer_service.main import app
from microservices.developer_service.routes_registry import get_all_routes

pytestmark = [pytest.mark.smoke, pytest.mark.tdd]


def test_developer_service_imports_with_expected_contract_routes():
    route_paths = {route.path for route in app.routes}
    registry_paths = {route["path"] for route in get_all_routes()}

    assert "/api/v1/developer/overview" in route_paths
    assert "/api/v1/developer/first-call" in route_paths
    assert "/api/v1/developer/health" in route_paths
    assert "/api/v1/developer/overview" in registry_paths
    assert "/api/v1/developer/first-call" in registry_paths


def test_developer_service_health_is_reachable_locally():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "developer_service"
