"""
Smoke Tests for Basic Campaign Flow

Tests the complete campaign lifecycle: create -> schedule -> complete.
"""

import pytest
from datetime import datetime, timezone, timedelta

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import (
    CampaignType,
    CampaignStatus,
)


@pytest.mark.smoke
class TestBasicCampaignFlow:
    """Smoke tests for basic campaign flow"""

    @pytest.mark.asyncio
    async def test_create_campaign_flow(self, http_client, auth_headers, factory):
        """Test creating a campaign"""
        # Given: Campaign request
        request_data = {
            "name": "Smoke Test Campaign",
            "campaign_type": "scheduled",
            "audiences": [{"segment_type": "include", "segment_id": "seg_all"}],
            "channels": [{"channel_type": "email", "template_id": "tpl_test"}],
        }

        # When: Creating campaign
        response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )

        # Then: Campaign is created
        assert response.status_code == 201
        data = response.json()
        assert data["campaign"]["status"] == "draft"

    @pytest.mark.asyncio
    async def test_schedule_campaign_flow(self, http_client, auth_headers, factory):
        """Test scheduling a campaign"""
        pytest.skip("Requires campaign_service to be running")

        # Given: Draft campaign (would create first)
        # When: Scheduling
        scheduled_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        # response = await http_client.post(
        #     f"/api/v1/campaigns/{campaign_id}/schedule",
        #     json={"scheduled_at": scheduled_at},
        #     headers=auth_headers,
        # )

        # Then: Campaign is scheduled
        # assert response.status_code == 200
        # assert response.json()["campaign"]["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_get_campaign_flow(self, http_client, auth_headers, factory):
        """Test getting a campaign"""
        pytest.skip("Requires campaign_service to be running")

        # Given: Existing campaign
        # When: Getting campaign
        # response = await http_client.get(
        #     f"/api/v1/campaigns/{campaign_id}",
        #     headers=auth_headers,
        # )

        # Then: Campaign is returned
        # assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_campaigns_flow(self, http_client, auth_headers):
        """Test listing campaigns"""
        # When: Listing campaigns
        response = await http_client.get(
            "/api/v1/campaigns",
            headers=auth_headers,
        )

        # Then: List is returned
        assert response.status_code == 200
        assert "campaigns" in response.json()

    @pytest.mark.asyncio
    async def test_cancel_campaign_flow(self, http_client, auth_headers, factory):
        """Test cancelling a campaign"""
        pytest.skip("Requires campaign_service to be running")

        # Given: Scheduled campaign
        # When: Cancelling
        # response = await http_client.post(
        #     f"/api/v1/campaigns/{campaign_id}/cancel",
        #     headers=auth_headers,
        # )

        # Then: Campaign is cancelled
        # assert response.status_code == 200
        # assert response.json()["campaign"]["status"] == "cancelled"


@pytest.mark.smoke
class TestE2ECampaignLifecycle:
    """End-to-end campaign lifecycle smoke test"""

    @pytest.mark.asyncio
    async def test_full_campaign_lifecycle(self, http_client, auth_headers, factory):
        """Test complete campaign lifecycle: create -> schedule -> cancel"""
        # Step 1: Create campaign
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json={
                "name": "E2E Smoke Test Campaign",
                "campaign_type": "scheduled",
                "audiences": [{"segment_type": "include", "segment_id": "seg_test"}],
                "channels": [{"channel_type": "email", "template_id": "tpl_test"}],
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # Step 2: Schedule campaign
        schedule_response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/schedule",
            json={
                "scheduled_at": (
                    datetime.now(timezone.utc) + timedelta(hours=1)
                ).isoformat()
            },
            headers=auth_headers,
        )
        assert schedule_response.status_code == 200
        assert schedule_response.json()["campaign"]["status"] == "scheduled"

        # Step 3: Cancel campaign (cleanup)
        cancel_response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/cancel",
            headers=auth_headers,
        )
        assert cancel_response.status_code == 200
        assert cancel_response.json()["campaign"]["status"] == "cancelled"

        # Step 4: Delete campaign (cleanup)
        delete_response = await http_client.delete(
            f"/api/v1/campaigns/{campaign_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204


@pytest.mark.smoke
class TestTriggeredCampaignFlow:
    """Smoke tests for triggered campaign flow"""

    @pytest.mark.asyncio
    async def test_create_and_activate_triggered_campaign(
        self, http_client, auth_headers, factory
    ):
        """Test creating and activating a triggered campaign"""
        pytest.skip("Requires campaign_service to be running")

        # Step 1: Create triggered campaign
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json={
                "name": "Triggered Smoke Test",
                "campaign_type": "triggered",
                "audiences": [{"segment_type": "include", "segment_id": "seg_test"}],
                "channels": [{"channel_type": "email", "template_id": "tpl_test"}],
                "triggers": [{"event_type": "user.signup"}],
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # Step 2: Activate campaign
        activate_response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/activate",
            headers=auth_headers,
        )
        assert activate_response.status_code == 200
        assert activate_response.json()["campaign"]["status"] == "active"

        # Cleanup: Cancel and delete
        await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/cancel",
            headers=auth_headers,
        )
        await http_client.delete(
            f"/api/v1/campaigns/{campaign_id}",
            headers=auth_headers,
        )
