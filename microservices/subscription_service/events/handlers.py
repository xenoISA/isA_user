"""
Subscription Event Handlers

Handles incoming events from other services that affect subscriptions.
"""

import logging
from typing import Dict, Any, Callable, Awaitable

from ..subscription_service import SubscriptionService
from ..models import ConsumeCreditsRequest

logger = logging.getLogger(__name__)


class SubscriptionEventHandlers:
    """Event handlers for subscription service"""

    def __init__(self, subscription_service: SubscriptionService):
        self.subscription_service = subscription_service

    def get_event_handler_map(self) -> Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]]:
        """Get mapping of event patterns to handler functions"""
        return {
            "billing.credits.consume": self.handle_credits_consume_request,
            "payment.succeeded": self.handle_payment_succeeded,
            "payment.failed": self.handle_payment_failed,
            "account.created": self.handle_account_created,
        }

    async def handle_credits_consume_request(self, event_data: Dict[str, Any]) -> None:
        """Handle request to consume credits"""
        try:
            user_id = event_data.get("user_id")
            organization_id = event_data.get("organization_id")
            credits_to_consume = event_data.get("credits_to_consume", 0)
            service_type = event_data.get("service_type", "unknown")
            usage_record_id = event_data.get("usage_record_id")

            if not user_id or credits_to_consume <= 0:
                logger.warning(f"Invalid credits consume request: {event_data}")
                return

            request = ConsumeCreditsRequest(
                user_id=user_id,
                organization_id=organization_id,
                credits_to_consume=credits_to_consume,
                service_type=service_type,
                usage_record_id=usage_record_id
            )

            response = await self.subscription_service.consume_credits(request)

            if response.success:
                logger.info(
                    f"Consumed {credits_to_consume} credits for user {user_id}, "
                    f"remaining: {response.credits_remaining}"
                )
            else:
                logger.warning(
                    f"Failed to consume credits for user {user_id}: {response.message}"
                )

        except Exception as e:
            logger.error(f"Error handling credits consume request: {e}", exc_info=True)

    async def handle_payment_succeeded(self, event_data: Dict[str, Any]) -> None:
        """Handle successful payment event"""
        try:
            subscription_id = event_data.get("subscription_id")
            if not subscription_id:
                return

            logger.info(f"Payment succeeded for subscription {subscription_id}")
            # Could trigger subscription renewal, status update, etc.

        except Exception as e:
            logger.error(f"Error handling payment succeeded: {e}", exc_info=True)

    async def handle_payment_failed(self, event_data: Dict[str, Any]) -> None:
        """Handle failed payment event"""
        try:
            subscription_id = event_data.get("subscription_id")
            if not subscription_id:
                return

            logger.info(f"Payment failed for subscription {subscription_id}")
            # Could trigger status change to past_due, send notification, etc.

        except Exception as e:
            logger.error(f"Error handling payment failed: {e}", exc_info=True)

    async def handle_account_created(self, event_data: Dict[str, Any]) -> None:
        """Handle new account creation - auto-create free subscription"""
        try:
            user_id = event_data.get("user_id")
            if not user_id:
                return

            logger.info(f"New account created: {user_id}, considering free tier assignment")
            # Could auto-create free subscription for new users

        except Exception as e:
            logger.error(f"Error handling account created: {e}", exc_info=True)


__all__ = ["SubscriptionEventHandlers"]
