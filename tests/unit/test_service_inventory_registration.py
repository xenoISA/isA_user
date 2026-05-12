"""Service inventory registration coverage for project and sharing services."""

from pathlib import Path
import re

import yaml

from core.deployment_targets import list_service_directories, resolve_deploy_target


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_yaml(relative_path: str):
    return yaml.safe_load((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def _tier_services(tier: int) -> list[str]:
    script = (REPO_ROOT / "deployment" / "local-dev.sh").read_text(encoding="utf-8")
    match = re.search(rf'^TIER{tier}_SERVICES="([^"]*)"', script, flags=re.MULTILINE)
    assert match, f"TIER{tier}_SERVICES not found"
    return match.group(1).split()


def test_project_and_sharing_are_in_ports_inventory():
    microservices = _load_yaml("config/ports.yaml")["microservices"]

    assert microservices["project_service"] == {
        "port": 8260,
        "k8s_service": "project",
        "description": "Project workspace management",
    }
    assert microservices["sharing_service"] == {
        "port": 8255,
        "k8s_service": "sharing",
        "description": "Session share links",
    }


def test_project_and_sharing_are_tiered_for_local_dev():
    assert "project_service" in _tier_services(2)
    assert "sharing_service" in _tier_services(4)

    configured = set(_load_yaml("config/ports.yaml")["microservices"])
    tiered = set().union(*(_tier_services(tier) for tier in range(1, 5)))
    assert configured - tiered == set()


def test_project_and_sharing_are_in_all_helm_values():
    for relative_path in (
        "deployment/helm/values.yaml",
        "deployment/helm/values-staging.yaml",
        "deployment/helm/values-production.yaml",
    ):
        services = _load_yaml(relative_path)["services"]
        assert services["project"] == {
            "name": "user-project-service",
            "repository": "isa/user-project",
            "port": 8260,
        }
        assert services["sharing"] == {
            "name": "user-sharing-service",
            "repository": "isa/user-sharing",
            "port": 8255,
        }


def test_project_and_sharing_are_deploy_targets():
    assert "project_service" in list_service_directories()
    assert "sharing_service" in list_service_directories()

    project = resolve_deploy_target("project")
    assert project.service_dir == "project_service"
    assert project.release_name == "user-project-service"
    assert project.port == 8260

    sharing = resolve_deploy_target("sharing_service")
    assert sharing.short_name == "sharing"
    assert sharing.release_name == "user-sharing-service"
    assert sharing.port == 8255
