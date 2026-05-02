"""Helpers for resolving and enforcing API-key rate limits."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Dict, Mapping, Optional, Tuple

from core.rate_limit_backend import build_sliding_window_counter
from core.rate_limiter import RateLimitConfig, SlidingWindowCounter

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


def _build_default_counter() -> SlidingWindowCounter:
    """Build the default auth rate-limit counter.

    Refs #208: delegates to ``core.rate_limit_backend.build_sliding_window_counter``
    so api-key quotas, HTTP rate limits, and other services share one Redis-vs-
    memory selection policy. Local/dev installs remain dependency-light and use
    the in-memory backend when no Redis URL is configured.
    """

    return build_sliding_window_counter(service_name="auth_service")
