"""
Artifact Service routes — golden API tests.

Tests the P0 slice from xenoISA/isA_user#441 (paired with xenoISA/isA_#427):
  POST   /api/v1/artifacts                       — create artifact + first version
  GET    /api/v1/artifacts                       — list with scope/q/cursor
  GET    /api/v1/artifacts/{id}                  — fetch with all versions
  PATCH  /api/v1/artifacts/{id}                  — update title / visibility / flags
  DELETE /api/v1/artifacts/{id}                  — soft delete
  POST   /api/v1/artifacts/{id}/versions         — append a new version

Each test sends a real HTTP request to the running artifact_service on
port 8291 (L4 layer per .claude/rules/tdd-standard.md).
"""

import os
import uuid

import httpx
import pytest

pytestmark = [pytest.mark.api, pytest.mark.asyncio, pytest.mark.golden]

ARTIFACT_SERVICE_URL = os.getenv("ARTIFACT_SERVICE_URL", "http://localhost:8291")
API_BASE = f"{ARTIFACT_SERVICE_URL}/api/v1"


@pytest.fixture
async def http_client():
    async with httpx.AsyncClient(timeout=15.0) as client:
        yield client


@pytest.fixture
def fresh_user_id():
    """Unique user id per test so library rows don't bleed across cases."""
    return f"test-441-{uuid.uuid4().hex[:10]}"


def _create_body(user_id: str, **artifact_overrides):
    artifact = {
        "title": "Hello artifact",
        "content_type": "code",
        "visibility": "private",
        "version": {
            "content": "console.log('hi')",
            "language": "typescript",
        },
    }
    artifact.update(artifact_overrides)
    return {"user_id": user_id, "artifact": artifact}


async def _create(http_client, user_id: str, **overrides) -> dict:
    resp = await http_client.post(f"{API_BASE}/artifacts", json=_create_body(user_id, **overrides))
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestCreate:
    async def test_create_returns_artifact_with_first_version(self, http_client, fresh_user_id):
        artifact = await _create(http_client, fresh_user_id, title="My snippet")
        assert artifact["title"] == "My snippet"
        assert artifact["owner_user_id"] == fresh_user_id
        assert artifact["visibility"] == "private"
        assert artifact["content_type"] == "code"
        assert len(artifact["versions"]) == 1
        assert artifact["versions"][0]["number"] == 1
        assert artifact["versions"][0]["content"] == "console.log('hi')"
        assert artifact["current_version_id"] == artifact["versions"][0]["id"]

    async def test_create_rejects_empty_title(self, http_client, fresh_user_id):
        body = _create_body(fresh_user_id)
        body["artifact"]["title"] = ""
        resp = await http_client.post(f"{API_BASE}/artifacts", json=body)
        assert resp.status_code == 422


class TestGet:
    async def test_get_returns_full_artifact_with_versions(self, http_client, fresh_user_id):
        created = await _create(http_client, fresh_user_id)
        resp = await http_client.get(
            f"{API_BASE}/artifacts/{created['id']}",
            params={"user_id": fresh_user_id},
        )
        assert resp.status_code == 200
        fetched = resp.json()
        assert fetched["id"] == created["id"]
        assert len(fetched["versions"]) == 1

    async def test_get_missing_returns_404(self, http_client, fresh_user_id):
        resp = await http_client.get(
            f"{API_BASE}/artifacts/does-not-exist",
            params={"user_id": fresh_user_id},
        )
        assert resp.status_code == 404


class TestList:
    async def test_list_returns_owned_artifacts_for_user(self, http_client, fresh_user_id):
        await _create(http_client, fresh_user_id, title="a")
        await _create(http_client, fresh_user_id, title="b")
        resp = await http_client.get(f"{API_BASE}/artifacts", params={"user_id": fresh_user_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        titles = {item["title"] for item in data["items"]}
        assert {"a", "b"}.issubset(titles)

    async def test_list_query_filter_matches_title(self, http_client, fresh_user_id):
        await _create(http_client, fresh_user_id, title="alpha tag")
        await _create(http_client, fresh_user_id, title="beta tag")
        resp = await http_client.get(
            f"{API_BASE}/artifacts",
            params={"user_id": fresh_user_id, "q": "alpha"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all("alpha" in item["title"].lower() for item in items)
        assert len(items) >= 1


class TestUpdate:
    async def test_patch_visibility(self, http_client, fresh_user_id):
        created = await _create(http_client, fresh_user_id)
        resp = await http_client.patch(
            f"{API_BASE}/artifacts/{created['id']}",
            json={"user_id": fresh_user_id, "update": {"visibility": "public"}},
        )
        assert resp.status_code == 200
        assert resp.json()["visibility"] == "public"

    async def test_patch_title(self, http_client, fresh_user_id):
        created = await _create(http_client, fresh_user_id)
        resp = await http_client.patch(
            f"{API_BASE}/artifacts/{created['id']}",
            json={"user_id": fresh_user_id, "update": {"title": "Renamed"}},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Renamed"


class TestSoftDelete:
    async def test_delete_hides_from_default_list(self, http_client, fresh_user_id):
        created = await _create(http_client, fresh_user_id, title="will-go")
        del_resp = await http_client.delete(
            f"{API_BASE}/artifacts/{created['id']}",
            params={"user_id": fresh_user_id},
        )
        assert del_resp.status_code == 200
        list_resp = await http_client.get(f"{API_BASE}/artifacts", params={"user_id": fresh_user_id})
        ids = {item["id"] for item in list_resp.json()["items"]}
        assert created["id"] not in ids


class TestVersions:
    async def test_add_version_appends_with_auto_increment(self, http_client, fresh_user_id):
        created = await _create(http_client, fresh_user_id)
        v2 = await http_client.post(
            f"{API_BASE}/artifacts/{created['id']}/versions",
            json={
                "user_id": fresh_user_id,
                "version": {"content": "v2 content", "language": "typescript"},
            },
        )
        assert v2.status_code == 200, v2.text
        body = v2.json()
        assert body["number"] == 2
        assert body["content"] == "v2 content"

        # Fetch confirms 2 versions live on the artifact.
        full = await http_client.get(
            f"{API_BASE}/artifacts/{created['id']}",
            params={"user_id": fresh_user_id},
        )
        assert len(full.json()["versions"]) == 2

    async def test_add_version_to_unknown_artifact_returns_404(self, http_client, fresh_user_id):
        resp = await http_client.post(
            f"{API_BASE}/artifacts/missing-id/versions",
            json={
                "user_id": fresh_user_id,
                "version": {"content": "anything"},
            },
        )
        assert resp.status_code == 404
