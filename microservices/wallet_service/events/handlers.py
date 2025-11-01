#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wallet Service Event Handlers

Handles incoming events from NATS message bus.
"""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from core.events.event_subscriber import EventHandler
from core.events.billing_events import BillingCalculatedEvent, EventType
from core.events.event_publisher import BillingEventPublisher

if TYPE_CHECKING:
    from ..wallet_service import WalletService

logger = logging.getLogger(__name__)


class BillingCalculatedEventHandler(EventHandler):
    """
    Handles billing.calculated events from billing_service.

    Flow:
    1. Receive BillingCalculatedEvent
    2. Get user's wallet
    3. Check if sufficient tokens
    4. Deduct tokens from wallet
    5. Publish wallet.tokens.deducted OR wallet.tokens.insufficient
    """

    def __init__(self, wallet_service: 'WalletService', event_publisher: BillingEventPublisher):
        """
        Initialize handler.

        Args:
            wallet_service: Wallet service instance
            event_publisher: Event publisher for downstream events
        """
        self.wallet_service = wallet_service
        self.event_publisher = event_publisher

    def event_type(self) -> str:
        """Return event type this handler processes"""
        return EventType.COST_CALCULATED

    async def handle(self, event: BillingCalculatedEvent) -> bool:
        """
        Handle billing.calculated event.

        Args:
            event: BillingCalculatedEvent from billing_service

        Returns:
            True if processed successfully
        """
        try:
            logger.info(
                f"Processing billing event: user={event.user_id}, "
                f"billing_record={event.billing_record_id}, "
                f"tokens={event.token_equivalent:.0f}, "
                f"cost=${event.cost_usd:.6f}"
            )

            # 1. Check if free tier or subscription included
            if event.is_free_tier or event.is_included_in_subscription:
                logger.info(
                    f"Billing covered by free tier/subscription for {event.user_id}, "
                    f"no wallet deduction needed"
                )
                # Still publish event for tracking
                await self.event_publisher.publish_tokens_deducted(
                    user_id=event.user_id,
                    billing_record_id=event.billing_record_id,
                    transaction_id=f"free_{event.billing_record_id}",
                    tokens_deducted=Decimal("0"),
                    balance_before=Decimal("0"),
                    balance_after=Decimal("0")
                )
                return True

            # 2. Get user's primary wallet
            wallet = await self.wallet_service.repository.get_primary_wallet(event.user_id)

            if not wallet:
                logger.warning(f"No wallet found for user {event.user_id}, creating default wallet")
                # Create default wallet with 0 balance
                from ..models import WalletCreate, WalletType
                create_result = await self.wallet_service.create_wallet(
                    WalletCreate(
                        user_id=event.user_id,
                        wallet_type=WalletType.FIAT,
                        initial_balance=Decimal(0),
                        currency="CREDIT"
                    )
                )
                if not create_result.success:
                    logger.error(f"Failed to create wallet for {event.user_id}")
                    return False

                wallet = await self.wallet_service.repository.get_primary_wallet(event.user_id)

            # 3. Check if sufficient tokens
            required_tokens = event.token_equivalent
            available_tokens = wallet.available_balance

            logger.info(
                f"Wallet check: user={event.user_id}, "
                f"required={required_tokens:.0f}, "
                f"available={available_tokens:.0f}"
            )

            if available_tokens < required_tokens:
                logger.warning(
                    f"Insufficient tokens for {event.user_id}: "
                    f"need {required_tokens:.0f}, have {available_tokens:.0f}"
                )

                # Publish insufficient tokens event
                await self.event_publisher.publish_tokens_insufficient(
                    user_id=event.user_id,
                    billing_record_id=event.billing_record_id,
                    tokens_required=required_tokens,
                    tokens_available=available_tokens,
                    suggested_action="upgrade_plan"
                )

                # TODO: Should we reject the operation or allow negative balance?
                # For now, we reject
                return False

            # 4. Deduct tokens from wallet
            from ..models import ConsumeRequest
            consume_result = await self.wallet_service.consume(
                wallet_id=wallet.wallet_id,
                request=ConsumeRequest(
                    amount=required_tokens,
                    description=f"Usage billing: {event.product_id}",
                    usage_record_id=event.billing_record_id,
                    metadata={
                        "product_id": event.product_id,
                        "usage_amount": float(event.actual_usage),
                        "unit_type": event.unit_type,
                        "cost_usd": float(event.cost_usd),
                        "usage_event_id": event.usage_event_id
                    }
                )
            )

            if not consume_result.success:
                logger.error(
                    f"Failed to deduct tokens for {event.user_id}: "
                    f"{consume_result.message}"
                )
                return False

            # 5. Get updated wallet balance
            balance_after = consume_result.balance
            balance_before = balance_after + required_tokens

            # 6. Calculate quota usage percentage (if subscription has quota)
            monthly_quota = None
            monthly_used = None
            percentage_used = None

            # TODO: Get subscription quota from product_service
            # For now, simplified calculation
            if balance_before > 0:
                percentage_used = float((required_tokens / balance_before) * 100)

            # 7. Publish tokens.deducted event
            success = await self.event_publisher.publish_tokens_deducted(
                user_id=event.user_id,
                billing_record_id=event.billing_record_id,
                transaction_id=consume_result.transaction_id,
                tokens_deducted=required_tokens,
                balance_before=balance_before,
                balance_after=balance_after,
                monthly_quota=monthly_quota,
                monthly_used=monthly_used,
                percentage_used=percentage_used
            )

            if success:
                logger.info(
                    f"✅ Tokens deducted successfully: "
                    f"user={event.user_id}, "
                    f"amount={required_tokens:.0f}, "
                    f"new_balance={balance_after:.0f}, "
                    f"transaction={consume_result.transaction_id}"
                )
                return True
            else:
                logger.error("Failed to publish tokens.deducted event")
                # Transaction already completed, so we return True
                # but log the publish failure
                return True

        except Exception as e:
            logger.error(f"Error handling billing.calculated event: {e}", exc_info=True)
            return False
