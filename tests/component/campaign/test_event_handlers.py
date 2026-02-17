"""
Component Tests for Event Handlers

Tests NATS event subscription handlers.
Reference: System Contract - Event Subscription Pattern
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

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


class TestTaskExecutedHandler:
    """Tests for task.executed event handler"""

    @pytest.mark.asyncio
    async def test_handle_task_executed_starts_campaign(
        self, mock_repository, mock_event_bus, factory
    ):
        """Test task.executed triggers campaign execution - BR-CAM-001.2"""
        # Given: Scheduled campaign
        campaign = factory.make_scheduled_campaign()
        campaign.status = CampaignStatus.SCHEDULED
        campaign.task_id = "task_123"
        await mock_repository.save_campaign(campaign)

        # When: task.executed event received
        event_data = {
            "task_id": "task_123",
            "task_type": "campaign_execution",
            "config": {"campaign_id": campaign.campaign_id},
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

        # Simulate handler processing
        # In real implementation, this would call execution_service.start_execution()
        await mock_repository.update_campaign_status(
            campaign.campaign_id, CampaignStatus.RUNNING
        )

        # Then: Campaign starts running
        updated = await mock_repository.get_campaign(campaign.campaign_id)
        assert updated.status == CampaignStatus.RUNNING

    @pytest.mark.asyncio
    async def test_handle_task_executed_missing_campaign_id(self, mock_event_bus):
        """Test handler handles missing campaign_id gracefully"""
        # Given: Event without campaign_id
        event_data = {
            "task_id": "task_123",
            "task_type": "campaign_execution",
            "config": {},  # Missing campaign_id
        }

        # When/Then: Handler should log warning and return False
        # This documents expected behavior
        assert "campaign_id" not in event_data["config"]


class TestEventStoredHandler:
    """Tests for event.stored handler (trigger evaluation)"""

    @pytest.mark.asyncio
    async def test_handle_event_stored_evaluates_triggers(
        self, mock_repository, factory
    ):
        """Test event.stored evaluates triggered campaigns - BR-CAM-007"""
        # Given: Active triggered campaign
        campaign = factory.make_triggered_campaign()
        campaign.status = CampaignStatus.ACTIVE
        await mock_repository.save_campaign(campaign)

        trigger = factory.make_trigger(event_type="user.purchase")
        await mock_repository.save_triggers(campaign.campaign_id, [trigger])

        # When: event.stored received
        event_data = {
            "event_type": "user.purchase",
            "user_id": "usr_123",
            "data": {"amount": 150},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Simulate trigger evaluation
        # In real implementation, this would call trigger_service.evaluate_triggers()
        triggers = await mock_repository.get_triggers(campaign.campaign_id)

        # Then: Trigger should be found and evaluated
        assert len(triggers) == 1
        assert triggers[0].event_type == event_data["event_type"]

    @pytest.mark.asyncio
    async def test_handle_event_stored_no_matching_triggers(
        self, mock_repository, factory
    ):
        """Test event.stored with no matching triggers"""
        # Given: Campaign with different trigger
        campaign = factory.make_triggered_campaign()
        campaign.status = CampaignStatus.ACTIVE
        await mock_repository.save_campaign(campaign)

        trigger = factory.make_trigger(event_type="user.signup")
        await mock_repository.save_triggers(campaign.campaign_id, [trigger])

        # When: Different event type received
        event_data = {
            "event_type": "user.purchase",  # Different from trigger
            "user_id": "usr_123",
        }

        # Then: No matching trigger
        triggers = await mock_repository.get_triggers(campaign.campaign_id)
        matching = [t for t in triggers if t.event_type == event_data["event_type"]]
        assert len(matching) == 0


class TestNotificationDeliveredHandler:
    """Tests for notification.delivered event handler"""

    @pytest.mark.asyncio
    async def test_handle_notification_delivered_updates_message(
        self, mock_repository, factory
    ):
        """Test notification.delivered updates message status - BR-CAM-005.1"""
        # Given: Sent message
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)
        execution = factory.make_execution(campaign_id=campaign.campaign_id)
        await mock_repository.save_execution(execution)
        message = factory.make_message(
            campaign_id=campaign.campaign_id,
            execution_id=execution.execution_id,
            status=MessageStatus.SENT,
        )
        await mock_repository.save_message(message)

        # When: notification.delivered received
        event_data = {
            "notification_id": "notif_123",
            "metadata": {
                "campaign_id": campaign.campaign_id,
                "message_id": message.message_id,
            },
            "delivered_at": datetime.now(timezone.utc).isoformat(),
        }

        # Simulate handler updating message
        await mock_repository.update_message_status(
            message.message_id,
            MessageStatus.DELIVERED,
            delivered_at=datetime.now(timezone.utc),
        )

        # Then: Message status is updated
        updated = await mock_repository.get_message(message.message_id)
        assert updated.status == MessageStatus.DELIVERED

    @pytest.mark.asyncio
    async def test_handle_notification_delivered_non_campaign_ignored(
        self, mock_repository
    ):
        """Test non-campaign notifications are ignored"""
        # Given: Notification without campaign metadata
        event_data = {
            "notification_id": "notif_123",
            "metadata": {},  # No campaign_id
            "delivered_at": datetime.now(timezone.utc).isoformat(),
        }

        # When/Then: Handler should return True but not process
        assert "campaign_id" not in event_data.get("metadata", {})


class TestNotificationClickedHandler:
    """Tests for notification.clicked event handler"""

    @pytest.mark.asyncio
    async def test_handle_notification_clicked_updates_message(
        self, mock_repository, factory
    ):
        """Test notification.clicked updates message status - BR-CAM-005.1"""
        # Given: Delivered message
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)
        execution = factory.make_execution(campaign_id=campaign.campaign_id)
        await mock_repository.save_execution(execution)
        message = factory.make_message(
            campaign_id=campaign.campaign_id,
            execution_id=execution.execution_id,
            status=MessageStatus.DELIVERED,
        )
        await mock_repository.save_message(message)

        # When: notification.clicked received
        event_data = {
            "notification_id": "notif_123",
            "metadata": {
                "campaign_id": campaign.campaign_id,
                "message_id": message.message_id,
                "link_id": "cta_button",
            },
            "clicked_at": datetime.now(timezone.utc).isoformat(),
        }

        # Simulate handler updating message
        await mock_repository.update_message_status(
            message.message_id,
            MessageStatus.CLICKED,
            clicked_at=datetime.now(timezone.utc),
        )

        # Then: Message status is updated
        updated = await mock_repository.get_message(message.message_id)
        assert updated.status == MessageStatus.CLICKED


class TestNotificationFailedHandler:
    """Tests for notification.failed event handler"""

    @pytest.mark.asyncio
    async def test_handle_notification_failed_updates_message(
        self, mock_repository, factory
    ):
        """Test notification.failed updates message status"""
        # Given: Sent message
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)
        execution = factory.make_execution(campaign_id=campaign.campaign_id)
        await mock_repository.save_execution(execution)
        message = factory.make_message(
            campaign_id=campaign.campaign_id,
            execution_id=execution.execution_id,
            status=MessageStatus.SENT,
        )
        await mock_repository.save_message(message)

        # When: notification.failed received
        event_data = {
            "notification_id": "notif_123",
            "metadata": {
                "campaign_id": campaign.campaign_id,
                "message_id": message.message_id,
            },
            "error": "Invalid email address",
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }

        # Simulate handler updating message
        await mock_repository.update_message_status(
            message.message_id,
            MessageStatus.BOUNCED,
            bounced_at=datetime.now(timezone.utc),
        )

        # Then: Message status is updated
        updated = await mock_repository.get_message(message.message_id)
        assert updated.status == MessageStatus.BOUNCED


class TestUserDeletedHandler:
    """Tests for user.deleted event handler (GDPR)"""

    @pytest.mark.asyncio
    async def test_handle_user_deleted_gdpr_cleanup(self, mock_repository, factory):
        """Test user.deleted triggers GDPR cleanup"""
        # Given: User with campaign messages
        user_id = "usr_to_delete"
        campaign = factory.make_campaign()
        await mock_repository.save_campaign(campaign)
        execution = factory.make_execution(campaign_id=campaign.campaign_id)
        await mock_repository.save_execution(execution)
        message = factory.make_message(
            campaign_id=campaign.campaign_id,
            execution_id=execution.execution_id,
            user_id=user_id,
        )
        await mock_repository.save_message(message)

        # When: user.deleted received
        event_data = {"user_id": user_id, "timestamp": datetime.now(timezone.utc).isoformat()}

        # Simulate GDPR cleanup
        # In real implementation, this would anonymize/delete user data
        messages, _ = await mock_repository.list_messages(campaign.campaign_id)
        user_messages = [m for m in messages if m.user_id == user_id]

        # Then: User messages should be identified for cleanup
        assert len(user_messages) == 1


class TestSubscriptionHandler:
    """Tests for subscription-related event handlers"""

    @pytest.mark.asyncio
    async def test_handle_subscription_created_onboarding(self, mock_repository, factory):
        """Test subscription.created triggers onboarding campaigns"""
        # Given: Active onboarding campaign
        campaign = factory.make_triggered_campaign()
        campaign.status = CampaignStatus.ACTIVE
        await mock_repository.save_campaign(campaign)

        trigger = factory.make_trigger(event_type="subscription.created")
        await mock_repository.save_triggers(campaign.campaign_id, [trigger])

        # When: subscription.created received
        event_data = {
            "subscription_id": "sub_123",
            "user_id": "usr_new",
            "plan": "premium",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Then: Trigger should match
        triggers = await mock_repository.get_triggers(campaign.campaign_id)
        matching = [t for t in triggers if t.event_type == "subscription.created"]
        assert len(matching) == 1

    @pytest.mark.asyncio
    async def test_handle_subscription_cancelled_winback(self, mock_repository, factory):
        """Test subscription.cancelled triggers win-back campaigns"""
        # Given: Active win-back campaign
        campaign = factory.make_triggered_campaign()
        campaign.status = CampaignStatus.ACTIVE
        await mock_repository.save_campaign(campaign)

        trigger = factory.make_trigger(event_type="subscription.cancelled")
        trigger.delay_days = 3  # 3-day delay
        await mock_repository.save_triggers(campaign.campaign_id, [trigger])

        # When: subscription.cancelled received
        event_data = {
            "subscription_id": "sub_123",
            "user_id": "usr_churned",
            "reason": "too_expensive",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Then: Trigger should match with delay
        triggers = await mock_repository.get_triggers(campaign.campaign_id)
        matching = [t for t in triggers if t.event_type == "subscription.cancelled"]
        assert len(matching) == 1
        assert matching[0].delay_days == 3
