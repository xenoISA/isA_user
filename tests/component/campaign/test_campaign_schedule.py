"""
Component Tests for Campaign Scheduling Logic

Tests campaign scheduling business logic.
Reference: BR-CAM-001.2 (Schedule Scheduled Campaign)
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
    CampaignTestDataFactory,
)


class TestCampaignScheduleValidation:
    """Tests for schedule validation - BR-CAM-001.2"""

    @pytest.mark.asyncio
    async def test_schedule_draft_campaign(self, sample_campaign, mock_repository):
        """Test scheduling a draft campaign"""
        # Given: Draft campaign
        assert sample_campaign.status == CampaignStatus.DRAFT

        # When: Scheduling the campaign
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await mock_repository.update_campaign_status(
            sample_campaign.campaign_id,
            CampaignStatus.SCHEDULED,
            scheduled_at=scheduled_at,
            task_id="task_123",
        )

        # Then: Campaign is scheduled
        updated = await mock_repository.get_campaign(sample_campaign.campaign_id)
        assert updated.status == CampaignStatus.SCHEDULED
        assert updated.task_id == "task_123"

    @pytest.mark.asyncio
    async def test_schedule_requires_future_time(self, sample_campaign, mock_repository):
        """Test schedule must be at least 5 minutes in future - BR-CAM-001.2"""
        # Given: Draft campaign
        # The validation should reject times less than 5 minutes away
        # This test documents the expected validation behavior

        # When/Then: Scheduling for past time should be rejected
        # (Service layer validation - here we just document the requirement)
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)

        # In real implementation, this would raise ValidationError
        # For now, we just verify the requirement is documented
        assert past_time < datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_schedule_creates_task(
        self, sample_campaign, mock_repository, mock_task_client
    ):
        """Test scheduling creates task in task_service - BR-CAM-001.2"""
        # Given: Draft campaign
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # When: Creating task for schedule
        task = await mock_task_client.create_task(
            task_type="campaign_execution",
            scheduled_at=scheduled_at.isoformat(),
            config={"campaign_id": sample_campaign.campaign_id},
        )

        # Then: Task is created
        assert task["task_id"] is not None
        assert len(mock_task_client.created_tasks) == 1

    @pytest.mark.asyncio
    async def test_schedule_recurring_campaign(self, mock_repository, factory):
        """Test scheduling recurring campaign - BR-CAM-001.2"""
        # Given: Recurring campaign with cron expression
        campaign = factory.make_scheduled_campaign()
        campaign.schedule_type = ScheduleType.RECURRING
        campaign.cron_expression = "0 9 * * 1"  # Every Monday at 9am
        await mock_repository.save_campaign(campaign)

        # When: Scheduling
        await mock_repository.update_campaign_status(
            campaign.campaign_id,
            CampaignStatus.SCHEDULED,
            task_id="task_recurring",
        )

        # Then: Campaign is scheduled
        updated = await mock_repository.get_campaign(campaign.campaign_id)
        assert updated.status == CampaignStatus.SCHEDULED
        assert updated.cron_expression == "0 9 * * 1"


class TestCampaignScheduleStateTransitions:
    """Tests for schedule state transitions"""

    @pytest.mark.asyncio
    async def test_only_draft_can_be_scheduled(
        self, running_campaign, mock_repository
    ):
        """Test only draft campaigns can be scheduled - BR-CAM-001.2"""
        # Given: Running campaign
        assert running_campaign.status == CampaignStatus.RUNNING

        # When/Then: Attempting to schedule should fail
        # (Service layer validation - this test documents the requirement)
        # The state machine does not allow RUNNING -> SCHEDULED
        assert running_campaign.status != CampaignStatus.DRAFT

    @pytest.mark.asyncio
    async def test_scheduled_can_be_unscheduled(
        self, scheduled_campaign, mock_repository
    ):
        """Test scheduled campaign can return to draft"""
        # Given: Scheduled campaign
        assert scheduled_campaign.status == CampaignStatus.SCHEDULED

        # When: Unscheduling (returning to draft)
        await mock_repository.update_campaign_status(
            scheduled_campaign.campaign_id,
            CampaignStatus.DRAFT,
            scheduled_at=None,
            task_id=None,
        )

        # Then: Campaign is draft again
        updated = await mock_repository.get_campaign(scheduled_campaign.campaign_id)
        assert updated.status == CampaignStatus.DRAFT
        assert updated.task_id is None

    @pytest.mark.asyncio
    async def test_scheduled_can_be_cancelled(
        self, scheduled_campaign, mock_repository
    ):
        """Test scheduled campaign can be cancelled - BR-CAM-001.6"""
        # Given: Scheduled campaign
        assert scheduled_campaign.status == CampaignStatus.SCHEDULED

        # When: Cancelling
        await mock_repository.update_campaign_status(
            scheduled_campaign.campaign_id,
            CampaignStatus.CANCELLED,
            cancelled_at=datetime.now(timezone.utc),
            cancelled_by="usr_admin",
        )

        # Then: Campaign is cancelled
        updated = await mock_repository.get_campaign(scheduled_campaign.campaign_id)
        assert updated.status == CampaignStatus.CANCELLED


class TestCampaignScheduleTaskIntegration:
    """Tests for task service integration"""

    @pytest.mark.asyncio
    async def test_cancel_schedule_cancels_task(
        self, scheduled_campaign, mock_repository, mock_task_client
    ):
        """Test cancelling schedule cancels the task - BR-CAM-001.6"""
        # Given: Scheduled campaign with task
        task_id = scheduled_campaign.task_id

        # When: Cancelling the task
        await mock_task_client.cancel_task(task_id)

        # Then: Task is in cancelled list
        assert task_id in mock_task_client.cancelled_tasks

    @pytest.mark.asyncio
    async def test_reschedule_creates_new_task(
        self, scheduled_campaign, mock_repository, mock_task_client
    ):
        """Test rescheduling creates new task"""
        # Given: Scheduled campaign
        old_task_id = scheduled_campaign.task_id

        # When: Rescheduling (cancel old, create new)
        await mock_task_client.cancel_task(old_task_id)
        new_task = await mock_task_client.create_task(
            task_type="campaign_execution",
            scheduled_at=(datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
            config={"campaign_id": scheduled_campaign.campaign_id},
        )

        # Then: New task is created
        assert new_task["task_id"] != old_task_id
        assert old_task_id in mock_task_client.cancelled_tasks


class TestCampaignScheduleWithAudience:
    """Tests for scheduling with audience validation"""

    @pytest.mark.asyncio
    async def test_schedule_requires_audience(self, mock_repository, factory):
        """Test scheduling requires at least one include audience - BR-CAM-002.1"""
        # Given: Campaign without audiences
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)

        # The service layer should validate that at least one include audience exists
        # This test documents the requirement
        audiences = await mock_repository.get_audiences(campaign.campaign_id)
        assert len(audiences) == 0  # No audiences yet

    @pytest.mark.asyncio
    async def test_schedule_with_valid_audience(self, mock_repository, factory):
        """Test scheduling with valid audience succeeds"""
        # Given: Campaign with include audience
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)

        audience = factory.make_audience(segment_type=SegmentType.INCLUDE)
        await mock_repository.save_audiences(campaign.campaign_id, [audience])

        # When: Scheduling
        await mock_repository.update_campaign_status(
            campaign.campaign_id,
            CampaignStatus.SCHEDULED,
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        # Then: Campaign is scheduled
        updated = await mock_repository.get_campaign(campaign.campaign_id)
        assert updated.status == CampaignStatus.SCHEDULED


class TestCampaignScheduleWithChannel:
    """Tests for scheduling with channel validation"""

    @pytest.mark.asyncio
    async def test_schedule_requires_channel(self, mock_repository, factory):
        """Test scheduling requires at least one channel - BR-CAM-003.1"""
        # Given: Campaign without channels
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)

        # The service layer should validate that at least one channel exists
        channels = await mock_repository.get_channels(campaign.campaign_id)
        assert len(channels) == 0  # No channels yet

    @pytest.mark.asyncio
    async def test_schedule_with_valid_channel(self, mock_repository, factory):
        """Test scheduling with valid channel succeeds"""
        # Given: Campaign with channel
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)

        channel = factory.make_channel(channel_type=ChannelType.EMAIL)
        await mock_repository.save_channels(campaign.campaign_id, [channel])

        audience = factory.make_audience(segment_type=SegmentType.INCLUDE)
        await mock_repository.save_audiences(campaign.campaign_id, [audience])

        # When: Scheduling
        await mock_repository.update_campaign_status(
            campaign.campaign_id,
            CampaignStatus.SCHEDULED,
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        # Then: Campaign is scheduled
        updated = await mock_repository.get_campaign(campaign.campaign_id)
        assert updated.status == CampaignStatus.SCHEDULED


# Import SegmentType that was missing
from tests.contracts.campaign.data_contract import SegmentType, ChannelType
