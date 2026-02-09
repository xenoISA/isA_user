"""
Component Tests for Campaign Creation Flows

Tests campaign creation business logic.
Reference: BR-CAM-001.1 (Campaign Creation)
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
    CampaignTestDataFactory,
    CampaignCreateRequestBuilder,
)


class TestCampaignCreateScheduled:
    """Tests for creating scheduled campaigns - BR-CAM-001.1"""

    @pytest.mark.asyncio
    async def test_create_scheduled_campaign_one_time(self, mock_repository, factory):
        """Test creating one-time scheduled campaign"""
        # Given: Valid scheduled campaign request
        campaign = factory.make_scheduled_campaign()
        campaign.schedule_type = ScheduleType.ONE_TIME
        campaign.scheduled_at = datetime.now(timezone.utc) + timedelta(hours=24)

        # When: Creating campaign
        saved = await mock_repository.save_campaign(campaign)

        # Then: Campaign created in DRAFT status
        assert saved.status == CampaignStatus.DRAFT
        assert saved.campaign_type == CampaignType.SCHEDULED
        assert saved.schedule_type == ScheduleType.ONE_TIME

    @pytest.mark.asyncio
    async def test_create_scheduled_campaign_recurring(self, mock_repository, factory):
        """Test creating recurring scheduled campaign"""
        # Given: Recurring campaign with cron expression
        campaign = factory.make_scheduled_campaign()
        campaign.schedule_type = ScheduleType.RECURRING
        campaign.cron_expression = "0 9 * * 1"  # Every Monday at 9am

        # When: Creating campaign
        saved = await mock_repository.save_campaign(campaign)

        # Then: Campaign created with recurring settings
        assert saved.schedule_type == ScheduleType.RECURRING
        assert saved.cron_expression == "0 9 * * 1"

    @pytest.mark.asyncio
    async def test_create_campaign_with_timezone(self, mock_repository, factory):
        """Test creating campaign with specific timezone"""
        # Given: Campaign with timezone
        campaign = factory.make_scheduled_campaign()
        campaign.timezone = "America/New_York"

        # When: Creating campaign
        saved = await mock_repository.save_campaign(campaign)

        # Then: Timezone is preserved
        assert saved.timezone == "America/New_York"


class TestCampaignCreateTriggered:
    """Tests for creating triggered campaigns - BR-CAM-001.1"""

    @pytest.mark.asyncio
    async def test_create_triggered_campaign(self, mock_repository, factory):
        """Test creating triggered campaign"""
        # Given: Triggered campaign with triggers
        campaign = factory.make_triggered_campaign()

        # When: Creating campaign
        saved = await mock_repository.save_campaign(campaign)

        # Then: Campaign is triggered type
        assert saved.campaign_type == CampaignType.TRIGGERED

    @pytest.mark.asyncio
    async def test_create_triggered_campaign_with_delay(self, mock_repository, factory):
        """Test creating triggered campaign with delay - BR-CAM-007.2"""
        # Given: Triggered campaign
        campaign = factory.make_triggered_campaign()
        trigger = factory.make_trigger(event_type="user.signup")
        trigger.delay_minutes = 60  # 1 hour delay

        # When: Creating campaign with trigger
        await mock_repository.save_campaign(campaign)
        await mock_repository.save_triggers(campaign.campaign_id, [trigger])

        # Then: Trigger has delay configured
        triggers = await mock_repository.get_triggers(campaign.campaign_id)
        assert triggers[0].delay_minutes == 60


class TestCampaignCreateAudience:
    """Tests for creating campaigns with audiences - BR-CAM-002"""

    @pytest.mark.asyncio
    async def test_create_campaign_with_include_audience(self, mock_repository, factory):
        """Test creating campaign with include segment"""
        # Given: Campaign with include audience
        campaign = factory.make_campaign()
        audience = factory.make_audience(segment_type=SegmentType.INCLUDE)

        # When: Creating campaign with audience
        await mock_repository.save_campaign(campaign)
        await mock_repository.save_audiences(campaign.campaign_id, [audience])

        # Then: Audience is saved
        audiences = await mock_repository.get_audiences(campaign.campaign_id)
        assert len(audiences) == 1
        assert audiences[0].segment_type == SegmentType.INCLUDE

    @pytest.mark.asyncio
    async def test_create_campaign_with_exclude_audience(self, mock_repository, factory):
        """Test creating campaign with exclude segment"""
        # Given: Campaign with exclude audience
        campaign = factory.make_campaign()
        include = factory.make_audience(segment_type=SegmentType.INCLUDE)
        exclude = factory.make_audience(segment_type=SegmentType.EXCLUDE)

        # When: Creating campaign with audiences
        await mock_repository.save_campaign(campaign)
        await mock_repository.save_audiences(campaign.campaign_id, [include, exclude])

        # Then: Both audiences are saved
        audiences = await mock_repository.get_audiences(campaign.campaign_id)
        assert len(audiences) == 2

    @pytest.mark.asyncio
    async def test_create_campaign_with_holdout(self, mock_repository, factory):
        """Test creating campaign with holdout group - BR-CAM-002.2"""
        # Given: Campaign with holdout
        campaign = factory.make_campaign()
        campaign.holdout_percentage = Decimal("10")

        # When: Creating campaign
        saved = await mock_repository.save_campaign(campaign)

        # Then: Holdout is preserved
        assert saved.holdout_percentage == Decimal("10")


class TestCampaignCreateChannel:
    """Tests for creating campaigns with channels - BR-CAM-003"""

    @pytest.mark.asyncio
    async def test_create_campaign_with_email_channel(self, mock_repository, factory):
        """Test creating campaign with email channel"""
        # Given: Campaign with email channel
        campaign = factory.make_campaign()
        channel = factory.make_channel(channel_type=ChannelType.EMAIL)

        # When: Creating campaign with channel
        await mock_repository.save_campaign(campaign)
        await mock_repository.save_channels(campaign.campaign_id, [channel])

        # Then: Channel is saved
        channels = await mock_repository.get_channels(campaign.campaign_id)
        assert len(channels) == 1
        assert channels[0].channel_type == ChannelType.EMAIL

    @pytest.mark.asyncio
    async def test_create_campaign_with_multiple_channels(self, mock_repository, factory):
        """Test creating campaign with multiple channels - BR-CAM-003.3"""
        # Given: Campaign with multiple channels
        campaign = factory.make_campaign()
        channels = [
            factory.make_channel(channel_type=ChannelType.EMAIL),
            factory.make_channel(channel_type=ChannelType.SMS),
            factory.make_channel(channel_type=ChannelType.IN_APP),
        ]

        # Set priority for fallback
        for i, channel in enumerate(channels):
            channel.priority = i + 1

        # When: Creating campaign with channels
        await mock_repository.save_campaign(campaign)
        await mock_repository.save_channels(campaign.campaign_id, channels)

        # Then: All channels saved with priority
        saved_channels = await mock_repository.get_channels(campaign.campaign_id)
        assert len(saved_channels) == 3


class TestCampaignCreateABTest:
    """Tests for creating A/B test campaigns - BR-CAM-004"""

    @pytest.mark.asyncio
    async def test_create_campaign_with_ab_test(self, mock_repository, factory):
        """Test creating campaign with A/B testing enabled - BR-CAM-004.1"""
        # Given: A/B test campaign
        campaign = factory.make_ab_test_campaign(num_variants=2)

        # When: Creating campaign
        saved = await mock_repository.save_campaign(campaign)

        # Then: A/B testing is enabled
        assert saved.ab_test.enabled is True

    @pytest.mark.asyncio
    async def test_create_campaign_with_variants(self, mock_repository, factory):
        """Test creating campaign with variants"""
        # Given: Campaign with variants
        campaign = factory.make_campaign()
        variants = [
            factory.make_variant(name="Variant A", allocation=Decimal("50")),
            factory.make_variant(name="Variant B", allocation=Decimal("50")),
        ]

        # When: Creating campaign with variants
        await mock_repository.save_campaign(campaign)
        for variant in variants:
            await mock_repository.save_variant(campaign.campaign_id, variant)

        # Then: Variants are saved
        saved_variants = await mock_repository.get_variants(campaign.campaign_id)
        assert len(saved_variants) == 2

    @pytest.mark.asyncio
    async def test_create_campaign_with_control_variant(self, mock_repository, factory):
        """Test creating campaign with control variant - BR-CAM-004.1"""
        # Given: Campaign with control variant
        campaign = factory.make_campaign()
        treatment = factory.make_variant(name="Treatment", allocation=Decimal("90"))
        control = factory.make_variant(name="Control", allocation=Decimal("10"))
        control.is_control = True

        # When: Creating campaign with variants
        await mock_repository.save_campaign(campaign)
        await mock_repository.save_variant(campaign.campaign_id, treatment)
        await mock_repository.save_variant(campaign.campaign_id, control)

        # Then: Control variant is marked
        variants = await mock_repository.get_variants(campaign.campaign_id)
        control_variants = [v for v in variants if v.is_control]
        assert len(control_variants) == 1


class TestCampaignCreateConversion:
    """Tests for creating campaigns with conversion tracking - BR-CAM-005.3"""

    @pytest.mark.asyncio
    async def test_create_campaign_with_conversion_tracking(self, mock_repository, factory):
        """Test creating campaign with conversion tracking"""
        # Given: Campaign with conversion config
        campaign = factory.make_campaign()
        campaign.conversion.conversion_event_type = "purchase.completed"
        campaign.conversion.attribution_window_days = 7

        # When: Creating campaign
        saved = await mock_repository.save_campaign(campaign)

        # Then: Conversion config is preserved
        assert saved.conversion.conversion_event_type == "purchase.completed"
        assert saved.conversion.attribution_window_days == 7


class TestCampaignCreateThrottle:
    """Tests for creating campaigns with throttle config - BR-CAM-006"""

    @pytest.mark.asyncio
    async def test_create_campaign_with_throttle(self, mock_repository, factory):
        """Test creating campaign with rate limiting - BR-CAM-006.1"""
        # Given: Campaign with throttle config
        campaign = factory.make_campaign()
        campaign.throttle.per_minute = 5000
        campaign.throttle.per_hour = 50000

        # When: Creating campaign
        saved = await mock_repository.save_campaign(campaign)

        # Then: Throttle config is preserved
        assert saved.throttle.per_minute == 5000
        assert saved.throttle.per_hour == 50000

    @pytest.mark.asyncio
    async def test_create_campaign_with_send_window(self, mock_repository, factory):
        """Test creating campaign with send window"""
        # Given: Campaign with send window
        campaign = factory.make_campaign()
        campaign.throttle.send_window_start = 9
        campaign.throttle.send_window_end = 18

        # When: Creating campaign
        saved = await mock_repository.save_campaign(campaign)

        # Then: Send window is preserved
        assert saved.throttle.send_window_start == 9
        assert saved.throttle.send_window_end == 18


class TestCampaignCreateRequestBuilder:
    """Tests for CampaignCreateRequestBuilder helper"""

    def test_builder_minimal(self):
        """Test builder with minimal fields"""
        request = (
            CampaignCreateRequestBuilder()
            .with_name("Test Campaign")
            .with_type(CampaignType.SCHEDULED)
            .build()
        )

        assert request.name == "Test Campaign"
        assert request.campaign_type == CampaignType.SCHEDULED

    def test_builder_with_schedule(self):
        """Test builder with schedule"""
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=24)
        request = (
            CampaignCreateRequestBuilder()
            .with_name("Scheduled Campaign")
            .with_type(CampaignType.SCHEDULED)
            .with_schedule(ScheduleType.ONE_TIME, scheduled_at)
            .build()
        )

        assert request.schedule_type == ScheduleType.ONE_TIME
        assert request.scheduled_at == scheduled_at

    def test_builder_with_audience(self):
        """Test builder with audience"""
        request = (
            CampaignCreateRequestBuilder()
            .with_name("Campaign with Audience")
            .with_type(CampaignType.SCHEDULED)
            .with_audience("seg_premium", SegmentType.INCLUDE)
            .build()
        )

        assert len(request.audiences) == 1
        assert request.audiences[0].segment_id == "seg_premium"

    def test_builder_with_holdout(self):
        """Test builder with holdout"""
        request = (
            CampaignCreateRequestBuilder()
            .with_name("Campaign with Holdout")
            .with_type(CampaignType.SCHEDULED)
            .with_holdout(Decimal("5"))
            .build()
        )

        assert request.holdout_percentage == Decimal("5")

    def test_builder_complete(self):
        """Test builder with all options"""
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=24)
        request = (
            CampaignCreateRequestBuilder()
            .with_name("Complete Campaign")
            .with_type(CampaignType.SCHEDULED)
            .with_schedule(ScheduleType.ONE_TIME, scheduled_at)
            .with_audience("seg_all", SegmentType.INCLUDE)
            .with_audience("seg_unsubscribed", SegmentType.EXCLUDE)
            .with_holdout(Decimal("10"))
            .with_ab_testing(enabled=True)
            .build()
        )

        assert request.name == "Complete Campaign"
        assert len(request.audiences) == 2
        assert request.holdout_percentage == Decimal("10")
        assert request.enable_ab_testing is True
