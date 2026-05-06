"""
L1 Unit Tests — core.distributed_lock.

Verifies the lock contract (atomic SETNX + TTL, token-validated release,
contention metric, fail-closed on Redis outage, half-open recovery,
idempotent retry contract via guard()).

Issue #348 — Redis-based distributed locks for event idempotency.
"""

from __future__ import annotations

import asyncio

import fakeredis.aioredis
import pytest

from core.distributed_lock import (
    DistributedLock,
    DistributedLockError,
    LockContended,
    build_distributed_lock,
)
from core.redis_cache import RedisCache


pytestmark = [pytest.mark.unit]


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _make_fake() -> fakeredis.aioredis.FakeRedis:
    return fakeredis.aioredis.FakeRedis(decode_responses=False)


def _make_shared_pair():
    server = fakeredis.aioredis.FakeServer()
    return (
        fakeredis.aioredis.FakeRedis(server=server, decode_responses=False),
        fakeredis.aioredis.FakeRedis(server=server, decode_responses=False),
    )


# ----------------------------------------------------------------------
# Acquire / release semantics
# ----------------------------------------------------------------------


async def test_acquire_returns_token_on_first_attempt():
    lock = DistributedLock("wallet_service", client=_make_fake())
    token = await lock.acquire("evt-1", ttl_seconds=30)
    assert token is not None and len(token) > 0


async def test_concurrent_acquire_only_one_wins():
    """SETNX guarantees exactly one acquirer wins."""
    client_a, client_b = _make_shared_pair()
    lock_a = DistributedLock("wallet_service", client=client_a)
    lock_b = DistributedLock("wallet_service", client=client_b)

    token_a = await lock_a.acquire("evt-shared", ttl_seconds=30)
    token_b = await lock_b.acquire("evt-shared", ttl_seconds=30)

    assert token_a is not None
    assert token_b is None  # B contended


async def test_release_succeeds_with_matching_token():
    lock = DistributedLock("wallet_service", client=_make_fake())
    token = await lock.acquire("evt-2", ttl_seconds=30)
    assert token is not None
    released = await lock.release("evt-2", token)
    assert released is True


async def test_release_rejects_wrong_token():
    """Security: lost-token release MUST NOT free another holder's lock."""
    client_a, client_b = _make_shared_pair()
    lock_a = DistributedLock("wallet_service", client=client_a)
    lock_b = DistributedLock("wallet_service", client=client_b)

    token_a = await lock_a.acquire("evt-3", ttl_seconds=30)
    assert token_a is not None
    # B never acquired; releasing with a fabricated token must fail.
    released = await lock_b.release("evt-3", token="not-the-real-token")
    assert released is False
    # A's lock is still held — a second acquire from B must still contend.
    token_b = await lock_b.acquire("evt-3", ttl_seconds=30)
    assert token_b is None


async def test_release_after_expiry_returns_false():
    """If the lock TTL'd out, release returns False (not an error)."""
    fake = _make_fake()
    lock = DistributedLock("wallet_service", client=fake)
    token = await lock.acquire("evt-4", ttl_seconds=30)
    assert token is not None
    # Drop the key to simulate TTL expiry.
    await fake.delete("lock:wallet_service:evt-4")
    released = await lock.release("evt-4", token)
    assert released is False


async def test_release_with_empty_token_raises():
    lock = DistributedLock("wallet_service", client=_make_fake())
    with pytest.raises(ValueError):
        await lock.release("evt-5", token="")


async def test_acquire_zero_ttl_rejected():
    lock = DistributedLock("wallet_service", client=_make_fake())
    with pytest.raises(ValueError):
        await lock.acquire("evt-6", ttl_seconds=0)


# ----------------------------------------------------------------------
# TTL expiry
# ----------------------------------------------------------------------


async def test_lock_ttl_set_via_setnx_ex():
    """The TTL argument is honoured via SET ... NX EX."""
    fake = _make_fake()
    lock = DistributedLock("wallet_service", client=fake)
    await lock.acquire("evt-ttl", ttl_seconds=42)
    ttl = await fake.ttl("lock:wallet_service:evt-ttl")
    assert 0 < ttl <= 42


async def test_lock_auto_releases_after_ttl():
    """After TTL fakeredis would tick the key out — simulate by deleting."""
    fake = _make_fake()
    lock_a = DistributedLock("wallet_service", client=fake)
    fake_b = fakeredis.aioredis.FakeRedis(
        server=fake.connection_pool.get_connection.__self__.server if False else None,
        decode_responses=False,
    )  # noqa: E501
    # Simpler: shared server pair.
    a, b = _make_shared_pair()
    lock_a = DistributedLock("wallet_service", client=a)
    lock_b = DistributedLock("wallet_service", client=b)

    token = await lock_a.acquire("evt-7", ttl_seconds=30)
    assert token is not None
    # While held, B contends.
    assert await lock_b.acquire("evt-7", ttl_seconds=30) is None
    # Simulate TTL expiry by deleting the underlying key.
    await a.delete("lock:wallet_service:evt-7")
    # Now B can acquire.
    token_b = await lock_b.acquire("evt-7", ttl_seconds=30)
    assert token_b is not None


# ----------------------------------------------------------------------
# Extend
# ----------------------------------------------------------------------


async def test_extend_succeeds_with_matching_token():
    fake = _make_fake()
    lock = DistributedLock("wallet_service", client=fake)
    token = await lock.acquire("evt-ext", ttl_seconds=10)
    assert token is not None
    ok = await lock.extend("evt-ext", token, ttl_seconds=120)
    assert ok is True
    # TTL is now ~120s.
    ttl = await fake.ttl("lock:wallet_service:evt-ext")
    assert ttl > 60


async def test_extend_rejects_wrong_token():
    lock = DistributedLock("wallet_service", client=_make_fake())
    token = await lock.acquire("evt-ext2", ttl_seconds=10)
    assert token is not None
    ok = await lock.extend("evt-ext2", token="bogus", ttl_seconds=120)
    assert ok is False


# ----------------------------------------------------------------------
# Namespace isolation
# ----------------------------------------------------------------------


async def test_namespace_keeps_locks_isolated():
    server = fakeredis.aioredis.FakeServer()
    a = fakeredis.aioredis.FakeRedis(server=server, decode_responses=False)
    b = fakeredis.aioredis.FakeRedis(server=server, decode_responses=False)
    wallet = DistributedLock("wallet_service", client=a)
    billing = DistributedLock("billing_service", client=b)

    # Same logical key, different namespaces => both can hold.
    t1 = await wallet.acquire("evt-X", ttl_seconds=30)
    t2 = await billing.acquire("evt-X", ttl_seconds=30)
    assert t1 is not None
    assert t2 is not None


# ----------------------------------------------------------------------
# guard() — idempotent retry contract
# ----------------------------------------------------------------------


async def test_guard_first_caller_does_work_and_caches():
    server = fakeredis.aioredis.FakeServer()
    lock_client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=False)
    cache_client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=False)
    lock = DistributedLock("wallet_service", client=lock_client)
    cache = RedisCache("wallet_results", client=cache_client, default_ttl=60)

    calls = {"n": 0}

    async def do_work():
        calls["n"] += 1
        return {"deducted": 100}

    async with lock.guard("evt-G", ttl_seconds=30, result_cache=cache) as outcome:
        assert outcome.is_cached is False
        assert outcome.cached_result is None
        result = await do_work()
        outcome.set_result(result)

    assert calls["n"] == 1
    # Result must be visible in cache after guard exits.
    cached = await cache.get("evt-G")
    assert cached == {"deducted": 100}


async def test_guard_concurrent_replays_see_cached_result():
    """The headline acceptance criterion from issue #348:
    10 concurrent identical events => exactly 1 processed, 9 see cached
    (or contended-then-cached after a brief wait).
    """
    server = fakeredis.aioredis.FakeServer()

    def client():
        return fakeredis.aioredis.FakeRedis(server=server, decode_responses=False)

    cache = RedisCache("wallet_results", client=client(), default_ttl=60)

    work_count = {"n": 0}
    work_started = asyncio.Event()
    release_work = asyncio.Event()

    async def attempt(event_id: str, idx: int):
        # Each replica owns its own lock + cache handle (sharing server).
        lock = DistributedLock("wallet_service", client=client())
        # The first replica's loaders block on release_work so all 10 are
        # in flight concurrently.
        async with lock.guard(
            event_id,
            ttl_seconds=30,
            result_cache=cache,
            wait_seconds=2.0,
            wait_poll_interval=0.01,
        ) as outcome:
            if outcome.is_cached:
                return ("cached", outcome.cached_result)
            work_count["n"] += 1
            if idx == 0:
                work_started.set()
                await release_work.wait()
            result = {"event": event_id, "ran": True}
            outcome.set_result(result)
            return ("processed", result)

    async def driver():
        # Kick off worker 0 first so the lock is held when others arrive.
        worker0 = asyncio.create_task(attempt("evt-CONCURRENT", 0))
        await work_started.wait()
        # Now fire 9 more concurrent attempts.
        peers = [
            asyncio.create_task(attempt("evt-CONCURRENT", i)) for i in range(1, 10)
        ]
        # Let worker 0 finish.
        release_work.set()
        results = await asyncio.gather(worker0, *peers)
        return results

    outcomes = await driver()
    statuses = [s for s, _ in outcomes]
    assert work_count["n"] == 1
    assert statuses.count("processed") == 1
    assert statuses.count("cached") == 9


async def test_guard_short_circuits_when_cache_already_populated():
    """If the cache already has the entry, we don't even touch the lock."""
    cache_client = _make_fake()
    lock_client = _make_fake()
    cache = RedisCache("wallet_results", client=cache_client, default_ttl=60)
    await cache.set("evt-CACHED", {"already": "done"})

    lock = DistributedLock("wallet_service", client=lock_client)
    work_calls = {"n": 0}

    async with lock.guard(
        "evt-CACHED",
        ttl_seconds=30,
        result_cache=cache,
    ) as outcome:
        assert outcome.is_cached is True
        assert outcome.cached_result == {"already": "done"}
        # Caller shouldn't reach this branch in practice — assert it
        # doesn't run by skipping work_calls increment.
        if not outcome.is_cached:  # pragma: no cover
            work_calls["n"] += 1

    # Lock key must not exist — short-circuit avoided the acquire.
    assert await lock_client.get("lock:wallet_service:evt-CACHED") is None


async def test_guard_raises_lock_contended_when_no_wait_and_no_cache():
    """When ``wait_seconds=0`` and the cache is empty, contention raises."""
    a, b = _make_shared_pair()
    lock_a = DistributedLock("wallet_service", client=a)
    lock_b = DistributedLock("wallet_service", client=b)

    # A acquires manually so we can drive a second guard from B.
    token = await lock_a.acquire("evt-CONT", ttl_seconds=30)
    assert token is not None

    with pytest.raises(LockContended):
        async with lock_b.guard(
            "evt-CONT",
            ttl_seconds=30,
            wait_seconds=0.0,
        ) as _:
            pass


async def test_guard_returns_outcome_when_on_contended_return():
    a, b = _make_shared_pair()
    lock_a = DistributedLock("wallet_service", client=a)
    lock_b = DistributedLock("wallet_service", client=b)

    token = await lock_a.acquire("evt-CONT2", ttl_seconds=30)
    assert token is not None

    async with lock_b.guard(
        "evt-CONT2",
        ttl_seconds=30,
        wait_seconds=0.0,
        on_contended="return",
    ) as outcome:
        # Caller can decide what to do with an empty outcome.
        assert outcome.token == ""
        assert outcome.cached_result is None
        assert outcome.is_cached is False


# ----------------------------------------------------------------------
# Fail-closed on Redis outage
# ----------------------------------------------------------------------


class _FlakyClient:
    """Async redis double that raises on all operations."""

    async def set(self, *_, **__):
        raise ConnectionError("redis is down")

    async def eval(self, *_, **__):
        raise ConnectionError("redis is down")

    async def get(self, *_):
        raise ConnectionError("redis is down")

    async def delete(self, *_):
        raise ConnectionError("redis is down")

    async def ping(self):
        raise ConnectionError("redis is down")


async def test_acquire_raises_on_redis_outage():
    """Fail closed: never silently allow unsynchronised processing."""
    lock = DistributedLock("wallet_service", client=_FlakyClient())
    with pytest.raises(DistributedLockError):
        await lock.acquire("evt-FAIL", ttl_seconds=30)


async def test_release_raises_on_redis_outage():
    lock = DistributedLock("wallet_service", client=_FlakyClient())
    with pytest.raises(DistributedLockError):
        await lock.release("evt-FAIL", token="x" * 32)


async def test_acquire_short_circuits_after_latch_trips():
    """Once the latch trips, subsequent acquires fail closed without a
    Redis round-trip until the recovery cooldown elapses."""
    flaky = _FlakyClient()
    lock = DistributedLock(
        "wallet_service",
        client=flaky,
        recovery_cooldown_seconds=60.0,
    )
    with pytest.raises(DistributedLockError):
        await lock.acquire("evt-FAIL", ttl_seconds=30)
    assert lock.healthy is False
    # Second call must also fail-closed (no silent "no lock" path).
    with pytest.raises(DistributedLockError):
        await lock.acquire("evt-FAIL2", ttl_seconds=30)


async def test_build_without_url_returns_failing_lock(monkeypatch):
    for var in ("WALLET_CACHE_REDIS_URL", "CACHE_REDIS_URL", "REDIS_URL"):
        monkeypatch.delenv(var, raising=False)

    lock = build_distributed_lock("wallet_service", service_name="wallet_service")
    assert lock.available is False
    # Operations on an unconfigured lock must fail closed.
    with pytest.raises(DistributedLockError):
        await lock.acquire("evt-NOREDIS", ttl_seconds=30)


# ----------------------------------------------------------------------
# Half-open recovery
# ----------------------------------------------------------------------


class _RecoveringClient:
    """Async redis double that fails N times then succeeds."""

    def __init__(self, fail_count: int = 1):
        self._remaining = fail_count
        self.set_calls = 0
        self.ping_calls = 0
        self.eval_calls = 0
        self._store: dict = {}

    async def set(self, key, value, *, nx=False, ex=None, **__):
        self.set_calls += 1
        if self._remaining > 0:
            self._remaining -= 1
            raise ConnectionError("blip")
        if nx and key in self._store:
            return False
        self._store[key] = value
        return True

    async def eval(self, script, numkeys, *args):
        self.eval_calls += 1
        if self._remaining > 0:
            self._remaining -= 1
            raise ConnectionError("blip")
        # _RELEASE_SCRIPT semantics — return 1 if key matches arg.
        key = args[0]
        token = args[1]
        if self._store.get(key) == token:
            del self._store[key]
            return 1
        return 0

    async def ping(self):
        self.ping_calls += 1
        if self._remaining > 0:
            self._remaining -= 1
            raise ConnectionError("blip")
        return True


async def test_latch_recovers_after_cooldown():
    flaky = _RecoveringClient(fail_count=1)
    lock = DistributedLock(
        "wallet_service",
        client=flaky,
        recovery_cooldown_seconds=0.0,
    )

    # First acquire trips the latch.
    with pytest.raises(DistributedLockError):
        await lock.acquire("evt-REC", ttl_seconds=30)
    assert lock.healthy is False

    # Cooldown is 0s — the next call probes (PING succeeds because
    # _remaining was already decremented to 0) and then runs.
    token = await lock.acquire("evt-REC2", ttl_seconds=30)
    assert token is not None
    assert lock.healthy is True


async def test_latch_does_not_recover_before_cooldown():
    flaky = _RecoveringClient(fail_count=1)
    lock = DistributedLock(
        "wallet_service",
        client=flaky,
        recovery_cooldown_seconds=60.0,
    )
    # Trip the latch.
    with pytest.raises(DistributedLockError):
        await lock.acquire("evt-REC3", ttl_seconds=30)
    pings_before = flaky.ping_calls
    # Subsequent calls fail closed without re-probing Redis.
    for _ in range(3):
        with pytest.raises(DistributedLockError):
            await lock.acquire("evt-REC3", ttl_seconds=30)
    assert flaky.ping_calls == pings_before


async def test_ping_clears_unhealthy_state_when_redis_recovers():
    flaky = _RecoveringClient(fail_count=1)
    lock = DistributedLock(
        "wallet_service",
        client=flaky,
        recovery_cooldown_seconds=60.0,
    )
    # Trip the latch.
    with pytest.raises(DistributedLockError):
        await lock.acquire("evt-REC4", ttl_seconds=30)
    # Out-of-band PING (e.g. health check) brings us back.
    assert await lock.ping() is True
    assert lock.healthy is True


# ----------------------------------------------------------------------
# Builder
# ----------------------------------------------------------------------


def test_build_with_explicit_client():
    lock = build_distributed_lock(
        "wallet_service",
        service_name="wallet_service",
        client=_make_fake(),
        default_ttl_seconds=120,
    )
    assert lock.available is True
    assert lock.namespace == "wallet_service"
    assert lock.default_ttl_seconds == 120


def test_namespace_required():
    with pytest.raises(ValueError):
        DistributedLock("", client=_make_fake())


# ----------------------------------------------------------------------
# Issue #348 follow-up to PR #357 — half-open recovery for delete_pattern
# ----------------------------------------------------------------------


async def test_redis_cache_delete_pattern_attempts_recovery_after_latch():
    """delete_pattern shouldn't fail-closed forever after a single blip
    if Redis comes back. This is the PR #357 review follow-up."""
    from core.redis_cache import CacheInvalidationError, RedisCache

    class _RecoveringScanClient:
        def __init__(self):
            self._scan_fail_remaining = 1
            self.scan_calls = 0
            self.delete_calls = 0
            self.ping_calls = 0
            self._store = {}

        async def get(self, *_):
            return None

        async def set(self, key, value, ex=None):
            self._store[key] = value
            return True

        async def delete(self, *keys):
            self.delete_calls += 1
            for k in keys:
                self._store.pop(k, None)
            return len(keys)

        def scan_iter(self, *, match=None):
            self.scan_calls += 1
            should_fail = self._scan_fail_remaining > 0
            if should_fail:
                self._scan_fail_remaining -= 1

            async def _gen():
                if should_fail:
                    raise ConnectionError("blip")
                # Yield matching keys from the store.
                for k in list(self._store.keys()):
                    yield k

            return _gen()

        async def ping(self):
            self.ping_calls += 1
            return True

    flaky = _RecoveringScanClient()
    cache = RedisCache(
        "perm",
        client=flaky,
        recovery_cooldown_seconds=0.0,
    )
    # Seed two matching keys.
    await cache.set("u1:a", {"v": 1})
    await cache.set("u1:b", {"v": 2})

    # First call trips the latch.
    with pytest.raises(CacheInvalidationError):
        await cache.delete_pattern("u1:*")
    assert cache.healthy is False

    # Second call: cooldown=0 -> probe succeeds -> proceeds with SCAN.
    deleted = await cache.delete_pattern("u1:*")
    assert deleted == 2
    assert cache.healthy is True
