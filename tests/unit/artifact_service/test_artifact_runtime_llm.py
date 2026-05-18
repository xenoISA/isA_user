"""L1 Unit — artifact_service Phase 3 polish (isA_Model + MCP transport).

Covers xenoISA/isA_user#441 Phase 3 follow-up: real isA_Model proxy for
``runtime_invoke`` and best-effort MCP transport for ``mcp_call``. The
service falls back to the original stub on upstream failure so the route
never 500s — these tests pin both the healthy and degraded paths.

Style follows ``tests/unit/storage_service/test_storage_service_config.py``:
mock the I/O boundaries (repo + isA_Model + aiohttp), exercise the service
method, assert on the response + side effects.
"""

from __future__ import annotations

import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from microservices.artifact_service.artifact_service import ArtifactService
from microservices.artifact_service.models import (
    Artifact,
    ArtifactRuntimeInvokeRequest,
    ArtifactRuntimeUsage,
    ArtifactStorageScope,
    ArtifactVisibility,
    ArtifactMCPGrant,
    MCPCallRequest,
    MCPGrantDecision,
    MCPGrantScope,
)


pytestmark = [pytest.mark.unit]


# ----- fixtures ---------------------------------------------------------------


def _make_artifact(*, ai_runtime_enabled: bool = True) -> Artifact:
    return Artifact(
        id="art_test123",
        owner_user_id="user_owner",
        title="My Artifact",
        content_type="code",
        visibility=ArtifactVisibility.PRIVATE,
        ai_runtime_enabled=ai_runtime_enabled,
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
    """Build an AsyncMock-driven repo stub with sensible defaults."""
    repo = MagicMock()
    repo.get_artifact = AsyncMock(return_value=_make_artifact())
    repo.get_today_usage = AsyncMock(return_value=_make_usage(calls=0))
    repo.record_usage = AsyncMock(return_value=_make_usage(calls=1))
    repo.find_always_grant = AsyncMock(return_value=_make_grant())
    repo.touch_grant_last_used = AsyncMock(return_value=True)
    return repo


# ----- runtime_invoke: healthy LLM path ---------------------------------------


@pytest.mark.asyncio
async def test_runtime_invoke_calls_llm_when_available():
    """When isA_Model returns a result, the response contains the model's
    output (NOT the stub prefix) and the booked token counts come from the
    model's usage block."""
    repo = _make_repo()
    service = ArtifactService(repository=repo)

    # Mock the isA_Model call at the service-method level — keeps the test
    # off the network and out of the inference_client innards.
    fake_response = ("The answer is 4.", 17, 9)  # output, prompt_tokens, completion_tokens
    with patch.object(
        ArtifactService,
        "_call_isa_model",
        new=AsyncMock(return_value=fake_response),
    ) as mock_llm:
        result = await service.runtime_invoke(
            "art_test123",
            ArtifactRuntimeInvokeRequest(user_id="user_owner", prompt="what is 2+2?"),
        )

    assert mock_llm.await_count == 1
    # Healthy path: output is the real model response, NOT the stub.
    assert result.output == "The answer is 4."
    assert not result.output.startswith("Phase 3 stub response for:")
    # Token counts come from the model when present.
    assert result.tokens_in == 17
    assert result.tokens_out == 9
    # Usage is still booked through the repo.
    repo.record_usage.assert_awaited_once()
    kwargs = repo.record_usage.await_args.kwargs
    assert kwargs["tokens_in"] == 17
    assert kwargs["tokens_out"] == 9


@pytest.mark.asyncio
async def test_runtime_invoke_estimates_tokens_when_llm_omits_usage():
    """If the model doesn't return usage counts, we estimate from string
    lengths and still book the call."""
    repo = _make_repo()
    service = ArtifactService(repository=repo)
    fake = ("hello world!", None, None)
    with patch.object(ArtifactService, "_call_isa_model", new=AsyncMock(return_value=fake)):
        result = await service.runtime_invoke(
            "art_test123",
            ArtifactRuntimeInvokeRequest(user_id="user_owner", prompt="hi"),
        )

    # Estimates: prompt "hi" -> max(1, 2//4) -> 1; output "hello world!" -> 12//4 = 3
    assert result.tokens_in == 1
    assert result.tokens_out == 3
    assert result.output == "hello world!"


# ----- runtime_invoke: fallback path ------------------------------------------


@pytest.mark.asyncio
async def test_runtime_invoke_falls_back_on_llm_error(caplog):
    """When isA_Model raises, the route returns the original stub shape
    (so the endpoint never 500s), still records usage, and logs the fallback."""
    repo = _make_repo()
    service = ArtifactService(repository=repo)

    with caplog.at_level(logging.WARNING, logger="microservices.artifact_service.artifact_service"):
        with patch.object(
            ArtifactService,
            "_call_isa_model",
            new=AsyncMock(side_effect=RuntimeError("isA_Model down")),
        ):
            result = await service.runtime_invoke(
                "art_test123",
                ArtifactRuntimeInvokeRequest(user_id="user_owner", prompt="what is 2+2?"),
            )

    # Fallback contract — same as Phase 3 stub.
    assert result.output == "Phase 3 stub response for: what is 2+2?"
    assert result.tokens_out == 32
    assert result.tokens_in >= 1
    # Usage still booked.
    repo.record_usage.assert_awaited_once()
    # Warning logged.
    assert any("falling back to stub" in rec.message and "isA_Model" in rec.message for rec in caplog.records), (
        "expected a fallback warning to be logged"
    )


@pytest.mark.asyncio
async def test_runtime_invoke_quota_check_runs_before_llm():
    """Quota exhaustion short-circuits before we ever call the model."""
    from microservices.artifact_service.artifact_service import ArtifactQuotaExceededError

    repo = _make_repo()
    # Pre-fill usage at the cap.
    repo.get_today_usage = AsyncMock(return_value=_make_usage(calls=999_999))
    service = ArtifactService(repository=repo)

    with patch.object(ArtifactService, "_call_isa_model", new=AsyncMock()) as mock_llm:
        with pytest.raises(ArtifactQuotaExceededError):
            await service.runtime_invoke(
                "art_test123",
                ArtifactRuntimeInvokeRequest(user_id="user_owner", prompt="hi"),
            )

    mock_llm.assert_not_called()
    repo.record_usage.assert_not_called()


# ----- mcp_call: real transport ----------------------------------------------


@pytest.mark.asyncio
async def test_mcp_call_invokes_real_tool_when_mcp_available():
    """With an active allow+always grant, mcp_call proxies to isA_MCP and
    returns the real (non-stubbed) result."""
    repo = _make_repo()
    service = ArtifactService(repository=repo)

    fake_real_result = {
        "tool_name": "fs.read_file",
        "server_id": "isA_MCP",
        "result": {"content": "127.0.0.1 localhost\n"},
    }
    with patch.object(
        ArtifactService,
        "_invoke_mcp_tool",
        new=AsyncMock(return_value=fake_real_result),
    ) as mock_mcp:
        resp = await service.mcp_call(
            "art_test123",
            MCPCallRequest(
                user_id="user_owner",
                tool_name="fs.read_file",
                server_id="isA_MCP",
                args={"path": "/etc/hosts"},
            ),
        )

    mock_mcp.assert_awaited_once()
    assert resp.requires_approval is False
    assert resp.result == fake_real_result
    # When wired, the stub sentinel must NOT be present.
    assert "stubbed" not in resp.result


@pytest.mark.asyncio
async def test_mcp_call_falls_back_on_transport_error(caplog):
    """When isA_MCP is unreachable, mcp_call returns the stub body (so the
    endpoint never 500s) and logs a warning."""
    repo = _make_repo()
    service = ArtifactService(repository=repo)

    with caplog.at_level(logging.WARNING, logger="microservices.artifact_service.artifact_service"):
        with patch.object(
            ArtifactService,
            "_invoke_mcp_tool",
            new=AsyncMock(side_effect=ConnectionError("isA_MCP down")),
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

    assert resp.requires_approval is False
    assert resp.result["stubbed"] is True
    assert resp.result["tool_name"] == "fs.read_file"
    assert resp.result["server_id"] == "isA_MCP"
    assert resp.result["args"] == {"path": "/etc/hosts"}
    assert any("falling back to stub" in rec.message and "isA_MCP" in rec.message for rec in caplog.records), (
        "expected a fallback warning to be logged"
    )


@pytest.mark.asyncio
async def test_mcp_call_without_grant_still_returns_approval_prompt():
    """The approval gate runs before the transport — no grant means no call
    to isA_MCP at all."""
    repo = _make_repo()
    repo.find_always_grant = AsyncMock(return_value=None)
    service = ArtifactService(repository=repo)

    with patch.object(ArtifactService, "_invoke_mcp_tool", new=AsyncMock()) as mock_mcp:
        resp = await service.mcp_call(
            "art_test123",
            MCPCallRequest(
                user_id="user_owner",
                tool_name="shell.exec",
                server_id="isA_MCP",
                args={},
            ),
        )

    mock_mcp.assert_not_called()
    assert resp.requires_approval is True


# ----- prompt envelope -------------------------------------------------------


def test_build_runtime_prompt_includes_artifact_metadata():
    """The system envelope must mention the artifact title and content_type
    so the model has a tiny bit of context."""
    artifact = _make_artifact()
    envelope = ArtifactService._build_runtime_prompt(artifact, "Hello")
    assert "My Artifact" in envelope
    assert "code" in envelope
    assert "Hello" in envelope


def test_resolve_max_tokens_clamps_to_cap():
    from microservices.artifact_service.artifact_service import (
        DEFAULT_RUNTIME_MAX_TOKENS,
        RUNTIME_MAX_TOKENS_CAP,
    )

    assert ArtifactService._resolve_max_tokens(None) == DEFAULT_RUNTIME_MAX_TOKENS
    assert ArtifactService._resolve_max_tokens(100) == 100
    assert ArtifactService._resolve_max_tokens(10_000) == RUNTIME_MAX_TOKENS_CAP
    assert ArtifactService._resolve_max_tokens(0) == 1
