"""
Wallet Event Handlers

Distributed event idempotency (issue #348):
    Each handler wraps its work in
    ``_event_lock().guard(event_id, ...)``. The first replica acquires
    a Redis-backed lock keyed by the event ID; concurrent replicas
    either wait briefly for the cached result or contend (and skip).
    Lock TTL is 2× the expected max processing time so a crashed
    handler frees the key automatically. The result cache short-
    circuits retried events back to the original outcome without
    re-processing — see ``core/distributed_lock.py`` for the contract.
"""

import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from core.distributed_lock import (
    DistributedLock,
    DistributedLockError,
    LockContended,
    build_distributed_lock,
)
from core.nats_client import Event
from core.redis_cache import RedisCache, build_redis_cache

from ..models import ConsumeRequest
from .models import (
    parse_billing_calculated_event,
)
from .publishers import publish_tokens_deducted, publish_tokens_insufficient

logger = logging.getLogger(__name__)


# ============================================================================
# Distributed lock + result cache singletons (issue #348)
# ============================================================================
#
# Lazy-built so importing the module in a test environment without
# Redis configured doesn't blow up. Production code path resolves
# ``WALLET_CACHE_REDIS_URL`` / ``CACHE_REDIS_URL`` / ``REDIS_URL``.
#
# Tests may override either singleton via ``set_event_idempotency_backends``.

_event_lock: Optional[DistributedLock] = None
_event_result_cache: Optional[RedisCache] = None

# Default lock TTL = 2× expected max processing time (60s observed in
# the wallet handler). Per-call override via the handler signature is
# possible but currently every wallet handler uses the same budget.
_DEFAULT_LOCK_TTL_SECONDS = int(os.getenv("WALLET_EVENT_LOCK_TTL_SECONDS", "120"))
# Result cache TTL: long enough to survive normal NATS retry windows
# but short enough that we don't pin obsolete results forever.
_DEFAULT_RESULT_CACHE_TTL_SECONDS = int(
    os.getenv("WALLET_EVENT_RESULT_CACHE_TTL_SECONDS", "900")
)


def _get_event_lock() -> DistributedLock:
    global _event_lock
    if _event_lock is None:
        _event_lock = build_distributed_lock(
            "wallet_service",
            service_name="wallet_service",
            default_ttl_seconds=_DEFAULT_LOCK_TTL_SECONDS,
        )
    return _event_lock


def _get_result_cache() -> RedisCache:
    global _event_result_cache
    if _event_result_cache is None:
        _event_result_cache = build_redis_cache(
            "wallet_event_results",
            service_name="wallet_service",
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
    """Return the configured lock guard with sensible defaults.

    Centralised so all wallet event handlers share identical TTL / wait
    / contention behaviour. Each handler keys its lock under
    ``<handler_label>:<event_id>`` to keep the "same handler, different
    event" cases isolated.
    """
    return _get_event_lock().guard(
        f"{handler_label}:{event_id}",
        ttl_seconds=_DEFAULT_LOCK_TTL_SECONDS,
        result_cache=_get_result_cache(),
        wait_seconds=0.5,
        wait_poll_interval=0.05,
        on_contended="return",
    )


async def handle_billing_calculated(event: Event, wallet_service, event_bus):
    """
    处理 billing.calculated 事件并执行 token 扣费

    Wrapped in a distributed idempotency lock (#348) keyed by event.id —
    HPA scale-out can deliver the same event to multiple replicas, and
    this wrapper guarantees exactly one replica performs the deduction.

    Args:
        event: 接收到的事件对象
        wallet_service: WalletService 实例
        event_bus: 事件总线实例

    工作流程:
        0. Acquire distributed idempotency lock keyed by event_id
        1. 解析计费事件数据
        2. 检查是否需要扣费（免费额度、订阅包含的不扣费）
        3. 获取用户钱包
        4. 检查余额是否充足
        5. 扣除 token
        6. 发布 tokens.deducted 或 tokens.insufficient 事件
    """
    try:
        async with _get_event_lock().guard(
            f"billing_calculated:{event.id}",
            ttl_seconds=_DEFAULT_LOCK_TTL_SECONDS,
            result_cache=_get_result_cache(),
            wait_seconds=0.5,
            wait_poll_interval=0.05,
            on_contended="return",
        ) as outcome:
            if outcome.is_cached:
                logger.debug(
                    "billing.calculated %s served from idempotency cache",
                    event.id,
                )
                return
            if outcome.token == "":
                logger.info(
                    "billing.calculated %s contended on lock; another "
                    "replica is processing",
                    event.id,
                )
                return
            await _process_billing_calculated(event, wallet_service, event_bus, outcome)
    except DistributedLockError as exc:
        logger.error(
            "billing.calculated %s aborted: distributed lock unavailable: %s",
            event.id,
            exc,
        )
    except LockContended:
        logger.info("billing.calculated %s contended; will retry", event.id)
    except Exception as e:
        logger.error(f"Error handling billing_calculated event: {e}", exc_info=True)


async def _process_billing_calculated(event, wallet_service, event_bus, outcome):
    """Inner body of handle_billing_calculated — runs under the lock."""
    try:
        # 解析事件数据
        billing_data = parse_billing_calculated_event(event.data)

        logger.info(
            f"Processing billing.calculated for user {billing_data.user_id}, "
            f"billing_record {billing_data.billing_record_id}, "
            f"tokens {billing_data.token_equivalent}"
        )

        # 检查是否需要扣费
        if billing_data.is_free_tier:
            logger.info(
                f"Free tier usage, no wallet deduction for {billing_data.user_id}"
            )
            outcome.set_result({"status": "skipped", "reason": "free_tier"})
            return

        if billing_data.is_included_in_subscription:
            logger.info(
                f"Subscription included usage, no wallet deduction for {billing_data.user_id}"
            )
            # 更新订阅使用量统计（如果需要）
            outcome.set_result({"status": "skipped", "reason": "subscription_included"})
            return

        # 需要从钱包扣费
        tokens_to_deduct = billing_data.token_equivalent
        consume_request = ConsumeRequest(
            amount=tokens_to_deduct,
            description=f"Usage charge for {billing_data.product_id}",
            usage_record_id=billing_data.billing_record_id,
        )

        # 调用 wallet_service 的扣费方法
        deduction_result = await wallet_service.consume_by_user(
            user_id=billing_data.user_id,
            request=consume_request,
        )
        deduction_payload = (
            deduction_result.model_dump()
            if hasattr(deduction_result, "model_dump")
            else deduction_result.dict()
            if hasattr(deduction_result, "dict")
            else deduction_result
        )
        data = (
            deduction_payload.get("data", {})
            if isinstance(deduction_payload, dict)
            else {}
        )
        transaction = data.get("transaction", {}) if isinstance(data, dict) else {}

        if deduction_payload.get("success"):
            # 扣费成功，发布 tokens.deducted 事件
            await publish_tokens_deducted(
                event_bus=event_bus,
                user_id=billing_data.user_id,
                billing_record_id=billing_data.billing_record_id,
                transaction_id=deduction_payload.get("transaction_id"),
                tokens_deducted=tokens_to_deduct,
                balance_before=Decimal(
                    str(
                        transaction.get(
                            "balance_before",
                            deduction_payload.get(
                                "balance_before", deduction_payload.get("balance", 0)
                            ),
                        )
                    )
                ),
                balance_after=Decimal(
                    str(
                        transaction.get(
                            "balance_after",
                            deduction_payload.get(
                                "balance_after", deduction_payload.get("balance", 0)
                            ),
                        )
                    )
                ),
                monthly_quota=data.get("monthly_quota"),
                monthly_used=data.get("monthly_used"),
            )

            outcome.set_result(
                {
                    "status": "deducted",
                    "user_id": billing_data.user_id,
                    "tokens_deducted": str(tokens_to_deduct),
                    "transaction_id": deduction_payload.get("transaction_id"),
                }
            )
            logger.info(
                f"Successfully deducted {tokens_to_deduct} tokens from user {billing_data.user_id}, "
                f"new balance: {deduction_payload.get('balance')}"
            )
        else:
            # 扣费失败（余额不足），发布 tokens.insufficient 事件
            await publish_tokens_insufficient(
                event_bus=event_bus,
                user_id=billing_data.user_id,
                billing_record_id=billing_data.billing_record_id,
                tokens_required=tokens_to_deduct,
                tokens_available=Decimal(
                    str(
                        data.get(
                            "balance_available",
                            deduction_payload.get("balance", 0),
                        )
                    )
                ),
                suggested_action=deduction_payload.get(
                    "suggested_action", "upgrade_plan"
                ),
            )

            outcome.set_result(
                {
                    "status": "insufficient",
                    "user_id": billing_data.user_id,
                    "tokens_required": str(tokens_to_deduct),
                }
            )
            logger.warning(
                f"Insufficient tokens for user {billing_data.user_id}, "
                f"required: {tokens_to_deduct}, available: {data.get('balance_available', deduction_payload.get('balance', 0))}"
            )

    except Exception as e:
        logger.error(f"Error handling billing_calculated event: {e}", exc_info=True)


async def setup_event_subscriptions(event_bus, wallet_service):
    """
    设置 wallet_service 的事件订阅

    Args:
        event_bus: 事件总线实例
        wallet_service: WalletService 实例

    订阅的事件:
        - billing.calculated (执行 token 扣费)
        - payment.completed (处理充值)
    """
    try:
        # 订阅计费完成事件
        await event_bus.subscribe_to_events(
            pattern="billing.calculated",
            handler=lambda event: handle_billing_calculated(
                event, wallet_service, event_bus
            ),
        )
        await event_bus.subscribe_to_events(
            pattern="*.billing.calculated",
            handler=lambda event: handle_billing_calculated(
                event, wallet_service, event_bus
            ),
        )
        await event_bus.subscribe_to_events(
            pattern="billing_service.billing.calculated",
            handler=lambda event: handle_billing_calculated(
                event, wallet_service, event_bus
            ),
        )

        logger.info("✅ Wallet service event subscriptions setup complete")
        logger.info("   - Subscribed to: billing.calculated")

    except Exception as e:
        logger.error(f"Failed to setup wallet event subscriptions: {e}", exc_info=True)
        raise


# =============================================================================
# NEW STANDARDIZED EVENT HANDLERS (Migrated from main.py)
# =============================================================================

# Idempotency tracking
_processed_event_ids = set()


def _is_event_processed(event_id: str) -> bool:
    """Check if event has already been processed (idempotency)"""
    return event_id in _processed_event_ids


def _mark_event_processed(event_id: str):
    """Mark event as processed"""
    global _processed_event_ids
    _processed_event_ids.add(event_id)
    if len(_processed_event_ids) > 10000:
        # Remove oldest half to prevent memory bloat
        _processed_event_ids = set(list(_processed_event_ids)[5000:])


async def handle_payment_completed(event: Event, wallet_service):
    """
    Handle payment.completed event
    Deposit funds into wallet after successful payment

    Args:
        event: NATS event object
        wallet_service: WalletService instance

    Event Data:
        - user_id: User ID
        - amount: Payment amount
        - currency: Currency code (default: USD)
        - payment_id: Payment transaction ID

    Workflow:
        1. Acquire distributed idempotency lock keyed by event ID (#348)
        2. Validate event data
        3. Get user's primary wallet
        4. Deposit funds to wallet
        5. Cache outcome so retries short-circuit without re-deposit
    """
    if _is_event_processed(event.id):
        logger.debug(f"Event {event.id} already processed, skipping")
        return

    try:
        async with _get_event_lock().guard(
            f"payment_completed:{event.id}",
            ttl_seconds=_DEFAULT_LOCK_TTL_SECONDS,
            result_cache=_get_result_cache(),
            wait_seconds=0.5,
            wait_poll_interval=0.05,
            on_contended="return",
        ) as outcome:
            if outcome.is_cached:
                logger.debug(
                    "payment.completed %s served from idempotency cache",
                    event.id,
                )
                _mark_event_processed(event.id)
                return
            if outcome.token == "":
                # Contended; another replica is processing — skip without
                # re-running. Retries will eventually hit the cache.
                logger.info(
                    "payment.completed %s contended on lock; another replica "
                    "is processing",
                    event.id,
                )
                return

            user_id = event.data.get("user_id")
            amount = event.data.get("amount")
            currency = event.data.get("currency", "USD")
            payment_id = event.data.get("payment_id")

            if not user_id or not amount:
                logger.warning(
                    f"payment.completed event missing required fields: {event.id}"
                )
                return

            # Get user's primary wallet
            wallet = await wallet_service.repository.get_primary_wallet(user_id)
            if not wallet:
                logger.warning(f"No wallet found for user {user_id}, skipping deposit")
                _mark_event_processed(event.id)
                outcome.set_result({"status": "skipped", "reason": "no_wallet"})
                return

            # Import here to avoid circular imports
            from ..models import DepositRequest

            # Deposit into wallet
            deposit_request = DepositRequest(
                amount=Decimal(str(amount)),
                description=f"Payment received (payment_id: {payment_id})",
                reference_id=payment_id,
                metadata={
                    "event_id": event.id,
                    "event_type": event.type,
                    "payment_id": payment_id,
                    "timestamp": event.timestamp,
                    "currency": currency,
                },
            )

            await wallet_service.deposit(wallet.wallet_id, deposit_request)

            _mark_event_processed(event.id)
            outcome.set_result(
                {
                    "status": "deposited",
                    "user_id": user_id,
                    "amount": str(amount),
                    "currency": currency,
                    "payment_id": payment_id,
                }
            )
            logger.info(
                f"✅ Deposited {amount} {currency} to wallet for user {user_id} (event: {event.id})"
            )
    except DistributedLockError as exc:
        # Fail closed: do NOT process without lock confirmation. The
        # event will be retried; if the prior holder finished the work,
        # the cache short-circuit will return.
        logger.error(
            "payment.completed %s aborted: distributed lock unavailable: %s",
            event.id,
            exc,
        )
    except LockContended:
        # Should not reach here when on_contended="return", but be safe.
        logger.info("payment.completed %s contended on lock; will retry", event.id)
    except Exception as e:
        logger.error(f"Failed to handle payment.completed event {event.id}: {e}")


async def handle_payment_refunded(event: Event, wallet_service):
    """
    Handle payment.refunded event
    Deposit refund amount back into user's wallet

    Args:
        event: NATS event object
        wallet_service: WalletService instance

    Event Data:
        - user_id: User ID
        - amount: Refund amount
        - currency: Currency code (default: USD)
        - payment_id: Original payment transaction ID
        - refund_id: Refund transaction ID
        - reason: Refund reason

    Workflow:
        0. Acquire distributed idempotency lock keyed by event_id (#348)
        1. Validate event data
        2. Get user's primary wallet
        3. Deposit refund to wallet
        4. Publish refund.completed event
    """
    if _is_event_processed(event.id):
        logger.debug(f"Event {event.id} already processed, skipping")
        return

    try:
        async with _event_lock_guard("payment_refunded", event.id) as outcome:
            if outcome.is_cached:
                _mark_event_processed(event.id)
                return
            if outcome.token == "":
                logger.info(
                    "payment.refunded %s contended on lock; another replica "
                    "is processing",
                    event.id,
                )
                return

            user_id = event.data.get("user_id")
            amount = event.data.get("amount")
            currency = event.data.get("currency", "USD")
            payment_id = event.data.get("payment_id")
            refund_id = event.data.get("refund_id")
            reason = event.data.get("reason", "Payment refund")

            if not user_id or not amount:
                logger.warning(
                    f"payment.refunded event missing required fields: {event.id}"
                )
                return

            wallet = await wallet_service.repository.get_primary_wallet(user_id)
            if not wallet:
                logger.warning(
                    f"No wallet found for user {user_id}, cannot process refund"
                )
                _mark_event_processed(event.id)
                outcome.set_result({"status": "skipped", "reason": "no_wallet"})
                return

            from ..models import DepositRequest

            deposit_request = DepositRequest(
                amount=Decimal(str(amount)),
                description=f"Refund: {reason} (payment_id: {payment_id})",
                reference_id=refund_id or payment_id,
                metadata={
                    "event_id": event.id,
                    "event_type": event.type,
                    "payment_id": payment_id,
                    "refund_id": refund_id,
                    "reason": reason,
                    "timestamp": event.timestamp,
                    "currency": currency,
                    "is_refund": True,
                },
            )

            await wallet_service.deposit(wallet.wallet_id, deposit_request)

            _mark_event_processed(event.id)
            outcome.set_result(
                {
                    "status": "refunded",
                    "user_id": user_id,
                    "amount": str(amount),
                    "currency": currency,
                    "refund_id": refund_id,
                }
            )
            logger.info(
                f"✅ Refunded {amount} {currency} to wallet for user {user_id} "
                f"(refund: {refund_id}, event: {event.id})"
            )
    except DistributedLockError as exc:
        logger.error(
            "payment.refunded %s aborted: distributed lock unavailable: %s",
            event.id,
            exc,
        )
    except LockContended:
        logger.info("payment.refunded %s contended; will retry", event.id)
    except Exception as e:
        logger.error(f"Failed to handle payment.refunded event {event.id}: {e}")


async def handle_subscription_created(event: Event, wallet_service):
    """
    Handle subscription.created event
    Allocate monthly credits to user's wallet based on subscription tier

    Args:
        event: NATS event object
        wallet_service: WalletService instance

    Event Data:
        - user_id: User ID
        - subscription_id: Subscription ID
        - plan_id: Plan/tier ID
        - monthly_credits: Credits included in subscription (optional)

    Workflow:
        0. Acquire distributed idempotency lock keyed by event_id (#348)
        1. Validate event data
        2. Get user's primary wallet
        3. Allocate subscription credits
    """
    if _is_event_processed(event.id):
        logger.debug(f"Event {event.id} already processed, skipping")
        return

    try:
        async with _event_lock_guard("subscription_created", event.id) as outcome:
            if outcome.is_cached:
                _mark_event_processed(event.id)
                return
            if outcome.token == "":
                logger.info(
                    "subscription.created %s contended on lock; another "
                    "replica is processing",
                    event.id,
                )
                return

            user_id = event.data.get("user_id")
            subscription_id = event.data.get("subscription_id")
            plan_id = event.data.get("plan_id")
            monthly_credits = event.data.get("monthly_credits", 0)

            if not user_id or not subscription_id:
                logger.warning(
                    f"subscription.created event missing required fields: {event.id}"
                )
                return

            wallet = await wallet_service.repository.get_primary_wallet(user_id)
            if not wallet:
                logger.warning(
                    f"No wallet found for user {user_id}, skipping credit allocation"
                )
                _mark_event_processed(event.id)
                outcome.set_result({"status": "skipped", "reason": "no_wallet"})
                return

            if monthly_credits and float(monthly_credits) > 0:
                from ..models import DepositRequest

                deposit_request = DepositRequest(
                    amount=Decimal(str(monthly_credits)),
                    description=f"Subscription credits ({plan_id})",
                    reference_id=subscription_id,
                    metadata={
                        "event_id": event.id,
                        "event_type": event.type,
                        "subscription_id": subscription_id,
                        "plan_id": plan_id,
                        "timestamp": event.timestamp,
                        "is_subscription_credit": True,
                    },
                )

                await wallet_service.deposit(wallet.wallet_id, deposit_request)
                outcome.set_result(
                    {
                        "status": "allocated",
                        "user_id": user_id,
                        "subscription_id": subscription_id,
                        "monthly_credits": str(monthly_credits),
                    }
                )
                logger.info(
                    f"✅ Allocated {monthly_credits} subscription credits to wallet for user {user_id} "
                    f"(subscription: {subscription_id})"
                )
            else:
                outcome.set_result(
                    {
                        "status": "no_credits",
                        "user_id": user_id,
                        "subscription_id": subscription_id,
                    }
                )
                logger.info(
                    f"Subscription {subscription_id} created for user {user_id} (no credits to allocate)"
                )

            _mark_event_processed(event.id)
    except DistributedLockError as exc:
        logger.error(
            "subscription.created %s aborted: distributed lock unavailable: %s",
            event.id,
            exc,
        )
    except LockContended:
        logger.info("subscription.created %s contended; will retry", event.id)
    except Exception as e:
        logger.error(f"Failed to handle subscription.created event {event.id}: {e}")


async def handle_user_deleted(event: Event, wallet_service):
    """
    Handle user.deleted event
    Clean up user's wallet data for GDPR compliance

    Args:
        event: NATS event object
        wallet_service: WalletService instance

    Event Data:
        - user_id: Deleted user ID

    Workflow:
        0. Acquire distributed idempotency lock keyed by event_id (#348)
        1. Validate event data
        2. Get user's wallets
        3. Mark wallets as deleted/frozen
        4. Anonymize transaction history (keep for accounting)
    """
    if _is_event_processed(event.id):
        logger.debug(f"Event {event.id} already processed, skipping")
        return

    try:
        async with _event_lock_guard("user_deleted_wallet", event.id) as outcome:
            if outcome.is_cached:
                _mark_event_processed(event.id)
                return
            if outcome.token == "":
                logger.info(
                    "user.deleted (wallet) %s contended on lock; another "
                    "replica is processing",
                    event.id,
                )
                return

            user_id = event.data.get("user_id")

            if not user_id:
                logger.warning(f"user.deleted event missing user_id: {event.id}")
                return

            logger.info(f"Processing user.deleted for wallet cleanup: {user_id}")

            wallets = await wallet_service.repository.get_user_wallets(user_id)

            if not wallets:
                logger.info(f"No wallets found for deleted user {user_id}")
                _mark_event_processed(event.id)
                outcome.set_result({"status": "skipped", "reason": "no_wallets"})
                return

            frozen_count = 0
            for wallet in wallets:
                try:
                    await wallet_service.repository.deactivate_wallet(wallet.wallet_id)

                    await wallet_service.repository.update_wallet_metadata(
                        wallet.wallet_id,
                        {
                            "user_deleted": True,
                            "user_deleted_at": datetime.now(timezone.utc).isoformat(),
                            "original_user_id": user_id,
                        },
                    )

                    frozen_count += 1
                    logger.debug(f"Frozen wallet {wallet.wallet_id}")

                except Exception as e:
                    logger.error(f"Failed to freeze wallet {wallet.wallet_id}: {e}")

            try:
                anonymized = (
                    await wallet_service.repository.anonymize_user_transactions(user_id)
                )
                logger.info(f"Anonymized {anonymized} transactions for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to anonymize transactions: {e}")

            _mark_event_processed(event.id)
            outcome.set_result(
                {
                    "status": "frozen",
                    "user_id": user_id,
                    "frozen_count": frozen_count,
                }
            )
            logger.info(
                f"✅ User {user_id} wallet cleanup completed: {frozen_count} wallets frozen"
            )
    except DistributedLockError as exc:
        logger.error(
            "user.deleted (wallet) %s aborted: distributed lock unavailable: %s",
            event.id,
            exc,
        )
    except LockContended:
        logger.info("user.deleted (wallet) %s contended; will retry", event.id)
    except Exception as e:
        logger.error(f"Failed to handle user.deleted event {event.id}: {e}")


async def handle_user_created(event: Event, wallet_service):
    """
    Handle user.created event
    Automatically create wallet for new user

    Args:
        event: NATS event object
        wallet_service: WalletService instance

    Event Data:
        - user_id: New user ID

    Workflow:
        0. Acquire distributed idempotency lock keyed by event_id (#348)
        1. Validate event data
        2. Create default wallet for user
        3. Publish wallet.created event
    """
    if _is_event_processed(event.id):
        logger.debug(f"Event {event.id} already processed, skipping")
        return

    try:
        async with _event_lock_guard("user_created", event.id) as outcome:
            if outcome.is_cached:
                _mark_event_processed(event.id)
                return
            if outcome.token == "":
                logger.info(
                    "user.created %s contended on lock; another replica is "
                    "processing",
                    event.id,
                )
                return

            user_id = event.data.get("user_id")

            if not user_id:
                logger.warning(f"user.created event missing user_id: {event.id}")
                return

            # Import here to avoid circular imports
            from datetime import timezone

            from ..models import WalletCreate, WalletType

            # Create wallet for user
            wallet_request = WalletCreate(
                user_id=user_id,
                wallet_type=WalletType.FIAT,
                currency="USD",
                initial_balance=Decimal("0"),
                metadata={
                    "auto_created": True,
                    "event_id": event.id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            wallet = await wallet_service.create_wallet(wallet_request)

            _mark_event_processed(event.id)
            outcome.set_result(
                {
                    "status": "created",
                    "user_id": user_id,
                    "wallet_id": str(wallet.wallet_id),
                }
            )
            logger.info(
                f"✅ Auto-created wallet {wallet.wallet_id} for user {user_id} (event: {event.id})"
            )
    except DistributedLockError as exc:
        logger.error(
            "user.created %s aborted: distributed lock unavailable: %s",
            event.id,
            exc,
        )
    except LockContended:
        logger.info("user.created %s contended; will retry", event.id)
    except Exception as e:
        logger.error(f"Failed to handle user.created event {event.id}: {e}")


# =============================================================================
# Event Handler Registry
# =============================================================================


def get_event_handlers(wallet_service, event_bus):
    """
    Get all event handlers for wallet service.

    Returns a dict mapping event patterns to handler functions.
    This is used by main.py to register all event subscriptions.

    Args:
        wallet_service: WalletService instance
        event_bus: Event bus instance

    Returns:
        Dict[str, callable]: Event pattern -> handler function mapping
    """
    return {
        "payment_service.payment.completed": lambda event: handle_payment_completed(
            event, wallet_service
        ),
        "payment_service.payment.refunded": lambda event: handle_payment_refunded(
            event, wallet_service
        ),
        "subscription_service.subscription.created": lambda event: handle_subscription_created(
            event, wallet_service
        ),
        "account_service.user.created": lambda event: handle_user_created(
            event, wallet_service
        ),
        "account_service.user.deleted": lambda event: handle_user_deleted(
            event, wallet_service
        ),
        "billing.calculated": lambda event: handle_billing_calculated(
            event, wallet_service, event_bus
        ),
        "*.billing.calculated": lambda event: handle_billing_calculated(
            event, wallet_service, event_bus
        ),
        "billing_service.billing.calculated": lambda event: handle_billing_calculated(
            event, wallet_service, event_bus
        ),
    }


__all__ = [
    "handle_billing_calculated",
    "handle_payment_completed",
    "handle_payment_refunded",
    "handle_subscription_created",
    "handle_user_created",
    "handle_user_deleted",
    "get_event_handlers",
]
