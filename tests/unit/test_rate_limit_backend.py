"""
L1 Unit Tests — Distributed rate-limit backend factory.

Validates that ``core.rate_limit_backend.build_rate_limit_backend`` selects
between an in-memory backend and a Redis-backed one based on environment
variables, and that Redis failures degrade gracefully to the in-memory
fallback.
"""

from __future__ import annotations

import pytest

from core.rate_limit_backend import (
    FallbackRateLimitBackend,
    build_rate_limit_backend,
    build_sliding_window_counter,
)
from core.rate_limiter import InMemoryBackend, RateLimitConfig, SlidingWindowCounter

pytestmark = [pytest.mark.unit]


def test_returns_in_memory_when_no_redis_configured(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("RATE_LIMIT_REDIS_URL", raising=False)
    monkeypatch.delenv("PAYMENT_RATE_LIMIT_REDIS_URL", raising=False)

    backend = build_rate_limit_backend(service_name="payment_service")

    assert isinstance(backend, InMemoryBackend)


def test_uses_service_specific_env_var_first(monkeypatch):
    monkeypatch.setenv(
        "PAYMENT_RATE_LIMIT_REDIS_URL", "redis://service-specific:6379/0"
    )
    monkeypatch.setenv("RATE_LIMIT_REDIS_URL", "redis://platform:6379/0")
    monkeypatch.setenv("REDIS_URL", "redis://generic:6379/0")

    captured = {}

    def fake_from_url(url, **kwargs):
        captured["url"] = url
        return _DummyRedis()

    monkeypatch.setattr("redis.asyncio.from_url", fake_from_url)

    backend = build_rate_limit_backend(service_name="payment_service")

    assert isinstance(backend, FallbackRateLimitBackend)
    assert captured["url"] == "redis://service-specific:6379/0"


def test_falls_back_to_platform_env_var(monkeypatch):
    monkeypatch.delenv("PAYMENT_RATE_LIMIT_REDIS_URL", raising=False)
    monkeypatch.setenv("RATE_LIMIT_REDIS_URL", "redis://platform:6379/0")
    monkeypatch.delenv("REDIS_URL", raising=False)

    captured = {}

    def fake_from_url(url, **kwargs):
        captured["url"] = url
        return _DummyRedis()

    monkeypatch.setattr("redis.asyncio.from_url", fake_from_url)

    backend = build_rate_limit_backend(service_name="payment_service")

    assert isinstance(backend, FallbackRateLimitBackend)
    assert captured["url"] == "redis://platform:6379/0"


def test_falls_back_to_generic_redis_url(monkeypatch):
    monkeypatch.delenv("PAYMENT_RATE_LIMIT_REDIS_URL", raising=False)
    monkeypatch.delenv("RATE_LIMIT_REDIS_URL", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://generic:6379/0")

    captured = {}

    def fake_from_url(url, **kwargs):
        captured["url"] = url
        return _DummyRedis()

    monkeypatch.setattr("redis.asyncio.from_url", fake_from_url)

    backend = build_rate_limit_backend(service_name="payment_service")

    assert isinstance(backend, FallbackRateLimitBackend)
    assert captured["url"] == "redis://generic:6379/0"


def test_redis_init_failure_returns_in_memory(monkeypatch):
    monkeypatch.setenv("PAYMENT_RATE_LIMIT_REDIS_URL", "redis://broken:6379/0")

    def fake_from_url(url, **kwargs):
        raise RuntimeError("boom — cannot reach redis")

    monkeypatch.setattr("redis.asyncio.from_url", fake_from_url)

    backend = build_rate_limit_backend(service_name="payment_service")

    assert isinstance(backend, InMemoryBackend)


def test_build_sliding_window_counter_wraps_backend(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("RATE_LIMIT_REDIS_URL", raising=False)
    monkeypatch.delenv("AUTH_RATE_LIMIT_REDIS_URL", raising=False)

    counter = build_sliding_window_counter(service_name="auth_service")

    assert isinstance(counter, SlidingWindowCounter)
    assert isinstance(counter.backend, InMemoryBackend)


@pytest.mark.asyncio
async def test_fallback_backend_uses_primary_when_healthy():
    primary = _RecordingBackend()
    fallback = InMemoryBackend()

    backend = FallbackRateLimitBackend(primary, fallback)
    count = await backend.increment("key", window=60)

    assert count == 1
    assert primary.calls == [("increment", "key", 60)]


@pytest.mark.asyncio
async def test_fallback_backend_degrades_to_memory_on_primary_error():
    primary = _RecordingBackend(raise_on=("increment",))
    fallback = InMemoryBackend()

    backend = FallbackRateLimitBackend(primary, fallback)

    # First call: primary raises -> fallback handles it
    count1 = await backend.increment("key", window=60)
    assert count1 == 1

    # Second call: primary marked as down, fallback used directly
    count2 = await backend.increment("key", window=60)
    assert count2 == 2
    # Primary was tried only once
    assert primary.calls == [("increment", "key", 60)]


@pytest.mark.asyncio
async def test_fallback_backend_routes_get_count_through_primary():
    primary = _RecordingBackend()
    fallback = InMemoryBackend()
    backend = FallbackRateLimitBackend(primary, fallback)

    primary.next_return = 7
    count = await backend.get_count("key", window=60)
    assert count == 7
    assert ("get_count", "key", 60) in primary.calls


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _DummyRedis:
    """Minimal redis stand-in for from_url stubbing."""

    async def ping(self):
        return True


class _RecordingBackend:
    """Records calls and optionally raises to simulate a failing Redis."""

    def __init__(self, raise_on: tuple = ()):
        self.calls: list = []
        self.raise_on = set(raise_on)
        self.next_return = 1

    async def increment(self, key: str, window: float) -> int:
        self.calls.append(("increment", key, window))
        if "increment" in self.raise_on:
            raise RuntimeError("redis down")
        return self.next_return

    async def get_count(self, key: str, window: float) -> int:
        self.calls.append(("get_count", key, window))
        if "get_count" in self.raise_on:
            raise RuntimeError("redis down")
        return self.next_return

    async def get_ttl(self, key: str) -> float:
        self.calls.append(("get_ttl", key))
        if "get_ttl" in self.raise_on:
            raise RuntimeError("redis down")
        return 1.0


def test_rate_limit_config_unchanged():
    """Sanity check that the helper hasn't broken core.rate_limiter contract."""
    cfg = RateLimitConfig(requests=10, window_seconds=30)
    assert cfg.requests == 10
    assert cfg.window_seconds == 30
