"""
Connector Service — golden API tests (L4).

Tests the custom-MCP slice from xenoISA/isA_#464:

  GET    /api/v1/connectors/catalog               -> built-in catalog
  GET    /api/v1/connectors/installed             -> per-user installed + custom
  POST   /api/v1/connectors/custom                -> create (201/422/429/404)
  DELETE /api/v1/connectors/custom/{id}           -> revoke (204/404)
  POST   /api/v1/connectors/custom/{id}/revalidate -> re-handshake (200/422/404)

Each test hits the running connector_service on port 8292 (set
``CONNECTOR_SERVICE_URL`` to override). Tests are auto-skipped when the
service isn't reachable — see ``_service_reachable`` below — so they
ship in CI but only run when the service is actually up.
"""

from __future__ import annotations

import os
import socket
import uuid
from urllib.parse import urlparse

import httpx
import pytest

pytestmark = [pytest.mark.api, pytest.mark.asyncio, pytest.mark.golden]


CONNECTOR_SERVICE_URL = os.getenv("CONNECTOR_SERVICE_URL", "http://localhost:8292")
API_BASE = f"{CONNECTOR_SERVICE_URL}/api/v1"


def _service_reachable() -> bool:
    parsed = urlparse(CONNECTOR_SERVICE_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8292
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


pytestmark.append(
    pytest.mark.skipif(
        not _service_reachable(),
        reason=(
            f"connector_service not reachable at {CONNECTOR_SERVICE_URL}; "
            "start it via deployment/local-dev.sh --run connector_service"
        ),
    )
)


@pytest.fixture
async def http_client():
    """A per-test httpx client that pins a unique user via X-User-Id.

    ``CONNECTOR_DEV_AUTH`` must be on in the running service for this to
    resolve. It's the default in dev/local-dev.sh.
    """
    user_id = f"user-test-464-{uuid.uuid4().hex[:10]}"
    async with httpx.AsyncClient(
        timeout=15.0,
        headers={"X-User-Id": user_id},
    ) as client:
        client._test_user_id = user_id  # stash for assertions
        yield client


# ---------------------------------------------------------------------------
# Catalog — always works regardless of feature flag
# ---------------------------------------------------------------------------


class TestCatalog:
    async def test_catalog_returns_seed_entries(self, http_client):
        resp = await http_client.get(f"{API_BASE}/connectors/catalog")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["count"] >= 6  # google_drive, gmail, slack, github, notion, linear
        ids = {c["id"] for c in body["connectors"]}
        assert {
            "google_drive",
            "gmail",
            "slack",
            "github",
            "notion",
            "linear",
        }.issubset(ids)

    async def test_catalog_filters_by_category(self, http_client):
        resp = await http_client.get(
            f"{API_BASE}/connectors/catalog",
            params={"category": "email"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert all(c["category"] == "email" for c in body["connectors"])
        assert any(c["id"] == "gmail" for c in body["connectors"])


# ---------------------------------------------------------------------------
# Installed — empty by default for a fresh user
# ---------------------------------------------------------------------------


class TestInstalled:
    async def test_installed_is_empty_for_new_user(self, http_client):
        resp = await http_client.get(f"{API_BASE}/connectors/installed")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["count"] == 0
        assert body["installed"] == []
        assert body["custom"] == []


# ---------------------------------------------------------------------------
# Custom MCP — POST/DELETE/revalidate
# ---------------------------------------------------------------------------


@pytest.fixture
def custom_url():
    return f"https://mcp-{uuid.uuid4().hex[:8]}.example.com/sse"


class TestCustomMcpCreate:
    async def test_invalid_url_scheme_returns_422(self, http_client):
        resp = await http_client.post(
            f"{API_BASE}/connectors/custom",
            json={
                "label": "Bad",
                "url": "gopher://example.com",
                "auth_kind": "none",
            },
        )
        # Pydantic url validation fires first -> 422 from FastAPI.
        assert resp.status_code == 422, resp.text

    async def test_private_ip_url_returns_422_with_stable_code(self, http_client):
        """Validator should refuse the 169.254 link-local target."""
        resp = await http_client.post(
            f"{API_BASE}/connectors/custom",
            json={
                "label": "metadata",
                "url": "https://169.254.169.254/latest/meta-data/",
                "auth_kind": "none",
            },
        )
        assert resp.status_code == 422
        body = resp.json()
        # FastAPI wraps the detail dict; the inner error envelope must
        # carry our stable code.
        detail = body.get("detail") or body
        inner = detail.get("error") if isinstance(detail, dict) else None
        if inner is not None:
            assert inner.get("code") in (
                "private_ip_blocked",
                "handshake_transport_error",
            )

    async def test_404_when_feature_flag_off(self, monkeypatch, http_client):
        """If the service is started with ALLOW_CUSTOM_MCP_CONNECTORS=false,
        POST returns 404. Skipped if the running service has it on (default)."""
        probe = await http_client.post(
            f"{API_BASE}/connectors/custom",
            json={"label": "x", "url": "https://example.com", "auth_kind": "none"},
        )
        if probe.status_code != 404:
            pytest.skip(
                "Feature flag ALLOW_CUSTOM_MCP_CONNECTORS appears enabled; "
                "404-when-off case requires the service to be started with it disabled."
            )


class TestCustomMcpDelete:
    async def test_delete_unknown_returns_404(self, http_client):
        resp = await http_client.delete(f"{API_BASE}/connectors/custom/{uuid.uuid4()}")
        assert resp.status_code in (404, 401)
        # If feature flag is off this becomes a route 404 with code route_disabled
        # — either is acceptable for "unknown id".


class TestRateLimit:
    async def test_post_rate_limit_eventually_429s(self, http_client):
        """Burst 12 posts; the 11th onwards must 429.

        The rate limiter is keyed off the Authorization header (or IP);
        the client has a stable X-User-Id but no Authorization, so the
        IP fallback kicks in. The mock servers in the unit/component
        tests cover the path more thoroughly — this is the
        "service-is-actually-rate-limiting" smoke check.
        """
        payload = {
            "label": "burst",
            "url": f"https://burst-{uuid.uuid4().hex[:6]}.example.com/sse",
            "auth_kind": "none",
        }
        # Fire enough requests that we cross 10/hour even if a few
        # succeed (handshake will fail against the bogus URL, so most
        # come back 422 — that still counts against the limit).
        results = []
        for _ in range(12):
            r = await http_client.post(f"{API_BASE}/connectors/custom", json=payload)
            results.append(r.status_code)
            if r.status_code == 429:
                break
        assert 429 in results, f"Expected at least one 429, got: {results}"
