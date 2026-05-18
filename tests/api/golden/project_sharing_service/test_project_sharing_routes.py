"""
Project Sharing Service — golden API tests (L4).

Tests the P0 slice from xenoISA/isA_user#442 (paired with xenoISA/isA_#429):

  POST   /api/v1/projects/{project_id}/shares          -> invite (idempotent on pending email)
  GET    /api/v1/projects/{project_id}/shares          -> list (?status= optional)
  PATCH  /api/v1/projects/{project_id}/shares/{share_id} -> update role
  DELETE /api/v1/projects/{project_id}/shares/{share_id} -> revoke (nulls token)
  POST   /api/v1/shares/accept/{token}                 -> accept (idempotent on accepted)

Each test sends a real HTTP request to the running project_sharing_service on
port 8270 (matches the L4 layer in .claude/rules/tdd-standard.md).
"""

import os
import uuid

import httpx
import pytest

pytestmark = [pytest.mark.api, pytest.mark.asyncio, pytest.mark.golden]

PROJECT_SHARING_SERVICE_URL = os.getenv("PROJECT_SHARING_SERVICE_URL", "http://localhost:8270")
API_BASE = f"{PROJECT_SHARING_SERVICE_URL}/api/v1"


@pytest.fixture
async def http_client():
    async with httpx.AsyncClient(timeout=15.0) as client:
        yield client


@pytest.fixture
def project_id():
    """Unique project_id per test so rows don't bleed between cases."""
    return str(uuid.uuid4())


@pytest.fixture
def invitee_email():
    """Unique email per test."""
    return f"test-442-{uuid.uuid4().hex[:10]}@example.com"


# ---------------------------------------------------------------------------
# Invite
# ---------------------------------------------------------------------------


class TestInvite:
    async def test_invite_happy_path_returns_token_and_url(self, http_client, project_id, invitee_email):
        resp = await http_client.post(
            f"{API_BASE}/projects/{project_id}/shares",
            json={"invitee_email": invitee_email, "role": "viewer"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["project_id"] == project_id
        assert data["invitee_email"] == invitee_email
        assert data["role"] == "viewer"
        assert data["status"] == "pending"
        assert data["invite_token"]
        assert len(data["invite_token"]) == 22  # 22-char base62
        assert data["share_url"].endswith(f"/{data['invite_token']}")
        assert data["created_at"] is not None
        # uuid sanity
        uuid.UUID(data["id"])

    async def test_invite_duplicate_pending_returns_same_row(self, http_client, project_id, invitee_email):
        first = await http_client.post(
            f"{API_BASE}/projects/{project_id}/shares",
            json={"invitee_email": invitee_email, "role": "viewer"},
        )
        assert first.status_code == 201, first.text
        second = await http_client.post(
            f"{API_BASE}/projects/{project_id}/shares",
            json={"invitee_email": invitee_email, "role": "editor"},
        )
        # Idempotent: same id + same token (the role on the existing row wins;
        # re-invite is a no-op while pending).
        assert second.status_code == 201, second.text
        assert second.json()["id"] == first.json()["id"]
        assert second.json()["invite_token"] == first.json()["invite_token"]
        assert second.json()["role"] == first.json()["role"]

    async def test_invite_with_invalid_email_returns_422(self, http_client, project_id):
        resp = await http_client.post(
            f"{API_BASE}/projects/{project_id}/shares",
            json={"invitee_email": "not-an-email", "role": "viewer"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


class TestList:
    async def test_list_returns_invited_share(self, http_client, project_id, invitee_email):
        await http_client.post(
            f"{API_BASE}/projects/{project_id}/shares",
            json={"invitee_email": invitee_email, "role": "viewer"},
        )
        resp = await http_client.get(f"{API_BASE}/projects/{project_id}/shares")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] == 1
        assert data["shares"][0]["invitee_email"] == invitee_email
        assert data["shares"][0]["status"] == "pending"

    async def test_list_filters_by_status(self, http_client, project_id, invitee_email):
        # Create two invites: one stays pending, one will be revoked.
        other_email = f"other-{uuid.uuid4().hex[:8]}@example.com"
        a = await http_client.post(
            f"{API_BASE}/projects/{project_id}/shares",
            json={"invitee_email": invitee_email, "role": "viewer"},
        )
        b = await http_client.post(
            f"{API_BASE}/projects/{project_id}/shares",
            json={"invitee_email": other_email, "role": "editor"},
        )
        assert a.status_code == 201 and b.status_code == 201

        # Revoke the second.
        revoke = await http_client.delete(f"{API_BASE}/projects/{project_id}/shares/{b.json()['id']}")
        assert revoke.status_code == 200, revoke.text

        # Filter pending: should only return the first.
        pending = await http_client.get(f"{API_BASE}/projects/{project_id}/shares", params={"status": "pending"})
        assert pending.status_code == 200
        pending_data = pending.json()
        assert pending_data["total"] == 1
        assert pending_data["shares"][0]["id"] == a.json()["id"]

        # Filter revoked: should only return the second.
        revoked = await http_client.get(f"{API_BASE}/projects/{project_id}/shares", params={"status": "revoked"})
        assert revoked.status_code == 200
        revoked_data = revoked.json()
        assert revoked_data["total"] == 1
        assert revoked_data["shares"][0]["id"] == b.json()["id"]

    async def test_list_with_invalid_status_returns_400(self, http_client, project_id):
        resp = await http_client.get(
            f"{API_BASE}/projects/{project_id}/shares",
            params={"status": "not-a-status"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Role update
# ---------------------------------------------------------------------------


class TestUpdateRole:
    async def test_patch_role_updates_share(self, http_client, project_id, invitee_email):
        created = await http_client.post(
            f"{API_BASE}/projects/{project_id}/shares",
            json={"invitee_email": invitee_email, "role": "viewer"},
        )
        share_id = created.json()["id"]

        resp = await http_client.patch(
            f"{API_BASE}/projects/{project_id}/shares/{share_id}",
            json={"role": "editor"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["role"] == "editor"
        assert resp.json()["id"] == share_id

    async def test_patch_unknown_share_returns_404(self, http_client, project_id):
        resp = await http_client.patch(
            f"{API_BASE}/projects/{project_id}/shares/{uuid.uuid4()}",
            json={"role": "editor"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Revoke
# ---------------------------------------------------------------------------


class TestRevoke:
    async def test_revoke_marks_status_and_nulls_token(self, http_client, project_id, invitee_email):
        created = await http_client.post(
            f"{API_BASE}/projects/{project_id}/shares",
            json={"invitee_email": invitee_email, "role": "viewer"},
        )
        share_id = created.json()["id"]
        token = created.json()["invite_token"]

        resp = await http_client.delete(f"{API_BASE}/projects/{project_id}/shares/{share_id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "revoked"
        assert resp.json()["revoked_at"] is not None

        # Listing the row should still show it but with no token.
        listed = await http_client.get(
            f"{API_BASE}/projects/{project_id}/shares",
            params={"status": "revoked"},
        )
        assert listed.status_code == 200
        rows = listed.json()["shares"]
        assert len(rows) == 1
        assert rows[0]["id"] == share_id
        assert rows[0]["invite_token"] is None
        assert rows[0]["share_url"] is None

        # And the old token must not be acceptable any more.
        accept = await http_client.post(
            f"{API_BASE}/shares/accept/{token}",
            json={"invitee_user_id": "u-anyone"},
        )
        assert accept.status_code == 404


# ---------------------------------------------------------------------------
# Accept
# ---------------------------------------------------------------------------


class TestAccept:
    async def test_accept_happy_path(self, http_client, project_id, invitee_email):
        created = await http_client.post(
            f"{API_BASE}/projects/{project_id}/shares",
            json={"invitee_email": invitee_email, "role": "viewer"},
        )
        token = created.json()["invite_token"]

        resp = await http_client.post(
            f"{API_BASE}/shares/accept/{token}",
            json={"invitee_user_id": "u-acceptor"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["invitee_user_id"] == "u-acceptor"
        assert data["accepted_at"] is not None
        assert data["id"] == created.json()["id"]

    async def test_accept_is_idempotent_for_already_accepted(self, http_client, project_id, invitee_email):
        created = await http_client.post(
            f"{API_BASE}/projects/{project_id}/shares",
            json={"invitee_email": invitee_email, "role": "viewer"},
        )
        token = created.json()["invite_token"]

        first = await http_client.post(
            f"{API_BASE}/shares/accept/{token}",
            json={"invitee_user_id": "u-acceptor"},
        )
        assert first.status_code == 200
        # Second accept on the same token should succeed (idempotent) and return the same row.
        second = await http_client.post(
            f"{API_BASE}/shares/accept/{token}",
            json={"invitee_user_id": "u-acceptor"},
        )
        assert second.status_code == 200, second.text
        assert second.json()["status"] == "accepted"
        assert second.json()["id"] == first.json()["id"]
        assert second.json()["accepted_at"] == first.json()["accepted_at"]

    async def test_accept_with_unknown_token_returns_404(self, http_client):
        bogus = "x" * 22  # well-formed but not in the DB
        resp = await http_client.post(
            f"{API_BASE}/shares/accept/{bogus}",
            json={"invitee_user_id": "u-nobody"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Health (smoke)
# ---------------------------------------------------------------------------


class TestHealth:
    async def test_health_endpoint_returns_200(self, http_client):
        resp = await http_client.get(f"{PROJECT_SHARING_SERVICE_URL}/health")
        assert resp.status_code == 200
        assert resp.json().get("status") in ("healthy", "degraded")
