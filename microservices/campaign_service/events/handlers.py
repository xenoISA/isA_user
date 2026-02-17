"""
Campaign Event Handlers

Handles incoming events from other services.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .models import (
    CampaignSubscribedEventType,
    TaskExecutedEventData,
    EventStoredEventData,
    NotificationStatusEventData,
    UserDeletedEventData,
    SubscriptionEventData,
    OrderCompletedEventData,
)
from ..models import MessageStatus, BounceType

logger = logging.getLogger(__name__)


class CampaignEventHandler:
    """Handler for campaign service subscribed events"""

    def __init__(
        self,
        campaign_service=None,
        campaign_repository=None,
    ):
        self.campaign_service = campaign_service
        self.repository = campaign_repository

    async def handle_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Route event to appropriate handler"""
        handlers = {
            CampaignSubscribedEventType.TASK_EXECUTED.value: self.handle_task_executed,
            CampaignSubscribedEventType.EVENT_STORED.value: self.handle_event_stored,
            CampaignSubscribedEventType.NOTIFICATION_DELIVERED.value: self.handle_notification_delivered,
            CampaignSubscribedEventType.NOTIFICATION_FAILED.value: self.handle_notification_failed,
            CampaignSubscribedEventType.NOTIFICATION_OPENED.value: self.handle_notification_opened,
            CampaignSubscribedEventType.NOTIFICATION_CLICKED.value: self.handle_notification_clicked,
            CampaignSubscribedEventType.USER_CREATED.value: self.handle_user_created,
            CampaignSubscribedEventType.USER_DELETED.value: self.handle_user_deleted,
            CampaignSubscribedEventType.USER_PREFERENCES_UPDATED.value: self.handle_preferences_updated,
            CampaignSubscribedEventType.SUBSCRIPTION_CREATED.value: self.handle_subscription_created,
            CampaignSubscribedEventType.SUBSCRIPTION_UPGRADED.value: self.handle_subscription_upgraded,
            CampaignSubscribedEventType.SUBSCRIPTION_CANCELLED.value: self.handle_subscription_cancelled,
            CampaignSubscribedEventType.ORDER_COMPLETED.value: self.handle_order_completed,
        }

        handler = handlers.get(event_type)
        if handler:
            try:
                await handler(data)
            except Exception as e:
                logger.error(f"Error handling event {event_type}: {e}", exc_info=True)
        else:
            logger.debug(f"No handler for event type: {event_type}")

    async def handle_task_executed(self, data: Dict[str, Any]) -> None:
        """
        Handle task.executed event - BR-CAM-001.2

        Triggered when task_service executes a scheduled campaign task.
        """
        try:
            event_data = TaskExecutedEventData(**data)

            if event_data.task_type != "campaign.execute":
                return

            campaign_id = event_data.payload.get("campaign_id")
            if not campaign_id:
                logger.warning("task.executed missing campaign_id in payload")
                return

            logger.info(f"Starting scheduled campaign execution: {campaign_id}")

            if self.campaign_service:
                # Start campaign execution
                campaign = await self.campaign_service.get_campaign(campaign_id)
                # Trigger execution logic (would be implemented in execution module)
                logger.info(f"Campaign {campaign_id} execution triggered by task {event_data.task_id}")

        except Exception as e:
            logger.error(f"Error handling task.executed: {e}", exc_info=True)

    async def handle_event_stored(self, data: Dict[str, Any]) -> None:
        """
        Handle event.stored event - BR-CAM-007

        Triggered when event_service stores an event.
        Evaluates if any triggered campaigns should fire.
        """
        try:
            event_data = EventStoredEventData(**data)

            if not self.campaign_service:
                return

            # Find active triggered campaigns with matching event_type
            # This would query campaigns with status='active' and matching triggers
            logger.debug(f"Evaluating triggers for event: {event_data.event_type}")

            # Implementation would:
            # 1. Find campaigns with triggers matching event_data.event_type
            # 2. Evaluate trigger conditions
            # 3. Fire campaigns that pass evaluation

        except Exception as e:
            logger.error(f"Error handling event.stored: {e}", exc_info=True)

    async def handle_notification_delivered(self, data: Dict[str, Any]) -> None:
        """
        Handle notification.delivered event - BR-CAM-005.1

        Updates message status when notification is delivered.
        """
        try:
            event_data = NotificationStatusEventData(**data)

            if not self.repository or not event_data.message_id:
                return

            await self.repository.update_message_status(
                event_data.message_id,
                MessageStatus.DELIVERED,
                delivered_at=datetime.now(timezone.utc),
                provider_message_id=event_data.provider_message_id,
            )

            logger.debug(f"Message delivered: {event_data.message_id}")

        except Exception as e:
            logger.error(f"Error handling notification.delivered: {e}", exc_info=True)

    async def handle_notification_failed(self, data: Dict[str, Any]) -> None:
        """
        Handle notification.failed event - BR-CAM-005.1

        Updates message status when notification fails or bounces.
        """
        try:
            event_data = NotificationStatusEventData(**data)

            if not self.repository or not event_data.message_id:
                return

            now = datetime.now(timezone.utc)

            if event_data.bounce_type:
                # Handle bounce
                bounce_type = BounceType(event_data.bounce_type) if event_data.bounce_type else BounceType.SOFT
                await self.repository.update_message_status(
                    event_data.message_id,
                    MessageStatus.BOUNCED,
                    bounced_at=now,
                    bounce_type=bounce_type,
                    error_message=event_data.error_message,
                )
            else:
                # Handle general failure
                await self.repository.update_message_status(
                    event_data.message_id,
                    MessageStatus.FAILED,
                    failed_at=now,
                    error_message=event_data.error_message,
                )

            logger.debug(f"Message failed: {event_data.message_id}")

        except Exception as e:
            logger.error(f"Error handling notification.failed: {e}", exc_info=True)

    async def handle_notification_opened(self, data: Dict[str, Any]) -> None:
        """
        Handle notification.opened event - BR-CAM-005.5

        Updates message status when email is opened (tracking pixel loaded).
        """
        try:
            event_data = NotificationStatusEventData(**data)

            if not self.repository or not event_data.message_id:
                return

            await self.repository.update_message_status(
                event_data.message_id,
                MessageStatus.OPENED,
                opened_at=datetime.now(timezone.utc),
            )

            logger.debug(f"Message opened: {event_data.message_id}")

        except Exception as e:
            logger.error(f"Error handling notification.opened: {e}", exc_info=True)

    async def handle_notification_clicked(self, data: Dict[str, Any]) -> None:
        """
        Handle notification.clicked event - BR-CAM-005.4

        Updates message status when link is clicked.
        """
        try:
            event_data = NotificationStatusEventData(**data)

            if not self.repository or not event_data.message_id:
                return

            await self.repository.update_message_status(
                event_data.message_id,
                MessageStatus.CLICKED,
                clicked_at=datetime.now(timezone.utc),
            )

            logger.debug(f"Message clicked: {event_data.message_id}")

        except Exception as e:
            logger.error(f"Error handling notification.clicked: {e}", exc_info=True)

    async def handle_user_created(self, data: Dict[str, Any]) -> None:
        """
        Handle user.created event

        Can trigger welcome/onboarding campaigns.
        """
        try:
            user_id = data.get("user_id")
            organization_id = data.get("organization_id")

            logger.debug(f"User created: {user_id} in org {organization_id}")

            # Implementation would find and trigger welcome campaigns

        except Exception as e:
            logger.error(f"Error handling user.created: {e}", exc_info=True)

    async def handle_user_deleted(self, data: Dict[str, Any]) -> None:
        """
        Handle user.deleted event - GDPR cleanup

        Removes user from all campaigns and cleans up related data.
        """
        try:
            event_data = UserDeletedEventData(**data)

            logger.info(f"GDPR cleanup for deleted user: {event_data.user_id}")

            # Implementation would:
            # 1. Remove user from all audience segments
            # 2. Cancel pending messages for user
            # 3. Anonymize historical message data

        except Exception as e:
            logger.error(f"Error handling user.deleted: {e}", exc_info=True)

    async def handle_preferences_updated(self, data: Dict[str, Any]) -> None:
        """
        Handle user.preferences.updated event

        Updates channel eligibility for user.
        """
        try:
            user_id = data.get("user_id")
            preferences = data.get("preferences", {})

            logger.debug(f"User preferences updated: {user_id}")

            # Implementation would update channel eligibility cache

        except Exception as e:
            logger.error(f"Error handling user.preferences.updated: {e}", exc_info=True)

    async def handle_subscription_created(self, data: Dict[str, Any]) -> None:
        """
        Handle subscription.created event

        Can trigger onboarding campaigns for new subscribers.
        """
        try:
            event_data = SubscriptionEventData(**data)

            logger.debug(f"Subscription created: {event_data.subscription_id}")

            # Implementation would trigger onboarding campaigns

        except Exception as e:
            logger.error(f"Error handling subscription.created: {e}", exc_info=True)

    async def handle_subscription_upgraded(self, data: Dict[str, Any]) -> None:
        """
        Handle subscription.upgraded event

        Can trigger upsell thank-you campaigns.
        """
        try:
            event_data = SubscriptionEventData(**data)

            logger.debug(f"Subscription upgraded: {event_data.subscription_id}")

            # Implementation would trigger upgrade thank-you campaigns

        except Exception as e:
            logger.error(f"Error handling subscription.upgraded: {e}", exc_info=True)

    async def handle_subscription_cancelled(self, data: Dict[str, Any]) -> None:
        """
        Handle subscription.cancelled event

        Can trigger win-back campaigns.
        """
        try:
            event_data = SubscriptionEventData(**data)

            logger.debug(f"Subscription cancelled: {event_data.subscription_id}")

            # Implementation would trigger win-back campaigns

        except Exception as e:
            logger.error(f"Error handling subscription.cancelled: {e}", exc_info=True)

    async def handle_order_completed(self, data: Dict[str, Any]) -> None:
        """
        Handle order.completed event

        Can trigger post-purchase campaigns and conversion tracking.
        """
        try:
            event_data = OrderCompletedEventData(**data)

            logger.debug(f"Order completed: {event_data.order_id}")

            # Implementation would:
            # 1. Track conversion attribution
            # 2. Trigger post-purchase campaigns

        except Exception as e:
            logger.error(f"Error handling order.completed: {e}", exc_info=True)


__all__ = ["CampaignEventHandler"]
