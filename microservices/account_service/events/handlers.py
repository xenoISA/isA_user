"""
Account Service Event Handlers

Handle events from other services that affect account management.
"""

import logging
from typing import Any, Dict, Union

logger = logging.getLogger(__name__)


def extract_event_data(event_or_data: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
    """
    Extract data from either an Event object or a raw dict.

    Handles both:
    - Event objects with .data attribute (from NATS)
    - Raw dict (for testing or direct calls)
    """
    if hasattr(event_or_data, 'data'):
        return event_or_data.data
    return event_or_data


# ============================================================================
# Event Handlers
# ============================================================================


async def handle_payment_completed(event_or_data: Union[Dict[str, Any], Any]):
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
        event_data = extract_event_data(event_or_data)
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


async def handle_organization_member_added(event_or_data: Union[Dict[str, Any], Any]):
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
        event_data = extract_event_data(event_or_data)
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


async def handle_wallet_created(event_or_data: Union[Dict[str, Any], Any]):
    """
    Handle wallet.created event from wallet_service

    Confirmation that wallet was created for a user

    Event data:
        - user_id: User ID
        - wallet_id: Wallet ID
        - currency: Wallet currency
    """
    try:
        event_data = extract_event_data(event_or_data)
        user_id = event_data.get("user_id")
        wallet_id = event_data.get("wallet_id")

        logger.info(
            f"Received wallet.created confirmation for user {user_id}, wallet_id: {wallet_id}"
        )

        # We can track that the wallet creation was successful
        # Useful for debugging account creation flows

    except Exception as e:
        logger.error(f"Error handling wallet.created event: {e}")


async def handle_subscription_created(event_or_data: Union[Dict[str, Any], Any], account_repository=None):
    """
    Handle subscription.created event from subscription_service

    Update user's subscription status when they subscribe

    Event data:
        - user_id: User ID
        - subscription_id: Subscription ID
        - tier_code: Subscription tier
        - credits_allocated: Monthly credits
    """
    try:
        event_data = extract_event_data(event_or_data)
        user_id = event_data.get("user_id")
        subscription_id = event_data.get("subscription_id")
        tier_code = event_data.get("tier_code")

        if not user_id:
            logger.warning("subscription.created event missing user_id")
            return

        logger.info(
            f"Processing subscription.created for user {user_id}, tier: {tier_code}"
        )

        # Update user's subscription status
        if account_repository:
            await account_repository.update_user_subscription(
                user_id=user_id,
                subscription_id=subscription_id,
                subscription_status=tier_code or "active",
            )
            logger.info(f"✅ Updated user {user_id} subscription to {tier_code}")

    except Exception as e:
        logger.error(f"Error handling subscription.created event: {e}")


async def handle_subscription_canceled(event_or_data: Union[Dict[str, Any], Any], account_repository=None):
    """
    Handle subscription.canceled event from subscription_service

    Update user's subscription status when cancelled

    Event data:
        - user_id: User ID
        - subscription_id: Subscription ID
        - reason: Cancellation reason
    """
    try:
        event_data = extract_event_data(event_or_data)
        user_id = event_data.get("user_id")
        subscription_id = event_data.get("subscription_id")
        reason = event_data.get("reason")

        if not user_id:
            logger.warning("subscription.canceled event missing user_id")
            return

        logger.info(
            f"Processing subscription.canceled for user {user_id}, reason: {reason}"
        )

        # Update user's subscription status to free/cancelled
        if account_repository:
            await account_repository.update_user_subscription(
                user_id=user_id,
                subscription_id=None,
                subscription_status="free",
            )
            logger.info(f"✅ Reset user {user_id} subscription to free tier")

    except Exception as e:
        logger.error(f"Error handling subscription.canceled event: {e}")


async def handle_organization_deleted(event_or_data: Union[Dict[str, Any], Any], account_repository=None):
    """
    Handle organization.deleted event from organization_service

    Update users' organization membership when org is deleted

    Event data:
        - organization_id: Organization ID
    """
    try:
        event_data = extract_event_data(event_or_data)
        organization_id = event_data.get("organization_id")

        if not organization_id:
            logger.warning("organization.deleted event missing organization_id")
            return

        logger.info(f"Processing organization.deleted for org {organization_id}")

        # Remove organization association from all users
        if account_repository:
            affected_users = await account_repository.remove_organization_from_users(
                organization_id=organization_id
            )
            logger.info(
                f"✅ Removed org {organization_id} from {affected_users} user accounts"
            )

    except Exception as e:
        logger.error(f"Error handling organization.deleted event: {e}")


# ============================================================================
# Event Handler Registry
# ============================================================================


def get_event_handlers(account_repository=None) -> Dict[str, callable]:
    """
    Return a mapping of event types to handler functions

    This will be used in main.py to register event subscriptions

    Args:
        account_repository: AccountRepository instance for data updates

    Note: All handlers now use extract_event_data() internally to handle
    both Event objects (with .data attr) and raw dicts.
    """
    return {
        "payment.completed": handle_payment_completed,
        "organization.member_added": handle_organization_member_added,
        "wallet.created": handle_wallet_created,
        "subscription_service.subscription.created": lambda event: handle_subscription_created(
            event, account_repository
        ),
        "subscription_service.subscription.canceled": lambda event: handle_subscription_canceled(
            event, account_repository
        ),
        "organization_service.organization.deleted": lambda event: handle_organization_deleted(
            event, account_repository
        ),
    }
