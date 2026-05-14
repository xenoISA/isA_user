"""
Unit tests for the OAuth authorization consent UI.

Covers: xenoISA/isA_user#156
"""

import os
import sys
import types
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, PROJECT_ROOT)

pytestmark = pytest.mark.unit


class _NoopMetric:
    def labels(self, *args, **kwargs):
        return self

    def inc(self, *args, **kwargs):
        return None

    def observe(self, *args, **kwargs):
        return None


def _install_isa_common_observability_stubs():
    if "isa_common.observability" not in sys.modules:
        observability = types.ModuleType("isa_common.observability")
        observability.setup_observability = lambda *args, **kwargs: {
            "metrics": False,
            "logging": False,
            "tracing": False,
        }
        sys.modules["isa_common.observability"] = observability

    if "isa_common.metrics" not in sys.modules:
        metrics = types.ModuleType("isa_common.metrics")
        metrics.setup_metrics = lambda *args, **kwargs: {
            "metrics": False,
            "logging": False,
            "tracing": False,
        }
        metrics.create_counter = lambda *args, **kwargs: _NoopMetric()
        metrics.create_histogram = lambda *args, **kwargs: _NoopMetric()
        metrics.create_gauge = lambda *args, **kwargs: _NoopMetric()
        metrics.metrics_text = lambda: b""
        sys.modules["isa_common.metrics"] = metrics


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def oauth_client():
    return {
        "client_id": "client_123",
        "client_name": "Claude Desktop",
        "client_type": "public",
        "redirect_uris": ["https://client.example/callback"],
        "require_pkce": True,
    }


@pytest.fixture
def oauth_repo(oauth_client):
    repo = MagicMock()
    repo.get_client = AsyncMock(return_value=oauth_client)
    return repo


@pytest.fixture
def auth_code_service():
    service = MagicMock()
    service.create_authorization_request = AsyncMock(
        return_value={
            "code": "auth_code_123",
            "state": "csrf-state",
            "redirect_uri": "https://client.example/callback",
        }
    )
    return service


@pytest.fixture
def auth_service():
    service = MagicMock()
    service.verify_access_token_for_resource = AsyncMock(
        return_value={
            "valid": True,
            "user_id": "usr_123",
            "organization_id": "org_123",
        }
    )
    return service


@pytest.fixture
async def client(oauth_repo, auth_code_service, auth_service):
    _install_isa_common_observability_stubs()

    from microservices.auth_service.main import (
        app,
        get_auth_service,
        get_authorization_code_service,
        get_oauth_client_repository,
    )

    app.dependency_overrides[get_oauth_client_repository] = lambda: oauth_repo
    app.dependency_overrides[get_authorization_code_service] = lambda: auth_code_service
    app.dependency_overrides[get_auth_service] = lambda: auth_service

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        follow_redirects=False,
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()


def _authorize_params():
    return {
        "response_type": "code",
        "client_id": "client_123",
        "redirect_uri": "https://client.example/callback",
        "scope": "mcp:tools:read mcp:tools:execute",
        "state": "csrf-state",
        "resource": "https://mcp.example",
        "code_challenge": "challenge_123",
        "code_challenge_method": "S256",
    }


@pytest.mark.anyio
async def test_authorize_renders_html_consent_screen(client):
    response = await client.get(
        "/oauth/authorize",
        params=_authorize_params(),
        headers={"accept": "text/html"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Claude Desktop" in response.text
    assert "mcp:tools:read" in response.text
    assert "mcp:tools:execute" in response.text
    assert "https://mcp.example" in response.text
    assert 'action="/oauth/consent-approval/form"' in response.text
    assert 'action="/oauth/consent-denial/form"' in response.text


@pytest.mark.anyio
async def test_authorize_json_contract_still_available(client):
    response = await client.get(
        "/oauth/authorize",
        params=_authorize_params(),
        headers={"accept": "application/json"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "consent_required"
    assert payload["client_name"] == "Claude Desktop"


@pytest.mark.anyio
async def test_approve_form_redirects_with_authorization_code(
    client, auth_code_service, auth_service
):
    response = await client.post(
        "/oauth/consent-approval/form",
        data=_authorize_params() | {"client_id": "client_123"},
        cookies={"isa_access_token": "browser-token"},
    )

    assert response.status_code == 303
    location = response.headers["location"]
    parsed = urlparse(location)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == (
        "https://client.example/callback"
    )
    query = parse_qs(parsed.query)
    assert query["code"] == ["auth_code_123"]
    assert query["state"] == ["csrf-state"]
    auth_service.verify_access_token_for_resource.assert_awaited_once_with(
        "browser-token"
    )
    auth_code_service.create_authorization_request.assert_awaited_once_with(
        client_id="client_123",
        redirect_uri="https://client.example/callback",
        scope="mcp:tools:read mcp:tools:execute",
        state="csrf-state",
        code_challenge="challenge_123",
        code_challenge_method="S256",
        resource="https://mcp.example",
        user_id="usr_123",
        organization_id="org_123",
    )


@pytest.mark.anyio
async def test_deny_form_redirects_with_access_denied(client):
    response = await client.post(
        "/oauth/consent-denial/form",
        data={
            "client_id": "client_123",
            "redirect_uri": "https://client.example/callback",
            "state": "csrf-state",
        },
    )

    assert response.status_code == 303
    parsed = urlparse(response.headers["location"])
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == (
        "https://client.example/callback"
    )
    query = parse_qs(parsed.query)
    assert query["error"] == ["access_denied"]
    assert query["state"] == ["csrf-state"]


@pytest.mark.anyio
async def test_deny_form_rejects_unregistered_redirect_uri(client):
    response = await client.post(
        "/oauth/consent-denial/form",
        data={
            "client_id": "client_123",
            "redirect_uri": "https://evil.example/callback",
            "state": "csrf-state",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_request: redirect_uri not registered"
