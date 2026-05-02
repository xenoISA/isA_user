"""
Distributed rate-limit backend factory.

This module is the shared seam between FastAPI services and the
``core.rate_limiter`` middleware. It picks the appropriate backend
based on environment configuration:

* ``InMemoryBackend`` — local dev / unit tests / single-process deployments.
* ``RedisBackend`` (wrapped in :class:`FallbackRateLimitBackend`) — multi-replica
  production / staging deployments where rate-limit state must be shared.

Resolution order for the Redis URL (first match wins):

1. ``<SERVICE>_RATE_LIMIT_REDIS_URL`` (e.g. ``PAYMENT_RATE_LIMIT_REDIS_URL``)
2. ``RATE_LIMIT_REDIS_URL`` (platform-wide override)
3. ``REDIS_URL`` (generic platform Redis)

If no URL resolves, or if Redis client construction fails, the helper logs
a warning and falls back to an in-memory backend so the service still boots.

Refs #208 — replaces in-memory state with a distributed-friendly default
across rate-limited microservices (auth, payment, storage).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Iterable, Optional

from core.rate_limiter import (
    InMemoryBackend,
    RedisBackend,
    SlidingWindowCounter,
)

logger = logging.getLogger(__name__)


__all__ = [
    "FallbackRateLimitBackend",
    "build_rate_limit_backend",
    "build_sliding_window_counter",
    "resolve_redis_url",
]


def _service_env_prefix(service_name: Optional[str]) -> Optional[str]:
    if not service_name:
        return None
    # "auth_service" -> "AUTH"; "payment_service" -> "PAYMENT"; "storage_service" -> "STORAGE"
    base = service_name.upper().replace("-", "_")
    if base.endswith("_SERVICE"):
        base = base[: -len("_SERVICE")]
    return base or None


def _candidate_env_vars(service_name: Optional[str]) -> Iterable[str]:
    prefix = _service_env_prefix(service_name)
    if prefix:
        yield f"{prefix}_RATE_LIMIT_REDIS_URL"
    yield "RATE_LIMIT_REDIS_URL"
    yield "REDIS_URL"


def resolve_redis_url(service_name: Optional[str] = None) -> Optional[str]:
    """Return the first non-empty Redis URL configured for this service."""
    for var in _candidate_env_vars(service_name):
        value = os.getenv(var)
        if value:
            return value
    return None


def build_rate_limit_backend(*, service_name: Optional[str] = None) -> Any:
    """Build the best available rate-limit backend for ``service_name``.

    Returns an :class:`InMemoryBackend` when no Redis URL is configured or
    when Redis client construction fails. Otherwise returns a
    :class:`FallbackRateLimitBackend` wrapping a :class:`RedisBackend` so a
    runtime Redis outage degrades to in-process counting instead of a 500.
    """
    redis_url = resolve_redis_url(service_name)
    if not redis_url:
        return InMemoryBackend()

    try:
        import redis.asyncio as redis_async  # local import — keeps redis optional

        redis_client = redis_async.from_url(redis_url, decode_responses=True)
    except Exception as exc:  # pragma: no cover - exercised via test double
        logger.warning(
            "Failed to initialize Redis rate-limit backend for %s (%s); "
            "using in-memory fallback",
            service_name or "service",
            exc,
        )
        return InMemoryBackend()

    logger.info(
        "Rate-limit backend for %s configured against Redis (%s)",
        service_name or "service",
        redis_url,
    )
    return FallbackRateLimitBackend(RedisBackend(redis_client), InMemoryBackend())


def build_sliding_window_counter(
    *, service_name: Optional[str] = None
) -> SlidingWindowCounter:
    """Convenience wrapper that returns a counter ready to plug into auth flows."""
    return SlidingWindowCounter(build_rate_limit_backend(service_name=service_name))


class FallbackRateLimitBackend:
    """Use the primary backend when healthy, then degrade to a local fallback.

    The first exception raised by the primary backend trips a latch — subsequent
    calls go straight to the fallback so we don't pay the latency of a broken
    Redis on every request. This mirrors the pattern already established by
    ``microservices.auth_service.rate_limit_state._FallbackRateLimitBackend``
    (introduced in PR #335) — kept in core so all services can reuse it.
    """

    def __init__(self, primary: Any, fallback: InMemoryBackend):
        self._primary = primary
        self._fallback = fallback
        self._primary_available = True

    @property
    def primary_available(self) -> bool:
        return self._primary_available

    async def increment(self, key: str, window: float) -> int:
        return await self._call("increment", key, window)

    async def get_ttl(self, key: str) -> float:
        return await self._call("get_ttl", key)

    async def get_count(self, key: str, window: float) -> int:
        return await self._call("get_count", key, window)

    async def _call(self, method_name: str, *args: Any) -> Any:
        if self._primary_available:
            try:
                method = getattr(self._primary, method_name)
                return await method(*args)
            except Exception as exc:
                self._primary_available = False
                logger.warning(
                    "Redis rate-limit backend unavailable; falling back to memory: %s",
                    exc,
                )
        method = getattr(self._fallback, method_name)
        return await method(*args)
