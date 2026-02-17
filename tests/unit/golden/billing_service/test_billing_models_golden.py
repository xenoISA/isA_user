"""
Billing Models Golden Tests

🔒 GOLDEN: These tests document CURRENT behavior of billing models.
   DO NOT MODIFY unless behavior intentionally changes.

Purpose:
- Protect against accidental regressions
- Document what code currently does
- All tests should PASS (they describe existing behavior)

Usage:
    pytest tests/unit/golden -v
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pydantic import ValidationError

from microservices.billing_service.models import (
    BillingStatus,
    BillingMethod, 
    ServiceType,
    Currency,
    BillingRecord,
    BillingEvent,
    UsageAggregation,
    BillingQuota,
    RecordUsageRequest,
    BillingCalculationRequest,
    BillingCalculationResponse,
    ProcessBillingRequest,
    ProcessBillingResponse,
    UsageStatsRequest,
    UsageStatsResponse,
    QuotaCheckRequest,
    QuotaCheckResponse,
    HealthResponse,
    ServiceInfo,
    BillingStats,
)

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# =============================================================================
# Enum Tests - Current Behavior
# =============================================================================

class TestBillingStatusEnum:
    """Characterization: BillingStatus enum current behavior"""

    def test_all_billing_statuses_defined(self):
        """CHAR: All expected billing statuses are defined"""
        expected_statuses = {
            "pending", "processing", "completed", "failed", "refunded"
        }
        actual_statuses = {bs.value for bs in BillingStatus}
        assert actual_statuses == expected_statuses

    def test_billing_status_values(self):
        """CHAR: Billing status values are correct"""
        assert BillingStatus.PENDING.value == "pending"
        assert BillingStatus.COMPLETED.value == "completed"
        assert BillingStatus.FAILED.value == "failed"


class TestBillingMethodEnum:
    """Characterization: BillingMethod enum current behavior"""

    def test_all_billing_methods_defined(self):
        """CHAR: All expected billing methods are defined"""
        expected_methods = {
            "wallet_deduction", "payment_charge", "credit_consumption", "subscription_included"
        }
        actual_methods = {bm.value for bm in BillingMethod}
        assert actual_methods == expected_methods

    def test_billing_method_values(self):
        """CHAR: Billing method values are correct"""
        assert BillingMethod.WALLET_DEDUCTION.value == "wallet_deduction"
        assert BillingMethod.CREDIT_CONSUMPTION.value == "credit_consumption"


class TestServiceTypeEnum:
    """Characterization: ServiceType enum current behavior"""

    def test_all_service_types_defined(self):
        """CHAR: All expected service types are defined"""
        expected_types = {
            "model_inference", "mcp_service", "agent_execution",
            "storage_minio", "api_gateway", "notification", "other"
        }
        actual_types = {st.value for st in ServiceType}
        assert actual_types == expected_types


class TestCurrencyEnum:
    """Characterization: Currency enum current behavior"""

    def test_all_currencies_defined(self):
        """CHAR: All expected currencies are defined"""
        expected_currencies = {"USD", "CNY", "CREDIT"}
        actual_currencies = {c.value for c in Currency}
        assert actual_currencies == expected_currencies

    def test_currency_values(self):
        """CHAR: Currency values are correct"""
        assert Currency.USD.value == "USD"
        assert Currency.CREDIT.value == "CREDIT"


# =============================================================================
# BillingRecord - Current Behavior
# =============================================================================

class TestBillingRecordChar:
    """Characterization: BillingRecord current behavior"""

    def test_accepts_minimal_billing_record(self):
        """CHAR: Minimal billing record is accepted"""
        record = BillingRecord(
            billing_id="bill_123",
            user_id="user_123",
            usage_record_id="usage_123",
            product_id="gpt-4",
            service_type=ServiceType.MODEL_INFERENCE,
            usage_amount=Decimal("100"),
            unit_price=Decimal("0.03"),
            total_amount=Decimal("3.00"),
            billing_method=BillingMethod.WALLET_DEDUCTION,
            billing_status=BillingStatus.PENDING,
            currency=Currency.CREDIT
        )
        assert record.billing_id == "bill_123"
        assert record.user_id == "user_123"
        assert record.currency == Currency.CREDIT
        assert record.billing_metadata == {}  # Default

    def test_accepts_full_billing_record(self):
        """CHAR: Full billing record with all fields is accepted"""
        now = datetime.now(timezone.utc)
        record = BillingRecord(
            billing_id="bill_full_123",
            user_id="user_123",
            organization_id="org_123",
            usage_record_id="usage_123",
            product_id="gpt-4",
            service_type=ServiceType.MODEL_INFERENCE,
            usage_amount=Decimal("1000"),
            unit_price=Decimal("0.025"),
            total_amount=Decimal("25.00"),
            currency=Currency.USD,
            billing_method=BillingMethod.PAYMENT_CHARGE,
            billing_status=BillingStatus.COMPLETED,
            processed_at=now,
            wallet_transaction_id="wallet_tx_123",
            billing_metadata={"session_id": "sess_123"},
            billing_period_start=now - timedelta(days=30),
            billing_period_end=now,
            created_at=now,
            updated_at=now
        )
        assert record.organization_id == "org_123"
        assert record.wallet_transaction_id == "wallet_tx_123"
        assert record.billing_metadata["session_id"] == "sess_123"

    def test_decimal_fields_accept_decimal_values(self):
        """CHAR: Decimal fields accept Decimal values"""
        record = BillingRecord(
            billing_id="bill_123",
            user_id="user_123",
            usage_record_id="usage_123",
            product_id="gpt-4",
            service_type=ServiceType.MODEL_INFERENCE,
            usage_amount=Decimal("100.5"),
            unit_price=Decimal("0.033"),
            total_amount=Decimal("3.3165"),
            billing_method=BillingMethod.WALLET_DEDUCTION,
            billing_status=BillingStatus.PENDING,
            currency=Currency.CREDIT
        )
        assert record.usage_amount == Decimal("100.5")
        assert record.total_amount == Decimal("3.3165")

    def test_optional_fields_default_to_none(self):
        """CHAR: Optional fields default to None"""
        record = BillingRecord(
            billing_id="bill_123",
            user_id="user_123",
            usage_record_id="usage_123",
            product_id="gpt-4",
            service_type=ServiceType.MODEL_INFERENCE,
            usage_amount=Decimal("100"),
            unit_price=Decimal("0.03"),
            total_amount=Decimal("3.00"),
            billing_method=BillingMethod.WALLET_DEDUCTION,
            billing_status=BillingStatus.PENDING,
            currency=Currency.CREDIT
        )
        assert record.organization_id is None
        assert record.processed_at is None
        assert record.failure_reason is None
        assert record.wallet_transaction_id is None


# =============================================================================
# RecordUsageRequest - Current Behavior
# =============================================================================

class TestRecordUsageRequestChar:
    """Characterization: RecordUsageRequest current behavior"""

    def test_accepts_minimal_usage_request(self):
        """CHAR: Minimal usage request is accepted"""
        request = RecordUsageRequest(
            user_id="user_123",
            product_id="gpt-4",
            service_type=ServiceType.MODEL_INFERENCE,
            usage_amount=Decimal("100")
        )
        assert request.user_id == "user_123"
        assert request.product_id == "gpt-4"
        assert request.usage_amount == Decimal("100")
        assert request.organization_id is None  # Default
        assert request.usage_details is None  # Default

    def test_accepts_full_usage_request(self):
        """CHAR: Full usage request with all fields is accepted"""
        now = datetime.now(timezone.utc)
        request = RecordUsageRequest(
            user_id="user_123",
            organization_id="org_123",
            subscription_id="sub_123",
            product_id="gpt-4",
            service_type=ServiceType.MCP_SERVICE,
            usage_amount=Decimal("50"),
            session_id="sess_123",
            request_id="req_123",
            usage_details={"model": "gpt-4", "tokens": 1000},
            usage_timestamp=now
        )
        assert request.organization_id == "org_123"
        assert request.session_id == "sess_123"
        assert request.usage_details["model"] == "gpt-4"

    def test_usage_amount_must_be_non_negative(self):
        """CHAR: usage_amount must be >= 0"""
        # Valid zero amount
        request_zero = RecordUsageRequest(
            user_id="user_123",
            product_id="gpt-4",
            service_type=ServiceType.MODEL_INFERENCE,
            usage_amount=Decimal("0")
        )
        assert request_zero.usage_amount == Decimal("0")

        # Valid positive amount
        request_positive = RecordUsageRequest(
            user_id="user_123",
            product_id="gpt-4",
            service_type=ServiceType.MODEL_INFERENCE,
            usage_amount=Decimal("100")
        )
        assert request_positive.usage_amount == Decimal("100")

        # Negative amount should raise ValidationError if validated
        with pytest.raises(ValidationError):
            RecordUsageRequest(
                user_id="user_123",
                product_id="gpt-4",
                service_type=ServiceType.MODEL_INFERENCE,
                usage_amount=Decimal("-10")
            )


# =============================================================================
# BillingCalculationRequest - Current Behavior
# =============================================================================

class TestBillingCalculationRequestChar:
    """Characterization: BillingCalculationRequest current behavior"""

    def test_accepts_calculation_request(self):
        """CHAR: Valid calculation request is accepted"""
        request = BillingCalculationRequest(
            user_id="user_123",
            organization_id="org_123",
            subscription_id="sub_123",
            product_id="gpt-4",
            usage_amount=Decimal("1000")
        )
        assert request.user_id == "user_123"
        assert request.product_id == "gpt-4"
        assert request.usage_amount == Decimal("1000")

    def test_optional_fields_can_be_none(self):
        """CHAR: Optional fields can be None"""
        request = BillingCalculationRequest(
            user_id="user_123",
            product_id="gpt-4",
            usage_amount=Decimal("100")
        )
        assert request.organization_id is None
        assert request.subscription_id is None

    def test_usage_amount_must_be_non_negative(self):
        """CHAR: usage_amount must be >= 0"""
        with pytest.raises(ValidationError):
            BillingCalculationRequest(
                user_id="user_123",
                product_id="gpt-4",
                usage_amount=Decimal("-1")
            )


# =============================================================================
# BillingCalculationResponse - Current Behavior
# =============================================================================

class TestBillingCalculationResponseChar:
    """Characterization: BillingCalculationResponse current behavior"""

    def test_accepts_calculation_response(self):
        """CHAR: Valid calculation response is accepted"""
        response = BillingCalculationResponse(
            success=True,
            message="Calculation successful",
            user_id="user_123",
            product_id="gpt-4",
            usage_amount=Decimal("1000"),
            unit_price=Decimal("0.025"),
            total_cost=Decimal("25.00"),
            currency=Currency.CREDIT,
            is_free_tier=False,
            is_included_in_subscription=False,
            suggested_billing_method=BillingMethod.WALLET_DEDUCTION,
            available_billing_methods=[BillingMethod.WALLET_DEDUCTION, BillingMethod.CREDIT_CONSUMPTION]
        )
        assert response.success is True
        assert response.product_id == "gpt-4"
        assert response.total_cost == Decimal("25.00")
        assert response.suggested_billing_method == BillingMethod.WALLET_DEDUCTION

    def test_response_with_free_tier(self):
        """CHAR: Response with free tier information"""
        response = BillingCalculationResponse(
            success=True,
            message="Within free tier",
            user_id="user_123",
            product_id="gpt-4",
            usage_amount=Decimal("100"),
            unit_price=Decimal("0"),
            total_cost=Decimal("0"),
            currency=Currency.CREDIT,
            is_free_tier=True,
            free_tier_remaining=Decimal("900"),
            suggested_billing_method=BillingMethod.WALLET_DEDUCTION,
            available_billing_methods=[BillingMethod.WALLET_DEDUCTION]
        )
        assert response.is_free_tier is True
        assert response.free_tier_remaining == Decimal("900")

    def test_optional_balance_fields(self):
        """CHAR: Balance fields are optional"""
        response = BillingCalculationResponse(
            success=True,
            message="Calculation successful",
            user_id="user_123",
            product_id="gpt-4",
            usage_amount=Decimal("100"),
            unit_price=Decimal("0.03"),
            total_cost=Decimal("3.00"),
            currency=Currency.CREDIT,
            suggested_billing_method=BillingMethod.WALLET_DEDUCTION,
            available_billing_methods=[BillingMethod.WALLET_DEDUCTION]
        )
        assert response.wallet_balance is None
        assert response.credit_balance is None

        # With balance info
        response_with_balance = BillingCalculationResponse(
            success=True,
            message="Calculation successful",
            user_id="user_123",
            product_id="gpt-4",
            usage_amount=Decimal("100"),
            unit_price=Decimal("0.03"),
            total_cost=Decimal("3.00"),
            currency=Currency.CREDIT,
            wallet_balance=Decimal("100.00"),
            credit_balance=Decimal("1000"),
            suggested_billing_method=BillingMethod.WALLET_DEDUCTION,
            available_billing_methods=[BillingMethod.WALLET_DEDUCTION]
        )
        assert response_with_balance.wallet_balance == Decimal("100.00")
        assert response_with_balance.credit_balance == Decimal("1000")


# =============================================================================
# BillingQuota - Current Behavior
# =============================================================================

class TestBillingQuotaChar:
    """Characterization: BillingQuota current behavior"""

    def test_accepts_quota_record(self):
        """CHAR: Valid quota record is accepted"""
        now = datetime.now(timezone.utc)
        reset_date = now + timedelta(days=30)
        
        quota = BillingQuota(
            quota_id="quota_123",
            user_id="user_123",
            service_type=ServiceType.MODEL_INFERENCE,
            product_id="gpt-4",
            quota_limit=Decimal("10000"),
            reset_date=reset_date,
            auto_reset=True
        )
        assert quota.quota_id == "quota_123"
        assert quota.user_id == "user_123"
        assert quota.quota_limit == Decimal("10000")
        assert quota.quota_used == Decimal("0")  # Default
        assert quota.quota_remaining == Decimal("0")  # Default
        assert quota.is_active is True  # Default
        assert quota.is_exceeded is False  # Default

    def test_quota_with_usage(self):
        """CHAR: Quota with current usage"""
        quota = BillingQuota(
            quota_id="quota_123",
            user_id="user_123",
            service_type=ServiceType.MODEL_INFERENCE,
            product_id="gpt-4",
            quota_limit=Decimal("10000"),
            quota_used=Decimal("3000"),
            quota_remaining=Decimal("7000"),
            reset_date=datetime.now(timezone.utc) + timedelta(days=30),
            auto_reset=True
        )
        assert quota.quota_used == Decimal("3000")
        assert quota.quota_remaining == Decimal("7000")

    def test_quota_must_be_non_negative(self):
        """CHAR: Quota fields must be >= 0"""
        with pytest.raises(ValidationError):
            BillingQuota(
                quota_id="quota_123",
                user_id="user_123",
                service_type=ServiceType.MODEL_INFERENCE,
                quota_limit=Decimal("-1000"),  # Negative
                reset_date=datetime.now(timezone.utc)
            )

        with pytest.raises(ValidationError):
            BillingQuota(
                quota_id="quota_123",
                user_id="user_123",
                service_type=ServiceType.MODEL_INFERENCE,
                quota_limit=Decimal("1000"),
                quota_used=Decimal("-500"),  # Negative
                reset_date=datetime.now(timezone.utc)
            )


# =============================================================================
# ProcessBillingRequest - Current Behavior
# =============================================================================

class TestProcessBillingRequestChar:
    """Characterization: ProcessBillingRequest current behavior"""

    def test_accepts_process_request(self):
        """CHAR: Valid process request is accepted"""
        request = ProcessBillingRequest(
            usage_record_id="usage_123",
            billing_method=BillingMethod.WALLET_DEDUCTION
        )
        assert request.usage_record_id == "usage_123"
        assert request.billing_method == BillingMethod.WALLET_DEDUCTION
        assert request.force_process is False  # Default

    def test_process_request_with_force(self):
        """CHAR: Process request with force flag"""
        request = ProcessBillingRequest(
            usage_record_id="usage_123",
            billing_method=BillingMethod.PAYMENT_CHARGE,
            force_process=True
        )
        assert request.force_process is True


# =============================================================================
# ProcessBillingResponse - Current Behavior
# =============================================================================

class TestProcessBillingResponseChar:
    """Characterization: ProcessBillingResponse current behavior"""

    def test_accepts_process_response(self):
        """CHAR: Valid process response is accepted"""
        response = ProcessBillingResponse(
            success=True,
            message="Billing processed successfully",
            billing_record_id="bill_123",
            amount_charged=Decimal("25.00"),
            billing_method_used=BillingMethod.WALLET_DEDUCTION,
            remaining_wallet_balance=Decimal("75.00"),
            wallet_transaction_id="wallet_tx_123"
        )
        assert response.success is True
        assert response.billing_record_id == "bill_123"
        assert response.amount_charged == Decimal("25.00")

    def test_process_response_with_failure(self):
        """CHAR: Process response with failure"""
        response = ProcessBillingResponse(
            success=False,
            message="Insufficient balance",
            billing_record_id=None,
            amount_charged=None,
            billing_method_used=None
        )
        assert response.success is False
        assert response.billing_record_id is None
        assert response.amount_charged is None

    def test_optional_fields_can_be_none(self):
        """CHAR: Optional fields can be None"""
        response = ProcessBillingResponse(
            success=True,
            message="Processed",
            billing_record_id="bill_123"
        )
        assert response.amount_charged is None
        assert response.billing_method_used is None
        assert response.wallet_transaction_id is None


# =============================================================================
# UsageStatsRequest - Current Behavior
# =============================================================================

class TestUsageStatsRequestChar:
    """Characterization: UsageStatsRequest current behavior"""

    def test_accepts_minimal_stats_request(self):
        """CHAR: Minimal stats request is accepted"""
        request = UsageStatsRequest()
        assert request.user_id is None  # Default
        assert request.service_type is None  # Default
        assert request.start_date is None  # Default
        assert request.end_date is None  # Default
        assert request.period_type == "daily"  # Default

    def test_accepts_full_stats_request(self):
        """CHAR: Full stats request with all fields"""
        start = datetime.now(timezone.utc) - timedelta(days=30)
        end = datetime.now(timezone.utc)
        
        request = UsageStatsRequest(
            user_id="user_123",
            organization_id="org_123",
            subscription_id="sub_123",
            service_type=ServiceType.MODEL_INFERENCE,
            product_id="gpt-4",
            start_date=start,
            end_date=end,
            period_type="monthly"
        )
        assert request.user_id == "user_123"
        assert request.service_type == ServiceType.MODEL_INFERENCE
        assert request.period_type == "monthly"


# =============================================================================
# HealthResponse - Current Behavior
# =============================================================================

class TestHealthResponseChar:
    """Characterization: HealthResponse current behavior"""

    def test_accepts_health_response(self):
        """CHAR: Valid health response is accepted"""
        response = HealthResponse(
            status="operational",
            service="billing_service",
            port=8216,
            version="1.0.0",
            dependencies={"postgres": "healthy", "wallet_service": "healthy"}
        )
        assert response.status == "operational"
        assert response.service == "billing_service"
        assert response.port == 8216
        assert "postgres" in response.dependencies


# =============================================================================
# ServiceInfo - Current Behavior
# =============================================================================

class TestServiceInfoChar:
    """Characterization: ServiceInfo current behavior"""

    def test_accepts_service_info(self):
        """CHAR: Valid service info is accepted"""
        info = ServiceInfo(
            service="billing_service",
            version="1.0.0",
            description="Usage tracking and billing processing",
            capabilities=["usage_tracking", "billing_calculation", "payment_processing"],
            supported_services=[ServiceType.MODEL_INFERENCE, ServiceType.MCP_SERVICE],
            supported_billing_methods=[BillingMethod.WALLET_DEDUCTION, BillingMethod.CREDIT_CONSUMPTION]
        )
        assert info.service == "billing_service"
        assert len(info.capabilities) == 3
        assert ServiceType.MODEL_INFERENCE in info.supported_services
        assert BillingMethod.WALLET_DEDUCTION in info.supported_billing_methods


# =============================================================================
# BillingStats - Current Behavior
# =============================================================================

class TestBillingStatsChar:
    """Characterization: BillingStats current behavior"""

    def test_accepts_billing_stats(self):
        """CHAR: Valid billing stats is accepted"""
        start = datetime.now(timezone.utc) - timedelta(days=30)
        end = datetime.now(timezone.utc)
        
        stats = BillingStats(
            total_billing_records=1000,
            pending_billing_records=50,
            completed_billing_records=900,
            failed_billing_records=50,
            total_revenue=Decimal("25000.00"),
            revenue_by_service={
                ServiceType.MODEL_INFERENCE: Decimal("20000.00"),
                ServiceType.MCP_SERVICE: Decimal("5000.00")
            },
            revenue_by_method={
                BillingMethod.WALLET_DEDUCTION: Decimal("15000.00"),
                BillingMethod.PAYMENT_CHARGE: Decimal("10000.00")
            },
            active_users=500,
            active_organizations=50,
            stats_period_start=start,
            stats_period_end=end
        )
        assert stats.total_billing_records == 1000
        assert stats.completed_billing_records == 900
        assert stats.active_users == 500
        assert ServiceType.MODEL_INFERENCE in stats.revenue_by_service
        assert BillingMethod.WALLET_DEDUCTION in stats.revenue_by_method


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
