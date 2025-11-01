"""
Event Handlers for Billing Service

Handles events from other services to track usage and process billing
"""

import logging
from datetime import datetime
from typing import Set
from decimal import Decimal

from core.nats_client import Event
from .billing_service import BillingService
from .models import RecordUsageRequest, ServiceType

logger = logging.getLogger(__name__)


class BillingEventHandlers:
    """Event handlers for billing service"""

    def __init__(self, billing_service: BillingService):
        self.billing_service = billing_service
        # Track processed event IDs for idempotency
        self.processed_event_ids: Set[str] = set()
        # TODO: In production, use Redis or database for distributed idempotency

    def is_event_processed(self, event_id: str) -> bool:
        """Check if event has already been processed (idempotency)"""
        return event_id in self.processed_event_ids

    def mark_event_processed(self, event_id: str):
        """Mark event as processed"""
        self.processed_event_ids.add(event_id)
        # Limit in-memory cache size
        if len(self.processed_event_ids) > 10000:
            # Remove oldest half
            self.processed_event_ids = set(list(self.processed_event_ids)[5000:])

    async def handle_session_tokens_used(self, event: Event):
        """
        Handle session.tokens_used event
        Record AI token usage for billing
        """
        try:
            # Check idempotency
            if self.is_event_processed(event.id):
                logger.debug(f"Event {event.id} already processed, skipping")
                return

            session_id = event.data.get("session_id")
            user_id = event.data.get("user_id")
            tokens_used = event.data.get("tokens_used", 0)
            cost_usd = event.data.get("cost_usd", 0.0)

            if not user_id or not session_id:
                logger.warning(f"session.tokens_used event missing required fields: {event.id}")
                return

            if tokens_used <= 0:
                logger.debug(f"Skipping zero-token event: {event.id}")
                return

            # Record usage for billing
            usage_request = RecordUsageRequest(
                user_id=user_id,
                product_id="ai_tokens",  # Product ID for AI token usage
                service_type=ServiceType.MODEL_INFERENCE,
                usage_amount=Decimal(str(tokens_used)),
                session_id=session_id,
                request_id=event.data.get("message_id"),
                usage_details={
                    "event_id": event.id,
                    "event_type": event.type,
                    "tokens_used": tokens_used,
                    "cost_usd": cost_usd,
                    "timestamp": event.timestamp
                },
                usage_timestamp=datetime.fromisoformat(event.timestamp) if event.timestamp else datetime.utcnow()
            )

            result = await self.billing_service.record_usage_and_bill(usage_request)

            # Mark as processed
            self.mark_event_processed(event.id)

            if result.success:
                logger.info(f"Recorded {tokens_used} tokens for user {user_id} (event: {event.id})")
            else:
                logger.warning(f"Failed to record tokens for user {user_id}: {result.message}")

        except Exception as e:
            logger.error(f"Failed to handle session.tokens_used event {event.id}: {e}")

    async def handle_order_completed(self, event: Event):
        """
        Handle order.completed event
        Record revenue from completed orders
        """
        try:
            # Check idempotency
            if self.is_event_processed(event.id):
                logger.debug(f"Event {event.id} already processed, skipping")
                return

            order_id = event.data.get("order_id")
            user_id = event.data.get("user_id")
            total_amount = event.data.get("total_amount", 0.0)
            currency = event.data.get("currency", "USD")
            order_type = event.data.get("order_type")

            if not user_id or not order_id:
                logger.warning(f"order.completed event missing required fields: {event.id}")
                return

            # Record order revenue
            # For now, we'll track as a special product type
            usage_request = RecordUsageRequest(
                user_id=user_id,
                product_id=f"order_{order_type}" if order_type else "order_generic",
                service_type=ServiceType.OTHER,
                usage_amount=Decimal(str(total_amount)),
                session_id=order_id,  # Use order_id as session_id for tracking
                request_id=event.data.get("transaction_id"),
                usage_details={
                    "event_id": event.id,
                    "event_type": event.type,
                    "order_id": order_id,
                    "order_type": order_type,
                    "total_amount": total_amount,
                    "currency": currency,
                    "transaction_id": event.data.get("transaction_id"),
                    "payment_confirmed": event.data.get("payment_confirmed", False),
                    "timestamp": event.timestamp
                },
                usage_timestamp=datetime.fromisoformat(event.timestamp) if event.timestamp else datetime.utcnow()
            )

            result = await self.billing_service.record_usage_and_bill(usage_request)

            # Mark as processed
            self.mark_event_processed(event.id)

            if result.success:
                logger.info(f"Recorded order revenue ${total_amount} for user {user_id} (order: {order_id}, event: {event.id})")
            else:
                logger.warning(f"Failed to record order revenue for {order_id}: {result.message}")

        except Exception as e:
            logger.error(f"Failed to handle order.completed event {event.id}: {e}")

    async def handle_session_ended(self, event: Event):
        """
        Handle session.ended event
        Record session completion metrics
        """
        try:
            # Check idempotency
            if self.is_event_processed(event.id):
                logger.debug(f"Event {event.id} already processed, skipping")
                return

            session_id = event.data.get("session_id")
            user_id = event.data.get("user_id")
            total_tokens = event.data.get("total_tokens", 0)
            total_cost = event.data.get("total_cost", 0.0)
            total_messages = event.data.get("total_messages", 0)

            if not user_id or not session_id:
                logger.warning(f"session.ended event missing required fields: {event.id}")
                return

            # Mark as processed (we may already have processed individual token events)
            self.mark_event_processed(event.id)

            logger.info(f"Session {session_id} ended for user {user_id}: {total_messages} messages, {total_tokens} tokens, ${total_cost} cost (event: {event.id})")

            # Note: Individual token usage already recorded via session.tokens_used events
            # This is just for logging/metrics

        except Exception as e:
            logger.error(f"Failed to handle session.ended event {event.id}: {e}")

    def get_event_handler_map(self):
        """Return map of event types to handler functions"""
        return {
            "session.tokens_used": self.handle_session_tokens_used,
            "order.completed": self.handle_order_completed,
            "session.ended": self.handle_session_ended,
        }
