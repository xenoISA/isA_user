"""
Wallet Service Smoke Tests

Basic end-to-end tests to verify service health and critical paths.
These tests are designed to be fast and run against deployed services.

Usage:
    pytest tests/smoke/wallet_service/test_wallet_smoke.py -v

Environment Variables:
    WALLET_SERVICE_URL: Wallet service base URL (default: http://localhost:8213)
"""
import os
import pytest
import httpx

pytestmark = [pytest.mark.smoke]

# Service configuration from environment
WALLET_SERVICE_URL = os.getenv("WALLET_SERVICE_URL", "http://localhost:8213")


@pytest.fixture
def client():
    """Create HTTP client for smoke tests"""
    return httpx.Client(base_url=WALLET_SERVICE_URL, timeout=10.0)


class TestServiceHealth:
    """
    Smoke: Verify service is running and healthy
    """

    def test_health_endpoint_available(self, client):
        """SMOKE: /health endpoint is accessible"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_healthy(self, client):
        """SMOKE: Service reports healthy status"""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_service_version_present(self, client):
        """SMOKE: Service version is present in health response"""
        response = client.get("/health")
        data = response.json()
        assert "version" in data
        assert data["version"] is not None


class TestCriticalPathWalletOperations:
    """
    Smoke: Critical path tests for wallet operations
    """

    def test_can_create_wallet(self, client):
        """SMOKE: Can create a new wallet"""
        import uuid

        user_id = f"smoke_test_user_{uuid.uuid4().hex[:8]}"

        request_data = {
            "user_id": user_id,
            "wallet_type": "fiat",
            "initial_balance": "100",
            "currency": "CREDIT",
        }

        response = client.post("/api/v1/wallets", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["wallet_id"] is not None

    def test_can_get_wallet(self, client):
        """SMOKE: Can retrieve wallet details"""
        import uuid

        # First create a wallet
        user_id = f"smoke_test_user_{uuid.uuid4().hex[:8]}"
        create_response = client.post("/api/v1/wallets", json={
            "user_id": user_id,
            "wallet_type": "fiat",
            "initial_balance": "0",
            "currency": "CREDIT",
        })

        wallet_id = create_response.json()["wallet_id"]

        # Then retrieve it
        response = client.get(f"/api/v1/wallets/{wallet_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["wallet_id"] == wallet_id

    def test_can_deposit_to_wallet(self, client):
        """SMOKE: Can deposit funds to wallet"""
        import uuid

        # First create a wallet
        user_id = f"smoke_test_user_{uuid.uuid4().hex[:8]}"
        create_response = client.post("/api/v1/wallets", json={
            "user_id": user_id,
            "wallet_type": "fiat",
            "initial_balance": "0",
            "currency": "CREDIT",
        })

        wallet_id = create_response.json()["wallet_id"]

        # Then deposit
        response = client.post(f"/api/v1/wallets/{wallet_id}/deposit", json={
            "amount": "50.00",
            "description": "Smoke test deposit",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_can_get_balance(self, client):
        """SMOKE: Can get wallet balance"""
        import uuid

        # First create a wallet with balance
        user_id = f"smoke_test_user_{uuid.uuid4().hex[:8]}"
        create_response = client.post("/api/v1/wallets", json={
            "user_id": user_id,
            "wallet_type": "fiat",
            "initial_balance": "500",
            "currency": "CREDIT",
        })

        wallet_id = create_response.json()["wallet_id"]

        # Then get balance
        response = client.get(f"/api/v1/wallets/{wallet_id}/balance")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "balance" in data


class TestCriticalPathTransactions:
    """
    Smoke: Critical path tests for transaction operations
    """

    def test_can_withdraw_from_wallet(self, client):
        """SMOKE: Can withdraw funds from wallet"""
        import uuid

        # Create wallet with balance
        user_id = f"smoke_test_user_{uuid.uuid4().hex[:8]}"
        create_response = client.post("/api/v1/wallets", json={
            "user_id": user_id,
            "wallet_type": "fiat",
            "initial_balance": "1000",
            "currency": "CREDIT",
        })

        wallet_id = create_response.json()["wallet_id"]

        # Withdraw
        response = client.post(f"/api/v1/wallets/{wallet_id}/withdraw", json={
            "amount": "100.00",
            "description": "Smoke test withdrawal",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_can_consume_credits(self, client):
        """SMOKE: Can consume credits from wallet"""
        import uuid

        # Create wallet with balance
        user_id = f"smoke_test_user_{uuid.uuid4().hex[:8]}"
        create_response = client.post("/api/v1/wallets", json={
            "user_id": user_id,
            "wallet_type": "fiat",
            "initial_balance": "500",
            "currency": "CREDIT",
        })

        wallet_id = create_response.json()["wallet_id"]

        # Consume
        response = client.post(f"/api/v1/wallets/{wallet_id}/consume", json={
            "amount": "25.00",
            "description": "Smoke test consumption",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_can_get_transaction_history(self, client):
        """SMOKE: Can retrieve transaction history"""
        import uuid

        # Create wallet and make some transactions
        user_id = f"smoke_test_user_{uuid.uuid4().hex[:8]}"
        create_response = client.post("/api/v1/wallets", json={
            "user_id": user_id,
            "wallet_type": "fiat",
            "initial_balance": "100",
            "currency": "CREDIT",
        })

        wallet_id = create_response.json()["wallet_id"]

        # Get transactions
        response = client.get(f"/api/v1/wallets/{wallet_id}/transactions")
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        assert "count" in data


class TestCriticalPathTransfer:
    """
    Smoke: Critical path tests for transfer operations
    """

    def test_can_transfer_between_wallets(self, client):
        """SMOKE: Can transfer funds between wallets"""
        import uuid

        # Create source wallet with balance
        user_id_1 = f"smoke_test_user_{uuid.uuid4().hex[:8]}"
        source_response = client.post("/api/v1/wallets", json={
            "user_id": user_id_1,
            "wallet_type": "fiat",
            "initial_balance": "1000",
            "currency": "CREDIT",
        })
        source_wallet_id = source_response.json()["wallet_id"]

        # Create destination wallet
        user_id_2 = f"smoke_test_user_{uuid.uuid4().hex[:8]}"
        dest_response = client.post("/api/v1/wallets", json={
            "user_id": user_id_2,
            "wallet_type": "fiat",
            "initial_balance": "0",
            "currency": "CREDIT",
        })
        dest_wallet_id = dest_response.json()["wallet_id"]

        # Transfer
        response = client.post(f"/api/v1/wallets/{source_wallet_id}/transfer", json={
            "to_wallet_id": dest_wallet_id,
            "amount": "200.00",
            "description": "Smoke test transfer",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestCriticalPathStatistics:
    """
    Smoke: Critical path tests for statistics
    """

    def test_can_get_wallet_statistics(self, client):
        """SMOKE: Can get wallet statistics"""
        import uuid

        # Create wallet
        user_id = f"smoke_test_user_{uuid.uuid4().hex[:8]}"
        create_response = client.post("/api/v1/wallets", json={
            "user_id": user_id,
            "wallet_type": "fiat",
            "initial_balance": "100",
            "currency": "CREDIT",
        })

        wallet_id = create_response.json()["wallet_id"]

        # Get statistics
        response = client.get(f"/api/v1/wallets/{wallet_id}/statistics")
        assert response.status_code == 200
        data = response.json()
        assert data["wallet_id"] == wallet_id


class TestBackwardCompatibility:
    """
    Smoke: Backward compatibility endpoints
    """

    def test_credit_balance_endpoint_works(self, client):
        """SMOKE: Credit balance backward compat endpoint works"""
        import uuid

        # Create wallet
        user_id = f"smoke_test_user_{uuid.uuid4().hex[:8]}"
        client.post("/api/v1/wallets", json={
            "user_id": user_id,
            "wallet_type": "fiat",
            "initial_balance": "500",
            "currency": "CREDIT",
        })

        # Get credit balance via backward compat endpoint
        response = client.get(
            "/api/v1/wallets/credits/balance",
            params={"user_id": user_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "balance" in data

    def test_service_stats_endpoint_works(self, client):
        """SMOKE: Service stats endpoint works"""
        response = client.get("/api/v1/wallet/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "wallet_service"
        assert data["status"] == "operational"
