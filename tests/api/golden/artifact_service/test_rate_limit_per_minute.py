"""
Artifact Service — per-minute rate limit golden tests.

Covers the xenoISA/isA_user#464 deferred follow-up of #441: an in-process
sliding-window cap on top of the per-day quota that protects against burst
abuse from a single caller (defense in depth — APISIX still caps at the
edge in real prod). Same pattern as PR isA_user#468's enforce_invite_rate_limit
on project_sharing_service.

Two independent buckets:
  - POST /api/v1/artifacts/{id}/runtime/invoke → 100/min  (ARTIFACT_RUNTIME_RATE_PER_MINUTE)
  - POST /api/v1/artifacts/{id}/mcp/call       →  60/min  (ARTIFACT_MCP_RATE_PER_MINUTE)

Tests rely on the service being started with low caps so 429 paths fire
without making 100+ HTTP calls each. Run with:

  ARTIFACT_RUNTIME_RATE_PER_MINUTE=5 \
  ARTIFACT_MCP_RATE_PER_MINUTE=5 \
  bash deployment/local-dev.sh --restart artifact_service

The tests read the configured cap from the env vars and walk the boundary
with one extra call. If the service was started with prod defaults we'd be
sending 101 calls in the runtime test — still functional, just slow. Keep
the env knobs low in CI.
"""

import os
import uuid

import httpx
import pytest

pytestmark = [pytest.mark.api, pytest.mark.asyncio, pytest.mark.golden]

ARTIFACT_SERVICE_URL = os.getenv("ARTIFACT_SERVICE_URL", "http://localhost:8291")
API_BASE = f"{ARTIFACT_SERVICE_URL}/api/v1"

# Per-minute caps configured for the test process. The service code reads the
# same env vars at request time, so tests and service stay in sync. Defaults
# match the production caps (100/60) but the local-dev / CI flow sets them to
# low single digits for speed.
RUNTIME_RATE_PER_MIN = int(os.getenv("ARTIFACT_RUNTIME_RATE_PER_MINUTE", "100"))
MCP_RATE_PER_MIN = int(os.getenv("ARTIFACT_MCP_RATE_PER_MINUTE", "60"))

# Hold the per-day quota high enough that the burst tests don't trip it first.
# The per-day test below explicitly verifies the two limits are independent —
# that one uses ARTIFACT_DAILY_QUOTA which the runtime tests set up front.
PER_DAY_QUOTA = int(os.getenv("ARTIFACT_DAILY_QUOTA", "3"))


@pytest.fixture
async def http_client():
    async with httpx.AsyncClient(timeout=15.0) as client:
        yield client


@pytest.fixture
def user_id():
    return f"test-441-rl-{uuid.uuid4().hex[:10]}"


@pytest.fixture
def other_user_id():
    return f"test-441-rl-other-{uuid.uuid4().hex[:10]}"


@pytest.fixture
def auth_headers():
    """Unique JWT-shaped Authorization header so this test gets its own bucket.

    The rate limit key uses a SHA1 prefix of the header value, so any unique
    bearer string isolates this run from other tests' counters."""
    token = f"test-jwt-{uuid.uuid4().hex}"
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers():
    token = f"test-jwt-other-{uuid.uuid4().hex}"
    return {"Authorization": f"Bearer {token}"}


async def _create_artifact(
    http_client: httpx.AsyncClient,
    owner: str,
    *,
    title: str = "RL test art",
    storage_scope: str = "none",
) -> dict:
    body = {
        "user_id": owner,
        "artifact": {
            "title": title,
            "content_type": "code",
            "visibility": "private",
            "storage_scope": storage_scope,
            "version": {"content": "print('hi')", "language": "python"},
        },
    }
    resp = await http_client.post(f"{API_BASE}/artifacts", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ==========================================================================
# Runtime/invoke — per-minute cap
# ==========================================================================


class TestRuntimeInvokePerMinute:
    async def test_runtime_invoke_429s_after_cap_calls_per_minute(
        self, http_client, user_id, auth_headers
    ):
        """N+1th /runtime/invoke call inside a minute MUST 429 with per_minute marker."""
        if RUNTIME_RATE_PER_MIN > 50:
            pytest.skip(
                f"ARTIFACT_RUNTIME_RATE_PER_MINUTE={RUNTIME_RATE_PER_MIN} is too high "
                "for the burst test — set it to <=10 in dev/CI."
            )

        art = await _create_artifact(http_client, user_id)
        last_ok_status = None
        # Drain the per-minute bucket exactly to the cap.
        for i in range(RUNTIME_RATE_PER_MIN):
            r = await http_client.post(
                f"{API_BASE}/artifacts/{art['id']}/runtime/invoke",
                json={"user_id": user_id, "prompt": f"burst {i}"},
                headers=auth_headers,
            )
            # If the per-day quota happens to be set <= RUNTIME_RATE_PER_MIN,
            # the per-day 429 may fire first. Both are valid for these
            # bookkeeping calls — we only assert specifics on the burst step.
            last_ok_status = r.status_code
            if r.status_code == 429:
                detail = r.json().get("detail", {})
                # Either limit is OK while draining — we just need to reach
                # the per-minute boundary on the next call. If the per-day cap
                # fires first, skip the per-minute assertion (covered elsewhere).
                if isinstance(detail, dict) and detail.get("limit_type") == "per_day":
                    pytest.skip(
                        "per-day quota fired before per-minute boundary — bump "
                        "ARTIFACT_DAILY_QUOTA above ARTIFACT_RUNTIME_RATE_PER_MINUTE."
                    )
        assert last_ok_status in (200, 429), last_ok_status

        # One more call → MUST 429 with per_minute marker.
        over = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/runtime/invoke",
            json={"user_id": user_id, "prompt": "one too many"},
            headers=auth_headers,
        )
        assert over.status_code == 429, over.text
        detail = over.json().get("detail", {})
        assert isinstance(detail, dict), detail
        assert detail.get("limit_type") == "per_minute", detail

    async def test_per_minute_429_includes_retry_after_header(
        self, http_client, user_id, auth_headers
    ):
        if RUNTIME_RATE_PER_MIN > 50:
            pytest.skip("cap too high for burst test")

        art = await _create_artifact(http_client, user_id)
        # Drain + one over.
        for i in range(RUNTIME_RATE_PER_MIN):
            await http_client.post(
                f"{API_BASE}/artifacts/{art['id']}/runtime/invoke",
                json={"user_id": user_id, "prompt": f"x{i}"},
                headers=auth_headers,
            )
        over = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/runtime/invoke",
            json={"user_id": user_id, "prompt": "over"},
            headers=auth_headers,
        )
        assert over.status_code == 429, over.text
        # Retry-After header set (case-insensitive).
        header_keys = {k.lower() for k in over.headers.keys()}
        assert "retry-after" in header_keys, list(over.headers.keys())
        retry_after = (
            over.headers.get("Retry-After") or over.headers.get("retry-after") or "0"
        )
        assert int(retry_after) > 0

    async def test_different_users_have_separate_buckets(
        self, http_client, user_id, other_user_id, auth_headers, other_auth_headers
    ):
        """Two callers with distinct Authorization headers must NOT share a bucket."""
        if RUNTIME_RATE_PER_MIN > 50:
            pytest.skip("cap too high for burst test")

        art = await _create_artifact(http_client, user_id)
        # User A burns the per-minute bucket.
        for i in range(RUNTIME_RATE_PER_MIN):
            await http_client.post(
                f"{API_BASE}/artifacts/{art['id']}/runtime/invoke",
                json={"user_id": user_id, "prompt": f"a{i}"},
                headers=auth_headers,
            )
        over_a = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/runtime/invoke",
            json={"user_id": user_id, "prompt": "a-over"},
            headers=auth_headers,
        )
        assert over_a.status_code == 429
        # User B's first call must NOT be rate-limited — separate bucket.
        first_b = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/runtime/invoke",
            json={"user_id": other_user_id, "prompt": "b1"},
            headers=other_auth_headers,
        )
        # 200 means it went through; a 429 would only be OK if it carried the
        # per_day marker (different limiter — but other_user_id has 0 calls so
        # that's also impossible). Anything else is a leak across buckets.
        assert (
            first_b.status_code == 200
        ), f"separate auth bucket leaked: {first_b.status_code} / {first_b.text}"


# ==========================================================================
# /mcp/call — per-minute cap (lower default cap than runtime)
# ==========================================================================


class TestMCPCallPerMinute:
    async def test_mcp_call_429s_after_cap_calls_per_minute(
        self, http_client, user_id, auth_headers
    ):
        if MCP_RATE_PER_MIN > 50:
            pytest.skip(
                f"ARTIFACT_MCP_RATE_PER_MINUTE={MCP_RATE_PER_MIN} too high — set <=10 for tests."
            )

        art = await _create_artifact(http_client, user_id)
        # The first MCP call (no grant) returns 200 with requires_approval=True,
        # which still counts against the per-minute bucket — that's the
        # intended behaviour, since it's still an inbound request the service
        # has to do work for.
        for i in range(MCP_RATE_PER_MIN):
            r = await http_client.post(
                f"{API_BASE}/artifacts/{art['id']}/mcp/call",
                json={
                    "user_id": user_id,
                    "tool_name": f"fs.read_{i}",
                    "server_id": "isA_MCP",
                    "args": {},
                },
                headers=auth_headers,
            )
            assert r.status_code == 200, r.text

        over = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/mcp/call",
            json={
                "user_id": user_id,
                "tool_name": "fs.read_over",
                "server_id": "isA_MCP",
                "args": {},
            },
            headers=auth_headers,
        )
        assert over.status_code == 429, over.text
        detail = over.json().get("detail", {})
        assert isinstance(detail, dict)
        assert detail.get("limit_type") == "per_minute"
        # Retry-After header MUST be present.
        header_keys = {k.lower() for k in over.headers.keys()}
        assert "retry-after" in header_keys


# ==========================================================================
# Per-day + per-minute are independent layers
# ==========================================================================


class TestPerDayVsPerMinuteIndependent:
    async def test_per_day_and_per_minute_are_independent(
        self, http_client, user_id, auth_headers
    ):
        """Exceeding the per-day quota MUST 429 with the existing daily marker.
        The per-minute 429 carries a different marker so the BFF can branch
        on detail.limit_type / detail.error to pick UX.
        """
        if RUNTIME_RATE_PER_MIN <= PER_DAY_QUOTA:
            pytest.skip(
                "Need ARTIFACT_RUNTIME_RATE_PER_MINUTE > ARTIFACT_DAILY_QUOTA to hit "
                "per-day boundary before per-minute boundary."
            )

        art = await _create_artifact(http_client, user_id)
        # Drain exactly to the per-day cap.
        for i in range(PER_DAY_QUOTA):
            r = await http_client.post(
                f"{API_BASE}/artifacts/{art['id']}/runtime/invoke",
                json={"user_id": user_id, "prompt": f"day {i}"},
                headers=auth_headers,
            )
            assert r.status_code == 200, r.text

        over = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/runtime/invoke",
            json={"user_id": user_id, "prompt": "over-day"},
            headers=auth_headers,
        )
        assert over.status_code == 429, over.text
        detail = over.json().get("detail", {})
        if isinstance(detail, dict):
            # Existing per-day shape — error stays 'daily_quota_exceeded' so
            # the BFF's existing branch keeps working.
            assert detail.get("error") == "daily_quota_exceeded"
            # New marker added by this PR — frontends pick UX off this field.
            assert detail.get("limit_type") == "per_day"
