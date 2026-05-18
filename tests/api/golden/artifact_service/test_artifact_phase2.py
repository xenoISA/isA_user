"""
Artifact Service Phase 2 — golden API tests.

Covers the publish / revoke / public-reader / remix routes from
xenoISA/isA_user#441 Phase 2 (paired with xenoISA/isA_#427 §7-8):

  POST   /api/v1/artifacts/{id}/publish
  POST   /api/v1/artifacts/{id}/revoke
  GET    /api/v1/artifacts/{id}/shares
  GET    /api/v1/shares/artifacts/{token}
  POST   /api/v1/artifacts/remix

Real HTTP against the running artifact_service on port 8291 (L4 layer per
.claude/rules/tdd-standard.md).
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
def user_id():
    return f"test-441p2-{uuid.uuid4().hex[:10]}"


@pytest.fixture
def other_user_id():
    return f"test-441p2-other-{uuid.uuid4().hex[:10]}"


async def _create(http_client, owner: str, title: str = "Hello") -> dict:
    body = {
        "user_id": owner,
        "artifact": {
            "title": title,
            "content_type": "code",
            "visibility": "private",
            "version": {"content": "console.log(1)", "language": "typescript"},
        },
    }
    resp = await http_client.post(f"{API_BASE}/artifacts", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _publish(
    http_client,
    artifact_id: str,
    owner: str,
    *,
    visibility: str = "public",
    version_pin: int | None = None,
    org_id: str | None = None,
) -> dict:
    body = {"user_id": owner, "visibility": visibility}
    if version_pin is not None:
        body["version_pin"] = version_pin
    if org_id is not None:
        body["org_id"] = org_id
    resp = await http_client.post(f"{API_BASE}/artifacts/{artifact_id}/publish", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestPublish:
    async def test_publish_returns_token_and_url(self, http_client, user_id):
        art = await _create(http_client, user_id)
        body = await _publish(http_client, art["id"], user_id)
        assert len(body["token"]) >= 16
        assert body["url"].startswith("/a/") and body["url"].endswith(body["token"])
        assert body["visibility"] == "public"
        assert body["artifact_id"] == art["id"]

    async def test_publish_rejects_non_owner(self, http_client, user_id, other_user_id):
        art = await _create(http_client, user_id)
        resp = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/publish",
            json={"user_id": other_user_id, "visibility": "public"},
        )
        assert resp.status_code == 403

    async def test_publish_rejects_unknown_version_pin(self, http_client, user_id):
        art = await _create(http_client, user_id)
        resp = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/publish",
            json={"user_id": user_id, "visibility": "public", "version_pin": 99},
        )
        assert resp.status_code == 400

    async def test_publish_org_visibility_requires_org_id(self, http_client, user_id):
        art = await _create(http_client, user_id)
        resp = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/publish",
            json={"user_id": user_id, "visibility": "org"},
        )
        # Owner has no org_id and the request omits one → 400.
        assert resp.status_code == 400


class TestPublicReader:
    async def test_public_reader_returns_artifact_and_version(self, http_client, user_id):
        art = await _create(http_client, user_id, title="public art")
        published = await _publish(http_client, art["id"], user_id)
        resp = await http_client.get(f"{API_BASE}/shares/artifacts/{published['token']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["artifact"]["id"] == art["id"]
        assert data["version"]["number"] == 1
        assert data["share"]["visibility"] == "public"

    async def test_public_reader_404_on_unknown_token(self, http_client):
        resp = await http_client.get(f"{API_BASE}/shares/artifacts/does-not-exist")
        assert resp.status_code == 404

    async def test_public_reader_410_on_revoked_share(self, http_client, user_id):
        art = await _create(http_client, user_id)
        pub = await _publish(http_client, art["id"], user_id)
        rev = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/revoke",
            json={"user_id": user_id, "token": pub["token"]},
        )
        assert rev.status_code == 200 and rev.json()["revoked"] == 1
        resp = await http_client.get(f"{API_BASE}/shares/artifacts/{pub['token']}")
        assert resp.status_code == 410


class TestRevoke:
    async def test_revoke_all_revokes_every_active_share(self, http_client, user_id):
        art = await _create(http_client, user_id)
        a = await _publish(http_client, art["id"], user_id)
        b = await _publish(http_client, art["id"], user_id)
        assert a["token"] != b["token"]
        resp = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/revoke",
            json={"user_id": user_id},
        )
        assert resp.status_code == 200
        assert resp.json()["revoked"] == 2

    async def test_revoke_rejects_non_owner(self, http_client, user_id, other_user_id):
        art = await _create(http_client, user_id)
        await _publish(http_client, art["id"], user_id)
        resp = await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/revoke",
            json={"user_id": other_user_id},
        )
        assert resp.status_code == 403


class TestListShares:
    async def test_list_shares_returns_active_and_revoked(self, http_client, user_id):
        art = await _create(http_client, user_id)
        a = await _publish(http_client, art["id"], user_id)
        b = await _publish(http_client, art["id"], user_id)
        await http_client.post(
            f"{API_BASE}/artifacts/{art['id']}/revoke",
            json={"user_id": user_id, "token": a["token"]},
        )
        resp = await http_client.get(
            f"{API_BASE}/artifacts/{art['id']}/shares",
            params={"user_id": user_id},
        )
        assert resp.status_code == 200
        shares = resp.json()["shares"]
        # Returns both — one with revoked_at set, one without.
        assert len(shares) == 2
        tokens = {s["token"] for s in shares}
        assert tokens == {a["token"], b["token"]}


class TestRemix:
    async def test_remix_creates_new_artifact_for_caller(self, http_client, user_id, other_user_id):
        source = await _create(http_client, user_id, title="Original")
        pub = await _publish(http_client, source["id"], user_id)

        resp = await http_client.post(
            f"{API_BASE}/artifacts/remix",
            json={"token": pub["token"], "user_id": other_user_id},
        )
        assert resp.status_code == 200, resp.text
        clone = resp.json()
        assert clone["id"] != source["id"]
        assert clone["owner_user_id"] == other_user_id
        assert clone["parent_artifact_id"] == source["id"]
        assert clone["visibility"] == "private"
        assert clone["title"].startswith("Remix of ")
        # Content copied verbatim into v1 of the remix.
        assert clone["versions"][0]["content"] == "console.log(1)"
        assert clone["metadata"]["remixed_from"] == source["id"]

    async def test_remix_410_on_revoked_token(self, http_client, user_id, other_user_id):
        source = await _create(http_client, user_id)
        pub = await _publish(http_client, source["id"], user_id)
        await http_client.post(
            f"{API_BASE}/artifacts/{source['id']}/revoke",
            json={"user_id": user_id, "token": pub["token"]},
        )
        resp = await http_client.post(
            f"{API_BASE}/artifacts/remix",
            json={"token": pub["token"], "user_id": other_user_id},
        )
        assert resp.status_code == 410

    async def test_remix_404_on_unknown_token(self, http_client, other_user_id):
        resp = await http_client.post(
            f"{API_BASE}/artifacts/remix",
            json={"token": "nonexistent-token-9999", "user_id": other_user_id},
        )
        assert resp.status_code == 404
