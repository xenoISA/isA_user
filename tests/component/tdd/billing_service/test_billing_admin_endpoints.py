"""
Billing Service — Component Tests for Admin Endpoints (#195)

Tests for:
- GET /api/v1/billing/admin/records — list all billing records (admin)
- POST /api/v1/billing/admin/refund — issue refund with reason

All tests use mocked dependencies via dependency injection overrides.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

pytestmark = [pytest.mark.component, pytest.mark.asyncio]

ADMIN_HEADERS = {"X-Admin-Role": "true", "X-Admin-User-Id": "admin_test_001"}
NON_ADMIN_HEADERS = {}


def _make_mock_billing_record(
    billing_id="bill_001",
    user_id="user_001",
    status="completed",
    total_amount="10.50",
):
    """Create a mock billing record object."""
    from microservices.billing_service.models import (
        BillingRecord,
        BillingStatus,
        BillingMethod,
        ServiceType,
        Currency,
    )

    return BillingRecord(
        billing_id=billing_id,
        user_id=user_id,
        usage_record_id="usage_001",
        product_id="prod_001",
        service_type=ServiceType.MODEL_INFERENCE,
        usage_amount=Decimal("100"),
        unit_price=Decimal("0.105"),
        total_amount=Decimal(total_amount),
        currency=Currency.CREDIT,
        billing_method=BillingMethod.CREDIT_CONSUMPTION,
        billing_status=BillingStatus(status),
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_billing_service():
    """Create a mock billing service with mocked repository."""
    service = MagicMock()
    service.repository = MagicMock()
    return service


@pytest.fixture
async def client(mock_billing_service):
    """Create an async test client with dependency overrides."""
    from microservices.billing_service.main import app, get_billing_service

    app.dependency_overrides[get_billing_service] = lambda: mock_billing_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


class TestAdminListBillingRecords:
    """Tests for GET /api/v1/billing/admin/records"""

    async def test_returns_403_without_admin_header(self, client):
        """Non-admin requests are rejected with 403"""
        response = await client.get(
            "/api/v1/billing/admin/records",
            headers=NON_ADMIN_HEADERS,
        )
        assert response.status_code == 403

    async def test_returns_records_with_admin_header(
        self, client, mock_billing_service
    ):
        """Admin can list all billing records"""
        record = _make_mock_billing_record()
        mock_billing_service.repository.list_billing_records = AsyncMock(
            return_value=([record], 1)
        )

        response = await client.get(
            "/api/v1/billing/admin/records",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["records"]) == 1
        assert data["total"] == 1

    async def test_supports_pagination(self, client, mock_billing_service):
        """Admin records endpoint supports pagination"""
        mock_billing_service.repository.list_billing_records = AsyncMock(
            return_value=([], 0)
        )

        response = await client.get(
            "/api/v1/billing/admin/records?page=2&page_size=10",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        call_kwargs = mock_billing_service.repository.list_billing_records.call_args
        assert call_kwargs.kwargs.get("offset") == 10 or call_kwargs[1].get("offset") == 10

    async def test_filters_by_user_id(self, client, mock_billing_service):
        """Admin can filter records by user_id"""
        mock_billing_service.repository.list_billing_records = AsyncMock(
            return_value=([], 0)
        )

        response = await client.get(
            "/api/v1/billing/admin/records?user_id=user_123",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        call_kwargs = mock_billing_service.repository.list_billing_records.call_args
        assert call_kwargs.kwargs.get("user_id") == "user_123" or call_kwargs[1].get("user_id") == "user_123"


class TestAdminIssueRefund:
    """Tests for POST /api/v1/billing/admin/refund"""

    async def test_returns_403_without_admin_header(self, client):
        """Non-admin requests are rejected with 403"""
        response = await client.post(
            "/api/v1/billing/admin/refund?billing_id=bill_001&reason=test",
            headers=NON_ADMIN_HEADERS,
        )
        assert response.status_code == 403

    async def test_issues_refund_successfully(self, client, mock_billing_service):
        """Admin can issue a refund"""
        record = _make_mock_billing_record(status="completed")
        mock_billing_service.repository.get_billing_record = AsyncMock(
            return_value=record
        )
        mock_billing_service.repository.update_billing_record_status = AsyncMock(
            return_value=record
        )

        response = await client.post(
            "/api/v1/billing/admin/refund?billing_id=bill_001&reason=customer+request",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["billing_id"] == "bill_001"
        assert "refunded_amount" in data

    async def test_returns_404_for_missing_record(self, client, mock_billing_service):
        """Returns 404 when billing record not found"""
        mock_billing_service.repository.get_billing_record = AsyncMock(
            return_value=None
        )

        response = await client.post(
            "/api/v1/billing/admin/refund?billing_id=bill_nonexistent&reason=test",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 404

    async def test_returns_400_for_already_refunded(self, client, mock_billing_service):
        """Returns 400 when record is already refunded"""
        record = _make_mock_billing_record(status="refunded")
        mock_billing_service.repository.get_billing_record = AsyncMock(
            return_value=record
        )

        response = await client.post(
            "/api/v1/billing/admin/refund?billing_id=bill_001&reason=test",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 400
