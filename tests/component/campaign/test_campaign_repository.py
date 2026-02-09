"""
Component Tests for CampaignRepository Class

Tests the data access layer with mock database.
Reference: System Contract - Database Access Pattern
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
    ChannelType,
    ExecutionStatus,
    MessageStatus,
    CampaignTestDataFactory,
)


class TestCampaignRepositoryHealth:
    """Tests for repository health check"""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_repository):
        """Test health check returns healthy"""
        result = await mock_repository.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_initialize_repository(self, mock_repository):
        """Test repository initialization"""
        # Should not raise
        await mock_repository.initialize()

    @pytest.mark.asyncio
    async def test_close_repository(self, mock_repository):
        """Test repository close"""
        # Should not raise
        await mock_repository.close()


class TestCampaignRepositoryCRUD:
    """Tests for basic CRUD operations"""

    @pytest.mark.asyncio
    async def test_save_and_get_campaign(self, mock_repository, factory):
        """Test saving and retrieving campaign"""
        # Given
        campaign = factory.make_campaign()

        # When
        saved = await mock_repository.save_campaign(campaign)
        retrieved = await mock_repository.get_campaign(campaign.campaign_id)

        # Then
        assert saved.campaign_id == campaign.campaign_id
        assert retrieved is not None
        assert retrieved.campaign_id == campaign.campaign_id
        assert retrieved.name == campaign.name

    @pytest.mark.asyncio
    async def test_update_campaign_fields(self, mock_repository, factory):
        """Test updating specific campaign fields"""
        # Given
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)

        # When
        updated = await mock_repository.update_campaign(
            campaign.campaign_id,
            {
                "name": "New Name",
                "description": "New description",
            },
        )

        # Then
        assert updated.name == "New Name"
        assert updated.description == "New description"

    @pytest.mark.asyncio
    async def test_update_nonexistent_campaign(self, mock_repository):
        """Test updating non-existent campaign returns None"""
        result = await mock_repository.update_campaign(
            "cmp_nonexistent", {"name": "New"}
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_campaign(self, mock_repository, factory):
        """Test deleting campaign"""
        # Given
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)

        # When
        result = await mock_repository.delete_campaign(campaign.campaign_id)

        # Then
        assert result is True
        deleted = await mock_repository.get_campaign(campaign.campaign_id)
        assert deleted.deleted_at is not None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_campaign(self, mock_repository):
        """Test deleting non-existent campaign returns False"""
        result = await mock_repository.delete_campaign("cmp_nonexistent")
        assert result is False


class TestCampaignRepositoryQuery:
    """Tests for query operations"""

    @pytest.mark.asyncio
    async def test_list_campaigns_empty(self, mock_repository):
        """Test listing campaigns when none exist"""
        campaigns, total = await mock_repository.list_campaigns()
        assert campaigns == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_campaigns_multiple(self, mock_repository, factory):
        """Test listing multiple campaigns"""
        # Given
        for _ in range(5):
            await mock_repository.save_campaign(factory.make_campaign())

        # When
        campaigns, total = await mock_repository.list_campaigns()

        # Then
        assert len(campaigns) == 5
        assert total == 5

    @pytest.mark.asyncio
    async def test_list_campaigns_filter_org(self, mock_repository, factory):
        """Test filtering by organization"""
        # Given
        campaign1 = factory.make_campaign()
        campaign1.organization_id = "org_1"
        campaign2 = factory.make_campaign()
        campaign2.organization_id = "org_2"

        await mock_repository.save_campaign(campaign1)
        await mock_repository.save_campaign(campaign2)

        # When
        campaigns, total = await mock_repository.list_campaigns(organization_id="org_1")

        # Then
        assert len(campaigns) == 1
        assert campaigns[0].organization_id == "org_1"

    @pytest.mark.asyncio
    async def test_list_campaigns_filter_status(self, mock_repository, factory):
        """Test filtering by status"""
        # Given
        draft = factory.make_campaign(status=CampaignStatus.DRAFT)
        scheduled = factory.make_campaign(status=CampaignStatus.SCHEDULED)

        await mock_repository.save_campaign(draft)
        await mock_repository.save_campaign(scheduled)

        # When
        campaigns, total = await mock_repository.list_campaigns(
            status=[CampaignStatus.DRAFT]
        )

        # Then
        assert len(campaigns) == 1
        assert campaigns[0].status == CampaignStatus.DRAFT

    @pytest.mark.asyncio
    async def test_list_campaigns_filter_type(self, mock_repository, factory):
        """Test filtering by campaign type"""
        # Given
        scheduled = factory.make_campaign(campaign_type=CampaignType.SCHEDULED)
        triggered = factory.make_campaign(campaign_type=CampaignType.TRIGGERED)

        await mock_repository.save_campaign(scheduled)
        await mock_repository.save_campaign(triggered)

        # When
        campaigns, total = await mock_repository.list_campaigns(
            campaign_type=CampaignType.TRIGGERED
        )

        # Then
        assert len(campaigns) == 1
        assert campaigns[0].campaign_type == CampaignType.TRIGGERED

    @pytest.mark.asyncio
    async def test_list_campaigns_excludes_deleted(self, mock_repository, factory):
        """Test deleted campaigns are excluded from list"""
        # Given
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)
        await mock_repository.delete_campaign(campaign.campaign_id)

        # When
        campaigns, total = await mock_repository.list_campaigns()

        # Then
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_campaigns_pagination(self, mock_repository, factory):
        """Test pagination"""
        # Given
        for i in range(15):
            await mock_repository.save_campaign(factory.make_campaign())

        # When
        page1, total = await mock_repository.list_campaigns(limit=5, offset=0)
        page2, _ = await mock_repository.list_campaigns(limit=5, offset=5)
        page3, _ = await mock_repository.list_campaigns(limit=5, offset=10)

        # Then
        assert len(page1) == 5
        assert len(page2) == 5
        assert len(page3) == 5
        assert total == 15


class TestCampaignRepositoryExecution:
    """Tests for execution operations"""

    @pytest.mark.asyncio
    async def test_save_and_get_execution(self, mock_repository, factory):
        """Test saving and retrieving execution"""
        # Given
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)
        execution = factory.make_execution(campaign_id=campaign.campaign_id)

        # When
        saved = await mock_repository.save_execution(execution)
        retrieved = await mock_repository.get_execution(execution.execution_id)

        # Then
        assert saved.execution_id == execution.execution_id
        assert retrieved is not None
        assert retrieved.campaign_id == campaign.campaign_id

    @pytest.mark.asyncio
    async def test_list_executions(self, mock_repository, factory):
        """Test listing executions for campaign"""
        # Given
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)

        for _ in range(3):
            execution = factory.make_execution(campaign_id=campaign.campaign_id)
            await mock_repository.save_execution(execution)

        # When
        executions, total = await mock_repository.list_executions(campaign.campaign_id)

        # Then
        assert len(executions) == 3
        assert total == 3

    @pytest.mark.asyncio
    async def test_update_execution_status(self, mock_repository, factory):
        """Test updating execution status"""
        # Given
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)
        execution = factory.make_execution(
            campaign_id=campaign.campaign_id, status=ExecutionStatus.PENDING
        )
        await mock_repository.save_execution(execution)

        # When
        updated = await mock_repository.update_execution_status(
            execution.execution_id,
            ExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        # Then
        assert updated.status == ExecutionStatus.RUNNING
        assert updated.started_at is not None


class TestCampaignRepositoryMessage:
    """Tests for message operations"""

    @pytest.mark.asyncio
    async def test_save_and_get_message(self, mock_repository, factory):
        """Test saving and retrieving message"""
        # Given
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)
        execution = factory.make_execution(campaign_id=campaign.campaign_id)
        await mock_repository.save_execution(execution)
        message = factory.make_message(
            campaign_id=campaign.campaign_id,
            execution_id=execution.execution_id,
        )

        # When
        saved = await mock_repository.save_message(message)
        retrieved = await mock_repository.get_message(message.message_id)

        # Then
        assert saved.message_id == message.message_id
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_list_messages_by_campaign(self, mock_repository, factory):
        """Test listing messages by campaign"""
        # Given
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)
        execution = factory.make_execution(campaign_id=campaign.campaign_id)
        await mock_repository.save_execution(execution)

        for _ in range(5):
            message = factory.make_message(
                campaign_id=campaign.campaign_id,
                execution_id=execution.execution_id,
            )
            await mock_repository.save_message(message)

        # When
        messages, total = await mock_repository.list_messages(campaign.campaign_id)

        # Then
        assert len(messages) == 5
        assert total == 5

    @pytest.mark.asyncio
    async def test_list_messages_filter_status(self, mock_repository, factory):
        """Test filtering messages by status"""
        # Given
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)
        execution = factory.make_execution(campaign_id=campaign.campaign_id)
        await mock_repository.save_execution(execution)

        queued = factory.make_message(
            campaign_id=campaign.campaign_id,
            execution_id=execution.execution_id,
            status=MessageStatus.QUEUED,
        )
        sent = factory.make_message(
            campaign_id=campaign.campaign_id,
            execution_id=execution.execution_id,
            status=MessageStatus.SENT,
        )
        await mock_repository.save_message(queued)
        await mock_repository.save_message(sent)

        # When
        messages, total = await mock_repository.list_messages(
            campaign.campaign_id, status=MessageStatus.QUEUED
        )

        # Then
        assert len(messages) == 1
        assert messages[0].status == MessageStatus.QUEUED

    @pytest.mark.asyncio
    async def test_update_message_status(self, mock_repository, factory):
        """Test updating message status"""
        # Given
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)
        execution = factory.make_execution(campaign_id=campaign.campaign_id)
        await mock_repository.save_execution(execution)
        message = factory.make_message(
            campaign_id=campaign.campaign_id,
            execution_id=execution.execution_id,
            status=MessageStatus.QUEUED,
        )
        await mock_repository.save_message(message)

        # When
        now = datetime.now(timezone.utc)
        updated = await mock_repository.update_message_status(
            message.message_id,
            MessageStatus.SENT,
            sent_at=now,
        )

        # Then
        assert updated.status == MessageStatus.SENT
        assert updated.sent_at == now


class TestCampaignRepositoryMetrics:
    """Tests for metrics operations"""

    @pytest.mark.asyncio
    async def test_save_and_get_metrics(self, mock_repository, factory):
        """Test saving and retrieving metrics summary"""
        # Given
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)
        metrics = factory.make_metrics_summary(campaign_id=campaign.campaign_id)

        # When
        saved = await mock_repository.save_metrics_summary(metrics)
        retrieved = await mock_repository.get_metrics_summary(campaign.campaign_id)

        # Then
        assert saved.campaign_id == campaign.campaign_id
        assert retrieved is not None
        assert retrieved.sent == metrics.sent

    @pytest.mark.asyncio
    async def test_get_metrics_not_found(self, mock_repository):
        """Test getting metrics for campaign with no metrics"""
        result = await mock_repository.get_metrics_summary("cmp_no_metrics")
        assert result is None
