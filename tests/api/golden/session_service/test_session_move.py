"""
Session Service — PATCH /api/v1/sessions/{session_id} move tests (Story 8).

Covers the metadata.project_id move flow added in Story 8 of #442:
- moving a session into a project sets metadata.project_id
- passing project_id=null removes the key from metadata
- moving a session between projects overwrites the previous id
- wrong user_id returns 404 (does not leak existence)
- nonexistent session returns 404

These are golden HTTP tests against the running session_service.
"""

import uuid

import pytest

from tests.api.conftest import APIAssertions, APIClient

pytestmark = [pytest.mark.api, pytest.mark.golden, pytest.mark.asyncio]


def _user() -> str:
    return f"api_test_{uuid.uuid4().hex[:12]}"


def _project() -> str:
    # project_id is stored as a JSON string in metadata, so any opaque
    # token works for these tests.
    return f"proj_{uuid.uuid4().hex[:16]}"


async def _create_session(session_api: APIClient, user_id: str) -> str:
    """Create a session and return its session_id."""
    resp = await session_api.post("", json={"user_id": user_id})
    assert resp.status_code in (200, 201), f"create_session failed: {resp.text}"
    return resp.json()["session_id"]


class TestSessionMovePATCH:
    """PATCH /api/v1/sessions/{session_id} — move into/out of project."""

    async def test_move_into_project_sets_metadata_project_id(self, session_api: APIClient, api_assert: APIAssertions):
        """PATCH with project_id sets metadata.project_id on the session."""
        user_id = _user()
        project_id = _project()
        session_id = await _create_session(session_api, user_id)

        resp = await session_api.client.patch(
            f"{session_api.url}/{session_id}",
            json={"user_id": user_id, "project_id": project_id},
        )
        api_assert.assert_success(resp)
        data = resp.json()
        assert data["session_id"] == session_id
        assert data["metadata"].get("project_id") == project_id

        # Read-back via GET confirms the persisted state.
        get_resp = await session_api.get(f"/{session_id}?user_id={user_id}")
        api_assert.assert_success(get_resp)
        assert get_resp.json()["metadata"].get("project_id") == project_id

    async def test_move_out_of_project_with_null_removes_key(self, session_api: APIClient, api_assert: APIAssertions):
        """PATCH with project_id=null removes metadata.project_id entirely."""
        user_id = _user()
        project_id = _project()
        session_id = await _create_session(session_api, user_id)

        # First put it into a project.
        first = await session_api.client.patch(
            f"{session_api.url}/{session_id}",
            json={"user_id": user_id, "project_id": project_id},
        )
        api_assert.assert_success(first)
        assert first.json()["metadata"].get("project_id") == project_id

        # Then move it out by passing null.
        second = await session_api.client.patch(
            f"{session_api.url}/{session_id}",
            json={"user_id": user_id, "project_id": None},
        )
        api_assert.assert_success(second)
        # Key should be missing (not present as null) so the frontend
        # can distinguish "never assigned" from "explicitly cleared".
        assert "project_id" not in second.json().get("metadata", {})

    async def test_move_between_projects_overwrites(self, session_api: APIClient, api_assert: APIAssertions):
        """PATCH twice with different project_ids overwrites the value."""
        user_id = _user()
        proj_a = _project()
        proj_b = _project()
        session_id = await _create_session(session_api, user_id)

        a = await session_api.client.patch(
            f"{session_api.url}/{session_id}",
            json={"user_id": user_id, "project_id": proj_a},
        )
        api_assert.assert_success(a)
        assert a.json()["metadata"].get("project_id") == proj_a

        b = await session_api.client.patch(
            f"{session_api.url}/{session_id}",
            json={"user_id": user_id, "project_id": proj_b},
        )
        api_assert.assert_success(b)
        assert b.json()["metadata"].get("project_id") == proj_b

    async def test_move_wrong_user_returns_404(self, session_api: APIClient, api_assert: APIAssertions):
        """PATCH with a user_id that doesn't own the session returns 404 (no leak)."""
        owner = _user()
        other = _user()
        session_id = await _create_session(session_api, owner)

        resp = await session_api.client.patch(
            f"{session_api.url}/{session_id}",
            json={"user_id": other, "project_id": _project()},
        )
        api_assert.assert_not_found(resp)

    async def test_move_nonexistent_session_returns_404(self, session_api: APIClient, api_assert: APIAssertions):
        """PATCH on a nonexistent session returns 404."""
        sid = f"sess_missing_{uuid.uuid4().hex[:12]}"
        resp = await session_api.client.patch(
            f"{session_api.url}/{sid}",
            json={"user_id": _user(), "project_id": _project()},
        )
        api_assert.assert_not_found(resp)
