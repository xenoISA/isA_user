"""
Project Service — star / archive routes (#442).

Layer 4 (api) — real HTTP against the running project_service on port 8260.
Pairs with design xenoISA/isA_#429 §15.3 (star) and §15.6 (archive).

Covered routes
--------------
- POST   /api/v1/projects/{id}/star
- DELETE /api/v1/projects/{id}/star
- POST   /api/v1/projects/{id}/archive
- POST   /api/v1/projects/{id}/unarchive
- GET    /api/v1/projects?include_archived=…&starred_only=…

The tests authenticate as "internal-service" using the dev-default secret
shipped in core/auth_dependencies.py — same pattern as
test_memory_phase2_routes.py.
"""

from __future__ import annotations

import os
import uuid
from typing import AsyncGenerator

import httpx
import pytest

pytestmark = [pytest.mark.api, pytest.mark.asyncio, pytest.mark.golden]

PROJECT_SERVICE_URL = os.getenv("PROJECT_SERVICE_URL", "http://localhost:8260")
API_BASE = f"{PROJECT_SERVICE_URL}/api/v1"

INTERNAL_SERVICE_SECRET = os.getenv(
    "INTERNAL_SERVICE_SECRET",
    "dev-internal-secret-change-in-production",
)


@pytest.fixture
def internal_headers() -> dict:
    return {
        "X-Internal-Service": "true",
        "X-Internal-Service-Secret": INTERNAL_SERVICE_SECRET,
        "Content-Type": "application/json",
    }


@pytest.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        yield client


@pytest.fixture
def fresh_user_id() -> str:
    """Each test gets a unique user_id so list-scoping doesn't bleed."""
    return f"test-442-{uuid.uuid4().hex[:10]}"


async def _create_project(
    http_client: httpx.AsyncClient,
    headers: dict,
    name: str = "p",
) -> dict:
    resp = await http_client.post(
        f"{API_BASE}/projects",
        headers=headers,
        json={"name": name},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestStarUnstar:
    async def test_star_sets_starred_at_and_returns_project(self, http_client, internal_headers):
        project = await _create_project(http_client, internal_headers, name="alpha")
        assert project["starred_at"] is None

        resp = await http_client.post(
            f"{API_BASE}/projects/{project['id']}/star",
            headers=internal_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"] == project["id"]
        assert body["starred_at"] is not None

    async def test_unstar_clears_starred_at(self, http_client, internal_headers):
        project = await _create_project(http_client, internal_headers, name="beta")
        await http_client.post(f"{API_BASE}/projects/{project['id']}/star", headers=internal_headers)

        resp = await http_client.delete(
            f"{API_BASE}/projects/{project['id']}/star",
            headers=internal_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["starred_at"] is None


class TestArchiveUnarchive:
    async def test_archive_sets_archived_at(self, http_client, internal_headers):
        project = await _create_project(http_client, internal_headers, name="gamma")
        assert project["archived_at"] is None

        resp = await http_client.post(
            f"{API_BASE}/projects/{project['id']}/archive",
            headers=internal_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["archived_at"] is not None

    async def test_unarchive_clears_archived_at(self, http_client, internal_headers):
        project = await _create_project(http_client, internal_headers, name="delta")
        await http_client.post(f"{API_BASE}/projects/{project['id']}/archive", headers=internal_headers)

        resp = await http_client.post(
            f"{API_BASE}/projects/{project['id']}/unarchive",
            headers=internal_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["archived_at"] is None

    async def test_archive_attempts_share_revocation_gracefully(self, http_client, internal_headers):
        """Archive must succeed even if project_sharing_service is unreachable
        (graceful degradation — archived_at is source of truth, design §15.6).

        We don't assert a network call was made — that's an internal detail —
        only that the archive succeeds with no sharing_service running.
        """
        project = await _create_project(http_client, internal_headers, name="epsilon")
        resp = await http_client.post(
            f"{API_BASE}/projects/{project['id']}/archive",
            headers=internal_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["archived_at"] is not None


class TestListFilters:
    async def test_archived_projects_hidden_by_default(self, http_client, internal_headers):
        # Use a fresh internal-service caller so previous test data doesn't
        # interfere. internal-service is the caller id regardless of user, so
        # we scope by checking that our specific project drops out of the list.
        active = await _create_project(http_client, internal_headers, name="active-one")
        archived = await _create_project(http_client, internal_headers, name="to-archive")
        await http_client.post(
            f"{API_BASE}/projects/{archived['id']}/archive",
            headers=internal_headers,
        )

        resp = await http_client.get(
            f"{API_BASE}/projects",
            headers=internal_headers,
            params={"limit": 100},
        )
        assert resp.status_code == 200, resp.text
        ids = {p["id"] for p in resp.json()["projects"]}
        assert active["id"] in ids
        assert archived["id"] not in ids

    async def test_archived_projects_visible_when_include_archived_true(self, http_client, internal_headers):
        archived = await _create_project(http_client, internal_headers, name="include-me")
        await http_client.post(
            f"{API_BASE}/projects/{archived['id']}/archive",
            headers=internal_headers,
        )

        resp = await http_client.get(
            f"{API_BASE}/projects",
            headers=internal_headers,
            params={"limit": 100, "include_archived": "true"},
        )
        assert resp.status_code == 200, resp.text
        ids = {p["id"] for p in resp.json()["projects"]}
        assert archived["id"] in ids

    async def test_starred_only_filter_returns_only_starred(self, http_client, internal_headers):
        starred = await _create_project(http_client, internal_headers, name="favourite")
        unstarred = await _create_project(http_client, internal_headers, name="meh")
        await http_client.post(f"{API_BASE}/projects/{starred['id']}/star", headers=internal_headers)

        resp = await http_client.get(
            f"{API_BASE}/projects",
            headers=internal_headers,
            params={"limit": 100, "starred_only": "true"},
        )
        assert resp.status_code == 200, resp.text
        projects = resp.json()["projects"]
        ids = {p["id"] for p in projects}
        assert starred["id"] in ids
        assert unstarred["id"] not in ids
        # Sanity: every row in starred_only response must actually be starred
        assert all(p.get("starred_at") is not None for p in projects)


class TestOwnerId:
    async def test_created_project_records_owner_id(self, http_client, internal_headers):
        """owner_id should be populated automatically from the authenticated
        caller (story 7 of #442 — back-fill is a separate data migration)."""
        project = await _create_project(http_client, internal_headers, name="zeta")

        # Re-fetch via GET to read the persisted record (POST body is
        # constructed in-memory and may not echo every column).
        resp = await http_client.get(
            f"{API_BASE}/projects/{project['id']}",
            headers=internal_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # owner_id is present and non-null (its precise value depends on the
        # auth model — internal-service callers get "internal-service").
        assert "owner_id" in body
        assert body["owner_id"] is not None
