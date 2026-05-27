from fastapi.testclient import TestClient

from microservices.training_service.main import create_app
from microservices.training_service.routes_registry import get_all_routes


def test_training_service_imports_with_expected_contract_routes():
    routes = get_all_routes()

    assert any(route["path"] == "/api/v1/training/courses" for route in routes)
    assert any(route["path"] == "/api/v1/training/me/progress" for route in routes)


def test_training_service_health_is_reachable_locally():
    client = TestClient(create_app())

    response = client.get("/api/v1/training/health")

    assert response.status_code == 200
    assert response.json()["service"] == "training_service"
