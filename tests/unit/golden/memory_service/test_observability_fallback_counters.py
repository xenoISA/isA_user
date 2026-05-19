"""L1 Unit — observability hooks for memory_service.synthesize_summary (#461).

When isA_Model is unreachable, ``summary_service.synthesize_summary`` falls
back to the deterministic ``"Summary of N memories (LLM synthesis
unavailable — fallback summary)."`` payload.  This test pins that the
fallback path now:

    1. increments ``memory_service_upstream_fallback_total{operation, reason}``
    2. calls ``sentry_sdk.capture_exception`` so the failure shows up in the
       dashboard (no-op when DSN absent — we mock it here)
    3. still returns the canonical fallback shape (regression guard).
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from microservices.memory_service import observability, summary_service

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# ---------------------------------------------------------------------------
# Test doubles (mirror test_summary_service_synthesis.py)
# ---------------------------------------------------------------------------


class _FakeChatCompletions:
    def __init__(self, *, response=None, error: Exception | None = None):
        self._response = response
        self._error = error
        self.calls: List[Dict[str, Any]] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._response


class _FakeChat:
    def __init__(self, completions: _FakeChatCompletions):
        self.completions = completions


class _FakeAsyncISAModel:
    def __init__(self, *, response=None, error: Exception | None = None):
        self._completions = _FakeChatCompletions(response=response, error=error)
        self.chat = _FakeChat(self._completions)
        self.init_calls: List[Dict[str, Any]] = []

    def __call__(self, *args, **kwargs):
        self.init_calls.append({"args": args, "kwargs": kwargs})
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _counter_value(operation: str, reason: str) -> float:
    try:
        child = observability.upstream_fallback_total.labels(operation=operation, reason=reason)
        return float(child._value.get())  # type: ignore[attr-defined]
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_synthesize_summary_increments_counter_on_llm_error(monkeypatch):
    """isA_Model raises → counter ↑, Sentry capture fired, fallback shape kept."""
    err = TimeoutError("model_service upstream timeout")
    fake = _FakeAsyncISAModel(error=err)

    monkeypatch.setattr(summary_service, "AsyncISAModel", fake)
    monkeypatch.setattr(summary_service, "_ISA_MODEL_AVAILABLE", True)

    memories = [
        {"memory_type": "factual", "content": "User lives in Tokyo."},
        {"memory_type": "preference", "content": "Prefers concise answers."},
    ]

    before = _counter_value("summary_regenerate", "Timeout")

    with patch("sentry_sdk.capture_exception") as mock_sentry:
        result = await summary_service.synthesize_summary(memories)

    # Fallback contract intact.
    assert result["fallback"] is True
    assert result["content"] == "Summary of 2 memories (LLM synthesis unavailable — fallback summary)."

    # Counter ticked on (summary_regenerate, Timeout).
    after = _counter_value("summary_regenerate", "Timeout")
    assert after - before == pytest.approx(1.0), (
        f"counter cell (summary_regenerate, Timeout) must bump by 1, got {after - before}"
    )

    # Sentry capture called with the same exception.
    assert mock_sentry.called
    assert mock_sentry.call_args[0][0] is err


async def test_synthesize_summary_increments_counter_on_json_parse_error(monkeypatch):
    """isA_Model returns non-JSON → fall back, counter increments under ParseError."""
    bad_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="this is not json {{{"))],
        usage=None,
    )
    fake = _FakeAsyncISAModel(response=bad_response)

    monkeypatch.setattr(summary_service, "AsyncISAModel", fake)
    monkeypatch.setattr(summary_service, "_ISA_MODEL_AVAILABLE", True)

    memories = [{"memory_type": "factual", "content": "User lives in Tokyo."}]

    before = _counter_value("summary_regenerate", "ParseError")

    with patch("sentry_sdk.capture_exception") as mock_sentry:
        result = await summary_service.synthesize_summary(memories)

    # JSONDecodeError → ParseError bucket.
    assert result["fallback"] is True
    after = _counter_value("summary_regenerate", "ParseError")
    assert after - before == pytest.approx(1.0)
    assert mock_sentry.called
    # The captured exception is a JSONDecodeError subclass of ValueError.
    captured = mock_sentry.call_args[0][0]
    assert isinstance(captured, json.JSONDecodeError)


async def test_synthesize_summary_no_counter_bump_on_happy_path(monkeypatch):
    """Healthy LLM response → counter must NOT increment (regression guard)."""
    good = json.dumps(
        {
            "content": "narrative " * 3,
            "highlights": ["a", "b", "c", "d", "e"],
        }
    )
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=good))],
        usage=None,
    )
    fake = _FakeAsyncISAModel(response=response)
    monkeypatch.setattr(summary_service, "AsyncISAModel", fake)
    monkeypatch.setattr(summary_service, "_ISA_MODEL_AVAILABLE", True)

    memories = [{"memory_type": "factual", "content": "User lives in Tokyo."}]

    before_any = sum(
        _counter_value("summary_regenerate", r)
        for r in ("Timeout", "ConnectionError", "HTTPError", "ParseError", "Other")
    )

    with patch("sentry_sdk.capture_exception") as mock_sentry:
        result = await summary_service.synthesize_summary(memories)

    after_any = sum(
        _counter_value("summary_regenerate", r)
        for r in ("Timeout", "ConnectionError", "HTTPError", "ParseError", "Other")
    )

    assert result["fallback"] is False
    assert after_any == pytest.approx(before_any)
    assert not mock_sentry.called


# ---------------------------------------------------------------------------
# Helper-level
# ---------------------------------------------------------------------------


def test_memory_service_init_sentry_noop_without_dsn(monkeypatch):
    """memory_service.observability.init_sentry is the same idempotent no-op."""
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.setattr(observability, "_SENTRY_READY", False)

    with patch("sentry_sdk.init") as mock_init:
        result = observability.init_sentry("memory_service")

    assert result is False
    mock_init.assert_not_called()
