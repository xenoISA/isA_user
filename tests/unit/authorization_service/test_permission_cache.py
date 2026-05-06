"""
L1/L2 Unit Tests — AuthorizationService Redis-backed permission cache.

Issue #347 — verifies cache hit / miss / write-invalidation /
multi-replica visibility / Redis-down fallback for the
``check_resource_access`` hot path.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest

from core.redis_cache import RedisCache
from microservices.authorization_service.authorization_service import (
    AuthorizationService,
)
from microservices.authorization_service.models import (
    AccessLevel,
    ExternalServiceUser,
    GrantPermissionRequest,
    PermissionSource,
    ResourceAccessRequest,
    ResourceType,
    RevokePermissionRequest,
    UserPermissionRecord,
)


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _make_user(user_id: str = "usr-1") -> ExternalServiceUser:
    return ExternalServiceUser(
        user_id=user_id,
        username=f"user-{user_id}",
        email=f"{user_id}@example.com",
        is_active=True,
        subscription_status="pro",
        organization_id=None,
        roles=[],
    )


def _make_admin_permission(user_id: str = "usr-1") -> UserPermissionRecord:
    return UserPermissionRecord(
        user_id=user_id,
        resource_type=ResourceType.MCP_TOOL,
        resource_name="weather_api",
        access_level=AccessLevel.READ_WRITE,
        permission_source=PermissionSource.ADMIN_GRANT,
        granted_by_user_id="admin",
    )


def _build_repo_mock(*, user=None, permission=None) -> MagicMock:
    repo = MagicMock()
    repo.get_user_info = AsyncMock(return_value=user or _make_user())
    repo.get_user_permission = AsyncMock(return_value=permission)
    repo.get_organization_permission = AsyncMock(return_value=None)
    repo.get_resource_permission = AsyncMock(return_value=None)
    repo.is_user_organization_member = AsyncMock(return_value=False)
    repo.get_organization_info = AsyncMock(return_value=None)
    repo.log_permission_action = AsyncMock(return_value=True)
    repo.grant_user_permission = AsyncMock(return_value=True)
    repo.revoke_user_permission = AsyncMock(return_value=True)
    return repo


def _build_service(cache: RedisCache, repo: MagicMock = None) -> AuthorizationService:
    """Construct an AuthorizationService with the given Redis cache and repo."""
    repo = repo or _build_repo_mock(permission=_make_admin_permission())
    return AuthorizationService(
        repository=repo,
        event_bus=None,
        permission_cache=cache,
    )


def _fake_cache(server: fakeredis.aioredis.FakeServer = None) -> RedisCache:
    server = server or fakeredis.aioredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=False)
    return RedisCache("authorization:permission", client=client, default_ttl=600)


def _request(user_id: str = "usr-1") -> ResourceAccessRequest:
    return ResourceAccessRequest(
        user_id=user_id,
        resource_type=ResourceType.MCP_TOOL,
        resource_name="weather_api",
        required_access_level=AccessLevel.READ_ONLY,
    )


# ----------------------------------------------------------------------
# Cache hit / miss
# ----------------------------------------------------------------------


async def test_check_resource_access_cache_miss_then_hit():
    cache = _fake_cache()
    repo = _build_repo_mock(permission=_make_admin_permission())
    svc = _build_service(cache, repo)

    req = _request()

    first = await svc.check_resource_access(req)
    second = await svc.check_resource_access(req)

    assert first.has_access is True
    assert second.has_access is True
    # Repo only consulted once — second call served from Redis.
    assert repo.get_user_info.await_count == 1
    assert repo.get_user_permission.await_count == 1


async def test_cache_key_uniqueness_by_resource():
    cache = _fake_cache()
    repo = _build_repo_mock(permission=_make_admin_permission())
    svc = _build_service(cache, repo)

    # Two different resources -> two distinct cache entries -> two
    # distinct DB lookups.
    req_a = ResourceAccessRequest(
        user_id="usr-1",
        resource_type=ResourceType.MCP_TOOL,
        resource_name="weather_api",
        required_access_level=AccessLevel.READ_ONLY,
    )
    req_b = ResourceAccessRequest(
        user_id="usr-1",
        resource_type=ResourceType.AI_MODEL,
        resource_name="gpt5",
        required_access_level=AccessLevel.READ_ONLY,
    )

    await svc.check_resource_access(req_a)
    await svc.check_resource_access(req_b)

    assert repo.get_user_info.await_count == 2


# ----------------------------------------------------------------------
# Write-invalidation
# ----------------------------------------------------------------------


async def test_grant_invalidates_user_cache():
    cache = _fake_cache()
    repo = _build_repo_mock(permission=_make_admin_permission())
    svc = _build_service(cache, repo)

    # Prime the cache.
    await svc.check_resource_access(_request())
    assert repo.get_user_permission.await_count == 1

    # Grant fires invalidation.
    await svc.grant_resource_permission(
        GrantPermissionRequest(
            user_id="usr-1",
            resource_type=ResourceType.MCP_TOOL,
            resource_name="weather_api",
            access_level=AccessLevel.READ_WRITE,
            permission_source=PermissionSource.ADMIN_GRANT,
            granted_by_user_id="admin",
        )
    )

    # Next check should miss and re-consult the DB.
    await svc.check_resource_access(_request())
    assert repo.get_user_permission.await_count == 2


async def test_revoke_invalidates_user_cache():
    cache = _fake_cache()
    repo = _build_repo_mock(permission=_make_admin_permission())
    svc = _build_service(cache, repo)

    await svc.check_resource_access(_request())
    initial_count = repo.get_user_permission.await_count
    assert initial_count == 1

    await svc.revoke_resource_permission(
        RevokePermissionRequest(
            user_id="usr-1",
            resource_type=ResourceType.MCP_TOOL,
            resource_name="weather_api",
            revoked_by_user_id="admin",
        )
    )
    # revoke_resource_permission itself calls get_user_permission once
    # for its audit log lookup — track that to assert deltas.
    after_revoke = repo.get_user_permission.await_count
    assert after_revoke >= initial_count + 1

    await svc.check_resource_access(_request())
    # The cache must have been invalidated -> at least one more DB call
    # for the post-revoke read.
    assert repo.get_user_permission.await_count >= after_revoke + 1


async def test_invalidate_does_not_purge_other_users():
    cache = _fake_cache()
    repo = _build_repo_mock(permission=_make_admin_permission(user_id="usr-1"))
    repo.get_user_info = AsyncMock(side_effect=lambda uid: _make_user(uid))
    repo.get_user_permission = AsyncMock(
        side_effect=lambda uid, *_: _make_admin_permission(user_id=uid)
    )
    svc = _build_service(cache, repo)

    await svc.check_resource_access(_request("usr-1"))
    await svc.check_resource_access(_request("usr-2"))
    assert repo.get_user_permission.await_count == 2

    # Invalidate only usr-1.
    await svc.invalidate_permission_cache(user_id="usr-1")

    # usr-2 still cached -> no new DB call.
    await svc.check_resource_access(_request("usr-2"))
    assert repo.get_user_permission.await_count == 2

    # usr-1 reloads.
    await svc.check_resource_access(_request("usr-1"))
    assert repo.get_user_permission.await_count == 3


# ----------------------------------------------------------------------
# Multi-replica visibility
# ----------------------------------------------------------------------


async def test_two_services_share_permission_cache():
    server = fakeredis.aioredis.FakeServer()
    cache_a = RedisCache(
        "authorization:permission",
        client=fakeredis.aioredis.FakeRedis(server=server, decode_responses=False),
    )
    cache_b = RedisCache(
        "authorization:permission",
        client=fakeredis.aioredis.FakeRedis(server=server, decode_responses=False),
    )

    repo_a = _build_repo_mock(permission=_make_admin_permission())
    repo_b = _build_repo_mock(permission=_make_admin_permission())

    svc_a = _build_service(cache_a, repo_a)
    svc_b = _build_service(cache_b, repo_b)

    # Replica A primes.
    await svc_a.check_resource_access(_request())
    assert repo_a.get_user_permission.await_count == 1

    # Replica B reads from the shared cache without hitting its DB.
    resp_b = await svc_b.check_resource_access(_request())
    assert resp_b.has_access is True
    assert repo_b.get_user_permission.await_count == 0

    # Replica A revokes -> replica B sees the eviction immediately.
    await svc_a.revoke_resource_permission(
        RevokePermissionRequest(
            user_id="usr-1",
            resource_type=ResourceType.MCP_TOOL,
            resource_name="weather_api",
            revoked_by_user_id="admin",
        )
    )

    await svc_b.check_resource_access(_request())
    # Replica B's DB now consulted.
    assert repo_b.get_user_permission.await_count == 1


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

    def scan_iter(self, *_, **__):
        raise ConnectionError("redis down")


async def test_check_resource_access_falls_back_to_db_when_redis_down():
    cache = RedisCache("authorization:permission", client=_FlakyClient())
    repo = _build_repo_mock(permission=_make_admin_permission())
    svc = _build_service(cache, repo)

    resp = await svc.check_resource_access(_request())
    assert resp.has_access is True
    # Both calls hit the DB — caching is best-effort, correctness is preserved.
    resp2 = await svc.check_resource_access(_request())
    assert resp2.has_access is True
    assert repo.get_user_permission.await_count == 2


# ----------------------------------------------------------------------
# Cache key fenceposts
# ----------------------------------------------------------------------


async def test_cache_key_returns_none_for_blank_request():
    """Defensive — never cache when essential identifiers are missing."""
    cache = _fake_cache()
    svc = _build_service(cache)

    req = ResourceAccessRequest(
        user_id="",
        resource_type=ResourceType.MCP_TOOL,
        resource_name="x",
        required_access_level=AccessLevel.READ_ONLY,
    )
    assert svc._permission_cache_key(req) is None


# ----------------------------------------------------------------------
# Issue #347 follow-up — cache key captures every decision-affecting
# field of ResourceAccessRequest (PR #357 review item #1).
# ----------------------------------------------------------------------


async def test_cache_key_differs_when_subscription_tier_in_context_differs():
    """Two requests differing only in their context.subscription_tier
    MUST produce different cache keys — otherwise an upgrade from FREE
    to PRO won't be observed until the cache TTL expires.
    """
    cache = _fake_cache()
    svc = _build_service(cache)

    req_free = ResourceAccessRequest(
        user_id="usr-1",
        resource_type=ResourceType.MCP_TOOL,
        resource_name="weather_api",
        required_access_level=AccessLevel.READ_ONLY,
        context={"subscription_tier": "free"},
    )
    req_pro = ResourceAccessRequest(
        user_id="usr-1",
        resource_type=ResourceType.MCP_TOOL,
        resource_name="weather_api",
        required_access_level=AccessLevel.READ_ONLY,
        context={"subscription_tier": "pro"},
    )

    key_free = svc._permission_cache_key(req_free)
    key_pro = svc._permission_cache_key(req_pro)
    assert key_free is not None and key_pro is not None
    assert key_free != key_pro


async def test_cache_key_differs_when_organization_id_differs():
    """Cross-org membership affects the decision; the key must reflect it."""
    cache = _fake_cache()
    svc = _build_service(cache)

    base_kwargs = dict(
        user_id="usr-1",
        resource_type=ResourceType.MCP_TOOL,
        resource_name="weather_api",
        required_access_level=AccessLevel.READ_ONLY,
    )
    key_a = svc._permission_cache_key(
        ResourceAccessRequest(organization_id="org-a", **base_kwargs)
    )
    key_b = svc._permission_cache_key(
        ResourceAccessRequest(organization_id="org-b", **base_kwargs)
    )
    assert key_a != key_b


async def test_cache_key_stable_across_dict_ordering_in_context():
    """Semantically identical context (same keys/values) must hash equal."""
    cache = _fake_cache()
    svc = _build_service(cache)

    req_a = ResourceAccessRequest(
        user_id="usr-1",
        resource_type=ResourceType.MCP_TOOL,
        resource_name="weather_api",
        required_access_level=AccessLevel.READ_ONLY,
        context={"a": 1, "b": 2, "c": 3},
    )
    req_b = ResourceAccessRequest(
        user_id="usr-1",
        resource_type=ResourceType.MCP_TOOL,
        resource_name="weather_api",
        required_access_level=AccessLevel.READ_ONLY,
        # Same keys, different insertion order.
        context={"c": 3, "a": 1, "b": 2},
    )
    assert svc._permission_cache_key(req_a) == svc._permission_cache_key(req_b)


async def test_cache_key_starts_with_user_prefix_for_invalidation():
    """The user-prefixed shape is required by SCAN-based invalidation."""
    cache = _fake_cache()
    svc = _build_service(cache)

    req = ResourceAccessRequest(
        user_id="usr-42",
        resource_type=ResourceType.MCP_TOOL,
        resource_name="weather_api",
        required_access_level=AccessLevel.READ_ONLY,
    )
    key = svc._permission_cache_key(req)
    assert key is not None
    assert key.startswith("user:usr-42:"), (
        f"key {key!r} must start with 'user:<id>:' so "
        "delete_pattern('user:<id>:*') still works"
    )


# ----------------------------------------------------------------------
# Issue #347 follow-up — revoke fails closed when invalidation cannot be
# confirmed (PR #357 review item #3).
# ----------------------------------------------------------------------


class _ScanFailClient:
    """Cache double whose SCAN raises after a successful initial set."""

    def __init__(self):
        self.deleted = []
        self._store: dict = {}

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value, ex=None):
        self._store[key] = value
        return True

    async def delete(self, *keys):
        for k in keys:
            self._store.pop(k, None)
            self.deleted.append(k)
        return len(keys)

    def scan_iter(self, *, match=None):
        async def _gen():
            raise ConnectionError("scan blew up")
            yield  # pragma: no cover

        return _gen()

    async def ping(self):
        return True


async def test_revoke_returns_false_when_cache_invalidation_fails():
    """If SCAN fails during invalidation, revoke must surface failure
    so the caller retries — leaving the DB delete done and the cache
    silently stale would let other replicas serve the granted state for
    up to the full TTL.
    """
    from core.redis_cache import RedisCache

    cache = RedisCache("authorization:permission", client=_ScanFailClient())
    repo = _build_repo_mock(permission=_make_admin_permission())
    svc = _build_service(cache, repo)

    ok = await svc.revoke_resource_permission(
        RevokePermissionRequest(
            user_id="usr-1",
            resource_type=ResourceType.MCP_TOOL,
            resource_name="weather_api",
            revoked_by_user_id="admin",
        )
    )
    assert ok is False
    # The DB revoke still ran (we don't have 2PC); we surface the cache
    # failure so a retry is mandatory.
    assert repo.revoke_user_permission.await_count == 1
    # The audit log records the failure with an explanatory message.
    # log_permission_action receives PermissionAuditLog objects whose
    # ``success=False`` flag indicates the failure was recorded.
    failure_logged = any(
        getattr(call.args[0], "success", True) is False
        for call in repo.log_permission_action.await_args_list
    )
    assert failure_logged


# ----------------------------------------------------------------------
# Issue #347 follow-up — deny TTL is shorter than allow TTL (review #5)
# ----------------------------------------------------------------------


async def test_deny_decisions_use_shorter_ttl_than_allow():
    """A cached deny must expire much faster than a cached allow so an
    operator-corrected grant becomes visible quickly.
    """
    from microservices.authorization_service.authorization_service import (
        PERMISSION_CACHE_TTL_SECONDS,
        PERMISSION_DENY_CACHE_TTL_SECONDS,
    )

    assert PERMISSION_DENY_CACHE_TTL_SECONDS < PERMISSION_CACHE_TTL_SECONDS

    # End-to-end: a denied request leaves an entry whose TTL <= deny TTL.
    cache = _fake_cache()
    repo = _build_repo_mock(permission=None)  # no permission record -> denial
    svc = _build_service(cache, repo)

    deny_req = ResourceAccessRequest(
        user_id="usr-1",
        resource_type=ResourceType.MCP_TOOL,
        # Made-up resource — no resource_permission record either, so
        # the service emits a "no resource permission found" denial.
        resource_name="restricted_tool_xyz",
        required_access_level=AccessLevel.READ_ONLY,
    )
    resp = await svc.check_resource_access(deny_req)
    assert resp.has_access is False

    # Inspect the underlying TTL on the cached entry.
    full_key = cache._full_key(svc._permission_cache_key(deny_req))
    ttl = await cache._client.ttl(full_key)
    assert 0 < ttl <= PERMISSION_DENY_CACHE_TTL_SECONDS, (
        f"deny TTL {ttl} should be at most {PERMISSION_DENY_CACHE_TTL_SECONDS}"
    )
