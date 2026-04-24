"""Regression tests for microservice startup packaging (Issue #216)."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MICROSERVICE_ROOT = PROJECT_ROOT / "microservices"
QUICKSTART_DOC = PROJECT_ROOT / "docs" / "guidance" / "quickstart.md"
LOCAL_DEV_SCRIPT = PROJECT_ROOT / "deployment" / "local-dev.sh"
README = PROJECT_ROOT / "README.md"
DOCKERFILES = (
    PROJECT_ROOT / "deployment" / "docker" / "Dockerfile.microservice",
    PROJECT_ROOT / "deployment" / "_legacy" / "k8s" / "Dockerfile.microservice",
)


def _iter_main_modules() -> list[Path]:
    return sorted(MICROSERVICE_ROOT.glob("*/main.py"))


def _find_sys_path_mutations(source: str) -> list[str]:
    tree = ast.parse(source)
    mutations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr not in {"insert", "append"}:
            continue

        value = func.value
        if not isinstance(value, ast.Attribute) or value.attr != "path":
            continue
        if not isinstance(value.value, ast.Name) or value.value.id != "sys":
            continue

        mutations.append(
            f"line {node.lineno}: sys.path.{func.attr}(...) is not allowed"
        )

    return mutations


def test_microservices_namespace_package_marker_exists():
    assert (MICROSERVICE_ROOT / "__init__.py").exists()


def test_microservice_main_modules_do_not_mutate_sys_path():
    offenders: list[str] = []

    for path in _iter_main_modules():
        mutations = _find_sys_path_mutations(path.read_text())
        for mutation in mutations:
            offenders.append(f"{path.relative_to(PROJECT_ROOT)} {mutation}")

    assert not offenders, "Found unsupported sys.path mutations:\n" + "\n".join(
        offenders
    )


def test_local_dev_uses_repo_root_pythonpath():
    local_dev = LOCAL_DEV_SCRIPT.read_text()

    assert (
        'PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/microservices/$SERVICE_NAME"'
        not in local_dev
    )
    assert (
        'export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/microservices/$SERVICE_NAME"'
        not in local_dev
    )
    assert 'PYTHONPATH="$PROJECT_ROOT"' in local_dev
    assert 'export PYTHONPATH="$PROJECT_ROOT"' in local_dev
    assert "python -m uvicorn microservices.$SERVICE_NAME.main:app" in local_dev


def test_quickstart_documents_module_startup():
    quickstart = QUICKSTART_DOC.read_text()

    assert "uvicorn main:app" not in quickstart
    assert "python -m uvicorn microservices.auth_service.main:app" in quickstart
    assert "python -m uvicorn microservices.${service}_service.main:app" in quickstart


def test_readme_documents_supported_local_startup():
    readme = README.read_text()

    assert "start_user_service.sh" not in readme
    assert "./deployment/local-dev.sh --run-all" in readme
    assert "./deployment/local-dev.sh --run payment_service" in readme
    assert (
        'PYTHONPATH="$PWD" python -m uvicorn microservices.auth_service.main:app'
        in readme
    )


def test_container_entrypoints_use_module_startup():
    for path in DOCKERFILES:
        text = path.read_text()
        assert "python -u -m uvicorn microservices.${SERVICE_NAME}.main:app" in text
