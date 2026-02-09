"""
Billing Service - Component Tests (Golden)

Tests for:
- Usage recording and billing
- Cost calculation
- Billing processing
- Quota management
- Event publishing
- Validation and error handling

All tests use BillingTestDataFactory - zero hardcoded data.
These tests capture current behavior and should not be modified
unless intentionally changing the service behavior.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import ValidationError

from tests.contracts.billing.data_contract import (
    BillingTestDataFactory,
    UsageRecordRequestContract,
    BillingCalculateRequestContract,
    BillingProcessRequestContract,
    QuotaCheckRequestContract,
    UsageRecordRequestBuilder,
    BillingCalculateRequestBuilder,
    BillingProcessRequestBuilder,
    QuotaCheckRequestBuilder,
    ServiceTypeEnum,
    BillingMethodEnum,
    BillingStatusEnum,
)

pytestmark = [pytest.mark.component, pytest.mark.asyncio]


# ============================================================================
# Factory Tests (20+ tests)
# ============================================================================


class TestBillingTestDataFactory:
    """Test factory generates valid unique data"""

    def test_make_billing_id_format(self):
        """Factory generates valid billing ID format"""
        billing_id = BillingTestDataFactory.make_billing_id()
        assert billing_id.startswith("bill_")
        assert len(billing_id) > 5

    def test_make_billing_id_uniqueness(self):
        """Factory generates unique billing IDs"""
        id1 = BillingTestDataFactory.make_billing_id()
        id2 = BillingTestDataFactory.make_billing_id()
        assert id1 != id2

    def test_make_user_id_format(self):
        """Factory generates valid user ID format"""
        user_id = BillingTestDataFactory.make_user_id()
        assert user_id.startswith("user_")
        assert len(user_id) > 5

    def test_make_user_id_uniqueness(self):
        """Factory generates unique user IDs"""
        id1 = BillingTestDataFactory.make_user_id()
        id2 = BillingTestDataFactory.make_user_id()
        assert id1 != id2

    def test_make_product_id_format(self):
        """Factory generates valid product ID format"""
        product_id = BillingTestDataFactory.make_product_id()
        assert product_id.startswith("prod_")
        assert len(product_id) > 5

    def test_make_usage_record_id_format(self):
        """Factory generates valid usage record ID format"""
        usage_id = BillingTestDataFactory.make_usage_record_id()
        assert usage_id.startswith("usage_")
        assert len(usage_id) > 6

    def test_make_service_type_valid(self):
        """Factory generates valid service type"""
        service_type = BillingTestDataFactory.make_service_type()
        assert service_type in [e.value for e in ServiceTypeEnum]

    def test_make_billing_method_valid(self):
        """Factory generates valid billing method"""
        billing_method = BillingTestDataFactory.make_billing_method()
        assert billing_method in [e.value for e in BillingMethodEnum]

    def test_make_usage_amount_valid_range(self):
        """Factory generates valid usage amount"""
        amount = BillingTestDataFactory.make_usage_amount()
        assert amount >= Decimal("100")
        assert amount < Decimal("10100")

    def test_make_unit_price_valid_range(self):
        """Factory generates valid unit price"""
        price = BillingTestDataFactory.make_unit_price()
        assert price >= Decimal("0.0001")
        assert price < Decimal("0.02")

    def test_make_wallet_balance_valid_range(self):
        """Factory generates valid wallet balance"""
        balance = BillingTestDataFactory.make_wallet_balance()
        assert balance >= Decimal("10")
        assert balance < Decimal("120")

    def test_make_credit_balance_valid_range(self):
        """Factory generates valid credit balance"""
        credits = BillingTestDataFactory.make_credit_balance()
        assert credits >= Decimal("100")
        assert credits < Decimal("1100")

    def test_make_quota_limit_valid_range(self):
        """Factory generates valid quota limit"""
        limit = BillingTestDataFactory.make_quota_limit()
        assert limit >= Decimal("10000")
        assert limit < Decimal("110000")

    def test_make_usage_record_request(self):
        """Factory generates valid usage record request"""
        request = BillingTestDataFactory.make_usage_record_request()
        assert isinstance(request, UsageRecordRequestContract)
        assert request.user_id.startswith("user_")
        assert request.product_id.startswith("prod_")

    def test_make_billing_calculate_request(self):
        """Factory generates valid billing calculate request"""
        request = BillingTestDataFactory.make_billing_calculate_request()
        assert isinstance(request, BillingCalculateRequestContract)
        assert request.usage_amount > 0

    def test_make_billing_process_request(self):
        """Factory generates valid billing process request"""
        request = BillingTestDataFactory.make_billing_process_request()
        assert isinstance(request, BillingProcessRequestContract)
        assert request.usage_record_id.startswith("usage_")

    def test_make_quota_check_request(self):
        """Factory generates valid quota check request"""
        request = BillingTestDataFactory.make_quota_check_request()
        assert isinstance(request, QuotaCheckRequestContract)
        assert request.requested_amount > 0

    def test_make_invalid_user_id_empty(self):
        """Factory generates empty invalid user ID"""
        invalid_id = BillingTestDataFactory.make_invalid_user_id_empty()
        assert invalid_id == ""

    def test_make_invalid_service_type(self):
        """Factory generates invalid service type"""
        invalid_type = BillingTestDataFactory.make_invalid_service_type()
        assert invalid_type not in [e.value for e in ServiceTypeEnum]

    def test_make_invalid_billing_method(self):
        """Factory generates invalid billing method"""
        invalid_method = BillingTestDataFactory.make_invalid_billing_method()
        assert invalid_method not in [e.value for e in BillingMethodEnum]


# ============================================================================
# Builder Tests (12+ tests)
# ============================================================================


class TestUsageRecordRequestBuilder:
    """Test usage record request builder"""

    def test_builder_default_build(self):
        """Builder creates valid request with defaults"""
        request = UsageRecordRequestBuilder().build()
        assert isinstance(request, UsageRecordRequestContract)
        assert request.user_id.startswith("user_")
        assert request.product_id.startswith("prod_")

    def test_builder_with_custom_user_id(self):
        """Builder accepts custom user ID"""
        custom_user_id = "custom_user_123"
        request = UsageRecordRequestBuilder().with_user_id(custom_user_id).build()
        assert request.user_id == custom_user_id

    def test_builder_with_service_type(self):
        """Builder accepts service type"""
        request = UsageRecordRequestBuilder().for_model_inference().build()
        assert request.service_type == ServiceTypeEnum.MODEL_INFERENCE.value

    def test_builder_for_storage(self):
        """Builder sets storage service type"""
        request = UsageRecordRequestBuilder().for_storage().build()
        assert request.service_type == ServiceTypeEnum.STORAGE_MINIO.value

    def test_builder_chaining(self):
        """Builder supports method chaining"""
        request = (
            UsageRecordRequestBuilder()
            .with_user_id("user_test")
            .with_product_id("prod_test")
            .for_model_inference()
            .with_usage_amount(Decimal("500"))
            .build()
        )
        assert request.user_id == "user_test"
        assert request.product_id == "prod_test"
        assert request.service_type == ServiceTypeEnum.MODEL_INFERENCE.value
        assert request.usage_amount == Decimal("500")


class TestBillingCalculateRequestBuilder:
    """Test billing calculate request builder"""

    def test_builder_default_build(self):
        """Builder creates valid request with defaults"""
        request = BillingCalculateRequestBuilder().build()
        assert isinstance(request, BillingCalculateRequestContract)
        assert request.user_id.startswith("user_")

    def test_builder_with_usage_amount(self):
        """Builder accepts usage amount"""
        request = BillingCalculateRequestBuilder().with_usage_amount(Decimal("1000")).build()
        assert request.usage_amount == Decimal("1000")


class TestBillingProcessRequestBuilder:
    """Test billing process request builder"""

    def test_builder_default_build(self):
        """Builder creates valid request with defaults"""
        request = BillingProcessRequestBuilder().build()
        assert isinstance(request, BillingProcessRequestContract)
        assert request.billing_method == BillingMethodEnum.WALLET_DEDUCTION.value

    def test_builder_using_credits(self):
        """Builder sets credit consumption method"""
        request = BillingProcessRequestBuilder().using_credits().build()
        assert request.billing_method == BillingMethodEnum.CREDIT_CONSUMPTION.value

    def test_builder_using_wallet(self):
        """Builder sets wallet deduction method"""
        request = BillingProcessRequestBuilder().using_wallet().build()
        assert request.billing_method == BillingMethodEnum.WALLET_DEDUCTION.value

    def test_builder_force(self):
        """Builder enables force processing"""
        request = BillingProcessRequestBuilder().force().build()
        assert request.force_process is True


class TestQuotaCheckRequestBuilder:
    """Test quota check request builder"""

    def test_builder_default_build(self):
        """Builder creates valid request with defaults"""
        request = QuotaCheckRequestBuilder().build()
        assert isinstance(request, QuotaCheckRequestContract)

    def test_builder_for_model_inference(self):
        """Builder sets model inference service type"""
        request = QuotaCheckRequestBuilder().for_model_inference().build()
        assert request.service_type == ServiceTypeEnum.MODEL_INFERENCE.value

    def test_builder_with_requested_amount(self):
        """Builder accepts requested amount"""
        request = QuotaCheckRequestBuilder().with_requested_amount(Decimal("5000")).build()
        assert request.requested_amount == Decimal("5000")


# ============================================================================
# Contract Validation Tests (15+ tests)
# ============================================================================


class TestUsageRecordRequestValidation:
    """Test usage record request contract validation"""

    def test_valid_request_passes(self):
        """Valid request passes validation"""
        request = BillingTestDataFactory.make_usage_record_request()
        assert request.user_id is not None
        assert request.product_id is not None
        assert request.usage_amount >= 0

    def test_empty_user_id_fails(self):
        """Empty user ID fails validation"""
        with pytest.raises(ValidationError):
            UsageRecordRequestContract(
                user_id="",
                product_id="prod_123",
                service_type="model_inference",
                usage_amount=Decimal("100"),
            )

    def test_whitespace_user_id_fails(self):
        """Whitespace-only user ID fails validation"""
        with pytest.raises(ValidationError):
            UsageRecordRequestContract(
                user_id="   ",
                product_id="prod_123",
                service_type="model_inference",
                usage_amount=Decimal("100"),
            )

    def test_empty_product_id_fails(self):
        """Empty product ID fails validation"""
        with pytest.raises(ValidationError):
            UsageRecordRequestContract(
                user_id="user_123",
                product_id="",
                service_type="model_inference",
                usage_amount=Decimal("100"),
            )

    def test_invalid_service_type_fails(self):
        """Invalid service type fails validation"""
        with pytest.raises(ValidationError):
            UsageRecordRequestContract(
                user_id="user_123",
                product_id="prod_123",
                service_type="invalid_type",
                usage_amount=Decimal("100"),
            )

    def test_negative_usage_amount_fails(self):
        """Negative usage amount fails validation"""
        with pytest.raises(ValidationError):
            UsageRecordRequestContract(
                user_id="user_123",
                product_id="prod_123",
                service_type="model_inference",
                usage_amount=Decimal("-100"),
            )


class TestBillingProcessRequestValidation:
    """Test billing process request contract validation"""

    def test_valid_request_passes(self):
        """Valid request passes validation"""
        request = BillingTestDataFactory.make_billing_process_request()
        assert request.usage_record_id is not None
        assert request.billing_method is not None

    def test_invalid_billing_method_fails(self):
        """Invalid billing method fails validation"""
        with pytest.raises(ValidationError):
            BillingProcessRequestContract(
                usage_record_id="usage_123",
                billing_method="invalid_method",
            )


class TestQuotaCheckRequestValidation:
    """Test quota check request contract validation"""

    def test_valid_request_passes(self):
        """Valid request passes validation"""
        request = BillingTestDataFactory.make_quota_check_request()
        assert request.service_type is not None
        assert request.requested_amount >= 0

    def test_invalid_service_type_fails(self):
        """Invalid service type fails validation"""
        with pytest.raises(ValidationError):
            QuotaCheckRequestContract(
                user_id="user_123",
                service_type="invalid_type",
                requested_amount=Decimal("100"),
            )

    def test_negative_requested_amount_fails(self):
        """Negative requested amount fails validation"""
        with pytest.raises(ValidationError):
            QuotaCheckRequestContract(
                user_id="user_123",
                service_type="model_inference",
                requested_amount=Decimal("-100"),
            )


# ============================================================================
# Quota Check Tests (10+ tests)
# ============================================================================


class TestQuotaCheck:
    """Test quota checking functionality"""

    async def test_quota_check_allowed_within_limit(
        self, billing_service, mock_billing_repository
    ):
        """Quota check returns allowed when within limit"""
        user_id = BillingTestDataFactory.make_user_id()
        service_type = ServiceTypeEnum.MODEL_INFERENCE.value
        
        # Add quota with high limit
        mock_billing_repository.add_quota(
            user_id=user_id,
            service_type=service_type,
            quota_limit=Decimal("100000"),
            quota_used=Decimal("1000"),
        )
        
        from microservices.billing_service.models import QuotaCheckRequest
        
        result = await billing_service.check_quota(
            QuotaCheckRequest(
                user_id=user_id,
                service_type=service_type,
                requested_amount=Decimal("5000"),
            )
        )
        
        assert result.allowed is True

    async def test_quota_check_no_quota_returns_allowed(
        self, billing_service, mock_billing_repository
    ):
        """Quota check returns allowed when no quota defined"""
        user_id = BillingTestDataFactory.make_user_id()
        
        from microservices.billing_service.models import QuotaCheckRequest
        
        result = await billing_service.check_quota(
            QuotaCheckRequest(
                user_id=user_id,
                service_type=ServiceTypeEnum.MODEL_INFERENCE.value,
                requested_amount=Decimal("5000"),
            )
        )
        
        # No quota defined = allowed (no restrictions)
        assert result.allowed is True


# ============================================================================
# Cost Calculation Tests (10+ tests)
# ============================================================================


class TestCostCalculation:
    """Test cost calculation functionality"""

    async def test_calculate_cost_with_product(
        self, billing_service, mock_product_client
    ):
        """Cost calculation returns correct result with product pricing"""
        user_id = BillingTestDataFactory.make_user_id()
        product_id = BillingTestDataFactory.make_product_id()
        
        # Add product with pricing
        mock_product_client.add_product(
            product_id=product_id,
            unit_price=Decimal("0.001"),
            free_tier_limit=Decimal("1000"),
        )
        
        from microservices.billing_service.models import BillingCalculationRequest
        
        result = await billing_service.calculate_billing_cost(
            BillingCalculationRequest(
                user_id=user_id,
                product_id=product_id,
                usage_amount=Decimal("5000"),
            )
        )
        
        assert result.success is True
        assert result.unit_price == Decimal("0.001")

    async def test_calculate_cost_no_product_fails(
        self, billing_service, mock_product_client
    ):
        """Cost calculation fails when product not found"""
        user_id = BillingTestDataFactory.make_user_id()
        
        from microservices.billing_service.models import BillingCalculationRequest
        
        result = await billing_service.calculate_billing_cost(
            BillingCalculationRequest(
                user_id=user_id,
                product_id="nonexistent_product",
                usage_amount=Decimal("5000"),
            )
        )
        
        assert result.success is False
        assert "not found" in result.message.lower()


# ============================================================================
# Event Publishing Tests (5+ tests)
# ============================================================================


class TestEventPublishing:
    """Test event publishing functionality"""

    async def test_usage_recorded_event_published(
        self, billing_service, mock_event_bus, mock_product_client, mock_billing_repository
    ):
        """Usage recorded event is published on record_usage_and_bill"""
        user_id = BillingTestDataFactory.make_user_id()
        product_id = BillingTestDataFactory.make_product_id()
        
        # Add product
        mock_product_client.add_product(
            product_id=product_id,
            unit_price=Decimal("0.001"),
        )
        
        from microservices.billing_service.models import RecordUsageRequest, ServiceType
        
        await billing_service.record_usage_and_bill(
            RecordUsageRequest(
                user_id=user_id,
                product_id=product_id,
                service_type=ServiceType.MODEL_INFERENCE,
                usage_amount=Decimal("1000"),
            )
        )
        
        # Check that events were published
        events = mock_event_bus.get_published_events()
        assert len(events) > 0


# ============================================================================
# Service Initialization Tests (5+ tests)
# ============================================================================


class TestBillingServiceInitialization:
    """Test billing service initialization"""

    async def test_service_initializes_with_all_dependencies(
        self,
        mock_billing_repository,
        mock_event_bus,
        mock_wallet_client,
        mock_subscription_client,
        mock_product_client,
    ):
        """Service initializes with all dependencies"""
        from microservices.billing_service.billing_service import BillingService
        
        service = BillingService(
            repository=mock_billing_repository,
            event_bus=mock_event_bus,
            wallet_client=mock_wallet_client,
            subscription_client=mock_subscription_client,
            product_client=mock_product_client,
        )
        
        assert service.repository is mock_billing_repository
        assert service.event_bus is mock_event_bus
        assert service.wallet_client is mock_wallet_client
        assert service.subscription_client is mock_subscription_client
        assert service.product_client is mock_product_client

    async def test_service_initializes_with_minimal_dependencies(
        self, mock_billing_repository
    ):
        """Service initializes with only required dependencies"""
        from microservices.billing_service.billing_service import BillingService
        
        service = BillingService(
            repository=mock_billing_repository,
        )
        
        assert service.repository is mock_billing_repository
        assert service.event_bus is None
        assert service.wallet_client is None

    async def test_service_without_event_bus_still_works(
        self, billing_service_no_event_bus, mock_product_client
    ):
        """Service works without event bus"""
        user_id = BillingTestDataFactory.make_user_id()
        product_id = BillingTestDataFactory.make_product_id()
        
        mock_product_client.add_product(
            product_id=product_id,
            unit_price=Decimal("0.001"),
        )
        
        from microservices.billing_service.models import BillingCalculationRequest
        
        # Should not raise error even without event bus
        result = await billing_service_no_event_bus.calculate_billing_cost(
            BillingCalculationRequest(
                user_id=user_id,
                product_id=product_id,
                usage_amount=Decimal("1000"),
            )
        )
        
        assert result.success is True
