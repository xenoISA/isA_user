"""
Memory Service Phase 2 routes — golden API tests.

Tests the simple Phase 2 slice from xenoISA/isA_user#439 (paired with
xenoISA/isA_#428 / #439):
  GET    /api/v1/memories/state
  POST   /api/v1/memories/pause
  POST   /api/v1/memories/resume
  POST   /api/v1/memories/reset
  GET    /api/v1/memories/export
  POST   /api/v1/memories/import

Each test sends a real HTTP request to the running memory_service on
port 8223 (matches the L4 layer in .claude/rules/tdd-standard.md).
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
    async with httpx.AsyncClient(timeout=15.0) as client:
        yield client


@pytest.fixture
def fresh_user_id():
    """Unique user id per test so state rows don't bleed between cases."""
    return f"test-439-{uuid.uuid4().hex[:10]}"


class TestStateEndpoint:
    async def test_state_for_new_user_defaults_to_unpaused(self, http_client, fresh_user_id):
        resp = await http_client.get(f"{API_BASE}/memories/state", params={"user_id": fresh_user_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["paused"] is False

    async def test_state_requires_user_id(self, http_client):
        resp = await http_client.get(f"{API_BASE}/memories/state")
        assert resp.status_code == 422  # FastAPI Query(...) validation


class TestPauseResume:
    async def test_pause_sets_paused_and_paused_at(self, http_client, fresh_user_id):
        resp = await http_client.post(f"{API_BASE}/memories/pause", json={"user_id": fresh_user_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["paused"] is True
        assert data["paused_at"] is not None

    async def test_resume_clears_paused(self, http_client, fresh_user_id):
        # Pause first so resume has something to flip.
        await http_client.post(f"{API_BASE}/memories/pause", json={"user_id": fresh_user_id})
        resp = await http_client.post(f"{API_BASE}/memories/resume", json={"user_id": fresh_user_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["paused"] is False
        assert data["paused_at"] is None

    async def test_get_state_reflects_pause_state_after_toggle(self, http_client, fresh_user_id):
        await http_client.post(f"{API_BASE}/memories/pause", json={"user_id": fresh_user_id})
        resp = await http_client.get(f"{API_BASE}/memories/state", params={"user_id": fresh_user_id})
        assert resp.json()["paused"] is True


class TestResetEndpoint:
    async def test_reset_without_confirmation_returns_400(self, http_client, fresh_user_id):
        resp = await http_client.post(
            f"{API_BASE}/memories/reset",
            json={"user_id": fresh_user_id, "confirmation": "please"},
        )
        assert resp.status_code == 400
        assert "RESET" in resp.json()["detail"]

    async def test_reset_with_typed_confirmation_succeeds(self, http_client, fresh_user_id):
        resp = await http_client.post(
            f"{API_BASE}/memories/reset",
            json={"user_id": fresh_user_id, "confirmation": "RESET"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "deleted" in data
        assert data["state"]["last_reset_at"] is not None


class TestExportImport:
    async def test_export_returns_versioned_bundle(self, http_client, fresh_user_id):
        resp = await http_client.get(
            f"{API_BASE}/memories/export",
            params={"user_id": fresh_user_id, "scope": "user"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["schema_version"] == "1.0"
        assert data["user_id"] == fresh_user_id
        assert data["scope"] == "user"
        assert isinstance(data["memories"], list)
        assert "counts" in data and "memories" in data["counts"]

    async def test_export_rejects_invalid_scope(self, http_client, fresh_user_id):
        resp = await http_client.get(
            f"{API_BASE}/memories/export",
            params={"user_id": fresh_user_id, "scope": "global"},
        )
        assert resp.status_code == 422

    async def test_import_rejects_bad_schema_version(self, http_client, fresh_user_id):
        resp = await http_client.post(
            f"{API_BASE}/memories/import",
            json={
                "user_id": fresh_user_id,
                "mode": "merge",
                "payload": {
                    "schema_version": "0.1",
                    "memories": [],
                    "counts": {"memories": 0, "by_type": {}},
                },
            },
        )
        assert resp.status_code == 400
        assert "schema_version" in resp.json()["detail"]

    async def test_import_rejects_bad_mode(self, http_client, fresh_user_id):
        resp = await http_client.post(
            f"{API_BASE}/memories/import",
            json={
                "user_id": fresh_user_id,
                "mode": "wat",
                "payload": {"schema_version": "1.0", "memories": []},
            },
        )
        assert resp.status_code == 400

    async def test_import_rejects_non_list_memories(self, http_client, fresh_user_id):
        resp = await http_client.post(
            f"{API_BASE}/memories/import",
            json={
                "user_id": fresh_user_id,
                "mode": "merge",
                "payload": {"schema_version": "1.0", "memories": "not-a-list"},
            },
        )
        assert resp.status_code == 400

    async def test_import_merge_returns_counts(self, http_client, fresh_user_id):
        resp = await http_client.post(
            f"{API_BASE}/memories/import",
            json={
                "user_id": fresh_user_id,
                "mode": "merge",
                "payload": {
                    "schema_version": "1.0",
                    "memories": [{"id": "m1"}, {"id": "m2"}],
                    "counts": {"memories": 2, "by_type": {}},
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "merge"
        assert data["skipped"] == 2
        assert data["errors"] == []
