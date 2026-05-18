import pytest

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
