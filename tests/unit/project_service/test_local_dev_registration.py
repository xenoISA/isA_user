from pathlib import Path

from microservices.project_service.routes_registry import get_routes_for_consul


ROOT = Path(__file__).resolve().parents[3]


def test_project_service_port_is_configured_for_local_dev():
    ports_yaml = (ROOT / "config" / "ports.yaml").read_text()

    assert "project_service:" in ports_yaml
    assert "port: 8260" in ports_yaml


def test_project_service_is_started_with_core_platform_services():
    local_dev = (ROOT / "deployment" / "local-dev.sh").read_text()

    tier2_line = next(
        line for line in local_dev.splitlines()
        if line.startswith("TIER2_SERVICES=")
    )
    assert "project_service" in tier2_line


def test_project_service_exposes_gateway_sync_metadata():
    route_meta = get_routes_for_consul()

    assert route_meta["base_path"] == "/api/v1/projects"
    assert int(route_meta["route_count"]) > 0
    assert int(route_meta["protected_count"]) > 0
