"""
Memory Service Phase 2 hard-slice routes — golden API tests.

Covers the four routes from xenoISA/isA_user#439 that need synthesis + vector
search (paired with #428 §4-5):
  GET   /api/v1/memories/summary?scope=&scope_id=
  PUT   /api/v1/memories/summary
  POST  /api/v1/memories/summary/regenerate
  POST  /api/v1/memories/past-chats/search

Each test sends a real HTTP request to the running memory_service on port 8223
(L4 layer per .claude/rules/tdd-standard.md). LLM and Qdrant fallbacks are
asserted on shape rather than content so the tests pass whether or not the
isA_Model / Qdrant sidecars are reachable.
"""

import os
import uuid

import httpx
import pytest

pytestmark = [pytest.mark.api, pytest.mark.asyncio, pytest.mark.golden]

MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://localhost:8223")
API_BASE = f"{MEMORY_SERVICE_URL}/api/v1"


@pytest.fixture
async def http_client():
    async with httpx.AsyncClient(timeout=60.0) as client:
        yield client


@pytest.fixture
def fresh_user_id():
    """Unique user id per test so summary rows / session memories don't bleed."""
    return f"test-439-hard-{uuid.uuid4().hex[:10]}"


# ---------------------------------------------------------------------------
# GET /summary
# ---------------------------------------------------------------------------


class TestGetSummary:
    async def test_get_summary_returns_404_when_none_exists(self, http_client, fresh_user_id):
        # The FE's getSummary contract maps 404 → null. We MUST 404 (not 200/empty)
        # so the client surface is correct.
        resp = await http_client.get(
            f"{API_BASE}/memories/summary",
            params={"scope": "user", "scope_id": fresh_user_id},
        )
        assert resp.status_code == 404

    async def test_get_summary_rejects_invalid_scope(self, http_client, fresh_user_id):
        resp = await http_client.get(
            f"{API_BASE}/memories/summary",
            params={"scope": "global", "scope_id": fresh_user_id},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT /summary
# ---------------------------------------------------------------------------


class TestSaveSummary:
    async def test_put_summary_creates_then_bumps_version(self, http_client, fresh_user_id):
        # Initial save → version 1, edited_at populated.
        resp = await http_client.put(
            f"{API_BASE}/memories/summary",
            json={"scope": "user", "scope_id": fresh_user_id, "content": "First edit"},
        )
        assert resp.status_code == 200
        first = resp.json()
        assert first["version"] == 1
        assert first["content"] == "First edit"
        assert first["edited_at"] is not None

        # Second save → version bumps to 2.
        resp2 = await http_client.put(
            f"{API_BASE}/memories/summary",
            json={"scope": "user", "scope_id": fresh_user_id, "content": "Second edit"},
        )
        assert resp2.status_code == 200
        second = resp2.json()
        assert second["version"] == 2
        assert second["content"] == "Second edit"

        # GET now returns the latest row (no longer 404).
        resp3 = await http_client.get(
            f"{API_BASE}/memories/summary",
            params={"scope": "user", "scope_id": fresh_user_id},
        )
        assert resp3.status_code == 200
        latest = resp3.json()
        assert latest["version"] == 2
        assert latest["content"] == "Second edit"


# ---------------------------------------------------------------------------
# POST /summary/regenerate
# ---------------------------------------------------------------------------


class TestRegenerateSummary:
    async def test_regenerate_for_empty_user_uses_fallback(self, http_client, fresh_user_id):
        # No memories → synthesize_summary returns the fallback "Summary of 0".
        # The endpoint MUST still return a valid MemorySummary row (200, not 500).
        resp = await http_client.post(
            f"{API_BASE}/memories/summary/regenerate",
            json={"scope": "user", "scope_id": fresh_user_id},
        )
        assert resp.status_code == 200
        row = resp.json()
        assert row["scope"] == "user"
        assert row["scope_id"] == fresh_user_id
        assert isinstance(row["content"], str) and row["content"]
        assert isinstance(row["highlights"], list)
        assert row["version"] >= 1
        assert row["edited_at"] is None  # regenerate clears edited_at
        assert row["generated_at"] is not None
        # source_counts MUST carry the shape the FE expects.
        assert "memories" in row["source_counts"]

    async def test_regenerate_bumps_version_over_existing_edit(self, http_client, fresh_user_id):
        # Seed an edit (version 1) → regenerate should produce version 2.
        await http_client.put(
            f"{API_BASE}/memories/summary",
            json={"scope": "user", "scope_id": fresh_user_id, "content": "Hand-edited"},
        )
        resp = await http_client.post(
            f"{API_BASE}/memories/summary/regenerate",
            json={"scope": "user", "scope_id": fresh_user_id},
        )
        assert resp.status_code == 200
        row = resp.json()
        assert row["version"] == 2
        assert row["edited_at"] is None  # cleared by regenerate


# ---------------------------------------------------------------------------
# POST /past-chats/search
# ---------------------------------------------------------------------------


class TestPastChatsSearch:
    async def test_past_chats_returns_empty_list_when_no_data(self, http_client, fresh_user_id):
        # Brand-new user has no session memories — must return [] not 500.
        resp = await http_client.post(
            f"{API_BASE}/memories/past-chats/search",
            json={
                "user_id": fresh_user_id,
                "query": "what did we discuss last week",
                "scope": "user",
                "k": 8,
                "exclude_incognito": True,
            },
        )
        assert resp.status_code == 200
        hits = resp.json()
        assert isinstance(hits, list)
        assert hits == []

    async def test_past_chats_empty_query_returns_empty_list(self, http_client, fresh_user_id):
        resp = await http_client.post(
            f"{API_BASE}/memories/past-chats/search",
            json={"user_id": fresh_user_id, "query": "", "k": 8},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_past_chats_filters_incognito_turn_via_sql_fallback(self, http_client, fresh_user_id):
        # Seed two session memories — one normal, one incognito. The ILIKE
        # fallback MUST drop the incognito row even if it text-matches.
        session_a = f"sess-{uuid.uuid4().hex[:8]}"
        session_b = f"sess-{uuid.uuid4().hex[:8]}"

        normal = await http_client.post(
            f"{API_BASE}/memories/session/store",
            json={
                "user_id": fresh_user_id,
                "session_id": session_a,
                "message_content": "We talked about quantum tunnelling in detail.",
                "message_type": "human",
                "role": "user",
            },
        )
        # If session/store is degraded we can't run the filter assertion — skip cleanly.
        if normal.status_code >= 500:
            pytest.skip("session/store unavailable in this environment")
        assert normal.status_code == 200

        incog = await http_client.post(
            f"{API_BASE}/memories/session/store",
            json={
                "user_id": fresh_user_id,
                "session_id": session_b,
                "message_content": "Secret quantum tunnelling chat (incognito).",
                "message_type": "human",
                "role": "user",
            },
        )
        assert incog.status_code == 200

        # Best-effort: stamp the second session as incognito via the
        # conversation_state column. The session/store endpoint sets
        # conversation_state from `message_type`/`role` only, so we patch it
        # directly through SQL to simulate an incognito-tagged turn.
        import asyncpg

        conn = await asyncpg.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            database=os.getenv("POSTGRES_DB", "isa_platform"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "staging_postgres_2024"),
        )
        try:
            # The session/store path double-encodes conversation_state as a
            # JSON string (jsonb_typeof = 'string'). Cast back to a real object
            # before patching so `->>'incognito'` works in the route filter.
            await conn.execute(
                """
                UPDATE memory.session_memories
                SET conversation_state = jsonb_set(
                    CASE
                        WHEN jsonb_typeof(conversation_state) = 'object'
                            THEN conversation_state
                        WHEN jsonb_typeof(conversation_state) = 'string'
                            THEN (conversation_state #>> '{}')::jsonb
                        ELSE '{}'::jsonb
                    END,
                    '{incognito}',
                    'true'::jsonb,
                    true
                )
                WHERE user_id = $1 AND session_id = $2
                """,
                fresh_user_id,
                session_b,
            )
        finally:
            await conn.close()

        resp = await http_client.post(
            f"{API_BASE}/memories/past-chats/search",
            json={
                "user_id": fresh_user_id,
                "query": "quantum tunnelling",
                "scope": "user",
                "k": 10,
                "exclude_incognito": True,
            },
        )
        assert resp.status_code == 200
        hits = resp.json()
        assert isinstance(hits, list)
        # All returned hits must be from the non-incognito session.
        returned_sessions = {h["session_id"] for h in hits}
        assert session_b not in returned_sessions, f"Incognito session {session_b} leaked into past-chats: {hits}"
        # And if Qdrant/SQL retrieved anything, it should be session_a.
        if hits:
            assert any(h["session_id"] == session_a for h in hits)
            # Shape contract — required PastChatHit fields.
            for h in hits:
                assert "session_id" in h
                assert "turn_id" in h
                assert "excerpt" in h
                assert "score" in h and 0.0 <= h["score"] <= 1.0
                assert "occurred_at" in h

    async def test_past_chats_rejects_invalid_scope(self, http_client, fresh_user_id):
        resp = await http_client.post(
            f"{API_BASE}/memories/past-chats/search",
            json={"user_id": fresh_user_id, "query": "hi", "scope": "global"},
        )
        assert resp.status_code == 400
