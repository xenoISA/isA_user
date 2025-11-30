"""
Payment Service Event Handlers

Handlers for events from other services
"""

import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


async def handle_order_created(event_data: Dict[str, Any], payment_service) -> None:
    """
    Handle order.created event

    Automatically create payment intent for new orders
    """
    try:
        order_id = event_data.get("order_id")
        user_id = event_data.get("user_id")
        amount = event_data.get("total_amount")

        if not all([order_id, user_id, amount]):
            logger.warning("order.created event missing required fields")
            return

        logger.info(f"Processing order.created event for order {order_id}")

        # Auto-create payment intent for the order
        # This is typically done via sync API call, but we can prepare here
        logger.info(f"Order {order_id} ready for payment processing")

    except Exception as e:
        logger.error(f"❌ Error handling order.created event: {e}")


async def handle_wallet_balance_changed(event_data: Dict[str, Any], payment_service) -> None:
    """
    Handle wallet.balance_changed event

    Retry failed payments when wallet balance increases
    """
    try:
        user_id = event_data.get("user_id")
        new_balance = event_data.get("new_balance")
        old_balance = event_data.get("old_balance", 0)

        if not user_id:
            logger.warning("wallet.balance_changed event missing user_id")
            return

        # If balance increased significantly, retry failed payments
        if new_balance and old_balance and new_balance > old_balance:
            logger.info(f"Wallet balance increased for user {user_id}, checking for retry opportunities")
            # TODO: Implement retry logic for failed subscription payments

    except Exception as e:
        logger.error(f"❌ Error handling wallet.balance_changed event: {e}")


async def handle_wallet_insufficient_funds(event_data: Dict[str, Any], payment_service) -> None:
    """
    Handle wallet.insufficient_funds event

    Pause subscriptions or send notifications
    """
    try:
        user_id = event_data.get("user_id")

        if not user_id:
            logger.warning("wallet.insufficient_funds event missing user_id")
            return

        logger.info(f"Processing insufficient funds event for user {user_id}")

        # Get user's active subscriptions
        # Mark them for payment retry or pause
        logger.info(f"User {user_id} has insufficient funds - subscriptions may need attention")

    except Exception as e:
        logger.error(f"❌ Error handling wallet.insufficient_funds event: {e}")


async def handle_subscription_usage_exceeded(event_data: Dict[str, Any], payment_service) -> None:
    """
    Handle subscription.usage_exceeded event from product_service

    Generate overage invoice
    """
    try:
        subscription_id = event_data.get("subscription_id")
        user_id = event_data.get("user_id")
        overage_amount = event_data.get("overage_amount")

        if not all([subscription_id, user_id]):
            logger.warning("subscription.usage_exceeded event missing required fields")
            return

        logger.info(f"Processing usage exceeded for subscription {subscription_id}")

        # Create overage invoice
        if overage_amount and float(overage_amount) > 0:
            logger.info(f"Creating overage invoice for subscription {subscription_id}, amount: {overage_amount}")
            # TODO: Implement invoice creation logic

    except Exception as e:
        logger.error(f"❌ Error handling subscription.usage_exceeded event: {e}")


async def handle_user_deleted(event_data: Dict[str, Any], payment_service) -> None:
    """
    Handle user.deleted event

    Cancel all subscriptions and process prorated refunds
    """
    try:
        user_id = event_data.get("user_id")

        if not user_id:
            logger.warning("user.deleted event missing user_id")
            return

        logger.info(f"Processing user.deleted event for user {user_id}")

        # Get all active subscriptions for this user
        # Cancel them and calculate prorated refunds
        logger.info(f"Canceling all subscriptions for deleted user {user_id}")
        # TODO: Implement subscription cancellation and refund logic

    except Exception as e:
        logger.error(f"❌ Error handling user.deleted event: {e}")


async def handle_user_upgraded(event_data: Dict[str, Any], payment_service) -> None:
    """
    Handle user.upgraded event from account_service

    Automatically upgrade subscription tier
    """
    try:
        user_id = event_data.get("user_id")
        new_tier = event_data.get("new_tier")

        if not all([user_id, new_tier]):
            logger.warning("user.upgraded event missing required fields")
            return

        logger.info(f"Processing user upgrade for user {user_id} to tier {new_tier}")

        # Find active subscription and upgrade to matching tier
        logger.info(f"Checking for subscription upgrade opportunities for user {user_id}")
        # TODO: Implement automatic subscription tier upgrade

    except Exception as e:
        logger.error(f"❌ Error handling user.upgraded event: {e}")


def get_event_handlers(payment_service) -> Dict[str, callable]:
    """
    Return a mapping of event patterns to handler functions

    Event patterns include the service prefix for proper event routing.
    This will be used in main.py to register event subscriptions.

    Args:
        payment_service: PaymentService instance for data access

    Returns:
        Dict mapping event patterns to handler functions
    """
    return {
        "order_service.order.created": lambda event: handle_order_created(event.data, payment_service),
        "wallet_service.wallet.balance_changed": lambda event: handle_wallet_balance_changed(event.data, payment_service),
        "wallet_service.wallet.insufficient_funds": lambda event: handle_wallet_insufficient_funds(event.data, payment_service),
        "product_service.subscription.usage_exceeded": lambda event: handle_subscription_usage_exceeded(event.data, payment_service),
        "account_service.user.deleted": lambda event: handle_user_deleted(event.data, payment_service),
        "account_service.user.upgraded": lambda event: handle_user_upgraded(event.data, payment_service),
    }
