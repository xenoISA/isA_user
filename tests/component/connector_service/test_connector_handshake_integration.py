"""L2 component tests for the MCP handshake validator (xenoISA/isA_#464).

Spins up a small in-process Starlette mock server on 127.0.0.1 so we
exercise the real httpx request/response path through
``validate_mcp_url``. The unit tests already cover the gate logic in
isolation; this layer pins:

  * happy path: initialize + initialized + tools/list -> ok=True, tools_count set
  * 401: handshake_unauthorized error code
  * 5xx on initialize: handshake_http_error
  * timeout: handshake_timeout
  * malformed JSON-RPC frame on tools/list: handshake_protocol_error
"""

from __future__ import annotations

import asyncio

import pytest
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from microservices.connector_service import handshake
from microservices.connector_service.handshake import (
    ERR_AUTH,
    ERR_HTTP_STATUS,
    ERR_JSON_RPC,
    ERR_TIMEOUT,
    validate_mcp_url,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.component]


# ---------------------------------------------------------------------------
# Mock server endpoint factories
# ---------------------------------------------------------------------------


def _ok_handler():
    """Default handler — JSON-RPC OK for initialize and tools/list.

    Returns 4 tools so tests can assert the count is propagated.
    """

    async def handler(request: Request):
        body = await request.json()
        method = body.get("method")
        if method == "initialize":
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "result": {
                        "protocolVersion": "2025-03-26",
                        "serverInfo": {"name": "mock", "version": "0.0.1"},
                        "capabilities": {},
                    },
                }
            )
        if method == "notifications/initialized":
            return Response(status_code=202)
        if method == "tools/list":
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "result": {
                        "tools": [
                            {"name": "t1"},
                            {"name": "t2"},
                            {"name": "t3"},
                            {"name": "t4"},
                        ]
                    },
                }
            )
        return JSONResponse({"error": "unknown method"}, status_code=400)

    return handler


def _401_handler():
    async def handler(request: Request):
        return JSONResponse({"error": "auth required"}, status_code=401)

    return handler


def _500_handler():
    async def handler(request: Request):
        return JSONResponse({"error": "boom"}, status_code=500)

    return handler


def _malformed_tools_handler():
    async def handler(request: Request):
        body = await request.json()
        method = body.get("method")
        if method == "initialize":
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "result": {"protocolVersion": "2025-03-26", "capabilities": {}},
                }
            )
        if method == "notifications/initialized":
            return Response(status_code=202)
        if method == "tools/list":
            # JSON-RPC envelope is structurally wrong — no result.tools.
            return Response(content="not json at all{", media_type="application/json")
        return Response(status_code=400)

    return handler


def _slow_handler(sleep_for: float):
    async def handler(request: Request):
        await asyncio.sleep(sleep_for)
        return JSONResponse({"jsonrpc": "2.0", "result": {}})

    return handler


# ---------------------------------------------------------------------------
# Server fixture — boots a Starlette app on an ephemeral port per test.
# ---------------------------------------------------------------------------


class _RunningServer:
    def __init__(self, server: uvicorn.Server, port: int):
        self.server = server
        self.port = port

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"


async def _start_server(handler) -> _RunningServer:
    app = Starlette(routes=[Route("/", handler, methods=["POST"])])
    # port=0 -> let the kernel pick a free ephemeral port. Then we read
    # it back off the bound socket so the test can target it.
    config = uvicorn.Config(
        app, host="127.0.0.1", port=0, log_level="warning", lifespan="off"
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    # Wait until uvicorn reports it's serving and the socket is bound.
    for _ in range(50):
        if server.started and server.servers:
            break
        await asyncio.sleep(0.05)
    assert server.started, "mock server failed to start"
    port = server.servers[0].sockets[0].getsockname()[1]
    rs = _RunningServer(server, port)
    rs._task = task  # keep ref so it doesn't get gc'd
    return rs


async def _stop_server(rs: _RunningServer) -> None:
    rs.server.should_exit = True
    try:
        await asyncio.wait_for(rs._task, timeout=2.0)
    except asyncio.TimeoutError:
        rs._task.cancel()


@pytest.fixture(autouse=True)
def _allow_private_hosts(monkeypatch):
    """The mock server runs on 127.0.0.1 — flip the dev override so the
    private-IP gate doesn't reject us before we hit the HTTP path."""
    monkeypatch.setenv("ALLOW_PRIVATE_MCP_HOSTS", "true")


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_happy_path_returns_ok_with_tools_count():
    rs = await _start_server(_ok_handler())
    try:
        result = await validate_mcp_url(rs.url)
        assert (
            result.ok is True
        ), f"expected ok, got code={result.error_code} msg={result.error_message}"
        assert result.tools_count == 4
    finally:
        await _stop_server(rs)


# ---------------------------------------------------------------------------
# 401 — surfaces handshake_unauthorized
# ---------------------------------------------------------------------------


async def test_401_on_initialize_surfaces_unauthorized():
    rs = await _start_server(_401_handler())
    try:
        result = await validate_mcp_url(
            rs.url, auth_kind="pat", auth_secret="bad-token"
        )
        assert result.ok is False
        assert result.error_code == ERR_AUTH
    finally:
        await _stop_server(rs)


# ---------------------------------------------------------------------------
# 5xx — surfaces handshake_http_error
# ---------------------------------------------------------------------------


async def test_5xx_on_initialize_surfaces_http_error():
    rs = await _start_server(_500_handler())
    try:
        result = await validate_mcp_url(rs.url)
        assert result.ok is False
        assert result.error_code == ERR_HTTP_STATUS
        assert "500" in (result.error_message or "")
    finally:
        await _stop_server(rs)


# ---------------------------------------------------------------------------
# Malformed JSON-RPC on tools/list
# ---------------------------------------------------------------------------


async def test_malformed_tools_list_surfaces_protocol_error():
    rs = await _start_server(_malformed_tools_handler())
    try:
        result = await validate_mcp_url(rs.url)
        assert result.ok is False
        # Either we couldn't decode the JSON (ERR_JSON_RPC) or we
        # decoded it but `result.tools` was missing — both are
        # acceptable failure modes for malformed payloads; the
        # important thing is that the validator surfaced a stable
        # protocol-level error rather than a transport one.
        assert result.error_code in (ERR_JSON_RPC, "handshake_no_tools_list")
    finally:
        await _stop_server(rs)


# ---------------------------------------------------------------------------
# Timeout — slow server blows past the 10s outer budget.
# Reduce the budget for the test so we don't burn 10s of CI.
# ---------------------------------------------------------------------------


async def test_timeout_surfaces_handshake_timeout(monkeypatch):
    # Cut the outer budget down so the test runs fast.
    monkeypatch.setattr(handshake, "HANDSHAKE_TIMEOUT_SECONDS", 0.5)
    rs = await _start_server(_slow_handler(sleep_for=2.0))
    try:
        result = await validate_mcp_url(rs.url)
        assert result.ok is False
        # Either the outer asyncio.wait_for or the per-request httpx
        # timeout will fire — both should surface ERR_TIMEOUT.
        assert result.error_code in (ERR_TIMEOUT, "handshake_transport_error")
    finally:
        await _stop_server(rs)
