from unittest.mock import AsyncMock

import httpx
import pytest

from microservices.auth_service import main as auth_main

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeOAuthClientRepository:
    def __init__(self, client=None):
        self.client = client or {
            "client_id": "client-1",
            "client_name": "Calendar <Client>",
            "client_type": "public",
            "redirect_uris": ["https://app.example/callback"],
            "require_pkce": True,
        }

    async def get_client(self, client_id):
        if client_id == self.client["client_id"]:
            return self.client
        return None


async def _caller():
    return {
        "user_id": "usr_1",
        "organization_id": "org_1",
    }


def _client():
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=auth_main.app),
        base_url="http://testserver",
        follow_redirects=False,
    )


@pytest.fixture
def authz_code_service():
    service = AsyncMock()
    service.create_authorization_request.return_value = {
        "code": "auth-code-123",
        "state": "csrf-state",
        "redirect_uri": "https://app.example/callback",
    }
    return service


@pytest.fixture(autouse=True)
def dependency_overrides(authz_code_service):
    auth_main.app.dependency_overrides[auth_main.get_oauth_client_repository] = lambda: FakeOAuthClientRepository()
    auth_main.app.dependency_overrides[auth_main.get_authorization_code_service] = lambda: authz_code_service
    auth_main.app.dependency_overrides[auth_main.get_current_caller] = _caller
    yield
    auth_main.app.dependency_overrides.clear()


def _authorize_params(**overrides):
    params = {
        "response_type": "code",
        "client_id": "client-1",
        "redirect_uri": "https://app.example/callback",
        "scope": "mcp:tools:execute mcp:resources:read",
        "state": "csrf-state",
        "resource": "https://mcp.example",
        "code_challenge": "pkce-challenge",
        "code_challenge_method": "S256",
    }
    params.update(overrides)
    return params


async def test_authorize_renders_server_consent_screen_for_html_accept():
    async with _client() as client:
        response = await client.get(
            "/oauth/authorize",
            params=_authorize_params(),
            headers={"Accept": "text/html"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Calendar &lt;Client&gt;" in response.text
    assert "mcp:tools:execute" in response.text
    assert "mcp:resources:read" in response.text
    assert "https://mcp.example" in response.text
    assert 'name="decision" value="approve"' in response.text
    assert 'name="decision" value="deny"' in response.text


async def test_authorize_keeps_json_payload_for_api_clients():
    async with _client() as client:
        response = await client.get(
            "/oauth/authorize",
            params=_authorize_params(),
            headers={"Accept": "application/json"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "action": "consent_required",
        "client_id": "client-1",
        "client_name": "Calendar <Client>",
        "redirect_uri": "https://app.example/callback",
        "scope": "mcp:tools:execute mcp:resources:read",
        "state": "csrf-state",
        "resource": "https://mcp.example",
        "code_challenge": "pkce-challenge",
        "code_challenge_method": "S256",
    }


async def test_consent_approve_redirects_back_with_authorization_code(authz_code_service):
    async with _client() as client:
        response = await client.post(
            "/oauth/consent",
            data={
                **_authorize_params(),
                "decision": "approve",
            },
            headers={"Authorization": "Bearer user-token"},
        )

    assert response.status_code == 303
    assert response.headers["location"] == ("https://app.example/callback?code=auth-code-123&state=csrf-state")
    authz_code_service.create_authorization_request.assert_awaited_once_with(
        client_id="client-1",
        redirect_uri="https://app.example/callback",
        scope="mcp:tools:execute mcp:resources:read",
        state="csrf-state",
        code_challenge="pkce-challenge",
        code_challenge_method="S256",
        resource="https://mcp.example",
        user_id="usr_1",
        organization_id="org_1",
    )


async def test_consent_deny_redirects_back_with_access_denied(authz_code_service):
    async with _client() as client:
        response = await client.post(
            "/oauth/consent",
            data={
                **_authorize_params(),
                "decision": "deny",
            },
            headers={"Authorization": "Bearer user-token"},
        )

    assert response.status_code == 303
    assert response.headers["location"] == ("https://app.example/callback?error=access_denied&state=csrf-state")
    authz_code_service.create_authorization_request.assert_not_awaited()


async def test_consent_deny_validates_redirect_uri_before_redirecting():
    async with _client() as client:
        response = await client.post(
            "/oauth/consent",
            data={
                **_authorize_params(redirect_uri="https://attacker.example/callback"),
                "decision": "deny",
            },
            headers={"Authorization": "Bearer user-token"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_request: redirect_uri not registered"
