"""
Billing Service Event Publishing Tests

Tests that Billing Service correctly publishes events for all billing operations
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
from microservices.billing_service.billing_service import BillingService
from microservices.billing_service.models import (
    RecordUsageRequest, BillingCalculationRequest, BillingCalculationResponse,
    ProcessBillingRequest, QuotaCheckRequest, QuotaCheckResponse,
    BillingStatus, BillingMethod, ServiceType, Currency
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


class MockBillingRepository:
    """Mock billing repository for testing"""

    def __init__(self):
        self.billing_records = {}
        self.billing_events = []

    async def create_billing_record(self, billing_record):
        """Create billing record"""
        self.billing_records[billing_record.billing_id] = billing_record
        return billing_record

    async def update_billing_record_status(self, billing_id: str, status, **kwargs):
        """Update billing record status"""
        if billing_id in self.billing_records:
            self.billing_records[billing_id].billing_status = status
            return self.billing_records[billing_id]
        return None

    async def create_billing_event(self, billing_event):
        """Create billing event"""
        self.billing_events.append(billing_event)
        return billing_event


async def test_usage_recorded_event():
    """Test that billing.usage.recorded event is published"""
    print("\n📝 Testing billing.usage.recorded event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockBillingRepository()

    service = BillingService(mock_repository, event_bus=mock_event_bus)

    # Override consul to avoid actual service calls
    service.consul = None

    # Mock the method that would call external services
    async def mock_record_usage(request):
        return "mock_usage_id_123"

    service._record_usage_to_product_service = mock_record_usage

    # Mock calculate_billing_cost to return a failing result to stop processing early
    async def mock_calculate_cost(request):
        return BillingCalculationResponse(
            success=False,
            message="Test - stopping early",
            product_id=request.product_id,
            usage_amount=request.usage_amount,
            unit_price=Decimal("0"),
            total_cost=Decimal("0"),
            currency=Currency.CREDIT,
            suggested_billing_method=BillingMethod.WALLET_DEDUCTION,
            available_billing_methods=[]
        )

    service.calculate_billing_cost = mock_calculate_cost

    request = RecordUsageRequest(
        user_id="user123",
        organization_id="org456",
        product_id="prod_tokens",
        service_type=ServiceType.MODEL_INFERENCE,
        usage_amount=Decimal("1000"),
        subscription_id=None
    )

    await service.record_usage_and_bill(request)

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.USAGE_RECORDED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.BILLING_SERVICE.value, "Event source should be billing_service"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["product_id"] == "prod_tokens", "Event should contain product_id"
    assert event.data["usage_amount"] == 1000.0, "Event should contain usage_amount"

    print("✅ TEST PASSED: billing.usage.recorded event published correctly")
    return True


async def test_billing_calculated_event():
    """Test that billing.calculated event is published"""
    print("\n📝 Testing billing.calculated event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockBillingRepository()

    service = BillingService(mock_repository, event_bus=mock_event_bus)
    service.consul = None

    # Mock external service calls
    async def mock_get_pricing(product_id, user_id, subscription_id):
        return {
            "pricing_model": {
                "base_unit_price": 0.01,
                "currency": "CREDIT"
            }
        }

    async def mock_get_balances(user_id):
        return Decimal("100"), Decimal("500")

    service._get_product_pricing = mock_get_pricing
    service._get_user_balances = mock_get_balances

    request = BillingCalculationRequest(
        user_id="user123",
        organization_id="org456",
        subscription_id=None,
        product_id="prod_tokens",
        usage_amount=Decimal("1000")
    )

    result = await service.calculate_billing_cost(request)

    # Check calculation succeeded
    assert result.success is True, "Calculation should succeed"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.BILLING_CALCULATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.BILLING_SERVICE.value, "Event source should be billing_service"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["product_id"] == "prod_tokens", "Event should contain product_id"
    assert event.data["total_cost"] == 10.0, "Event should contain total_cost"
    assert event.data["currency"] == "CREDIT", "Event should contain currency"

    print("✅ TEST PASSED: billing.calculated event published correctly")
    return True


async def test_quota_exceeded_event():
    """Test that billing.quota.exceeded event is published"""
    print("\n📝 Testing billing.quota.exceeded event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockBillingRepository()

    service = BillingService(mock_repository, event_bus=mock_event_bus)
    service.consul = None

    # Mock check_quota to return not allowed
    async def mock_check_quota(request):
        return QuotaCheckResponse(
            allowed=False,
            message="Quota exceeded",
            quota_limit=Decimal("10000"),
            quota_used=Decimal("9500"),
            quota_remaining=Decimal("500")
        )

    # Mock other methods
    async def mock_record_usage(request):
        return "mock_usage_id"

    async def mock_calculate_cost(request):
        return BillingCalculationResponse(
            success=True,
            message="Calculated",
            product_id=request.product_id,
            usage_amount=request.usage_amount,
            unit_price=Decimal("0.01"),
            total_cost=Decimal("10"),
            currency=Currency.CREDIT,
            suggested_billing_method=BillingMethod.WALLET_DEDUCTION,
            available_billing_methods=[BillingMethod.WALLET_DEDUCTION]
        )

    service._record_usage_to_product_service = mock_record_usage
    service.calculate_billing_cost = mock_calculate_cost
    service.check_quota = mock_check_quota

    request = RecordUsageRequest(
        user_id="user123",
        organization_id="org456",
        product_id="prod_tokens",
        service_type=ServiceType.MODEL_INFERENCE,
        usage_amount=Decimal("1000"),
        subscription_id="sub_123"
    )

    result = await service.record_usage_and_bill(request)

    # Check result failed due to quota
    assert result.success is False, "Should fail due to quota exceeded"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.QUOTA_EXCEEDED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.BILLING_SERVICE.value, "Event source should be billing_service"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["requested_amount"] == 1000.0, "Event should contain requested_amount"
    assert event.data["quota_limit"] == 10000.0, "Event should contain quota_limit"

    print("✅ TEST PASSED: billing.quota.exceeded event published correctly")
    return True


async def test_billing_record_created_event():
    """Test that billing.record.created event is published"""
    print("\n📝 Testing billing.record.created event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockBillingRepository()

    service = BillingService(mock_repository, event_bus=mock_event_bus)

    # Create a mock calculation response with extra attributes
    class MockCalculation:
        user_id = "user123"
        organization_id = "org456"
        product_id = "prod_test"
        usage_amount = Decimal("100")
        unit_price = Decimal("0.5")
        total_cost = Decimal("50")
        currency = Currency.CREDIT
        is_free_tier = False
        is_included_in_subscription = False

    calculation = MockCalculation()

    # Create billing record
    billing_record = await service._create_billing_record(
        usage_record_id="usage_123",
        calculation=calculation,
        billing_method=BillingMethod.WALLET_DEDUCTION,
        status=BillingStatus.PROCESSING
    )

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.BILLING_RECORD_CREATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.BILLING_SERVICE.value, "Event source should be billing_service"
    assert event.data["billing_record_id"] == billing_record.billing_id, "Event should contain billing_record_id"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["total_amount"] == 50.0, "Event should contain total_amount"
    assert event.data["billing_method"] == "wallet_deduction", "Event should contain billing_method"

    print("✅ TEST PASSED: billing.record.created event published correctly")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("BILLING SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)

    tests = [
        ("Usage Recorded Event", test_usage_recorded_event),
        ("Billing Calculated Event", test_billing_calculated_event),
        ("Quota Exceeded Event", test_quota_exceeded_event),
        ("Billing Record Created Event", test_billing_record_created_event),
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
