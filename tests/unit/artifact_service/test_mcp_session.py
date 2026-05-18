"""L1 Unit — artifact_service MCP session-aware client + JWT pass-through.

Covers the #441 polish that lands the streamable-HTTP MCP transport with
a real ``initialize`` -> ``notifications/initialized`` -> ``tools/call``
handshake, session-id caching per (artifact_id, server_id), SSE response
parsing, session-expiry re-init, and JWT pass-through to the two upstream
services the artifact_service proxies to (isA_Model + isA_MCP).

Style follows ``tests/unit/artifact_service/test_artifact_runtime_llm.py``:
mock the I/O boundaries (repo + httpx + isA_Model client), exercise the
service method, assert on the response + side effects.
"""

from __future__ import annotations

import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from microservices.artifact_service.artifact_service import (
    ArtifactService,
    _McpSession,
    _McpSessionExpired,
)
from microservices.artifact_service.models import (
    Artifact,
    ArtifactMCPGrant,
    ArtifactRuntimeInvokeRequest,
    ArtifactRuntimeUsage,
    ArtifactStorageScope,
    ArtifactVisibility,
    MCPCallRequest,
    MCPGrantDecision,
    MCPGrantScope,
)


pytestmark = [pytest.mark.unit]


# ----- fixtures ---------------------------------------------------------------


def _make_artifact() -> Artifact:
    return Artifact(
        id="art_test123",
        owner_user_id="user_owner",
        title="My Artifact",
        content_type="code",
        visibility=ArtifactVisibility.PRIVATE,
        ai_runtime_enabled=True,
        storage_scope=ArtifactStorageScope.NONE,
    )


def _make_usage(*, calls: int = 0) -> ArtifactRuntimeUsage:
    return ArtifactRuntimeUsage(
        artifact_id="art_test123",
        user_id="user_owner",
        day_bucket="2025-01-01",
        tokens_in=0,
        tokens_out=0,
        calls=calls,
    )


def _make_grant() -> ArtifactMCPGrant:
    return ArtifactMCPGrant(
        id="grnt_abc",
        artifact_id="art_test123",
        user_id="user_owner",
        tool_name="fs.read_file",
        server_id="isA_MCP",
        decision=MCPGrantDecision.ALLOW,
        scope=MCPGrantScope.ALWAYS,
        approved_at=datetime.utcnow(),
    )


def _make_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_artifact = AsyncMock(return_value=_make_artifact())
    repo.get_today_usage = AsyncMock(return_value=_make_usage(calls=0))
    repo.record_usage = AsyncMock(return_value=_make_usage(calls=1))
    repo.find_always_grant = AsyncMock(return_value=_make_grant())
    repo.touch_grant_last_used = AsyncMock(return_value=True)
    return repo


class _FakeResponse:
    """Stand-in for httpx.Response — only the bits ``_McpSession`` reads."""

    def __init__(
        self,
        *,
        status_code: int = 200,
        headers: dict | None = None,
        content: bytes = b"",
        text: str | None = None,
    ):
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content
        self.text = text if text is not None else content.decode("utf-8", errors="replace")


class _FakeAsyncClient:
    """Mock httpx.AsyncClient — captures every POST + replays queued responses.

    Use ``.post`` directly as a fake; the production code uses
    ``async with httpx.AsyncClient(...) as client: await client.post(...)``
    so we also implement async context manager.
    """

    def __init__(self, responses: list[_FakeResponse]):
        self._responses = list(responses)
        self.calls: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, *, json=None, headers=None, **kwargs):
        self.calls.append({"url": url, "json": json, "headers": headers or {}})
        if not self._responses:
            raise RuntimeError("FakeAsyncClient ran out of queued responses")
        return self._responses.pop(0)


def _install_fake_httpx(monkeypatch, fake_client: _FakeAsyncClient) -> None:
    """Replace ``httpx.AsyncClient`` so ``_McpSession._post`` uses our fake."""
    import httpx

    def factory(*args, **kwargs):
        return fake_client

    monkeypatch.setattr(httpx, "AsyncClient", factory)


# ----- 1) session client initializes on first call, caches session_id --------


@pytest.mark.asyncio
async def test_mcp_session_initializes_and_caches_session_id(monkeypatch):
    """First tools/call performs initialize + notifications/initialized,
    captures the Mcp-Session-Id header, and reuses it on the second call."""
    fake = _FakeAsyncClient(
        responses=[
            # 1. initialize -> returns session id in header
            _FakeResponse(
                status_code=200,
                headers={"Mcp-Session-Id": "sess-abc", "Content-Type": "application/json"},
                content=b'{"jsonrpc":"2.0","id":"1","result":{"capabilities":{}}}',
            ),
            # 2. notifications/initialized -> 202 no body
            _FakeResponse(status_code=202, content=b""),
            # 3. tools/call -> result
            _FakeResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                content=b'{"jsonrpc":"2.0","id":"2","result":{"content":"hello"}}',
            ),
            # 4. tools/call again (no re-init) -> result
            _FakeResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                content=b'{"jsonrpc":"2.0","id":"3","result":{"content":"hi again"}}',
            ),
        ]
    )
    _install_fake_httpx(monkeypatch, fake)

    session = _McpSession(server_url="http://localhost:8081/mcp", server_id="isA_MCP")
    result_1 = await session.tools_call("fs.read", {"path": "/tmp/x"})
    result_2 = await session.tools_call("fs.read", {"path": "/tmp/y"})

    # Handshake (2 calls) + 2x tools/call = 4 total POSTs
    assert len(fake.calls) == 4

    methods = [call["json"]["method"] for call in fake.calls]
    assert methods == [
        "initialize",
        "notifications/initialized",
        "tools/call",
        "tools/call",
    ]

    # Session id was cached after initialize.
    assert session.session_id == "sess-abc"
    # All post-init calls carry the Mcp-Session-Id header.
    for call in fake.calls[1:]:
        assert call["headers"].get("Mcp-Session-Id") == "sess-abc"

    # Results were unwrapped from JSON-RPC ``result``.
    assert result_1["result"] == {"content": "hello"}
    assert result_2["result"] == {"content": "hi again"}


# ----- 2) session expiry triggers re-init ------------------------------------


@pytest.mark.asyncio
async def test_mcp_session_reinit_on_expiry(monkeypatch):
    """A 404 on tools/call (session expired) triggers a fresh handshake
    and retries the call exactly once."""
    fake = _FakeAsyncClient(
        responses=[
            # First handshake
            _FakeResponse(
                status_code=200,
                headers={"Mcp-Session-Id": "sess-1", "Content-Type": "application/json"},
                content=b'{"jsonrpc":"2.0","id":"1","result":{}}',
            ),
            _FakeResponse(status_code=202, content=b""),
            # tools/call -> 404 (server forgot the session)
            _FakeResponse(status_code=404, content=b"session expired"),
            # Re-init handshake
            _FakeResponse(
                status_code=200,
                headers={"Mcp-Session-Id": "sess-2", "Content-Type": "application/json"},
                content=b'{"jsonrpc":"2.0","id":"2","result":{}}',
            ),
            _FakeResponse(status_code=202, content=b""),
            # Retry tools/call -> success
            _FakeResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                content=b'{"jsonrpc":"2.0","id":"3","result":{"ok":true}}',
            ),
        ]
    )
    _install_fake_httpx(monkeypatch, fake)

    repo = _make_repo()
    service = ArtifactService(repository=repo)

    resp = await service.mcp_call(
        "art_test123",
        MCPCallRequest(
            user_id="user_owner",
            tool_name="fs.read_file",
            server_id="isA_MCP",
            args={"path": "/etc/hosts"},
        ),
    )

    # The session-aware path should have made: init(2) + call(1 -> 404)
    # then re-init(2) + retry(1) = 6 POSTs total. The fallback stub must
    # NOT have fired.
    assert len(fake.calls) == 6
    assert resp.requires_approval is False
    assert resp.result["result"] == {"ok": True}
    assert "stubbed" not in resp.result


# ----- 3) streaming SSE response is parsed correctly -------------------------


@pytest.mark.asyncio
async def test_mcp_session_parses_sse_event_stream(monkeypatch):
    """When the server returns Content-Type: text/event-stream, the client
    walks ``data: ...`` frames and picks the one with a ``result``."""
    sse_body = (
        b"event: message\n"
        b'data: {"jsonrpc":"2.0","id":"x","method":"notifications/progress","params":{"pct":50}}\n'
        b"\n"
        b"event: message\n"
        b'data: {"jsonrpc":"2.0","id":"2","result":{"content":"streamed"}}\n'
        b"\n"
    )
    fake = _FakeAsyncClient(
        responses=[
            _FakeResponse(
                status_code=200,
                headers={"Mcp-Session-Id": "sess-stream", "Content-Type": "application/json"},
                content=b'{"jsonrpc":"2.0","id":"1","result":{}}',
            ),
            _FakeResponse(status_code=202, content=b""),
            _FakeResponse(
                status_code=200,
                headers={"Content-Type": "text/event-stream"},
                content=sse_body,
            ),
        ]
    )
    _install_fake_httpx(monkeypatch, fake)

    session = _McpSession(server_url="http://localhost:8081/mcp", server_id="isA_MCP")
    result = await session.tools_call("slow.tool", {})

    # The streamed result was picked out of the SSE frames, NOT the progress one.
    assert result["result"] == {"content": "streamed"}


# ----- 4) non-streaming single-POST fallback still works ---------------------


@pytest.mark.asyncio
async def test_mcp_session_single_post_json_body(monkeypatch):
    """A vanilla server that just returns plain JSON (no SSE) still works —
    same handshake, but the response is application/json instead of an
    event stream. This is the most common case."""
    fake = _FakeAsyncClient(
        responses=[
            _FakeResponse(
                status_code=200,
                headers={"Mcp-Session-Id": "sess-plain", "Content-Type": "application/json"},
                content=b'{"jsonrpc":"2.0","id":"1","result":{"server":"vanilla"}}',
            ),
            _FakeResponse(status_code=200, content=b""),
            _FakeResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                content=b'{"jsonrpc":"2.0","id":"2","result":{"value":42}}',
            ),
        ]
    )
    _install_fake_httpx(monkeypatch, fake)

    session = _McpSession(server_url="http://localhost:8081/mcp", server_id="isA_MCP")
    result = await session.tools_call("calc.add", {"a": 40, "b": 2})

    assert result["tool_name"] == "calc.add"
    assert result["server_id"] == "isA_MCP"
    assert result["result"] == {"value": 42}


# ----- 5) JWT forwarded to upstream isA_MCP ----------------------------------


@pytest.mark.asyncio
async def test_jwt_forwarded_to_isa_mcp(monkeypatch):
    """When a caller-supplied bearer token is threaded through, every MCP
    request carries an ``Authorization: Bearer ...`` header."""
    fake = _FakeAsyncClient(
        responses=[
            _FakeResponse(
                status_code=200,
                headers={"Mcp-Session-Id": "sess-jwt", "Content-Type": "application/json"},
                content=b'{"jsonrpc":"2.0","id":"1","result":{}}',
            ),
            _FakeResponse(status_code=202, content=b""),
            _FakeResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                content=b'{"jsonrpc":"2.0","id":"2","result":{"ok":true}}',
            ),
        ]
    )
    _install_fake_httpx(monkeypatch, fake)

    repo = _make_repo()
    service = ArtifactService(repository=repo)

    resp = await service.mcp_call(
        "art_test123",
        MCPCallRequest(
            user_id="user_owner",
            tool_name="fs.read_file",
            server_id="isA_MCP",
            args={},
        ),
        auth_token="user-jwt-xyz",
    )

    assert resp.requires_approval is False
    # Every upstream POST carries the bearer token.
    for call in fake.calls:
        assert call["headers"].get("Authorization") == "Bearer user-jwt-xyz", f"missing JWT on call to {call['url']}"


# ----- 6) JWT forwarded to upstream isA_Model --------------------------------


@pytest.mark.asyncio
async def test_jwt_forwarded_to_isa_model():
    """``runtime_invoke`` passes the caller's bearer token to AsyncISAModel
    via the ``extra_headers`` kwarg so isA_Model sees the upstream user."""
    repo = _make_repo()
    service = ArtifactService(repository=repo)

    captured_headers: dict = {}

    class _FakeChoiceMessage:
        content = "ok"

    class _FakeChoice:
        message = _FakeChoiceMessage()

    class _FakeUsage:
        prompt_tokens = 5
        completion_tokens = 3

    class _FakeResponse:
        choices = [_FakeChoice()]
        usage = _FakeUsage()

    class _FakeAsyncISAModel:
        def __init__(self, *, base_url=None, extra_headers=None, **kwargs):
            captured_headers["base_url"] = base_url
            captured_headers["extra_headers"] = extra_headers
            self.chat = MagicMock()
            self.chat.completions = MagicMock()
            self.chat.completions.create = AsyncMock(return_value=_FakeResponse())

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    with patch.dict("sys.modules", {"isa_model.inference_client": MagicMock(AsyncISAModel=_FakeAsyncISAModel)}):
        result = await service.runtime_invoke(
            "art_test123",
            ArtifactRuntimeInvokeRequest(user_id="user_owner", prompt="hi"),
            auth_token="user-jwt-456",
        )

    assert result.output == "ok"
    # The bearer token was passed through to AsyncISAModel as extra_headers.
    assert captured_headers["extra_headers"] == {"Authorization": "Bearer user-jwt-456"}


# ----- 7) bearer-less path: no Authorization header is sent ------------------


@pytest.mark.asyncio
async def test_no_jwt_means_no_auth_header_on_mcp(monkeypatch):
    """When ``auth_token`` is None, MCP requests do NOT carry an
    Authorization header — upstream falls back to whatever service-to-service
    auth it already does."""
    fake = _FakeAsyncClient(
        responses=[
            _FakeResponse(
                status_code=200,
                headers={"Mcp-Session-Id": "sess-anon", "Content-Type": "application/json"},
                content=b'{"jsonrpc":"2.0","id":"1","result":{}}',
            ),
            _FakeResponse(status_code=202, content=b""),
            _FakeResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                content=b'{"jsonrpc":"2.0","id":"2","result":{"ok":true}}',
            ),
        ]
    )
    _install_fake_httpx(monkeypatch, fake)

    repo = _make_repo()
    service = ArtifactService(repository=repo)

    await service.mcp_call(
        "art_test123",
        MCPCallRequest(
            user_id="user_owner",
            tool_name="fs.read_file",
            server_id="isA_MCP",
            args={},
        ),
        # auth_token defaults to None — dev/no-auth path
    )

    for call in fake.calls:
        assert "Authorization" not in call["headers"], f"unexpected Authorization header on {call['url']}"


# ----- 8) HTTP 500 from MCP triggers the existing fallback path -------------


@pytest.mark.asyncio
async def test_mcp_call_5xx_falls_back_to_stub(monkeypatch, caplog):
    """A 5xx from MCP isn't a session-expiry signal — the service falls back
    to the stub (preserving the never-500 contract) and logs a warning."""
    fake = _FakeAsyncClient(
        responses=[
            _FakeResponse(
                status_code=500,
                content=b"oops",
            ),
        ]
    )
    _install_fake_httpx(monkeypatch, fake)

    repo = _make_repo()
    service = ArtifactService(repository=repo)

    with caplog.at_level(logging.WARNING, logger="microservices.artifact_service.artifact_service"):
        resp = await service.mcp_call(
            "art_test123",
            MCPCallRequest(
                user_id="user_owner",
                tool_name="fs.read_file",
                server_id="isA_MCP",
                args={"path": "/etc/hosts"},
            ),
        )

    assert resp.requires_approval is False
    assert resp.result["stubbed"] is True
    assert any("falling back to stub" in rec.message and "isA_MCP" in rec.message for rec in caplog.records), (
        "expected a fallback warning"
    )


# ----- 9) session cache is keyed per (artifact_id, server_id) ----------------


@pytest.mark.asyncio
async def test_mcp_session_cache_keyed_per_artifact_and_server(monkeypatch):
    """Two artifacts on the same server get distinct cached sessions, and
    two servers under the same artifact also get distinct sessions."""
    # Six handshake responses for three distinct cache keys.
    responses = []
    for sid in ("sess-art-A", "sess-art-B", "sess-art-A-other-server"):
        responses.append(
            _FakeResponse(
                status_code=200,
                headers={"Mcp-Session-Id": sid, "Content-Type": "application/json"},
                content=b'{"jsonrpc":"2.0","id":"1","result":{}}',
            )
        )
        responses.append(_FakeResponse(status_code=202, content=b""))
        responses.append(
            _FakeResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                content=b'{"jsonrpc":"2.0","id":"2","result":{}}',
            )
        )
    fake = _FakeAsyncClient(responses=responses)
    _install_fake_httpx(monkeypatch, fake)

    repo = _make_repo()
    service = ArtifactService(repository=repo)

    await service._invoke_mcp_tool("t", "srv1", {}, artifact_id="art_A")
    await service._invoke_mcp_tool("t", "srv1", {}, artifact_id="art_B")
    await service._invoke_mcp_tool("t", "srv2", {}, artifact_id="art_A")

    cache = service._mcp_sessions
    assert set(cache.keys()) == {
        ("art_A", "srv1"),
        ("art_B", "srv1"),
        ("art_A", "srv2"),
    }
    # Each session got its own id.
    ids = {cache[k].session_id for k in cache}
    assert ids == {"sess-art-A", "sess-art-B", "sess-art-A-other-server"}


# ----- 10) _McpSessionExpired propagates only on 401/404 ---------------------


@pytest.mark.asyncio
async def test_mcp_session_raises_expired_on_401(monkeypatch):
    """A 401 from the server during tools/call surfaces as _McpSessionExpired
    so the wrapper can re-init."""
    fake = _FakeAsyncClient(
        responses=[
            _FakeResponse(
                status_code=200,
                headers={"Mcp-Session-Id": "sess-401", "Content-Type": "application/json"},
                content=b'{"jsonrpc":"2.0","id":"1","result":{}}',
            ),
            _FakeResponse(status_code=202, content=b""),
            _FakeResponse(status_code=401, content=b"unauthorized"),
        ]
    )
    _install_fake_httpx(monkeypatch, fake)

    session = _McpSession(server_url="http://localhost:8081/mcp", server_id="isA_MCP")
    with pytest.raises(_McpSessionExpired):
        await session.tools_call("fs.read", {})
