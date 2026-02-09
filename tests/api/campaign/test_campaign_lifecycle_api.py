"""
API Tests for Campaign Lifecycle Endpoints

Tests lifecycle endpoints: schedule, activate, pause, resume, cancel.
Reference: logic_contract.md - API Contracts section
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import (
    CampaignType,
    CampaignStatus,
    ScheduleType,
)


@pytest.mark.api
class TestScheduleEndpoint:
    """Tests for POST /api/v1/campaigns/{campaign_id}/schedule"""

    @pytest.mark.asyncio
    async def test_schedule_campaign_success(
        self, http_client, auth_headers, api_helper
    ):
        """Test scheduling campaign returns 200 - BR-CAM-001.2"""
        # Given: Draft scheduled campaign with audiences and channels
        request_data = {
            "name": "Schedule Test Campaign",
            "organization_id": "org_test",
            "campaign_type": "scheduled",
            "created_by": "test_user",
            "audiences": [{"segment_type": "include", "segment_id": "seg_all_users"}],
            "channels": [{"channel_type": "email", "template_id": "tpl_welcome"}],
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # When: POST /api/v1/campaigns/{id}/schedule
        scheduled_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/schedule",
            json={"scheduled_at": scheduled_at, "scheduled_by": "test_user"},
            headers=auth_headers,
        )

        # Then: 200 with scheduled campaign
        api_helper.assert_success(response, 200)
        assert response.json()["campaign"]["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_schedule_past_time_fails(self, http_client, auth_headers, api_helper):
        """Test scheduling for past time returns 400 - BR-CAM-001.2"""
        # Given: Draft campaign with audiences and channels
        request_data = {
            "name": "Past Time Test Campaign",
            "organization_id": "org_test",
            "campaign_type": "scheduled",
            "created_by": "test_user",
            "audiences": [{"segment_type": "include", "segment_id": "seg_all_users"}],
            "channels": [{"channel_type": "email", "template_id": "tpl_welcome"}],
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # When: Scheduling for past time
        past_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/schedule",
            json={"scheduled_at": past_time, "scheduled_by": "test_user"},
            headers=auth_headers,
        )

        # Then: 422 Unprocessable Entity (validation error)
        api_helper.assert_error(response, 422)

    @pytest.mark.asyncio
    async def test_schedule_non_draft_fails(self, http_client, auth_headers, api_helper):
        """Test scheduling non-draft campaign returns 409"""
        # Given: Scheduled campaign (not draft)
        request_data = {
            "name": "Non Draft Test Campaign",
            "organization_id": "org_test",
            "campaign_type": "scheduled",
            "created_by": "test_user",
            "audiences": [{"segment_type": "include", "segment_id": "seg_all_users"}],
            "channels": [{"channel_type": "email", "template_id": "tpl_welcome"}],
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # Schedule it first
        scheduled_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/schedule",
            json={"scheduled_at": scheduled_at, "scheduled_by": "test_user"},
            headers=auth_headers,
        )

        # When: Attempting to schedule again
        new_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/schedule",
            json={"scheduled_at": new_time, "scheduled_by": "test_user"},
            headers=auth_headers,
        )

        # Then: 409 Conflict
        api_helper.assert_error(response, 409)


@pytest.mark.api
class TestActivateEndpoint:
    """Tests for POST /api/v1/campaigns/{campaign_id}/activate"""

    @pytest.mark.asyncio
    async def test_activate_triggered_campaign_success(
        self, http_client, auth_headers, api_helper
    ):
        """Test activating triggered campaign returns 200 - BR-CAM-001.3"""
        # Given: Draft triggered campaign with triggers
        request_data = {
            "name": "Activate Test Campaign",
            "organization_id": "org_test",
            "campaign_type": "triggered",
            "created_by": "test_user",
            "triggers": [
                {
                    "event_type": "user_signup",
                    "conditions": [],
                }
            ],
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # When: POST /api/v1/campaigns/{id}/activate
        response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/activate",
            json={"activated_by": "test_user"},
            headers=auth_headers,
        )

        # Then: 200 with active campaign
        api_helper.assert_success(response, 200)
        assert response.json()["campaign"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_activate_scheduled_campaign_fails(
        self, http_client, auth_headers, api_helper
    ):
        """Test activating scheduled campaign returns 400"""
        # Given: Draft scheduled campaign
        request_data = {
            "name": "Scheduled Activate Test",
            "organization_id": "org_test",
            "campaign_type": "scheduled",
            "created_by": "test_user",
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # When: Attempting to activate
        response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/activate",
            json={"activated_by": "test_user"},
            headers=auth_headers,
        )

        # Then: 400 Bad Request (use schedule instead)
        api_helper.assert_error(response, 400)


@pytest.mark.api
class TestPauseEndpoint:
    """Tests for POST /api/v1/campaigns/{campaign_id}/pause"""

    @pytest.mark.asyncio
    async def test_pause_active_campaign_success(
        self, http_client, auth_headers, api_helper
    ):
        """Test pausing active campaign returns 200 - BR-CAM-001.4"""
        # Given: Active triggered campaign
        request_data = {
            "name": "Pause Test Campaign",
            "organization_id": "org_test",
            "campaign_type": "triggered",
            "created_by": "test_user",
            "triggers": [{"event_type": "user_login", "conditions": []}],
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # Activate the campaign first
        await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/activate",
            json={"activated_by": "test_user"},
            headers=auth_headers,
        )

        # When: POST /api/v1/campaigns/{id}/pause
        response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/pause",
            json={"paused_by": "test_user", "reason": "Testing pause"},
            headers=auth_headers,
        )

        # Then: 200 with paused campaign
        api_helper.assert_success(response, 200)
        assert response.json()["campaign"]["status"] == "paused"

    @pytest.mark.asyncio
    async def test_pause_draft_campaign_fails(
        self, http_client, auth_headers, api_helper
    ):
        """Test pausing draft campaign returns 409"""
        # Given: Draft campaign
        request_data = {
            "name": "Draft Pause Test",
            "organization_id": "org_test",
            "campaign_type": "scheduled",
            "created_by": "test_user",
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # When: Attempting to pause draft
        response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/pause",
            json={"paused_by": "test_user"},
            headers=auth_headers,
        )

        # Then: 409 Conflict
        api_helper.assert_error(response, 409)

    @pytest.mark.asyncio
    async def test_pause_cancelled_campaign_fails(
        self, http_client, auth_headers, api_helper
    ):
        """Test pausing cancelled campaign returns 409"""
        # Given: Cancelled campaign
        request_data = {
            "name": "Cancelled Pause Test",
            "organization_id": "org_test",
            "campaign_type": "triggered",
            "created_by": "test_user",
            "triggers": [{"event_type": "test_event", "conditions": []}],
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # Activate then cancel
        await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/activate",
            json={"activated_by": "test_user"},
            headers=auth_headers,
        )
        await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/cancel",
            json={"cancelled_by": "test_user", "reason": "Testing"},
            headers=auth_headers,
        )

        # When: Attempting to pause cancelled campaign
        response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/pause",
            json={"paused_by": "test_user"},
            headers=auth_headers,
        )

        # Then: 409 Conflict
        api_helper.assert_error(response, 409)


@pytest.mark.api
class TestResumeEndpoint:
    """Tests for POST /api/v1/campaigns/{campaign_id}/resume"""

    @pytest.mark.asyncio
    async def test_resume_paused_campaign_success(
        self, http_client, auth_headers, api_helper
    ):
        """Test resuming paused campaign returns 200 - BR-CAM-001.5"""
        # Given: Paused campaign
        request_data = {
            "name": "Resume Test Campaign",
            "organization_id": "org_test",
            "campaign_type": "triggered",
            "created_by": "test_user",
            "triggers": [{"event_type": "user_action", "conditions": []}],
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # Activate then pause
        await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/activate",
            json={"activated_by": "test_user"},
            headers=auth_headers,
        )
        await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/pause",
            json={"paused_by": "test_user"},
            headers=auth_headers,
        )

        # When: POST /api/v1/campaigns/{id}/resume
        response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/resume",
            json={"resumed_by": "test_user"},
            headers=auth_headers,
        )

        # Then: 200 with active campaign
        api_helper.assert_success(response, 200)
        assert response.json()["campaign"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_resume_non_paused_fails(
        self, http_client, auth_headers, api_helper
    ):
        """Test resuming non-paused campaign returns 409"""
        # Given: Active (not paused) campaign
        request_data = {
            "name": "Non-Paused Resume Test",
            "organization_id": "org_test",
            "campaign_type": "triggered",
            "created_by": "test_user",
            "triggers": [{"event_type": "some_event", "conditions": []}],
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # Activate without pausing
        await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/activate",
            json={"activated_by": "test_user"},
            headers=auth_headers,
        )

        # When: Attempting to resume active (not paused) campaign
        response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/resume",
            json={"resumed_by": "test_user"},
            headers=auth_headers,
        )

        # Then: 409 Conflict
        api_helper.assert_error(response, 409)


@pytest.mark.api
class TestCancelEndpoint:
    """Tests for POST /api/v1/campaigns/{campaign_id}/cancel"""

    @pytest.mark.asyncio
    async def test_cancel_scheduled_campaign_success(
        self, http_client, auth_headers, api_helper
    ):
        """Test cancelling scheduled campaign returns 200 - BR-CAM-001.6"""
        # Given: Scheduled campaign
        request_data = {
            "name": "Cancel Scheduled Test",
            "organization_id": "org_test",
            "campaign_type": "scheduled",
            "created_by": "test_user",
            "audiences": [{"segment_type": "include", "segment_id": "seg_all_users"}],
            "channels": [{"channel_type": "email", "template_id": "tpl_welcome"}],
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # Schedule it
        scheduled_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/schedule",
            json={"scheduled_at": scheduled_at, "scheduled_by": "test_user"},
            headers=auth_headers,
        )

        # When: POST /api/v1/campaigns/{id}/cancel
        response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/cancel",
            json={"cancelled_by": "test_user", "reason": "No longer needed"},
            headers=auth_headers,
        )

        # Then: 200 with cancelled campaign
        api_helper.assert_success(response, 200)
        assert response.json()["campaign"]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_active_campaign_success(
        self, http_client, auth_headers, api_helper
    ):
        """Test cancelling active campaign returns 200 - BR-CAM-001.6"""
        # Given: Active campaign
        request_data = {
            "name": "Cancel Active Test",
            "organization_id": "org_test",
            "campaign_type": "triggered",
            "created_by": "test_user",
            "triggers": [{"event_type": "cancel_test", "conditions": []}],
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # Activate
        await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/activate",
            json={"activated_by": "test_user"},
            headers=auth_headers,
        )

        # When: POST /api/v1/campaigns/{id}/cancel
        response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/cancel",
            json={"cancelled_by": "test_user", "reason": "Strategy change"},
            headers=auth_headers,
        )

        # Then: 200 with cancelled campaign
        api_helper.assert_success(response, 200)
        assert response.json()["campaign"]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_draft_campaign_success(
        self, http_client, auth_headers, api_helper
    ):
        """Test cancelling draft campaign returns 200"""
        # Given: Draft campaign
        request_data = {
            "name": "Cancel Draft Test",
            "organization_id": "org_test",
            "campaign_type": "scheduled",
            "created_by": "test_user",
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # When: POST /api/v1/campaigns/{id}/cancel
        response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/cancel",
            json={"cancelled_by": "test_user", "reason": "Changed plans"},
            headers=auth_headers,
        )

        # Then: 200 with cancelled campaign
        api_helper.assert_success(response, 200)
        assert response.json()["campaign"]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled_fails(
        self, http_client, auth_headers, api_helper
    ):
        """Test cancelling already cancelled campaign returns 409"""
        # Given: Cancelled campaign
        request_data = {
            "name": "Double Cancel Test",
            "organization_id": "org_test",
            "campaign_type": "scheduled",
            "created_by": "test_user",
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # Cancel it
        await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/cancel",
            json={"cancelled_by": "test_user", "reason": "First cancel"},
            headers=auth_headers,
        )

        # When: Attempting to cancel again
        response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/cancel",
            json={"cancelled_by": "test_user", "reason": "Second cancel"},
            headers=auth_headers,
        )

        # Then: 409 Conflict
        api_helper.assert_error(response, 409)


@pytest.mark.api
class TestCloneEndpoint:
    """Tests for POST /api/v1/campaigns/{campaign_id}/clone"""

    @pytest.mark.asyncio
    async def test_clone_campaign_success(
        self, http_client, auth_headers, api_helper
    ):
        """Test cloning campaign returns 201"""
        # Given: Existing campaign
        request_data = {
            "name": "Original Campaign",
            "organization_id": "org_test",
            "campaign_type": "scheduled",
            "created_by": "test_user",
            "description": "Original description",
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        campaign_id = create_response.json()["campaign"]["campaign_id"]

        # When: POST /api/v1/campaigns/{id}/clone
        response = await http_client.post(
            f"/api/v1/campaigns/{campaign_id}/clone",
            json={"name": "Cloned Campaign"},
            headers=auth_headers,
        )

        # Then: 201 with new campaign in draft status
        api_helper.assert_success(response, 201)
        cloned = response.json()["campaign"]
        assert cloned["status"] == "draft"
        assert cloned["name"] == "Cloned Campaign"

    @pytest.mark.asyncio
    async def test_clone_generates_new_id(
        self, http_client, auth_headers, api_helper
    ):
        """Test cloned campaign has new ID"""
        # Given: Existing campaign
        request_data = {
            "name": "Source Campaign",
            "organization_id": "org_test",
            "campaign_type": "scheduled",
            "created_by": "test_user",
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        original_id = create_response.json()["campaign"]["campaign_id"]

        # When: Cloning
        response = await http_client.post(
            f"/api/v1/campaigns/{original_id}/clone",
            json={"new_name": "New Clone", "cloned_by": "test_user"},
            headers=auth_headers,
        )

        # Then: New campaign has different ID
        api_helper.assert_success(response, 201)
        cloned_id = response.json()["campaign"]["campaign_id"]
        assert cloned_id != original_id

    @pytest.mark.asyncio
    async def test_clone_references_original(
        self, http_client, auth_headers, api_helper
    ):
        """Test cloned campaign references original via cloned_from_id"""
        # Given: Existing campaign
        request_data = {
            "name": "Parent Campaign",
            "organization_id": "org_test",
            "campaign_type": "triggered",
            "created_by": "test_user",
        }
        create_response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )
        api_helper.assert_success(create_response, 201)
        original_id = create_response.json()["campaign"]["campaign_id"]

        # When: Cloning
        response = await http_client.post(
            f"/api/v1/campaigns/{original_id}/clone",
            json={"new_name": "Child Campaign", "cloned_by": "test_user"},
            headers=auth_headers,
        )

        # Then: cloned_from_id references original
        api_helper.assert_success(response, 201)
        cloned = response.json()["campaign"]
        assert cloned.get("cloned_from_id") == original_id
