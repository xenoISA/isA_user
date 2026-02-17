"""
Component Tests for CampaignService Class

Tests the core CampaignService business logic with mocked dependencies.
Reference: BR-CAM-001 (Campaign Lifecycle)
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import (
    CampaignType,
    CampaignStatus,
    ScheduleType,
    ChannelType,
    SegmentType,
    ExecutionStatus,
    Campaign,
    CampaignAudience,
    CampaignChannel,
    CampaignVariant,
    CampaignTestDataFactory,
)


class TestCampaignServiceCreate:
    """Tests for campaign creation - BR-CAM-001.1"""

    @pytest.mark.asyncio
    async def test_create_campaign_minimal(self, mock_repository, mock_event_bus, factory):
        """Test creating campaign with minimal required fields"""
        # This test will FAIL until implementation exists
        # Given: A valid campaign create request
        campaign = factory.make_campaign(
            campaign_type=CampaignType.SCHEDULED, status=CampaignStatus.DRAFT
        )

        # When: Saving the campaign
        saved = await mock_repository.save_campaign(campaign)

        # Then: Campaign is created with DRAFT status
        assert saved.campaign_id is not None
        assert saved.status == CampaignStatus.DRAFT
        assert saved.created_at is not None

    @pytest.mark.asyncio
    async def test_create_campaign_with_audiences(
        self, mock_repository, mock_event_bus, factory
    ):
        """Test creating campaign with audience segments - BR-CAM-001.1"""
        # Given: Campaign with include/exclude audiences
        campaign = factory.make_campaign(campaign_type=CampaignType.SCHEDULED)
        audiences = [
            factory.make_audience(segment_type=SegmentType.INCLUDE),
            factory.make_audience(segment_type=SegmentType.EXCLUDE),
        ]

        # When: Saving campaign and audiences
        await mock_repository.save_campaign(campaign)
        await mock_repository.save_audiences(campaign.campaign_id, audiences)

        # Then: Audiences are associated with campaign
        saved_audiences = await mock_repository.get_audiences(campaign.campaign_id)
        assert len(saved_audiences) == 2
        assert any(a.segment_type == SegmentType.INCLUDE for a in saved_audiences)
        assert any(a.segment_type == SegmentType.EXCLUDE for a in saved_audiences)

    @pytest.mark.asyncio
    async def test_create_campaign_with_channels(
        self, mock_repository, mock_event_bus, factory
    ):
        """Test creating campaign with delivery channels - BR-CAM-003"""
        # Given: Campaign with multiple channels
        campaign = factory.make_campaign(campaign_type=CampaignType.SCHEDULED)
        channels = [
            factory.make_channel(channel_type=ChannelType.EMAIL),
            factory.make_channel(channel_type=ChannelType.SMS),
        ]

        # When: Saving campaign and channels
        await mock_repository.save_campaign(campaign)
        await mock_repository.save_channels(campaign.campaign_id, channels)

        # Then: Channels are associated with campaign
        saved_channels = await mock_repository.get_channels(campaign.campaign_id)
        assert len(saved_channels) == 2

    @pytest.mark.asyncio
    async def test_create_campaign_generates_unique_id(
        self, mock_repository, mock_event_bus, factory
    ):
        """Test each campaign gets unique ID"""
        # Given: Multiple campaigns
        campaign1 = factory.make_campaign(campaign_type=CampaignType.SCHEDULED)
        campaign2 = factory.make_campaign(campaign_type=CampaignType.SCHEDULED)

        # When: Saving both
        await mock_repository.save_campaign(campaign1)
        await mock_repository.save_campaign(campaign2)

        # Then: IDs are unique
        assert campaign1.campaign_id != campaign2.campaign_id


class TestCampaignServiceGet:
    """Tests for campaign retrieval"""

    @pytest.mark.asyncio
    async def test_get_campaign_by_id(self, sample_campaign, mock_repository):
        """Test getting campaign by ID"""
        # When: Getting campaign by ID
        result = await mock_repository.get_campaign(sample_campaign.campaign_id)

        # Then: Campaign is returned
        assert result is not None
        assert result.campaign_id == sample_campaign.campaign_id

    @pytest.mark.asyncio
    async def test_get_campaign_not_found(self, mock_repository):
        """Test getting non-existent campaign returns None"""
        # When: Getting non-existent campaign
        result = await mock_repository.get_campaign("cmp_nonexistent")

        # Then: None is returned
        assert result is None

    @pytest.mark.asyncio
    async def test_get_campaign_by_org(self, sample_campaign, mock_repository):
        """Test getting campaign by organization"""
        # When: Getting campaign by org
        result = await mock_repository.get_campaign_by_org(
            sample_campaign.organization_id, sample_campaign.campaign_id
        )

        # Then: Campaign is returned
        assert result is not None
        assert result.organization_id == sample_campaign.organization_id

    @pytest.mark.asyncio
    async def test_get_campaign_wrong_org(self, sample_campaign, mock_repository):
        """Test getting campaign with wrong org returns None"""
        # When: Getting campaign with wrong org
        result = await mock_repository.get_campaign_by_org(
            "org_wrong", sample_campaign.campaign_id
        )

        # Then: None is returned
        assert result is None


class TestCampaignServiceList:
    """Tests for campaign listing with filters"""

    @pytest.mark.asyncio
    async def test_list_campaigns_by_status(self, mock_repository, factory):
        """Test listing campaigns by status"""
        # Given: Campaigns with different statuses
        draft = factory.make_campaign(status=CampaignStatus.DRAFT)
        scheduled = factory.make_campaign(status=CampaignStatus.SCHEDULED)
        completed = factory.make_campaign(status=CampaignStatus.COMPLETED)

        await mock_repository.save_campaign(draft)
        await mock_repository.save_campaign(scheduled)
        await mock_repository.save_campaign(completed)

        # When: Listing by status
        results, total = await mock_repository.list_campaigns(
            status=[CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]
        )

        # Then: Only matching campaigns returned
        assert len(results) == 2
        assert all(c.status in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED] for c in results)

    @pytest.mark.asyncio
    async def test_list_campaigns_by_type(self, mock_repository, factory):
        """Test listing campaigns by type"""
        # Given: Campaigns of different types
        scheduled = factory.make_campaign(campaign_type=CampaignType.SCHEDULED)
        triggered = factory.make_campaign(campaign_type=CampaignType.TRIGGERED)

        await mock_repository.save_campaign(scheduled)
        await mock_repository.save_campaign(triggered)

        # When: Listing by type
        results, total = await mock_repository.list_campaigns(
            campaign_type=CampaignType.SCHEDULED
        )

        # Then: Only matching campaigns returned
        assert len(results) == 1
        assert results[0].campaign_type == CampaignType.SCHEDULED

    @pytest.mark.asyncio
    async def test_list_campaigns_pagination(self, mock_repository, factory):
        """Test campaign listing pagination"""
        # Given: Many campaigns
        for i in range(25):
            campaign = factory.make_campaign()
            await mock_repository.save_campaign(campaign)

        # When: Paginating
        page1, total = await mock_repository.list_campaigns(limit=10, offset=0)
        page2, _ = await mock_repository.list_campaigns(limit=10, offset=10)
        page3, _ = await mock_repository.list_campaigns(limit=10, offset=20)

        # Then: Correct pagination
        assert len(page1) == 10
        assert len(page2) == 10
        assert len(page3) == 5
        assert total == 25

    @pytest.mark.asyncio
    async def test_list_campaigns_search(self, mock_repository, factory):
        """Test campaign search by name"""
        # Given: Campaigns with different names
        campaign1 = factory.make_campaign()
        campaign1.name = "New Year Promotion"
        campaign2 = factory.make_campaign()
        campaign2.name = "Summer Sale"

        await mock_repository.save_campaign(campaign1)
        await mock_repository.save_campaign(campaign2)

        # When: Searching
        results, _ = await mock_repository.list_campaigns(search="Year")

        # Then: Only matching campaigns returned
        assert len(results) == 1
        assert "Year" in results[0].name


class TestCampaignServiceUpdate:
    """Tests for campaign updates - BR-CAM-001.5-8"""

    @pytest.mark.asyncio
    async def test_update_draft_campaign(self, sample_campaign, mock_repository):
        """Test updating draft campaign - BR-CAM-001.8"""
        # Given: Draft campaign
        assert sample_campaign.status == CampaignStatus.DRAFT

        # When: Updating
        await mock_repository.update_campaign(
            sample_campaign.campaign_id, {"name": "Updated Name", "description": "Updated"}
        )

        # Then: Updates are applied
        updated = await mock_repository.get_campaign(sample_campaign.campaign_id)
        assert updated.name == "Updated Name"
        assert updated.description == "Updated"
        assert updated.updated_at is not None

    @pytest.mark.asyncio
    async def test_update_status(self, sample_campaign, mock_repository):
        """Test updating campaign status"""
        # Given: Draft campaign
        assert sample_campaign.status == CampaignStatus.DRAFT

        # When: Updating status to scheduled
        await mock_repository.update_campaign_status(
            sample_campaign.campaign_id,
            CampaignStatus.SCHEDULED,
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        # Then: Status is updated
        updated = await mock_repository.get_campaign(sample_campaign.campaign_id)
        assert updated.status == CampaignStatus.SCHEDULED


class TestCampaignServiceDelete:
    """Tests for campaign deletion"""

    @pytest.mark.asyncio
    async def test_delete_campaign_soft_delete(self, sample_campaign, mock_repository):
        """Test campaign soft delete"""
        # Given: Existing campaign
        assert sample_campaign.deleted_at is None

        # When: Deleting
        result = await mock_repository.delete_campaign(sample_campaign.campaign_id)

        # Then: Campaign is soft deleted
        assert result is True
        deleted = await mock_repository.get_campaign(sample_campaign.campaign_id)
        assert deleted.deleted_at is not None

    @pytest.mark.asyncio
    async def test_deleted_campaign_excluded_from_list(
        self, sample_campaign, mock_repository
    ):
        """Test deleted campaigns are excluded from listings"""
        # Given: Deleted campaign
        await mock_repository.delete_campaign(sample_campaign.campaign_id)

        # When: Listing campaigns
        results, _ = await mock_repository.list_campaigns()

        # Then: Deleted campaign not in results
        assert sample_campaign.campaign_id not in [c.campaign_id for c in results]


class TestCampaignServiceVariants:
    """Tests for variant management - BR-CAM-004"""

    @pytest.mark.asyncio
    async def test_add_variant_to_campaign(self, sample_campaign, mock_repository, factory):
        """Test adding A/B test variant - BR-CAM-004.1"""
        # Given: Campaign
        variant = factory.make_variant(name="Variant A", allocation=Decimal("50"))

        # When: Adding variant
        await mock_repository.save_variant(sample_campaign.campaign_id, variant)

        # Then: Variant is saved
        variants = await mock_repository.get_variants(sample_campaign.campaign_id)
        assert len(variants) == 1
        assert variants[0].name == "Variant A"

    @pytest.mark.asyncio
    async def test_update_variant(self, sample_campaign, mock_repository, factory):
        """Test updating variant"""
        # Given: Campaign with variant
        variant = factory.make_variant(name="Original", allocation=Decimal("50"))
        await mock_repository.save_variant(sample_campaign.campaign_id, variant)

        # When: Updating variant
        await mock_repository.update_variant(
            sample_campaign.campaign_id,
            variant.variant_id,
            {"name": "Updated", "allocation_percentage": Decimal("60")},
        )

        # Then: Variant is updated
        variants = await mock_repository.get_variants(sample_campaign.campaign_id)
        assert variants[0].name == "Updated"
        assert variants[0].allocation_percentage == Decimal("60")

    @pytest.mark.asyncio
    async def test_delete_variant(self, sample_campaign, mock_repository, factory):
        """Test deleting variant"""
        # Given: Campaign with variant
        variant = factory.make_variant(name="To Delete", allocation=Decimal("100"))
        await mock_repository.save_variant(sample_campaign.campaign_id, variant)

        # When: Deleting variant
        result = await mock_repository.delete_variant(
            sample_campaign.campaign_id, variant.variant_id
        )

        # Then: Variant is deleted
        assert result is True
        variants = await mock_repository.get_variants(sample_campaign.campaign_id)
        assert len(variants) == 0


class TestCampaignServiceTriggers:
    """Tests for trigger management - BR-CAM-007"""

    @pytest.mark.asyncio
    async def test_add_triggers_to_campaign(
        self, mock_repository, factory
    ):
        """Test adding triggers to triggered campaign - BR-CAM-007.1"""
        # Given: Triggered campaign
        campaign = factory.make_triggered_campaign()
        await mock_repository.save_campaign(campaign)

        triggers = [
            factory.make_trigger(event_type="user.purchase"),
            factory.make_trigger(event_type="user.signup"),
        ]

        # When: Saving triggers
        await mock_repository.save_triggers(campaign.campaign_id, triggers)

        # Then: Triggers are saved
        saved_triggers = await mock_repository.get_triggers(campaign.campaign_id)
        assert len(saved_triggers) == 2

    @pytest.mark.asyncio
    async def test_get_triggers(self, mock_repository, factory):
        """Test getting triggers for campaign"""
        # Given: Campaign with triggers
        campaign = factory.make_triggered_campaign()
        await mock_repository.save_campaign(campaign)

        trigger = factory.make_trigger(event_type="order.completed")
        await mock_repository.save_triggers(campaign.campaign_id, [trigger])

        # When: Getting triggers
        triggers = await mock_repository.get_triggers(campaign.campaign_id)

        # Then: Triggers are returned
        assert len(triggers) == 1
        assert triggers[0].event_type == "order.completed"
