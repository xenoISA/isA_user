"""
Product Service Event Publishers

Functions to publish events from product service
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from core.nats_client import Event, EventType, ServiceSource
from .models import (
    SubscriptionCreatedEvent,
    SubscriptionStatusChangedEvent,
    ProductUsageRecordedEvent
)

logger = logging.getLogger(__name__)


async def publish_subscription_created(
    event_bus,
    subscription_id: str,
    user_id: str,
    organization_id: Optional[str],
    plan_id: str,
    plan_tier: str,
    billing_cycle: str,
    status: str,
    current_period_start: datetime,
    current_period_end: datetime,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Publish subscription.created event

    Args:
        event_bus: NATS event bus instance
        subscription_id: Subscription ID
        user_id: User ID
        organization_id: Organization ID (optional)
        plan_id: Service plan ID
        plan_tier: Plan tier
        billing_cycle: Billing cycle
        status: Subscription status
        current_period_start: Period start time
        current_period_end: Period end time
        metadata: Additional metadata (optional)

    Returns:
        True if published successfully, False otherwise
    """
    if not event_bus:
        logger.warning("Event bus not available, skipping subscription.created event")
        return False

    try:
        event_data = SubscriptionCreatedEvent(
            subscription_id=subscription_id,
            user_id=user_id,
            organization_id=organization_id,
            plan_id=plan_id,
            plan_tier=plan_tier,
            billing_cycle=billing_cycle,
            status=status,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            metadata=metadata or {}
        )

        event = Event(
            event_type=EventType.SUBSCRIPTION_CREATED,
            source=ServiceSource.PRODUCT_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published subscription.created event for subscription {subscription_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish subscription.created event: {e}")
        return False


async def publish_subscription_status_changed(
    event_bus,
    subscription_id: str,
    user_id: str,
    organization_id: Optional[str],
    plan_id: str,
    old_status: str,
    new_status: str,
    reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Publish subscription.status_changed event

    Args:
        event_bus: NATS event bus instance
        subscription_id: Subscription ID
        user_id: User ID
        organization_id: Organization ID (optional)
        plan_id: Service plan ID
        old_status: Previous status
        new_status: New status
        reason: Reason for status change (optional)
        metadata: Additional metadata (optional)

    Returns:
        True if published successfully, False otherwise
    """
    if not event_bus:
        logger.warning("Event bus not available, skipping subscription.status_changed event")
        return False

    try:
        event_data = SubscriptionStatusChangedEvent(
            subscription_id=subscription_id,
            user_id=user_id,
            organization_id=organization_id,
            plan_id=plan_id,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            metadata=metadata or {}
        )

        # Determine event type based on new status
        if new_status == "active":
            event_type = EventType.SUBSCRIPTION_ACTIVATED
        elif new_status == "canceled":
            event_type = EventType.SUBSCRIPTION_CANCELED
        elif new_status in ("incomplete_expired", "expired"):
            event_type = EventType.SUBSCRIPTION_EXPIRED
        else:
            event_type = EventType.SUBSCRIPTION_UPDATED

        event = Event(
            event_type=event_type,
            source=ServiceSource.PRODUCT_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published subscription status change event: {old_status} -> {new_status} for {subscription_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish subscription status change event: {e}")
        return False


async def publish_product_usage_recorded(
    event_bus,
    usage_record_id: str,
    user_id: str,
    organization_id: Optional[str],
    subscription_id: Optional[str],
    product_id: str,
    usage_amount: float,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    usage_details: Optional[Dict[str, Any]] = None,
    timestamp: Optional[datetime] = None
) -> bool:
    """
    Publish product.usage.recorded event

    Args:
        event_bus: NATS event bus instance
        usage_record_id: Usage record ID
        user_id: User ID
        organization_id: Organization ID (optional)
        subscription_id: Subscription ID (optional)
        product_id: Product ID
        usage_amount: Usage amount
        session_id: Session ID (optional)
        request_id: Request ID (optional)
        usage_details: Additional usage details (optional)
        timestamp: Usage timestamp (optional)

    Returns:
        True if published successfully, False otherwise
    """
    if not event_bus:
        logger.warning("Event bus not available, skipping product.usage.recorded event")
        return False

    try:
        event_data = ProductUsageRecordedEvent(
            usage_record_id=usage_record_id,
            user_id=user_id,
            organization_id=organization_id,
            subscription_id=subscription_id,
            product_id=product_id,
            usage_amount=usage_amount,
            session_id=session_id,
            request_id=request_id,
            usage_details=usage_details,
            timestamp=timestamp or datetime.utcnow()
        )

        event = Event(
            event_type=EventType.PRODUCT_USAGE_RECORDED,
            source=ServiceSource.PRODUCT_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published product.usage.recorded event for user {user_id}, product {product_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish product.usage.recorded event: {e}")
        return False
