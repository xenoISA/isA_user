"""
Order Service Event Handlers

Handlers for events from other services
MIGRATED from main.py:67-142 + new handlers
"""

import logging
from typing import Dict, Any
from datetime import datetime
from decimal import Decimal


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

        # Commit inventory and create shipment for shippable items
        if order_service.inventory_client and order_service.fulfillment_client:
            items = []
            for i in (order.items or []):
                if hasattr(i, "model_dump"):
                    items.append(i.model_dump())
                else:
                    items.append(i)
            shippable_items = [i for i in items if i.get("fulfillment_type") == "ship"]
            if shippable_items and order.shipping_address:
                address = order.shipping_address.model_dump() if hasattr(order.shipping_address, "model_dump") else order.shipping_address
                await order_service.inventory_client.commit(order.order_id)
                shipment = await order_service.fulfillment_client.create_shipment(
                    order_id=order.order_id,
                    items=shippable_items,
                    address=address
                )
                if shipment and shipment.get("tracking_number"):
                    await order_service.repository.update_order(
                        order_id=order.order_id,
                        fulfillment_status="shipped",
                        tracking_number=shipment.get("tracking_number")
                    )

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

        if order_service.inventory_client:
            await order_service.inventory_client.release(order.order_id)

        if event_id:
            mark_event_processed(event_id)
        logger.info(f"✅ Order {order.order_id} marked as failed after payment failure")

    except Exception as e:
        logger.error(f"❌ Failed to handle payment.failed event: {e}")


async def handle_payment_initiated(event_data: Dict[str, Any], order_service, event_id: str = None) -> None:
    """Handle payment.initiated event to attach payment_intent_id to order."""
    try:
        if event_id and is_event_processed(event_id):
            return

        order_id = event_data.get("order_id")
        payment_intent_id = event_data.get("payment_intent_id")

        if not order_id or not payment_intent_id:
            return

        await order_service.repository.update_order(
            order_id=order_id,
            payment_intent_id=payment_intent_id
        )

        if event_id:
            mark_event_processed(event_id)
        logger.info(f"✅ Order {order_id} updated with payment_intent_id")

    except Exception as e:
        logger.error(f"❌ Failed to handle payment.initiated event: {e}")


async def handle_payment_refunded(event_data: Dict[str, Any], order_service, event_id: str = None) -> None:
    """
    Handle payment.refunded event
    Update order status to refunded

    Args:
        event_data: Event data containing payment details
        order_service: OrderService instance
        event_id: Event ID for idempotency
    """
    try:
        if event_id and is_event_processed(event_id):
            logger.debug(f"Event {event_id} already processed, skipping")
            return

        payment_id = event_data.get("payment_id")
        payment_intent_id = event_data.get("payment_intent_id")
        refund_amount = event_data.get("amount")
        user_id = event_data.get("user_id")

        if not payment_id and not payment_intent_id:
            logger.warning("payment.refunded event missing payment_id and payment_intent_id")
            return

        logger.info(f"Processing payment refund for payment {payment_id or payment_intent_id}, amount: {refund_amount}")

        # Find order by payment_intent_id or transaction_id
        order = None
        if payment_intent_id:
            order = await order_service.repository.get_order_by_payment_intent(payment_intent_id)

        if not order and payment_id:
            # Try to find by transaction_id
            order = await order_service.repository.get_order_by_transaction_id(payment_id)

        if not order:
            logger.warning(f"No order found for payment {payment_id or payment_intent_id}")
            if event_id:
                mark_event_processed(event_id)
            return

        # Update order status to refunded
        from ..models import OrderStatus, PaymentStatus

        await order_service.repository.update_order_status(
            order.order_id,
            OrderStatus.REFUNDED,
            payment_status=PaymentStatus.REFUNDED
        )

        # Update refund amount in order metadata
        await order_service.repository.update_order_metadata(
            order.order_id,
            {
                "refund_amount": str(refund_amount),
                "refund_payment_id": payment_id,
                "refunded_at": datetime.utcnow().isoformat()
            }
        )

        if event_id:
            mark_event_processed(event_id)

        logger.info(f"✅ Order {order.order_id} marked as refunded (amount: {refund_amount})")

    except Exception as e:
        logger.error(f"❌ Failed to handle payment.refunded event: {e}", exc_info=True)


async def handle_wallet_credits_added(event_data: Dict[str, Any], order_service, event_id: str = None) -> None:
    """
    Handle wallet.credits_added event
    Auto-fulfill pending wallet top-up orders

    Args:
        event_data: Event data containing wallet details
        order_service: OrderService instance
        event_id: Event ID for idempotency
    """
    try:
        if event_id and is_event_processed(event_id):
            logger.debug(f"Event {event_id} already processed, skipping")
            return

        user_id = event_data.get("user_id")
        amount = event_data.get("amount")
        reference_id = event_data.get("reference_id")

        if not user_id:
            logger.warning("wallet.credits_added event missing user_id")
            return

        logger.info(f"Wallet credits added for user {user_id}, amount: {amount}")

        # Find pending wallet/credit orders for this user
        from ..models import OrderStatus, OrderType

        pending_orders = await order_service.repository.get_pending_orders_by_user(
            user_id=user_id,
            order_type=OrderType.CREDIT_PURCHASE if hasattr(OrderType, 'CREDIT_PURCHASE') else None
        )

        fulfilled_count = 0
        for order in pending_orders:
            # Check if this credit deposit matches an order
            if reference_id and str(order.order_id) == reference_id:
                # This deposit was for this specific order
                from ..models import OrderCompleteRequest
                complete_request = OrderCompleteRequest(
                    payment_confirmed=True,
                    credits_added=Decimal(str(amount)) if amount else None
                )
                await order_service.complete_order(order.order_id, complete_request)
                fulfilled_count += 1
                logger.info(f"✅ Fulfilled order {order.order_id} after wallet credits added")

        if event_id:
            mark_event_processed(event_id)

        if fulfilled_count > 0:
            logger.info(f"Fulfilled {fulfilled_count} pending orders for user {user_id}")

    except Exception as e:
        logger.error(f"❌ Failed to handle wallet.credits_added event: {e}", exc_info=True)


async def handle_subscription_created(event_data: Dict[str, Any], order_service, event_id: str = None) -> None:
    """
    Handle subscription.created event
    Create recurring order record for subscription tracking

    Args:
        event_data: Event data containing subscription details
        order_service: OrderService instance
        event_id: Event ID for idempotency
    """
    try:
        if event_id and is_event_processed(event_id):
            logger.debug(f"Event {event_id} already processed, skipping")
            return

        subscription_id = event_data.get("subscription_id")
        user_id = event_data.get("user_id")
        plan_id = event_data.get("plan_id")
        amount = event_data.get("amount", 0)

        if not all([subscription_id, user_id]):
            logger.warning("subscription.created event missing required fields")
            return

        logger.info(f"Subscription created: {subscription_id} for user {user_id}, plan: {plan_id}")

        # Create subscription order record for tracking
        from ..models import OrderCreateRequest, OrderType, OrderStatus

        order_request = OrderCreateRequest(
            user_id=user_id,
            order_type=OrderType.SUBSCRIPTION if hasattr(OrderType, 'SUBSCRIPTION') else OrderType.SERVICE,
            total_amount=Decimal(str(amount)) if amount else Decimal("0"),
            currency="USD",
            items=[{
                "product_id": plan_id or "subscription",
                "quantity": 1,
                "unit_price": float(amount) if amount else 0,
                "description": f"Subscription: {plan_id}"
            }],
            metadata={
                "subscription_id": subscription_id,
                "plan_id": plan_id,
                "is_recurring": True,
                "event_id": event_id
            }
        )

        order = await order_service.create_order(order_request)

        # Mark as completed since subscription is already active
        from ..models import OrderCompleteRequest
        complete_request = OrderCompleteRequest(
            payment_confirmed=True,
            transaction_id=subscription_id
        )
        await order_service.complete_order(order.order_id, complete_request)

        if event_id:
            mark_event_processed(event_id)

        logger.info(f"✅ Created subscription order {order.order_id} for subscription {subscription_id}")

    except Exception as e:
        logger.error(f"❌ Failed to handle subscription.created event: {e}", exc_info=True)


async def handle_subscription_canceled(event_data: Dict[str, Any], order_service, event_id: str = None) -> None:
    """
    Handle subscription.canceled event
    Cancel pending subscription orders and update records

    Args:
        event_data: Event data containing subscription details
        order_service: OrderService instance
        event_id: Event ID for idempotency
    """
    try:
        if event_id and is_event_processed(event_id):
            logger.debug(f"Event {event_id} already processed, skipping")
            return

        subscription_id = event_data.get("subscription_id")
        user_id = event_data.get("user_id")
        reason = event_data.get("reason", "user_requested")

        if not subscription_id:
            logger.warning("subscription.canceled event missing subscription_id")
            return

        logger.info(f"Subscription canceled: {subscription_id}, reason: {reason}")

        # Find and cancel any pending orders for this subscription
        from ..models import OrderStatus

        # Get orders by subscription_id in metadata
        orders = await order_service.repository.get_orders_by_metadata(
            "subscription_id", subscription_id
        )

        cancelled_count = 0
        for order in orders:
            if order.status in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
                await order_service.repository.update_order_status(
                    order.order_id,
                    OrderStatus.CANCELLED
                )
                await order_service.repository.update_order_metadata(
                    order.order_id,
                    {
                        "cancellation_reason": f"subscription_canceled: {reason}",
                        "cancelled_at": datetime.utcnow().isoformat()
                    }
                )
                cancelled_count += 1

        if event_id:
            mark_event_processed(event_id)

        logger.info(f"✅ Cancelled {cancelled_count} pending orders for subscription {subscription_id}")

    except Exception as e:
        logger.error(f"❌ Failed to handle subscription.canceled event: {e}", exc_info=True)


async def handle_user_deleted(event_data: Dict[str, Any], order_service, event_id: str = None) -> None:
    """
    Handle user.deleted event
    Cancel all pending orders for deleted user and anonymize data

    Args:
        event_data: Event data containing user details
        order_service: OrderService instance
        event_id: Event ID for idempotency
    """
    try:
        if event_id and is_event_processed(event_id):
            logger.debug(f"Event {event_id} already processed, skipping")
            return

        user_id = event_data.get("user_id")

        if not user_id:
            logger.warning("user.deleted event missing user_id")
            return

        logger.info(f"Processing user deletion for user {user_id}")

        from ..models import OrderStatus

        # Get all orders for this user
        all_orders = await order_service.repository.get_user_orders(user_id, limit=1000)

        cancelled_count = 0
        anonymized_count = 0

        for order in all_orders:
            try:
                # Cancel pending orders
                if order.status in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
                    await order_service.repository.update_order_status(
                        order.order_id,
                        OrderStatus.CANCELLED
                    )
                    cancelled_count += 1

                # Anonymize user data in completed orders (keep for accounting)
                await order_service.repository.update_order_metadata(
                    order.order_id,
                    {
                        "user_deleted": True,
                        "user_deleted_at": datetime.utcnow().isoformat(),
                        "original_user_id": user_id  # Keep for audit trail
                    }
                )

                # Optionally anonymize PII in order
                await order_service.repository.anonymize_order_pii(order.order_id)
                anonymized_count += 1

            except Exception as e:
                logger.error(f"Failed to process order {order.order_id}: {e}")

        if event_id:
            mark_event_processed(event_id)

        logger.info(
            f"✅ User {user_id} deletion processed: "
            f"{cancelled_count} orders cancelled, {anonymized_count} orders anonymized"
        )

    except Exception as e:
        logger.error(f"❌ Failed to handle user.deleted event: {e}", exc_info=True)


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
        "payment_service.payment.initiated": lambda event: handle_payment_initiated(
            event.data, order_service, event.id
        ),
        "payment_service.payment.completed": lambda event: handle_payment_completed(
            event.data, order_service, event.id
        ),
        "payment_service.payment.failed": lambda event: handle_payment_failed(
            event.data, order_service, event.id
        ),
        "payment_service.payment.refunded": lambda event: handle_payment_refunded(
            event.data, order_service, event.id
        ),
        "wallet_service.wallet.credits_added": lambda event: handle_wallet_credits_added(
            event.data, order_service, event.id
        ),
        "subscription_service.subscription.created": lambda event: handle_subscription_created(
            event.data, order_service, event.id
        ),
        "subscription_service.subscription.canceled": lambda event: handle_subscription_canceled(
            event.data, order_service, event.id
        ),
        "account_service.user.deleted": lambda event: handle_user_deleted(
            event.data, order_service, event.id
        ),
    }
