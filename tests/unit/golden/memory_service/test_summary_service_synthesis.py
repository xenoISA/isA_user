"""
Unit tests for `memory_service.summary_service.synthesize_summary`.

Covers the LLM-backed synthesis path added for #439 follow-up:
  - When isA_Model returns a valid JSON payload, the function returns the
    model's narrative + highlights (not the deterministic stub).
  - When the LLM client raises (model unreachable, timeout, etc.), the function
    must degrade to the deterministic fallback shape so the regenerate route
    still returns a valid MemorySummary row.

The isA_Model client is patched at the `summary_service.AsyncISAModel` symbol
(module-level binding) so we never make a real network call. We also force
`_ISA_MODEL_AVAILABLE = True` in case the import probe at module load failed
in this test environment.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from microservices.memory_service import summary_service

pytestmark = [pytest.mark.unit, pytest.mark.asyncio, pytest.mark.golden]


# ---------------------------------------------------------------------------
# Helpers — minimal async-context-manager stand-in for AsyncISAModel
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
    """Drop-in for `AsyncISAModel(base_url=...)` used by summary_service."""

    last_instance: "_FakeAsyncISAModel | None" = None

    def __init__(self, *, response=None, error: Exception | None = None):
        self._completions = _FakeChatCompletions(response=response, error=error)
        self.chat = _FakeChat(self._completions)
        _FakeAsyncISAModel.last_instance = self

    def __call__(self, *args, **kwargs):  # noqa: D401 - acts as constructor proxy
        # The class itself doubles as the factory: `AsyncISAModel(base_url=...)`
        # calls __call__, which returns self so we keep one fixed fake instance.
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _build_response(content: str, *, usage: Dict[str, int] | None = None):
    """Compose the SimpleNamespace shape that mimics the OpenAI SDK response."""
    msg = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=msg)
    usage_ns = SimpleNamespace(**usage) if usage else None
    return SimpleNamespace(choices=[choice], usage=usage_ns)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_regenerate_calls_llm_when_available(monkeypatch):
    """LLM returns valid JSON → synthesize_summary uses the model output."""
    llm_json = json.dumps(
        {
            "content": "The user prefers concise answers and lives in Tokyo.\n\nThey work on AI infrastructure.\n\nRecurring theme: prompt engineering.",
            "highlights": [
                "Lives in Tokyo",
                "Prefers concise answers",
                "Works on AI infra",
                "Interested in prompt engineering",
                "Active in 2026",
            ],
        }
    )
    fake = _FakeAsyncISAModel(
        response=_build_response(llm_json, usage={"prompt_tokens": 120, "completion_tokens": 80, "total_tokens": 200})
    )

    monkeypatch.setattr(summary_service, "AsyncISAModel", fake)
    monkeypatch.setattr(summary_service, "_ISA_MODEL_AVAILABLE", True)

    memories = [
        {"memory_type": "factual", "content": "User lives in Tokyo.", "importance_score": 0.9},
        {"memory_type": "preference", "content": "Prefers concise answers.", "importance_score": 0.8},
        {"memory_type": "episodic", "content": "Shipped #439 hard slice.", "importance_score": 0.7},
    ]

    result = await summary_service.synthesize_summary(memories)

    assert result["fallback"] is False
    assert "Tokyo" in result["content"]
    assert "fallback summary" not in result["content"]
    assert isinstance(result["highlights"], list)
    assert len(result["highlights"]) == 5
    assert "Lives in Tokyo" in result["highlights"]

    # The LLM client must have been called exactly once with the JSON contract.
    assert len(fake._completions.calls) == 1
    call = fake._completions.calls[0]
    assert call["response_format"] == {"type": "json_object"}
    # User prompt carries the bulleted memories.
    user_msg = next(m for m in call["messages"] if m["role"] == "user")
    assert "Memories (" in user_msg["content"]
    assert "User lives in Tokyo." in user_msg["content"]


async def test_regenerate_falls_back_on_llm_error(monkeypatch):
    """LLM raises → synthesize_summary returns the deterministic stub."""
    fake = _FakeAsyncISAModel(error=RuntimeError("model_service unreachable"))

    monkeypatch.setattr(summary_service, "AsyncISAModel", fake)
    monkeypatch.setattr(summary_service, "_ISA_MODEL_AVAILABLE", True)

    memories = [
        {"memory_type": "factual", "content": "User lives in Tokyo."},
        {"memory_type": "preference", "content": "Prefers concise answers."},
    ]

    result = await summary_service.synthesize_summary(memories)

    assert result["fallback"] is True
    assert result["content"] == "Summary of 2 memories (LLM synthesis unavailable — fallback summary)."
    assert result["highlights"] == ["2 memories on record"]


async def test_regenerate_caps_at_top_50_by_importance(monkeypatch):
    """Inputs >50 memories must be ranked + trimmed before the prompt is built."""
    fake = _FakeAsyncISAModel(
        response=_build_response(
            json.dumps(
                {
                    "content": "narrative",
                    "highlights": ["a", "b", "c", "d", "e"],
                }
            )
        )
    )
    monkeypatch.setattr(summary_service, "AsyncISAModel", fake)
    monkeypatch.setattr(summary_service, "_ISA_MODEL_AVAILABLE", True)

    # 60 memories; only the high-importance ones should reach the prompt.
    memories = [{"memory_type": "factual", "content": f"low-{i}", "importance_score": 0.1} for i in range(50)] + [
        {"memory_type": "factual", "content": f"HIGH-{i}", "importance_score": 0.99} for i in range(10)
    ]

    await summary_service.synthesize_summary(memories)

    call = fake._completions.calls[0]
    user_msg = next(m for m in call["messages"] if m["role"] == "user")
    # All 10 HIGH-* must be present (they win the importance sort).
    for i in range(10):
        assert f"HIGH-{i}" in user_msg["content"]
    # The prompt header advertises exactly 50 memories used.
    assert "Memories (50)" in user_msg["content"]
