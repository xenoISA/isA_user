"""L1 unit tests for the MCP handshake validator (xenoISA/isA_#464 backend).

These tests cover the pre-flight gates and the URL/payload validation —
NO network is touched. The actual streamable-HTTP handshake is exercised
in tests/component/connector_service/test_connector_handshake_integration.py.

Covered failure modes:
  * Invalid / unsupported scheme (gopher://, file://, plain http://)
  * Missing hostname
  * Literal private / loopback / link-local IPs
  * DNS rebind — hostname resolves to a blocked IP
  * Feature flag ``ALLOW_PRIVATE_MCP_HOSTS`` bypass

And request payload shape:
  * CreateCustomMcpRequest validates label, auth_kind, url
"""

from __future__ import annotations


import pytest

from microservices.connector_service import handshake
from microservices.connector_service.handshake import (
    ERR_DNS,
    ERR_HOSTNAME,
    ERR_PRIVATE_IP,
    ERR_SCHEME,
    HandshakeResult,
    validate_mcp_url,
)
from microservices.connector_service.models import (
    CreateCustomMcpRequest,
    CustomMcpAuthKind,
)


# ---------------------------------------------------------------------------
# Scheme + hostname gates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSchemeGate:
    async def test_rejects_gopher_scheme(self):
        result = await validate_mcp_url("gopher://example.com/")
        assert result.ok is False
        assert result.error_code == ERR_SCHEME
        assert "gopher" in (result.error_message or "").lower()

    async def test_rejects_file_scheme(self):
        result = await validate_mcp_url("file:///etc/passwd")
        assert result.ok is False
        assert result.error_code == ERR_SCHEME

    async def test_rejects_plain_http_when_private_hosts_disallowed(self, monkeypatch):
        monkeypatch.delenv("ALLOW_PRIVATE_MCP_HOSTS", raising=False)
        result = await validate_mcp_url("http://example.com/mcp")
        assert result.ok is False
        assert result.error_code == ERR_SCHEME
        assert "http" in (result.error_message or "").lower()

    async def test_missing_hostname_is_rejected(self):
        result = await validate_mcp_url("https://")
        assert result.ok is False
        # urlparse on "https://" yields no hostname -> we surface
        # invalid_hostname rather than invalid_scheme.
        assert result.error_code in (ERR_HOSTNAME, ERR_SCHEME)


# ---------------------------------------------------------------------------
# Private-IP gate (literal + post-DNS)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPrivateIPGate:
    @pytest.mark.parametrize(
        "blocked_url",
        [
            "https://127.0.0.1/mcp",
            "https://10.0.0.5/mcp",
            "https://192.168.1.1/mcp",
            "https://169.254.169.254/latest/meta-data/",  # AWS metadata
            "https://[::1]/mcp",
        ],
    )
    async def test_blocks_literal_private_or_loopback_ip(
        self, blocked_url, monkeypatch
    ):
        monkeypatch.delenv("ALLOW_PRIVATE_MCP_HOSTS", raising=False)
        result = await validate_mcp_url(blocked_url)
        assert result.ok is False, f"{blocked_url} should be blocked"
        assert result.error_code == ERR_PRIVATE_IP

    async def test_dns_rebind_blocked_after_resolution(self, monkeypatch):
        """Hostname looks innocuous, but DNS returns a private IP -> blocked."""
        monkeypatch.delenv("ALLOW_PRIVATE_MCP_HOSTS", raising=False)

        def fake_getaddrinfo(host, *args, **kwargs):
            # Pretend the public hostname resolves to a private RFC1918 address.
            return [(2, 1, 6, "", ("10.5.6.7", 0))]

        monkeypatch.setattr(handshake.socket, "getaddrinfo", fake_getaddrinfo)
        result = await validate_mcp_url("https://innocent.example.com/mcp")
        assert result.ok is False
        assert result.error_code == ERR_PRIVATE_IP

    async def test_dns_failure_surfaces_dns_error(self, monkeypatch):
        monkeypatch.delenv("ALLOW_PRIVATE_MCP_HOSTS", raising=False)

        import socket as _socket

        def boom(*_a, **_kw):
            raise _socket.gaierror("nodename nor servname provided")

        monkeypatch.setattr(handshake.socket, "getaddrinfo", boom)
        result = await validate_mcp_url("https://does-not-resolve.example/mcp")
        assert result.ok is False
        assert result.error_code == ERR_DNS

    async def test_allow_private_hosts_lets_localhost_through_to_handshake(
        self, monkeypatch
    ):
        """ALLOW_PRIVATE_MCP_HOSTS bypasses both literal + DNS-post checks.

        The check returns ok=False because no HTTP server is at localhost
        in this unit test environment, but the error code must NOT be
        private_ip_blocked — the gate must be skipped.
        """
        monkeypatch.setenv("ALLOW_PRIVATE_MCP_HOSTS", "true")
        result = await validate_mcp_url("https://127.0.0.1:9/mcp")
        assert result.ok is False
        assert result.error_code != ERR_PRIVATE_IP


# ---------------------------------------------------------------------------
# Handshake call is mocked — verify routing through the validator
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestValidatorPathThrough:
    async def test_success_path_passes_tools_count_through(self, monkeypatch):
        """If everything else passes, the validator surfaces tools_count
        from the mocked handshake unchanged."""
        monkeypatch.setenv("ALLOW_PRIVATE_MCP_HOSTS", "true")

        async def fake_handshake(url, auth_kind, auth_secret):
            return HandshakeResult(ok=True, tools_count=7)

        monkeypatch.setattr(handshake, "_run_handshake", fake_handshake)
        result = await validate_mcp_url(
            "https://127.0.0.1:9999/mcp",
            auth_kind="pat",
            auth_secret="tok_abc",
        )
        assert result.ok is True
        assert result.tools_count == 7
        assert result.error_code is None

    async def test_handshake_failure_propagates(self, monkeypatch):
        monkeypatch.setenv("ALLOW_PRIVATE_MCP_HOSTS", "true")

        async def fake_handshake(url, auth_kind, auth_secret):
            return HandshakeResult(
                ok=False,
                error_code="handshake_unauthorized",
                error_message="server said no",
            )

        monkeypatch.setattr(handshake, "_run_handshake", fake_handshake)
        result = await validate_mcp_url("https://127.0.0.1:9999/mcp")
        assert result.ok is False
        assert result.error_code == "handshake_unauthorized"


# ---------------------------------------------------------------------------
# Pydantic request shape
# ---------------------------------------------------------------------------


class TestCreateCustomMcpRequest:
    def test_minimal_valid_request(self):
        req = CreateCustomMcpRequest(
            label="My MCP",
            url="https://mcp.example.com/sse",
            auth_kind=CustomMcpAuthKind.NONE,
        )
        assert req.auth_secret is None
        assert req.auth_kind == CustomMcpAuthKind.NONE

    def test_pat_request_carries_secret(self):
        req = CreateCustomMcpRequest(
            label="Notion",
            url="https://mcp.example.com/sse",
            auth_kind=CustomMcpAuthKind.PAT,
            auth_secret="sk_live_abc",
        )
        assert req.auth_secret == "sk_live_abc"

    def test_invalid_url_rejected(self):
        with pytest.raises(Exception):
            CreateCustomMcpRequest(
                label="Bad",
                url="not-a-url",
                auth_kind=CustomMcpAuthKind.NONE,
            )

    def test_label_required(self):
        with pytest.raises(Exception):
            CreateCustomMcpRequest(
                label="",
                url="https://mcp.example.com",
                auth_kind=CustomMcpAuthKind.NONE,
            )

    def test_label_max_length(self):
        with pytest.raises(Exception):
            CreateCustomMcpRequest(
                label="x" * 200,
                url="https://mcp.example.com",
                auth_kind=CustomMcpAuthKind.NONE,
            )


# ---------------------------------------------------------------------------
# Auth header construction (defense-in-depth check on the Bearer wiring)
# ---------------------------------------------------------------------------


class TestAuthHeader:
    def test_none_produces_no_header(self):
        assert handshake._auth_header("none", None) == {}

    def test_pat_produces_bearer(self):
        h = handshake._auth_header("pat", "tok_abc")
        assert h["Authorization"].startswith("Bearer ")
        assert "tok_abc" in h["Authorization"]

    def test_oauth_oob_uses_bearer(self):
        h = handshake._auth_header("oauth_oob", "oauth_xyz")
        assert h["Authorization"] == "Bearer oauth_xyz"

    def test_missing_secret_with_pat_falls_back_to_no_header(self):
        assert handshake._auth_header("pat", None) == {}
