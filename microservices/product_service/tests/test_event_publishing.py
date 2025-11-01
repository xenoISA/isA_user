"""
Product Service Event Publishing Tests

Tests that Product Service correctly publishes events for all operations
"""
import asyncio
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.product_service.product_service import ProductService
from microservices.product_service.models import (
    BillingCycle, SubscriptionStatus, ProductType
)


class MockEventBus:
    """Mock event bus for testing"""

    def __init__(self):
        self.published_events = []

    async def publish_event(self, event: Event):
        """Mock publish event"""
        self.published_events.append(event)

    def get_events_by_type(self, event_type: str):
        """Get events by type"""
        return [e for e in self.published_events if e.type == event_type]

    def clear(self):
        """Clear published events"""
        self.published_events = []


class MockProductRepository:
    """Mock product repository for testing"""

    def __init__(self):
        self.subscriptions = {}
        self.usage_records = []
        self.service_plans = {}
        self.products = {}

    async def create_subscription(self, subscription):
        """Create subscription"""
        self.subscriptions[subscription.subscription_id] = subscription
        return subscription

    async def get_subscription(self, subscription_id: str):
        """Get subscription by ID"""
        return self.subscriptions.get(subscription_id)

    async def update_subscription_status(self, subscription_id: str, status, **kwargs):
        """Update subscription status"""
        if subscription_id in self.subscriptions:
            self.subscriptions[subscription_id].status = status
            return self.subscriptions[subscription_id]
        return None

    async def record_product_usage(self, user_id: str, organization_id: Optional[str],
                                   subscription_id: Optional[str], product_id: str,
                                   usage_amount, session_id: Optional[str] = None,
                                   request_id: Optional[str] = None,
                                   usage_details: Optional[Dict[str, Any]] = None,
                                   usage_timestamp: Optional[Any] = None):
        """Record product usage"""
        usage_record = {
            "user_id": user_id,
            "product_id": product_id,
            "usage_amount": usage_amount
        }
        self.usage_records.append(usage_record)
        return "usage_record_123"

    async def get_service_plan(self, plan_id: str):
        """Get service plan by ID"""
        return self.service_plans.get(plan_id)

    async def get_product(self, product_id: str):
        """Get product by ID"""
        return self.products.get(product_id)


async def test_subscription_created_event():
    """Test that subscription.created event is published"""
    print("\n📝 Testing subscription.created event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockProductRepository()

    # Create mock plan in repository
    class MockPlan:
        plan_id = "plan_123"
        plan_tier = "pro"  # Must be lowercase to match enum
        billing_cycle = BillingCycle.MONTHLY

    mock_repository.service_plans["plan_123"] = MockPlan()

    service = ProductService(mock_repository, event_bus=mock_event_bus)

    # Create subscription
    result = await service.create_subscription(
        user_id="user123",
        plan_id="plan_123",
        organization_id="org456",
        billing_cycle=BillingCycle.MONTHLY,
        metadata={"source": "test"}
    )

    # Check subscription was created
    assert result is not None, "Subscription should be created"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.SUBSCRIPTION_CREATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.PRODUCT_SERVICE.value, "Event source should be product_service"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["plan_id"] == "plan_123", "Event should contain plan_id"
    assert event.data["organization_id"] == "org456", "Event should contain organization_id"

    print("✅ TEST PASSED: subscription.created event published correctly")
    return True


async def test_product_usage_recorded_event():
    """Test that product.usage.recorded event is published"""
    print("\n📝 Testing product.usage.recorded event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockProductRepository()

    # Create mock product in repository
    class MockProduct:
        product_id = "prod_tokens"
        product_name = "AI Tokens"

        def model_dump(self):
            return {
                "product_id": self.product_id,
                "product_name": self.product_name
            }

    mock_repository.products["prod_tokens"] = MockProduct()

    # Create mock active subscription
    class MockSubscription:
        subscription_id = "sub_123"
        user_id = "user123"
        status = SubscriptionStatus.ACTIVE

    mock_repository.subscriptions["sub_123"] = MockSubscription()

    service = ProductService(mock_repository, event_bus=mock_event_bus)

    # Record product usage
    result = await service.record_product_usage(
        user_id="user123",
        organization_id="org456",
        subscription_id="sub_123",
        product_id="prod_tokens",
        usage_amount=Decimal("1000"),
        session_id="session_789",
        request_id="req_456",
        usage_details={"model": "gpt-4"},
        usage_timestamp=datetime.utcnow()
    )

    # Check usage record was created
    assert result["success"] is True, "Usage recording should succeed"
    assert result["usage_record_id"] == "usage_record_123", "Usage record ID should match"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.PRODUCT_USAGE_RECORDED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.PRODUCT_SERVICE.value, "Event source should be product_service"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["product_id"] == "prod_tokens", "Event should contain product_id"
    assert event.data["usage_amount"] == 1000.0, "Event should contain usage_amount"
    assert event.data["session_id"] == "session_789", "Event should contain session_id"

    print("✅ TEST PASSED: product.usage.recorded event published correctly")
    return True


async def test_subscription_activated_event():
    """Test that subscription.activated event is published"""
    print("\n📝 Testing subscription.activated event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockProductRepository()

    service = ProductService(mock_repository, event_bus=mock_event_bus)

    # Create a subscription first
    class MockSubscription:
        subscription_id = "sub_123"
        user_id = "user123"
        organization_id = "org456"
        plan_id = "plan_789"
        status = SubscriptionStatus.PAUSED

    mock_subscription = MockSubscription()
    mock_repository.subscriptions["sub_123"] = mock_subscription

    # Update subscription status to ACTIVE
    await service.update_subscription_status(
        subscription_id="sub_123",
        status=SubscriptionStatus.ACTIVE
    )

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.SUBSCRIPTION_ACTIVATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.PRODUCT_SERVICE.value, "Event source should be product_service"
    assert event.data["subscription_id"] == "sub_123", "Event should contain subscription_id"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["new_status"] == "active", "Event should contain new_status"

    print("✅ TEST PASSED: subscription.activated event published correctly")
    return True


async def test_subscription_canceled_event():
    """Test that subscription.canceled event is published"""
    print("\n📝 Testing subscription.canceled event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockProductRepository()

    service = ProductService(mock_repository, event_bus=mock_event_bus)

    # Create a subscription first
    class MockSubscription:
        subscription_id = "sub_456"
        user_id = "user789"
        organization_id = "org123"
        plan_id = "plan_456"
        status = SubscriptionStatus.ACTIVE

    mock_subscription = MockSubscription()
    mock_repository.subscriptions["sub_456"] = mock_subscription

    # Update subscription status to CANCELED
    await service.update_subscription_status(
        subscription_id="sub_456",
        status=SubscriptionStatus.CANCELED
    )

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.SUBSCRIPTION_CANCELED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.PRODUCT_SERVICE.value, "Event source should be product_service"
    assert event.data["subscription_id"] == "sub_456", "Event should contain subscription_id"
    assert event.data["user_id"] == "user789", "Event should contain user_id"
    assert event.data["new_status"] == "canceled", "Event should contain new_status"

    print("✅ TEST PASSED: subscription.canceled event published correctly")
    return True


async def test_subscription_expired_event():
    """Test that subscription.expired event is published"""
    print("\n📝 Testing subscription.expired event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockProductRepository()

    service = ProductService(mock_repository, event_bus=mock_event_bus)

    # Create a subscription first
    class MockSubscription:
        subscription_id = "sub_789"
        user_id = "user456"
        organization_id = "org789"
        plan_id = "plan_123"
        status = SubscriptionStatus.ACTIVE

    mock_subscription = MockSubscription()
    mock_repository.subscriptions["sub_789"] = mock_subscription

    # Update subscription status to INCOMPLETE_EXPIRED
    await service.update_subscription_status(
        subscription_id="sub_789",
        status=SubscriptionStatus.INCOMPLETE_EXPIRED
    )

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.SUBSCRIPTION_EXPIRED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.PRODUCT_SERVICE.value, "Event source should be product_service"
    assert event.data["subscription_id"] == "sub_789", "Event should contain subscription_id"
    assert event.data["user_id"] == "user456", "Event should contain user_id"
    assert event.data["new_status"] == "incomplete_expired", "Event should contain new_status"

    print("✅ TEST PASSED: subscription.expired event published correctly")
    return True


async def test_subscription_updated_event():
    """Test that subscription.updated event is published for non-specific status changes"""
    print("\n📝 Testing subscription.updated event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockProductRepository()

    service = ProductService(mock_repository, event_bus=mock_event_bus)

    # Create a subscription first
    class MockSubscription:
        subscription_id = "sub_999"
        user_id = "user999"
        organization_id = "org999"
        plan_id = "plan_999"
        status = SubscriptionStatus.ACTIVE

    mock_subscription = MockSubscription()
    mock_repository.subscriptions["sub_999"] = mock_subscription

    # Update subscription status to PAST_DUE (should trigger generic UPDATED event)
    await service.update_subscription_status(
        subscription_id="sub_999",
        status=SubscriptionStatus.PAST_DUE
    )

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.SUBSCRIPTION_UPDATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.PRODUCT_SERVICE.value, "Event source should be product_service"
    assert event.data["subscription_id"] == "sub_999", "Event should contain subscription_id"
    assert event.data["user_id"] == "user999", "Event should contain user_id"
    assert event.data["new_status"] == "past_due", "Event should contain new_status"

    print("✅ TEST PASSED: subscription.updated event published correctly")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("PRODUCT SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)

    tests = [
        ("Subscription Created Event", test_subscription_created_event),
        ("Product Usage Recorded Event", test_product_usage_recorded_event),
        ("Subscription Activated Event", test_subscription_activated_event),
        ("Subscription Canceled Event", test_subscription_canceled_event),
        ("Subscription Expired Event", test_subscription_expired_event),
        ("Subscription Updated Event", test_subscription_updated_event),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} total")
    print("="*80)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
