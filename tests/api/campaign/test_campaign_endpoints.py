"""
API Tests for Campaign CRUD Endpoints

Tests all campaign CRUD endpoints with real HTTP requests.
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
    ChannelType,
    SegmentType,
)


@pytest.mark.api
class TestCreateCampaignEndpoint:
    """Tests for POST /api/v1/campaigns"""

    @pytest.mark.asyncio
    async def test_create_campaign_success(
        self, http_client, auth_headers, factory, api_helper, cleaner
    ):
        """Test creating campaign returns 201"""
        # Given: Valid campaign request
        request_data = {
            "name": "API Test Campaign",
            "organization_id": "org_test",
            "campaign_type": "scheduled",
            "created_by": "test_user",
            "audiences": [{"segment_type": "include", "segment_id": "seg_all_users"}],
            "channels": [
                {
                    "channel_type": "email",
                    "template_id": "tpl_welcome",
                }
            ],
        }

        # When: POST /api/v1/campaigns
        response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )

        # Then: 201 Created
        api_helper.assert_success(response, 201)
        data = response.json()
        assert data["campaign"]["name"] == "API Test Campaign"
        assert data["campaign"]["status"] == "draft"

        # Track for cleanup
        if "campaign" in data and "campaign_id" in data["campaign"]:
            cleaner.track(data["campaign"]["campaign_id"])

    @pytest.mark.asyncio
    async def test_create_campaign_missing_name(
        self, http_client, auth_headers, api_helper
    ):
        """Test creating campaign without name returns 422"""
        # Given: Request without name
        request_data = {
            "campaign_type": "scheduled",
            "organization_id": "org_test",
            "created_by": "test_user",
        }

        # When: POST /api/v1/campaigns
        response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )

        # Then: 422 Unprocessable Entity
        api_helper.assert_error(response, 422)

    @pytest.mark.asyncio
    async def test_create_campaign_invalid_type(
        self, http_client, auth_headers, api_helper
    ):
        """Test creating campaign with invalid type returns 422"""
        # Given: Request with invalid type
        request_data = {
            "name": "Test Campaign",
            "organization_id": "org_test",
            "created_by": "test_user",
            "campaign_type": "invalid_type",
        }

        # When: POST /api/v1/campaigns
        response = await http_client.post(
            "/api/v1/campaigns",
            json=request_data,
            headers=auth_headers,
        )

        # Then: 422 Unprocessable Entity
        api_helper.assert_error(response, 422)


@pytest.mark.api
class TestGetCampaignEndpoint:
    """Tests for GET /api/v1/campaigns/{campaign_id}"""

    @pytest.mark.asyncio
    async def test_get_campaign_success(self, http_client, auth_headers, api_helper):
        """Test getting campaign returns 200"""
        # Given: Create a campaign first
        request_data = {
            "name": "Get Test Campaign",
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

        # When: GET /api/v1/campaigns/{campaign_id}
        response = await http_client.get(
            f"/api/v1/campaigns/{campaign_id}",
            headers=auth_headers,
        )

        # Then: 200 with campaign data
        api_helper.assert_success(response, 200)
        assert response.json()["campaign"]["campaign_id"] == campaign_id

    @pytest.mark.asyncio
    async def test_get_campaign_not_found(self, http_client, auth_headers, api_helper):
        """Test getting non-existent campaign returns 404"""
        # When: GET /api/v1/campaigns/cmp_nonexistent
        response = await http_client.get(
            "/api/v1/campaigns/cmp_nonexistent",
            headers=auth_headers,
        )

        # Then: 404 Not Found
        api_helper.assert_error(response, 404)


@pytest.mark.api
class TestListCampaignsEndpoint:
    """Tests for GET /api/v1/campaigns"""

    @pytest.mark.asyncio
    async def test_list_campaigns_success(self, http_client, auth_headers, api_helper):
        """Test listing campaigns returns 200"""
        # When: GET /api/v1/campaigns
        response = await http_client.get(
            "/api/v1/campaigns",
            headers=auth_headers,
        )

        # Then: 200 with list
        api_helper.assert_success(response, 200)
        data = response.json()
        assert "campaigns" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

    @pytest.mark.asyncio
    async def test_list_campaigns_with_filters(
        self, http_client, auth_headers, api_helper
    ):
        """Test listing campaigns with status filter"""
        # When: GET /api/v1/campaigns?status=draft
        response = await http_client.get(
            "/api/v1/campaigns",
            params={"status": "draft"},
            headers=auth_headers,
        )

        # Then: 200 with filtered list
        api_helper.assert_success(response, 200)

    @pytest.mark.asyncio
    async def test_list_campaigns_pagination(
        self, http_client, auth_headers, api_helper
    ):
        """Test listing campaigns with pagination"""
        # When: GET /api/v1/campaigns?limit=10&offset=0
        response = await http_client.get(
            "/api/v1/campaigns",
            params={"limit": 10, "offset": 0},
            headers=auth_headers,
        )

        # Then: 200 with correct pagination
        api_helper.assert_success(response, 200)
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0


@pytest.mark.api
class TestUpdateCampaignEndpoint:
    """Tests for PATCH /api/v1/campaigns/{campaign_id}"""

    @pytest.mark.asyncio
    async def test_update_campaign_success(self, http_client, auth_headers, api_helper):
        """Test updating campaign returns 200"""
        # Given: Create a draft campaign first
        request_data = {
            "name": "Update Test Campaign",
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

        # When: PATCH /api/v1/campaigns/{campaign_id}
        response = await http_client.patch(
            f"/api/v1/campaigns/{campaign_id}",
            json={"name": "Updated Campaign Name", "updated_by": "test_user"},
            headers=auth_headers,
        )

        # Then: 200 with updated campaign
        api_helper.assert_success(response, 200)
        assert response.json()["campaign"]["name"] == "Updated Campaign Name"

    @pytest.mark.asyncio
    async def test_update_campaign_not_found(
        self, http_client, auth_headers, api_helper
    ):
        """Test updating non-existent campaign returns 404"""
        # When: PATCH /api/v1/campaigns/cmp_nonexistent
        response = await http_client.patch(
            "/api/v1/campaigns/cmp_nonexistent",
            json={"name": "New Name"},
            headers=auth_headers,
        )

        # Then: 404 Not Found
        api_helper.assert_error(response, 404)


@pytest.mark.api
class TestDeleteCampaignEndpoint:
    """Tests for DELETE /api/v1/campaigns/{campaign_id}"""

    @pytest.mark.asyncio
    async def test_delete_campaign_success(self, http_client, auth_headers, api_helper):
        """Test deleting campaign returns 200"""
        # Given: Create a campaign to delete
        request_data = {
            "name": "Delete Test Campaign",
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

        # When: DELETE /api/v1/campaigns/{campaign_id}
        response = await http_client.delete(
            f"/api/v1/campaigns/{campaign_id}",
            headers=auth_headers,
        )

        # Then: 204 No Content (REST standard for successful DELETE)
        api_helper.assert_success(response, 204)

    @pytest.mark.asyncio
    async def test_delete_campaign_not_found(
        self, http_client, auth_headers, api_helper
    ):
        """Test deleting non-existent campaign returns 404"""
        # When: DELETE /api/v1/campaigns/cmp_nonexistent
        response = await http_client.delete(
            "/api/v1/campaigns/cmp_nonexistent",
            headers=auth_headers,
        )

        # Then: 404 Not Found
        api_helper.assert_error(response, 404)
