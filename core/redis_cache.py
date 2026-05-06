"""
Shared async Redis cache helper.

Issue #347 — migrate per-replica in-memory caches (compliance policies,
membership tiers, authorization permissions) onto a shared Redis store so
HPA scale-out doesn't break cache coherency.

Design notes:

* The helper is intentionally small. Services own their own (de)serialisation
  via ``loads``/``dumps`` callbacks; the cache only knows about ``str``-keyed
  JSON-encodable payloads.

* Redis URL resolution mirrors :mod:`core.rate_limit_backend`:

    1. ``<SERVICE>_CACHE_REDIS_URL``
    2. ``CACHE_REDIS_URL``
    3. ``REDIS_URL``

  This lets staging override the cache target independently from rate-limit
  Redis without forcing every microservice to learn new env vars.

* If Redis is not configured or is unavailable at runtime, the helper
  short-circuits. The first failure trips a latch (mirroring
  ``FallbackRateLimitBackend`` from PR #335) so we don't pay the latency
  of a broken Redis on every read; ``healthy`` reports ``False`` so the
  service health endpoint can report ``degraded`` per
  :mod:`core.health` semantics.

* Metrics are emitted via ``isa_common.metrics`` (already used by
  :mod:`core.metrics`) so they show up in the standard Prometheus scrape.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Awaitable, Callable, Iterable, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "CacheInvalidationError",
    "RedisCache",
    "build_redis_cache",
    "resolve_cache_redis_url",
    "CACHE_HITS",
    "CACHE_MISSES",
    "CACHE_ERRORS",
]


class CacheInvalidationError(RuntimeError):
    """Raised when a cache invalidation operation cannot be confirmed.

    Issue #347 follow-up: ``delete_pattern`` previously swallowed SCAN/DEL
    failures silently, which is dangerous for security-critical
    invalidations (e.g. ``revoke_resource_permission``). The cache layer
    now raises this typed error so callers can fail-closed on revokes
    instead of "succeeding" while stale grants linger across replicas.
    """


# ----------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------

try:
    # Reuse the platform observability helpers; do not duplicate.
    from isa_common.metrics import create_counter

    CACHE_HITS = create_counter(
        "cache_hits_total",
        "Total cache hits served from Redis",
        ["cache"],
    )
    CACHE_MISSES = create_counter(
        "cache_misses_total",
        "Total cache misses (key absent or expired)",
        ["cache"],
    )
    CACHE_ERRORS = create_counter(
        "cache_errors_total",
        "Total cache errors (Redis unavailable / serialisation failures)",
        ["cache", "operation"],
    )
except Exception:  # pragma: no cover - exercised when isa_common is absent
    # Tests / minimal environments may not expose isa_common. Fall back to a
    # no-op shim so the module still imports cleanly.
    class _NoopCounter:
        def labels(self, *_, **__):
            return self

        def inc(self, *_, **__):
            return None

    CACHE_HITS = _NoopCounter()
    CACHE_MISSES = _NoopCounter()
    CACHE_ERRORS = _NoopCounter()


# ----------------------------------------------------------------------
# URL resolution
# ----------------------------------------------------------------------


def _service_env_prefix(service_name: Optional[str]) -> Optional[str]:
    if not service_name:
        return None
    base = service_name.upper().replace("-", "_")
    if base.endswith("_SERVICE"):
        base = base[: -len("_SERVICE")]
    return base or None


def _candidate_env_vars(service_name: Optional[str]) -> Iterable[str]:
    prefix = _service_env_prefix(service_name)
    if prefix:
        yield f"{prefix}_CACHE_REDIS_URL"
    yield "CACHE_REDIS_URL"
    yield "REDIS_URL"


def resolve_cache_redis_url(service_name: Optional[str] = None) -> Optional[str]:
    """Return the first non-empty Redis URL configured for ``service_name``.

    Probed in order:

    1. ``<SERVICE>_CACHE_REDIS_URL`` (e.g. ``COMPLIANCE_CACHE_REDIS_URL``)
    2. ``CACHE_REDIS_URL`` (platform-wide cache override)
    3. ``REDIS_URL`` (generic platform Redis)
    """
    for var in _candidate_env_vars(service_name):
        value = os.getenv(var)
        if value:
            return value
    return None


# ----------------------------------------------------------------------
# RedisCache wrapper
# ----------------------------------------------------------------------


class RedisCache:
    """Thin async wrapper over a redis.asyncio client.

    The cache is namespaced — every key is prefixed with ``namespace:`` so
    multiple services can safely share a single Redis without collision. The
    ``cache`` label on metrics is the namespace, which makes per-cache
    dashboards trivially filterable.

    The helper accepts an injected client (for tests with fakeredis) and an
    optional URL (for production, where the client is built lazily).
    """

    # Default cooldown before the half-open probe is allowed (seconds).
    # Exposed as a class attr so tests can monkeypatch it to 0 if needed.
    DEFAULT_RECOVERY_COOLDOWN_SECONDS: float = 30.0

    def __init__(
        self,
        namespace: str,
        client: Any = None,
        *,
        default_ttl: int = 300,
        url: Optional[str] = None,
        recovery_cooldown_seconds: Optional[float] = None,
    ):
        if not namespace:
            raise ValueError("RedisCache requires a non-empty namespace")
        self.namespace = namespace
        self.default_ttl = default_ttl
        self._client = client
        self._url = url
        # Set to False when the underlying Redis throws; the service health
        # endpoint can then report ``degraded`` per core.health semantics.
        self._available: bool = client is not None or bool(url)
        # Latch that flips on the first failure so callers don't pay the
        # latency of a broken Redis on every miss.
        self._healthy: bool = self._available
        # Half-open circuit-breaker state (issue #347 follow-up): once the
        # latch trips we record ``_unhealthy_since`` and, after the cooldown
        # elapses, allow exactly one probe attempt to flip the latch back
        # to True without paying the per-call latency cost on every read.
        self._recovery_cooldown: float = (
            recovery_cooldown_seconds
            if recovery_cooldown_seconds is not None
            else self.DEFAULT_RECOVERY_COOLDOWN_SECONDS
        )
        self._unhealthy_since: Optional[float] = None
        self._recovery_lock: asyncio.Lock = asyncio.Lock()

    # -- Connection management -----------------------------------------

    async def _ensure_client(self) -> Optional[Any]:
        """Return an async redis client, building one from ``url`` if needed."""
        if self._client is not None:
            return self._client
        if not self._url:
            return None
        try:
            import redis.asyncio as redis_async  # local import — keeps redis optional

            self._client = redis_async.from_url(
                self._url, decode_responses=False
            )
            return self._client
        except Exception as exc:
            logger.warning(
                "redis_cache(%s): failed to construct client from URL: %s",
                self.namespace,
                exc,
            )
            self._available = False
            self._healthy = False
            CACHE_ERRORS.labels(cache=self.namespace, operation="connect").inc()
            return None

    # -- Health / recovery helpers ------------------------------------

    def _mark_unhealthy(self) -> None:
        """Record the latch trip and remember when it happened.

        Called from every operation that observes a Redis exception. The
        timestamp lets :meth:`_should_attempt_recovery` open the circuit
        for exactly one probe after the cooldown elapses.
        """
        now = time.monotonic()
        self._healthy = False
        if self._unhealthy_since is None:
            self._unhealthy_since = now

    def _should_attempt_recovery(self) -> bool:
        """Return True if enough time has passed to allow a single probe."""
        if self._healthy:
            return False
        if self._unhealthy_since is None:
            # Defensive — if the latch is False but we never recorded a
            # trip, treat the next call as a probe so we don't deadlatch.
            return True
        return (
            time.monotonic() - self._unhealthy_since
        ) >= self._recovery_cooldown

    async def _attempt_recovery(self, client: Any) -> bool:
        """Attempt a single PING probe under the recovery lock.

        Returns True if Redis is reachable again. Only one coroutine per
        process probes at a time — the rest see ``_healthy=False`` and
        keep short-circuiting until the probe completes.
        """
        if self._healthy:
            return True
        # ``asyncio.Lock`` ensures only one probe is in-flight; concurrent
        # readers fall back through the miss path below.
        if self._recovery_lock.locked():
            return False
        async with self._recovery_lock:
            # Re-check inside the lock — another coroutine may have just
            # flipped us back to healthy.
            if self._healthy:
                return True
            try:
                pong = await client.ping()
            except Exception as exc:
                # Reset the timer so we wait another full cooldown before
                # re-probing rather than spinning on every miss.
                self._unhealthy_since = time.monotonic()
                logger.debug(
                    "redis_cache(%s): recovery probe failed: %s",
                    self.namespace,
                    exc,
                )
                CACHE_ERRORS.labels(
                    cache=self.namespace, operation="recovery"
                ).inc()
                return False
            if not pong:
                self._unhealthy_since = time.monotonic()
                return False
            self._healthy = True
            self._unhealthy_since = None
            logger.info(
                "redis_cache(%s): recovered after probe",
                self.namespace,
            )
            return True

    @property
    def healthy(self) -> bool:
        """True if the cache is currently considered healthy.

        Health endpoints should treat ``False`` as ``degraded`` (not
        ``unhealthy``) because the caller is expected to fall back to the
        database — the cache outage is a performance regression, not a
        correctness one.
        """
        return self._available and self._healthy

    @property
    def available(self) -> bool:
        """True if a client was supplied or a URL is configured.

        ``available`` reflects configuration; ``healthy`` reflects runtime
        state. A service can have ``available=True`` but ``healthy=False``
        after the first transient Redis failure.
        """
        return self._available

    async def close(self) -> None:
        """Close the underlying client if we own it."""
        if self._client is None:
            return
        try:
            close_fn = getattr(self._client, "aclose", None) or getattr(
                self._client, "close", None
            )
            if close_fn is None:
                return
            result = close_fn()
            if hasattr(result, "__await__"):
                await result
        except Exception as exc:  # pragma: no cover - best effort cleanup
            logger.debug("redis_cache(%s): close failed: %s", self.namespace, exc)

    # -- Key helpers ---------------------------------------------------

    def _full_key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    # -- Read paths ----------------------------------------------------

    async def get(
        self,
        key: str,
        loads: Callable[[bytes], Any] = json.loads,
    ) -> Optional[Any]:
        """Return the cached value, or ``None`` on miss/error.

        ``loads`` defaults to :func:`json.loads`; callers that store
        domain models supply their own deserialiser (e.g. a Pydantic
        ``model_validate_json``).
        """
        client = await self._ensure_client()
        if client is None:
            CACHE_MISSES.labels(cache=self.namespace).inc()
            return None
        # Half-open recovery (issue #347 follow-up): if the latch is
        # tripped, only attempt a probe after the cooldown has elapsed.
        if not self._healthy:
            if not self._should_attempt_recovery():
                CACHE_MISSES.labels(cache=self.namespace).inc()
                return None
            recovered = await self._attempt_recovery(client)
            if not recovered:
                CACHE_MISSES.labels(cache=self.namespace).inc()
                return None
        full_key = self._full_key(key)
        try:
            raw = await client.get(full_key)
        except Exception as exc:
            self._mark_unhealthy()
            logger.warning(
                "redis_cache(%s): GET failed for %r: %s",
                self.namespace,
                full_key,
                exc,
            )
            CACHE_ERRORS.labels(cache=self.namespace, operation="get").inc()
            CACHE_MISSES.labels(cache=self.namespace).inc()
            return None

        if raw is None:
            CACHE_MISSES.labels(cache=self.namespace).inc()
            return None

        try:
            value = loads(raw)
        except Exception as exc:
            logger.warning(
                "redis_cache(%s): deserialise failed for %r: %s",
                self.namespace,
                full_key,
                exc,
            )
            CACHE_ERRORS.labels(cache=self.namespace, operation="deserialise").inc()
            CACHE_MISSES.labels(cache=self.namespace).inc()
            return None

        CACHE_HITS.labels(cache=self.namespace).inc()
        return value

    # -- Write paths ---------------------------------------------------

    async def set(
        self,
        key: str,
        value: Any,
        *,
        ttl: Optional[int] = None,
        dumps: Callable[[Any], Any] = None,
    ) -> bool:
        """Persist ``value`` with an optional TTL (seconds).

        ``dumps`` defaults to :func:`json.dumps` with ``default=str`` to
        handle datetime / Decimal payloads emitted by Pydantic v2.
        """
        client = await self._ensure_client()
        if client is None:
            return False
        if dumps is None:
            dumps = lambda v: json.dumps(v, default=str)  # noqa: E731
        full_key = self._full_key(key)
        try:
            payload = dumps(value)
        except Exception as exc:
            logger.warning(
                "redis_cache(%s): serialise failed for %r: %s",
                self.namespace,
                full_key,
                exc,
            )
            CACHE_ERRORS.labels(cache=self.namespace, operation="serialise").inc()
            return False

        ex = ttl if ttl is not None else self.default_ttl
        try:
            await client.set(full_key, payload, ex=ex)
            # Successful write while the latch was open is itself a recovery
            # signal — flip back to healthy so subsequent reads return.
            if not self._healthy:
                self._healthy = True
                self._unhealthy_since = None
            return True
        except Exception as exc:
            self._mark_unhealthy()
            logger.warning(
                "redis_cache(%s): SET failed for %r: %s",
                self.namespace,
                full_key,
                exc,
            )
            CACHE_ERRORS.labels(cache=self.namespace, operation="set").inc()
            return False

    async def delete(self, key: str) -> bool:
        """Delete a single key. Returns True on success (even if missing)."""
        client = await self._ensure_client()
        if client is None:
            return False
        full_key = self._full_key(key)
        try:
            await client.delete(full_key)
            return True
        except Exception as exc:
            self._mark_unhealthy()
            logger.warning(
                "redis_cache(%s): DEL failed for %r: %s",
                self.namespace,
                full_key,
                exc,
            )
            CACHE_ERRORS.labels(cache=self.namespace, operation="delete").inc()
            return False

    async def delete_pattern(self, pattern: str, *, raise_on_error: bool = True) -> int:
        """Delete every key matching ``pattern`` (within the namespace).

        Uses ``SCAN`` instead of ``KEYS`` to stay non-blocking on large
        keyspaces.

        Issue #347 follow-up: when SCAN/DEL fails or the cache is
        unconfigured, callers MUST be able to distinguish "successfully
        invalidated 0 keys" from "Redis blip, cannot confirm
        invalidation". Security-critical paths
        (e.g. ``revoke_resource_permission``) need the failure signal so
        they can fail-closed on the revoke instead of "succeeding" while
        replicas keep serving the granted state.

        :param pattern: Pattern relative to the namespace (e.g.
            ``user:<id>:*``).
        :param raise_on_error: If True (default) raise
            :class:`CacheInvalidationError` when SCAN or DEL fails. Set
            to False for best-effort cleanups that already tolerate
            stale entries.
        :returns: Number of keys deleted on success.
        :raises CacheInvalidationError: When the cache is unavailable
            and ``raise_on_error`` is True, or when SCAN/DEL throws.
        """
        client = await self._ensure_client()
        if client is None:
            if raise_on_error:
                raise CacheInvalidationError(
                    f"redis_cache({self.namespace}): cache unavailable; "
                    f"cannot invalidate pattern {pattern!r}"
                )
            return 0
        full_pattern = self._full_key(pattern)
        deleted = 0
        try:
            # redis.asyncio supports scan_iter as an async generator.
            async for raw_key in client.scan_iter(match=full_pattern):
                # Per-key DEL failures are part of the same operation —
                # surface them too so the caller doesn't think the
                # invalidation succeeded when half the keys were left
                # behind.
                await client.delete(raw_key)
                deleted += 1
            return deleted
        except Exception as exc:
            self._mark_unhealthy()
            logger.warning(
                "redis_cache(%s): SCAN/DEL failed for pattern %r after %d "
                "deletes: %s",
                self.namespace,
                full_pattern,
                deleted,
                exc,
            )
            CACHE_ERRORS.labels(cache=self.namespace, operation="scan").inc()
            if raise_on_error:
                raise CacheInvalidationError(
                    f"redis_cache({self.namespace}): SCAN/DEL failed for "
                    f"pattern {pattern!r}: {exc}"
                ) from exc
            return deleted

    # -- Health check helper -------------------------------------------

    async def ping(self) -> bool:
        """Return True if Redis is reachable.

        Used by ``core.health`` to drive the per-service ``redis_cache`` probe.
        Failure flips the latch so subsequent reads short-circuit; success
        clears the unhealthy timestamp so half-open recovery is reset.
        """
        client = await self._ensure_client()
        if client is None:
            return False
        try:
            pong = await client.ping()
            if pong:
                self._healthy = True
                self._unhealthy_since = None
                return True
            self._mark_unhealthy()
            return False
        except Exception as exc:
            self._mark_unhealthy()
            logger.debug("redis_cache(%s): ping failed: %s", self.namespace, exc)
            CACHE_ERRORS.labels(cache=self.namespace, operation="ping").inc()
            return False

    # -- get_or_load convenience wrapper -------------------------------

    async def get_or_load(
        self,
        key: str,
        loader: Callable[[], Awaitable[Any]],
        *,
        ttl: Optional[int] = None,
        loads: Callable[[bytes], Any] = json.loads,
        dumps: Callable[[Any], Any] = None,
    ) -> Any:
        """Return the cached value, falling back to ``loader`` on miss.

        Convenience wrapper that encapsulates the read-through pattern.
        On Redis outage the loader still runs (DB fallback path) and the
        result is returned without being cached — see ``set`` for the
        write attempt that's silently dropped on failure.
        """
        cached = await self.get(key, loads=loads)
        if cached is not None:
            return cached
        loaded = await loader()
        if loaded is not None:
            await self.set(key, loaded, ttl=ttl, dumps=dumps)
        return loaded


# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------


def build_redis_cache(
    namespace: str,
    *,
    service_name: Optional[str] = None,
    default_ttl: int = 300,
    client: Any = None,
) -> RedisCache:
    """Build a :class:`RedisCache` for ``service_name`` / ``namespace``.

    Resolution order:

    * If ``client`` is provided (typically a fakeredis instance), use it.
    * Otherwise resolve the Redis URL from the standard env vars; the
      client is built lazily on first read.

    The returned cache is always usable — operations against an
    unconfigured cache return ``None`` and increment the miss/error
    counters so callers don't have to special-case the "no Redis" branch.
    """
    if client is not None:
        return RedisCache(namespace, client=client, default_ttl=default_ttl)

    url = resolve_cache_redis_url(service_name=service_name)
    if not url:
        logger.info(
            "redis_cache(%s): no REDIS_URL configured for %s; cache will no-op",
            namespace,
            service_name or "service",
        )
        # Construct a disabled cache — every read is a miss, every write a no-op.
        cache = RedisCache(namespace, client=None, default_ttl=default_ttl)
        cache._available = False  # type: ignore[attr-defined]
        cache._healthy = False  # type: ignore[attr-defined]
        return cache

    logger.info(
        "redis_cache(%s): backed by Redis (%s) ttl=%ss",
        namespace,
        url,
        default_ttl,
    )
    return RedisCache(namespace, client=None, default_ttl=default_ttl, url=url)
