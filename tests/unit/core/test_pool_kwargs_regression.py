"""
Regression tests for the pool-kwargs leak (PR #358 / story #346).

A mass substitution in PR #358 inadvertently added ``min_pool_size`` /
``max_pool_size`` kwargs to **HTTP-client method calls** and a
``list_orders(...)`` call inside repositories that have nothing to do with
asyncpg pool sizing. Those sites were guarded by ``if self.org_client:``
(or were on a non-default code path) so existing test runs never hit them
and they would only blow up in production with ``TypeError: <method>()
got an unexpected keyword argument 'min_pool_size'``.

These tests force-execute each of the previously-broken paths with a mock
client / mock DB and assert no ``TypeError`` is raised. If a future
mass-rewrite ever re-introduces the bug, these tests will fail loudly.

Sites under test (lines as of this commit, may shift):

1. ``microservices/authorization_service/authorization_repository.py``:
   - ``get_organization_info`` → ``self.org_client.get_organization(...)``
   - ``get_organization_info`` → ``self.org_client.get_members(...)``
   - ``is_user_organization_member`` → ``self.org_client.get_members(...)``

2. ``microservices/auth_service/device_auth_repository.py``:
   - ``create_device_credential`` → ``self.organization_service_client.get_organization(...)``

3. ``microservices/order_service/order_repository.py``:
   - ``get_user_orders`` → ``self.list_orders(...)``
"""

from __future__ import annotations

import os
import sys
import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

# Make microservices/ importable for the repository modules under test.
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, PROJECT_ROOT)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strict_kwargs_mock_method(
    allowed_kwargs: set[str],
    return_value=None,
) -> AsyncMock:
    """Create an AsyncMock that *rejects* unexpected kwargs.

    Default ``AsyncMock()`` accepts any kwargs silently. That's what hid the
    bug originally — the test mock didn't reject ``min_pool_size`` so the
    broken call sites looked fine in tests. Here we explicitly reject any
    kwarg outside the allow-list and otherwise return ``return_value``.
    """

    async def _impl(*args, **kwargs):
        unexpected = set(kwargs) - allowed_kwargs
        if unexpected:
            raise TypeError(
                f"got unexpected keyword arguments {sorted(unexpected)!r} "
                f"(allowed: {sorted(allowed_kwargs)!r})"
            )
        return return_value

    return AsyncMock(side_effect=_impl)


def _make_async_db_mock() -> MagicMock:
    """An async-context-manager-friendly DB stub that returns no rows."""
    mock_db = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.execute = AsyncMock()
    mock_db.query_row = AsyncMock(return_value=None)
    mock_db.query = AsyncMock(return_value=[])
    return mock_db


# ---------------------------------------------------------------------------
# authorization_service/authorization_repository.py
# ---------------------------------------------------------------------------


class TestAuthorizationRepositoryOrgClientCalls:
    """Three call sites: get_organization, get_members (×2)."""

    @pytest.fixture
    def repo(self, monkeypatch):
        # Stub ConfigManager + AsyncPostgresClient so __init__ doesn't reach IO.
        from core import config_manager as cm
        from microservices.authorization_service import (
            authorization_repository as mod,
        )

        mock_cm = MagicMock()
        mock_cm.return_value.discover_service.return_value = ("stub-host", 5432)
        monkeypatch.setattr(cm, "ConfigManager", mock_cm)
        # The repository imports ConfigManager via ``from core.config_manager
        # import ConfigManager`` so the symbol on the repository module also
        # needs to be patched.
        monkeypatch.setattr(mod, "ConfigManager", mock_cm)
        monkeypatch.setattr(mod, "AsyncPostgresClient", MagicMock())

        repo = mod.AuthorizationRepository()
        # Force a clean async DB stub (the _make_async_db_mock isn't strictly
        # needed for these org_client paths but keeps things hermetic).
        repo.db = _make_async_db_mock()
        return repo

    @pytest.mark.asyncio
    async def test_get_organization_info_uses_only_allowed_kwargs(self, repo):
        """``get_organization`` and ``get_members`` must not receive pool kwargs."""
        org_client = MagicMock()
        org_client.get_organization = _strict_kwargs_mock_method(
            {"organization_id", "user_id"},
            return_value={
                "organization_id": "org_1",
                "plan": "free",
                "is_active": True,
            },
        )
        org_client.get_members = _strict_kwargs_mock_method(
            {"organization_id", "user_id"},
            return_value=[],
        )
        repo.org_client = org_client

        # Should not raise. The previously-broken code passed
        # ``min_pool_size``/``max_pool_size`` and would have TypeErrored.
        result = await repo.get_organization_info("org_1")
        assert result is not None
        assert result.organization_id == "org_1"
        # Both calls actually happened (skipped if first returned None).
        assert org_client.get_organization.await_count == 1
        assert org_client.get_members.await_count == 1

    @pytest.mark.asyncio
    async def test_is_user_organization_member_uses_only_allowed_kwargs(self, repo):
        org_client = MagicMock()
        org_client.get_members = _strict_kwargs_mock_method(
            {"organization_id", "user_id"},
            return_value=[{"user_id": "user_1", "status": "active"}],
        )
        repo.org_client = org_client

        result = await repo.is_user_organization_member("user_1", "org_1")
        assert result is True
        assert org_client.get_members.await_count == 1


# ---------------------------------------------------------------------------
# auth_service/device_auth_repository.py
# ---------------------------------------------------------------------------


class TestDeviceAuthRepositoryOrgClientCall:
    """``create_device_credential`` calls ``organization_service_client
    .get_organization(...)`` — must not pass pool kwargs."""

    @pytest.mark.asyncio
    async def test_get_organization_uses_only_allowed_kwargs(self, monkeypatch):
        from core import config_manager as cm
        from microservices.auth_service import device_auth_repository as mod

        mock_cm = MagicMock()
        mock_cm.return_value.discover_service.return_value = ("stub-host", 5432)
        monkeypatch.setattr(cm, "ConfigManager", mock_cm)
        monkeypatch.setattr(mod, "ConfigManager", mock_cm)
        monkeypatch.setattr(mod, "AsyncPostgresClient", MagicMock())

        org_client = MagicMock()
        org_client.get_organization = _strict_kwargs_mock_method(
            {"organization_id", "user_id"},
            return_value={"organization_id": "org_1"},
        )

        repo = mod.DeviceAuthRepository(organization_service_client=org_client)
        # Replace the DB stub with our async-friendly mock so the rest of the
        # method can run far enough to actually hit the org_client call.
        repo.db = _make_async_db_mock()
        repo.db.query_row.return_value = {
            "device_id": "dev_1",
            "device_secret": "secret",
            "organization_id": "org_1",
            "device_name": "n",
            "device_type": "t",
            "status": "active",
            "metadata": "{}",
            "expires_at": None,
            "created_at": None,
            "updated_at": None,
        }

        try:
            await repo.create_device_credential(
                {
                    "device_id": "dev_1",
                    "device_secret": "secret",
                    "organization_id": "org_1",
                    "device_name": "n",
                    "device_type": "t",
                    "status": "active",
                    "metadata": {},
                    "expires_at": None,
                }
            )
        except TypeError as exc:
            pytest.fail(f"unexpected TypeError from org_client call: {exc}")
        except Exception:
            # The method has lots of downstream logic we don't care about
            # here — only that the org_client call site itself doesn't raise
            # TypeError on its kwargs.
            pass

        assert org_client.get_organization.await_count == 1


# ---------------------------------------------------------------------------
# order_service/order_repository.py
# ---------------------------------------------------------------------------


class TestOrderRepositoryListOrdersCall:
    """``get_user_orders`` calls ``self.list_orders(...)`` — must not pass
    pool kwargs."""

    def test_list_orders_signature_does_not_accept_pool_kwargs(self):
        """Sanity check the function signature itself.

        If a future change adds ``**kwargs`` to ``list_orders`` the
        regression test below would silently pass even with the bad kwargs
        re-introduced. This signature check is the second line of defence.
        """
        from microservices.order_service import order_repository as mod

        sig = inspect.signature(mod.OrderRepository.list_orders)
        params = sig.parameters
        assert "min_pool_size" not in params
        assert "max_pool_size" not in params
        # And there's no **kwargs catch-all that would silently absorb them.
        assert not any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())

    @pytest.mark.asyncio
    async def test_get_user_orders_invokes_list_orders_with_safe_kwargs(
        self, monkeypatch
    ):
        from core import config_manager as cm
        from microservices.order_service import order_repository as mod

        mock_cm = MagicMock()
        mock_cm.return_value.discover_service.return_value = ("stub-host", 5432)
        monkeypatch.setattr(cm, "ConfigManager", mock_cm)
        monkeypatch.setattr(mod, "ConfigManager", mock_cm)
        monkeypatch.setattr(mod, "AsyncPostgresClient", MagicMock())

        repo = mod.OrderRepository()
        repo.db = _make_async_db_mock()

        # Spy on list_orders to capture the kwargs get_user_orders forwards.
        captured: dict = {}

        async def _spy_list_orders(self, **kwargs):
            captured.update(kwargs)
            return []

        monkeypatch.setattr(
            mod.OrderRepository,
            "list_orders",
            _spy_list_orders,
        )

        result = await repo.get_user_orders("user_1", limit=10, offset=0)
        assert result == []
        # The forwarded kwargs must NOT include the pool-sizing leakage.
        assert "min_pool_size" not in captured
        assert "max_pool_size" not in captured
        # And the legitimate forwarded kwargs are still there.
        assert captured.get("user_id") == "user_1"
        assert captured.get("limit") == 10
        assert captured.get("offset") == 0
