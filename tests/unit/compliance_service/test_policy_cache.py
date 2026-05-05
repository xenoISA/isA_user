"""
L1/L2 Unit Tests — ComplianceService Redis-backed policy cache.

Verifies the policy cache contract introduced by #347:

- Hit: a second lookup hits Redis, not the DB
- Miss: first lookup falls back to the DB and primes the cache
- Invalidation: explicit DEL drops the entry without flushing siblings
- Multi-replica visibility: writer in cache A is visible from cache B
- Redis-down fallback: lookup still works when Redis errors out
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest

from core.redis_cache import RedisCache
from microservices.compliance_service.compliance_service import ComplianceService
from microservices.compliance_service.models import (
    ComplianceCheckRequest,
    ComplianceCheckType,
    CompliancePolicy,
    ContentType,
)


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _make_policy(policy_id: str = "p1", organization_id: str = None) -> CompliancePolicy:
    return CompliancePolicy(
        policy_id=policy_id,
        policy_name=f"policy-{policy_id}",
        organization_id=organization_id,
        content_types=[ContentType.TEXT],
        check_types=[ComplianceCheckType.CONTENT_MODERATION],
        rules={"foo": "bar"},
    )


def _build_service(cache: RedisCache, repo_mock: MagicMock = None) -> ComplianceService:
    """Build a ComplianceService with the cache injected and repo mocked.

    The constructor builds a ComplianceRepository internally, but we don't
    let it talk to Postgres — we replace the attribute with a MagicMock
    immediately after construction.
    """
    service = ComplianceService.__new__(ComplianceService)
    service.repository = repo_mock or MagicMock()
    service.event_bus = None
    service.enable_openai_moderation = False
    service.enable_local_checks = False
    service._policy_cache = cache
    service._stats = {"total_checks": 0, "blocked_content": 0, "flagged_content": 0}
    return service


def _fake_cache(server: fakeredis.aioredis.FakeServer = None) -> RedisCache:
    server = server or fakeredis.aioredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=False)
    return RedisCache("compliance:policy", client=client, default_ttl=300)


# ----------------------------------------------------------------------
# get_policy_by_id — cache hit / miss
# ----------------------------------------------------------------------


async def test_policy_by_id_cache_miss_then_hit():
    cache = _fake_cache()
    repo = MagicMock()
    policy = _make_policy("p1")
    repo.get_policy_by_id = AsyncMock(return_value=policy)

    service = _build_service(cache, repo)

    first = await service._get_policy_by_id_cached("p1")
    second = await service._get_policy_by_id_cached("p1")

    assert first is not None and second is not None
    assert first.policy_id == "p1"
    assert second.policy_id == "p1"
    # DB should be hit exactly once — second read served from cache.
    assert repo.get_policy_by_id.await_count == 1


async def test_policy_by_id_returns_none_when_db_returns_none():
    cache = _fake_cache()
    repo = MagicMock()
    repo.get_policy_by_id = AsyncMock(return_value=None)

    service = _build_service(cache, repo)
    assert await service._get_policy_by_id_cached("missing") is None


# ----------------------------------------------------------------------
# get_active_policies — cache hit / miss
# ----------------------------------------------------------------------


async def test_active_policies_cache_miss_then_hit():
    cache = _fake_cache()
    repo = MagicMock()
    policies = [_make_policy("p1", organization_id="org-1")]
    repo.get_active_policies = AsyncMock(return_value=policies)

    service = _build_service(cache, repo)

    first = await service._get_active_policies_cached("org:org-1:active", "org-1")
    second = await service._get_active_policies_cached("org:org-1:active", "org-1")

    assert len(first) == 1 and len(second) == 1
    assert repo.get_active_policies.await_count == 1


# ----------------------------------------------------------------------
# Write-invalidation
# ----------------------------------------------------------------------


async def test_invalidate_drops_specific_policy_id():
    cache = _fake_cache()
    repo = MagicMock()
    repo.get_policy_by_id = AsyncMock(return_value=_make_policy("p1"))

    service = _build_service(cache, repo)

    # Prime cache.
    await service._get_policy_by_id_cached("p1")
    assert repo.get_policy_by_id.await_count == 1

    # Invalidate -> next read goes back to the DB.
    await service.invalidate_policy_cache(policy_id="p1")
    await service._get_policy_by_id_cached("p1")
    assert repo.get_policy_by_id.await_count == 2


async def test_invalidate_does_not_flush_other_keys():
    cache = _fake_cache()
    repo = MagicMock()
    repo.get_policy_by_id = AsyncMock(
        side_effect=lambda pid: _make_policy(pid)
    )

    service = _build_service(cache, repo)

    await service._get_policy_by_id_cached("p1")
    await service._get_policy_by_id_cached("p2")
    assert repo.get_policy_by_id.await_count == 2

    # Drop only p1.
    await service.invalidate_policy_cache(policy_id="p1")

    # p2 still cached.
    await service._get_policy_by_id_cached("p2")
    assert repo.get_policy_by_id.await_count == 2

    # p1 reloaded.
    await service._get_policy_by_id_cached("p1")
    assert repo.get_policy_by_id.await_count == 3


async def test_invalidate_drops_org_active_list():
    cache = _fake_cache()
    repo = MagicMock()
    repo.get_active_policies = AsyncMock(
        return_value=[_make_policy("p1", organization_id="org-1")]
    )
    service = _build_service(cache, repo)

    await service._get_active_policies_cached("org:org-1:active", "org-1")
    assert repo.get_active_policies.await_count == 1

    await service.invalidate_policy_cache(organization_id="org-1")
    await service._get_active_policies_cached("org:org-1:active", "org-1")
    assert repo.get_active_policies.await_count == 2


# ----------------------------------------------------------------------
# Multi-replica visibility
# ----------------------------------------------------------------------


async def test_two_replicas_share_policy_cache():
    server = fakeredis.aioredis.FakeServer()
    cache_a = RedisCache(
        "compliance:policy",
        client=fakeredis.aioredis.FakeRedis(server=server, decode_responses=False),
    )
    cache_b = RedisCache(
        "compliance:policy",
        client=fakeredis.aioredis.FakeRedis(server=server, decode_responses=False),
    )

    repo_a = MagicMock()
    repo_a.get_policy_by_id = AsyncMock(return_value=_make_policy("p1"))
    repo_b = MagicMock()
    repo_b.get_policy_by_id = AsyncMock(return_value=_make_policy("p1"))

    svc_a = _build_service(cache_a, repo_a)
    svc_b = _build_service(cache_b, repo_b)

    # Replica A primes the shared Redis.
    await svc_a._get_policy_by_id_cached("p1")
    assert repo_a.get_policy_by_id.await_count == 1

    # Replica B reads from the shared cache without hitting its own DB.
    p = await svc_b._get_policy_by_id_cached("p1")
    assert p is not None and p.policy_id == "p1"
    assert repo_b.get_policy_by_id.await_count == 0

    # Replica A invalidates -> replica B observes the eviction.
    await svc_a.invalidate_policy_cache(policy_id="p1")
    await svc_b._get_policy_by_id_cached("p1")
    assert repo_b.get_policy_by_id.await_count == 1


# ----------------------------------------------------------------------
# Redis-down fallback path
# ----------------------------------------------------------------------


class _FlakyClient:
    async def get(self, key):
        raise ConnectionError("redis down")

    async def set(self, *_, **__):
        raise ConnectionError("redis down")

    async def delete(self, *_):
        raise ConnectionError("redis down")


async def test_lookup_falls_back_to_db_when_redis_errors():
    cache = RedisCache("compliance:policy", client=_FlakyClient())
    repo = MagicMock()
    repo.get_policy_by_id = AsyncMock(return_value=_make_policy("p1"))

    service = _build_service(cache, repo)
    p = await service._get_policy_by_id_cached("p1")

    assert p is not None and p.policy_id == "p1"
    # The DB call still happens; the cache outage is invisible to callers.
    assert repo.get_policy_by_id.await_count == 1
