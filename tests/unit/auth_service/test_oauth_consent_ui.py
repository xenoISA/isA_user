import pytest

from microservices.auth_service.oauth_consent import (
    authorization_consent_payload,
    redirect_with_oauth_params,
    render_consent_screen,
    wants_html_response,
)

pytestmark = pytest.mark.unit


def _payload(**overrides):
    payload = authorization_consent_payload(
        client={
            "client_id": "client-1",
            "client_name": "Calendar <Client>",
        },
        client_id="client-1",
        redirect_uri="https://app.example/callback",
        scope="mcp:tools:execute mcp:resources:read",
        state="csrf-state",
        resource="https://mcp.example",
        code_challenge="pkce-challenge",
        code_challenge_method="S256",
    )
    payload.update(overrides)
    return payload


def test_authorization_consent_payload_preserves_json_contract():
    assert _payload() == {
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


def test_render_consent_screen_escapes_client_and_renders_scopes():
    html = render_consent_screen(_payload())

    assert "Calendar &lt;Client&gt;" in html
    assert "mcp:tools:execute" in html
    assert "mcp:resources:read" in html
    assert "https://mcp.example" in html
    assert 'name="decision" value="approve"' in html
    assert 'name="decision" value="deny"' in html
    assert 'name="code_challenge" value="pkce-challenge"' in html


def test_render_consent_screen_handles_empty_scope_and_resource():
    html = render_consent_screen(_payload(scope="", resource=None))

    assert "No scopes requested" in html
    assert "Default resource" in html


def test_wants_html_response_uses_accept_header():
    assert wants_html_response("text/html,application/xhtml+xml") is True
    assert wants_html_response("application/json") is False
    assert wants_html_response("*/*") is False


def test_redirect_with_oauth_params_appends_code_and_state():
    redirect = redirect_with_oauth_params(
        "https://app.example/callback",
        {
            "code": "auth-code-123",
            "state": "csrf-state",
        },
    )

    assert (
        redirect == "https://app.example/callback?code=auth-code-123&state=csrf-state"
    )


def test_redirect_with_oauth_params_preserves_query_and_fragment():
    redirect = redirect_with_oauth_params(
        "https://app.example/callback?existing=1#done",
        {
            "error": "access_denied",
            "state": "",
        },
    )

    assert (
        redirect == "https://app.example/callback?existing=1&error=access_denied#done"
    )
