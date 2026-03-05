"""
L1 Unit Tests — Rate Limiter

Tests pure sliding window counter logic with no I/O.
Uses the in-memory backend only.
"""

import asyncio
import time

import pytest

from core.rate_limiter import InMemoryBackend, RateLimitConfig, SlidingWindowCounter


class TestSlidingWindowCounter:
    """Test sliding window rate limiting logic"""

    @pytest.fixture
    def backend(self):
        return InMemoryBackend()

    @pytest.fixture
    def counter(self, backend):
        return SlidingWindowCounter(backend)

    @pytest.mark.asyncio
    async def test_allows_under_limit(self, counter):
        config = RateLimitConfig(requests=5, window_seconds=60)
        allowed, info = await counter.check("test-key", config)
        assert allowed is True
        assert info["remaining"] == 4

    @pytest.mark.asyncio
    async def test_blocks_at_limit(self, counter):
        config = RateLimitConfig(requests=3, window_seconds=60)
        for _ in range(3):
            await counter.check("test-key", config)
        allowed, info = await counter.check("test-key", config)
        assert allowed is False
        assert info["remaining"] == 0

    @pytest.mark.asyncio
    async def test_separate_keys(self, counter):
        config = RateLimitConfig(requests=1, window_seconds=60)
        allowed1, _ = await counter.check("key-a", config)
        allowed2, _ = await counter.check("key-b", config)
        assert allowed1 is True
        assert allowed2 is True

    @pytest.mark.asyncio
    async def test_window_expiry(self, counter):
        config = RateLimitConfig(requests=1, window_seconds=0.01)
        await counter.check("test-key", config)
        # Wait for window to expire
        await asyncio.sleep(0.02)
        allowed, info = await counter.check("test-key", config)
        assert allowed is True

    @pytest.mark.asyncio
    async def test_returns_retry_after(self, counter):
        config = RateLimitConfig(requests=1, window_seconds=60)
        await counter.check("test-key", config)
        allowed, info = await counter.check("test-key", config)
        assert allowed is False
        assert info["retry_after"] > 0
        assert info["retry_after"] <= 60

    @pytest.mark.asyncio
    async def test_returns_limit_and_remaining(self, counter):
        config = RateLimitConfig(requests=10, window_seconds=60)
        _, info = await counter.check("test-key", config)
        assert info["limit"] == 10
        assert info["remaining"] == 9


class TestRateLimitConfig:
    """Test rate limit configuration"""

    def test_defaults(self):
        config = RateLimitConfig()
        assert config.requests == 60
        assert config.window_seconds == 60

    def test_custom(self):
        config = RateLimitConfig(requests=10, window_seconds=30)
        assert config.requests == 10
        assert config.window_seconds == 30


class TestInMemoryBackend:
    """Test in-memory storage backend"""

    @pytest.mark.asyncio
    async def test_increment_returns_count(self):
        backend = InMemoryBackend()
        count = await backend.increment("key", window=60)
        assert count == 1

    @pytest.mark.asyncio
    async def test_increment_accumulates(self):
        backend = InMemoryBackend()
        await backend.increment("key", window=60)
        await backend.increment("key", window=60)
        count = await backend.increment("key", window=60)
        assert count == 3

    @pytest.mark.asyncio
    async def test_get_ttl(self):
        backend = InMemoryBackend()
        await backend.increment("key", window=60)
        ttl = await backend.get_ttl("key")
        assert 0 < ttl <= 60

    @pytest.mark.asyncio
    async def test_expired_entries_cleaned(self):
        backend = InMemoryBackend()
        await backend.increment("key", window=0.01)
        await asyncio.sleep(0.02)
        count = await backend.increment("key", window=0.01)
        assert count == 1  # Old entries expired
