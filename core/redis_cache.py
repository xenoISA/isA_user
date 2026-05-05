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

import json
import logging
import os
from typing import Any, Awaitable, Callable, Iterable, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "RedisCache",
    "build_redis_cache",
    "resolve_cache_redis_url",
    "CACHE_HITS",
    "CACHE_MISSES",
    "CACHE_ERRORS",
]


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

    def __init__(
        self,
        namespace: str,
        client: Any = None,
        *,
        default_ttl: int = 300,
        url: Optional[str] = None,
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
        if client is None or not self._healthy:
            CACHE_MISSES.labels(cache=self.namespace).inc()
            return None
        full_key = self._full_key(key)
        try:
            raw = await client.get(full_key)
        except Exception as exc:
            self._healthy = False
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
            return True
        except Exception as exc:
            self._healthy = False
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
            self._healthy = False
            logger.warning(
                "redis_cache(%s): DEL failed for %r: %s",
                self.namespace,
                full_key,
                exc,
            )
            CACHE_ERRORS.labels(cache=self.namespace, operation="delete").inc()
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete every key matching ``pattern`` (within the namespace).

        Uses ``SCAN`` instead of ``KEYS`` to stay non-blocking on large
        keyspaces.

        Returns the number of keys deleted (0 on any failure).
        """
        client = await self._ensure_client()
        if client is None:
            return 0
        full_pattern = self._full_key(pattern)
        deleted = 0
        try:
            # redis.asyncio supports scan_iter as an async generator.
            async for raw_key in client.scan_iter(match=full_pattern):
                try:
                    await client.delete(raw_key)
                    deleted += 1
                except Exception as exc:
                    logger.debug(
                        "redis_cache(%s): scan-delete failed for %r: %s",
                        self.namespace,
                        raw_key,
                        exc,
                    )
            return deleted
        except Exception as exc:
            self._healthy = False
            logger.warning(
                "redis_cache(%s): SCAN failed for pattern %r: %s",
                self.namespace,
                full_pattern,
                exc,
            )
            CACHE_ERRORS.labels(cache=self.namespace, operation="scan").inc()
            return deleted

    # -- Health check helper -------------------------------------------

    async def ping(self) -> bool:
        """Return True if Redis is reachable.

        Used by ``core.health`` to drive the per-service ``redis_cache`` probe.
        Failure flips the latch so subsequent reads short-circuit.
        """
        client = await self._ensure_client()
        if client is None:
            return False
        try:
            pong = await client.ping()
            self._healthy = bool(pong)
            return self._healthy
        except Exception as exc:
            self._healthy = False
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
