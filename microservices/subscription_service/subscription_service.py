"""
Subscription Service

Business logic for subscription management and credit allocation.
"""

import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from core.nats_client import Event, EventType, ServiceSource
from .subscription_repository import SubscriptionRepository
from .models import (
    UserSubscription, SubscriptionHistory,
    SubscriptionStatus, BillingCycle, SubscriptionAction, InitiatedBy,
    CreateSubscriptionRequest, CreateSubscriptionResponse,
    UpdateSubscriptionRequest, CancelSubscriptionRequest, CancelSubscriptionResponse,
    ConsumeCreditsRequest, ConsumeCreditsResponse, CreditBalanceResponse,
    SubscriptionResponse, SubscriptionListResponse, SubscriptionHistoryResponse,
    SubscriptionStatsResponse
)

logger = logging.getLogger(__name__)


# ====================
# Exceptions
# ====================

class SubscriptionServiceError(Exception):
    """Base exception for subscription service errors"""
    pass


class SubscriptionNotFoundError(SubscriptionServiceError):
    """Subscription not found"""
    pass


class SubscriptionValidationError(SubscriptionServiceError):
    """Validation error"""
    pass


class InsufficientCreditsError(SubscriptionServiceError):
    """Not enough credits"""
    pass


class TierNotFoundError(SubscriptionServiceError):
    """Subscription tier not found"""
    pass


# ====================
# Subscription Service
# ====================

class SubscriptionService:
    """Subscription management service"""

    def __init__(self, event_bus=None, config=None):
        """Initialize subscription service"""
        self.repository = SubscriptionRepository(config=config)
        self.event_bus = event_bus
        self._tier_cache: Dict[str, Dict[str, Any]] = {}
        logger.info("Subscription service initialized")

    async def initialize(self):
        """Initialize the service"""
        await self.repository.initialize()
        # Pre-load tier information
        await self._load_tier_cache()

    async def _load_tier_cache(self):
        """Load subscription tier information from product service"""
        # Default tier definitions (fallback)
        self._tier_cache = {
            "free": {
                "tier_id": "tier_free_001",
                "tier_code": "free",
                "tier_name": "Free",
                "monthly_price_usd": 0,
                "monthly_credits": 1000000,  # 1M credits
                "credit_rollover": False,
                "max_rollover_credits": 0,
                "trial_days": 0
            },
            "pro": {
                "tier_id": "tier_pro_001",
                "tier_code": "pro",
                "tier_name": "Pro",
                "monthly_price_usd": 20,
                "monthly_credits": 30000000,  # 30M credits
                "credit_rollover": True,
                "max_rollover_credits": 15000000,
                "trial_days": 14
            },
            "max": {
                "tier_id": "tier_max_001",
                "tier_code": "max",
                "tier_name": "Max",
                "monthly_price_usd": 50,
                "monthly_credits": 100000000,  # 100M credits
                "credit_rollover": True,
                "max_rollover_credits": 50000000,
                "trial_days": 14
            },
            "team": {
                "tier_id": "tier_team_001",
                "tier_code": "team",
                "tier_name": "Team",
                "monthly_price_usd": 25,  # Per seat
                "monthly_credits": 50000000,  # 50M per seat
                "credit_rollover": True,
                "max_rollover_credits": 25000000,
                "trial_days": 14
            },
            "enterprise": {
                "tier_id": "tier_enterprise_001",
                "tier_code": "enterprise",
                "tier_name": "Enterprise",
                "monthly_price_usd": 0,  # Custom
                "monthly_credits": 0,  # Custom
                "credit_rollover": True,
                "max_rollover_credits": None,
                "trial_days": 30
            }
        }
        logger.info(f"Loaded {len(self._tier_cache)} subscription tiers")

    def _get_tier_info(self, tier_code: str) -> Dict[str, Any]:
        """Get tier information"""
        tier = self._tier_cache.get(tier_code.lower())
        if not tier:
            raise TierNotFoundError(f"Tier '{tier_code}' not found")
        return tier

    # ====================
    # Subscription Operations
    # ====================

    async def create_subscription(
        self,
        request: CreateSubscriptionRequest
    ) -> CreateSubscriptionResponse:
        """Create a new subscription for a user"""
        try:
            # Validate tier
            tier = self._get_tier_info(request.tier_code)

            # Check for existing active subscription
            existing = await self.repository.get_user_subscription(
                user_id=request.user_id,
                organization_id=request.organization_id,
                active_only=True
            )
            if existing:
                return CreateSubscriptionResponse(
                    success=False,
                    message=f"User already has an active subscription: {existing.subscription_id}"
                )

            # Calculate period
            now = datetime.now(timezone.utc)
            if request.billing_cycle == BillingCycle.YEARLY:
                period_end = now + timedelta(days=365)
            elif request.billing_cycle == BillingCycle.QUARTERLY:
                period_end = now + timedelta(days=90)
            else:
                period_end = now + timedelta(days=30)

            # Calculate price
            price = Decimal(str(tier["monthly_price_usd"]))
            if request.billing_cycle == BillingCycle.YEARLY:
                price = price * 12 * Decimal("0.8")  # 20% discount
            elif request.billing_cycle == BillingCycle.QUARTERLY:
                price = price * 3 * Decimal("0.9")  # 10% discount

            # Calculate credits
            credits_allocated = tier["monthly_credits"]
            if request.billing_cycle == BillingCycle.YEARLY:
                credits_allocated = credits_allocated * 12
            elif request.billing_cycle == BillingCycle.QUARTERLY:
                credits_allocated = credits_allocated * 3

            # For team tier, multiply by seats
            if tier["tier_code"] == "team":
                credits_allocated = credits_allocated * request.seats
                price = price * request.seats

            # Handle trial
            is_trial = request.use_trial and tier["trial_days"] > 0
            trial_start = now if is_trial else None
            trial_end = now + timedelta(days=tier["trial_days"]) if is_trial else None

            # Create subscription
            subscription = UserSubscription(
                subscription_id=f"sub_{uuid.uuid4().hex[:16]}",
                user_id=request.user_id,
                organization_id=request.organization_id,
                tier_id=tier["tier_id"],
                tier_code=tier["tier_code"],
                status=SubscriptionStatus.TRIALING if is_trial else SubscriptionStatus.ACTIVE,
                billing_cycle=request.billing_cycle,
                price_paid=price if not is_trial else Decimal("0"),
                currency="USD",
                credits_allocated=credits_allocated,
                credits_used=0,
                credits_remaining=credits_allocated,
                credits_rolled_over=0,
                current_period_start=now,
                current_period_end=period_end,
                trial_start=trial_start,
                trial_end=trial_end,
                is_trial=is_trial,
                seats_purchased=request.seats,
                seats_used=1,
                payment_method_id=request.payment_method_id,
                auto_renew=True,
                next_billing_date=trial_end if is_trial else period_end,
                metadata=request.metadata or {}
            )

            created = await self.repository.create_subscription(subscription)
            if not created:
                return CreateSubscriptionResponse(
                    success=False,
                    message="Failed to create subscription"
                )

            # Add history entry
            await self.repository.add_history(SubscriptionHistory(
                history_id=f"hist_{uuid.uuid4().hex[:16]}",
                subscription_id=created.subscription_id,
                user_id=request.user_id,
                organization_id=request.organization_id,
                action=SubscriptionAction.TRIAL_STARTED if is_trial else SubscriptionAction.CREATED,
                new_tier_code=tier["tier_code"],
                new_status=created.status.value,
                credits_change=credits_allocated,
                credits_balance_after=credits_allocated,
                period_start=now,
                period_end=period_end,
                initiated_by=InitiatedBy.USER
            ))

            # Publish event
            if self.event_bus:
                await self._publish_event(EventType.SUBSCRIPTION_CREATED, {
                    "subscription_id": created.subscription_id,
                    "user_id": request.user_id,
                    "organization_id": request.organization_id,
                    "tier_code": tier["tier_code"],
                    "credits_allocated": credits_allocated,
                    "is_trial": is_trial
                }, subject=created.subscription_id)

            return CreateSubscriptionResponse(
                success=True,
                message=f"Subscription created successfully",
                subscription=created,
                credits_allocated=credits_allocated,
                next_billing_date=created.next_billing_date
            )

        except TierNotFoundError as e:
            return CreateSubscriptionResponse(success=False, message=str(e))
        except Exception as e:
            logger.error(f"Error creating subscription: {e}", exc_info=True)
            return CreateSubscriptionResponse(success=False, message=str(e))

    async def get_subscription(self, subscription_id: str) -> SubscriptionResponse:
        """Get subscription by ID"""
        subscription = await self.repository.get_subscription(subscription_id)
        if not subscription:
            return SubscriptionResponse(
                success=False,
                message=f"Subscription {subscription_id} not found"
            )
        return SubscriptionResponse(
            success=True,
            message="Subscription found",
            subscription=subscription
        )

    async def get_user_subscription(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> SubscriptionResponse:
        """Get active subscription for a user"""
        subscription = await self.repository.get_user_subscription(
            user_id=user_id,
            organization_id=organization_id,
            active_only=True
        )
        if not subscription:
            return SubscriptionResponse(
                success=False,
                message="No active subscription found"
            )
        return SubscriptionResponse(
            success=True,
            message="Subscription found",
            subscription=subscription
        )

    async def get_subscriptions(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        status: Optional[SubscriptionStatus] = None,
        page: int = 1,
        page_size: int = 50
    ) -> SubscriptionListResponse:
        """Get subscriptions with filters"""
        offset = (page - 1) * page_size
        subscriptions = await self.repository.get_subscriptions(
            user_id=user_id,
            organization_id=organization_id,
            status=status,
            limit=page_size,
            offset=offset
        )
        return SubscriptionListResponse(
            success=True,
            message="Subscriptions retrieved",
            subscriptions=subscriptions,
            total=len(subscriptions),
            page=page,
            page_size=page_size
        )

    async def cancel_subscription(
        self,
        subscription_id: str,
        request: CancelSubscriptionRequest,
        user_id: str
    ) -> CancelSubscriptionResponse:
        """Cancel a subscription"""
        try:
            subscription = await self.repository.get_subscription(subscription_id)
            if not subscription:
                raise SubscriptionNotFoundError(f"Subscription {subscription_id} not found")

            # Verify ownership
            if subscription.user_id != user_id:
                raise SubscriptionValidationError("Not authorized to cancel this subscription")

            now = datetime.now(timezone.utc)

            if request.immediate:
                # Cancel immediately
                updates = {
                    "status": SubscriptionStatus.CANCELED.value,
                    "canceled_at": now,
                    "cancellation_reason": request.reason,
                    "auto_renew": False
                }
                effective_date = now
            else:
                # Cancel at period end
                updates = {
                    "cancel_at_period_end": True,
                    "canceled_at": now,
                    "cancellation_reason": request.reason,
                    "auto_renew": False
                }
                effective_date = subscription.current_period_end

            updated = await self.repository.update_subscription(subscription_id, updates)

            # Add history
            await self.repository.add_history(SubscriptionHistory(
                history_id=f"hist_{uuid.uuid4().hex[:16]}",
                subscription_id=subscription_id,
                user_id=user_id,
                organization_id=subscription.organization_id,
                action=SubscriptionAction.CANCELED,
                previous_status=subscription.status.value,
                new_status=SubscriptionStatus.CANCELED.value if request.immediate else subscription.status.value,
                credits_balance_after=updated.credits_remaining if updated else subscription.credits_remaining,
                reason=request.reason,
                initiated_by=InitiatedBy.USER
            ))

            # Publish event
            if self.event_bus:
                await self._publish_event(EventType.SUBSCRIPTION_CANCELED, {
                    "subscription_id": subscription_id,
                    "user_id": user_id,
                    "immediate": request.immediate,
                    "effective_date": effective_date.isoformat()
                }, subject=subscription_id)

            return CancelSubscriptionResponse(
                success=True,
                message="Subscription canceled" if request.immediate else "Subscription will cancel at period end",
                canceled_at=now,
                effective_date=effective_date,
                credits_remaining=updated.credits_remaining if updated else subscription.credits_remaining
            )

        except (SubscriptionNotFoundError, SubscriptionValidationError) as e:
            return CancelSubscriptionResponse(success=False, message=str(e))
        except Exception as e:
            logger.error(f"Error canceling subscription: {e}", exc_info=True)
            return CancelSubscriptionResponse(success=False, message=str(e))

    # ====================
    # Credit Operations
    # ====================

    async def consume_credits(
        self,
        request: ConsumeCreditsRequest
    ) -> ConsumeCreditsResponse:
        """Consume credits from a user's subscription"""
        try:
            # Get user's active subscription
            subscription = await self.repository.get_user_subscription(
                user_id=request.user_id,
                organization_id=request.organization_id,
                active_only=True
            )

            if not subscription:
                return ConsumeCreditsResponse(
                    success=False,
                    message="No active subscription found",
                    credits_consumed=0,
                    credits_remaining=0
                )

            # Check if enough credits
            if subscription.credits_remaining < request.credits_to_consume:
                return ConsumeCreditsResponse(
                    success=False,
                    message=f"Insufficient credits. Available: {subscription.credits_remaining}, Requested: {request.credits_to_consume}",
                    credits_consumed=0,
                    credits_remaining=subscription.credits_remaining,
                    subscription_id=subscription.subscription_id
                )

            # Consume credits
            updated = await self.repository.consume_credits(
                subscription_id=subscription.subscription_id,
                credits_to_consume=request.credits_to_consume
            )

            if not updated:
                return ConsumeCreditsResponse(
                    success=False,
                    message="Failed to consume credits",
                    credits_consumed=0,
                    credits_remaining=subscription.credits_remaining,
                    subscription_id=subscription.subscription_id
                )

            # Add history entry
            await self.repository.add_history(SubscriptionHistory(
                history_id=f"hist_{uuid.uuid4().hex[:16]}",
                subscription_id=subscription.subscription_id,
                user_id=request.user_id,
                organization_id=request.organization_id,
                action=SubscriptionAction.CREDITS_CONSUMED,
                credits_change=-request.credits_to_consume,
                credits_balance_after=updated.credits_remaining,
                reason=f"{request.service_type}: {request.description or 'Usage'}",
                initiated_by=InitiatedBy.SYSTEM,
                metadata={
                    "service_type": request.service_type,
                    "usage_record_id": request.usage_record_id,
                    **(request.metadata or {})
                }
            ))

            # Publish event
            if self.event_bus:
                await self._publish_event(EventType.CREDITS_CONSUMED, {
                    "subscription_id": subscription.subscription_id,
                    "user_id": request.user_id,
                    "credits_consumed": request.credits_to_consume,
                    "credits_remaining": updated.credits_remaining,
                    "service_type": request.service_type,
                    "usage_record_id": request.usage_record_id
                }, subject=subscription.subscription_id)

            return ConsumeCreditsResponse(
                success=True,
                message="Credits consumed successfully",
                credits_consumed=request.credits_to_consume,
                credits_remaining=updated.credits_remaining,
                subscription_id=subscription.subscription_id,
                consumed_from="subscription"
            )

        except Exception as e:
            logger.error(f"Error consuming credits: {e}", exc_info=True)
            return ConsumeCreditsResponse(
                success=False,
                message=str(e),
                credits_consumed=0,
                credits_remaining=0
            )

    async def get_credit_balance(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> CreditBalanceResponse:
        """Get credit balance for a user"""
        try:
            subscription = await self.repository.get_user_subscription(
                user_id=user_id,
                organization_id=organization_id,
                active_only=True
            )

            if not subscription:
                return CreditBalanceResponse(
                    success=True,
                    message="No active subscription",
                    user_id=user_id,
                    organization_id=organization_id,
                    subscription_credits_remaining=0,
                    subscription_credits_total=0,
                    total_credits_available=0
                )

            tier = self._tier_cache.get(subscription.tier_code, {})

            return CreditBalanceResponse(
                success=True,
                message="Credit balance retrieved",
                user_id=user_id,
                organization_id=organization_id,
                subscription_credits_remaining=subscription.credits_remaining,
                subscription_credits_total=subscription.credits_allocated,
                subscription_period_end=subscription.current_period_end,
                total_credits_available=subscription.credits_remaining,
                subscription_id=subscription.subscription_id,
                tier_code=subscription.tier_code,
                tier_name=tier.get("tier_name", subscription.tier_code)
            )

        except Exception as e:
            logger.error(f"Error getting credit balance: {e}", exc_info=True)
            return CreditBalanceResponse(
                success=False,
                message=str(e),
                user_id=user_id,
                organization_id=organization_id
            )

    # ====================
    # History Operations
    # ====================

    async def get_subscription_history(
        self,
        subscription_id: str,
        page: int = 1,
        page_size: int = 50
    ) -> SubscriptionHistoryResponse:
        """Get subscription history"""
        offset = (page - 1) * page_size
        history = await self.repository.get_subscription_history(
            subscription_id=subscription_id,
            limit=page_size,
            offset=offset
        )
        return SubscriptionHistoryResponse(
            success=True,
            message="History retrieved",
            history=history,
            total=len(history)
        )

    # ====================
    # Health Check
    # ====================

    async def health_check(self) -> Dict[str, Any]:
        """Service health check"""
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tiers_loaded": len(self._tier_cache)
        }

    # ====================
    # Event Publishing
    # ====================

    async def _publish_event(self, event_type: EventType, data: Dict[str, Any], subject: Optional[str] = None):
        """Publish an event using the NATS event bus"""
        if self.event_bus:
            try:
                event = Event(
                    event_type=event_type,
                    source=ServiceSource.SUBSCRIPTION_SERVICE,
                    data=data,
                    subject=subject
                )
                result = await self.event_bus.publish_event(event)
                if result:
                    logger.info(f"Published event: {event_type.value}")
                else:
                    logger.warning(f"Failed to publish event: {event_type.value}")
            except Exception as e:
                logger.error(f"Failed to publish event {event_type.value}: {e}")


__all__ = [
    "SubscriptionService",
    "SubscriptionServiceError",
    "SubscriptionNotFoundError",
    "SubscriptionValidationError",
    "InsufficientCreditsError",
    "TierNotFoundError"
]
