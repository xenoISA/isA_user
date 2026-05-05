"""
L1/L2 Unit Tests — MembershipRepository Redis-backed tier cache.

Issue #347 — verifies that the tier cache reads through Redis with
1-hour TTL, supports invalidation on writes, and degrades gracefully
when Redis is unavailable.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest

from core.redis_cache import RedisCache
from microservices.membership_service.membership_repository import (
    MembershipRepository,
    _tier_dumps,
    _tier_loads,
)
from microservices.membership_service.models import MembershipTier, Tier


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _make_tier(code: str = "gold", name: str = "Gold") -> Tier:
    return Tier(
        tier_code=MembershipTier(code),
        tier_name=name,
        qualification_threshold=10000,
        point_multiplier=Decimal("1.5"),
    )


def _build_repo(cache: RedisCache, db_row: dict | None = None) -> MembershipRepository:
    """Build a MembershipRepository with the cache injected and DB stubbed.

    The constructor itself opens a postgres pool; we sidestep that by
    instantiating via __new__ and wiring the attributes manually.
    """
    repo = MembershipRepository.__new__(MembershipRepository)
    repo.db = MagicMock()

    # Async context manager that yields the db itself; query_row returns
    # whatever the test wants.
    async def __aenter__(_self):
        return repo.db

    async def __aexit__(_self, *_args):
        return None

    repo.db.__aenter__ = __aenter__
    repo.db.__aexit__ = __aexit__
    repo.db.query_row = AsyncMock(return_value=db_row)

    repo.schema = "membership"
    repo.tiers_table = "tiers"
    repo._tier_cache = cache
    return repo


def _fake_cache(server: fakeredis.aioredis.FakeServer = None) -> RedisCache:
    server = server or fakeredis.aioredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=False)
    return RedisCache("membership:tier", client=client, default_ttl=3600)


# ----------------------------------------------------------------------
# Cache hit / miss
# ----------------------------------------------------------------------


async def test_get_tier_cache_miss_loads_from_db_and_primes_cache():
    cache = _fake_cache()
    db_row = {
        "id": 1,
        "tier_code": "gold",
        "tier_name": "Gold",
        "display_order": 3,
        "qualification_threshold": 20000,
        "point_multiplier": Decimal("1.5"),
        "is_active": True,
        "created_at": None,
    }
    repo = _build_repo(cache, db_row=db_row)

    first = await repo.get_tier("gold")
    second = await repo.get_tier("gold")

    assert first is not None and first.tier_code == MembershipTier.GOLD
    assert second is not None and second.tier_code == MembershipTier.GOLD
    # DB hit only once — second read served by Redis.
    assert repo.db.query_row.await_count == 1


async def test_get_tier_returns_none_when_db_empty():
    cache = _fake_cache()
    repo = _build_repo(cache, db_row=None)
    assert await repo.get_tier("ghost") is None


# ----------------------------------------------------------------------
# Direct cache read (pre-primed)
# ----------------------------------------------------------------------


async def test_get_tier_serves_pre_primed_cache_without_db():
    cache = _fake_cache()
    await cache.set("gold", _make_tier("gold"), dumps=_tier_dumps)

    repo = _build_repo(cache, db_row=None)
    tier = await repo.get_tier("gold")
    assert tier is not None
    assert tier.tier_code == MembershipTier.GOLD
    # DB never touched.
    assert repo.db.query_row.await_count == 0


# ----------------------------------------------------------------------
# Invalidation
# ----------------------------------------------------------------------


async def test_invalidate_tier_cache_drops_specific_code():
    cache = _fake_cache()
    await cache.set("gold", _make_tier("gold"), dumps=_tier_dumps)
    await cache.set("silver", _make_tier("silver"), dumps=_tier_dumps)

    repo = _build_repo(cache, db_row=None)
    await repo.invalidate_tier_cache(tier_code="gold")

    assert await cache.get("gold", loads=_tier_loads) is None
    # Other codes untouched (no FLUSHDB).
    silver = await cache.get("silver", loads=_tier_loads)
    assert silver is not None and silver.tier_code == MembershipTier.SILVER


async def test_invalidate_tier_cache_with_no_args_purges_namespace():
    cache = _fake_cache()
    await cache.set("gold", _make_tier("gold"), dumps=_tier_dumps)
    await cache.set("silver", _make_tier("silver"), dumps=_tier_dumps)

    repo = _build_repo(cache, db_row=None)
    await repo.invalidate_tier_cache()

    assert await cache.get("gold", loads=_tier_loads) is None
    assert await cache.get("silver", loads=_tier_loads) is None


# ----------------------------------------------------------------------
# Multi-replica visibility
# ----------------------------------------------------------------------


async def test_two_repositories_share_tier_cache():
    server = fakeredis.aioredis.FakeServer()
    cache_a = RedisCache(
        "membership:tier",
        client=fakeredis.aioredis.FakeRedis(server=server, decode_responses=False),
    )
    cache_b = RedisCache(
        "membership:tier",
        client=fakeredis.aioredis.FakeRedis(server=server, decode_responses=False),
    )

    db_row = {
        "id": 1,
        "tier_code": "platinum",
        "tier_name": "Platinum",
        "display_order": 4,
        "qualification_threshold": 50000,
        "point_multiplier": Decimal("2.0"),
        "is_active": True,
        "created_at": None,
    }
    repo_a = _build_repo(cache_a, db_row=db_row)
    repo_b = _build_repo(cache_b, db_row=None)  # B has no DB row available.

    # Replica A primes the shared Redis.
    tier_a = await repo_a.get_tier("platinum")
    assert tier_a is not None

    # Replica B reads through the shared cache without touching its DB.
    tier_b = await repo_b.get_tier("platinum")
    assert tier_b is not None and tier_b.tier_code == MembershipTier.PLATINUM
    assert repo_b.db.query_row.await_count == 0

    # Replica A invalidates -> replica B falls back to its DB (which
    # returns None). Coherency preserved.
    await repo_a.invalidate_tier_cache(tier_code="platinum")
    tier_b_after = await repo_b.get_tier("platinum")
    assert tier_b_after is None


# ----------------------------------------------------------------------
# Redis-down DB fallback path
# ----------------------------------------------------------------------


class _FlakyClient:
    async def get(self, key):
        raise ConnectionError("redis down")

    async def set(self, *_, **__):
        raise ConnectionError("redis down")

    async def delete(self, *_):
        raise ConnectionError("redis down")


async def test_get_tier_falls_back_to_db_when_redis_errors():
    cache = RedisCache("membership:tier", client=_FlakyClient())
    db_row = {
        "id": 1,
        "tier_code": "diamond",
        "tier_name": "Diamond",
        "display_order": 5,
        "qualification_threshold": 100000,
        "point_multiplier": Decimal("3.0"),
        "is_active": True,
        "created_at": None,
    }
    repo = _build_repo(cache, db_row=db_row)

    tier = await repo.get_tier("diamond")
    assert tier is not None and tier.tier_code == MembershipTier.DIAMOND
    # The DB call still happens — service stays functional.
    assert repo.db.query_row.await_count == 1
