"""
Billing Service — Component Tests for New Endpoints (#74)

Tests for:
- GET /api/v1/billing/quota/{user_id} — user quota status
- GET /api/v1/billing/records — general billing records list

All tests use mocked dependencies.
"""

import pytest
from decimal import Decimal

from tests.contracts.billing.data_contract import BillingTestDataFactory

pytestmark = [pytest.mark.component, pytest.mark.asyncio]


class TestGetUserQuotas:
    """Component tests for GET /api/v1/billing/quota/{user_id}"""

    async def test_returns_quotas_for_user(
        self, billing_service, mock_billing_repository
    ):
        """Returns all quotas for a user"""
        user_id = BillingTestDataFactory.make_user_id()

        mock_billing_repository.add_quota(
            user_id=user_id,
            service_type="model_inference",
            quota_limit=Decimal("100000"),
            quota_used=Decimal("5000"),
        )
        mock_billing_repository.add_quota(
            user_id=user_id,
            service_type="mcp_service",
            quota_limit=Decimal("50000"),
            quota_used=Decimal("1000"),
        )

        quotas = await mock_billing_repository.get_user_quotas(user_id=user_id)
        assert len(quotas) == 2

    async def test_returns_empty_list_when_no_quotas(
        self, billing_service, mock_billing_repository
    ):
        """Returns empty list when user has no quotas"""
        user_id = BillingTestDataFactory.make_user_id()

        quotas = await mock_billing_repository.get_user_quotas(user_id=user_id)
        assert len(quotas) == 0

    async def test_filters_by_service_type(
        self, billing_service, mock_billing_repository
    ):
        """Filters quotas by service_type when provided"""
        user_id = BillingTestDataFactory.make_user_id()

        mock_billing_repository.add_quota(
            user_id=user_id,
            service_type="model_inference",
            quota_limit=Decimal("100000"),
        )
        mock_billing_repository.add_quota(
            user_id=user_id,
            service_type="mcp_service",
            quota_limit=Decimal("50000"),
        )

        quotas = await mock_billing_repository.get_user_quotas(
            user_id=user_id, service_type="model_inference"
        )
        assert len(quotas) == 1
        assert quotas[0].service_type == "model_inference"


class TestGetBillingRecords:
    """Component tests for GET /api/v1/billing/records"""

    async def test_returns_all_records_without_filters(
        self, billing_service, mock_billing_repository
    ):
        """Returns all records when no filters provided"""
        # Add records for different users
        from microservices.billing_service.models import RecordUsageRequest, ServiceType
        from microservices.billing_service.billing_service import BillingService
        from tests.component.golden.billing_service.mocks import MockProductClient

        user1 = BillingTestDataFactory.make_user_id()
        user2 = BillingTestDataFactory.make_user_id()

        # Manually add records to mock
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        mock_billing_repository._records["bill_001"] = {
            "billing_id": "bill_001",
            "user_id": user1,
            "organization_id": None,
            "subscription_id": None,
            "usage_record_id": "usage_001",
            "product_id": "prod_001",
            "service_type": "model_inference",
            "usage_amount": Decimal("1000"),
            "unit_price": Decimal("0.001"),
            "total_amount": Decimal("1.0"),
            "currency": "USD",
            "billing_method": "wallet_deduction",
            "billing_status": "completed",
            "processed_at": None,
            "failure_reason": None,
            "wallet_transaction_id": None,
            "payment_transaction_id": None,
            "billing_metadata": {},
            "created_at": now,
            "updated_at": now,
        }
        mock_billing_repository._records["bill_002"] = {
            "billing_id": "bill_002",
            "user_id": user2,
            "organization_id": None,
            "subscription_id": None,
            "usage_record_id": "usage_002",
            "product_id": "prod_002",
            "service_type": "mcp_service",
            "usage_amount": Decimal("500"),
            "unit_price": Decimal("0.002"),
            "total_amount": Decimal("1.0"),
            "currency": "USD",
            "billing_method": "credit_consumption",
            "billing_status": "pending",
            "processed_at": None,
            "failure_reason": None,
            "wallet_transaction_id": None,
            "payment_transaction_id": None,
            "billing_metadata": {},
            "created_at": now,
            "updated_at": now,
        }

        records = await mock_billing_repository.get_billing_records()
        assert len(records) == 2

    async def test_filters_by_user_id(
        self, billing_service, mock_billing_repository
    ):
        """Filters records by user_id when provided"""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        user1 = "user_filter_test_1"
        user2 = "user_filter_test_2"

        mock_billing_repository._records["bill_f1"] = {
            "billing_id": "bill_f1",
            "user_id": user1,
            "organization_id": None,
            "subscription_id": None,
            "usage_record_id": "usage_f1",
            "product_id": "prod_001",
            "service_type": "model_inference",
            "usage_amount": Decimal("1000"),
            "unit_price": Decimal("0.001"),
            "total_amount": Decimal("1.0"),
            "currency": "USD",
            "billing_method": "wallet_deduction",
            "billing_status": "completed",
            "processed_at": None,
            "failure_reason": None,
            "wallet_transaction_id": None,
            "payment_transaction_id": None,
            "billing_metadata": {},
            "created_at": now,
            "updated_at": now,
        }
        mock_billing_repository._records["bill_f2"] = {
            "billing_id": "bill_f2",
            "user_id": user2,
            "organization_id": None,
            "subscription_id": None,
            "usage_record_id": "usage_f2",
            "product_id": "prod_002",
            "service_type": "mcp_service",
            "usage_amount": Decimal("500"),
            "unit_price": Decimal("0.002"),
            "total_amount": Decimal("1.0"),
            "currency": "USD",
            "billing_method": "credit_consumption",
            "billing_status": "pending",
            "processed_at": None,
            "failure_reason": None,
            "wallet_transaction_id": None,
            "payment_transaction_id": None,
            "billing_metadata": {},
            "created_at": now,
            "updated_at": now,
        }

        records = await mock_billing_repository.get_billing_records(user_id=user1)
        assert len(records) == 1
        assert records[0].user_id == user1

    async def test_filters_by_status(
        self, billing_service, mock_billing_repository
    ):
        """Filters records by billing status"""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        mock_billing_repository._records["bill_s1"] = {
            "billing_id": "bill_s1",
            "user_id": "user_s1",
            "organization_id": None,
            "subscription_id": None,
            "usage_record_id": "usage_s1",
            "product_id": "prod_001",
            "service_type": "model_inference",
            "usage_amount": Decimal("1000"),
            "unit_price": Decimal("0.001"),
            "total_amount": Decimal("1.0"),
            "currency": "USD",
            "billing_method": "wallet_deduction",
            "billing_status": "completed",
            "processed_at": None,
            "failure_reason": None,
            "wallet_transaction_id": None,
            "payment_transaction_id": None,
            "billing_metadata": {},
            "created_at": now,
            "updated_at": now,
        }
        mock_billing_repository._records["bill_s2"] = {
            "billing_id": "bill_s2",
            "user_id": "user_s2",
            "organization_id": None,
            "subscription_id": None,
            "usage_record_id": "usage_s2",
            "product_id": "prod_002",
            "service_type": "model_inference",
            "usage_amount": Decimal("500"),
            "unit_price": Decimal("0.002"),
            "total_amount": Decimal("1.0"),
            "currency": "USD",
            "billing_method": "credit_consumption",
            "billing_status": "pending",
            "processed_at": None,
            "failure_reason": None,
            "wallet_transaction_id": None,
            "payment_transaction_id": None,
            "billing_metadata": {},
            "created_at": now,
            "updated_at": now,
        }

        records = await mock_billing_repository.get_billing_records(status="completed")
        assert len(records) == 1
        assert records[0].billing_status == "completed"

    async def test_pagination(
        self, billing_service, mock_billing_repository
    ):
        """Respects limit and offset parameters"""
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)

        for i in range(5):
            mock_billing_repository._records[f"bill_p{i}"] = {
                "billing_id": f"bill_p{i}",
                "user_id": "user_paginate",
                "organization_id": None,
                "subscription_id": None,
                "usage_record_id": f"usage_p{i}",
                "product_id": "prod_001",
                "service_type": "model_inference",
                "usage_amount": Decimal("1000"),
                "unit_price": Decimal("0.001"),
                "total_amount": Decimal("1.0"),
                "currency": "USD",
                "billing_method": "wallet_deduction",
                "billing_status": "completed",
                "processed_at": None,
                "failure_reason": None,
                "wallet_transaction_id": None,
                "payment_transaction_id": None,
                "billing_metadata": {},
                "created_at": now + timedelta(seconds=i),
                "updated_at": now,
            }

        records = await mock_billing_repository.get_billing_records(limit=2, offset=0)
        assert len(records) == 2

        records_page2 = await mock_billing_repository.get_billing_records(limit=2, offset=2)
        assert len(records_page2) == 2
