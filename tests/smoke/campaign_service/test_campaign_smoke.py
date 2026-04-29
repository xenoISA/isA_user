"""
Campaign Service — Smoke tests for campaign CRUD and lifecycle.

Port: 8251 (SERVICE_PORT env var)
Routes: /api/v1/campaigns/...
"""

import uuid

import httpx
import pytest

from tests.smoke.conftest import resolve_base_url, resolve_service_url

pytestmark = pytest.mark.smoke

BASE_URL = resolve_base_url("campaign_service", "CAMPAIGN_SERVICE_URL")
HEALTH_URL = resolve_service_url("campaign_service", "/health", "CAMPAIGN_SERVICE_URL")
API_HEALTH_URL = f"{BASE_URL}/api/v1/campaigns/health"
TIMEOUT = 15.0

INTERNAL_HEADERS = {
    "X-Internal-Call": "true",
    "X-Internal-Service": "true",
    "X-Internal-Service-Secret": "dev-internal-secret-change-in-production",
    "user-id": "smoke-test-user",
}

_state: dict = {}


class TestCampaignHealthSmoke:
    @pytest.mark.asyncio
    async def test_health(self):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(HEALTH_URL)
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_api_health_alias(self):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(API_HEALTH_URL)
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_response_shape(self):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(HEALTH_URL)
            assert resp.status_code == 200
            data = resp.json()
            assert "status" in data or "service" in data


class TestCampaignCRUDSmoke:
    @pytest.mark.asyncio
    async def test_create_campaign(self):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/campaigns",
                headers=INTERNAL_HEADERS,
                json={
                    "name": f"Smoke Test Campaign {uuid.uuid4().hex[:6]}",
                    "type": "one_time",
                    "channel": "email",
                    "description": "Created by smoke test",
                },
            )
            assert resp.status_code in (
                200,
                201,
            ), f"Create failed: {resp.status_code} {resp.text[:200]}"
            data = resp.json()
            _state["campaign_id"] = data.get("id") or data.get("campaign_id")
            assert _state["campaign_id"]

    @pytest.mark.asyncio
    async def test_get_campaign(self):
        cid = _state.get("campaign_id")
        if not cid:
            pytest.skip("No campaign created")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/api/v1/campaigns/{cid}",
                headers=INTERNAL_HEADERS,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("id") == cid or data.get("campaign_id") == cid

    @pytest.mark.asyncio
    async def test_list_campaigns(self):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/api/v1/campaigns",
                headers=INTERNAL_HEADERS,
                params={"limit": 5},
            )
            assert resp.status_code == 200
            data = resp.json()
            # List response — array or object with items
            items = (
                data
                if isinstance(data, list)
                else data.get("items", data.get("campaigns", []))
            )
            assert isinstance(items, list)

    @pytest.mark.asyncio
    async def test_update_campaign(self):
        cid = _state.get("campaign_id")
        if not cid:
            pytest.skip("No campaign created")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.patch(
                f"{BASE_URL}/api/v1/campaigns/{cid}",
                headers=INTERNAL_HEADERS,
                json={"description": "Updated by smoke test"},
            )
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_clone_campaign(self):
        cid = _state.get("campaign_id")
        if not cid:
            pytest.skip("No campaign created")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/campaigns/{cid}/clone",
                headers=INTERNAL_HEADERS,
                json={"name": f"Cloned Smoke {uuid.uuid4().hex[:4]}"},
            )
            assert resp.status_code in (200, 201)
            clone_data = resp.json()
            _state["cloned_id"] = clone_data.get("id") or clone_data.get("campaign_id")

    @pytest.mark.asyncio
    async def test_delete_campaign(self):
        cid = _state.get("campaign_id")
        if not cid:
            pytest.skip("No campaign created")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.delete(
                f"{BASE_URL}/api/v1/campaigns/{cid}",
                headers=INTERNAL_HEADERS,
            )
            assert resp.status_code in (200, 204)

        # Clean up clone too
        clone_id = _state.get("cloned_id")
        if clone_id:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                await client.delete(
                    f"{BASE_URL}/api/v1/campaigns/{clone_id}",
                    headers=INTERNAL_HEADERS,
                )


class TestCampaignLifecycleSmoke:
    @pytest.mark.asyncio
    async def test_schedule_campaign(self):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Create a campaign to schedule
            create = await client.post(
                f"{BASE_URL}/api/v1/campaigns",
                headers=INTERNAL_HEADERS,
                json={
                    "name": f"Schedule Smoke {uuid.uuid4().hex[:6]}",
                    "type": "one_time",
                    "channel": "email",
                },
            )
            if create.status_code not in (200, 201):
                pytest.skip("Cannot create campaign for lifecycle test")

            cid = create.json().get("id") or create.json().get("campaign_id")
            resp = await client.post(
                f"{BASE_URL}/api/v1/campaigns/{cid}/schedule",
                headers=INTERNAL_HEADERS,
                json={"timezone": "UTC"},
            )
            assert resp.status_code in (200, 400, 422)  # 400/422 if missing content

            # Cleanup
            await client.delete(
                f"{BASE_URL}/api/v1/campaigns/{cid}",
                headers=INTERNAL_HEADERS,
            )

    @pytest.mark.asyncio
    async def test_get_metrics(self):
        cid = _state.get("campaign_id") or "nonexistent"
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/api/v1/campaigns/{cid}/metrics",
                headers=INTERNAL_HEADERS,
            )
            # 200 if campaign exists, 404 if not
            assert resp.status_code in (200, 404)
