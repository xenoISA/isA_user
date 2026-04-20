"""
Auth Service — Full lifecycle smoke test.

Tests the complete auth flow through live infrastructure:
  1. Health check
  2. Admin bootstrap (get admin token)
  3. Register user → verify code → get tokens
  4. Login → access + refresh tokens
  5. Verify token → valid
  6. Refresh token → new access token
  7. Create API key → verify → revoke → verify invalid

Usage:
    pytest tests/smoke/auth_service/test_auth_flow_smoke.py -v
    SMOKE_MODE=gateway pytest tests/smoke/auth_service/test_auth_flow_smoke.py -v

Env vars:
    SMOKE_MODE          - "direct" (default, port 8201) or "gateway" (port 8000)
    HEALTH_HOST         - hostname (default: localhost)
    ADMIN_BOOTSTRAP_SECRET - bootstrap secret (default: dev-bootstrap-secret)
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
BOOTSTRAP_SECRET = os.getenv("ADMIN_BOOTSTRAP_SECRET", "dev-bootstrap-secret")

# Internal service headers for bypassing gateway auth on admin endpoints
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
def test_user_id():
    return f"smoke-user-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def test_password():
    return f"SmokePass!{uuid.uuid4().hex[:6]}"


# ── 1. Health ──


class TestAuthHealthSmoke:
    """Verify service is reachable and healthy."""

    @pytest.mark.asyncio
    async def test_health(self, base_url):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{base_url}/health")
            assert resp.status_code == 200
            data = resp.json()
            assert "status" in data
            assert data["status"] in ("healthy", "ok", True)

    @pytest.mark.asyncio
    async def test_api_v1_health(self, base_url):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{base_url}/api/v1/auth/health")
            assert resp.status_code == 200
            data = resp.json()
            assert "status" in data


# ── 2. Admin Bootstrap ──


class TestAdminBootstrapSmoke:
    """Bootstrap an admin user to get admin-scoped tokens."""

    @pytest.mark.asyncio
    async def test_admin_bootstrap(self, base_url, test_user_id):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/admin/bootstrap",
                json={
                    "user_id": test_user_id,
                    "bootstrap_secret": BOOTSTRAP_SECRET,
                },
                headers=INTERNAL_HEADERS,
            )
            if resp.status_code == 403:
                pytest.skip(
                    "Admin bootstrap disabled or secret mismatch — "
                    "set ADMIN_BOOTSTRAP_SECRET env var"
                )

            assert resp.status_code == 200, (
                f"Admin bootstrap failed: {resp.status_code} {resp.text}"
            )
            data = resp.json()
            # Schema shape assertion
            assert "access_token" in data
            assert "refresh_token" in data
            assert isinstance(data["access_token"], str)
            assert len(data["access_token"]) > 20

            _state["admin_token"] = data["access_token"]
            _state["admin_user_id"] = test_user_id

    @pytest.mark.asyncio
    async def test_admin_bootstrap_wrong_secret(self, base_url, test_user_id):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/admin/bootstrap",
                json={
                    "user_id": test_user_id,
                    "bootstrap_secret": "wrong-secret",
                },
                headers=INTERNAL_HEADERS,
            )
            assert resp.status_code == 403


# ── 3. Registration ──


class TestAuthRegistrationSmoke:
    """Register a new user with email/password, then verify the code."""

    @pytest.mark.asyncio
    async def test_register_user(self, base_url, test_email, test_password):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/register",
                json={
                    "email": test_email,
                    "password": test_password,
                    "name": "Smoke Test User",
                },
            )
            # 200/201 = new registration, 409 = already registered (idempotent)
            assert resp.status_code in (200, 201, 409), (
                f"Registration failed: {resp.status_code} {resp.text}"
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                # Schema shape: pending registration
                assert "pending_registration_id" in data
                assert isinstance(data["pending_registration_id"], str)
                _state["pending_registration_id"] = data["pending_registration_id"]

    @pytest.mark.asyncio
    async def test_verify_registration(self, base_url):
        pending_id = _state.get("pending_registration_id")
        if not pending_id:
            pytest.skip("No pending registration (already registered or skipped)")

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Fetch verification code from dev endpoint
            code_resp = await client.get(
                f"{base_url}/api/v1/auth/dev/pending-registration/{pending_id}",
            )
            if code_resp.status_code == 404:
                pytest.skip("Dev endpoint not available (not in development mode)")

            assert code_resp.status_code == 200
            code_data = code_resp.json()
            code = code_data.get("code") or code_data.get("verification_code")
            assert code, f"No verification code in response: {code_data}"

            # Verify the registration
            resp = await client.post(
                f"{base_url}/api/v1/auth/verify",
                json={
                    "pending_registration_id": pending_id,
                    "code": str(code),
                },
            )
            assert resp.status_code == 200, (
                f"Verification failed: {resp.status_code} {resp.text}"
            )
            data = resp.json()
            assert data.get("success") is True
            # Schema shape: verified registration returns tokens
            assert "access_token" in data
            assert "user_id" in data
            _state["user_id"] = data["user_id"]


# ── 4. Login ──


class TestAuthLoginSmoke:
    """Login with email/password, get access + refresh tokens."""

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
            # Schema shape assertion
            assert "access_token" in data or "token" in data
            access = data.get("access_token") or data.get("token")
            assert isinstance(access, str)
            assert len(access) > 20

            _state["access_token"] = access
            _state["refresh_token"] = data.get("refresh_token")
            _state["user_id"] = _state.get("user_id") or data.get("user_id")

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

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, base_url):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/login",
                json={
                    "email": f"nonexistent-{uuid.uuid4().hex[:8]}@test.isa.dev",
                    "password": "DoesntMatter!1",
                },
            )
            assert resp.status_code in (401, 403, 404)


# ── 5. Token Verification ──


class TestAuthTokenSmoke:
    """Verify and refresh tokens."""

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
            # Schema shape: verification response
            assert "valid" in data or "user_id" in data
            if "valid" in data:
                assert data["valid"] is True
            if "user_id" in data:
                assert isinstance(data["user_id"], str)

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self, base_url):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/verify-token",
                json={"token": "invalid.jwt.token"},
            )
            # Could be 200 with valid=false or 401
            if resp.status_code == 200:
                data = resp.json()
                assert data.get("valid") is False or data.get("error")
            else:
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
            # Schema shape: refresh returns new access token
            new_token = data.get("access_token") or data.get("token")
            assert new_token, "No new access token from refresh"
            assert isinstance(new_token, str)
            assert len(new_token) > 20

            # Update state with refreshed token
            _state["access_token"] = new_token
            if data.get("refresh_token"):
                _state["refresh_token"] = data["refresh_token"]

    @pytest.mark.asyncio
    async def test_user_info(self, base_url):
        token = _state.get("access_token")
        if not token:
            pytest.skip("No access token")

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/user-info",
                json={"token": token},
            )
            assert resp.status_code == 200
            data = resp.json()
            # Schema shape: user info
            assert "user_id" in data or "email" in data


# ── 6. API Key Lifecycle ──


class TestAuthApiKeySmoke:
    """Create, verify, revoke, and re-verify an API key."""

    @pytest.mark.asyncio
    async def test_create_api_key(self, base_url):
        # Use admin token for API key creation (requires auth scope)
        token = _state.get("admin_token") or _state.get("access_token")
        if not token:
            pytest.skip("No token available")

        org_id = _state.get("user_id", "smoke-test-org")

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/api-keys",
                json={
                    "name": f"smoke-test-{uuid.uuid4().hex[:6]}",
                    "organization_id": org_id,
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    **INTERNAL_HEADERS,
                },
            )
            assert resp.status_code in (200, 201), (
                f"API key creation failed: {resp.status_code} {resp.text}"
            )
            data = resp.json()
            # Schema shape: API key response
            api_key = data.get("key") or data.get("api_key")
            key_id = data.get("id") or data.get("key_id")
            assert api_key, f"No API key in response: {data}"
            assert key_id, f"No key ID in response: {data}"
            assert isinstance(api_key, str)

            _state["api_key"] = api_key
            _state["api_key_id"] = key_id
            _state["api_key_org_id"] = org_id

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
            # Schema shape: API key verification
            assert "valid" in data
            assert data["valid"] is True

    @pytest.mark.asyncio
    async def test_revoke_api_key(self, base_url):
        token = _state.get("admin_token") or _state.get("access_token")
        key_id = _state.get("api_key_id")
        org_id = _state.get("api_key_org_id")
        if not token or not key_id:
            pytest.skip("No token or API key ID")

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.delete(
                f"{base_url}/api/v1/auth/api-keys/{key_id}",
                params={"organization_id": org_id},
                headers={
                    "Authorization": f"Bearer {token}",
                    **INTERNAL_HEADERS,
                },
            )
            assert resp.status_code in (200, 204)

    @pytest.mark.asyncio
    async def test_verify_revoked_api_key(self, base_url):
        api_key = _state.get("api_key")
        if not api_key:
            pytest.skip("No API key to verify")

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/verify-api-key",
                json={"api_key": api_key},
            )
            # Revoked key should be invalid
            if resp.status_code == 200:
                data = resp.json()
                assert data.get("valid") is False, "Revoked API key should be invalid"
            else:
                assert resp.status_code in (401, 404)

    @pytest.mark.asyncio
    async def test_verify_nonexistent_api_key(self, base_url):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/api/v1/auth/verify-api-key",
                json={"api_key": f"fake-key-{uuid.uuid4().hex}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                assert data.get("valid") is False
            else:
                assert resp.status_code in (401, 404)
