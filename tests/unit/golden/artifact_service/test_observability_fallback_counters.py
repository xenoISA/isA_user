"""L1 Unit — observability hooks for artifact_service upstream fallbacks (#461).

Covers xenoISA/isA_user#461: when isA_Model / isA_MCP are unreachable, the
service falls back to a deterministic stub.  Previously this degradation was
silent — these tests pin the three-channel observability we wired in:

    1. ``artifact_service_upstream_fallback_total{operation, reason}`` ↑
    2. ``sentry_sdk.capture_exception(exc)`` fires (mocked — DSN not set in tests)
    3. WARN log emitted with structured fields

We test the helper in isolation AND through the real service-method call so
regressions in either layer are caught.
"""

from __future__ import annotations

import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from microservices.artifact_service import observability
from microservices.artifact_service.artifact_service import ArtifactService
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

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# ----- fixtures (mirror test_artifact_runtime_llm.py shape) -----------------


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
        day_bucket="2026-05-19",
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


def _counter_value(operation: str, reason: str) -> float:
    """Read the current value of the (operation, reason) cell.

    Prometheus client lets us snapshot via ``Counter._value.get()`` on the
    labelled child — we wrap it so the test reads naturally.  Returns 0.0 when
    the label combination has never been incremented in this process.
    """
    try:
        child = observability.upstream_fallback_total.labels(operation=operation, reason=reason)
        # prometheus_client.Counter -> child._value.get()
        return float(child._value.get())  # type: ignore[attr-defined]
    except Exception:
        return 0.0


# ----- runtime_invoke fallback -> counter + sentry ---------------------------


@pytest.mark.asyncio
async def test_runtime_invoke_increments_counter_on_fallback():
    """When isA_Model raises, the fallback path bumps the Prometheus counter
    AND calls sentry_sdk.capture_exception, AND keeps the original stub
    contract intact."""
    repo = _make_repo()
    service = ArtifactService(repository=repo)

    err = TimeoutError("isA_Model upstream timed out")

    before = _counter_value("runtime_invoke", "Timeout")

    with patch("sentry_sdk.capture_exception") as mock_sentry:
        with patch.object(
            ArtifactService,
            "_call_isa_model",
            new=AsyncMock(side_effect=err),
        ):
            result = await service.runtime_invoke(
                "art_test123",
                ArtifactRuntimeInvokeRequest(user_id="user_owner", prompt="ping"),
            )

    # Stub contract intact — endpoint still returns 200 with the canned shape.
    assert result.output == "Phase 3 stub response for: ping"
    assert result.tokens_out == 32

    # Counter ticked exactly once on the (runtime_invoke, Timeout) cell.
    after = _counter_value("runtime_invoke", "Timeout")
    assert after - before == pytest.approx(1.0), (
        f"counter cell (runtime_invoke, Timeout) must bump by 1, got {after - before}"
    )

    # Sentry was invoked with the same exception so the dashboard groups it.
    assert mock_sentry.called, "sentry_sdk.capture_exception must fire on fallback"
    sent_exc = mock_sentry.call_args[0][0]
    assert sent_exc is err


# ----- mcp_call fallback -> counter + sentry ---------------------------------


@pytest.mark.asyncio
async def test_mcp_call_increments_counter_on_fallback():
    """When isA_MCP is unreachable, mcp_call falls back to the stub AND
    increments the counter under operation=mcp_call."""
    repo = _make_repo()
    service = ArtifactService(repository=repo)

    err = ConnectionError("isA_MCP transport failed")

    before = _counter_value("mcp_call", "ConnectionError")

    with patch("sentry_sdk.capture_exception") as mock_sentry:
        with patch.object(
            ArtifactService,
            "_invoke_mcp_tool",
            new=AsyncMock(side_effect=err),
        ):
            resp = await service.mcp_call(
                "art_test123",
                MCPCallRequest(
                    user_id="user_owner",
                    tool_name="fs.read_file",
                    server_id="isA_MCP",
                    args={"path": "/etc/hosts"},
                ),
            )

    # Stub contract intact.
    assert resp.requires_approval is False
    assert resp.result["stubbed"] is True

    # Counter bumped on (mcp_call, ConnectionError).
    after = _counter_value("mcp_call", "ConnectionError")
    assert after - before == pytest.approx(1.0)

    # Sentry capture fired with the same exception.
    assert mock_sentry.called
    assert mock_sentry.call_args[0][0] is err


# ----- structured log emission ----------------------------------------------


@pytest.mark.asyncio
async def test_runtime_invoke_fallback_emits_structured_warn(caplog):
    """The observability helper logs at WARN with the canonical
    ``fallback_fired service=... operation=... reason=...`` shape so devs can
    grep without Sentry."""
    repo = _make_repo()
    service = ArtifactService(repository=repo)

    with caplog.at_level(logging.WARNING):
        with patch("sentry_sdk.capture_exception"):
            with patch.object(
                ArtifactService,
                "_call_isa_model",
                new=AsyncMock(side_effect=RuntimeError("boom")),
            ):
                await service.runtime_invoke(
                    "art_test123",
                    ArtifactRuntimeInvokeRequest(user_id="user_owner", prompt="hello"),
                )

    matching = [
        rec
        for rec in caplog.records
        if "fallback_fired" in rec.message
        and "operation=runtime_invoke" in rec.message
        and "service=artifact_service" in rec.message
    ]
    assert matching, "expected a structured fallback_fired WARN line from observability helper"


# ----- helper-level coverage -------------------------------------------------


def test_classify_reason_buckets_known_exceptions():
    """The reason classifier MUST keep label cardinality bounded — exhaustive
    coverage of the buckets we declare in the docstring."""
    assert observability.classify_reason(TimeoutError("x")) == "Timeout"
    assert observability.classify_reason(ConnectionError("x")) == "ConnectionError"

    # Synthesise an HTTPError-named exception (httpx/requests both ship one).
    class HTTPStatusError(Exception):
        pass

    assert observability.classify_reason(HTTPStatusError("503")) == "HTTPError"

    import json as _json

    assert observability.classify_reason(_json.JSONDecodeError("x", "y", 0)) == "ParseError"
    assert observability.classify_reason(ValueError("bad shape")) == "ParseError"
    assert observability.classify_reason(RuntimeError("anything else")) == "Other"


def test_init_sentry_is_noop_without_dsn(monkeypatch):
    """When SENTRY_DSN is unset, init_sentry returns False and does NOT call
    sentry_sdk.init — dev/local environments stay silent."""
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    # Reset the idempotency flag so this test sees a fresh call.
    monkeypatch.setattr(observability, "_SENTRY_READY", False)

    with patch("sentry_sdk.init") as mock_init:
        result = observability.init_sentry("artifact_service")

    assert result is False
    mock_init.assert_not_called()


def test_record_upstream_fallback_returns_reason_label():
    """The helper returns the classified reason so callers can include it in
    their own structured logs / response headers without re-classifying."""
    with patch("sentry_sdk.capture_exception"):
        reason = observability.record_upstream_fallback(
            operation="runtime_invoke",
            exc=TimeoutError("slow upstream"),
            prompt_len=42,
        )
    assert reason == "Timeout"
