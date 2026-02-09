"""
Wallet Service API Golden Tests

Tests API endpoint contracts, request/response validation, and error handling.
Uses FastAPI TestClient for synchronous testing without running server.

Usage:
    pytest tests/api/golden/wallet_service/test_wallet_api_golden.py -v
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.api, pytest.mark.golden]


@pytest.fixture
def mock_wallet_service():
    """Create mock wallet service for API tests"""
    mock = AsyncMock()
    return mock


@pytest.fixture
def test_client(mock_wallet_service):
    """Create FastAPI TestClient with mocked dependencies"""
    with patch('microservices.wallet_service.main.wallet_microservice') as mock_ms:
        mock_ms.wallet_service = mock_wallet_service
        from microservices.wallet_service.main import app
        client = TestClient(app)
        yield client


class TestHealthEndpoint:
    """
    Golden: /health endpoint tests
    """

    def test_health_returns_200(self, test_client):
        """GOLDEN: Health endpoint returns 200"""
        response = test_client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, test_client):
        """GOLDEN: Health response has correct structure"""
        response = test_client.get("/health")
        data = response.json()

        assert "status" in data
        assert "service" in data
        assert "port" in data
        assert "version" in data
        assert "timestamp" in data

    def test_health_status_is_healthy(self, test_client):
        """GOLDEN: Health status is 'healthy'"""
        response = test_client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"


class TestCreateWalletEndpoint:
    """
    Golden: POST /api/v1/wallets endpoint tests
    """

    def test_create_wallet_success(self, test_client, mock_wallet_service):
        """GOLDEN: Create wallet with valid data returns 200"""
        from microservices.wallet_service.models import WalletResponse

        mock_wallet_service.create_wallet = AsyncMock(return_value=WalletResponse(
            success=True,
            message="Wallet created successfully",
            wallet_id="wallet_test_123",
            balance=Decimal("0"),
        ))

        request_data = {
            "user_id": "user_test_456",
            "wallet_type": "fiat",
            "initial_balance": "0",
            "currency": "CREDIT",
        }

        response = test_client.post("/api/v1/wallets", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["wallet_id"] == "wallet_test_123"

    def test_create_wallet_missing_user_id(self, test_client):
        """GOLDEN: Create wallet without user_id returns 422"""
        request_data = {
            "wallet_type": "fiat",
            "initial_balance": "0",
        }

        response = test_client.post("/api/v1/wallets", json=request_data)

        assert response.status_code == 422  # Pydantic validation error

    def test_create_wallet_invalid_type(self, test_client):
        """GOLDEN: Create wallet with invalid type returns 422"""
        request_data = {
            "user_id": "user_test_456",
            "wallet_type": "invalid_type",
            "initial_balance": "0",
        }

        response = test_client.post("/api/v1/wallets", json=request_data)

        assert response.status_code == 422

    def test_create_wallet_negative_balance(self, test_client):
        """GOLDEN: Create wallet with negative balance returns 422"""
        request_data = {
            "user_id": "user_test_456",
            "wallet_type": "fiat",
            "initial_balance": "-100",
        }

        response = test_client.post("/api/v1/wallets", json=request_data)

        assert response.status_code == 422


class TestGetWalletEndpoint:
    """
    Golden: GET /api/v1/wallets/{wallet_id} endpoint tests
    """

    def test_get_wallet_success(self, test_client, mock_wallet_service):
        """GOLDEN: Get wallet returns wallet details"""
        from microservices.wallet_service.models import WalletBalance, WalletType

        mock_wallet_service.get_wallet = AsyncMock(return_value=WalletBalance(
            wallet_id="wallet_123",
            user_id="user_456",
            balance=Decimal("1000"),
            locked_balance=Decimal("0"),
            available_balance=Decimal("1000"),
            currency="CREDIT",
            wallet_type=WalletType.FIAT,
            last_updated=datetime.now(timezone.utc),
        ))

        response = test_client.get("/api/v1/wallets/wallet_123")

        assert response.status_code == 200
        data = response.json()
        assert data["wallet_id"] == "wallet_123"

    def test_get_wallet_not_found(self, test_client, mock_wallet_service):
        """GOLDEN: Get non-existent wallet returns 404"""
        mock_wallet_service.get_wallet = AsyncMock(return_value=None)

        response = test_client.get("/api/v1/wallets/nonexistent")

        assert response.status_code == 404


class TestDepositEndpoint:
    """
    Golden: POST /api/v1/wallets/{wallet_id}/deposit endpoint tests
    """

    def test_deposit_success(self, test_client, mock_wallet_service):
        """GOLDEN: Valid deposit returns 200"""
        from microservices.wallet_service.models import WalletResponse

        mock_wallet_service.deposit = AsyncMock(return_value=WalletResponse(
            success=True,
            message="Deposited successfully",
            wallet_id="wallet_123",
            balance=Decimal("600"),
            transaction_id="txn_123",
        ))

        request_data = {
            "amount": "100.00",
            "description": "Test deposit",
        }

        response = test_client.post("/api/v1/wallets/wallet_123/deposit", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_deposit_zero_amount(self, test_client):
        """GOLDEN: Deposit with zero amount returns 422"""
        request_data = {
            "amount": "0",
            "description": "Invalid",
        }

        response = test_client.post("/api/v1/wallets/wallet_123/deposit", json=request_data)

        assert response.status_code == 422

    def test_deposit_negative_amount(self, test_client):
        """GOLDEN: Deposit with negative amount returns 422"""
        request_data = {
            "amount": "-50",
            "description": "Invalid",
        }

        response = test_client.post("/api/v1/wallets/wallet_123/deposit", json=request_data)

        assert response.status_code == 422


class TestWithdrawEndpoint:
    """
    Golden: POST /api/v1/wallets/{wallet_id}/withdraw endpoint tests
    """

    def test_withdraw_success(self, test_client, mock_wallet_service):
        """GOLDEN: Valid withdrawal returns 200"""
        from microservices.wallet_service.models import WalletResponse

        mock_wallet_service.withdraw = AsyncMock(return_value=WalletResponse(
            success=True,
            message="Withdrawal successful",
            wallet_id="wallet_123",
            balance=Decimal("450"),
            transaction_id="txn_123",
        ))

        request_data = {
            "amount": "50.00",
            "description": "Test withdrawal",
        }

        response = test_client.post("/api/v1/wallets/wallet_123/withdraw", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_withdraw_insufficient_balance(self, test_client, mock_wallet_service):
        """GOLDEN: Withdrawal with insufficient balance returns 400"""
        from microservices.wallet_service.models import WalletResponse

        mock_wallet_service.withdraw = AsyncMock(return_value=WalletResponse(
            success=False,
            message="Insufficient balance",
        ))

        request_data = {
            "amount": "999999.00",
            "description": "Large withdrawal",
        }

        response = test_client.post("/api/v1/wallets/wallet_123/withdraw", json=request_data)

        assert response.status_code == 400


class TestConsumeEndpoint:
    """
    Golden: POST /api/v1/wallets/{wallet_id}/consume endpoint tests
    """

    def test_consume_success(self, test_client, mock_wallet_service):
        """GOLDEN: Valid consumption returns 200"""
        from microservices.wallet_service.models import WalletResponse

        mock_wallet_service.consume = AsyncMock(return_value=WalletResponse(
            success=True,
            message="Consumption successful",
            wallet_id="wallet_123",
            balance=Decimal("475"),
            transaction_id="txn_123",
        ))

        request_data = {
            "amount": "25.00",
            "description": "API usage",
            "usage_record_id": 12345,
        }

        response = test_client.post("/api/v1/wallets/wallet_123/consume", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestTransferEndpoint:
    """
    Golden: POST /api/v1/wallets/{wallet_id}/transfer endpoint tests
    """

    def test_transfer_success(self, test_client, mock_wallet_service):
        """GOLDEN: Valid transfer returns 200"""
        from microservices.wallet_service.models import WalletResponse

        mock_wallet_service.transfer = AsyncMock(return_value=WalletResponse(
            success=True,
            message="Transfer successful",
            wallet_id="wallet_source",
            balance=Decimal("400"),
            transaction_id="txn_123",
        ))

        request_data = {
            "to_wallet_id": "wallet_dest",
            "amount": "100.00",
            "description": "Test transfer",
        }

        response = test_client.post("/api/v1/wallets/wallet_source/transfer", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_transfer_missing_destination(self, test_client):
        """GOLDEN: Transfer without destination returns 422"""
        request_data = {
            "amount": "100.00",
            "description": "Invalid transfer",
        }

        response = test_client.post("/api/v1/wallets/wallet_source/transfer", json=request_data)

        assert response.status_code == 422


class TestRefundEndpoint:
    """
    Golden: POST /api/v1/transactions/{transaction_id}/refund endpoint tests
    """

    def test_refund_success(self, test_client, mock_wallet_service):
        """GOLDEN: Valid refund returns 200"""
        from microservices.wallet_service.models import WalletResponse

        mock_wallet_service.refund = AsyncMock(return_value=WalletResponse(
            success=True,
            message="Refund successful",
            wallet_id="wallet_123",
            balance=Decimal("550"),
            transaction_id="txn_refund_123",
        ))

        request_data = {
            "original_transaction_id": "txn_original_123",
            "amount": "50.00",
            "reason": "Customer request",
        }

        response = test_client.post("/api/v1/transactions/txn_original_123/refund", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_refund_missing_reason(self, test_client):
        """GOLDEN: Refund without reason returns 422"""
        request_data = {
            "original_transaction_id": "txn_123",
            "amount": "50.00",
            # Missing reason
        }

        response = test_client.post("/api/v1/transactions/txn_123/refund", json=request_data)

        assert response.status_code == 422


class TestTransactionHistoryEndpoint:
    """
    Golden: GET /api/v1/wallets/{wallet_id}/transactions endpoint tests
    """

    def test_get_transactions_success(self, test_client, mock_wallet_service):
        """GOLDEN: Get transactions returns paginated list"""
        from microservices.wallet_service.models import WalletTransaction, TransactionType

        mock_wallet_service.get_transactions = AsyncMock(return_value=[
            WalletTransaction(
                transaction_id="txn_1",
                wallet_id="wallet_123",
                user_id="user_456",
                transaction_type=TransactionType.DEPOSIT,
                amount=Decimal("100"),
                balance_before=Decimal("0"),
                balance_after=Decimal("100"),
                created_at=datetime.now(timezone.utc),
            ),
        ])

        response = test_client.get("/api/v1/wallets/wallet_123/transactions")

        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        assert "count" in data

    def test_get_transactions_with_pagination(self, test_client, mock_wallet_service):
        """GOLDEN: Get transactions respects pagination params"""
        mock_wallet_service.get_transactions = AsyncMock(return_value=[])

        response = test_client.get(
            "/api/v1/wallets/wallet_123/transactions",
            params={"limit": 10, "offset": 20}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 20


class TestStatisticsEndpoint:
    """
    Golden: GET /api/v1/wallets/{wallet_id}/statistics endpoint tests
    """

    def test_get_statistics_success(self, test_client, mock_wallet_service):
        """GOLDEN: Get statistics returns aggregated data"""
        from microservices.wallet_service.models import WalletStatistics

        mock_wallet_service.get_statistics = AsyncMock(return_value=WalletStatistics(
            wallet_id="wallet_123",
            user_id="user_456",
            current_balance=Decimal("1000"),
            total_deposits=Decimal("5000"),
            total_withdrawals=Decimal("2000"),
            total_consumed=Decimal("1500"),
            total_refunded=Decimal("500"),
            total_transfers_in=Decimal("1000"),
            total_transfers_out=Decimal("2000"),
            transaction_count=47,
        ))

        response = test_client.get("/api/v1/wallets/wallet_123/statistics")

        assert response.status_code == 200
        data = response.json()
        assert data["wallet_id"] == "wallet_123"
        assert data["transaction_count"] == 47

    def test_get_statistics_not_found(self, test_client, mock_wallet_service):
        """GOLDEN: Get statistics for non-existent wallet returns 404"""
        mock_wallet_service.get_statistics = AsyncMock(return_value=None)

        response = test_client.get("/api/v1/wallets/nonexistent/statistics")

        assert response.status_code == 404


class TestCreditBalanceEndpoint:
    """
    Golden: /api/v1/wallets/credits/balance endpoint tests (backward compat)
    """

    def test_get_credit_balance_success(self, test_client, mock_wallet_service):
        """GOLDEN: Get credit balance returns balance info"""
        from microservices.wallet_service.models import WalletBalance, WalletType

        mock_wallet_service.get_user_wallets = AsyncMock(return_value=[
            WalletBalance(
                wallet_id="wallet_123",
                user_id="user_456",
                balance=Decimal("1000"),
                locked_balance=Decimal("50"),
                available_balance=Decimal("950"),
                currency="CREDIT",
                wallet_type=WalletType.FIAT,
                last_updated=datetime.now(timezone.utc),
            ),
        ])

        response = test_client.get(
            "/api/v1/wallets/credits/balance",
            params={"user_id": "user_456"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "balance" in data
        assert "available_balance" in data

    def test_get_credit_balance_missing_user_id(self, test_client):
        """GOLDEN: Get credit balance without user_id returns 422"""
        response = test_client.get("/api/v1/wallets/credits/balance")

        assert response.status_code == 422
