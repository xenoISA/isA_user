"""
Product Service Event Handlers

Handlers for events from other services
"""

import logging
from typing import Dict, Any

from core.nats_client import EventType

logger = logging.getLogger(__name__)


async def handle_payment_completed(event_data: Dict[str, Any], product_service) -> None:
    """
    Handle payment.completed event

    When payment is completed for a subscription, activate it

    Args:
        event_data: Event data containing payment details
        product_service: ProductService instance
    """
    try:
        subscription_id = event_data.get("subscription_id")
        if not subscription_id:
            logger.warning("payment.completed event missing subscription_id")
            return

        logger.info(f"Processing payment.completed event for subscription {subscription_id}")

        # Update subscription status to active
        from ..models import SubscriptionStatus
        await product_service.update_subscription_status(
            subscription_id=subscription_id,
            status=SubscriptionStatus.ACTIVE
        )

        logger.info(f"✅ Subscription {subscription_id} activated after payment completion")

    except Exception as e:
        logger.error(f"❌ Error handling payment.completed event: {e}")


async def handle_wallet_insufficient_funds(event_data: Dict[str, Any], product_service) -> None:
    """
    Handle wallet.insufficient_funds event

    When wallet has insufficient funds, suspend related subscriptions

    Args:
        event_data: Event data containing wallet details
        product_service: ProductService instance
    """
    try:
        user_id = event_data.get("user_id")
        if not user_id:
            logger.warning("wallet.insufficient_funds event missing user_id")
            return

        logger.info(f"Processing wallet.insufficient_funds event for user {user_id}")

        # Get user's active subscriptions
        from ..models import SubscriptionStatus
        subscriptions = await product_service.get_user_subscriptions(
            user_id=user_id,
            status=SubscriptionStatus.ACTIVE
        )

        # Suspend subscriptions due to insufficient funds
        for subscription in subscriptions:
            await product_service.update_subscription_status(
                subscription_id=subscription.subscription_id,
                status=SubscriptionStatus.PAST_DUE
            )
            logger.info(f"Subscription {subscription.subscription_id} suspended due to insufficient funds")

        logger.info(f"✅ Processed {len(subscriptions)} subscriptions for user {user_id}")

    except Exception as e:
        logger.error(f"❌ Error handling wallet.insufficient_funds event: {e}")


async def handle_user_deleted(event_data: Dict[str, Any], product_service) -> None:
    """
    Handle user.deleted event

    When user is deleted, cancel all their subscriptions

    Args:
        event_data: Event data containing user details
        product_service: ProductService instance
    """
    try:
        user_id = event_data.get("user_id")
        if not user_id:
            logger.warning("user.deleted event missing user_id")
            return

        logger.info(f"Processing user.deleted event for user {user_id}")

        # Get all user subscriptions
        subscriptions = await product_service.get_user_subscriptions(user_id=user_id)

        # Cancel all subscriptions
        from ..models import SubscriptionStatus
        for subscription in subscriptions:
            if subscription.status not in [SubscriptionStatus.CANCELED, SubscriptionStatus.INCOMPLETE_EXPIRED]:
                await product_service.update_subscription_status(
                    subscription_id=subscription.subscription_id,
                    status=SubscriptionStatus.CANCELED
                )
                logger.info(f"Subscription {subscription.subscription_id} canceled due to user deletion")

        logger.info(f"✅ Canceled {len(subscriptions)} subscriptions for deleted user {user_id}")

    except Exception as e:
        logger.error(f"❌ Error handling user.deleted event: {e}")


async def register_event_handlers(event_bus, product_service) -> None:
    """
    Register all event handlers for product service

    Args:
        event_bus: NATS event bus instance
        product_service: ProductService instance
    """
    if not event_bus:
        logger.warning("Event bus not available, skipping event handler registration")
        return

    try:
        # Register handler for payment.completed
        await event_bus.subscribe(
            EventType.PAYMENT_COMPLETED,
            lambda data: handle_payment_completed(data, product_service)
        )
        logger.info("✅ Registered handler for payment.completed event")

        # Register handler for wallet.insufficient_funds
        await event_bus.subscribe(
            EventType.WALLET_INSUFFICIENT_FUNDS,
            lambda data: handle_wallet_insufficient_funds(data, product_service)
        )
        logger.info("✅ Registered handler for wallet.insufficient_funds event")

        # Register handler for user.deleted
        await event_bus.subscribe(
            EventType.USER_DELETED,
            lambda data: handle_user_deleted(data, product_service)
        )
        logger.info("✅ Registered handler for user.deleted event")

        logger.info("✅ All event handlers registered successfully")

    except Exception as e:
        logger.error(f"❌ Error registering event handlers: {e}")
