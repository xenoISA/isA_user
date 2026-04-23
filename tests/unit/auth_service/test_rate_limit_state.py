import pytest

from microservices.auth_service.rate_limit_state import (
    RequestRateLimitExceeded,
    RequestRateLimiter,
    merge_rate_limits,
)


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class TestMergeRateLimits:
    async def test_key_fields_override_org_defaults(self):
        effective, sources = merge_rate_limits(
            {
                "requests_per_second": 1,
                "requests_per_minute": 60,
                "requests_per_day": 1000,
                "tokens_per_day": 10000,
            },
            {"requests_per_minute": 5},
        )

        assert effective == {
            "requests_per_second": 1,
            "requests_per_minute": 5,
            "requests_per_day": 1000,
            "tokens_per_day": 10000,
        }
        assert sources["requests_per_minute"] == "api_key"
        assert sources["requests_per_day"] == "organization"

    async def test_null_key_value_explicitly_clears_org_default(self):
        effective, sources = merge_rate_limits(
            {"requests_per_day": 1000},
            {"requests_per_day": None},
        )

        assert effective["requests_per_day"] is None
        assert sources["requests_per_day"] == "api_key"


class TestRequestRateLimiter:
    async def test_org_scoped_limits_are_shared_across_keys(self):
        limiter = RequestRateLimiter()
        effective = {
            "requests_per_second": None,
            "requests_per_minute": 1,
            "requests_per_day": None,
        }
        sources = {
            "requests_per_second": "unset",
            "requests_per_minute": "organization",
            "requests_per_day": "unset",
        }

        await limiter.enforce(
            organization_id="org-1",
            key_id="key-a",
            effective_limits=effective,
            field_sources=sources,
        )

        with pytest.raises(RequestRateLimitExceeded) as exc_info:
            await limiter.enforce(
                organization_id="org-1",
                key_id="key-b",
                effective_limits=effective,
                field_sources=sources,
            )

        assert exc_info.value.field == "requests_per_minute"
        assert exc_info.value.source == "organization"
        assert exc_info.value.scope_id == "org-1"

    async def test_key_scoped_limits_do_not_collide_with_other_keys(self):
        limiter = RequestRateLimiter()
        effective = {
            "requests_per_second": None,
            "requests_per_minute": 1,
            "requests_per_day": None,
        }
        sources = {
            "requests_per_second": "unset",
            "requests_per_minute": "api_key",
            "requests_per_day": "unset",
        }

        await limiter.enforce(
            organization_id="org-1",
            key_id="key-a",
            effective_limits=effective,
            field_sources=sources,
        )
        await limiter.enforce(
            organization_id="org-1",
            key_id="key-b",
            effective_limits=effective,
            field_sources=sources,
        )

    async def test_snapshot_reads_current_counter_state(self):
        limiter = RequestRateLimiter()
        effective = {
            "requests_per_second": None,
            "requests_per_minute": 3,
            "requests_per_day": 10,
        }
        sources = {
            "requests_per_second": "unset",
            "requests_per_minute": "organization",
            "requests_per_day": "organization",
        }

        await limiter.enforce(
            organization_id="org-1",
            key_id="key-a",
            effective_limits=effective,
            field_sources=sources,
        )

        usage = await limiter.snapshot_request_usage(
            organization_id="org-1",
            key_id="key-a",
            effective_limits=effective,
            field_sources=sources,
        )

        assert usage["requests_per_minute"]["used"] == 1
        assert usage["requests_per_minute"]["remaining"] == 2
        assert usage["requests_per_day"]["used"] == 1

    async def test_default_counter_uses_shared_redis_when_configured(self, monkeypatch):
        import redis.asyncio as redis_asyncio

        fake_redis = _FakeRedis()
        monkeypatch.setenv("AUTH_RATE_LIMIT_REDIS_URL", "redis://shared-rate-limits/1")
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.setattr(
            redis_asyncio,
            "from_url",
            lambda url, decode_responses=True: fake_redis,
        )
        effective = {
            "requests_per_second": None,
            "requests_per_minute": 1,
            "requests_per_day": None,
        }
        sources = {
            "requests_per_second": "unset",
            "requests_per_minute": "organization",
            "requests_per_day": "unset",
        }

        limiter_a = RequestRateLimiter()
        limiter_b = RequestRateLimiter()

        await limiter_a.enforce(
            organization_id="org-redis",
            key_id="key-a",
            effective_limits=effective,
            field_sources=sources,
        )

        with pytest.raises(RequestRateLimitExceeded):
            await limiter_b.enforce(
                organization_id="org-redis",
                key_id="key-b",
                effective_limits=effective,
                field_sources=sources,
            )

    async def test_default_counter_falls_back_to_memory_when_redis_fails(
        self, monkeypatch
    ):
        import redis.asyncio as redis_asyncio

        monkeypatch.setenv("AUTH_RATE_LIMIT_REDIS_URL", "redis://down-rate-limits/1")
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.setattr(
            redis_asyncio,
            "from_url",
            lambda url, decode_responses=True: _FakeRedis(fail=True),
        )
        limiter = RequestRateLimiter()
        effective = {
            "requests_per_second": None,
            "requests_per_minute": 1,
            "requests_per_day": None,
        }
        sources = {
            "requests_per_second": "unset",
            "requests_per_minute": "organization",
            "requests_per_day": "unset",
        }

        await limiter.enforce(
            organization_id="org-fallback",
            key_id="key-a",
            effective_limits=effective,
            field_sources=sources,
        )

        with pytest.raises(RequestRateLimitExceeded):
            await limiter.enforce(
                organization_id="org-fallback",
                key_id="key-b",
                effective_limits=effective,
                field_sources=sources,
            )


class _FakeRedis:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.store = {}

    def pipeline(self):
        return _FakeRedisPipeline(self.store, self.fail)

    async def ttl(self, key):
        return 60 if key in self.store else -2


class _FakeRedisPipeline:
    def __init__(self, store, fail: bool):
        self.store = store
        self.fail = fail
        self.ops = []

    def zremrangebyscore(self, key, min_score, max_score):
        self.ops.append(("zremrangebyscore", key, min_score, max_score))
        return self

    def zadd(self, key, values):
        self.ops.append(("zadd", key, values))
        return self

    def zcard(self, key):
        self.ops.append(("zcard", key))
        return self

    def expire(self, key, ttl):
        self.ops.append(("expire", key, ttl))
        return self

    async def execute(self):
        if self.fail:
            raise ConnectionError("redis unavailable")

        results = []
        for op in self.ops:
            if op[0] == "zremrangebyscore":
                _, key, min_score, max_score = op
                values = self.store.setdefault(key, {})
                for member, score in list(values.items()):
                    if min_score <= score <= max_score:
                        del values[member]
                results.append(0)
            elif op[0] == "zadd":
                _, key, values = op
                self.store.setdefault(key, {}).update(values)
                results.append(len(values))
            elif op[0] == "zcard":
                _, key = op
                results.append(len(self.store.setdefault(key, {})))
            elif op[0] == "expire":
                results.append(True)
        return results
