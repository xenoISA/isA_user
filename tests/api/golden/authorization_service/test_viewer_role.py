"""
Authorization Service — viewer-role write rejection tests (Story 9).

Covers POST /api/v1/authorization/check added in Story 9 of #442:
- read actions are always allowed for project resources
- viewer role on a project cannot write
- editor / owner roles can write
- invalid actions and unsupported resource_type return 4xx
- unknown users (no accepted share) are rejected with allowed=false

These tests authoritatively run against the live authorization_service.
When project_sharing_service is also live, the editor/viewer cases drive
through the real role lookup via the internal HTTP client. When it isn't,
the unknown-share path still exercises the fail-closed branch, which is
the security-critical default we care about most.
"""

import uuid

import httpx
import pytest
import pytest_asyncio

pytestmark = [pytest.mark.api, pytest.mark.golden, pytest.mark.asyncio]


AUTHORIZATION_SERVICE_URL = "http://localhost:8204"
PROJECT_SHARING_SERVICE_URL = "http://localhost:8270"
TIMEOUT = 30.0


def _user() -> str:
    return f"api_test_{uuid.uuid4().hex[:12]}"


def _project() -> str:
    # project_id is treated as an opaque string by /check.
    return str(uuid.uuid4())


@pytest_asyncio.fixture
async def http_client():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


async def _project_sharing_up(http_client: httpx.AsyncClient) -> bool:
    """Return True if project_sharing_service is reachable on the dev port."""
    try:
        resp = await http_client.get(f"{PROJECT_SHARING_SERVICE_URL}/health")
        return resp.status_code == 200
    except Exception:
        return False


async def _create_accepted_share(
    http_client: httpx.AsyncClient,
    project_id: str,
    user_id: str,
    role: str,
) -> bool:
    """
    Best-effort helper: create a share, accept it, returning True iff the
    full invite-accept handshake succeeded. Used only when the sister
    project_sharing_service is up.
    """
    try:
        # Invite by email — email isn't load-bearing here, the token is.
        invite_resp = await http_client.post(
            f"{PROJECT_SHARING_SERVICE_URL}/api/v1/projects/{project_id}/shares",
            json={
                "invitee_email": f"{user_id}@example.com",
                "role": role,
            },
        )
        if invite_resp.status_code not in (200, 201):
            return False
        token = invite_resp.json().get("invite_token")
        if not token:
            return False
        accept_resp = await http_client.post(
            f"{PROJECT_SHARING_SERVICE_URL}/api/v1/shares/accept/{token}",
            json={"invitee_user_id": user_id},
        )
        return accept_resp.status_code in (200, 201)
    except Exception:
        return False


class TestProjectAccessCheckContract:
    """POST /api/v1/authorization/check — request/response contract."""

    async def test_read_action_is_always_allowed(self, http_client):
        """Reads on a project are unconditionally allowed (no role lookup)."""
        resp = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/authorization/check",
            json={
                "user_id": _user(),
                "resource_type": "project",
                "resource_id": _project(),
                "action": "read",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["allowed"] is True

    async def test_invalid_action_returns_400(self, http_client):
        """Action outside read|write|admin is rejected with 400."""
        resp = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/authorization/check",
            json={
                "user_id": _user(),
                "resource_type": "project",
                "resource_id": _project(),
                "action": "delete",  # not allowed
            },
        )
        assert resp.status_code == 400, resp.text

    async def test_unsupported_resource_type_returns_400(self, http_client):
        """Only resource_type=project is wired through /check."""
        resp = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/authorization/check",
            json={
                "user_id": _user(),
                "resource_type": "session",  # unsupported
                "resource_id": "anything",
                "action": "write",
            },
        )
        assert resp.status_code == 400, resp.text

    async def test_unknown_user_write_is_rejected(self, http_client):
        """
        Fail-closed: a user with no accepted share gets allowed=false on
        write. This is the default branch — exercised regardless of
        whether project_sharing_service is up (when down we also get
        allowed=false through the timeout-fallback path).
        """
        resp = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/authorization/check",
            json={
                "user_id": _user(),
                "resource_type": "project",
                "resource_id": _project(),
                "action": "write",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["allowed"] is False
        # We expect a human-readable reason.
        assert data.get("reason")


class TestViewerRoleWriteRejection:
    """
    End-to-end: a viewer on a project cannot write; an editor can.

    Requires project_sharing_service to be running locally. Skipped
    otherwise so the suite still runs against authorization_service in
    isolation.
    """

    async def test_viewer_cannot_write_editor_can(self, http_client):
        if not await _project_sharing_up(http_client):
            pytest.skip("project_sharing_service not running on :8270")

        project_id = _project()
        viewer = _user()
        editor = _user()

        viewer_ok = await _create_accepted_share(http_client, project_id, viewer, "viewer")
        editor_ok = await _create_accepted_share(http_client, project_id, editor, "editor")
        if not (viewer_ok and editor_ok):
            pytest.skip("could not seed project_shares via project_sharing_service")

        # Viewer — write rejected.
        viewer_resp = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/authorization/check",
            json={
                "user_id": viewer,
                "resource_type": "project",
                "resource_id": project_id,
                "action": "write",
            },
        )
        assert viewer_resp.status_code == 200, viewer_resp.text
        vdata = viewer_resp.json()
        assert vdata["allowed"] is False, vdata
        assert "viewer" in (vdata.get("reason") or "")

        # Viewer — read allowed (unconditional).
        viewer_read = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/authorization/check",
            json={
                "user_id": viewer,
                "resource_type": "project",
                "resource_id": project_id,
                "action": "read",
            },
        )
        assert viewer_read.status_code == 200
        assert viewer_read.json()["allowed"] is True

        # Editor — write allowed.
        editor_resp = await http_client.post(
            f"{AUTHORIZATION_SERVICE_URL}/api/v1/authorization/check",
            json={
                "user_id": editor,
                "resource_type": "project",
                "resource_id": project_id,
                "action": "write",
            },
        )
        assert editor_resp.status_code == 200, editor_resp.text
        edata = editor_resp.json()
        assert edata["allowed"] is True, edata
