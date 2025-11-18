"""
Event Publishers for Notification Service

Centralized event publishing logic for notification_service
Publishes events to NATS for other services to consume
"""

import logging
from datetime import datetime
from typing import Optional

from core.nats_client import Event, EventType, ServiceSource
from .models import (
    NotificationSentEventData,
    NotificationFailedEventData,
    NotificationDeliveredEventData,
    NotificationClickedEventData,
    NotificationBatchCompletedEventData
)

logger = logging.getLogger(__name__)


class NotificationEventPublishers:
    """Publishers for notification service events"""

    def __init__(self, event_bus):
        """
        Initialize event publishers

        Args:
            event_bus: NATS event bus instance
        """
        self.event_bus = event_bus

    async def publish_notification_sent(
        self,
        notification_id: str,
        notification_type: str,
        recipient_id: Optional[str] = None,
        recipient_email: Optional[str] = None,
        status: str = "sent",
        subject: Optional[str] = None,
        priority: str = "normal"
    ):
        """
        Publish notification.sent event

        Args:
            notification_id: Notification ID
            notification_type: Type (email, in_app, push, sms, webhook)
            recipient_id: Recipient user ID
            recipient_email: Recipient email
            status: Notification status
            subject: Notification subject
            priority: Priority level
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping notification.sent event")
            return

        try:
            event_data = NotificationSentEventData(
                notification_id=notification_id,
                notification_type=notification_type,
                recipient_id=recipient_id,
                recipient_email=recipient_email,
                status=status,
                subject=subject,
                priority=priority,
                timestamp=datetime.utcnow().isoformat()
            )

            event = Event(
                event_type=EventType.NOTIFICATION_SENT,
                source=ServiceSource.NOTIFICATION_SERVICE,
                data=event_data.model_dump()
            )

            await self.event_bus.publish_event(event)
            logger.info(f"Published notification.sent event for {notification_id}")

        except Exception as e:
            logger.error(f"Failed to publish notification.sent event: {e}")

    async def publish_notification_failed(
        self,
        notification_id: str,
        notification_type: str,
        error_message: str,
        recipient_id: Optional[str] = None,
        recipient_email: Optional[str] = None,
        retry_count: int = 0
    ):
        """
        Publish notification.failed event

        Args:
            notification_id: Notification ID
            notification_type: Type (email, in_app, push, sms, webhook)
            error_message: Error message
            recipient_id: Recipient user ID
            recipient_email: Recipient email
            retry_count: Number of retry attempts
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping notification.failed event")
            return

        try:
            event_data = NotificationFailedEventData(
                notification_id=notification_id,
                notification_type=notification_type,
                recipient_id=recipient_id,
                recipient_email=recipient_email,
                error_message=error_message,
                retry_count=retry_count,
                timestamp=datetime.utcnow().isoformat()
            )

            event = Event(
                event_type=EventType.NOTIFICATION_FAILED,
                source=ServiceSource.NOTIFICATION_SERVICE,
                data=event_data.model_dump()
            )

            await self.event_bus.publish_event(event)
            logger.info(f"Published notification.failed event for {notification_id}")

        except Exception as e:
            logger.error(f"Failed to publish notification.failed event: {e}")

    async def publish_notification_delivered(
        self,
        notification_id: str,
        notification_type: str,
        recipient_id: Optional[str] = None
    ):
        """
        Publish notification.delivered event

        Args:
            notification_id: Notification ID
            notification_type: Type (email, in_app, push, sms, webhook)
            recipient_id: Recipient user ID
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping notification.delivered event")
            return

        try:
            event_data = NotificationDeliveredEventData(
                notification_id=notification_id,
                notification_type=notification_type,
                recipient_id=recipient_id,
                delivered_at=datetime.utcnow().isoformat()
            )

            event = Event(
                event_type=EventType.NOTIFICATION_DELIVERED,
                source=ServiceSource.NOTIFICATION_SERVICE,
                data=event_data.model_dump()
            )

            await self.event_bus.publish_event(event)
            logger.info(f"Published notification.delivered event for {notification_id}")

        except Exception as e:
            logger.error(f"Failed to publish notification.delivered event: {e}")

    async def publish_notification_clicked(
        self,
        notification_id: str,
        user_id: str,
        click_url: Optional[str] = None
    ):
        """
        Publish notification.clicked event

        Args:
            notification_id: Notification ID
            user_id: User ID who clicked
            click_url: URL that was clicked
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping notification.clicked event")
            return

        try:
            event_data = NotificationClickedEventData(
                notification_id=notification_id,
                user_id=user_id,
                click_url=click_url,
                clicked_at=datetime.utcnow().isoformat()
            )

            event = Event(
                event_type=EventType.NOTIFICATION_CLICKED,
                source=ServiceSource.NOTIFICATION_SERVICE,
                data=event_data.model_dump()
            )

            await self.event_bus.publish_event(event)
            logger.info(f"Published notification.clicked event for {notification_id}")

        except Exception as e:
            logger.error(f"Failed to publish notification.clicked event: {e}")

    async def publish_batch_completed(
        self,
        batch_id: str,
        total_recipients: int,
        sent_count: int,
        delivered_count: int,
        failed_count: int
    ):
        """
        Publish notification.batch_completed event

        Args:
            batch_id: Batch ID
            total_recipients: Total number of recipients
            sent_count: Successfully sent count
            delivered_count: Delivered count
            failed_count: Failed count
        """
        if not self.event_bus:
            logger.warning("Event bus not available, skipping notification.batch_completed event")
            return

        try:
            event_data = NotificationBatchCompletedEventData(
                batch_id=batch_id,
                total_recipients=total_recipients,
                sent_count=sent_count,
                delivered_count=delivered_count,
                failed_count=failed_count,
                completed_at=datetime.utcnow().isoformat()
            )

            event = Event(
                event_type=EventType.NOTIFICATION_BATCH_COMPLETED,
                source=ServiceSource.NOTIFICATION_SERVICE,
                data=event_data.model_dump()
            )

            await self.event_bus.publish_event(event)
            logger.info(f"Published notification.batch_completed event for batch {batch_id}")

        except Exception as e:
            logger.error(f"Failed to publish notification.batch_completed event: {e}")
