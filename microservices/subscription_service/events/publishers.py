"""
Subscription Event Publishers

Publishes subscription-related events to the event bus.
"""

import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from .models import SubscriptionEventType

logger = logging.getLogger(__name__)


class SubscriptionEventPublisher:
    """Publisher for subscription events"""

    def __init__(self, event_bus):
        self.event_bus = event_bus

    async def publish_subscription_created(
        self,
        subscription_id: str,
        user_id: str,
        organization_id: Optional[str],
        tier_code: str,
        credits_allocated: int,
        billing_cycle: str,
        is_trial: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Publish subscription created event"""
        return await self._publish_event(
            event_type=SubscriptionEventType.SUBSCRIPTION_CREATED,
            subscription_id=subscription_id,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "tier_code": tier_code,
                "credits_allocated": credits_allocated,
                "billing_cycle": billing_cycle,
                "is_trial": is_trial,
                **(metadata or {})
            }
        )

    async def publish_subscription_canceled(
        self,
        subscription_id: str,
        user_id: str,
        organization_id: Optional[str],
        immediate: bool,
        effective_date: datetime,
        reason: Optional[str] = None
    ) -> bool:
        """Publish subscription canceled event"""
        return await self._publish_event(
            event_type=SubscriptionEventType.SUBSCRIPTION_CANCELED,
            subscription_id=subscription_id,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "immediate": immediate,
                "effective_date": effective_date.isoformat(),
                "reason": reason
            }
        )

    async def publish_credits_consumed(
        self,
        subscription_id: str,
        user_id: str,
        organization_id: Optional[str],
        credits_consumed: int,
        credits_remaining: int,
        service_type: str,
        usage_record_id: Optional[str] = None
    ) -> bool:
        """Publish credits consumed event"""
        return await self._publish_event(
            event_type=SubscriptionEventType.CREDITS_CONSUMED,
            subscription_id=subscription_id,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "credits_consumed": credits_consumed,
                "credits_remaining": credits_remaining,
                "service_type": service_type,
                "usage_record_id": usage_record_id
            }
        )

    async def publish_credits_low(
        self,
        subscription_id: str,
        user_id: str,
        organization_id: Optional[str],
        credits_remaining: int,
        credits_total: int,
        percentage_remaining: float
    ) -> bool:
        """Publish credits low warning event"""
        return await self._publish_event(
            event_type=SubscriptionEventType.CREDITS_LOW,
            subscription_id=subscription_id,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "credits_remaining": credits_remaining,
                "credits_total": credits_total,
                "percentage_remaining": percentage_remaining
            }
        )

    async def publish_credits_depleted(
        self,
        subscription_id: str,
        user_id: str,
        organization_id: Optional[str]
    ) -> bool:
        """Publish credits depleted event"""
        return await self._publish_event(
            event_type=SubscriptionEventType.CREDITS_DEPLETED,
            subscription_id=subscription_id,
            user_id=user_id,
            organization_id=organization_id,
            data={}
        )

    async def _publish_event(
        self,
        event_type: SubscriptionEventType,
        subscription_id: str,
        user_id: str,
        organization_id: Optional[str],
        data: Dict[str, Any]
    ) -> bool:
        """Internal method to publish events"""
        if not self.event_bus:
            logger.warning("Event bus not available, event not published")
            return False

        try:
            event_data = {
                "event_id": f"evt_{uuid.uuid4().hex[:16]}",
                "event_type": event_type.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "subscription_id": subscription_id,
                "user_id": user_id,
                "organization_id": organization_id,
                **data
            }

            await self.event_bus.publish(event_type.value, event_data)
            logger.debug(f"Published event: {event_type.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event {event_type.value}: {e}")
            return False


__all__ = ["SubscriptionEventPublisher"]
