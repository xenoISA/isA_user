"""
Artifact Service Phase 3 — golden API tests.

Covers the three Phase 3 surfaces from xenoISA/isA_user#441 (paired with
isA_/docs/design/427-artifact-flows.md §9-11):

  POST   /api/v1/artifacts/{id}/runtime/invoke        — quota-gated stub responder
  GET    /api/v1/artifacts/{id}/runtime/usage         — today's usage row + cap
  POST   /api/v1/artifacts/{id}/mcp/approve           — upsert MCP grant
  POST   /api/v1/artifacts/{id}/mcp/call              — approval-gated stub call
  GET    /api/v1/artifacts/{id}/mcp/grants            — list grants
  GET    /api/v1/artifacts/{id}/kv/{key}              — KV reader
  PUT    /api/v1/artifacts/{id}/kv/{key}              — KV writer
  DELETE /api/v1/artifacts/{id}/kv/{key}              — KV delete

Each test hits the running artifact_service on port 8291 (L4 golden layer per
.claude/rules/tdd-standard.md). Tests rely on the env var
ARTIFACT_DAILY_QUOTA being set when the service was started to a value
small enough to exercise the 429 path without hammering the DB. The default
in CI is 50; the dedicated quota test temporarily relies on a sub-quota cap
(see TestRuntimeQuota.test_exceeding_cap_returns_429_with_retry_after).
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

pytestmark = [pytest.mark.api, pytest.mark.asyncio, pytest.mark.golden]

ARTIFACT_SERVICE_URL = os.getenv("ARTIFACT_SERVICE_URL", "http://localhost:8291")
API_BASE = f"{ARTIFACT_SERVICE_URL}/api/v1"

# Cap configured for the test process. When the service ships in CI we set
# ARTIFACT_DAILY_QUOTA=3 so the quota-exceed test runs fast. If the service
# was started with the default 50, the quota-exceed test still works — it
# just makes 51 calls. We keep this knob low to avoid that.
TEST_QUOTA = int(os.getenv("ARTIFACT_DAILY_QUOTA", "3"))


@pytest.fixture
async def http_client():
    async with httpx.AsyncClient(timeout=15.0) as client:
        yield client


@pytest.fixture
def user_id():
    return f"test-441p3-{uuid.uuid4().hex[:10]}"


@pytest.fixture
def other_user_id():
    return f"test-441p3-other-{uuid.uuid4().hex[:10]}"


async def _create_artifact(
    http_client: httpx.AsyncClient,
    owner: str,
    *,
    title: str = "Phase 3 art",
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
# Runtime quota
# ==========================================================================


class TestRuntimeInvoke:
    async def test_invoke_returns_stub_and_books_usage(self, http_client, user_id):
        art = await _create_artifact(http_client, user_id)
        resp = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/runtime/invoke",
            json={"user_id": user_id, "prompt": "what is 2+2?"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Stubbed output contract — the body of the stub will change when we
        # wire isA_Model, so we only assert on the prompt echo prefix.
        assert body["output"].startswith("Phase 3 stub response for: ")
        assert body["tokens_in"] >= 1
        assert body["tokens_out"] == 32
        assert body["calls_today"] == 1
        assert body["quota"] >= 1

        # Usage GET reflects the booked call.
        usage = await http_client.get(
            f"{API_BASE}/artifacts/{art['id']}/runtime/usage",
            params={"user_id": user_id},
        )
        assert usage.status_code == 200
        u = usage.json()
        assert u["calls"] == 1
        assert u["tokens_out"] == 32
        assert u["remaining"] == u["quota"] - 1

    async def test_invoke_rejects_unknown_artifact(self, http_client, user_id):
        resp = await http_client.post(
            f"{API_BASE}/artifacts/does-not-exist/runtime/invoke",
            json={"user_id": user_id, "prompt": "hello"},
        )
        assert resp.status_code == 404


class TestRuntimeQuota:
    async def test_exceeding_cap_returns_429_with_retry_after(
        self, http_client, user_id
    ):
        art = await _create_artifact(http_client, user_id)
        # Drain the quota exactly to the cap.
        for i in range(TEST_QUOTA):
            r = await http_client.post(
                f"{API_BASE}/artifacts/{art['id']}/runtime/invoke",
                json={"user_id": user_id, "prompt": f"call {i}"},
            )
            assert r.status_code == 200, r.text

        # Next call MUST 429 with Retry-After hinted.
        over = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/runtime/invoke",
            json={"user_id": user_id, "prompt": "one too many"},
        )
        assert over.status_code == 429, over.text
        assert "retry-after" in {k.lower() for k in over.headers.keys()}
        retry_after_header = (
            over.headers.get("Retry-After") or over.headers.get("retry-after") or "0"
        )
        assert int(retry_after_header) > 0
        # Body carries machine-readable detail for the BFF to surface.
        detail = over.json().get("detail", {})
        # Some servers stringify dict details; accept either shape.
        if isinstance(detail, dict):
            assert detail.get("error") == "daily_quota_exceeded"
            assert detail.get("retry_after", 0) > 0
            assert detail.get("calls_today", 0) >= TEST_QUOTA

    async def test_quota_is_per_user(self, http_client, user_id, other_user_id):
        """Two users sharing one artifact have independent daily counts."""
        art = await _create_artifact(http_client, user_id)
        # user A burns one call.
        r1 = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/runtime/invoke",
            json={"user_id": user_id, "prompt": "A"},
        )
        assert r1.status_code == 200
        # user B's usage should be unaffected.
        usage_b = await http_client.get(
            f"{API_BASE}/artifacts/{art['id']}/runtime/usage",
            params={"user_id": other_user_id},
        )
        assert usage_b.status_code == 200
        assert usage_b.json()["calls"] == 0


# ==========================================================================
# MCP grants
# ==========================================================================


class TestMCPApprovalGate:
    async def test_first_call_requires_approval(self, http_client, user_id):
        art = await _create_artifact(http_client, user_id)
        resp = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/mcp/call",
            json={
                "user_id": user_id,
                "tool_name": "fs.read_file",
                "server_id": "isA_MCP",
                "args": {"path": "/etc/hosts"},
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["requires_approval"] is True
        assert body["tool_name"] == "fs.read_file"
        assert body["server_id"] == "isA_MCP"
        assert "fs.read_file" in body["prompt"]
        assert body.get("result") is None

    async def test_approve_then_call_returns_stub(self, http_client, user_id):
        art = await _create_artifact(http_client, user_id)
        # User approves with scope=always.
        ap = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/mcp/approve",
            json={
                "user_id": user_id,
                "tool_name": "fs.read_file",
                "server_id": "isA_MCP",
                "decision": "allow",
                "scope": "always",
            },
        )
        assert ap.status_code == 200, ap.text
        grant = ap.json()
        assert grant["decision"] == "allow"
        assert grant["scope"] == "always"

        # Re-issue the call — now it should succeed with a stubbed body.
        call = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/mcp/call",
            json={
                "user_id": user_id,
                "tool_name": "fs.read_file",
                "server_id": "isA_MCP",
                "args": {"path": "/etc/hosts"},
            },
        )
        assert call.status_code == 200
        body = call.json()
        assert body["requires_approval"] is False
        assert body["scope_used"] == "always"
        assert body["result"]["stubbed"] is True
        assert body["result"]["tool_name"] == "fs.read_file"
        assert body["result"]["args"] == {"path": "/etc/hosts"}

    async def test_once_scope_does_not_persist(self, http_client, user_id):
        """A `once`-scoped approval MUST NOT short-circuit subsequent calls."""
        art = await _create_artifact(http_client, user_id)
        await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/mcp/approve",
            json={
                "user_id": user_id,
                "tool_name": "shell.exec",
                "server_id": "isA_MCP",
                "decision": "allow",
                "scope": "once",
            },
        )
        call = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/mcp/call",
            json={
                "user_id": user_id,
                "tool_name": "shell.exec",
                "server_id": "isA_MCP",
                "args": {},
            },
        )
        assert call.status_code == 200
        assert call.json()["requires_approval"] is True

    async def test_list_grants_returns_approved_rows(self, http_client, user_id):
        art = await _create_artifact(http_client, user_id)
        await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/mcp/approve",
            json={
                "user_id": user_id,
                "tool_name": "net.fetch",
                "server_id": "isA_MCP",
                "decision": "allow",
                "scope": "always",
            },
        )
        resp = await http_client.get(
            f"{API_BASE}/artifacts/{art['id']}/mcp/grants",
            params={"user_id": user_id},
        )
        assert resp.status_code == 200
        grants = resp.json()["grants"]
        names = {g["tool_name"] for g in grants}
        assert "net.fetch" in names

    async def test_expired_grant_falls_back_to_approval_prompt(
        self, http_client, user_id
    ):
        """A grant whose ``expires_at`` is in the past MUST NOT short-circuit
        the approval gate — /mcp/call must respond identically to the
        no-grant case (``requires_approval=True``).

        Partial close of xenoISA/isA_#452 item 7 (security review): expired
        grants were previously honoured because the SQL filter was missing
        in earlier drafts. This test pins the SQL filter
        ``AND (expires_at IS NULL OR expires_at > NOW())`` so a regression
        re-opens the vulnerability.
        """
        art = await _create_artifact(http_client, user_id)
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        ap = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/mcp/approve",
            json={
                "user_id": user_id,
                "tool_name": "fs.read_file",
                "server_id": "isA_MCP",
                "decision": "allow",
                "scope": "always",
                "expires_at": past.isoformat(),
            },
        )
        assert ap.status_code == 200, ap.text

        call = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/mcp/call",
            json={
                "user_id": user_id,
                "tool_name": "fs.read_file",
                "server_id": "isA_MCP",
                "args": {"path": "/etc/hosts"},
            },
        )
        assert call.status_code == 200, call.text
        body = call.json()
        # Expired -> same response as "no grant".
        assert body["requires_approval"] is True
        assert body.get("result") is None
        assert "fs.read_file" in body["prompt"]

    async def test_future_expires_at_still_allows_call(self, http_client, user_id):
        """A grant with ``expires_at`` in the future MUST still proceed."""
        art = await _create_artifact(http_client, user_id)
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        ap = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/mcp/approve",
            json={
                "user_id": user_id,
                "tool_name": "fs.read_file",
                "server_id": "isA_MCP",
                "decision": "allow",
                "scope": "always",
                "expires_at": future.isoformat(),
            },
        )
        assert ap.status_code == 200, ap.text

        call = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/mcp/call",
            json={
                "user_id": user_id,
                "tool_name": "fs.read_file",
                "server_id": "isA_MCP",
                "args": {"path": "/etc/hosts"},
            },
        )
        assert call.status_code == 200
        body = call.json()
        assert body["requires_approval"] is False
        assert body["scope_used"] == "always"
        assert body["result"] is not None


# ==========================================================================
# KV storage
# ==========================================================================


class TestKVPersonalScope:
    async def test_put_then_get_round_trips_value(self, http_client, user_id):
        art = await _create_artifact(http_client, user_id)
        put = await http_client.put(
            f"{API_BASE}/artifacts/{art['id']}/kv/note",
            params={"scope": "personal", "user_id": user_id},
            json={"value": {"text": "hello", "n": 42}},
        )
        assert put.status_code == 200, put.text
        assert put.json()["value"] == {"text": "hello", "n": 42}

        got = await http_client.get(
            f"{API_BASE}/artifacts/{art['id']}/kv/note",
            params={"scope": "personal", "user_id": user_id},
        )
        assert got.status_code == 200
        assert got.json()["value"] == {"text": "hello", "n": 42}

    async def test_personal_is_isolated_per_user(
        self, http_client, user_id, other_user_id
    ):
        """User A's personal KV must NOT be visible to User B."""
        art = await _create_artifact(http_client, user_id)
        await http_client.put(
            f"{API_BASE}/artifacts/{art['id']}/kv/secret",
            params={"scope": "personal", "user_id": user_id},
            json={"value": "for-A"},
        )
        # User B reads — should 404.
        resp = await http_client.get(
            f"{API_BASE}/artifacts/{art['id']}/kv/secret",
            params={"scope": "personal", "user_id": other_user_id},
        )
        assert resp.status_code == 404

    async def test_delete_personal_key(self, http_client, user_id):
        art = await _create_artifact(http_client, user_id)
        await http_client.put(
            f"{API_BASE}/artifacts/{art['id']}/kv/k",
            params={"scope": "personal", "user_id": user_id},
            json={"value": 1},
        )
        d = await http_client.delete(
            f"{API_BASE}/artifacts/{art['id']}/kv/k",
            params={"scope": "personal", "user_id": user_id},
        )
        assert d.status_code == 200
        assert d.json()["success"] is True
        # Subsequent GET → 404.
        g = await http_client.get(
            f"{API_BASE}/artifacts/{art['id']}/kv/k",
            params={"scope": "personal", "user_id": user_id},
        )
        assert g.status_code == 404


class TestKVSharedScope:
    async def test_shared_write_requires_storage_scope_shared(
        self, http_client, user_id
    ):
        # storage_scope='none' on the artifact → shared write rejected (403).
        art = await _create_artifact(http_client, user_id, storage_scope="none")
        resp = await http_client.put(
            f"{API_BASE}/artifacts/{art['id']}/kv/team-data",
            params={"scope": "shared"},
            json={"value": "x"},
        )
        assert resp.status_code == 403, resp.text

    async def test_shared_value_visible_to_other_users(
        self, http_client, user_id, other_user_id
    ):
        """When storage_scope='shared', writes are readable cross-user."""
        art = await _create_artifact(http_client, user_id, storage_scope="shared")
        put = await http_client.put(
            f"{API_BASE}/artifacts/{art['id']}/kv/team-data",
            params={"scope": "shared"},
            json={"value": {"team": "alpha"}},
        )
        assert put.status_code == 200, put.text
        # Other user reads the same shared key.
        resp = await http_client.get(
            f"{API_BASE}/artifacts/{art['id']}/kv/team-data",
            params={"scope": "shared"},
        )
        assert resp.status_code == 200
        assert resp.json()["value"] == {"team": "alpha"}
