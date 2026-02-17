"""
Credit Service Event Publishers

Publish events for credit lifecycle and campaign management.
Following the standard event-driven architecture pattern.
"""

import logging
from datetime import datetime
from typing import List, Optional

from core.nats_client import Event

from .models import (
    create_campaign_budget_exhausted_event_data,
    create_credit_allocated_event_data,
    create_credit_consumed_event_data,
    create_credit_expired_event_data,
    create_credit_expiring_soon_event_data,
    create_credit_transferred_event_data,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Credit Lifecycle Event Publishers
# ============================================================================


async def publish_credit_allocated(
    event_bus,
    allocation_id: str,
    user_id: str,
    credit_type: str,
    amount: int,
    expires_at: datetime,
    balance_after: int,
    campaign_id: Optional[str] = None,
):
    """
    Publish credit.allocated event

    Args:
        event_bus: NATS event bus instance
        allocation_id: Allocation record ID
        user_id: User receiving credits
        credit_type: Type of credit (bonus, subscription, referral, etc.)
        amount: Amount of credits allocated
        expires_at: Credit expiration timestamp
        balance_after: Account balance after allocation
        campaign_id: Campaign ID if from campaign (optional)
    """
    try:
        event_data = create_credit_allocated_event_data(
            allocation_id=allocation_id,
            user_id=user_id,
            credit_type=credit_type,
            amount=amount,
            expires_at=expires_at,
            balance_after=balance_after,
            campaign_id=campaign_id,
        )

        event = Event(
            event_type="subscription.credits.allocated",
            source="product_service",  # Using PRODUCT_SERVICE as proxy for credit_service
            data=event_data.model_dump(mode='json'),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published credit.allocated for user {user_id}: {amount} {credit_type} credits"
        )

    except Exception as e:
        logger.error(f"Failed to publish credit.allocated: {e}")


async def publish_credit_consumed(
    event_bus,
    transaction_ids: List[str],
    user_id: str,
    amount: int,
    balance_before: int,
    balance_after: int,
    billing_record_id: Optional[str] = None,
):
    """
    Publish credit.consumed event

    Args:
        event_bus: NATS event bus instance
        transaction_ids: List of transaction IDs (FIFO may use multiple)
        user_id: User consuming credits
        amount: Amount of credits consumed
        balance_before: Account balance before consumption
        balance_after: Account balance after consumption
        billing_record_id: Associated billing record (optional)
    """
    try:
        event_data = create_credit_consumed_event_data(
            transaction_ids=transaction_ids,
            user_id=user_id,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            billing_record_id=billing_record_id,
        )

        event = Event(
            event_type="subscription.credits.consumed",
            source="product_service",  # Using PRODUCT_SERVICE as proxy for credit_service
            data=event_data.model_dump(mode='json'),
        )

        await event_bus.publish_event(event)
        logger.info(
            f"Published credit.consumed for user {user_id}: {amount} credits, balance: {balance_before} -> {balance_after}"
        )

    except Exception as e:
        logger.error(f"Failed to publish credit.consumed: {e}")


async def publish_credit_expired(
    event_bus,
    user_id: str,
    amount: int,
    credit_type: str,
    balance_after: int,
):
    """
    Publish credit.expired event

    Args:
        event_bus: NATS event bus instance
        user_id: User whose credits expired
        amount: Amount of credits expired
        credit_type: Type of credit that expired
        balance_after: Account balance after expiration
    """
    try:
        event_data = create_credit_expired_event_data(
            user_id=user_id,
            amount=amount,
            credit_type=credit_type,
            balance_after=balance_after,
        )

        # Using a custom subject since credit.expired isn't in EventType enum
        # We'll publish with CREDITS_CONSUMED type but different subject
        from core.nats_client import Event as NATSEvent

        await event_bus.publish(
            "credit.expired",
            {
                "event_type": "CREDIT_EXPIRED",
                "source": "credit_service",
                "data": event_data.model_dump(mode='json'),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        logger.info(
            f"Published credit.expired for user {user_id}: {amount} {credit_type} credits"
        )

    except Exception as e:
        logger.error(f"Failed to publish credit.expired: {e}")


async def publish_credit_transferred(
    event_bus,
    transfer_id: str,
    from_user_id: str,
    to_user_id: str,
    amount: int,
    credit_type: str,
):
    """
    Publish credit.transferred event

    Args:
        event_bus: NATS event bus instance
        transfer_id: Transfer transaction ID
        from_user_id: User sending credits
        to_user_id: User receiving credits
        amount: Amount of credits transferred
        credit_type: Type of credit transferred
    """
    try:
        event_data = create_credit_transferred_event_data(
            transfer_id=transfer_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            amount=amount,
            credit_type=credit_type,
        )

        # Using custom subject for credit.transferred
        await event_bus.publish(
            "credit.transferred",
            {
                "event_type": "CREDIT_TRANSFERRED",
                "source": "credit_service",
                "data": event_data.model_dump(mode='json'),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        logger.info(
            f"Published credit.transferred: {amount} {credit_type} from {from_user_id} to {to_user_id}"
        )

    except Exception as e:
        logger.error(f"Failed to publish credit.transferred: {e}")


async def publish_credit_expiring_soon(
    event_bus,
    user_id: str,
    amount: int,
    expires_at: datetime,
    credit_type: str,
):
    """
    Publish credit.expiring_soon event

    Args:
        event_bus: NATS event bus instance
        user_id: User whose credits are expiring
        amount: Amount of credits expiring
        expires_at: Expiration timestamp
        credit_type: Type of credit expiring
    """
    try:
        event_data = create_credit_expiring_soon_event_data(
            user_id=user_id,
            amount=amount,
            expires_at=expires_at,
            credit_type=credit_type,
        )

        # Using custom subject for credit.expiring_soon
        await event_bus.publish(
            "credit.expiring_soon",
            {
                "event_type": "CREDIT_EXPIRING_SOON",
                "source": "credit_service",
                "data": event_data.model_dump(mode='json'),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        logger.info(
            f"Published credit.expiring_soon for user {user_id}: {amount} {credit_type} expiring at {expires_at}"
        )

    except Exception as e:
        logger.error(f"Failed to publish credit.expiring_soon: {e}")


# ============================================================================
# Campaign Event Publishers
# ============================================================================


async def publish_campaign_budget_exhausted(
    event_bus,
    campaign_id: str,
    name: str,
    total_budget: int,
    allocated_amount: int,
):
    """
    Publish credit.campaign.budget_exhausted event

    Args:
        event_bus: NATS event bus instance
        campaign_id: Campaign ID
        name: Campaign name
        total_budget: Total budget allocated to campaign
        allocated_amount: Amount allocated so far (should equal total_budget)
    """
    try:
        event_data = create_campaign_budget_exhausted_event_data(
            campaign_id=campaign_id,
            name=name,
            total_budget=total_budget,
            allocated_amount=allocated_amount,
        )

        # Using custom subject for campaign budget exhausted
        await event_bus.publish(
            "credit.campaign.budget_exhausted",
            {
                "event_type": "CAMPAIGN_BUDGET_EXHAUSTED",
                "source": "credit_service",
                "data": event_data.model_dump(mode='json'),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        logger.info(
            f"Published credit.campaign.budget_exhausted for campaign {campaign_id}: {name}"
        )

    except Exception as e:
        logger.error(f"Failed to publish credit.campaign.budget_exhausted: {e}")
