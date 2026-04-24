from pathlib import Path

import pytest

from core.deployment_targets import (
    list_service_directories,
    normalize_requested_services,
    resolve_deploy_target,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "deploy.yml"


@pytest.mark.unit
def test_resolve_deploy_target_uses_canonical_short_name_mapping():
    target = resolve_deploy_target("auth_service")

    assert target.service_dir == "auth_service"
    assert target.short_name == "auth"
    assert target.image_name == "auth"
    assert target.k8s_service_name == "auth"
    assert target.release_name == "user-auth-service"
    assert target.deployment_name == "user-auth-service"
    assert target.container_name == "user-auth-service"


@pytest.mark.unit
def test_normalize_requested_services_accepts_directory_and_short_names():
    assert normalize_requested_services("auth_service,sharing") == [
        "auth_service",
        "sharing_service",
    ]


@pytest.mark.unit
def test_list_service_directories_only_returns_configured_services():
    service_dirs = list_service_directories()

    assert "auth_service" in service_dirs
    assert "sharing_service" in service_dirs
    assert "project_service" not in service_dirs


@pytest.mark.unit
def test_resolve_deploy_target_rejects_unknown_service():
    with pytest.raises(ValueError, match="Unknown service"):
        resolve_deploy_target("does_not_exist")


@pytest.mark.unit
def test_deploy_workflow_uses_resolver_and_rollout_validation():
    workflow_text = WORKFLOW_PATH.read_text()

    assert "core/deployment_targets.py --normalize-list" in workflow_text
    assert 'python core/deployment_targets.py "$1" --format env' in workflow_text
    assert "Validate rollout target" in workflow_text
    assert "${service%-service}" not in workflow_text
