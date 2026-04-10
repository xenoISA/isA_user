"""
Billing Event Handlers

处理计费相关的事件订阅

Supports both:
- Legacy: core.nats_client.Event (from NATSEventBus)
- New: core.nats_transport.EventEnvelope (from NATSTransport)

Both Event and EventEnvelope have the same interface:
- .id, .type, .source, .data, .timestamp, .metadata
"""

import logging
import os
from datetime import datetime
from decimal import Decimal
from typing import Set, Union

# Support both old and new event types
from core.nats_client import Event
from core.nats_client import EventEnvelope

from ..models import RecordUsageRequest, ServiceType
from .models import BillingSubscribedEventType, UnitType, UsageEventData, parse_usage_event
from .publishers import (
    publish_billing_calculated,
    publish_billing_error,
    publish_usage_recorded,
)

logger = logging.getLogger(__name__)

# Type alias for both event types
EventType = Union[Event, EventEnvelope]


# ============================================================================
# Idempotency Management
# ============================================================================

# Track processed event IDs for idempotency
# TODO: In production, use Redis or database for distributed idempotency
_processed_event_ids: Set[str] = set()


def is_event_processed(event_id: str) -> bool:
    """Check if event has already been processed (idempotency)"""
    return event_id in _processed_event_ids


def mark_event_processed(event_id: str):
    """Mark event as processed"""
    global _processed_event_ids
    _processed_event_ids.add(event_id)
    # Limit in-memory cache size
    if len(_processed_event_ids) > 10000:
        # Remove oldest half
        _processed_event_ids = set(list(_processed_event_ids)[5000:])


def _get_event_repository(billing_service):
    """Return the repository when the active billing service exposes one."""
    repository = getattr(billing_service, "repository", None)
    if repository is None:
        return None
    required_methods = (
        "claim_event_processing",
        "mark_event_processing_completed",
        "mark_event_processing_failed",
    )
    if all(hasattr(repository, method_name) for method_name in required_methods):
        return repository
    return None


async def _claim_usage_event_processing(
    billing_service,
    claim_key: str,
    source_event_id: str,
) -> bool:
    """Claim the event in durable storage when available, otherwise use local memory."""
    repository = _get_event_repository(billing_service)
    if repository is not None:
        processor_id = f"billing_service:{os.getenv('HOSTNAME') or 'local'}:{os.getpid()}"
        return await repository.claim_event_processing(
            claim_key=claim_key,
            source_event_id=source_event_id,
            processor_id=processor_id,
        )

    if is_event_processed(claim_key):
        return False
    return True


async def _mark_usage_event_completed(
    billing_service,
    claim_key: str,
    source_event_id: str,
) -> None:
    repository = _get_event_repository(billing_service)
    if repository is not None:
        await repository.mark_event_processing_completed(
            claim_key=claim_key,
            source_event_id=source_event_id,
        )


async def _mark_usage_event_failed(
    billing_service,
    claim_key: str,
    source_event_id: str,
    error_message: str,
) -> None:
    repository = _get_event_repository(billing_service)
    if repository is not None:
        await repository.mark_event_processing_failed(
            claim_key=claim_key,
            source_event_id=source_event_id,
            error_message=error_message,
        )


# ============================================================================
# Event Handlers - New Architecture (usage.recorded)
# ============================================================================


async def handle_usage_recorded(event: Event, billing_service, event_bus):
    """
    Handle a `billing.usage.recorded.*` event from another service.

    Args:
        event: The incoming event envelope.
        billing_service: Billing service instance.
        event_bus: Event bus instance.
    """
    dedup_key = event.id
    completed = False
    try:
        # Check idempotency by event id first
        if is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        # Parse event payload
        usage_data = parse_usage_event(event.data)
        dedup_key = usage_data.idempotency_key or event.id
        if dedup_key != event.id and is_event_processed(dedup_key):
            logger.debug("Usage event %s already processed via key %s", event.id, dedup_key)
            mark_event_processed(event.id)
            return

        claimed = await _claim_usage_event_processing(
            billing_service=billing_service,
            claim_key=dedup_key,
            source_event_id=event.id,
        )
        if not claimed:
            logger.debug(
                "Usage event %s already has an active/completed durable claim for key %s",
                event.id,
                dedup_key,
            )
            mark_event_processed(event.id)
            if dedup_key != event.id:
                mark_event_processed(dedup_key)
            return

        logger.info(
            f"Processing usage event for user {usage_data.user_id}, "
            f"product {usage_data.product_id}, "
            f"usage {usage_data.usage_amount} {usage_data.unit_type}"
        )

        # Prefer the first-class service_type field and fall back to usage_details
        service_type_str = (
            usage_data.service_type
            or usage_data.usage_details.get("service_type")
            or "model_inference"
        )
        try:
            service_type = ServiceType(service_type_str)
        except ValueError:
            service_type = ServiceType.OTHER

        usage_details = dict(usage_data.usage_details or {})
        if usage_data.service_type:
            usage_details.setdefault("service_type", usage_data.service_type)
        if usage_data.operation_type:
            usage_details.setdefault("operation_type", usage_data.operation_type)
        if usage_data.source_service:
            usage_details.setdefault("source_service", usage_data.source_service)
        if usage_data.resource_name:
            usage_details.setdefault("resource_name", usage_data.resource_name)
        if usage_data.meter_type:
            usage_details.setdefault("meter_type", usage_data.meter_type)
        usage_details.setdefault("billing_surface", usage_data.billing_surface.value)
        if usage_data.cost_components:
            usage_details.setdefault(
                "cost_components",
                [
                    component.model_dump(mode="json", exclude_none=True)
                    for component in usage_data.cost_components
                ],
            )
        if service_type == ServiceType.OTHER and service_type_str:
            usage_details.setdefault("original_service_type", service_type_str)

        # Build the canonical billing request
        request = RecordUsageRequest(
            user_id=usage_data.user_id,
            actor_user_id=usage_data.actor_user_id,
            billing_account_type=usage_data.billing_account_type,
            billing_account_id=usage_data.billing_account_id,
            organization_id=usage_data.organization_id,
            agent_id=usage_data.agent_id,
            subscription_id=usage_data.subscription_id,
            product_id=usage_data.product_id,
            service_type=service_type,
            usage_amount=usage_data.usage_amount,
            unit_type=usage_data.unit_type.value,
            meter_type=usage_data.meter_type,
            operation_type=usage_data.operation_type,
            source_service=usage_data.source_service,
            resource_name=usage_data.resource_name,
            billing_surface=usage_data.billing_surface.value,
            cost_components=[
                component.model_dump(mode="json", exclude_none=True)
                for component in usage_data.cost_components
            ] if usage_data.cost_components else None,
            session_id=usage_data.session_id,
            request_id=usage_data.request_id,
            usage_details=usage_details,
            usage_timestamp=usage_data.timestamp,
        )

        if usage_data.credit_consumption_handled:
            logger.info(
                "Usage event %s was already billed upstream; recording only",
                event.id,
            )
            billing_result = await billing_service.record_usage_with_external_billing(
                request,
                credits_used=usage_data.credits_used,
                cost_usd=usage_data.cost_usd,
                idempotency_key=usage_data.idempotency_key,
                source_event_id=event.id,
            )
        else:
            billing_result = await billing_service.record_usage_and_bill(request)

        if not billing_result or not billing_result.success:
            error_msg = billing_result.message if billing_result else "No response from billing service"
            logger.error(f"Failed to process usage for user {usage_data.user_id}: {error_msg}")
            await _mark_usage_event_failed(
                billing_service=billing_service,
                claim_key=dedup_key,
                source_event_id=event.id,
                error_message=error_msg,
            )
            # Publish an error event for downstream visibility
            await publish_billing_error(
                event_bus=event_bus,
                user_id=usage_data.user_id,
                product_id=usage_data.product_id,
                error_code="BILLING_PROCESSING_FAILED",
                error_message=error_msg,
                usage_event_id=event.id,
            )
            return

        await _mark_usage_event_completed(
            billing_service=billing_service,
            claim_key=dedup_key,
            source_event_id=event.id,
        )
        completed = True

        # Mark both the transport id and publisher idempotency key
        mark_event_processed(event.id)
        if dedup_key != event.id:
            mark_event_processed(dedup_key)

        # Publish the calculated billing event for downstream consumers
        try:
            await publish_billing_calculated(
                event_bus=event_bus,
                user_id=usage_data.user_id,
                billing_record_id=billing_result.billing_record_id or str(event.id),
                product_id=usage_data.product_id,
                actual_usage=usage_data.usage_amount,
                unit_type=usage_data.unit_type,
                token_equivalent=usage_data.usage_amount,  # Simplified: use usage_amount directly
                cost_usd=billing_result.amount_charged or Decimal("0"),
                unit_price=Decimal("0"),  # Simplified placeholder until product pricing is attached
                token_conversion_rate=Decimal("1"),
                is_free_tier=False,
                is_included_in_subscription=False,
                usage_event_id=event.id,
            )
        except Exception as publish_error:
            logger.error(
                "Billing succeeded for usage event %s but publishing billing.calculated failed: %s",
                event.id,
                publish_error,
                exc_info=True,
            )

        logger.info(
            f"✅ Successfully processed usage event {event.id}, "
            f"charged: ${billing_result.amount_charged}, "
            f"method: {billing_result.billing_method_used}"
        )

    except Exception as e:
        if not completed:
            try:
                await _mark_usage_event_failed(
                    billing_service=billing_service,
                    claim_key=dedup_key,
                    source_event_id=event.id,
                    error_message=str(e),
                )
            except Exception as claim_error:
                logger.error(
                    "Failed to mark usage event %s as failed: %s",
                    event.id,
                    claim_error,
                    exc_info=True,
                )
        logger.error(f"❌ Error handling usage_recorded event: {e}", exc_info=True)

        # Publish an error event if the handler itself fails
        try:
            await publish_billing_error(
                event_bus=event_bus,
                user_id=event.data.get("user_id", "unknown"),
                product_id=event.data.get("product_id", "unknown"),
                error_code="HANDLER_ERROR",
                error_message=str(e),
                usage_event_id=event.id,
            )
        except Exception as pub_error:
            logger.error(f"Failed to publish error event: {pub_error}")


# ============================================================================
# Event Handlers - Legacy Support (session.tokens_used, order.completed)
# ============================================================================


async def handle_session_tokens_used(event: Event, billing_service, event_bus):
    """
    Handle session.tokens_used event
    Record AI token usage for billing

    Legacy handler - converts session events to usage records
    """
    try:
        # Check idempotency
        if is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        session_id = event.data.get("session_id")
        user_id = event.data.get("user_id")
        tokens_used = event.data.get("tokens_used", 0)
        cost_usd = event.data.get("cost_usd", 0.0)

        if not user_id or not session_id:
            logger.warning(
                f"session.tokens_used event missing required fields: {event.id}"
            )
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
                "timestamp": event.timestamp,
            },
            usage_timestamp=datetime.fromisoformat(event.timestamp)
            if event.timestamp
            else datetime.utcnow(),
        )

        result = await billing_service.record_usage_and_bill(usage_request)

        # Mark as processed
        mark_event_processed(event.id)

        if result.success:
            logger.info(
                f"✅ Recorded {tokens_used} tokens for user {user_id} (event: {event.id})"
            )
        else:
            logger.warning(
                f"⚠️  Failed to record tokens for user {user_id}: {result.message}"
            )

    except Exception as e:
        logger.error(f"❌ Failed to handle session.tokens_used event {event.id}: {e}")


async def handle_order_completed(event: Event, billing_service, event_bus):
    """
    Handle order.completed event
    Record revenue from completed orders

    Legacy handler - tracks order revenue
    """
    try:
        # Check idempotency
        if is_event_processed(event.id):
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
                "timestamp": event.timestamp,
            },
            usage_timestamp=datetime.fromisoformat(event.timestamp)
            if event.timestamp
            else datetime.utcnow(),
        )

        result = await billing_service.record_usage_and_bill(usage_request)

        # Mark as processed
        mark_event_processed(event.id)

        if result.success:
            logger.info(
                f"✅ Recorded order revenue ${total_amount} for user {user_id} "
                f"(order: {order_id}, event: {event.id})"
            )
        else:
            logger.warning(
                f"⚠️  Failed to record order revenue for {order_id}: {result.message}"
            )

    except Exception as e:
        logger.error(f"❌ Failed to handle order.completed event {event.id}: {e}")


async def handle_session_ended(event: Event, billing_service, event_bus):
    """
    Handle session.ended event
    Record session completion metrics

    Legacy handler - for logging/metrics only
    """
    try:
        # Check idempotency
        if is_event_processed(event.id):
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

        # Mark as processed
        mark_event_processed(event.id)

        logger.info(
            f"Session {session_id} ended for user {user_id}: "
            f"{total_messages} messages, {total_tokens} tokens, ${total_cost} cost (event: {event.id})"
        )

        # Note: Individual token usage already recorded via session.tokens_used events
        # This is just for logging/metrics

    except Exception as e:
        logger.error(f"❌ Failed to handle session.ended event {event.id}: {e}")


# ============================================================================
# Event Subscription Helper
# ============================================================================


async def handle_user_deleted(event: Event, billing_service, event_bus):
    """
    Handle user.deleted event

    When a user is deleted:
    - Finalize any pending billing records
    - Mark user's billing history as from deleted account
    - Cancel any active subscriptions

    Args:
        event: Event object
        billing_service: BillingService instance
        event_bus: Event bus instance
    """
    try:
        # Check idempotency
        if is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        user_id = event.data.get("user_id")

        if not user_id:
            logger.warning(f"user.deleted event missing user_id: {event.id}")
            return

        logger.info(f"Handling user.deleted event for user {user_id}")

        # Finalize any pending billing records
        try:
            await billing_service.finalize_user_billing(user_id)
            logger.info(f"Finalized pending billing for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to finalize billing for user {user_id}: {e}")

        # Cancel any active subscriptions
        try:
            await billing_service.cancel_user_subscriptions(user_id, reason="user_deleted")
            logger.info(f"Cancelled subscriptions for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to cancel subscriptions for user {user_id}: {e}")

        # Mark as processed
        mark_event_processed(event.id)

        logger.info(f"Successfully handled user.deleted event for user {user_id}")

    except Exception as e:
        logger.error(f"❌ Failed to handle user.deleted event {event.id}: {e}")


def get_event_handlers(billing_service, event_bus):
    """
    获取所有事件处理器的映射

    Args:
        billing_service: BillingService 实例
        event_bus: 事件总线实例

    Returns:
        dict: {pattern: handler_function} 映射
    """
    return {
        # New architecture
        "billing.usage.recorded.>": lambda event: handle_usage_recorded(
            event, billing_service, event_bus
        ),
        "*.billing.usage.recorded.>": lambda event: handle_usage_recorded(
            event, billing_service, event_bus
        ),
        # Legacy support
        "session.tokens_used": lambda event: handle_session_tokens_used(
            event, billing_service, event_bus
        ),
        "*.session.tokens_used": lambda event: handle_session_tokens_used(
            event, billing_service, event_bus
        ),
        "order.completed": lambda event: handle_order_completed(
            event, billing_service, event_bus
        ),
        "*.order.completed": lambda event: handle_order_completed(
            event, billing_service, event_bus
        ),
        "session.ended": lambda event: handle_session_ended(
            event, billing_service, event_bus
        ),
        "*.session.ended": lambda event: handle_session_ended(
            event, billing_service, event_bus
        ),
        # User lifecycle
        "user.deleted": lambda event: handle_user_deleted(
            event, billing_service, event_bus
        ),
        "*.user.deleted": lambda event: handle_user_deleted(
            event, billing_service, event_bus
        ),
    }
