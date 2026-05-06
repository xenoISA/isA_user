"""
L1 Unit Tests — core.redis_cache.

Verifies the cache wrapper contract (get / set / delete / delete_pattern,
namespace prefixing, miss-on-disconnect fallback, multi-replica
visibility) using fakeredis to stay hermetic.

Issue #347 — shared Redis cache for compliance / membership / authorization.
"""

from __future__ import annotations

import asyncio
import json

import fakeredis.aioredis
import pytest

from core import redis_cache as cache_mod
from core.redis_cache import (
    CacheInvalidationError,
    RedisCache,
    build_redis_cache,
    resolve_cache_redis_url,
)


pytestmark = [pytest.mark.unit]


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _make_fake() -> fakeredis.aioredis.FakeRedis:
    """Build an isolated fake redis client (binary-safe — matches our wrapper)."""
    return fakeredis.aioredis.FakeRedis(decode_responses=False)


# ----------------------------------------------------------------------
# URL resolution
# ----------------------------------------------------------------------


def test_resolve_cache_redis_url_prefers_service_specific(monkeypatch):
    monkeypatch.setenv("COMPLIANCE_CACHE_REDIS_URL", "redis://compliance:6379/0")
    monkeypatch.setenv("CACHE_REDIS_URL", "redis://generic:6379/0")
    monkeypatch.setenv("REDIS_URL", "redis://platform:6379/0")

    assert (
        resolve_cache_redis_url(service_name="compliance_service")
        == "redis://compliance:6379/0"
    )


def test_resolve_cache_redis_url_falls_back_to_platform(monkeypatch):
    monkeypatch.delenv("COMPLIANCE_CACHE_REDIS_URL", raising=False)
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://platform:6379/0")

    assert (
        resolve_cache_redis_url(service_name="compliance_service")
        == "redis://platform:6379/0"
    )


def test_resolve_cache_redis_url_returns_none_when_unset(monkeypatch):
    for var in (
        "COMPLIANCE_CACHE_REDIS_URL",
        "CACHE_REDIS_URL",
        "REDIS_URL",
    ):
        monkeypatch.delenv(var, raising=False)

    assert resolve_cache_redis_url(service_name="compliance_service") is None


# ----------------------------------------------------------------------
# Get / set / delete
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_and_get_roundtrip():
    cache = RedisCache("policy", client=_make_fake(), default_ttl=60)

    ok = await cache.set("p1", {"name": "default", "version": 2})
    assert ok is True

    got = await cache.get("p1")
    assert got == {"name": "default", "version": 2}


@pytest.mark.asyncio
async def test_get_returns_none_on_miss():
    cache = RedisCache("policy", client=_make_fake())
    assert await cache.get("missing-key") is None


@pytest.mark.asyncio
async def test_set_respects_ttl_argument():
    fake = _make_fake()
    cache = RedisCache("tier", client=fake)

    await cache.set("bronze", {"tier": "bronze"}, ttl=42)
    ttl = await fake.ttl("tier:bronze")
    assert 0 < ttl <= 42


@pytest.mark.asyncio
async def test_delete_removes_key():
    cache = RedisCache("perm", client=_make_fake())
    await cache.set("u1:resource", {"granted": True})
    assert await cache.get("u1:resource") is not None

    assert await cache.delete("u1:resource") is True
    assert await cache.get("u1:resource") is None


@pytest.mark.asyncio
async def test_delete_pattern_purges_matching_keys():
    cache = RedisCache("perm", client=_make_fake())

    await cache.set("u1:r1", {"v": 1})
    await cache.set("u1:r2", {"v": 2})
    await cache.set("u2:r1", {"v": 3})

    deleted = await cache.delete_pattern("u1:*")
    assert deleted == 2

    assert await cache.get("u1:r1") is None
    assert await cache.get("u1:r2") is None
    # Other namespace must remain.
    assert await cache.get("u2:r1") == {"v": 3}


# ----------------------------------------------------------------------
# Namespace isolation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_namespace_keeps_keys_isolated():
    server = fakeredis.aioredis.FakeServer()
    client_a = fakeredis.aioredis.FakeRedis(server=server, decode_responses=False)
    client_b = fakeredis.aioredis.FakeRedis(server=server, decode_responses=False)

    policy_cache = RedisCache("policy", client=client_a)
    tier_cache = RedisCache("tier", client=client_b)

    await policy_cache.set("default", {"src": "policy"})
    await tier_cache.set("default", {"src": "tier"})

    # Same logical key, different namespaces -> different physical keys.
    assert await policy_cache.get("default") == {"src": "policy"}
    assert await tier_cache.get("default") == {"src": "tier"}


# ----------------------------------------------------------------------
# Multi-replica visibility (acceptance criterion)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_caches_share_state_via_redis():
    """Replica A writes; replica B reads the same value back through Redis.

    This is the multi-replica coherency assertion from issue #347 —
    simulated by two cache instances pointing at the same FakeServer.
    """
    server = fakeredis.aioredis.FakeServer()
    client_a = fakeredis.aioredis.FakeRedis(server=server, decode_responses=False)
    client_b = fakeredis.aioredis.FakeRedis(server=server, decode_responses=False)

    cache_a = RedisCache("policy", client=client_a)
    cache_b = RedisCache("policy", client=client_b)

    await cache_a.set("org-1", {"version": 1, "rules": ["pii"]})

    # Replica B sees the value immediately.
    assert await cache_b.get("org-1") == {"version": 1, "rules": ["pii"]}

    # Replica A invalidates -> replica B observes the eviction.
    await cache_a.delete("org-1")
    assert await cache_b.get("org-1") is None


# ----------------------------------------------------------------------
# Failure / fallback semantics
# ----------------------------------------------------------------------


class _FlakyClient:
    """Async redis double that raises on the first GET."""

    def __init__(self):
        self.calls = 0

    async def get(self, key):
        self.calls += 1
        raise ConnectionError("redis is down")

    async def set(self, *_, **__):
        raise ConnectionError("redis is down")

    async def delete(self, *_):
        raise ConnectionError("redis is down")

    async def ping(self):
        raise ConnectionError("redis is down")


@pytest.mark.asyncio
async def test_get_returns_none_when_redis_errors():
    cache = RedisCache("policy", client=_FlakyClient())
    assert await cache.get("k") is None
    # The latch flips so subsequent reads bypass redis entirely.
    assert cache.healthy is False


@pytest.mark.asyncio
async def test_set_returns_false_when_redis_errors():
    cache = RedisCache("policy", client=_FlakyClient())
    assert await cache.set("k", {"x": 1}) is False
    assert cache.healthy is False


@pytest.mark.asyncio
async def test_subsequent_get_short_circuits_after_failure():
    flaky = _FlakyClient()
    cache = RedisCache("policy", client=flaky)

    await cache.get("k")
    await cache.get("k2")
    await cache.get("k3")

    # The latch must keep the wrapper from re-hitting Redis after the
    # first failure — exactly one call to the underlying client.
    assert flaky.calls == 1


@pytest.mark.asyncio
async def test_ping_returns_true_when_alive():
    cache = RedisCache("policy", client=_make_fake())
    assert await cache.ping() is True
    assert cache.healthy is True


@pytest.mark.asyncio
async def test_ping_returns_false_when_dead():
    cache = RedisCache("policy", client=_FlakyClient())
    assert await cache.ping() is False
    assert cache.healthy is False


# ----------------------------------------------------------------------
# Custom serialisers (Pydantic-style)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_custom_serialiser_roundtrip():
    cache = RedisCache("tier", client=_make_fake())

    payload = {"tier": "gold", "multiplier": "1.5"}

    def my_dumps(v):
        return ("V1::" + json.dumps(v)).encode()

    def my_loads(b: bytes):
        text = b.decode()
        assert text.startswith("V1::")
        return json.loads(text[len("V1::"):])

    await cache.set("gold", payload, dumps=my_dumps)
    assert await cache.get("gold", loads=my_loads) == payload


# ----------------------------------------------------------------------
# get_or_load convenience wrapper
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_or_load_caches_on_miss():
    cache = RedisCache("policy", client=_make_fake())
    calls = {"n": 0}

    async def loader():
        calls["n"] += 1
        return {"loaded": True}

    first = await cache.get_or_load("key", loader)
    second = await cache.get_or_load("key", loader)

    assert first == {"loaded": True}
    assert second == {"loaded": True}
    # Loader runs once on the miss; the second call is served from Redis.
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_get_or_load_runs_loader_when_redis_down():
    """If Redis is unavailable, the loader still runs (DB fallback path)."""
    cache = RedisCache("policy", client=_FlakyClient())
    calls = {"n": 0}

    async def loader():
        calls["n"] += 1
        return {"db": True}

    out = await cache.get_or_load("key", loader)
    assert out == {"db": True}
    assert calls["n"] == 1


# ----------------------------------------------------------------------
# Builder
# ----------------------------------------------------------------------


def test_build_redis_cache_returns_disabled_cache_without_url(monkeypatch):
    for var in ("COMPLIANCE_CACHE_REDIS_URL", "CACHE_REDIS_URL", "REDIS_URL"):
        monkeypatch.delenv(var, raising=False)

    cache = build_redis_cache("policy", service_name="compliance_service")
    assert cache.available is False
    assert cache.healthy is False


def test_build_redis_cache_with_explicit_client():
    fake = _make_fake()
    cache = build_redis_cache("policy", client=fake, default_ttl=120)
    assert cache.available is True
    assert cache.namespace == "policy"
    assert cache.default_ttl == 120


@pytest.mark.asyncio
async def test_build_redis_cache_lazy_url_construction(monkeypatch):
    monkeypatch.setenv("COMPLIANCE_CACHE_REDIS_URL", "redis://stub:6379/0")

    fake = _make_fake()

    def fake_from_url(url, **kwargs):
        assert url == "redis://stub:6379/0"
        return fake

    monkeypatch.setattr("redis.asyncio.from_url", fake_from_url)

    cache = build_redis_cache("policy", service_name="compliance_service")
    assert cache.available is True

    # First read materialises the client.
    assert await cache.set("p", {"v": 1}) is True
    assert await cache.get("p") == {"v": 1}


# ----------------------------------------------------------------------
# Misuse
# ----------------------------------------------------------------------


def test_namespace_required():
    with pytest.raises(ValueError):
        RedisCache("", client=_make_fake())


# ----------------------------------------------------------------------
# core.health integration
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_probe_reports_healthy_when_alive():
    from core.health import HealthCheck

    cache = RedisCache("policy", client=_make_fake())
    health = HealthCheck(service_name="test_svc")
    health.add_redis_cache(lambda: cache)

    response = await health.check()
    body = json.loads(response.body)
    assert body["status"] == "healthy"
    assert body["dependencies"]["redis_cache"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_probe_reports_degraded_when_disabled():
    """Cache without a configured client should yield ``degraded``."""
    from core.health import HealthCheck

    cache = build_redis_cache("policy", service_name="ghost_service")
    # Force the disabled state regardless of env.
    cache._available = False
    health = HealthCheck(service_name="test_svc")
    health.add_redis_cache(lambda: cache)

    response = await health.check()
    body = json.loads(response.body)
    # Critical=False -> failure -> degraded, not unhealthy.
    assert body["status"] == "degraded"
    assert response.status_code == 200


# ----------------------------------------------------------------------
# Issue #347 follow-up — delete_pattern surfaces failures (PR #357 #3)
# ----------------------------------------------------------------------


class _ScanFailClient:
    """Async redis double whose ``scan_iter`` raises on first iteration."""

    def __init__(self):
        self.delete_calls = 0

    def scan_iter(self, *, match=None):
        async def _gen():
            raise ConnectionError("scan blew up")
            yield  # pragma: no cover - unreachable; makes this an async gen

        return _gen()

    async def delete(self, *_):
        self.delete_calls += 1
        return 1

    async def get(self, *_):
        return None

    async def set(self, *_, **__):
        return True

    async def ping(self):
        return True


@pytest.mark.asyncio
async def test_delete_pattern_raises_when_scan_fails():
    """SCAN failure must surface as ``CacheInvalidationError`` so callers
    can fail-closed on revoke (issue #347 follow-up, PR #357 review #3).
    """
    cache = RedisCache("perm", client=_ScanFailClient())
    with pytest.raises(CacheInvalidationError):
        await cache.delete_pattern("user:42:*")


@pytest.mark.asyncio
async def test_delete_pattern_swallows_when_raise_on_error_false():
    """Best-effort callers can opt out of the typed error."""
    cache = RedisCache("perm", client=_ScanFailClient())
    # Must not raise; returns 0 because scan_iter blew up before yielding.
    assert await cache.delete_pattern("user:42:*", raise_on_error=False) == 0


@pytest.mark.asyncio
async def test_delete_pattern_raises_when_cache_unavailable():
    """An unconfigured cache must not silently 'succeed' invalidation."""
    cache = RedisCache("perm", client=None, url=None)
    cache._available = False
    cache._healthy = False
    with pytest.raises(CacheInvalidationError):
        await cache.delete_pattern("user:42:*")


# ----------------------------------------------------------------------
# Issue #347 follow-up — half-open latch recovery (PR #357 review #4)
# ----------------------------------------------------------------------


class _RecoveringClient:
    """Async redis double that fails N times then succeeds.

    Lets us drive the half-open probe path without sleeping in tests.
    """

    def __init__(self, fail_count: int = 1):
        self._remaining_failures = fail_count
        self.get_calls = 0
        self.ping_calls = 0
        self.set_calls = 0
        self._store: dict = {}

    async def get(self, key):
        self.get_calls += 1
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise ConnectionError("blip")
        return self._store.get(key)

    async def set(self, key, value, ex=None):
        self.set_calls += 1
        self._store[key] = value
        return True

    async def delete(self, *keys):
        for k in keys:
            self._store.pop(k, None)
        return len(keys)

    async def ping(self):
        self.ping_calls += 1
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise ConnectionError("blip")
        return True


@pytest.mark.asyncio
async def test_latch_recovers_after_cooldown():
    """Once cooldown elapses, a successful PING flips ``healthy`` back."""
    flaky = _RecoveringClient(fail_count=1)
    cache = RedisCache("perm", client=flaky, recovery_cooldown_seconds=0.0)

    # First read trips the latch.
    assert await cache.get("k") is None
    assert cache.healthy is False

    # Cooldown is 0s -> the next read attempts the recovery probe and
    # finds Redis healthy. After recovery the second call exercises the
    # actual GET path (no remaining failures), proving we re-entered
    # the live read path.
    await flaky.set("perm:k", b'{"v":1}')
    got = await cache.get("k")
    assert got == {"v": 1}
    assert cache.healthy is True


@pytest.mark.asyncio
async def test_latch_does_not_recover_before_cooldown():
    """Within the cooldown window no probe is issued."""
    flaky = _RecoveringClient(fail_count=1)
    # Cooldown larger than any test would take.
    cache = RedisCache("perm", client=flaky, recovery_cooldown_seconds=60.0)

    # Trip the latch.
    assert await cache.get("k") is None
    assert cache.healthy is False
    initial_pings = flaky.ping_calls

    # Subsequent reads short-circuit; ping_calls must NOT increase.
    for _ in range(3):
        assert await cache.get("k") is None
    assert flaky.ping_calls == initial_pings


@pytest.mark.asyncio
async def test_latch_recovery_only_one_concurrent_probe():
    """Concurrent reads after cooldown must not all probe — exactly one wins."""
    flaky = _RecoveringClient(fail_count=1)
    cache = RedisCache("perm", client=flaky, recovery_cooldown_seconds=0.0)

    # Trip the latch.
    assert await cache.get("k") is None
    assert cache.healthy is False
    pings_before = flaky.ping_calls

    # Fire many concurrent reads — only one should probe.
    results = await asyncio.gather(*[cache.get("k") for _ in range(10)])
    assert all(r is None for r in results)  # nothing in store yet
    # At most one probe issued among the concurrent callers.
    assert (flaky.ping_calls - pings_before) <= 1


# ----------------------------------------------------------------------
# Issue #347 follow-up — env-var prefix stability (PR #357 review #7)
# ----------------------------------------------------------------------


def test_service_env_prefix_strips_service_suffix():
    """The env-var prefix is documented; lock the contract under test."""
    assert (
        cache_mod._service_env_prefix("authorization_service")
        == "AUTHORIZATION"
    )
    assert cache_mod._service_env_prefix("compliance_service") == "COMPLIANCE"
    assert cache_mod._service_env_prefix("membership_service") == "MEMBERSHIP"


def test_authorization_resolves_authorization_cache_redis_url(monkeypatch):
    """The authorization service must read AUTHORIZATION_CACHE_REDIS_URL."""
    monkeypatch.setenv("AUTHORIZATION_CACHE_REDIS_URL", "redis://az:6379/0")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    assert (
        resolve_cache_redis_url(service_name="authorization_service")
        == "redis://az:6379/0"
    )
