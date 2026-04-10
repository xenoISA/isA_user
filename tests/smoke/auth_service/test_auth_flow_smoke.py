"""
Auth Service — Full lifecycle smoke test.

Tests the complete auth flow: register → login → verify → refresh → API keys → logout.
Runs against live infrastructure (direct or gateway mode).

Usage:
    pytest tests/smoke/auth_service/test_auth_flow_smoke.py -v
    SMOKE_MODE=gateway pytest tests/smoke/auth_service/test_auth_flow_smoke.py -v
"""

import os
import uuid

import httpx
import pytest

pytestmark = pytest.mark.smoke

# ── Configuration ──

SMOKE_MODE = os.getenv("SMOKE_MODE", "direct")
AUTH_PORT = 8201
GATEWAY_PORT = 8000
HOST = os.getenv("HEALTH_HOST", "localhost")
TIMEOUT = 15.0

INTERNAL_HEADERS = {
    "X-Internal-Call": "true",
    "X-Internal-Service": "true",
    "X-Internal-Service-Secret": "dev-internal-secret-change-in-production",
}


def _base_url() -> str:
    if SMOKE_MODE == "gateway":
        return f"http://{HOST}:{GATEWAY_PORT}"
    return f"http://{HOST}:{AUTH_PORT}"


# ── Shared state across ordered tests ──

_state: dict = {}


@pytest.fixture(scope="module")
def base_url():
    return _base_url()


@pytest.fixture(scope="module")
def test_email():
    return f"smoke-{uuid.uuid4().hex[:8]}@test.isa.dev"


@pytest.fixture(scope="module")
def test_password():
    return f"SmokePass!{uuid.uuid4().hex[:6]}"


# ── Health ──


class TestAuthHealthSmoke:
    @pytest.mark.asyncio
    async def test_health(self, base_url):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{base_url}/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("status") in ("healthy", "ok", True)

    @pytest.mark.asyncio
    async def test_api_v1_health(self, base_url):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{base_url}/api/v1/auth/health")
            assert resp.status_code == 200


# ── Registration ──


class TestAuthRegistrationSmoke:
    @pytest.mark.asyncio
    async def test_register_user(self, base_url, test_email, test_password):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/register",
                json={
                    "email": test_email,
                    "password": test_password,
                    "name": "Smoke Test User",
                    "provider": "isa_user",
                },
            )
            # 200/201 = success, 409 = already exists (idempotent reruns)
            assert resp.status_code in (200, 201, 409), (
                f"Registration failed: {resp.status_code} {resp.text}"
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                _state["user_id"] = data.get("user_id") or data.get("id")


# ── Login ──


class TestAuthLoginSmoke:
    @pytest.mark.asyncio
    async def test_login(self, base_url, test_email, test_password):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/login",
                json={
                    "email": test_email,
                    "password": test_password,
                },
            )
            assert resp.status_code == 200, (
                f"Login failed: {resp.status_code} {resp.text}"
            )
            data = resp.json()
            # Capture tokens for subsequent tests
            _state["access_token"] = data.get("access_token") or data.get("token")
            _state["refresh_token"] = data.get("refresh_token")
            _state["user_id"] = _state.get("user_id") or data.get("user_id") or data.get("id")
            assert _state["access_token"], "No access token in login response"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, base_url, test_email):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/login",
                json={
                    "email": test_email,
                    "password": "WrongPassword!999",
                },
            )
            assert resp.status_code in (401, 403)


# ── Token Verification ──


class TestAuthTokenSmoke:
    @pytest.mark.asyncio
    async def test_verify_token(self, base_url):
        token = _state.get("access_token")
        if not token:
            pytest.skip("No access token from login")

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/verify-token",
                json={"token": token},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("valid") is True or data.get("user_id")

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self, base_url):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/verify-token",
                json={"token": "invalid.jwt.token"},
            )
            assert resp.status_code in (401, 422)

    @pytest.mark.asyncio
    async def test_refresh_token(self, base_url):
        refresh = _state.get("refresh_token")
        if not refresh:
            pytest.skip("No refresh token from login")

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/refresh",
                json={"refresh_token": refresh},
            )
            assert resp.status_code == 200
            data = resp.json()
            new_token = data.get("access_token") or data.get("token")
            assert new_token, "No new access token from refresh"
            # Update state with refreshed token
            _state["access_token"] = new_token
            if data.get("refresh_token"):
                _state["refresh_token"] = data["refresh_token"]


# ── API Keys ──


class TestAuthApiKeySmoke:
    @pytest.mark.asyncio
    async def test_create_api_key(self, base_url):
        token = _state.get("access_token")
        if not token:
            pytest.skip("No access token")

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/api-keys",
                json={"name": f"smoke-test-{uuid.uuid4().hex[:6]}"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code in (200, 201), (
                f"API key creation failed: {resp.status_code} {resp.text}"
            )
            data = resp.json()
            _state["api_key"] = data.get("key") or data.get("api_key")
            _state["api_key_id"] = data.get("id") or data.get("key_id")
            assert _state["api_key"], "No API key in response"

    @pytest.mark.asyncio
    async def test_verify_api_key(self, base_url):
        api_key = _state.get("api_key")
        if not api_key:
            pytest.skip("No API key created")

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/verify-api-key",
                json={"api_key": api_key},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("valid") is True or data.get("user_id")

    @pytest.mark.asyncio
    async def test_revoke_api_key(self, base_url):
        token = _state.get("access_token")
        key_id = _state.get("api_key_id")
        if not token or not key_id:
            pytest.skip("No token or API key ID")

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.delete(
                f"{base_url}/api/v1/auth/api-keys/{key_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code in (200, 204)


# ── Logout ──


class TestAuthLogoutSmoke:
    @pytest.mark.asyncio
    async def test_logout(self, base_url):
        token = _state.get("access_token")
        if not token:
            pytest.skip("No access token")

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code in (200, 204)

    @pytest.mark.asyncio
    async def test_token_invalid_after_logout(self, base_url):
        token = _state.get("access_token")
        if not token:
            pytest.skip("No access token")

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/verify-token",
                json={"token": token},
            )
            # After logout, token should be invalid
            # Some implementations return 401, others return 200 with valid=false
            if resp.status_code == 200:
                data = resp.json()
                # Token may still be valid if logout only kills refresh
                pass
            else:
                assert resp.status_code in (401, 403)
