"""
Wallet Event Publishers

Centralized event publishing functions for wallet service.
All events published by wallet service should be defined here.
"""

import logging
from decimal import Decimal
from typing import Optional

from core.nats_client import Event

from .models import (
    create_tokens_deducted_event_data,
    create_tokens_insufficient_event_data,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Event Publishers
# =============================================================================


async def publish_tokens_deducted(
    event_bus,
    user_id: str,
    billing_record_id: str,
    transaction_id: str,
    tokens_deducted: Decimal,
    balance_before: Decimal,
    balance_after: Decimal,
    monthly_quota: Optional[Decimal] = None,
    monthly_used: Optional[Decimal] = None,
) -> bool:
    """
    Publish wallet.tokens.deducted event

    Notifies other services that tokens have been successfully deducted.

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        billing_record_id: Associated billing record ID
        transaction_id: Wallet transaction ID
        tokens_deducted: Amount of tokens deducted
        balance_before: Balance before deduction
        balance_after: Balance after deduction
        monthly_quota: Optional monthly quota limit
        monthly_used: Optional monthly usage count

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - notification_service: Send low balance alerts
        - compliance_service: Log usage for audit
        - billing_service: Update billing status
    """
    try:
        # Construct event data
        event_data = create_tokens_deducted_event_data(
            user_id=user_id,
            billing_record_id=billing_record_id,
            transaction_id=transaction_id,
            tokens_deducted=tokens_deducted,
            balance_before=balance_before,
            balance_after=balance_after,
            monthly_quota=monthly_quota,
            monthly_used=monthly_used,
        )

        # Create event
        event = Event(
            event_type="wallet.consumed",
            source="wallet_service",
            data=event_data.model_dump(),
        )

        # Override with specific event type
        event.type = "wallet.tokens.deducted"

        # Publish event
        result = await event_bus.publish_event(event)

        if result:
            logger.info(
                f"✅ Published wallet.tokens.deducted event for user {user_id}, "
                f"tokens {tokens_deducted}, balance {balance_after}"
            )
        else:
            logger.error(
                f"❌ Failed to publish wallet.tokens.deducted event for user {user_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error publishing tokens_deducted event: {e}", exc_info=True)
        return False


async def publish_tokens_insufficient(
    event_bus,
    user_id: str,
    billing_record_id: str,
    tokens_required: Decimal,
    tokens_available: Decimal,
    suggested_action: str = "upgrade_plan",
) -> bool:
    """
    Publish wallet.tokens.insufficient event

    Notifies other services that a user has insufficient tokens.

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        billing_record_id: Associated billing record ID
        tokens_required: Required token amount
        tokens_available: Available token amount
        suggested_action: Suggested action (e.g., "upgrade_plan", "add_credits")

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - notification_service: Alert user about insufficient balance
        - billing_service: Mark billing record as failed
    """
    try:
        # Construct event data
        event_data = create_tokens_insufficient_event_data(
            user_id=user_id,
            billing_record_id=billing_record_id,
            tokens_required=tokens_required,
            tokens_available=tokens_available,
            suggested_action=suggested_action,
        )

        # Create event
        event = Event(
            event_type="wallet.consumed",
            source="wallet_service",
            data=event_data.model_dump(),
        )

        # Override with specific event type
        event.type = "wallet.tokens.insufficient"

        # Publish event
        result = await event_bus.publish_event(event)

        if result:
            logger.warning(
                f"⚠️  Published wallet.tokens.insufficient event for user {user_id}, "
                f"required {tokens_required}, available {tokens_available}"
            )
        else:
            logger.error(
                f"❌ Failed to publish wallet.tokens.insufficient event for user {user_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error publishing tokens_insufficient event: {e}", exc_info=True)
        return False


async def publish_wallet_created(
    event_bus,
    user_id: str,
    wallet_id: str,
    wallet_type: str,
    currency: str,
    initial_balance: Decimal,
) -> bool:
    """
    Publish wallet.created event

    Notifies other services that a new wallet has been created.

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        wallet_id: New wallet ID
        wallet_type: Wallet type (e.g., "FIAT", "CRYPTO")
        currency: Currency code
        initial_balance: Initial balance

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - audit_service: Log wallet creation
        - notification_service: Welcome notification
    """
    try:
        event_data = {
            "user_id": user_id,
            "wallet_id": wallet_id,
            "wallet_type": wallet_type,
            "currency": currency,
            "initial_balance": float(initial_balance),
        }

        event = Event(
            event_type="wallet.created",
            source="wallet_service",
            data=event_data,
        )

        result = await event_bus.publish_event(event)

        if result:
            logger.info(
                f"✅ Published wallet.created event for user {user_id}, wallet {wallet_id}"
            )
        else:
            logger.error(
                f"❌ Failed to publish wallet.created event for user {user_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error publishing wallet.created event: {e}", exc_info=True)
        return False


async def publish_balance_low_warning(
    event_bus,
    user_id: str,
    wallet_id: str,
    current_balance: Decimal,
    threshold: Decimal,
) -> bool:
    """
    Publish wallet.balance.low event

    Notifies when wallet balance falls below threshold.

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        wallet_id: Wallet ID
        current_balance: Current balance
        threshold: Low balance threshold

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - notification_service: Alert user about low balance
    """
    try:
        event_data = {
            "user_id": user_id,
            "wallet_id": wallet_id,
            "current_balance": float(current_balance),
            "threshold": float(threshold),
        }

        event = Event(
            event_type="wallet.consumed",  # Reuse existing type
            source="wallet_service",
            data=event_data,
        )

        # Override with specific event type
        event.type = "wallet.balance.low"

        result = await event_bus.publish_event(event)

        if result:
            logger.warning(
                f"⚠️  Published wallet.balance.low event for user {user_id}, "
                f"balance {current_balance} below threshold {threshold}"
            )
        else:
            logger.error(
                f"❌ Failed to publish wallet.balance.low event for user {user_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error publishing balance.low event: {e}", exc_info=True)
        return False


async def publish_deposit_completed(
    event_bus,
    user_id: str,
    wallet_id: str,
    transaction_id: str,
    amount: Decimal,
    balance_after: Decimal,
    reference_id: Optional[str] = None,
) -> bool:
    """
    Publish wallet.deposit.completed event

    Notifies when funds are deposited to wallet.

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        wallet_id: Wallet ID
        transaction_id: Transaction ID
        amount: Deposited amount
        balance_after: Balance after deposit
        reference_id: Optional external reference (e.g., payment_id)

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - notification_service: Notify user of successful deposit
        - audit_service: Log financial transaction
    """
    try:
        event_data = {
            "user_id": user_id,
            "wallet_id": wallet_id,
            "transaction_id": transaction_id,
            "amount": float(amount),
            "balance_after": float(balance_after),
            "reference_id": reference_id,
        }

        event = Event(
            event_type="wallet.deposited",
            source="wallet_service",
            data=event_data,
        )

        result = await event_bus.publish_event(event)

        if result:
            logger.info(
                f"✅ Published wallet.deposit.completed event for user {user_id}, "
                f"amount {amount}"
            )
        else:
            logger.error(
                f"❌ Failed to publish wallet.deposit.completed event for user {user_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error publishing deposit.completed event: {e}", exc_info=True)
        return False


__all__ = [
    "publish_tokens_deducted",
    "publish_tokens_insufficient",
    "publish_wallet_created",
    "publish_balance_low_warning",
    "publish_deposit_completed",
]
