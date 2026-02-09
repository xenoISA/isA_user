"""
Campaign Event Publishers

Publishes events to NATS JetStream.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .models import (
    CampaignEventType,
    CampaignCreatedEventData,
    CampaignUpdatedEventData,
    CampaignScheduledEventData,
    CampaignActivatedEventData,
    CampaignStartedEventData,
    CampaignPausedEventData,
    CampaignResumedEventData,
    CampaignCompletedEventData,
    CampaignCancelledEventData,
    CampaignMessageEventData,
    CampaignMetricUpdatedEventData,
)

logger = logging.getLogger(__name__)


class CampaignEventPublisher:
    """Publisher for campaign service events"""

    def __init__(self, nats_client=None):
        self.nats_client = nats_client
        self.source = "campaign_service"

    async def publish(
        self,
        event_type: CampaignEventType,
        data: Dict[str, Any],
    ) -> bool:
        """
        Publish an event to NATS.

        Args:
            event_type: The event type enum
            data: Event data payload

        Returns:
            True if published successfully, False otherwise
        """
        if not self.nats_client:
            logger.debug(f"NATS client not configured, skipping publish: {event_type.value}")
            return False

        try:
            event = {
                "event_type": event_type.value,
                "source": self.source,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data,
            }

            await self.nats_client.publish(event_type.value, event)
            logger.debug(f"Published event: {event_type.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event {event_type.value}: {e}")
            return False

    # ====================
    # Campaign Lifecycle Events
    # ====================

    async def publish_campaign_created(
        self,
        campaign_id: str,
        organization_id: str,
        name: str,
        campaign_type: str,
        created_by: str,
        cloned_from_id: Optional[str] = None,
    ) -> bool:
        """Publish campaign.created event"""
        data = CampaignCreatedEventData(
            campaign_id=campaign_id,
            organization_id=organization_id,
            name=name,
            campaign_type=campaign_type,
            status="draft",
            created_by=created_by,
            cloned_from_id=cloned_from_id,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.CREATED, data.model_dump())

    async def publish_campaign_updated(
        self,
        campaign_id: str,
        changed_fields: list,
        updated_by: str,
    ) -> bool:
        """Publish campaign.updated event"""
        data = CampaignUpdatedEventData(
            campaign_id=campaign_id,
            changed_fields=changed_fields,
            updated_by=updated_by,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.UPDATED, data.model_dump())

    async def publish_campaign_scheduled(
        self,
        campaign_id: str,
        scheduled_at: str,
        task_id: Optional[str] = None,
    ) -> bool:
        """Publish campaign.scheduled event"""
        data = CampaignScheduledEventData(
            campaign_id=campaign_id,
            scheduled_at=scheduled_at,
            task_id=task_id,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.SCHEDULED, data.model_dump())

    async def publish_campaign_activated(
        self,
        campaign_id: str,
        trigger_count: int,
    ) -> bool:
        """Publish campaign.activated event"""
        data = CampaignActivatedEventData(
            campaign_id=campaign_id,
            activated_at=datetime.now(timezone.utc).isoformat(),
            trigger_count=trigger_count,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.ACTIVATED, data.model_dump())

    async def publish_campaign_started(
        self,
        campaign_id: str,
        execution_id: str,
        audience_size: int,
        holdout_size: int,
    ) -> bool:
        """Publish campaign.started event"""
        data = CampaignStartedEventData(
            campaign_id=campaign_id,
            execution_id=execution_id,
            audience_size=audience_size,
            holdout_size=holdout_size,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.STARTED, data.model_dump())

    async def publish_campaign_paused(
        self,
        campaign_id: str,
        paused_by: Optional[str],
        messages_sent: int,
        messages_remaining: int,
        execution_id: Optional[str] = None,
    ) -> bool:
        """Publish campaign.paused event"""
        data = CampaignPausedEventData(
            campaign_id=campaign_id,
            execution_id=execution_id,
            paused_by=paused_by,
            messages_sent=messages_sent,
            messages_remaining=messages_remaining,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.PAUSED, data.model_dump())

    async def publish_campaign_resumed(
        self,
        campaign_id: str,
        resumed_by: Optional[str],
        messages_remaining: int,
        execution_id: Optional[str] = None,
    ) -> bool:
        """Publish campaign.resumed event"""
        data = CampaignResumedEventData(
            campaign_id=campaign_id,
            execution_id=execution_id,
            resumed_by=resumed_by,
            messages_remaining=messages_remaining,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.RESUMED, data.model_dump())

    async def publish_campaign_completed(
        self,
        campaign_id: str,
        execution_id: str,
        total_sent: int,
        total_delivered: int,
        total_failed: int,
        duration_minutes: int,
    ) -> bool:
        """Publish campaign.completed event"""
        data = CampaignCompletedEventData(
            campaign_id=campaign_id,
            execution_id=execution_id,
            total_sent=total_sent,
            total_delivered=total_delivered,
            total_failed=total_failed,
            duration_minutes=duration_minutes,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.COMPLETED, data.model_dump())

    async def publish_campaign_cancelled(
        self,
        campaign_id: str,
        cancelled_by: Optional[str],
        reason: Optional[str],
        messages_sent_before_cancel: int,
    ) -> bool:
        """Publish campaign.cancelled event"""
        data = CampaignCancelledEventData(
            campaign_id=campaign_id,
            cancelled_by=cancelled_by,
            reason=reason,
            messages_sent_before_cancel=messages_sent_before_cancel,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.CANCELLED, data.model_dump())

    # ====================
    # Message Events
    # ====================

    async def publish_message_queued(
        self,
        campaign_id: str,
        message_id: str,
        execution_id: str,
        user_id: str,
        channel_type: str,
        variant_id: Optional[str] = None,
    ) -> bool:
        """Publish campaign.message.queued event"""
        data = CampaignMessageEventData(
            campaign_id=campaign_id,
            message_id=message_id,
            execution_id=execution_id,
            user_id=user_id,
            variant_id=variant_id,
            channel_type=channel_type,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.MESSAGE_QUEUED, data.model_dump())

    async def publish_message_sent(
        self,
        campaign_id: str,
        message_id: str,
        notification_id: str,
        provider_message_id: Optional[str] = None,
    ) -> bool:
        """Publish campaign.message.sent event"""
        data = CampaignMessageEventData(
            campaign_id=campaign_id,
            message_id=message_id,
            notification_id=notification_id,
            provider_message_id=provider_message_id,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.MESSAGE_SENT, data.model_dump())

    async def publish_message_delivered(
        self,
        campaign_id: str,
        message_id: str,
    ) -> bool:
        """Publish campaign.message.delivered event"""
        data = CampaignMessageEventData(
            campaign_id=campaign_id,
            message_id=message_id,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.MESSAGE_DELIVERED, data.model_dump())

    async def publish_message_opened(
        self,
        campaign_id: str,
        message_id: str,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Publish campaign.message.opened event"""
        data = CampaignMessageEventData(
            campaign_id=campaign_id,
            message_id=message_id,
            user_agent=user_agent,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.MESSAGE_OPENED, data.model_dump())

    async def publish_message_clicked(
        self,
        campaign_id: str,
        message_id: str,
        link_id: str,
        link_url: str,
    ) -> bool:
        """Publish campaign.message.clicked event"""
        data = CampaignMessageEventData(
            campaign_id=campaign_id,
            message_id=message_id,
            link_id=link_id,
            link_url=link_url,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.MESSAGE_CLICKED, data.model_dump())

    async def publish_message_converted(
        self,
        campaign_id: str,
        message_id: str,
        conversion_event: str,
        conversion_value: Optional[float] = None,
        attribution_model: str = "last_touch",
    ) -> bool:
        """Publish campaign.message.converted event"""
        data = CampaignMessageEventData(
            campaign_id=campaign_id,
            message_id=message_id,
            conversion_event=conversion_event,
            conversion_value=conversion_value,
            attribution_model=attribution_model,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.MESSAGE_CONVERTED, data.model_dump())

    async def publish_message_bounced(
        self,
        campaign_id: str,
        message_id: str,
        bounce_type: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Publish campaign.message.bounced event"""
        data = CampaignMessageEventData(
            campaign_id=campaign_id,
            message_id=message_id,
            bounce_type=bounce_type,
            error_reason=reason,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.MESSAGE_BOUNCED, data.model_dump())

    async def publish_message_unsubscribed(
        self,
        campaign_id: str,
        message_id: str,
        user_id: str,
        channel_type: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Publish campaign.message.unsubscribed event"""
        data = CampaignMessageEventData(
            campaign_id=campaign_id,
            message_id=message_id,
            user_id=user_id,
            channel_type=channel_type,
            error_reason=reason,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.MESSAGE_UNSUBSCRIBED, data.model_dump())

    # ====================
    # Metric Events
    # ====================

    async def publish_metric_updated(
        self,
        campaign_id: str,
        metric_type: str,
        count: int,
        rate: Optional[float] = None,
    ) -> bool:
        """Publish campaign.metric.updated event"""
        data = CampaignMetricUpdatedEventData(
            campaign_id=campaign_id,
            metric_type=metric_type,
            count=count,
            rate=rate,
            timestamp=datetime.now(timezone.utc),
        )
        return await self.publish(CampaignEventType.METRIC_UPDATED, data.model_dump())


__all__ = ["CampaignEventPublisher"]
