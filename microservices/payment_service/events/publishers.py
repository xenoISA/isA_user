"""
Payment Service Event Publishers

Functions to publish events from payment service
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from core.nats_client import Event, EventType, ServiceSource
from .models import (
    PaymentCompletedEvent,
    PaymentFailedEvent,
    PaymentRefundedEvent,
    PaymentIntentCreatedEvent,
    SubscriptionCreatedEvent,
    SubscriptionCanceledEvent,
    SubscriptionUpdatedEvent,
    InvoiceCreatedEvent,
    InvoicePaidEvent
)

logger = logging.getLogger(__name__)


async def publish_payment_completed(
    event_bus,
    payment_intent_id: str,
    user_id: str,
    amount: float,
    currency: str = "USD",
    payment_id: Optional[str] = None,
    payment_method: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish payment.completed event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping payment.completed event")
        return False

    try:
        event_data = PaymentCompletedEvent(
            payment_intent_id=payment_intent_id,
            payment_id=payment_id,
            user_id=user_id,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            metadata=metadata or {}
        )

        event = Event(
            event_type=EventType.PAYMENT_COMPLETED,
            source=ServiceSource.PAYMENT_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published payment.completed event for payment {payment_intent_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish payment.completed event: {e}")
        return False


async def publish_payment_failed(
    event_bus,
    payment_intent_id: str,
    user_id: str,
    amount: float,
    currency: str = "USD",
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish payment.failed event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping payment.failed event")
        return False

    try:
        event_data = PaymentFailedEvent(
            payment_intent_id=payment_intent_id,
            user_id=user_id,
            amount=amount,
            currency=currency,
            error_code=error_code,
            error_message=error_message,
            metadata=metadata or {}
        )

        event = Event(
            event_type=EventType.PAYMENT_FAILED,
            source=ServiceSource.PAYMENT_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published payment.failed event for payment {payment_intent_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish payment.failed event: {e}")
        return False


async def publish_payment_refunded(
    event_bus,
    payment_id: str,
    refund_id: str,
    user_id: str,
    amount: float,
    currency: str = "USD",
    reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish payment.refunded event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping payment.refunded event")
        return False

    try:
        event_data = PaymentRefundedEvent(
            payment_id=payment_id,
            refund_id=refund_id,
            user_id=user_id,
            amount=amount,
            currency=currency,
            reason=reason,
            metadata=metadata or {}
        )

        event = Event(
            event_type=EventType.PAYMENT_REFUNDED,
            source=ServiceSource.PAYMENT_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published payment.refunded event for payment {payment_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish payment.refunded event: {e}")
        return False


async def publish_payment_intent_created(
    event_bus,
    payment_intent_id: str,
    user_id: str,
    amount: float,
    currency: str = "USD",
    order_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish payment.intent.created event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping payment.intent.created event")
        return False

    try:
        event_data = PaymentIntentCreatedEvent(
            payment_intent_id=payment_intent_id,
            user_id=user_id,
            amount=amount,
            currency=currency,
            order_id=order_id,
            metadata=metadata or {}
        )

        event = Event(
            event_type=EventType.PAYMENT_INTENT_CREATED,
            source=ServiceSource.PAYMENT_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published payment.intent.created event for {payment_intent_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish payment.intent.created event: {e}")
        return False


async def publish_subscription_created(
    event_bus,
    subscription_id: str,
    user_id: str,
    plan_id: str,
    status: str,
    current_period_start: datetime,
    current_period_end: datetime,
    trial_end: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish subscription.created event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping subscription.created event")
        return False

    try:
        event_data = SubscriptionCreatedEvent(
            subscription_id=subscription_id,
            user_id=user_id,
            plan_id=plan_id,
            status=status,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            trial_end=trial_end,
            metadata=metadata or {}
        )

        event = Event(
            event_type=EventType.SUBSCRIPTION_CREATED,
            source=ServiceSource.PAYMENT_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published subscription.created event for subscription {subscription_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish subscription.created event: {e}")
        return False


async def publish_subscription_canceled(
    event_bus,
    subscription_id: str,
    user_id: str,
    canceled_at: datetime,
    plan_id: Optional[str] = None,
    reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish subscription.canceled event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping subscription.canceled event")
        return False

    try:
        event_data = SubscriptionCanceledEvent(
            subscription_id=subscription_id,
            user_id=user_id,
            plan_id=plan_id,
            canceled_at=canceled_at,
            reason=reason,
            metadata=metadata or {}
        )

        event = Event(
            event_type=EventType.SUBSCRIPTION_CANCELED,
            source=ServiceSource.PAYMENT_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published subscription.canceled event for subscription {subscription_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish subscription.canceled event: {e}")
        return False


async def publish_subscription_updated(
    event_bus,
    subscription_id: str,
    user_id: str,
    old_plan_id: Optional[str] = None,
    new_plan_id: Optional[str] = None,
    old_status: Optional[str] = None,
    new_status: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish subscription.updated event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping subscription.updated event")
        return False

    try:
        event_data = SubscriptionUpdatedEvent(
            subscription_id=subscription_id,
            user_id=user_id,
            old_plan_id=old_plan_id,
            new_plan_id=new_plan_id,
            old_status=old_status,
            new_status=new_status,
            changes=changes
        )

        event = Event(
            event_type=EventType.SUBSCRIPTION_UPDATED,
            source=ServiceSource.PAYMENT_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published subscription.updated event for subscription {subscription_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish subscription.updated event: {e}")
        return False


async def publish_invoice_created(
    event_bus,
    invoice_id: str,
    user_id: str,
    amount_due: float,
    currency: str = "USD",
    subscription_id: Optional[str] = None,
    due_date: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Publish invoice.created event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping invoice.created event")
        return False

    try:
        event_data = InvoiceCreatedEvent(
            invoice_id=invoice_id,
            user_id=user_id,
            subscription_id=subscription_id,
            amount_due=amount_due,
            currency=currency,
            due_date=due_date,
            metadata=metadata or {}
        )

        event = Event(
            event_type=EventType.INVOICE_CREATED,
            source=ServiceSource.PAYMENT_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published invoice.created event for invoice {invoice_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish invoice.created event: {e}")
        return False


async def publish_invoice_paid(
    event_bus,
    invoice_id: str,
    payment_id: str,
    user_id: str,
    amount_paid: float,
    currency: str = "USD",
    paid_at: Optional[datetime] = None
) -> bool:
    """Publish invoice.paid event"""
    if not event_bus:
        logger.warning("Event bus not available, skipping invoice.paid event")
        return False

    try:
        event_data = InvoicePaidEvent(
            invoice_id=invoice_id,
            payment_id=payment_id,
            user_id=user_id,
            amount_paid=amount_paid,
            currency=currency,
            paid_at=paid_at or datetime.utcnow()
        )

        event = Event(
            event_type=EventType.INVOICE_PAID,
            source=ServiceSource.PAYMENT_SERVICE,
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"✅ Published invoice.paid event for invoice {invoice_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to publish invoice.paid event: {e}")
        return False
