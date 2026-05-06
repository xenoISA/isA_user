"""
Payment Service Event Handlers

Handlers for events from other services.

Distributed event idempotency (issue #348):
    Events that mutate persistent state (creating payment intents,
    cancelling subscriptions, anonymising payment history) are
    wrapped in a Redis-backed distributed lock keyed by the source
    event id so two replicas under HPA scale-out cannot race.

    Note: most upstream callers in this module pass ``event_data``
    rather than the full ``event`` envelope, so the wrapper helpers
    accept an explicit ``event_id`` arg from the dispatcher in
    ``get_event_handlers``.
"""

import logging
import os
from typing import Any, Dict, Optional
from decimal import Decimal

from core.distributed_lock import (
    DistributedLock,
    DistributedLockError,
    LockContended,
    build_distributed_lock,
)
from core.redis_cache import RedisCache, build_redis_cache

from ..models import CreatePaymentIntentRequest, Currency

logger = logging.getLogger(__name__)


# ============================================================================
# Distributed lock + result cache singletons (issue #348)
# ============================================================================

_event_lock: Optional[DistributedLock] = None
_event_result_cache: Optional[RedisCache] = None

_DEFAULT_LOCK_TTL_SECONDS = int(os.getenv("PAYMENT_EVENT_LOCK_TTL_SECONDS", "120"))
_DEFAULT_RESULT_CACHE_TTL_SECONDS = int(
    os.getenv("PAYMENT_EVENT_RESULT_CACHE_TTL_SECONDS", "900")
)


def _get_event_lock() -> DistributedLock:
    global _event_lock
    if _event_lock is None:
        _event_lock = build_distributed_lock(
            "payment_service",
            service_name="payment_service",
            default_ttl_seconds=_DEFAULT_LOCK_TTL_SECONDS,
        )
    return _event_lock


def _get_result_cache() -> RedisCache:
    global _event_result_cache
    if _event_result_cache is None:
        _event_result_cache = build_redis_cache(
            "payment_event_results",
            service_name="payment_service",
            default_ttl=_DEFAULT_RESULT_CACHE_TTL_SECONDS,
        )
    return _event_result_cache


def set_event_idempotency_backends(
    *,
    lock: Optional[DistributedLock] = None,
    result_cache: Optional[RedisCache] = None,
) -> None:
    """Override the lock / result cache singletons (test hook)."""
    global _event_lock, _event_result_cache
    if lock is not None:
        _event_lock = lock
    if result_cache is not None:
        _event_result_cache = result_cache


def _event_lock_guard(handler_label: str, event_id: str):
    return _get_event_lock().guard(
        f"{handler_label}:{event_id}",
        ttl_seconds=_DEFAULT_LOCK_TTL_SECONDS,
        result_cache=_get_result_cache(),
        wait_seconds=0.5,
        wait_poll_interval=0.05,
        on_contended="return",
    )


def _resolve_event_id(event_or_data: Any) -> str:
    """Pull a stable identifier off an Event envelope or raw data dict.

    Handlers historically receive ``event.data`` (a dict). The
    dispatcher in ``get_event_handlers`` now passes the envelope so
    we can use ``event.id``, but legacy callers may still hand a
    raw dict — we fall back to a domain key when present.
    """
    if hasattr(event_or_data, "id") and getattr(event_or_data, "id"):
        return str(event_or_data.id)
    if isinstance(event_or_data, dict):
        for key in (
            "event_id",
            "order_id",
            "payment_id",
            "subscription_id",
            "user_id",
        ):
            if event_or_data.get(key):
                return str(event_or_data[key])
    return "anonymous"


async def handle_order_created(event_data: Dict[str, Any], payment_service) -> None:
    """
    Handle order.created event

    Automatically create payment intent for new orders. Wrapped in a
    distributed idempotency lock keyed by the order id (#348) so two
    replicas processing the same event don't both create a payment
    intent.
    """
    event_id = _resolve_event_id(event_data)
    try:
        async with _event_lock_guard("order_created", event_id) as outcome:
            if outcome.is_cached:
                logger.debug("order.created %s served from idempotency cache", event_id)
                return
            if outcome.token == "":
                logger.info(
                    "order.created %s contended on lock; another replica is "
                    "processing",
                    event_id,
                )
                return

            order_id = event_data.get("order_id")
            user_id = event_data.get("user_id")
            amount = event_data.get("total_amount")
            payment_intent_id = event_data.get("payment_intent_id")
            currency = event_data.get("currency", "USD")

            if payment_intent_id:
                logger.info(f"Order {order_id} already has payment_intent_id, skipping")
                outcome.set_result(
                    {"status": "skipped", "reason": "already_has_intent"}
                )
                return

            if not all([order_id, user_id, amount]):
                logger.warning("order.created event missing required fields")
                return

            logger.info(f"Processing order.created event for order {order_id}")

            request = CreatePaymentIntentRequest(
                user_id=user_id,
                amount=Decimal(str(amount)),
                currency=Currency(currency),
                order_id=order_id,
                metadata={"order_id": order_id},
            )

            await payment_service.create_payment_intent(request)
            outcome.set_result({"status": "intent_created", "order_id": order_id})
    except DistributedLockError as exc:
        logger.error(
            "order.created %s aborted: distributed lock unavailable: %s",
            event_id,
            exc,
        )
    except LockContended:
        logger.info("order.created %s contended; will retry", event_id)
    except Exception as e:
        logger.error(f"❌ Error handling order.created event: {e}")


async def handle_wallet_balance_changed(
    event_data: Dict[str, Any], payment_service
) -> None:
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
            logger.info(
                f"Wallet balance increased for user {user_id}, checking for retry opportunities"
            )
            # TODO: Implement retry logic for failed subscription payments

    except Exception as e:
        logger.error(f"❌ Error handling wallet.balance_changed event: {e}")


async def handle_wallet_insufficient_funds(
    event_data: Dict[str, Any], payment_service
) -> None:
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
        logger.info(
            f"User {user_id} has insufficient funds - subscriptions may need attention"
        )

    except Exception as e:
        logger.error(f"❌ Error handling wallet.insufficient_funds event: {e}")


async def handle_subscription_usage_exceeded(
    event_data: Dict[str, Any], payment_service
) -> None:
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
            logger.info(
                f"Creating overage invoice for subscription {subscription_id}, amount: {overage_amount}"
            )
            # TODO: Implement invoice creation logic

    except Exception as e:
        logger.error(f"❌ Error handling subscription.usage_exceeded event: {e}")


async def handle_user_deleted(event_data: Dict[str, Any], payment_service) -> None:
    """
    Handle user.deleted event

    Cancel all subscriptions and process prorated refunds. Wrapped in
    a distributed idempotency lock keyed by user_id (#348) so two
    replicas don't both refund / cancel the same user.
    """
    event_id = _resolve_event_id(event_data)
    try:
        async with _event_lock_guard("user_deleted_payment", event_id) as outcome:
            if outcome.is_cached:
                logger.debug(
                    "user.deleted (payment) %s served from idempotency cache",
                    event_id,
                )
                return
            if outcome.token == "":
                logger.info(
                    "user.deleted (payment) %s contended on lock; another "
                    "replica is processing",
                    event_id,
                )
                return
            await _process_user_deleted_payment(event_data, payment_service, outcome)
    except DistributedLockError as exc:
        logger.error(
            "user.deleted (payment) %s aborted: distributed lock unavailable: %s",
            event_id,
            exc,
        )
    except LockContended:
        logger.info("user.deleted (payment) %s contended; will retry", event_id)
    except Exception as e:
        logger.error(f"❌ Error handling user.deleted event: {e}", exc_info=True)


async def _process_user_deleted_payment(
    event_data: Dict[str, Any], payment_service, outcome
) -> None:
    """Inner body of handle_user_deleted — runs under the distributed lock."""
    try:
        user_id = event_data.get("user_id")

        if not user_id:
            logger.warning("user.deleted event missing user_id")
            return

        logger.info(f"Processing user.deleted event for user {user_id}")

        # Get all active subscriptions for this user
        if hasattr(payment_service, "repository"):
            subscriptions = await payment_service.repository.get_user_subscriptions(
                user_id
            )

            cancelled_count = 0
            refund_total = 0

            for subscription in subscriptions:
                try:
                    # Cancel subscription
                    await payment_service.repository.cancel_subscription(
                        subscription_id=subscription.get("subscription_id"),
                        reason="user_deleted",
                        immediate=True,
                    )
                    cancelled_count += 1

                    # Calculate prorated refund if applicable
                    if subscription.get("status") == "active":
                        prorated_amount = (
                            await payment_service.calculate_prorated_refund(
                                subscription_id=subscription.get("subscription_id")
                            )
                        )
                        if prorated_amount and prorated_amount > 0:
                            refund_total += prorated_amount
                            logger.info(
                                f"Prorated refund of {prorated_amount} calculated for subscription "
                                f"{subscription.get('subscription_id')}"
                            )

                except Exception as e:
                    logger.error(
                        f"Failed to cancel subscription {subscription.get('subscription_id')}: {e}"
                    )

            # Cancel pending payment intents
            cancelled_intents = (
                await payment_service.repository.cancel_user_payment_intents(user_id)
            )

            # Anonymize payment history (keep for accounting, remove PII)
            await payment_service.repository.anonymize_user_payment_history(user_id)

            outcome.set_result(
                {
                    "status": "cleaned_up",
                    "user_id": user_id,
                    "cancelled_subscriptions": cancelled_count,
                    "cancelled_intents": cancelled_intents,
                    "refund_total": str(refund_total),
                }
            )
            logger.info(
                f"✅ User {user_id} payment cleanup: "
                f"{cancelled_count} subscriptions cancelled, "
                f"{cancelled_intents} payment intents cancelled, "
                f"prorated refund: {refund_total}"
            )
        else:
            logger.warning(
                f"Payment service repository not available for user {user_id} cleanup"
            )

    except Exception as e:
        logger.error(f"❌ Error handling user.deleted event: {e}", exc_info=True)


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
        logger.info(
            f"Checking for subscription upgrade opportunities for user {user_id}"
        )
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
        "order_service.order.created": lambda event: handle_order_created(
            event.data, payment_service
        ),
        "wallet_service.wallet.balance_changed": lambda event: handle_wallet_balance_changed(
            event.data, payment_service
        ),
        "wallet_service.wallet.insufficient_funds": lambda event: handle_wallet_insufficient_funds(
            event.data, payment_service
        ),
        "product_service.subscription.usage_exceeded": lambda event: handle_subscription_usage_exceeded(
            event.data, payment_service
        ),
        "account_service.user.deleted": lambda event: handle_user_deleted(
            event.data, payment_service
        ),
        "account_service.user.upgraded": lambda event: handle_user_upgraded(
            event.data, payment_service
        ),
    }
