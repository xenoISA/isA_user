"""
Wallet Service — Component Tests for Admin Endpoints (#195)

Tests for:
- GET /api/v1/wallet/admin/{user_id} — wallet details (admin)
- POST /api/v1/wallet/admin/{user_id}/adjust — balance adjustment with reason

All tests use mocked dependencies via dependency injection overrides.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient, ASGITransport

pytestmark = [pytest.mark.component, pytest.mark.asyncio]

ADMIN_HEADERS = {"X-Admin-Role": "true", "X-Admin-User-Id": "admin_test_001"}
NON_ADMIN_HEADERS = {}


def _make_mock_wallet(
    wallet_id="wal_001",
    user_id="user_001",
    balance="100.00",
    wallet_type="fiat",
):
    """Create a mock wallet balance object."""
    from microservices.wallet_service.models import WalletBalance, WalletType

    return WalletBalance(
        wallet_id=wallet_id,
        user_id=user_id,
        balance=Decimal(balance),
        locked_balance=Decimal("0"),
        available_balance=Decimal(balance),
        currency="CREDIT",
        wallet_type=WalletType(wallet_type),
        last_updated=datetime.now(timezone.utc),
    )


def _make_wallet_response(success=True, balance="150.00", wallet_id="wal_001", tx_id="tx_001"):
    """Create a mock WalletResponse."""
    from microservices.wallet_service.models import WalletResponse

    return WalletResponse(
        success=success,
        message="OK",
        wallet_id=wallet_id,
        balance=Decimal(balance),
        transaction_id=tx_id,
    )


@pytest.fixture
def mock_wallet_service():
    """Create a mock wallet service."""
    service = MagicMock()
    return service


@pytest.fixture
async def client(mock_wallet_service):
    """Create an async test client with dependency overrides."""
    from microservices.wallet_service.main import app, get_wallet_service

    app.dependency_overrides[get_wallet_service] = lambda: mock_wallet_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


class TestAdminGetWalletDetails:
    """Tests for GET /api/v1/wallet/admin/{user_id}"""

    async def test_returns_403_without_admin_header(self, client):
        """Non-admin requests are rejected with 403"""
        response = await client.get(
            "/api/v1/wallet/admin/user_001",
            headers=NON_ADMIN_HEADERS,
        )
        assert response.status_code == 403

    async def test_returns_wallet_details_with_admin_header(
        self, client, mock_wallet_service
    ):
        """Admin can retrieve user wallet details"""
        wallet = _make_mock_wallet(balance="250.50")
        mock_wallet_service.get_user_wallets = AsyncMock(return_value=[wallet])

        response = await client.get(
            "/api/v1/wallet/admin/user_001",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user_id"] == "user_001"
        assert data["wallet_count"] == 1
        assert len(data["wallets"]) == 1

    async def test_returns_empty_wallets_for_new_user(
        self, client, mock_wallet_service
    ):
        """Returns empty wallet list for user with no wallets"""
        mock_wallet_service.get_user_wallets = AsyncMock(return_value=[])

        response = await client.get(
            "/api/v1/wallet/admin/user_new",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["wallet_count"] == 0

    async def test_returns_multiple_wallets(self, client, mock_wallet_service):
        """Returns all wallets when user has multiple"""
        wallets = [
            _make_mock_wallet(wallet_id="wal_001", balance="100.00"),
            _make_mock_wallet(wallet_id="wal_002", balance="50.00", wallet_type="fiat"),
        ]
        mock_wallet_service.get_user_wallets = AsyncMock(return_value=wallets)

        response = await client.get(
            "/api/v1/wallet/admin/user_001",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["wallet_count"] == 2
        assert data["total_balance"] == 150.0


class TestAdminAdjustWalletBalance:
    """Tests for POST /api/v1/wallet/admin/{user_id}/adjust"""

    async def test_returns_403_without_admin_header(self, client):
        """Non-admin requests are rejected with 403"""
        response = await client.post(
            "/api/v1/wallet/admin/user_001/adjust?amount=50&reason=test",
            headers=NON_ADMIN_HEADERS,
        )
        assert response.status_code == 403

    async def test_adds_balance_successfully(self, client, mock_wallet_service):
        """Admin can add balance to user wallet"""
        wallet = _make_mock_wallet(balance="100.00")
        mock_wallet_service.get_user_wallets = AsyncMock(return_value=[wallet])
        mock_wallet_service.deposit = AsyncMock(
            return_value=_make_wallet_response(balance="150.00")
        )

        response = await client.post(
            "/api/v1/wallet/admin/user_001/adjust?amount=50&reason=promotional+credit",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_balance"] == "150.00"

    async def test_subtracts_balance_successfully(self, client, mock_wallet_service):
        """Admin can subtract balance from user wallet"""
        wallet = _make_mock_wallet(balance="100.00")
        mock_wallet_service.get_user_wallets = AsyncMock(return_value=[wallet])
        mock_wallet_service.withdraw = AsyncMock(
            return_value=_make_wallet_response(balance="70.00")
        )

        response = await client.post(
            "/api/v1/wallet/admin/user_001/adjust?amount=-30&reason=correction",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_balance"] == "70.00"

    async def test_returns_404_when_no_fiat_wallet(self, client, mock_wallet_service):
        """Returns 404 when user has no fiat wallet"""
        mock_wallet_service.get_user_wallets = AsyncMock(return_value=[])

        response = await client.post(
            "/api/v1/wallet/admin/user_001/adjust?amount=50&reason=test",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 404

    async def test_returns_400_for_zero_amount(self, client, mock_wallet_service):
        """Returns 400 when adjustment amount is zero"""
        wallet = _make_mock_wallet()
        mock_wallet_service.get_user_wallets = AsyncMock(return_value=[wallet])

        response = await client.post(
            "/api/v1/wallet/admin/user_001/adjust?amount=0&reason=test",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 400

    async def test_targets_specific_wallet_by_id(self, client, mock_wallet_service):
        """Admin can target a specific wallet by ID"""
        wallet = _make_mock_wallet(wallet_id="wal_specific", user_id="user_001")
        mock_wallet_service.get_wallet = AsyncMock(return_value=wallet)
        mock_wallet_service.deposit = AsyncMock(
            return_value=_make_wallet_response(balance="200.00", wallet_id="wal_specific")
        )

        response = await client.post(
            "/api/v1/wallet/admin/user_001/adjust?amount=100&reason=bonus&wallet_id=wal_specific",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["wallet_id"] == "wal_specific"

    async def test_returns_400_when_deposit_fails(self, client, mock_wallet_service):
        """Returns 400 when the deposit operation fails"""
        wallet = _make_mock_wallet()
        mock_wallet_service.get_user_wallets = AsyncMock(return_value=[wallet])
        mock_wallet_service.deposit = AsyncMock(
            return_value=_make_wallet_response(success=False, balance="100.00")
        )

        # The WalletResponse has success=False so endpoint raises 400
        from microservices.wallet_service.models import WalletResponse
        fail_resp = WalletResponse(success=False, message="Deposit failed")
        mock_wallet_service.deposit = AsyncMock(return_value=fail_resp)

        response = await client.post(
            "/api/v1/wallet/admin/user_001/adjust?amount=50&reason=test",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 400
