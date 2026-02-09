"""
Component Tests for Event Publishers

Tests NATS event publishing logic.
Reference: System Contract - Event Publishing Pattern
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import (
    CampaignType,
    CampaignStatus,
    ChannelType,
    MessageStatus,
    ExecutionStatus,
    CampaignTestDataFactory,
)


class MockNATSEvent:
    """Mock NATS event for testing"""

    def __init__(self, event_type: str, source: str, data: dict):
        self.event_type = event_type
        self.source = source
        self.data = data


class TestCampaignCreatedEvent:
    """Tests for campaign.created event publishing"""

    @pytest.mark.asyncio
    async def test_publish_campaign_created_event(self, mock_event_bus, factory):
        """Test publishing campaign.created event"""
        # Given: Created campaign
        campaign = factory.make_campaign()

        # When: Publishing event
        event = MockNATSEvent(
            event_type="campaign.created",
            source="campaign_service",
            data={
                "campaign_id": campaign.campaign_id,
                "organization_id": campaign.organization_id,
                "name": campaign.name,
                "campaign_type": campaign.campaign_type.value,
                "status": campaign.status.value,
                "created_by": campaign.created_by,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await mock_event_bus.publish_event(event)

        # Then: Event is published
        events = mock_event_bus.get_events_by_type("campaign.created")
        assert len(events) == 1
        assert events[0]["data"]["campaign_id"] == campaign.campaign_id

    @pytest.mark.asyncio
    async def test_campaign_created_event_has_required_fields(self, mock_event_bus, factory):
        """Test campaign.created event has all required fields"""
        # Given: Created campaign
        campaign = factory.make_campaign()

        # When: Publishing event
        event = MockNATSEvent(
            event_type="campaign.created",
            source="campaign_service",
            data={
                "campaign_id": campaign.campaign_id,
                "organization_id": campaign.organization_id,
                "name": campaign.name,
                "campaign_type": campaign.campaign_type.value,
                "status": campaign.status.value,
                "created_by": campaign.created_by,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await mock_event_bus.publish_event(event)

        # Then: All required fields are present
        events = mock_event_bus.get_events_by_type("campaign.created")
        data = events[0]["data"]

        assert "campaign_id" in data
        assert "organization_id" in data
        assert "name" in data
        assert "campaign_type" in data
        assert "status" in data
        assert "created_by" in data
        assert "timestamp" in data


class TestCampaignScheduledEvent:
    """Tests for campaign.scheduled event publishing"""

    @pytest.mark.asyncio
    async def test_publish_campaign_scheduled_event(self, mock_event_bus, factory):
        """Test publishing campaign.scheduled event"""
        # Given: Scheduled campaign
        campaign = factory.make_scheduled_campaign()
        scheduled_at = datetime.now(timezone.utc)
        task_id = "task_123"

        # When: Publishing event
        event = MockNATSEvent(
            event_type="campaign.scheduled",
            source="campaign_service",
            data={
                "campaign_id": campaign.campaign_id,
                "scheduled_at": scheduled_at.isoformat(),
                "task_id": task_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await mock_event_bus.publish_event(event)

        # Then: Event is published
        events = mock_event_bus.get_events_by_type("campaign.scheduled")
        assert len(events) == 1
        assert events[0]["data"]["task_id"] == task_id


class TestCampaignStartedEvent:
    """Tests for campaign.started event publishing"""

    @pytest.mark.asyncio
    async def test_publish_campaign_started_event(self, mock_event_bus, factory):
        """Test publishing campaign.started event"""
        # Given: Started campaign execution
        campaign = factory.make_campaign()
        execution = factory.make_execution(campaign_id=campaign.campaign_id)

        # When: Publishing event
        event = MockNATSEvent(
            event_type="campaign.started",
            source="campaign_service",
            data={
                "campaign_id": campaign.campaign_id,
                "execution_id": execution.execution_id,
                "audience_size": 10000,
                "holdout_size": 500,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await mock_event_bus.publish_event(event)

        # Then: Event is published with audience info
        events = mock_event_bus.get_events_by_type("campaign.started")
        assert len(events) == 1
        assert events[0]["data"]["audience_size"] == 10000
        assert events[0]["data"]["holdout_size"] == 500


class TestCampaignCompletedEvent:
    """Tests for campaign.completed event publishing"""

    @pytest.mark.asyncio
    async def test_publish_campaign_completed_event(self, mock_event_bus, factory):
        """Test publishing campaign.completed event"""
        # Given: Completed campaign
        campaign = factory.make_campaign()
        execution = factory.make_execution(campaign_id=campaign.campaign_id)

        # When: Publishing event
        event = MockNATSEvent(
            event_type="campaign.completed",
            source="campaign_service",
            data={
                "campaign_id": campaign.campaign_id,
                "execution_id": execution.execution_id,
                "total_sent": 9500,
                "total_delivered": 9200,
                "total_failed": 300,
                "duration_minutes": 45,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await mock_event_bus.publish_event(event)

        # Then: Event is published with metrics
        events = mock_event_bus.get_events_by_type("campaign.completed")
        assert len(events) == 1
        assert events[0]["data"]["total_sent"] == 9500


class TestCampaignCancelledEvent:
    """Tests for campaign.cancelled event publishing"""

    @pytest.mark.asyncio
    async def test_publish_campaign_cancelled_event(self, mock_event_bus, factory):
        """Test publishing campaign.cancelled event"""
        # Given: Cancelled campaign
        campaign = factory.make_campaign()

        # When: Publishing event
        event = MockNATSEvent(
            event_type="campaign.cancelled",
            source="campaign_service",
            data={
                "campaign_id": campaign.campaign_id,
                "cancelled_by": "usr_admin",
                "reason": "Budget constraints",
                "messages_sent_before_cancel": 5000,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await mock_event_bus.publish_event(event)

        # Then: Event is published
        events = mock_event_bus.get_events_by_type("campaign.cancelled")
        assert len(events) == 1
        assert events[0]["data"]["cancelled_by"] == "usr_admin"


class TestMessageStatusEvents:
    """Tests for message status event publishing"""

    @pytest.mark.asyncio
    async def test_publish_message_sent_event(self, mock_event_bus, factory):
        """Test publishing campaign.message.sent event"""
        # Given: Sent message
        message = factory.make_message(status=MessageStatus.SENT)

        # When: Publishing event
        event = MockNATSEvent(
            event_type="campaign.message.sent",
            source="campaign_service",
            data={
                "campaign_id": message.campaign_id,
                "message_id": message.message_id,
                "notification_id": "notif_123",
                "provider_id": "sendgrid",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await mock_event_bus.publish_event(event)

        # Then: Event is published
        events = mock_event_bus.get_events_by_type("campaign.message.sent")
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_publish_message_delivered_event(self, mock_event_bus, factory):
        """Test publishing campaign.message.delivered event"""
        # Given: Delivered message
        message = factory.make_message(status=MessageStatus.DELIVERED)

        # When: Publishing event
        event = MockNATSEvent(
            event_type="campaign.message.delivered",
            source="campaign_service",
            data={
                "campaign_id": message.campaign_id,
                "message_id": message.message_id,
                "delivered_at": datetime.now(timezone.utc).isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await mock_event_bus.publish_event(event)

        # Then: Event is published
        events = mock_event_bus.get_events_by_type("campaign.message.delivered")
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_publish_message_opened_event(self, mock_event_bus, factory):
        """Test publishing campaign.message.opened event"""
        # Given: Opened message
        message = factory.make_message(status=MessageStatus.OPENED)

        # When: Publishing event
        event = MockNATSEvent(
            event_type="campaign.message.opened",
            source="campaign_service",
            data={
                "campaign_id": message.campaign_id,
                "message_id": message.message_id,
                "opened_at": datetime.now(timezone.utc).isoformat(),
                "user_agent": "Mozilla/5.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await mock_event_bus.publish_event(event)

        # Then: Event is published
        events = mock_event_bus.get_events_by_type("campaign.message.opened")
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_publish_message_clicked_event(self, mock_event_bus, factory):
        """Test publishing campaign.message.clicked event"""
        # Given: Clicked message
        message = factory.make_message(status=MessageStatus.CLICKED)

        # When: Publishing event
        event = MockNATSEvent(
            event_type="campaign.message.clicked",
            source="campaign_service",
            data={
                "campaign_id": message.campaign_id,
                "message_id": message.message_id,
                "link_id": "link_cta",
                "link_url": "https://example.com/offer",
                "clicked_at": datetime.now(timezone.utc).isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await mock_event_bus.publish_event(event)

        # Then: Event is published
        events = mock_event_bus.get_events_by_type("campaign.message.clicked")
        assert len(events) == 1
        assert events[0]["data"]["link_url"] == "https://example.com/offer"


class TestConversionEvent:
    """Tests for conversion event publishing"""

    @pytest.mark.asyncio
    async def test_publish_message_converted_event(self, mock_event_bus, factory):
        """Test publishing campaign.message.converted event"""
        # Given: Converted message
        message = factory.make_message()

        # When: Publishing event
        event = MockNATSEvent(
            event_type="campaign.message.converted",
            source="campaign_service",
            data={
                "campaign_id": message.campaign_id,
                "message_id": message.message_id,
                "user_id": message.user_id,
                "conversion_event": "purchase.completed",
                "conversion_value": 99.99,
                "attribution_model": "last_touch",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await mock_event_bus.publish_event(event)

        # Then: Event is published
        events = mock_event_bus.get_events_by_type("campaign.message.converted")
        assert len(events) == 1
        assert events[0]["data"]["conversion_value"] == 99.99


class TestEventBusConnection:
    """Tests for event bus connection handling"""

    @pytest.mark.asyncio
    async def test_event_bus_connected(self, mock_event_bus):
        """Test event bus is connected"""
        assert mock_event_bus.is_connected is True

    @pytest.mark.asyncio
    async def test_event_bus_close(self, mock_event_bus):
        """Test event bus close"""
        await mock_event_bus.close()
        assert mock_event_bus.is_connected is False

    @pytest.mark.asyncio
    async def test_clear_events(self, mock_event_bus, factory):
        """Test clearing published events"""
        # Given: Some published events
        event = MockNATSEvent(
            event_type="test.event",
            source="test",
            data={"test": True},
        )
        await mock_event_bus.publish_event(event)
        assert len(mock_event_bus.published_events) == 1

        # When: Clearing
        mock_event_bus.clear_events()

        # Then: Events are cleared
        assert len(mock_event_bus.published_events) == 0
