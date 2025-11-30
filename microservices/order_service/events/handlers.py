"""
Order Service Event Handlers

Handlers for events from other services
MIGRATED from main.py:67-142 + new handlers
"""

import logging
from typing import Dict, Any
from datetime import datetime
from decimal import Decimal

from core.nats_client import EventType

logger = logging.getLogger(__name__)

# Idempotency tracking (moved from main.py)
processed_event_ids = set()


def is_event_processed(event_id: str) -> bool:
    """Check if event has already been processed (idempotency)"""
    return event_id in processed_event_ids


def mark_event_processed(event_id: str):
    """Mark event as processed"""
    global processed_event_ids
    processed_event_ids.add(event_id)
    # Limit size to prevent memory issues
    if len(processed_event_ids) > 10000:
        processed_event_ids = set(list(processed_event_ids)[5000:])


async def handle_payment_completed(event_data: Dict[str, Any], order_service, event_id: str = None) -> None:
    """
    Handle payment.completed event
    Automatically complete order after successful payment

    MIGRATED from main.py:67-105
    """
    try:
        if event_id and is_event_processed(event_id):
            logger.debug(f"Event {event_id} already processed, skipping")
            return

        payment_intent_id = event_data.get("payment_intent_id")
        user_id = event_data.get("user_id")
        amount = event_data.get("amount")

        if not payment_intent_id:
            logger.warning(f"payment.completed event missing payment_intent_id")
            return

        # Find order by payment_intent_id
        order = await order_service.repository.get_order_by_payment_intent(payment_intent_id)
        if not order:
            logger.warning(f"No order found for payment_intent_id: {payment_intent_id}")
            if event_id:
                mark_event_processed(event_id)
            return

        # Update order status to completed
        from ..models import OrderCompleteRequest
        complete_request = OrderCompleteRequest(
            payment_confirmed=True,
            transaction_id=event_data.get("payment_id") or event_data.get("transaction_id"),
            credits_added=Decimal(str(amount)) if amount else None
        )

        await order_service.complete_order(order.order_id, complete_request)

        if event_id:
            mark_event_processed(event_id)
        logger.info(f"✅ Order {order.order_id} completed after payment success")

    except Exception as e:
        logger.error(f"❌ Failed to handle payment.completed event: {e}")


async def handle_payment_failed(event_data: Dict[str, Any], order_service, event_id: str = None) -> None:
    """
    Handle payment.failed event
    Mark order as payment failed

    MIGRATED from main.py:108-142
    """
    try:
        if event_id and is_event_processed(event_id):
            logger.debug(f"Event {event_id} already processed, skipping")
            return

        payment_intent_id = event_data.get("payment_intent_id")

        if not payment_intent_id:
            logger.warning(f"payment.failed event missing payment_intent_id")
            return

        # Find order by payment_intent_id
        order = await order_service.repository.get_order_by_payment_intent(payment_intent_id)
        if not order:
            logger.warning(f"No order found for payment_intent_id: {payment_intent_id}")
            if event_id:
                mark_event_processed(event_id)
            return

        # Update order status to failed
        from ..models import OrderStatus, PaymentStatus
        await order_service.repository.update_order_status(
            order.order_id,
            OrderStatus.FAILED,
            payment_status=PaymentStatus.FAILED
        )

        if event_id:
            mark_event_processed(event_id)
        logger.info(f"✅ Order {order.order_id} marked as failed after payment failure")

    except Exception as e:
        logger.error(f"❌ Failed to handle payment.failed event: {e}")


async def handle_payment_refunded(event_data: Dict[str, Any], order_service) -> None:
    """
    Handle payment.refunded event
    Update order status to refunded

    NEW handler
    """
    try:
        payment_id = event_data.get("payment_id")
        refund_amount = event_data.get("amount")

        if not payment_id:
            logger.warning("payment.refunded event missing payment_id")
            return

        logger.info(f"Processing payment refund for payment {payment_id}, amount: {refund_amount}")

        # Find orders associated with this payment
        # Update status to refunded
        # TODO: Implement order lookup by payment_id

    except Exception as e:
        logger.error(f"❌ Failed to handle payment.refunded event: {e}")


async def handle_wallet_credits_added(event_data: Dict[str, Any], order_service) -> None:
    """
    Handle wallet.credits_added event
    Auto-fulfill pending wallet top-up orders

    NEW handler
    """
    try:
        user_id = event_data.get("user_id")
        amount = event_data.get("amount")

        if not user_id:
            logger.warning("wallet.credits_added event missing user_id")
            return

        logger.info(f"Wallet credits added for user {user_id}, amount: {amount}")

        # Find pending wallet orders for this user
        # Mark them as completed
        # TODO: Implement pending wallet order completion

    except Exception as e:
        logger.error(f"❌ Failed to handle wallet.credits_added event: {e}")


async def handle_subscription_created(event_data: Dict[str, Any], order_service) -> None:
    """
    Handle subscription.created event
    Create recurring order record

    NEW handler
    """
    try:
        subscription_id = event_data.get("subscription_id")
        user_id = event_data.get("user_id")

        if not all([subscription_id, user_id]):
            logger.warning("subscription.created event missing required fields")
            return

        logger.info(f"Subscription created: {subscription_id} for user {user_id}")

        # Create recurring order record for subscription billing
        # TODO: Implement subscription order creation

    except Exception as e:
        logger.error(f"❌ Failed to handle subscription.created event: {e}")


async def handle_subscription_canceled(event_data: Dict[str, Any], order_service) -> None:
    """
    Handle subscription.canceled event
    Cancel pending subscription orders

    NEW handler
    """
    try:
        subscription_id = event_data.get("subscription_id")
        user_id = event_data.get("user_id")

        if not subscription_id:
            logger.warning("subscription.canceled event missing subscription_id")
            return

        logger.info(f"Subscription canceled: {subscription_id}")

        # Cancel any pending orders for this subscription
        # TODO: Implement subscription order cancellation

    except Exception as e:
        logger.error(f"❌ Failed to handle subscription.canceled event: {e}")


async def handle_user_deleted(event_data: Dict[str, Any], order_service) -> None:
    """
    Handle user.deleted event
    Cancel all pending orders for deleted user

    NEW handler
    """
    try:
        user_id = event_data.get("user_id")

        if not user_id:
            logger.warning("user.deleted event missing user_id")
            return

        logger.info(f"Processing user deletion for user {user_id}")

        # Find all pending/active orders for this user
        # Cancel them
        from ..models import OrderStatus
        # TODO: Implement bulk order cancellation for deleted user

    except Exception as e:
        logger.error(f"❌ Failed to handle user.deleted event: {e}")


def get_event_handlers(order_service):
    """
    Get all event handlers for order service.

    Returns a dict mapping event patterns to handler functions.
    This is used by main.py to register all event subscriptions.

    Args:
        order_service: OrderService instance

    Returns:
        Dict[str, callable]: Event pattern -> handler function mapping
    """
    return {
        "payment_service.payment.completed": lambda event: handle_payment_completed(
            event.data, order_service, event.id
        ),
        "payment_service.payment.failed": lambda event: handle_payment_failed(
            event.data, order_service, event.id
        ),
        "payment_service.payment.refunded": lambda event: handle_payment_refunded(
            event.data, order_service
        ),
        "wallet_service.wallet.credits_added": lambda event: handle_wallet_credits_added(
            event.data, order_service
        ),
        "billing_service.subscription.created": lambda event: handle_subscription_created(
            event.data, order_service
        ),
        "billing_service.subscription.canceled": lambda event: handle_subscription_canceled(
            event.data, order_service
        ),
        "account_service.user.deleted": lambda event: handle_user_deleted(
            event.data, order_service
        ),
    }
