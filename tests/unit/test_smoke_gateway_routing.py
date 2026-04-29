from __future__ import annotations

from pathlib import Path


from tests.smoke.conftest import resolve_base_url, resolve_service_url


def test_resolve_base_url_uses_direct_mode_by_default(monkeypatch):
    monkeypatch.delenv("SMOKE_MODE", raising=False)

    assert resolve_base_url("task_service", "TASK_BASE_URL") == "http://localhost:8211"


def test_resolve_base_url_uses_gateway_when_requested(monkeypatch):
    monkeypatch.setenv("SMOKE_MODE", "gateway")

    assert resolve_base_url("task_service", "TASK_BASE_URL") == "http://localhost:8000"


def test_resolve_service_url_rewrites_health_for_gateway(monkeypatch):
    monkeypatch.setenv("SMOKE_MODE", "gateway")

    assert (
        resolve_service_url("organization_service", "/health", "ORGANIZATION_BASE_URL")
        == "http://localhost:8000/api/v1/organization/health"
    )
    assert (
        resolve_service_url(
            "session_service",
            "/health/detailed",
            "SESSION_BASE_URL",
        )
        == "http://localhost:8000/api/v1/sessions/health/detailed"
    )
    assert (
        resolve_service_url("credit_service", "/health", "CREDIT_BASE_URL")
        == "http://localhost:8000/api/v1/credits/health"
    )
    assert (
        resolve_service_url("membership_service", "/health", "MEMBERSHIP_BASE_URL")
        == "http://localhost:8000/api/v1/membership/health"
    )


def test_resolve_service_url_preserves_api_paths_in_gateway_mode(monkeypatch):
    monkeypatch.setenv("SMOKE_MODE", "gateway")

    assert (
        resolve_service_url(
            "billing_service", "/api/v1/billing/usage/record", "BILLING_BASE_URL"
        )
        == "http://localhost:8000/api/v1/billing/usage/record"
    )


def test_explicit_service_env_override_wins(monkeypatch):
    monkeypatch.setenv("SMOKE_MODE", "gateway")
    monkeypatch.setenv("TASK_BASE_URL", "http://debug-host:9999")

    assert resolve_base_url("task_service", "TASK_BASE_URL") == "http://debug-host:9999"
    assert (
        resolve_service_url("task_service", "/health", "TASK_BASE_URL")
        == "http://debug-host:9999/health"
    )


def test_core_smoke_suites_use_shared_gateway_router():
    repo_root = Path(__file__).resolve().parents[2]
    smoke_files = [
        "tests/smoke/auth_service/test_auth_flow_smoke.py",
        "tests/smoke/billing_service/test_billing_smoke.py",
        "tests/smoke/campaign_service/test_campaign_smoke.py",
        "tests/smoke/credit_service/conftest.py",
        "tests/smoke/document_service/test_document_smoke.py",
        "tests/smoke/event_service/test_event_smoke.py",
        "tests/smoke/fulfillment_service/test_fulfillment_smoke.py",
        "tests/smoke/inventory_service/test_inventory_smoke.py",
        "tests/smoke/membership_service/test_membership_smoke.py",
        "tests/smoke/organization_service/test_organization_smoke.py",
        "tests/smoke/order_service/test_order_smoke.py",
        "tests/smoke/payment_service/test_payment_smoke.py",
        "tests/smoke/session_service/test_session_smoke.py",
        "tests/smoke/task_service/test_task_smoke.py",
        "tests/smoke/tax_service/test_tax_smoke.py",
        "tests/smoke/telemetry_service/test_telemetry_smoke.py",
        "tests/smoke/vault_service/test_vault_smoke.py",
        "tests/smoke/wallet_service/test_wallet_smoke.py",
    ]

    missing = []
    for relative_path in smoke_files:
        contents = (repo_root / relative_path).read_text()
        if (
            "resolve_base_url(" not in contents
            or "resolve_service_url(" not in contents
        ):
            missing.append(relative_path)

    assert (
        not missing
    ), f"Smoke suites missing shared gateway routing helpers: {missing}"
