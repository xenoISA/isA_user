"""Helpers for resolving and enforcing API-key rate limits."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from typing import Any, Dict, Mapping, Optional, Tuple

from core.rate_limiter import (
    InMemoryBackend,
    RateLimitConfig,
    RedisBackend,
    SlidingWindowCounter,
)

logger = logging.getLogger(__name__)

RATE_LIMIT_FIELDS = (
    "requests_per_second",
    "requests_per_minute",
    "requests_per_day",
    "tokens_per_day",
)

REQUEST_RATE_WINDOWS = {
    "requests_per_second": 1,
    "requests_per_minute": 60,
    "requests_per_day": 86_400,
}


def merge_rate_limits(
    org_limits: Optional[Mapping[str, Any]],
    key_limits: Optional[Mapping[str, Any]],
) -> Tuple[Dict[str, Optional[int]], Dict[str, str]]:
    """Merge org defaults with per-key overrides.

    Semantics:
    - If a key-level field is present, it wins even when its value is ``None``.
    - Missing key-level fields fall back to the org default.
    - Missing fields in both scopes resolve to ``None`` and ``unset``.
    """

    org = dict(org_limits or {})
    key = dict(key_limits or {})
    effective: Dict[str, Optional[int]] = {}
    sources: Dict[str, str] = {}

    for field in RATE_LIMIT_FIELDS:
        if field in key:
            effective[field] = key.get(field)
            sources[field] = "api_key"
        elif field in org:
            effective[field] = org.get(field)
            sources[field] = "organization"
        else:
            effective[field] = None
            sources[field] = "unset"

    return effective, sources


@dataclass
class RequestRateLimitExceeded(Exception):
    """Structured error raised when a request-based limit is exceeded."""

    field: str
    limit: int
    retry_after: int
    source: str
    scope_id: str

    def detail(self) -> Dict[str, Any]:
        return {
            "error": "Rate limit exceeded",
            "field": self.field,
            "limit": self.limit,
            "source": self.source,
            "scope_id": self.scope_id,
            "retry_after": self.retry_after,
        }

    def headers(self) -> Dict[str, str]:
        return {
            "Retry-After": str(self.retry_after),
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Field": self.field,
            "X-RateLimit-Source": self.source,
        }


class RequestRateLimiter:
    """Shared request counter keyed by either organization or api-key scope."""

    def __init__(self, counter: Optional[SlidingWindowCounter] = None):
        self.counter = counter or _build_default_counter()

    async def enforce(
        self,
        *,
        organization_id: str,
        key_id: str,
        effective_limits: Mapping[str, Optional[int]],
        field_sources: Mapping[str, str],
    ) -> None:
        """Increment request counters and raise on the first exceeded limit."""

        for field, window_seconds in REQUEST_RATE_WINDOWS.items():
            limit = effective_limits.get(field)
            if limit is None:
                continue

            source = field_sources.get(field, "unset")
            if source == "unset":
                continue

            scope_id = key_id if source == "api_key" else organization_id
            rate_key = self._rate_key(
                field=field,
                source=source,
                organization_id=organization_id,
                key_id=key_id,
            )
            allowed, info = await self.counter.check(
                rate_key,
                RateLimitConfig(requests=int(limit), window_seconds=window_seconds),
            )
            if not allowed:
                raise RequestRateLimitExceeded(
                    field=field,
                    limit=int(limit),
                    retry_after=int(info.get("retry_after", window_seconds)),
                    source=source,
                    scope_id=scope_id,
                )

    async def snapshot_request_usage(
        self,
        *,
        organization_id: str,
        key_id: str,
        effective_limits: Mapping[str, Optional[int]],
        field_sources: Mapping[str, str],
    ) -> Dict[str, Dict[str, Any]]:
        """Read current request counts without incrementing counters."""

        usage: Dict[str, Dict[str, Any]] = {}
        backend = getattr(self.counter, "backend", None)
        get_count = getattr(backend, "get_count", None)

        for field, window_seconds in REQUEST_RATE_WINDOWS.items():
            limit = effective_limits.get(field)
            source = field_sources.get(field, "unset")
            used = 0

            if callable(get_count) and limit is not None and source != "unset":
                rate_key = self._rate_key(
                    field=field,
                    source=source,
                    organization_id=organization_id,
                    key_id=key_id,
                )
                used = int(await get_count(rate_key, window_seconds))

            remaining = None if limit is None else max(int(limit) - used, 0)
            percentage = None
            if limit not in (None, 0):
                percentage = round(min(100.0, (used / int(limit)) * 100), 2)

            usage[field] = {
                "limit": int(limit) if limit is not None else None,
                "used": used,
                "remaining": remaining,
                "source": source,
                "window_seconds": window_seconds,
                "percentage": percentage,
            }

        return usage

    @staticmethod
    def _rate_key(
        *,
        field: str,
        source: str,
        organization_id: str,
        key_id: str,
    ) -> str:
        scope = f"key:{key_id}" if source == "api_key" else f"org:{organization_id}"
        return f"auth_rate_limit:{field}:{scope}"


class _FallbackRateLimitBackend:
    """Use Redis counters when healthy, then fall back to process-local memory."""

    def __init__(self, primary, fallback: InMemoryBackend):
        self._primary = primary
        self._fallback = fallback
        self._primary_available = True

    async def increment(self, key: str, window: float) -> int:
        return await self._call("increment", key, window)

    async def get_ttl(self, key: str) -> float:
        return await self._call("get_ttl", key)

    async def get_count(self, key: str, window: float) -> int:
        return await self._call("get_count", key, window)

    async def _call(self, method_name: str, *args):
        if self._primary_available:
            try:
                method = getattr(self._primary, method_name)
                return await method(*args)
            except Exception as exc:
                self._primary_available = False
                logger.warning(
                    "Redis unavailable for auth rate limits; falling back to memory: %s",
                    exc,
                )

        method = getattr(self._fallback, method_name)
        return await method(*args)


def _build_default_counter() -> SlidingWindowCounter:
    """Build the default auth rate-limit counter.

    Production/staging deployments can share counters across auth_service
    replicas via Redis. Local/dev installs remain dependency-light and use the
    in-memory backend when no Redis URL is configured or Redis is unavailable.
    """

    redis_url = os.getenv("AUTH_RATE_LIMIT_REDIS_URL") or os.getenv("REDIS_URL")
    if not redis_url:
        return SlidingWindowCounter(InMemoryBackend())

    try:
        import redis.asyncio as redis

        redis_client = redis.from_url(redis_url, decode_responses=True)
        backend = _FallbackRateLimitBackend(
            RedisBackend(redis_client),
            InMemoryBackend(),
        )
        logger.info("Auth API-key rate limits configured with Redis backend")
        return SlidingWindowCounter(backend)
    except Exception as exc:
        logger.warning(
            "Failed to initialize Redis auth rate-limit backend; using memory: %s",
            exc,
        )
        return SlidingWindowCounter(InMemoryBackend())
