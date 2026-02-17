"""
Wallet Service Integration Golden Tests

Tests WalletService with HTTP and database integration.
These tests require running services for full integration testing.

Usage:
    pytest tests/integration/golden/wallet_service/test_wallet_integration_golden.py -v
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
import httpx

pytestmark = [pytest.mark.integration, pytest.mark.golden]

# Service configuration
WALLET_SERVICE_URL = "http://localhost:8213"


@pytest.fixture
def wallet_client():
    """Create HTTP client for wallet service"""
    return httpx.AsyncClient(base_url=WALLET_SERVICE_URL, timeout=30.0)


class TestWalletServiceHealth:
    """
    Golden: Wallet Service Health Checks
    """

    @pytest.mark.asyncio
    async def test_health_endpoint(self, wallet_client):
        """GOLDEN: /health returns healthy status"""
        response = await wallet_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "wallet_service"
        assert "version" in data
        assert "timestamp" in data


class TestWalletCreationIntegration:
    """
    Golden: Wallet Creation Integration Tests
    """

    @pytest.mark.asyncio
    async def test_create_wallet_full_flow(self, wallet_client):
        """GOLDEN: Full wallet creation flow"""
        from tests.contracts.wallet.data_contract import WalletTestDataFactory

        user_id = WalletTestDataFactory.make_user_id()

        request_data = {
            "user_id": user_id,
            "wallet_type": "fiat",
            "initial_balance": "0",
            "currency": "CREDIT",
        }

        response = await wallet_client.post("/api/v1/wallets", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["wallet_id"] is not None

    @pytest.mark.asyncio
    async def test_create_duplicate_fiat_wallet(self, wallet_client):
        """GOLDEN: Creating duplicate FIAT wallet returns existing"""
        from tests.contracts.wallet.data_contract import WalletTestDataFactory

        user_id = WalletTestDataFactory.make_user_id()

        request_data = {
            "user_id": user_id,
            "wallet_type": "fiat",
            "initial_balance": "0",
            "currency": "CREDIT",
        }

        # First creation
        response1 = await wallet_client.post("/api/v1/wallets", json=request_data)
        assert response1.status_code == 200
        data1 = response1.json()

        # Second creation attempt
        response2 = await wallet_client.post("/api/v1/wallets", json=request_data)
        assert response2.status_code == 200
        data2 = response2.json()

        # Should return same wallet ID
        if data1["success"]:
            # First was new
            assert data2["success"] is False
            assert data2["wallet_id"] == data1["wallet_id"]


class TestWalletTransactionsIntegration:
    """
    Golden: Wallet Transactions Integration Tests
    """

    @pytest.fixture
    async def test_wallet(self, wallet_client):
        """Create a test wallet for transaction tests"""
        from tests.contracts.wallet.data_contract import WalletTestDataFactory

        user_id = WalletTestDataFactory.make_user_id()

        request_data = {
            "user_id": user_id,
            "wallet_type": "fiat",
            "initial_balance": "1000",
            "currency": "CREDIT",
        }

        response = await wallet_client.post("/api/v1/wallets", json=request_data)
        data = response.json()

        return {
            "wallet_id": data["wallet_id"],
            "user_id": user_id,
        }

    @pytest.mark.asyncio
    async def test_deposit_full_flow(self, wallet_client, test_wallet):
        """GOLDEN: Full deposit flow"""
        wallet_id = test_wallet["wallet_id"]

        request_data = {
            "amount": "100.00",
            "description": "Test deposit",
            "reference_id": "payment_test_123",
        }

        response = await wallet_client.post(
            f"/api/v1/wallets/{wallet_id}/deposit",
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["transaction_id"] is not None

    @pytest.mark.asyncio
    async def test_withdraw_full_flow(self, wallet_client, test_wallet):
        """GOLDEN: Full withdrawal flow"""
        wallet_id = test_wallet["wallet_id"]

        request_data = {
            "amount": "50.00",
            "description": "Test withdrawal",
        }

        response = await wallet_client.post(
            f"/api/v1/wallets/{wallet_id}/withdraw",
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_withdraw_insufficient_balance(self, wallet_client, test_wallet):
        """GOLDEN: Withdrawal with insufficient balance fails"""
        wallet_id = test_wallet["wallet_id"]

        request_data = {
            "amount": "999999.00",
            "description": "Large withdrawal",
        }

        response = await wallet_client.post(
            f"/api/v1/wallets/{wallet_id}/withdraw",
            json=request_data
        )

        assert response.status_code == 200  # Still 200 but success=False
        data = response.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_consume_full_flow(self, wallet_client, test_wallet):
        """GOLDEN: Full consumption flow"""
        wallet_id = test_wallet["wallet_id"]

        request_data = {
            "amount": "25.50",
            "description": "API usage charge",
            "usage_record_id": 12345,
        }

        response = await wallet_client.post(
            f"/api/v1/wallets/{wallet_id}/consume",
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestWalletQueryIntegration:
    """
    Golden: Wallet Query Integration Tests
    """

    @pytest.fixture
    async def test_wallet(self, wallet_client):
        """Create a test wallet for query tests"""
        from tests.contracts.wallet.data_contract import WalletTestDataFactory

        user_id = WalletTestDataFactory.make_user_id()

        request_data = {
            "user_id": user_id,
            "wallet_type": "fiat",
            "initial_balance": "500",
            "currency": "CREDIT",
        }

        response = await wallet_client.post("/api/v1/wallets", json=request_data)
        data = response.json()

        return {
            "wallet_id": data["wallet_id"],
            "user_id": user_id,
        }

    @pytest.mark.asyncio
    async def test_get_wallet_details(self, wallet_client, test_wallet):
        """GOLDEN: Get wallet details"""
        wallet_id = test_wallet["wallet_id"]

        response = await wallet_client.get(f"/api/v1/wallets/{wallet_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["wallet_id"] == wallet_id

    @pytest.mark.asyncio
    async def test_get_wallet_balance(self, wallet_client, test_wallet):
        """GOLDEN: Get wallet balance"""
        wallet_id = test_wallet["wallet_id"]

        response = await wallet_client.get(f"/api/v1/wallets/{wallet_id}/balance")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "balance" in data

    @pytest.mark.asyncio
    async def test_get_user_wallets(self, wallet_client, test_wallet):
        """GOLDEN: Get all wallets for user"""
        user_id = test_wallet["user_id"]

        response = await wallet_client.get(
            "/api/v1/wallets",
            params={"user_id": user_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert "wallets" in data
        assert data["count"] >= 1

    @pytest.mark.asyncio
    async def test_get_wallet_transactions(self, wallet_client, test_wallet):
        """GOLDEN: Get wallet transaction history"""
        wallet_id = test_wallet["wallet_id"]

        response = await wallet_client.get(
            f"/api/v1/wallets/{wallet_id}/transactions",
            params={"limit": 50, "offset": 0}
        )

        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        assert "count" in data

    @pytest.mark.asyncio
    async def test_get_wallet_statistics(self, wallet_client, test_wallet):
        """GOLDEN: Get wallet statistics"""
        wallet_id = test_wallet["wallet_id"]

        response = await wallet_client.get(f"/api/v1/wallets/{wallet_id}/statistics")

        assert response.status_code == 200
        data = response.json()
        assert data["wallet_id"] == wallet_id


class TestWalletTransferIntegration:
    """
    Golden: Wallet Transfer Integration Tests
    """

    @pytest.fixture
    async def source_wallet(self, wallet_client):
        """Create source wallet with balance"""
        from tests.contracts.wallet.data_contract import WalletTestDataFactory

        user_id = WalletTestDataFactory.make_user_id()

        request_data = {
            "user_id": user_id,
            "wallet_type": "fiat",
            "initial_balance": "1000",
            "currency": "CREDIT",
        }

        response = await wallet_client.post("/api/v1/wallets", json=request_data)
        return response.json()

    @pytest.fixture
    async def dest_wallet(self, wallet_client):
        """Create destination wallet"""
        from tests.contracts.wallet.data_contract import WalletTestDataFactory

        user_id = WalletTestDataFactory.make_user_id()

        request_data = {
            "user_id": user_id,
            "wallet_type": "fiat",
            "initial_balance": "100",
            "currency": "CREDIT",
        }

        response = await wallet_client.post("/api/v1/wallets", json=request_data)
        return response.json()

    @pytest.mark.asyncio
    async def test_transfer_full_flow(self, wallet_client, source_wallet, dest_wallet):
        """GOLDEN: Full transfer flow between wallets"""
        source_id = source_wallet["wallet_id"]
        dest_id = dest_wallet["wallet_id"]

        request_data = {
            "to_wallet_id": dest_id,
            "amount": "100.00",
            "description": "Test transfer",
        }

        response = await wallet_client.post(
            f"/api/v1/wallets/{source_id}/transfer",
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestCreditBalanceIntegration:
    """
    Golden: Credit Balance Backward Compatibility Tests
    """

    @pytest.fixture
    async def test_user(self, wallet_client):
        """Create a test user with wallet"""
        from tests.contracts.wallet.data_contract import WalletTestDataFactory

        user_id = WalletTestDataFactory.make_user_id()

        request_data = {
            "user_id": user_id,
            "wallet_type": "fiat",
            "initial_balance": "5000",
            "currency": "CREDIT",
        }

        await wallet_client.post("/api/v1/wallets", json=request_data)
        return user_id

    @pytest.mark.asyncio
    async def test_get_credit_balance(self, wallet_client, test_user):
        """GOLDEN: Get credit balance via backward compat endpoint"""
        response = await wallet_client.get(
            "/api/v1/wallets/credits/balance",
            params={"user_id": test_user}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "balance" in data
        assert "available_balance" in data
        assert data["currency"] == "CREDIT"

    @pytest.mark.asyncio
    async def test_consume_credits_by_user(self, wallet_client, test_user):
        """GOLDEN: Consume credits via backward compat endpoint"""
        request_data = {
            "amount": "50.00",
            "description": "API usage",
        }

        response = await wallet_client.post(
            "/api/v1/wallets/credits/consume",
            params={"user_id": test_user},
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
