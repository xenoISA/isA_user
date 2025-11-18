"""
Wallet Event Handlers

处理钱包相关的事件订阅和发布
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from core.nats_client import Event, EventType, ServiceSource

from .models import (
    BillingCalculatedEventData,
    TokensDeductedEventData,
    TokensInsufficientEventData,
    parse_billing_calculated_event,
)
from .publishers import publish_tokens_deducted, publish_tokens_insufficient

logger = logging.getLogger(__name__)


async def handle_billing_calculated(event: Event, wallet_service, event_bus):
    """
    处理 billing.calculated 事件并执行 token 扣费

    Args:
        event: 接收到的事件对象
        wallet_service: WalletService 实例
        event_bus: 事件总线实例

    工作流程:
        1. 解析计费事件数据
        2. 检查是否需要扣费（免费额度、订阅包含的不扣费）
        3. 获取用户钱包
        4. 检查余额是否充足
        5. 扣除 token
        6. 发布 tokens.deducted 或 tokens.insufficient 事件
    """
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
            return

        if billing_data.is_included_in_subscription:
            logger.info(
                f"Subscription included usage, no wallet deduction for {billing_data.user_id}"
            )
            # 更新订阅使用量统计（如果需要）
            return

        # 需要从钱包扣费
        tokens_to_deduct = billing_data.token_equivalent

        # 调用 wallet_service 的扣费方法
        deduction_result = await wallet_service.consume_tokens(
            user_id=billing_data.user_id,
            amount=tokens_to_deduct,
            billing_record_id=billing_data.billing_record_id,
            description=f"Usage charge for {billing_data.product_id}",
        )

        if deduction_result.get("success"):
            # 扣费成功，发布 tokens.deducted 事件
            await publish_tokens_deducted(
                event_bus=event_bus,
                user_id=billing_data.user_id,
                billing_record_id=billing_data.billing_record_id,
                transaction_id=deduction_result.get("transaction_id"),
                tokens_deducted=tokens_to_deduct,
                balance_before=Decimal(str(deduction_result.get("balance_before", 0))),
                balance_after=Decimal(str(deduction_result.get("balance_after", 0))),
                monthly_quota=deduction_result.get("monthly_quota"),
                monthly_used=deduction_result.get("monthly_used"),
            )

            logger.info(
                f"Successfully deducted {tokens_to_deduct} tokens from user {billing_data.user_id}, "
                f"new balance: {deduction_result.get('balance_after')}"
            )
        else:
            # 扣费失败（余额不足），发布 tokens.insufficient 事件
            await publish_tokens_insufficient(
                event_bus=event_bus,
                user_id=billing_data.user_id,
                billing_record_id=billing_data.billing_record_id,
                tokens_required=tokens_to_deduct,
                tokens_available=Decimal(
                    str(deduction_result.get("balance_available", 0))
                ),
                suggested_action=deduction_result.get(
                    "suggested_action", "upgrade_plan"
                ),
            )

            logger.warning(
                f"Insufficient tokens for user {billing_data.user_id}, "
                f"required: {tokens_to_deduct}, available: {deduction_result.get('balance_available')}"
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
        1. Validate event data
        2. Get user's primary wallet
        3. Deposit funds to wallet
        4. Publish deposit.completed event
    """
    try:
        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
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

        result = await wallet_service.deposit(wallet.wallet_id, deposit_request)

        _mark_event_processed(event.id)
        logger.info(
            f"✅ Deposited {amount} {currency} to wallet for user {user_id} (event: {event.id})"
        )

    except Exception as e:
        logger.error(f"Failed to handle payment.completed event {event.id}: {e}")


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
        1. Validate event data
        2. Create default wallet for user
        3. Publish wallet.created event
    """
    try:
        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
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
        logger.info(
            f"✅ Auto-created wallet {wallet.wallet_id} for user {user_id} (event: {event.id})"
        )

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
        "account_service.user.created": lambda event: handle_user_created(
            event, wallet_service
        ),
        "billing_service.billing.calculated": lambda event: handle_billing_calculated(
            event, wallet_service, event_bus
        ),
    }


__all__ = [
    "handle_billing_calculated",
    "handle_payment_completed",
    "handle_user_created",
    "get_event_handlers",
]
