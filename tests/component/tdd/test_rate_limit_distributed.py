"""
L2 Component Tests — Distributed RateLimitMiddleware backend.

Verifies that two FastAPI app instances configured with the same Redis-backed
rate-limit counter share their state — i.e. requests against replica A count
toward the limit observed by replica B. This is the multi-replica behaviour
that PR #335 + issue #208 require.
"""

from __future__ import annotations

import pytest
import fakeredis.aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.rate_limit_backend import build_rate_limit_backend
from core.rate_limiter import (
    InMemoryBackend,
    RateLimitConfig,
    RateLimitMiddleware,
    RedisBackend,
)

pytestmark = [pytest.mark.component]


def _make_app(backend) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        default_limit=RateLimitConfig(requests=3, window_seconds=60),
        path_limits={
            "/api/v1/limited": RateLimitConfig(requests=2, window_seconds=60),
        },
        backend=backend,
        # Use a stable client key so both replicas hash to the same bucket.
        key_func=lambda request: request.headers.get("x-test-client", "shared-client"),
    )

    @app.get("/api/v1/limited")
    async def limited():
        return {"ok": True}

    @app.get("/api/v1/free")
    async def free():
        return {"ok": True}

    return app


def test_two_replicas_share_distributed_rate_limit_state():
    """Replica A consumes the budget; replica B sees the limit immediately.

    The test uses a single backend instance shared between two FastAPI app
    instances to prove the wiring path. In production this single instance
    is a ``RedisBackend`` (per ``build_rate_limit_backend``) — the contract
    that both middlewares observe the same counter holds regardless of the
    underlying store.
    """
    shared_backend = InMemoryBackend()

    replica_a = TestClient(_make_app(shared_backend))
    replica_b = TestClient(_make_app(shared_backend))

    # Burn the entire 2-req budget on replica A.
    r1 = replica_a.get("/api/v1/limited")
    r2 = replica_a.get("/api/v1/limited")
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text

    # Replica B must see the bucket as already exhausted.
    r3 = replica_b.get("/api/v1/limited")
    assert r3.status_code == 429, r3.text
    assert r3.json().get("error") == "Rate limit exceeded"


@pytest.mark.asyncio
async def test_redis_backend_shares_counter_across_replicas():
    """Direct backend-level proof using fakeredis: two RedisBackend instances
    pointing at the same FakeServer share their sliding-window counter."""
    server = fakeredis.aioredis.FakeServer()
    client_a = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    client_b = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)

    backend_a = RedisBackend(client_a)
    backend_b = RedisBackend(client_b)

    # Replica A increments three times.
    await backend_a.increment("rl:shared:/api/v1/limited", 60)
    await backend_a.increment("rl:shared:/api/v1/limited", 60)
    await backend_a.increment("rl:shared:/api/v1/limited", 60)

    # Replica B observes the shared counter.
    count = await backend_b.get_count("rl:shared:/api/v1/limited", 60)
    assert count == 3


def test_in_memory_backends_do_not_share_state():
    """Sanity check: with separate InMemoryBackend instances, replicas do NOT
    share — this is the regression #208 cures by switching to Redis."""
    backend_a = InMemoryBackend()
    backend_b = InMemoryBackend()

    replica_a = TestClient(_make_app(backend_a))
    replica_b = TestClient(_make_app(backend_b))

    # Burn the entire 2-req budget on replica A.
    replica_a.get("/api/v1/limited")
    replica_a.get("/api/v1/limited")

    # Replica B has its own counter -> still fresh.
    r3 = replica_b.get("/api/v1/limited")
    assert r3.status_code == 200, r3.text


def test_build_rate_limit_backend_returns_redis_backed_when_configured(monkeypatch):
    """When an env var is set, the helper should produce a Redis-backed wrapper.

    We monkeypatch ``redis.asyncio.from_url`` to return a fake redis instance
    so this stays an L2 test (no real network).
    """
    monkeypatch.setenv("PAYMENT_RATE_LIMIT_REDIS_URL", "redis://stub:6379/0")
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)

    def fake_from_url(url, **kwargs):
        assert url == "redis://stub:6379/0"
        return fake

    monkeypatch.setattr("redis.asyncio.from_url", fake_from_url)

    backend = build_rate_limit_backend(service_name="payment_service")

    # The returned object should NOT be an InMemoryBackend.
    from core.rate_limiter import InMemoryBackend

    assert not isinstance(backend, InMemoryBackend)


def test_storage_service_picks_up_storage_specific_env(monkeypatch):
    monkeypatch.delenv("PAYMENT_RATE_LIMIT_REDIS_URL", raising=False)
    monkeypatch.setenv("STORAGE_RATE_LIMIT_REDIS_URL", "redis://storage-stub:6379/0")

    captured = {}

    def fake_from_url(url, **kwargs):
        captured["url"] = url
        return fakeredis.aioredis.FakeRedis(decode_responses=True)

    monkeypatch.setattr("redis.asyncio.from_url", fake_from_url)

    backend = build_rate_limit_backend(service_name="storage_service")
    from core.rate_limiter import InMemoryBackend

    assert not isinstance(backend, InMemoryBackend)
    assert captured["url"] == "redis://storage-stub:6379/0"
