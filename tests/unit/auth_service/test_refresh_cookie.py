"""
Tests for the HttpOnly refresh-token cookie behaviour.

Covers xenoISA/isA_user#499 — refresh tokens MUST be returned as
HttpOnly + SameSite=Lax cookies (Secure in production), never inside
the JSON response body.

The auth service is exercised via FastAPI's TestClient with the
`get_auth_service` dependency overridden to a stub. This keeps the
test hermetic — no DB, no Consul, no JWT signing.

Endpoints under test:
- POST /api/v1/auth/login
- POST /api/v1/auth/admin/login
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, PROJECT_ROOT)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Stub auth service
# ---------------------------------------------------------------------------


def _stub_auth_service(
    *,
    login_refresh: str = "user-refresh-token-abc",
    admin_refresh: str = "admin-refresh-token-xyz",
    refreshed_refresh: Optional[str] = "rotated-refresh-token-789",
) -> MagicMock:
    """Build a MagicMock that satisfies the calls /login, /admin/login,
    and /refresh make on AuthenticationService."""
    svc = MagicMock()
    svc.login = AsyncMock(
        return_value={
            "success": True,
            "user_id": "usr_test",
            "email": "user@example.com",
            "name": "Test User",
            "access_token": "user-access-token",
            "refresh_token": login_refresh,
            "token_type": "Bearer",
            "expires_in": 3600,
        }
    )
    svc.admin_login = AsyncMock(
        return_value={
            "success": True,
            "user_id": "usr_admin",
            "email": "admin@example.com",
            "name": "Admin",
            "admin_roles": ["super_admin"],
            "access_token": "admin-access-token",
            "refresh_token": admin_refresh,
            "token_type": "Bearer",
            "expires_in": 14400,
        }
    )

    async def _refresh(token: str) -> Dict[str, Any]:
        if not token:
            return {"success": False, "error": "Missing refresh token"}
        payload: Dict[str, Any] = {
            "success": True,
            "access_token": f"new-access-for::{token}",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        if refreshed_refresh:
            payload["refresh_token"] = refreshed_refresh
        return payload

    svc.refresh_access_token = AsyncMock(side_effect=_refresh)
    return svc


@pytest.fixture
def client(monkeypatch) -> TestClient:
    """TestClient with auth-service dependency replaced by a stub.

    Defaults match production: SECURE_COOKIES=true,
    AUTH_COOKIE_DOMAIN=.iapro.ai, refresh-in-body OFF.
    """
    # Set deterministic env BEFORE importing the app — _refresh_cookie_settings
    # reads env at call time so changing it per-test is also fine.
    monkeypatch.setenv("SECURE_COOKIES", "true")
    monkeypatch.setenv("AUTH_COOKIE_DOMAIN", ".iapro.ai")
    monkeypatch.delenv("RETURN_REFRESH_TOKEN_IN_BODY", raising=False)
    monkeypatch.setenv("JWT_SECRET", "unit-test-secret")

    from microservices.auth_service import main as auth_main

    svc = _stub_auth_service()
    auth_main.app.dependency_overrides[auth_main.get_auth_service] = lambda: svc

    # NOTE: do NOT enter TestClient as a context manager — that triggers
    # the lifespan, which calls signal.signal() and fails in pytest worker
    # threads ("signal only works in main thread"). Direct instantiation
    # skips lifespan but routes still work for these unit tests.
    tc = TestClient(auth_main.app)
    tc.app.state.stub_svc = svc  # type: ignore[attr-defined]
    try:
        yield tc
    finally:
        auth_main.app.dependency_overrides.pop(auth_main.get_auth_service, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_cookie_header(resp) -> str:
    """Return the raw Set-Cookie header (joined if multiple)."""
    # httpx exposes multiple Set-Cookie via .headers.get_list, TestClient too
    headers = resp.headers
    items = headers.get_list("set-cookie") if hasattr(headers, "get_list") else []
    if not items:
        single = headers.get("set-cookie")
        items = [single] if single else []
    return "\n".join(items)


# ---------------------------------------------------------------------------
# /login
# ---------------------------------------------------------------------------


class TestLoginSetsRefreshCookie:
    def test_login_sets_httponly_refresh_cookie(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "pw"},
        )
        assert resp.status_code == 200, resp.text
        header = _set_cookie_header(resp)
        assert "refresh_token=" in header
        assert "HttpOnly" in header
        assert "SameSite=lax" in header.lower() or "samesite=lax" in header.lower()

    def test_login_cookie_has_secure_in_prod(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "pw"},
        )
        header = _set_cookie_header(resp)
        assert "Secure" in header, f"Set-Cookie should include Secure flag: {header!r}"

    def test_login_cookie_has_iapro_domain(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "pw"},
        )
        header = _set_cookie_header(resp)
        assert "Domain=.iapro.ai" in header or "domain=.iapro.ai" in header.lower()

    def test_login_body_omits_refresh_token_by_default(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "pw"},
        )
        body = resp.json()
        assert body["success"] is True
        assert body["access_token"] == "user-access-token"
        assert body.get("refresh_token") is None, (
            "refresh_token must NOT appear in JSON body by default — "
            "frontend smoke test (xenoISA/isA_#488) asserts the same."
        )

    def test_login_body_includes_refresh_when_flag_on(self, client, monkeypatch):
        monkeypatch.setenv("RETURN_REFRESH_TOKEN_IN_BODY", "true")
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "pw"},
        )
        body = resp.json()
        assert body["refresh_token"] == "user-refresh-token-abc"
        # cookie still set in parallel
        assert "refresh_token=" in _set_cookie_header(resp)


# ---------------------------------------------------------------------------
# /admin/login
# ---------------------------------------------------------------------------


class TestAdminLoginSetsRefreshCookie:
    def test_admin_login_sets_httponly_cookie(self, client):
        resp = client.post(
            "/api/v1/auth/admin/login",
            json={"email": "admin@example.com", "password": "pw"},
        )
        assert resp.status_code == 200, resp.text
        header = _set_cookie_header(resp)
        assert "refresh_token=admin-refresh-token-xyz" in header
        assert "HttpOnly" in header

    def test_admin_login_body_omits_refresh_token(self, client):
        resp = client.post(
            "/api/v1/auth/admin/login",
            json={"email": "admin@example.com", "password": "pw"},
        )
        assert resp.json().get("refresh_token") is None


# ---------------------------------------------------------------------------
# /refresh
# ---------------------------------------------------------------------------


class TestRefreshReadsCookie:
    def test_refresh_reads_token_from_cookie(self, client):
        resp = client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": "incoming-refresh-token"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        assert body["access_token"] == "new-access-for::incoming-refresh-token"
        # No refresh_token in body — cookie only
        assert "refresh_token" not in body

    def test_refresh_rotates_cookie_on_success(self, client):
        resp = client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": "incoming-refresh-token"},
        )
        header = _set_cookie_header(resp)
        assert "refresh_token=rotated-refresh-token-789" in header
        assert "HttpOnly" in header

    def test_refresh_without_cookie_returns_401(self, client):
        resp = client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401

    def test_refresh_falls_back_to_body_during_transition(self, client):
        # During backwards-compat window, body-supplied refresh_token still works.
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "legacy-body-token"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["access_token"] == "new-access-for::legacy-body-token"


# ---------------------------------------------------------------------------
# /logout
# ---------------------------------------------------------------------------


class TestLogoutClearsCookie:
    def test_logout_clears_refresh_cookie(self, client):
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        header = _set_cookie_header(resp)
        # delete_cookie sets Max-Age=0 with an empty value
        assert "refresh_token=" in header
        assert ("Max-Age=0" in header) or ("max-age=0" in header.lower())


# ---------------------------------------------------------------------------
# SECURE_COOKIES toggle (local dev / non-prod)
# ---------------------------------------------------------------------------


class TestSecureCookieToggle:
    def test_secure_cookies_false_omits_secure_flag(self, client, monkeypatch):
        monkeypatch.setenv("SECURE_COOKIES", "false")
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "pw"},
        )
        header = _set_cookie_header(resp)
        assert "Secure" not in header, (
            "Local/dev SECURE_COOKIES=false should NOT emit Secure attr"
        )
        # HttpOnly still mandatory regardless of env
        assert "HttpOnly" in header
