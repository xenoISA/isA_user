"""Component tests for account claims endpoint used by auth_service."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from microservices.account_service.models import User

pytestmark = pytest.mark.component


class _NoopMetric:
    def labels(self, *args, **kwargs):
        return self

    def inc(self, *args, **kwargs):
        return None

    def observe(self, *args, **kwargs):
        return None


def _install_isa_common_stubs():
    if "isa_common.observability" not in sys.modules:
        observability = types.ModuleType("isa_common.observability")

        def setup_observability(*args, **kwargs):
            return {"metrics": False, "logging": False, "tracing": False}

        observability.setup_observability = setup_observability
        sys.modules["isa_common.observability"] = observability

    if "isa_common.metrics" not in sys.modules:
        metrics = types.ModuleType("isa_common.metrics")
        metrics.create_counter = lambda *args, **kwargs: _NoopMetric()
        metrics.create_histogram = lambda *args, **kwargs: _NoopMetric()
        sys.modules["isa_common.metrics"] = metrics


@pytest.fixture
def account_claims_client():
    """TestClient with account_service and auth dependency overridden."""
    _install_isa_common_stubs()
    import microservices.account_service.main as account_main
    from microservices.account_service.main import get_authenticated_caller

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    orig_lifespan = account_main.app.router.lifespan_context
    orig_service = account_main.account_microservice.account_service
    account_main.app.router.lifespan_context = noop_lifespan

    fake_service = MagicMock()
    fake_service.account_repo = MagicMock()
    account_main.account_microservice.account_service = fake_service

    async def _override_caller():
        return "internal-service"

    account_main.app.dependency_overrides[get_authenticated_caller] = _override_caller

    with TestClient(account_main.app, raise_server_exceptions=False) as client:
        client.fake_service = fake_service  # type: ignore[attr-defined]
        yield client

    account_main.app.dependency_overrides.pop(get_authenticated_caller, None)
    account_main.account_microservice.account_service = orig_service
    account_main.app.router.lifespan_context = orig_lifespan


def _user(*, is_active=True, admin_roles=None):
    return User(
        user_id="usr_claims_001",
        email="claims@example.com",
        name="Claims User",
        is_active=is_active,
        admin_roles=admin_roles,
        preferences={},
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )


def test_account_claims_returns_minimal_identity(account_claims_client):
    account_claims_client.fake_service.account_repo.get_account_by_id = AsyncMock(
        return_value=_user(admin_roles=["super_admin"])
    )

    response = account_claims_client.get("/api/v1/accounts/claims/usr_claims_001")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "usr_claims_001",
        "name": "Claims User",
        "is_active": True,
        "admin_roles": ["super_admin"],
    }


def test_account_claims_includes_inactive_status(account_claims_client):
    account_claims_client.fake_service.account_repo.get_account_by_id = AsyncMock(
        return_value=_user(is_active=False, admin_roles=[])
    )

    response = account_claims_client.get("/api/v1/accounts/claims/usr_claims_001")

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert response.json()["admin_roles"] == []


def test_account_claims_returns_404_for_missing_account(account_claims_client):
    account_claims_client.fake_service.account_repo.get_account_by_id = AsyncMock(
        return_value=None
    )

    response = account_claims_client.get("/api/v1/accounts/claims/missing")

    assert response.status_code == 404
