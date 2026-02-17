"""
Credit Service Event Handlers

Handle events from other services that trigger credit operations.
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


async def handle_user_created(event_or_data: Union[Dict[str, Any], Any], credit_service=None):
    """
    Handle user.created event from account_service

    Allocate sign-up bonus credits to new users

    Event data:
        - user_id: User ID
        - email: User email
        - name: User display name
        - subscription_plan: Initial subscription plan
    """
    try:
        event_data = extract_event_data(event_or_data)
        user_id = event_data.get("user_id")

        if not user_id:
            logger.warning("user.created event missing user_id")
            return

        logger.info(f"Processing user.created for user {user_id}")

        # Find active sign-up bonus campaign
        if credit_service:
            campaign = await credit_service.get_active_signup_campaign()
            if campaign:
                try:
                    await credit_service.allocate_from_campaign(
                        user_id=user_id,
                        campaign_id=campaign["campaign_id"]
                    )
                    logger.info(f"Sign-up bonus allocated for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to allocate sign-up bonus: {e}")
            else:
                logger.info(f"No active sign-up campaign found for user {user_id}")

    except Exception as e:
        logger.error(f"Error handling user.created event: {e}")


async def handle_subscription_created(event_or_data: Union[Dict[str, Any], Any], credit_service=None):
    """
    Handle subscription.created event from subscription_service

    Allocate initial subscription credits when user subscribes

    Event data:
        - user_id: User ID
        - subscription_id: Subscription ID
        - tier_code: Subscription tier
        - credits_included: Monthly credits included (optional)
    """
    try:
        event_data = extract_event_data(event_or_data)
        user_id = event_data.get("user_id")
        subscription_id = event_data.get("subscription_id")
        credits_included = event_data.get("credits_included", 0)

        if not user_id:
            logger.warning("subscription.created event missing user_id")
            return

        logger.info(
            f"Processing subscription.created for user {user_id}, credits: {credits_included}"
        )

        if credit_service and credits_included > 0:
            try:
                await credit_service.allocate_credits(
                    user_id=user_id,
                    credit_type="subscription",
                    amount=credits_included,
                    description=f"Subscription credits: {subscription_id}",
                    reference_id=subscription_id,
                    reference_type="subscription",
                )
                logger.info(f"Subscription credits allocated for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to allocate subscription credits: {e}")

    except Exception as e:
        logger.error(f"Error handling subscription.created event: {e}")


async def handle_subscription_renewed(event_or_data: Union[Dict[str, Any], Any], credit_service=None):
    """
    Handle subscription.renewed event from subscription_service

    Allocate monthly subscription credits on renewal

    Event data:
        - user_id: User ID
        - subscription_id: Subscription ID
        - tier_code: Subscription tier
        - credits_included: Monthly credits included
        - period_end: Subscription period end date
    """
    try:
        event_data = extract_event_data(event_or_data)
        user_id = event_data.get("user_id")
        subscription_id = event_data.get("subscription_id")
        credits_included = event_data.get("credits_included", 0)
        period_end = event_data.get("period_end")

        if not user_id:
            logger.warning("subscription.renewed event missing user_id")
            return

        logger.info(
            f"Processing subscription.renewed for user {user_id}, credits: {credits_included}"
        )

        if credit_service and credits_included > 0:
            try:
                # Parse period_end if it's a string
                expires_at = None
                if period_end:
                    from datetime import datetime
                    if isinstance(period_end, str):
                        expires_at = datetime.fromisoformat(period_end.replace('Z', '+00:00'))
                    else:
                        expires_at = period_end

                await credit_service.allocate_credits(
                    user_id=user_id,
                    credit_type="subscription",
                    amount=credits_included,
                    description=f"Monthly subscription credits: {subscription_id}",
                    reference_id=subscription_id,
                    reference_type="subscription",
                    expires_at=expires_at,  # Expire with subscription period
                )
                logger.info(f"Monthly credits allocated for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to allocate monthly credits: {e}")

    except Exception as e:
        logger.error(f"Error handling subscription.renewed event: {e}")


async def handle_order_completed(event_or_data: Union[Dict[str, Any], Any], credit_service=None):
    """
    Handle order.completed event from order_service

    Process referral credits when order completed with referral code

    Event data:
        - user_id: User ID (new customer)
        - order_id: Order ID
        - referral_code: Referral code used (optional)
        - amount: Order amount
    """
    try:
        event_data = extract_event_data(event_or_data)
        user_id = event_data.get("user_id")
        referral_code = event_data.get("referral_code")

        if not referral_code:
            return  # Not a referred order

        logger.info(
            f"Processing order.completed with referral code {referral_code} for user {user_id}"
        )

        if credit_service:
            # Find referrer by code
            referrer = await credit_service.get_referrer_by_code(referral_code)
            if referrer:
                try:
                    # Allocate to referee (new customer)
                    await credit_service.allocate_credits(
                        user_id=user_id,
                        credit_type="referral",
                        amount=500,  # Configurable
                        description="Referral welcome bonus",
                    )
                    # Allocate to referrer
                    await credit_service.allocate_credits(
                        user_id=referrer["user_id"],
                        credit_type="referral",
                        amount=500,  # Configurable
                        description=f"Referral reward for {user_id}",
                    )
                    logger.info(
                        f"Referral credits allocated for {user_id} and {referrer['user_id']}"
                    )
                except Exception as e:
                    logger.error(f"Failed to process referral credits: {e}")
            else:
                logger.warning(f"Referrer not found for code: {referral_code}")

    except Exception as e:
        logger.error(f"Error handling order.completed event: {e}")


async def handle_user_deleted(event_or_data: Union[Dict[str, Any], Any], credit_service=None):
    """
    Handle user.deleted event from account_service

    GDPR compliance - archive all user credit data

    Event data:
        - user_id: User ID
        - email: User email (optional)
        - reason: Deletion reason (optional)
    """
    try:
        event_data = extract_event_data(event_or_data)
        user_id = event_data.get("user_id")

        if not user_id:
            logger.warning("user.deleted event missing user_id")
            return

        logger.info(f"Processing user.deleted for user {user_id} (GDPR cleanup)")

        if credit_service:
            try:
                deleted_count = await credit_service.repository.delete_user_data(user_id)
                logger.info(f"Deleted {deleted_count} credit records for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to delete user credit data: {e}")

    except Exception as e:
        logger.error(f"Error handling user.deleted event: {e}")


# ============================================================================
# Event Handler Registry
# ============================================================================


def get_event_handlers(credit_service=None) -> Dict[str, callable]:
    """
    Return a mapping of event types to handler functions

    This will be used in main.py to register event subscriptions

    Args:
        credit_service: CreditService instance for credit operations

    Note: All handlers use extract_event_data() internally to handle
    both Event objects (with .data attr) and raw dicts.

    Events subscribed:
        - user.created: Allocate sign-up bonus credits
        - subscription.created: Allocate initial subscription credits
        - subscription.renewed: Allocate monthly subscription credits
        - order.completed: Process referral credits
        - user.deleted: GDPR cleanup
    """
    return {
        "user.created": lambda event: handle_user_created(event, credit_service),
        "subscription.created": lambda event: handle_subscription_created(event, credit_service),
        "subscription.renewed": lambda event: handle_subscription_renewed(event, credit_service),
        "order.completed": lambda event: handle_order_completed(event, credit_service),
        "user.deleted": lambda event: handle_user_deleted(event, credit_service),
    }
