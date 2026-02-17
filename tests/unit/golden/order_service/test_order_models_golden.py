"""
Order Service - Unit Tests (Golden)

Tests for:
- Data contract validation (Pydantic schemas)
- Test data factory methods
- Request builders
- Business rule validation
- Response contracts
- Edge cases
- Invalid data handling

All tests use OrderTestDataFactory - zero hardcoded data.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pydantic import ValidationError

from tests.contracts.order.data_contract import (
    # Enums
    OrderStatusContract,
    OrderTypeContract,
    PaymentStatusContract,
    # Request Contracts
    OrderCreateRequestContract,
    OrderUpdateRequestContract,
    OrderCancelRequestContract,
    OrderCompleteRequestContract,
    OrderListParamsContract,
    OrderSearchParamsContract,
    OrderFilterContract,
    OrderItemContract,
    # Response Contracts
    OrderContract,
    OrderResponseContract,
    OrderListResponseContract,
    OrderStatisticsResponseContract,
    # Factory
    OrderTestDataFactory,
    # Builders
    OrderCreateRequestBuilder,
    OrderUpdateRequestBuilder,
    OrderCancelRequestBuilder,
    OrderCompleteRequestBuilder,
)

pytestmark = [pytest.mark.unit]


# ============================================================================
# Test OrderTestDataFactory - ID Generators (10 tests)
# ============================================================================

class TestOrderTestDataFactoryIdGenerators:
    """Test factory ID generation methods"""

    def test_make_order_id_format(self):
        """Factory generates order ID with correct prefix"""
        order_id = OrderTestDataFactory.make_order_id()
        assert order_id.startswith("order_")
        assert len(order_id) > 6

    def test_make_order_id_uniqueness(self):
        """Factory generates unique order IDs"""
        ids = [OrderTestDataFactory.make_order_id() for _ in range(100)]
        assert len(ids) == len(set(ids))

    def test_make_user_id_format(self):
        """Factory generates user ID with correct prefix"""
        user_id = OrderTestDataFactory.make_user_id()
        assert user_id.startswith("user_")
        assert len(user_id) > 5

    def test_make_user_id_uniqueness(self):
        """Factory generates unique user IDs"""
        ids = [OrderTestDataFactory.make_user_id() for _ in range(100)]
        assert len(ids) == len(set(ids))

    def test_make_payment_intent_id_format(self):
        """Factory generates payment intent ID with correct prefix"""
        pi_id = OrderTestDataFactory.make_payment_intent_id()
        assert pi_id.startswith("pi_")
        assert len(pi_id) > 3

    def test_make_subscription_id_format(self):
        """Factory generates subscription ID with correct prefix"""
        sub_id = OrderTestDataFactory.make_subscription_id()
        assert sub_id.startswith("sub_")
        assert len(sub_id) > 4

    def test_make_wallet_id_format(self):
        """Factory generates wallet ID with correct prefix"""
        wallet_id = OrderTestDataFactory.make_wallet_id()
        assert wallet_id.startswith("wallet_")
        assert len(wallet_id) > 7

    def test_make_transaction_id_format(self):
        """Factory generates transaction ID with correct prefix"""
        txn_id = OrderTestDataFactory.make_transaction_id()
        assert txn_id.startswith("txn_")
        assert len(txn_id) > 4

    def test_make_product_id_format(self):
        """Factory generates product ID with correct prefix"""
        prod_id = OrderTestDataFactory.make_product_id()
        assert prod_id.startswith("prod_")
        assert len(prod_id) > 5

    def test_all_ids_are_strings(self):
        """All factory ID methods return strings"""
        assert isinstance(OrderTestDataFactory.make_order_id(), str)
        assert isinstance(OrderTestDataFactory.make_user_id(), str)
        assert isinstance(OrderTestDataFactory.make_payment_intent_id(), str)
        assert isinstance(OrderTestDataFactory.make_subscription_id(), str)
        assert isinstance(OrderTestDataFactory.make_wallet_id(), str)
        assert isinstance(OrderTestDataFactory.make_transaction_id(), str)
        assert isinstance(OrderTestDataFactory.make_product_id(), str)


# ============================================================================
# Test OrderTestDataFactory - Amount Generators (8 tests)
# ============================================================================

class TestOrderTestDataFactoryAmountGenerators:
    """Test factory amount generation methods"""

    def test_make_amount_positive(self):
        """Factory generates positive amounts"""
        for _ in range(10):
            amount = OrderTestDataFactory.make_amount()
            assert amount > 0

    def test_make_amount_decimal_type(self):
        """Factory generates Decimal amounts"""
        amount = OrderTestDataFactory.make_amount()
        assert isinstance(amount, Decimal)

    def test_make_amount_reasonable_range(self):
        """Factory generates amounts in reasonable range"""
        for _ in range(10):
            amount = OrderTestDataFactory.make_amount()
            assert Decimal("9.99") <= amount <= Decimal("999.99")

    def test_make_small_amount_range(self):
        """Factory generates small amounts correctly"""
        for _ in range(10):
            amount = OrderTestDataFactory.make_small_amount()
            assert Decimal("0.99") <= amount <= Decimal("9.99")

    def test_make_large_amount_range(self):
        """Factory generates large amounts correctly"""
        for _ in range(10):
            amount = OrderTestDataFactory.make_large_amount()
            assert Decimal("1000.00") <= amount <= Decimal("9999.99")

    def test_make_credit_amount_integer_like(self):
        """Factory generates integer-like credit amounts"""
        for _ in range(10):
            amount = OrderTestDataFactory.make_credit_amount()
            assert amount == amount.to_integral_value()
            assert 10 <= amount <= 1000

    def test_make_refund_amount_within_original(self):
        """Factory generates refund amounts within original"""
        original = Decimal("100.00")
        for _ in range(10):
            refund = OrderTestDataFactory.make_refund_amount(original)
            assert Decimal("0") < refund <= original

    def test_make_currency_valid(self):
        """Factory generates valid currency codes"""
        valid_currencies = {"USD", "EUR", "GBP", "CAD", "AUD"}
        for _ in range(20):
            currency = OrderTestDataFactory.make_currency()
            assert currency in valid_currencies


# ============================================================================
# Test OrderTestDataFactory - Timestamp Generators (5 tests)
# ============================================================================

class TestOrderTestDataFactoryTimestampGenerators:
    """Test factory timestamp generation methods"""

    def test_make_timestamp_is_datetime(self):
        """Factory generates datetime objects"""
        ts = OrderTestDataFactory.make_timestamp()
        assert isinstance(ts, datetime)

    def test_make_timestamp_has_timezone(self):
        """Factory generates timezone-aware timestamps"""
        ts = OrderTestDataFactory.make_timestamp()
        assert ts.tzinfo is not None

    def test_make_past_timestamp_is_past(self):
        """Factory generates past timestamps"""
        now = datetime.now(timezone.utc)
        past = OrderTestDataFactory.make_past_timestamp(days=7)
        assert past < now

    def test_make_future_timestamp_is_future(self):
        """Factory generates future timestamps"""
        now = datetime.now(timezone.utc)
        future = OrderTestDataFactory.make_future_timestamp(minutes=30)
        assert future > now

    def test_make_expiration_minutes_valid_range(self):
        """Factory generates valid expiration minutes"""
        for _ in range(10):
            minutes = OrderTestDataFactory.make_expiration_minutes()
            assert 15 <= minutes <= 60


# ============================================================================
# Test OrderTestDataFactory - Type Generators (6 tests)
# ============================================================================

class TestOrderTestDataFactoryTypeGenerators:
    """Test factory type generation methods"""

    def test_make_order_type_valid(self):
        """Factory generates valid order types"""
        for _ in range(20):
            order_type = OrderTestDataFactory.make_order_type()
            assert order_type in OrderTypeContract

    def test_make_purchase_type(self):
        """Factory generates purchase order type"""
        order_type = OrderTestDataFactory.make_purchase_type()
        assert order_type == OrderTypeContract.PURCHASE

    def test_make_subscription_type(self):
        """Factory generates subscription order type"""
        order_type = OrderTestDataFactory.make_subscription_type()
        assert order_type == OrderTypeContract.SUBSCRIPTION

    def test_make_credit_purchase_type(self):
        """Factory generates credit purchase order type"""
        order_type = OrderTestDataFactory.make_credit_purchase_type()
        assert order_type == OrderTypeContract.CREDIT_PURCHASE

    def test_make_order_status_valid(self):
        """Factory generates valid order statuses"""
        for _ in range(20):
            status = OrderTestDataFactory.make_order_status()
            assert status in OrderStatusContract

    def test_make_payment_status_valid(self):
        """Factory generates valid payment statuses"""
        for _ in range(20):
            status = OrderTestDataFactory.make_payment_status()
            assert status in PaymentStatusContract


# ============================================================================
# Test OrderTestDataFactory - Complex Objects (12 tests)
# ============================================================================

class TestOrderTestDataFactoryComplexObjects:
    """Test factory complex object generation methods"""

    def test_make_order_item_has_required_fields(self):
        """Factory generates order items with required fields"""
        item = OrderTestDataFactory.make_order_item()
        assert "product_id" in item
        assert "name" in item
        assert "quantity" in item
        assert "unit_price" in item
        assert "total_price" in item

    def test_make_order_item_quantity_positive(self):
        """Factory generates items with positive quantity"""
        item = OrderTestDataFactory.make_order_item()
        assert item["quantity"] >= 1

    def test_make_order_item_price_positive(self):
        """Factory generates items with positive price"""
        item = OrderTestDataFactory.make_order_item()
        assert item["unit_price"] > 0
        assert item["total_price"] > 0

    def test_make_order_items_returns_list(self):
        """Factory generates list of order items"""
        items = OrderTestDataFactory.make_order_items(count=3)
        assert isinstance(items, list)
        assert len(items) == 3

    def test_make_metadata_is_dict(self):
        """Factory generates metadata as dict"""
        metadata = OrderTestDataFactory.make_metadata()
        assert isinstance(metadata, dict)
        assert "source" in metadata

    def test_make_create_request_valid(self):
        """Factory generates valid create request"""
        request = OrderTestDataFactory.make_create_request()
        assert isinstance(request, OrderCreateRequestContract)
        assert request.user_id
        assert request.total_amount > 0

    def test_make_credit_purchase_request_has_wallet(self):
        """Factory generates credit purchase with wallet_id"""
        request = OrderTestDataFactory.make_credit_purchase_request()
        assert request.order_type == OrderTypeContract.CREDIT_PURCHASE
        assert request.wallet_id is not None

    def test_make_subscription_request_has_subscription_id(self):
        """Factory generates subscription with subscription_id"""
        request = OrderTestDataFactory.make_subscription_request()
        assert request.order_type == OrderTypeContract.SUBSCRIPTION
        assert request.subscription_id is not None

    def test_make_update_request_valid(self):
        """Factory generates valid update request"""
        request = OrderTestDataFactory.make_update_request()
        assert isinstance(request, OrderUpdateRequestContract)

    def test_make_cancel_request_has_reason(self):
        """Factory generates cancel request with reason"""
        request = OrderTestDataFactory.make_cancel_request()
        assert isinstance(request, OrderCancelRequestContract)
        assert request.reason is not None

    def test_make_complete_request_confirmed(self):
        """Factory generates complete request with confirmation"""
        request = OrderTestDataFactory.make_complete_request()
        assert isinstance(request, OrderCompleteRequestContract)
        assert request.payment_confirmed is True

    def test_make_order_valid(self):
        """Factory generates valid order object"""
        order = OrderTestDataFactory.make_order()
        assert isinstance(order, OrderContract)
        assert order.order_id
        assert order.user_id
        assert order.created_at


# ============================================================================
# Test OrderTestDataFactory - Invalid Data (10 tests)
# ============================================================================

class TestOrderTestDataFactoryInvalidData:
    """Test factory invalid data generation methods"""

    def test_make_invalid_order_id(self):
        """Factory generates invalid order ID"""
        invalid_id = OrderTestDataFactory.make_invalid_order_id()
        assert not invalid_id.startswith("order_") or len(invalid_id) < 10

    def test_make_invalid_user_id_empty(self):
        """Factory generates empty user ID"""
        invalid_id = OrderTestDataFactory.make_invalid_user_id()
        assert invalid_id == ""

    def test_make_empty_user_id_whitespace(self):
        """Factory generates whitespace user ID"""
        invalid_id = OrderTestDataFactory.make_empty_user_id()
        assert invalid_id.strip() == ""

    def test_make_invalid_amount_zero(self):
        """Factory generates zero amount"""
        amount = OrderTestDataFactory.make_invalid_amount()
        assert amount == Decimal("0")

    def test_make_negative_amount(self):
        """Factory generates negative amount"""
        amount = OrderTestDataFactory.make_negative_amount()
        assert amount < 0

    def test_make_invalid_currency(self):
        """Factory generates invalid currency"""
        currency = OrderTestDataFactory.make_invalid_currency()
        assert currency not in {"USD", "EUR", "GBP", "CAD", "AUD"}

    def test_make_invalid_order_type(self):
        """Factory generates invalid order type"""
        order_type = OrderTestDataFactory.make_invalid_order_type()
        assert order_type not in [t.value for t in OrderTypeContract]

    def test_make_invalid_create_request_missing_user(self):
        """Factory generates request missing user_id"""
        invalid_data = OrderTestDataFactory.make_invalid_create_request_missing_user()
        assert "user_id" not in invalid_data

    def test_make_invalid_create_request_zero_amount(self):
        """Factory generates request with zero amount"""
        invalid_data = OrderTestDataFactory.make_invalid_create_request_zero_amount()
        assert invalid_data["total_amount"] == 0

    def test_make_invalid_refund_amount_exceeds(self):
        """Factory generates refund exceeding original"""
        original = Decimal("100.00")
        invalid_refund = OrderTestDataFactory.make_invalid_refund_amount(original)
        assert invalid_refund > original


# ============================================================================
# Test Request Contract Validation (15 tests)
# ============================================================================

class TestOrderCreateRequestValidation:
    """Test OrderCreateRequestContract validation"""

    def test_valid_request_passes(self):
        """Valid request passes Pydantic validation"""
        request = OrderTestDataFactory.make_create_request()
        assert isinstance(request, OrderCreateRequestContract)

    def test_empty_user_id_fails(self):
        """Empty user_id raises ValidationError"""
        with pytest.raises(ValidationError):
            OrderCreateRequestContract(
                user_id="",
                order_type=OrderTypeContract.PURCHASE,
                total_amount=Decimal("99.99")
            )

    def test_whitespace_user_id_fails(self):
        """Whitespace user_id raises ValidationError"""
        with pytest.raises(ValidationError):
            OrderCreateRequestContract(
                user_id="   ",
                order_type=OrderTypeContract.PURCHASE,
                total_amount=Decimal("99.99")
            )

    def test_zero_amount_fails(self):
        """Zero amount raises ValidationError"""
        with pytest.raises(ValidationError):
            OrderCreateRequestContract(
                user_id=OrderTestDataFactory.make_user_id(),
                order_type=OrderTypeContract.PURCHASE,
                total_amount=Decimal("0")
            )

    def test_negative_amount_fails(self):
        """Negative amount raises ValidationError"""
        with pytest.raises(ValidationError):
            OrderCreateRequestContract(
                user_id=OrderTestDataFactory.make_user_id(),
                order_type=OrderTypeContract.PURCHASE,
                total_amount=Decimal("-10.00")
            )

    def test_invalid_currency_fails(self):
        """Invalid currency raises ValidationError"""
        with pytest.raises(ValidationError):
            OrderCreateRequestContract(
                user_id=OrderTestDataFactory.make_user_id(),
                order_type=OrderTypeContract.PURCHASE,
                total_amount=Decimal("99.99"),
                currency="INVALID"
            )

    def test_currency_normalized_to_uppercase(self):
        """Currency is normalized to uppercase"""
        request = OrderCreateRequestContract(
            user_id=OrderTestDataFactory.make_user_id(),
            order_type=OrderTypeContract.PURCHASE,
            total_amount=Decimal("99.99"),
            currency="usd"
        )
        assert request.currency == "USD"

    def test_default_currency_is_usd(self):
        """Default currency is USD"""
        request = OrderTestDataFactory.make_create_request()
        assert request.currency == "USD"

    def test_default_expiration_is_30(self):
        """Default expiration is 30 minutes"""
        request = OrderTestDataFactory.make_create_request()
        assert request.expires_in_minutes == 30


class TestOrderCancelRequestValidation:
    """Test OrderCancelRequestContract validation"""

    def test_valid_cancel_request(self):
        """Valid cancel request passes validation"""
        request = OrderTestDataFactory.make_cancel_request()
        assert isinstance(request, OrderCancelRequestContract)

    def test_empty_reason_becomes_none(self):
        """Empty reason string becomes None"""
        request = OrderCancelRequestContract(reason="   ")
        assert request.reason is None

    def test_negative_refund_fails(self):
        """Negative refund amount raises ValidationError"""
        with pytest.raises(ValidationError):
            OrderCancelRequestContract(refund_amount=Decimal("-10.00"))


class TestOrderCompleteRequestValidation:
    """Test OrderCompleteRequestContract validation"""

    def test_valid_complete_request(self):
        """Valid complete request passes validation"""
        request = OrderTestDataFactory.make_complete_request()
        assert isinstance(request, OrderCompleteRequestContract)
        assert request.payment_confirmed is True

    def test_negative_credits_fails(self):
        """Negative credits_added raises ValidationError"""
        with pytest.raises(ValidationError):
            OrderCompleteRequestContract(
                payment_confirmed=True,
                credits_added=Decimal("-100")
            )


class TestOrderSearchParamsValidation:
    """Test OrderSearchParamsContract validation"""

    def test_valid_search_params(self):
        """Valid search params pass validation"""
        params = OrderTestDataFactory.make_search_params()
        assert isinstance(params, OrderSearchParamsContract)

    def test_empty_query_fails(self):
        """Empty query raises ValidationError"""
        with pytest.raises(ValidationError):
            OrderSearchParamsContract(query="")

    def test_whitespace_query_fails(self):
        """Whitespace query raises ValidationError"""
        with pytest.raises(ValidationError):
            OrderSearchParamsContract(query="   ")


# ============================================================================
# Test Request Builders (15 tests)
# ============================================================================

class TestOrderCreateRequestBuilder:
    """Test OrderCreateRequestBuilder"""

    def test_builder_default_build(self):
        """Builder creates valid request with defaults"""
        request = OrderCreateRequestBuilder().build()
        assert isinstance(request, OrderCreateRequestContract)
        assert request.user_id
        assert request.total_amount > 0

    def test_builder_with_user_id(self):
        """Builder accepts custom user_id"""
        custom_id = "custom_user_123"
        request = OrderCreateRequestBuilder().with_user_id(custom_id).build()
        assert request.user_id == custom_id

    def test_builder_with_order_type(self):
        """Builder accepts custom order_type"""
        request = OrderCreateRequestBuilder() \
            .with_order_type(OrderTypeContract.SUBSCRIPTION) \
            .with_subscription_id(OrderTestDataFactory.make_subscription_id()) \
            .build()
        assert request.order_type == OrderTypeContract.SUBSCRIPTION

    def test_builder_with_amount(self):
        """Builder accepts custom amount"""
        amount = Decimal("199.99")
        request = OrderCreateRequestBuilder().with_total_amount(amount).build()
        assert request.total_amount == amount

    def test_builder_with_currency(self):
        """Builder accepts custom currency"""
        request = OrderCreateRequestBuilder().with_currency("EUR").build()
        assert request.currency == "EUR"

    def test_builder_as_credit_purchase(self):
        """Builder creates credit purchase with wallet_id"""
        request = OrderCreateRequestBuilder().as_credit_purchase().build()
        assert request.order_type == OrderTypeContract.CREDIT_PURCHASE
        assert request.wallet_id is not None

    def test_builder_as_subscription(self):
        """Builder creates subscription with subscription_id"""
        request = OrderCreateRequestBuilder().as_subscription().build()
        assert request.order_type == OrderTypeContract.SUBSCRIPTION
        assert request.subscription_id is not None

    def test_builder_chaining(self):
        """Builder supports method chaining"""
        request = (
            OrderCreateRequestBuilder()
            .with_user_id("chain_user")
            .with_total_amount(Decimal("50.00"))
            .with_currency("GBP")
            .with_expires_in_minutes(60)
            .build()
        )
        assert request.user_id == "chain_user"
        assert request.total_amount == Decimal("50.00")
        assert request.currency == "GBP"
        assert request.expires_in_minutes == 60


class TestOrderUpdateRequestBuilder:
    """Test OrderUpdateRequestBuilder"""

    def test_builder_default_build(self):
        """Builder creates valid empty update request"""
        request = OrderUpdateRequestBuilder().build()
        assert isinstance(request, OrderUpdateRequestContract)

    def test_builder_as_processing(self):
        """Builder creates processing status update"""
        request = OrderUpdateRequestBuilder().as_processing().build()
        assert request.status == OrderStatusContract.PROCESSING
        assert request.payment_status == PaymentStatusContract.PROCESSING

    def test_builder_as_completed(self):
        """Builder creates completed status update"""
        request = OrderUpdateRequestBuilder().as_completed().build()
        assert request.status == OrderStatusContract.COMPLETED
        assert request.payment_status == PaymentStatusContract.COMPLETED


class TestOrderCancelRequestBuilder:
    """Test OrderCancelRequestBuilder"""

    def test_builder_with_reason(self):
        """Builder accepts cancellation reason"""
        reason = "Customer changed mind"
        request = OrderCancelRequestBuilder().with_reason(reason).build()
        assert request.reason == reason

    def test_builder_with_full_refund(self):
        """Builder calculates full refund"""
        original = Decimal("100.00")
        request = OrderCancelRequestBuilder().with_full_refund(original).build()
        assert request.refund_amount == original

    def test_builder_with_partial_refund(self):
        """Builder calculates partial refund"""
        original = Decimal("100.00")
        request = OrderCancelRequestBuilder().with_partial_refund(original, 0.5).build()
        assert request.refund_amount == Decimal("50.00")


class TestOrderCompleteRequestBuilder:
    """Test OrderCompleteRequestBuilder"""

    def test_builder_with_payment_details(self):
        """Builder adds transaction ID"""
        request = OrderCompleteRequestBuilder().with_payment_details().build()
        assert request.transaction_id is not None

    def test_builder_for_credit_purchase(self):
        """Builder configures for credit purchase"""
        amount = Decimal("100.00")
        request = OrderCompleteRequestBuilder().for_credit_purchase(amount).build()
        assert request.credits_added == amount
        assert request.transaction_id is not None


# ============================================================================
# Test Response Contracts (8 tests)
# ============================================================================

class TestResponseContracts:
    """Test response contract models"""

    def test_order_response_success(self):
        """Order response with success"""
        response = OrderTestDataFactory.make_order_response(success=True)
        assert response.success is True
        assert response.order is not None
        assert response.error_code is None

    def test_order_response_failure(self):
        """Order response with failure"""
        response = OrderTestDataFactory.make_order_response(success=False)
        assert response.success is False
        assert response.order is None
        assert response.error_code is not None

    def test_order_list_response_structure(self):
        """Order list response has required fields"""
        orders = [OrderTestDataFactory.make_order() for _ in range(3)]
        response = OrderListResponseContract(
            orders=orders,
            total_count=3,
            page=1,
            page_size=50,
            has_next=False
        )
        assert len(response.orders) == 3
        assert response.total_count == 3

    def test_statistics_response_structure(self):
        """Statistics response has required fields"""
        stats = OrderTestDataFactory.make_statistics()
        assert stats.total_orders >= 0
        assert isinstance(stats.orders_by_status, dict)
        assert isinstance(stats.orders_by_type, dict)
        assert stats.total_revenue >= 0

    def test_completed_order_has_completed_at(self):
        """Completed order has completed_at timestamp"""
        order = OrderTestDataFactory.make_completed_order()
        assert order.status == OrderStatusContract.COMPLETED
        assert order.completed_at is not None

    def test_health_response_structure(self):
        """Health response has required fields"""
        health = OrderTestDataFactory.make_health_response()
        assert health.status == "healthy"
        assert health.service == "order_service"
        assert health.port == 8210

    def test_order_contract_serialization(self):
        """Order contract can be serialized to dict"""
        order = OrderTestDataFactory.make_order()
        data = order.model_dump()
        assert isinstance(data, dict)
        assert "order_id" in data
        assert "user_id" in data

    def test_order_contract_json_serialization(self):
        """Order contract can be serialized to JSON"""
        order = OrderTestDataFactory.make_order()
        json_str = order.model_dump_json()
        assert isinstance(json_str, str)
        assert order.order_id in json_str


# ============================================================================
# Test Business Rule Validation (10 tests)
# ============================================================================

class TestBusinessRuleValidation:
    """Test business rules from logic contract"""

    def test_br_ord_003_positive_amount(self):
        """BR-ORD-003: Positive amount required"""
        request = OrderTestDataFactory.make_create_request()
        assert request.total_amount > 0

    def test_br_ord_007_credit_purchase_requires_wallet(self):
        """BR-ORD-007: Credit purchase requires wallet_id"""
        request = OrderTestDataFactory.make_credit_purchase_request()
        assert request.wallet_id is not None

    def test_br_ord_008_subscription_requires_sub_id(self):
        """BR-ORD-008: Subscription requires subscription_id"""
        request = OrderTestDataFactory.make_subscription_request()
        assert request.subscription_id is not None

    def test_br_ord_009_initial_status_pending(self):
        """BR-ORD-009: Initial order status is pending"""
        order = OrderTestDataFactory.make_order()
        assert order.status == OrderStatusContract.PENDING

    def test_br_ord_010_expiration_default(self):
        """BR-ORD-010: Default expiration is 30 minutes"""
        request = OrderTestDataFactory.make_create_request()
        assert request.expires_in_minutes == 30

    def test_br_ord_031_completion_requires_confirmation(self):
        """BR-ORD-031: Completion requires payment_confirmed=true"""
        request = OrderTestDataFactory.make_complete_request()
        assert request.payment_confirmed is True

    def test_br_ord_039_pagination_max_100(self):
        """BR-ORD-039: Pagination max is 100"""
        params = OrderListParamsContract(page_size=100)
        assert params.page_size == 100
        
        with pytest.raises(ValidationError):
            OrderListParamsContract(page_size=101)

    def test_br_ord_041_search_query_not_empty(self):
        """BR-ORD-041: Search query cannot be empty"""
        with pytest.raises(ValidationError):
            OrderSearchParamsContract(query="")

    def test_br_ord_025_refund_within_total(self):
        """BR-ORD-025: Refund should be within total"""
        original = Decimal("100.00")
        refund = OrderTestDataFactory.make_refund_amount(original)
        assert refund <= original

    def test_all_status_values_valid(self):
        """All order statuses are valid enum values"""
        valid_statuses = [s.value for s in OrderStatusContract]
        assert "pending" in valid_statuses
        assert "processing" in valid_statuses
        assert "completed" in valid_statuses
        assert "failed" in valid_statuses
        assert "cancelled" in valid_statuses
        assert "refunded" in valid_statuses
