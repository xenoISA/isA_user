"""
TDD Test: Billing Record Creation Error Handling

This test reproduces the bug where database errors in create_billing_record
are hidden and replaced with a generic "Failed to create billing record" message.

Following TDD approach:
1. RED: Write failing test that exposes the bug
2. GREEN: Fix the code to make test pass
3. REFACTOR: Improve error handling
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from microservices.billing_service.billing_repository import BillingRepository
from microservices.billing_service.models import (
    BillingRecord,
    BillingStatus,
    BillingMethod,
    ServiceType,
    Currency,
)

pytestmark = [pytest.mark.component, pytest.mark.asyncio]


class TestBillingRecordCreationErrors:
    """Test error handling in billing record creation"""

    @pytest_asyncio.fixture
    async def mock_db_client(self):
        """Mock AsyncPostgresClient for testing"""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client

    @pytest_asyncio.fixture
    async def repository_with_mock_db(self, mock_db_client, monkeypatch):
        """Create repository with mocked database"""
        from core.config_manager import ConfigManager

        # Mock ConfigManager to avoid real service discovery
        mock_config = MagicMock(spec=ConfigManager)
        mock_config.discover_service = MagicMock(return_value=("localhost", 50061))

        # Create repository
        repository = BillingRepository(config=mock_config)

        # Replace db client with mock
        repository.db = mock_db_client

        return repository

    def create_test_billing_record(self) -> BillingRecord:
        """Helper to create a test billing record"""
        return BillingRecord(
            billing_id="bill_test_123",  # Required field
            user_id="test_user_123",
            product_id="gpt-4",
            service_type=ServiceType.MODEL_INFERENCE,
            usage_amount=Decimal("1000"),
            unit_price=Decimal("0.03"),
            total_amount=Decimal("30.00"),
            currency=Currency.USD,
            billing_method=BillingMethod.CREDIT_CONSUMPTION,
            billing_status=BillingStatus.PENDING,
            usage_record_id="usage_123",
        )

    @pytest.mark.asyncio
    async def test_database_error_should_propagate_original_exception(
        self, repository_with_mock_db, mock_db_client
    ):
        """
        BUG REPRODUCTION: When database query fails, the original error
        should be propagated, not replaced with generic message.

        Current behavior: Raises "Failed to create billing record"
        Expected behavior: Raises the actual database error
        """
        # Arrange: Mock database to raise a specific error
        db_error = Exception("Database constraint violation: column 'invalid_field' does not exist")
        mock_db_client.query = AsyncMock(side_effect=db_error)

        billing_record = self.create_test_billing_record()

        # Act & Assert: Should propagate original error, not generic message
        with pytest.raises(Exception) as exc_info:
            await repository_with_mock_db.create_billing_record(billing_record)

        # The exception message should contain the actual database error
        assert "constraint violation" in str(exc_info.value).lower() or \
               "invalid_field" in str(exc_info.value).lower(), \
               f"Expected database error details, got: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_empty_results_should_explain_why(
        self, repository_with_mock_db, mock_db_client
    ):
        """
        BUG REPRODUCTION: When INSERT returns no results,
        error message should explain why (not just "Failed to create")

        Current behavior: Raises "Failed to create billing record"
        Expected behavior: Raises meaningful error about why INSERT failed
        """
        # Arrange: Mock database to return empty results (INSERT didn't work)
        mock_db_client.query = AsyncMock(return_value=[])  # Empty list

        billing_record = self.create_test_billing_record()

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await repository_with_mock_db.create_billing_record(billing_record)

        # Error should indicate INSERT returned no rows
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in [
            "no rows", "returned", "insert", "failed"
        ]), f"Error message should explain INSERT failure, got: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_successful_creation_returns_record_with_id(
        self, repository_with_mock_db, mock_db_client
    ):
        """
        Verify successful case: INSERT should return created record with ID
        """
        # Arrange: Mock successful database INSERT
        mock_db_client.query = AsyncMock(return_value=[{
            "id": 1,
            "billing_id": "bill_abc123",
            "user_id": "test_user_123",
            "organization_id": None,
            "subscription_id": None,
            "usage_record_id": "usage_123",
            "product_id": "gpt-4",
            "service_type": "model_inference",
            "usage_amount": 1000.0,
            "unit_price": 0.03,
            "total_amount": 30.00,
            "currency": "USD",
            "billing_method": "credit_consumption",
            "billing_status": "pending",
            "wallet_transaction_id": None,
            "payment_transaction_id": None,
            "failure_reason": None,
            "billing_metadata": {},
            "billing_period_start": None,
            "billing_period_end": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }])

        billing_record = self.create_test_billing_record()

        # Act
        result = await repository_with_mock_db.create_billing_record(billing_record)

        # Assert
        assert result is not None
        assert result.billing_id == "bill_abc123"
        assert result.user_id == "test_user_123"
        assert result.product_id == "gpt-4"
