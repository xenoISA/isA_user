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
            event_type="subscription.created",
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
            event_type="subscription.canceled",
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

    async def publish_subscription_renewed(
        self,
        subscription_id: str,
        user_id: str,
        organization_id: Optional[str],
        new_period_start: datetime,
        new_period_end: datetime,
        credits_allocated: int,
        amount_charged: Optional[float] = None
    ) -> bool:
        """Publish subscription renewed event"""
        return await self._publish_event(
            event_type=SubscriptionEventType.SUBSCRIPTION_RENEWED,
            subscription_id=subscription_id,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "new_period_start": new_period_start.isoformat(),
                "new_period_end": new_period_end.isoformat(),
                "credits_allocated": credits_allocated,
                "amount_charged": amount_charged
            }
        )

    async def publish_subscription_paused(
        self,
        subscription_id: str,
        user_id: str,
        organization_id: Optional[str],
        paused_at: datetime,
        reason: Optional[str] = None
    ) -> bool:
        """Publish subscription paused event"""
        return await self._publish_event(
            event_type=SubscriptionEventType.SUBSCRIPTION_PAUSED,
            subscription_id=subscription_id,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "paused_at": paused_at.isoformat(),
                "reason": reason
            }
        )

    async def publish_subscription_resumed(
        self,
        subscription_id: str,
        user_id: str,
        organization_id: Optional[str],
        resumed_at: datetime
    ) -> bool:
        """Publish subscription resumed event"""
        return await self._publish_event(
            event_type=SubscriptionEventType.SUBSCRIPTION_RESUMED,
            subscription_id=subscription_id,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "resumed_at": resumed_at.isoformat()
            }
        )

    async def publish_subscription_expired(
        self,
        subscription_id: str,
        user_id: str,
        organization_id: Optional[str],
        expired_at: datetime,
        reason: str = "period_ended"
    ) -> bool:
        """Publish subscription expired event"""
        return await self._publish_event(
            event_type=SubscriptionEventType.SUBSCRIPTION_EXPIRED,
            subscription_id=subscription_id,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "expired_at": expired_at.isoformat(),
                "reason": reason
            }
        )

    async def publish_subscription_upgraded(
        self,
        subscription_id: str,
        user_id: str,
        organization_id: Optional[str],
        old_tier: str,
        new_tier: str,
        prorated_amount: Optional[float] = None
    ) -> bool:
        """Publish subscription upgraded event"""
        return await self._publish_event(
            event_type=SubscriptionEventType.SUBSCRIPTION_UPGRADED,
            subscription_id=subscription_id,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "old_tier": old_tier,
                "new_tier": new_tier,
                "prorated_amount": prorated_amount
            }
        )

    async def publish_subscription_downgraded(
        self,
        subscription_id: str,
        user_id: str,
        organization_id: Optional[str],
        old_tier: str,
        new_tier: str,
        effective_date: datetime
    ) -> bool:
        """Publish subscription downgraded event"""
        return await self._publish_event(
            event_type=SubscriptionEventType.SUBSCRIPTION_DOWNGRADED,
            subscription_id=subscription_id,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "old_tier": old_tier,
                "new_tier": new_tier,
                "effective_date": effective_date.isoformat()
            }
        )

    async def publish_trial_started(
        self,
        subscription_id: str,
        user_id: str,
        organization_id: Optional[str],
        trial_end_date: datetime,
        trial_tier: str
    ) -> bool:
        """Publish trial started event"""
        return await self._publish_event(
            event_type=SubscriptionEventType.TRIAL_STARTED,
            subscription_id=subscription_id,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "trial_end_date": trial_end_date.isoformat(),
                "trial_tier": trial_tier
            }
        )

    async def publish_trial_ending_soon(
        self,
        subscription_id: str,
        user_id: str,
        organization_id: Optional[str],
        trial_end_date: datetime,
        days_remaining: int
    ) -> bool:
        """Publish trial ending soon warning event"""
        return await self._publish_event(
            event_type=SubscriptionEventType.TRIAL_ENDING_SOON,
            subscription_id=subscription_id,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "trial_end_date": trial_end_date.isoformat(),
                "days_remaining": days_remaining
            }
        )

    async def publish_trial_ended(
        self,
        subscription_id: str,
        user_id: str,
        organization_id: Optional[str],
        converted_to_paid: bool,
        new_tier: Optional[str] = None
    ) -> bool:
        """Publish trial ended event"""
        return await self._publish_event(
            event_type=SubscriptionEventType.TRIAL_ENDED,
            subscription_id=subscription_id,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "converted_to_paid": converted_to_paid,
                "new_tier": new_tier
            }
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
