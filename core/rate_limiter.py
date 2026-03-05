"""
Rate Limiting Middleware for FastAPI Services

Sliding window counter with pluggable backends (in-memory, Redis).
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Paths that should never be rate limited
EXCLUDED_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json", "/info")


@dataclass
class RateLimitConfig:
    """Rate limit configuration for an endpoint or default."""

    requests: int = 60
    window_seconds: int = 60


class InMemoryBackend:
    """In-memory sliding window backend. Suitable for single-process deployments."""

    def __init__(self):
        self._windows: Dict[str, list] = {}

    async def increment(self, key: str, window: float) -> int:
        """Add a timestamp and return current request count within the window."""
        now = time.monotonic()
        cutoff = now - window

        if key not in self._windows:
            self._windows[key] = []

        # Prune expired entries
        self._windows[key] = [t for t in self._windows[key] if t > cutoff]

        # Add current request
        self._windows[key].append(now)
        return len(self._windows[key])

    async def get_ttl(self, key: str) -> float:
        """Return seconds until the oldest entry in the window expires."""
        if key not in self._windows or not self._windows[key]:
            return 0
        oldest = self._windows[key][0]
        # TTL is approximate — based on when the oldest entry will expire
        return max(0, time.monotonic() - oldest)

    async def get_count(self, key: str, window: float) -> int:
        """Get current request count without incrementing."""
        now = time.monotonic()
        cutoff = now - window
        if key not in self._windows:
            return 0
        return len([t for t in self._windows[key] if t > cutoff])


class RedisBackend:
    """Redis-backed sliding window. For multi-process / distributed deployments."""

    def __init__(self, redis_client):
        self._redis = redis_client

    async def increment(self, key: str, window: float) -> int:
        """Increment counter using Redis sorted set with timestamp scores."""
        import time as _time

        now = _time.time()
        cutoff = now - window
        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, cutoff)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, int(window) + 1)
        results = await pipe.execute()
        return results[2]

    async def get_ttl(self, key: str) -> float:
        ttl = await self._redis.ttl(key)
        return max(0, ttl)


class SlidingWindowCounter:
    """Sliding window rate limiter using a pluggable backend."""

    def __init__(self, backend=None):
        self.backend = backend or InMemoryBackend()

    async def check(self, key: str, config: RateLimitConfig) -> tuple:
        """
        Check rate limit for a key.

        Returns:
            (allowed: bool, info: dict) where info contains limit, remaining, retry_after
        """
        count = await self.backend.increment(key, config.window_seconds)
        remaining = max(0, config.requests - count)
        allowed = count <= config.requests

        info = {
            "limit": config.requests,
            "remaining": remaining,
            "retry_after": 0,
        }

        if not allowed:
            # Approximate retry-after: time until window slides enough
            info["retry_after"] = config.window_seconds

        return allowed, info


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for HTTP rate limiting.

    Usage:
        app.add_middleware(
            RateLimitMiddleware,
            default_limit=RateLimitConfig(requests=60, window_seconds=60),
            path_limits={
                "/api/v1/auth/login": RateLimitConfig(requests=20, window_seconds=60),
            },
        )
    """

    def __init__(
        self,
        app,
        default_limit: Optional[RateLimitConfig] = None,
        path_limits: Optional[Dict[str, RateLimitConfig]] = None,
        backend=None,
        key_func: Optional[Callable] = None,
    ):
        super().__init__(app)
        self.default_limit = default_limit or RateLimitConfig()
        self.path_limits = path_limits or {}
        self.counter = SlidingWindowCounter(backend or InMemoryBackend())
        self.key_func = key_func or self._default_key

    @staticmethod
    def _default_key(request: Request) -> str:
        """Default key: client IP."""
        if request.client:
            return request.client.host
        return "unknown"

    def _get_config(self, path: str) -> Optional[RateLimitConfig]:
        """Get rate limit config for a path, or None if excluded."""
        # Check exclusions
        for prefix in EXCLUDED_PREFIXES:
            if path.startswith(prefix):
                return None

        # Check path-specific limits (longest prefix match)
        for pattern, config in sorted(
            self.path_limits.items(), key=lambda x: -len(x[0])
        ):
            if path.startswith(pattern):
                return config

        return self.default_limit

    async def dispatch(self, request: Request, call_next) -> Response:
        config = self._get_config(request.url.path)
        if config is None:
            return await call_next(request)

        client_key = self.key_func(request)
        rate_key = f"rl:{client_key}:{request.url.path}"

        allowed, info = await self.counter.check(rate_key, config)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": info["retry_after"],
                },
                headers={
                    "Retry-After": str(info["retry_after"]),
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        return response


__all__ = [
    "InMemoryBackend",
    "RateLimitConfig",
    "RateLimitMiddleware",
    "RedisBackend",
    "SlidingWindowCounter",
]
