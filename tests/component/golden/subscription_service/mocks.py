"""
Subscription Service - Mock Dependencies

Mock implementations for component testing.
These mocks simulate repository and external service behavior.
"""
from unittest.mock import AsyncMock, MagicMock
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from decimal import Decimal
import uuid


class MockSubscriptionRepository:
    """Mock subscription repository for component testing"""

    def __init__(self):
        self._subscriptions: Dict[str, Dict] = {}
        self._history: Dict[str, List[Dict]] = {}
        self._initialized = False

        # Setup mock methods
        self.initialize = AsyncMock(side_effect=self._initialize)
        self.close = AsyncMock()
        self.create_subscription = AsyncMock(side_effect=self._create_subscription)
        self.get_subscription = AsyncMock(side_effect=self._get_subscription)
        self.get_user_subscription = AsyncMock(side_effect=self._get_user_subscription)
        self.get_subscriptions = AsyncMock(side_effect=self._get_subscriptions)
        self.update_subscription = AsyncMock(side_effect=self._update_subscription)
        self.consume_credits = AsyncMock(side_effect=self._consume_credits)
        self.allocate_credits = AsyncMock(side_effect=self._allocate_credits)
        self.add_history = AsyncMock(side_effect=self._add_history)
        self.get_subscription_history = AsyncMock(side_effect=self._get_subscription_history)

    async def _initialize(self) -> None:
        """Mock initialization"""
        self._initialized = True

    async def _create_subscription(self, subscription) -> Any:
        """Mock subscription creation"""
        sub_id = subscription.subscription_id
        now = datetime.now(timezone.utc)

        # Create mock subscription object
        sub = MagicMock()
        sub.subscription_id = sub_id
        sub.user_id = subscription.user_id
        sub.organization_id = subscription.organization_id
        sub.tier_id = subscription.tier_id
        sub.tier_code = subscription.tier_code
        sub.status = subscription.status
        sub.billing_cycle = subscription.billing_cycle
        sub.price_paid = subscription.price_paid
        sub.currency = subscription.currency
        sub.credits_allocated = subscription.credits_allocated
        sub.credits_used = subscription.credits_used
        sub.credits_remaining = subscription.credits_remaining
        sub.credits_rolled_over = subscription.credits_rolled_over
        sub.current_period_start = subscription.current_period_start
        sub.current_period_end = subscription.current_period_end
        sub.trial_start = subscription.trial_start
        sub.trial_end = subscription.trial_end
        sub.is_trial = subscription.is_trial
        sub.seats_purchased = subscription.seats_purchased
        sub.seats_used = subscription.seats_used
        sub.cancel_at_period_end = subscription.cancel_at_period_end
        sub.canceled_at = subscription.canceled_at
        sub.cancellation_reason = subscription.cancellation_reason
        sub.payment_method_id = subscription.payment_method_id
        sub.auto_renew = subscription.auto_renew
        sub.next_billing_date = subscription.next_billing_date
        sub.metadata = subscription.metadata
        sub.created_at = now
        sub.updated_at = now

        self._subscriptions[sub_id] = {
            "subscription_id": sub_id,
            "user_id": subscription.user_id,
            "organization_id": subscription.organization_id,
            "tier_id": subscription.tier_id,
            "tier_code": subscription.tier_code,
            "status": subscription.status.value if hasattr(subscription.status, 'value') else subscription.status,
            "billing_cycle": subscription.billing_cycle.value if hasattr(subscription.billing_cycle, 'value') else subscription.billing_cycle,
            "price_paid": float(subscription.price_paid),
            "currency": subscription.currency,
            "credits_allocated": subscription.credits_allocated,
            "credits_used": subscription.credits_used,
            "credits_remaining": subscription.credits_remaining,
            "credits_rolled_over": subscription.credits_rolled_over,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "trial_start": subscription.trial_start,
            "trial_end": subscription.trial_end,
            "is_trial": subscription.is_trial,
            "seats_purchased": subscription.seats_purchased,
            "seats_used": subscription.seats_used,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "canceled_at": subscription.canceled_at,
            "cancellation_reason": subscription.cancellation_reason,
            "payment_method_id": subscription.payment_method_id,
            "auto_renew": subscription.auto_renew,
            "next_billing_date": subscription.next_billing_date,
            "metadata": subscription.metadata,
            "created_at": now,
            "updated_at": now,
        }

        return sub

    async def _get_subscription(self, subscription_id: str) -> Optional[Any]:
        """Mock get subscription by ID"""
        data = self._subscriptions.get(subscription_id)
        if not data:
            return None

        sub = MagicMock()
        for key, value in data.items():
            setattr(sub, key, value)
        return sub

    async def _get_user_subscription(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        active_only: bool = True
    ) -> Optional[Any]:
        """Mock get user subscription"""
        for sub_id, data in self._subscriptions.items():
            if data["user_id"] == user_id:
                # Check org context
                if organization_id is not None:
                    if data.get("organization_id") != organization_id:
                        continue
                else:
                    if data.get("organization_id") is not None:
                        continue

                # Check active status
                if active_only:
                    if data["status"] not in ["active", "trialing"]:
                        continue

                sub = MagicMock()
                for key, value in data.items():
                    setattr(sub, key, value)
                return sub
        return None

    async def _get_subscriptions(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        status: Optional[str] = None,
        tier_code: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Any]:
        """Mock get subscriptions with filters"""
        results = []
        for sub_id, data in self._subscriptions.items():
            if user_id and data["user_id"] != user_id:
                continue
            if organization_id and data.get("organization_id") != organization_id:
                continue
            if status:
                status_val = status.value if hasattr(status, 'value') else status
                if data["status"] != status_val:
                    continue
            if tier_code and data["tier_code"] != tier_code:
                continue

            sub = MagicMock()
            for key, value in data.items():
                setattr(sub, key, value)
            results.append(sub)

        return results[offset:offset + limit]

    async def _update_subscription(
        self,
        subscription_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Any]:
        """Mock update subscription"""
        if subscription_id not in self._subscriptions:
            return None

        data = self._subscriptions[subscription_id]
        data.update(update_data)
        data["updated_at"] = datetime.now(timezone.utc)

        sub = MagicMock()
        for key, value in data.items():
            setattr(sub, key, value)
        return sub

    async def _consume_credits(
        self,
        subscription_id: str,
        credits_to_consume: int
    ) -> Optional[Any]:
        """Mock consume credits"""
        if subscription_id not in self._subscriptions:
            return None

        data = self._subscriptions[subscription_id]
        if data["credits_remaining"] < credits_to_consume:
            return None

        data["credits_used"] += credits_to_consume
        data["credits_remaining"] -= credits_to_consume
        data["updated_at"] = datetime.now(timezone.utc)

        sub = MagicMock()
        for key, value in data.items():
            setattr(sub, key, value)
        return sub

    async def _allocate_credits(
        self,
        subscription_id: str,
        credits: int,
        rollover: int = 0
    ) -> bool:
        """Mock allocate credits"""
        if subscription_id not in self._subscriptions:
            return False

        data = self._subscriptions[subscription_id]
        data["credits_allocated"] = credits
        data["credits_remaining"] = credits + rollover
        data["credits_rolled_over"] = rollover
        data["credits_used"] = 0
        data["updated_at"] = datetime.now(timezone.utc)
        return True

    async def _add_history(self, history) -> Any:
        """Mock add history"""
        hist_id = history.history_id
        sub_id = history.subscription_id
        now = datetime.now(timezone.utc)

        hist = MagicMock()
        hist.history_id = hist_id
        hist.subscription_id = sub_id
        hist.user_id = history.user_id
        hist.organization_id = history.organization_id
        hist.action = history.action
        hist.previous_tier_code = history.previous_tier_code
        hist.new_tier_code = history.new_tier_code
        hist.previous_status = history.previous_status
        hist.new_status = history.new_status
        hist.credits_change = history.credits_change
        hist.credits_balance_after = history.credits_balance_after
        hist.reason = history.reason
        hist.initiated_by = history.initiated_by
        hist.metadata = history.metadata
        hist.created_at = now

        if sub_id not in self._history:
            self._history[sub_id] = []
        self._history[sub_id].append({
            "history_id": hist_id,
            "subscription_id": sub_id,
            "user_id": history.user_id,
            "action": history.action.value if hasattr(history.action, 'value') else history.action,
            "credits_change": history.credits_change,
            "credits_balance_after": history.credits_balance_after,
            "created_at": now,
        })

        return hist

    async def _get_subscription_history(
        self,
        subscription_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Any]:
        """Mock get subscription history"""
        history_list = self._history.get(subscription_id, [])
        results = []
        for h in history_list[offset:offset + limit]:
            hist = MagicMock()
            for key, value in h.items():
                setattr(hist, key, value)
            results.append(hist)
        return results

    def add_subscription(self, subscription_data: Dict[str, Any]):
        """Helper to add subscription for testing"""
        sub_id = subscription_data.get("subscription_id", f"sub_{uuid.uuid4().hex[:16]}")
        subscription_data["subscription_id"] = sub_id
        self._subscriptions[sub_id] = subscription_data

    def reset(self):
        """Reset mock state"""
        self._subscriptions.clear()
        self._history.clear()


class MockEventBus:
    """Mock NATS event bus for component testing"""

    def __init__(self):
        self.published_events: List[Any] = []
        self.publish_event = AsyncMock(side_effect=self._publish_event)

    async def _publish_event(self, event: Any) -> bool:
        """Mock event publishing"""
        self.published_events.append(event)
        return True

    def get_published_events(self) -> List[Any]:
        """Get all published events"""
        return self.published_events

    def get_events_by_type(self, event_type: str) -> List[Any]:
        """Get published events by type"""
        result = []
        for e in self.published_events:
            # Event objects from nats_client use 'type' attribute, not 'event_type'
            if hasattr(e, 'type'):
                evt_type = e.type.value if hasattr(e.type, 'value') else str(e.type)
                if evt_type == event_type:
                    result.append(e)
            elif hasattr(e, 'event_type'):
                evt_type = e.event_type.value if hasattr(e.event_type, 'value') else str(e.event_type)
                if evt_type == event_type:
                    result.append(e)
        return result

    def reset(self):
        """Reset mock state"""
        self.published_events.clear()


# ============================================================================
# Test Data Factory for Component Tests
# ============================================================================

class SubscriptionTestDataFactory:
    """Test data factory for component tests"""

    @staticmethod
    def make_subscription_id() -> str:
        return f"sub_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_user_id() -> str:
        return f"user_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_organization_id() -> str:
        return f"org_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_active_subscription_data(user_id: str = None, credits: int = 30000000) -> Dict[str, Any]:
        """Generate active subscription data"""
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        return {
            "subscription_id": SubscriptionTestDataFactory.make_subscription_id(),
            "user_id": user_id or SubscriptionTestDataFactory.make_user_id(),
            "organization_id": None,
            "tier_id": "tier_pro_001",
            "tier_code": "pro",
            "status": "active",
            "billing_cycle": "monthly",
            "price_paid": 20.0,
            "currency": "USD",
            "credits_allocated": credits,
            "credits_used": 0,
            "credits_remaining": credits,
            "credits_rolled_over": 0,
            "current_period_start": now,
            "current_period_end": now + timedelta(days=30),
            "trial_start": None,
            "trial_end": None,
            "is_trial": False,
            "seats_purchased": 1,
            "seats_used": 1,
            "cancel_at_period_end": False,
            "canceled_at": None,
            "cancellation_reason": None,
            "payment_method_id": f"pm_{uuid.uuid4().hex[:16]}",
            "auto_renew": True,
            "next_billing_date": now + timedelta(days=30),
            "metadata": {},
            "created_at": now,
            "updated_at": now,
        }
