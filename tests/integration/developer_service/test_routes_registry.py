import pytest

from microservices.developer_service.routes_registry import (
    DEVELOPER_SERVICE_ROUTES,
    SERVICE_METADATA,
    get_routes_for_consul,
)

pytestmark = [pytest.mark.integration, pytest.mark.tdd]


def test_routes_registry_exposes_overview_and_health_routes():
    paths = {route["path"] for route in DEVELOPER_SERVICE_ROUTES}

    assert "/health" in paths
    assert "/api/v1/developer/health" in paths
    assert "/api/v1/developer/overview" in paths
    assert "/api/v1/developer/first-call" in paths


def test_consul_route_metadata_is_compact_and_protected():
    route_meta = get_routes_for_consul()

    assert SERVICE_METADATA["service_name"] == "developer_service"
    assert route_meta["base_path"] == "/api/v1/developer"
    assert route_meta["api_path"] == "/api/v1/developer"
    assert route_meta["auth_required"] == "false"
    assert route_meta["rate_limit"] == "100"
    assert route_meta["route_count"] == str(len(DEVELOPER_SERVICE_ROUTES))
    assert route_meta["protected_count"] == "2"
    assert route_meta["public_count"] == "2"
