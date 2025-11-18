"""
Account Service Event Handlers

Handle events from other services that affect account management.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


# ============================================================================
# Event Handlers
# ============================================================================


async def handle_payment_completed(event_data: Dict[str, Any]):
    """
    Handle payment.completed event from billing_service

    When a payment is completed for a subscription, update user's subscription status

    Event data:
        - user_id: User ID
        - payment_type: Type of payment (subscription/one_time)
        - subscription_plan: New subscription plan (if applicable)
        - amount: Payment amount
    """
    try:
        user_id = event_data.get("user_id")
        payment_type = event_data.get("payment_type")
        subscription_plan = event_data.get("subscription_plan")

        logger.info(
            f"Received payment.completed for user {user_id}, type: {payment_type}"
        )

        # Only process subscription payments
        if payment_type == "subscription" and subscription_plan:
            # TODO: Update user's subscription_status in database
            # This would require accessing the account repository
            logger.info(
                f"User {user_id} subscription should be updated to {subscription_plan}"
            )

            # Note: In a real implementation, we would:
            # 1. Get account repository instance
            # 2. Update user's subscription_status field
            # 3. Publish user.subscription_changed event

    except Exception as e:
        logger.error(f"Error handling payment.completed event: {e}")
        # Don't raise - event handler failures should be logged but not crash the service


async def handle_organization_member_added(event_data: Dict[str, Any]):
    """
    Handle organization.member_added event from organization_service

    When a user is added to an organization, we might want to:
    - Update user's default organization
    - Track user's organization memberships
    - Send notification

    Event data:
        - organization_id: Organization ID
        - user_id: User ID
        - role: User's role in organization
    """
    try:
        organization_id = event_data.get("organization_id")
        user_id = event_data.get("user_id")
        role = event_data.get("role")

        logger.info(
            f"Received organization.member_added: user {user_id} added to org {organization_id} as {role}"
        )

        # TODO: Update user's organization membership info if needed
        # For now, just log it

    except Exception as e:
        logger.error(f"Error handling organization.member_added event: {e}")


async def handle_wallet_created(event_data: Dict[str, Any]):
    """
    Handle wallet.created event from wallet_service

    Confirmation that wallet was created for a user

    Event data:
        - user_id: User ID
        - wallet_id: Wallet ID
        - currency: Wallet currency
    """
    try:
        user_id = event_data.get("user_id")
        wallet_id = event_data.get("wallet_id")

        logger.info(
            f"Received wallet.created confirmation for user {user_id}, wallet_id: {wallet_id}"
        )

        # We can track that the wallet creation was successful
        # Useful for debugging account creation flows

    except Exception as e:
        logger.error(f"Error handling wallet.created event: {e}")


# ============================================================================
# Event Handler Registry
# ============================================================================


def get_event_handlers() -> Dict[str, callable]:
    """
    Return a mapping of event types to handler functions

    This will be used in main.py to register event subscriptions
    """
    return {
        "payment.completed": handle_payment_completed,
        "organization.member_added": handle_organization_member_added,
        "wallet.created": handle_wallet_created,
    }
