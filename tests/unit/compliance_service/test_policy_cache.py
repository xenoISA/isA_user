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
    ComplianceCheckType,
    CompliancePolicy,
    ContentType,
)


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _make_policy(
    policy_id: str = "p1", organization_id: str = None
) -> CompliancePolicy:
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
    # Issue #347 follow-up: invalidate_policy_cache(policy_id=...) now
    # also looks the policy up to find its org for active-list eviction;
    # that lookup adds an extra get_policy_by_id call.
    await service.invalidate_policy_cache(policy_id="p1")
    assert repo.get_policy_by_id.await_count == 2  # 1 prime + 1 org lookup
    await service._get_policy_by_id_cached("p1")
    assert repo.get_policy_by_id.await_count == 3  # + the post-invalidate read


async def test_invalidate_does_not_flush_other_keys():
    cache = _fake_cache()
    repo = MagicMock()
    repo.get_policy_by_id = AsyncMock(side_effect=lambda pid: _make_policy(pid))

    service = _build_service(cache, repo)

    await service._get_policy_by_id_cached("p1")
    await service._get_policy_by_id_cached("p2")
    assert repo.get_policy_by_id.await_count == 2

    # Drop only p1. The invalidate path now performs one extra DB lookup
    # to find the org owning p1 so we can also evict the active list —
    # bumping the await count by 1.
    await service.invalidate_policy_cache(policy_id="p1")
    assert repo.get_policy_by_id.await_count == 3

    # p2 still cached -> no more DB calls.
    await service._get_policy_by_id_cached("p2")
    assert repo.get_policy_by_id.await_count == 3

    # p1 reloaded -> one more DB call.
    await service._get_policy_by_id_cached("p1")
    assert repo.get_policy_by_id.await_count == 4


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
    # repo_a serves the org-lookup that invalidate_policy_cache performs.
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


# ----------------------------------------------------------------------
# Issue #347 follow-up — invalidate_policy_cache(policy_id=...) also
# evicts the owning org's active list (PR #357 review item #2).
# ----------------------------------------------------------------------


async def test_invalidate_policy_id_also_drops_owning_org_active_list():
    """When the caller passes only ``policy_id``, the helper must look
    the policy up to find its ``organization_id`` and drop the matching
    ``org:<org>:active`` key. Without this fix, the active list keeps
    serving the just-edited / deleted policy for the full TTL even
    though the per-policy entry has been evicted.
    """
    cache = _fake_cache()
    repo = MagicMock()
    org_policy = _make_policy("p1", organization_id="org-7")
    repo.get_policy_by_id = AsyncMock(return_value=org_policy)
    repo.get_active_policies = AsyncMock(return_value=[org_policy])

    service = _build_service(cache, repo)

    # Prime the per-policy and per-org caches.
    await service._get_policy_by_id_cached("p1")
    await service._get_active_policies_cached("org:org-7:active", "org-7")
    assert repo.get_active_policies.await_count == 1

    # Invalidate by policy_id only — must also evict the active list.
    await service.invalidate_policy_cache(policy_id="p1")

    # Active list lookup now goes back to the DB.
    await service._get_active_policies_cached("org:org-7:active", "org-7")
    assert repo.get_active_policies.await_count == 2


async def test_invalidate_policy_id_does_not_purge_other_orgs():
    """The fix must NOT walk every org's active list — only the owning
    org. Other tenants' active lists stay warm.
    """
    cache = _fake_cache()
    repo = MagicMock()
    p1 = _make_policy("p1", organization_id="org-7")
    p2 = _make_policy("p2", organization_id="org-9")
    repo.get_policy_by_id = AsyncMock(side_effect=lambda pid: p1 if pid == "p1" else p2)
    repo.get_active_policies = AsyncMock(
        side_effect=lambda org: [p1] if org == "org-7" else [p2]
    )

    service = _build_service(cache, repo)

    # Prime both org active lists.
    await service._get_active_policies_cached("org:org-7:active", "org-7")
    await service._get_active_policies_cached("org:org-9:active", "org-9")
    assert repo.get_active_policies.await_count == 2

    # Invalidate p1 (org-7) only.
    await service.invalidate_policy_cache(policy_id="p1")

    # org-9 active list still cached.
    await service._get_active_policies_cached("org:org-9:active", "org-9")
    assert repo.get_active_policies.await_count == 2

    # org-7 active list reloads.
    await service._get_active_policies_cached("org:org-7:active", "org-7")
    assert repo.get_active_policies.await_count == 3


async def test_invalidate_purge_all_orgs_walks_pattern():
    """When the caller explicitly opts in via ``purge_all_orgs=True``,
    the helper SCAN-deletes every ``org:*:active`` entry. That's the
    documented escape hatch for retiring a platform-wide rule.
    """
    cache = _fake_cache()
    repo = MagicMock()
    repo.get_active_policies = AsyncMock(
        side_effect=lambda org: [_make_policy("p1", organization_id=org)]
    )

    service = _build_service(cache, repo)

    await service._get_active_policies_cached("org:org-7:active", "org-7")
    await service._get_active_policies_cached("org:org-9:active", "org-9")
    assert repo.get_active_policies.await_count == 2

    await service.invalidate_policy_cache(purge_all_orgs=True)

    # Both org active lists must reload from the DB.
    await service._get_active_policies_cached("org:org-7:active", "org-7")
    await service._get_active_policies_cached("org:org-9:active", "org-9")
    assert repo.get_active_policies.await_count == 4


async def test_invalidate_with_explicit_org_skips_db_lookup():
    """When the caller passes both ``policy_id`` and ``organization_id``
    we trust them — no extra DB roundtrip.
    """
    cache = _fake_cache()
    repo = MagicMock()
    repo.get_policy_by_id = AsyncMock(
        return_value=_make_policy("p1", organization_id="org-7")
    )

    service = _build_service(cache, repo)

    await service._get_policy_by_id_cached("p1")
    db_calls_before = repo.get_policy_by_id.await_count

    await service.invalidate_policy_cache(policy_id="p1", organization_id="org-7")

    # Only the prime call counts — invalidate_policy_cache did NOT
    # re-look up the policy because the caller supplied the org.
    assert repo.get_policy_by_id.await_count == db_calls_before
