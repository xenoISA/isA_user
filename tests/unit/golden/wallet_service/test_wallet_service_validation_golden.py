"""
Wallet Service Validation Logic Golden Tests

Tests the pure validation methods and business logic in WalletService.
Uses mock dependencies to isolate service layer.

Usage:
    pytest tests/unit/golden/wallet_service/test_wallet_service_validation_golden.py -v
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

pytestmark = [pytest.mark.unit, pytest.mark.golden]


class TestWalletServiceCreation:
    """
    Golden: WalletService wallet creation logic
    """

    def _create_service(self, repository=None, event_bus=None, account_client=None):
        """Create WalletService with mock dependencies"""
        from microservices.wallet_service.wallet_service import WalletService
        return WalletService(
            repository=repository or MagicMock(),
            event_bus=event_bus,
            account_client=account_client,
        )

    def _create_wallet_create_request(
        self,
        user_id="user_test_123",
        wallet_type="fiat",
        initial_balance=Decimal("0"),
        currency="CREDIT",
    ):
        """Create WalletCreate request"""
        from microservices.wallet_service.models import WalletCreate, WalletType
        return WalletCreate(
            user_id=user_id,
            wallet_type=WalletType(wallet_type),
            initial_balance=initial_balance,
            currency=currency,
        )

    @pytest.mark.asyncio
    async def test_create_wallet_success(self):
        """GOLDEN: Valid wallet creation succeeds"""
        from microservices.wallet_service.wallet_service import WalletService
        from microservices.wallet_service.models import WalletBalance, WalletType

        mock_repo = AsyncMock()
        mock_repo.get_user_wallets = AsyncMock(return_value=[])
        mock_repo.create_wallet = AsyncMock(return_value=WalletBalance(
            wallet_id="wallet_123",
            user_id="user_test_123",
            balance=Decimal("100"),
            locked_balance=Decimal("0"),
            available_balance=Decimal("100"),
            currency="CREDIT",
            wallet_type=WalletType.FIAT,
            last_updated=datetime.now(timezone.utc),
        ))

        service = self._create_service(repository=mock_repo)
        request = self._create_wallet_create_request(initial_balance=Decimal("100"))

        result = await service.create_wallet(request)

        assert result.success is True
        assert result.wallet_id == "wallet_123"
        assert result.balance == Decimal("100")

    @pytest.mark.asyncio
    async def test_create_duplicate_fiat_wallet_fails(self):
        """GOLDEN: Creating second FIAT wallet returns existing wallet info"""
        from microservices.wallet_service.wallet_service import WalletService
        from microservices.wallet_service.models import WalletBalance, WalletType

        existing_wallet = WalletBalance(
            wallet_id="existing_wallet_456",
            user_id="user_test_123",
            balance=Decimal("500"),
            locked_balance=Decimal("0"),
            available_balance=Decimal("500"),
            currency="CREDIT",
            wallet_type=WalletType.FIAT,
            last_updated=datetime.now(timezone.utc),
        )

        mock_repo = AsyncMock()
        mock_repo.get_user_wallets = AsyncMock(return_value=[existing_wallet])

        service = self._create_service(repository=mock_repo)
        request = self._create_wallet_create_request()

        result = await service.create_wallet(request)

        # Should return existing wallet info, not create new
        assert result.success is False
        assert "already has" in result.message.lower()
        assert result.wallet_id == "existing_wallet_456"

    @pytest.mark.asyncio
    async def test_create_wallet_publishes_event(self):
        """GOLDEN: Successful wallet creation publishes event"""
        from microservices.wallet_service.wallet_service import WalletService
        from microservices.wallet_service.models import WalletBalance, WalletType

        mock_repo = AsyncMock()
        mock_repo.get_user_wallets = AsyncMock(return_value=[])
        mock_repo.create_wallet = AsyncMock(return_value=WalletBalance(
            wallet_id="wallet_123",
            user_id="user_test_123",
            balance=Decimal("0"),
            locked_balance=Decimal("0"),
            available_balance=Decimal("0"),
            currency="CREDIT",
            wallet_type=WalletType.FIAT,
            last_updated=datetime.now(timezone.utc),
        ))

        mock_event_bus = AsyncMock()
        mock_event_bus.publish_event = AsyncMock()

        service = self._create_service(repository=mock_repo, event_bus=mock_event_bus)
        request = self._create_wallet_create_request()

        result = await service.create_wallet(request)

        assert result.success is True
        mock_event_bus.publish_event.assert_called_once()


class TestWalletServiceDeposit:
    """
    Golden: WalletService deposit operations
    """

    def _create_service(self, repository=None, event_bus=None):
        """Create WalletService with mock dependencies"""
        from microservices.wallet_service.wallet_service import WalletService
        return WalletService(
            repository=repository or MagicMock(),
            event_bus=event_bus,
        )

    def _create_deposit_request(
        self,
        amount=Decimal("100"),
        description="Test deposit",
        reference_id=None,
    ):
        """Create DepositRequest"""
        from microservices.wallet_service.models import DepositRequest
        return DepositRequest(
            amount=amount,
            description=description,
            reference_id=reference_id,
        )

    @pytest.mark.asyncio
    async def test_deposit_success(self):
        """GOLDEN: Valid deposit succeeds"""
        from microservices.wallet_service.models import WalletTransaction, TransactionType

        mock_repo = AsyncMock()
        mock_repo.deposit = AsyncMock(return_value=WalletTransaction(
            transaction_id="txn_123",
            wallet_id="wallet_456",
            user_id="user_789",
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal("100"),
            balance_before=Decimal("500"),
            balance_after=Decimal("600"),
            created_at=datetime.now(timezone.utc),
        ))

        service = self._create_service(repository=mock_repo)
        request = self._create_deposit_request()

        result = await service.deposit("wallet_456", request)

        assert result.success is True
        assert result.transaction_id == "txn_123"
        assert result.balance == Decimal("600")

    @pytest.mark.asyncio
    async def test_deposit_to_nonexistent_wallet_fails(self):
        """GOLDEN: Deposit to non-existent wallet fails"""
        mock_repo = AsyncMock()
        mock_repo.deposit = AsyncMock(return_value=None)

        service = self._create_service(repository=mock_repo)
        request = self._create_deposit_request()

        result = await service.deposit("nonexistent_wallet", request)

        assert result.success is False

    @pytest.mark.asyncio
    async def test_deposit_publishes_event(self):
        """GOLDEN: Successful deposit publishes event"""
        from microservices.wallet_service.models import WalletTransaction, TransactionType

        mock_repo = AsyncMock()
        mock_repo.deposit = AsyncMock(return_value=WalletTransaction(
            transaction_id="txn_123",
            wallet_id="wallet_456",
            user_id="user_789",
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal("100"),
            balance_before=Decimal("500"),
            balance_after=Decimal("600"),
            created_at=datetime.now(timezone.utc),
        ))

        mock_event_bus = AsyncMock()
        mock_event_bus.publish_event = AsyncMock()

        service = self._create_service(repository=mock_repo, event_bus=mock_event_bus)
        request = self._create_deposit_request()

        result = await service.deposit("wallet_456", request)

        assert result.success is True
        mock_event_bus.publish_event.assert_called_once()


class TestWalletServiceWithdraw:
    """
    Golden: WalletService withdrawal operations
    """

    def _create_service(self, repository=None, event_bus=None):
        """Create WalletService with mock dependencies"""
        from microservices.wallet_service.wallet_service import WalletService
        return WalletService(
            repository=repository or MagicMock(),
            event_bus=event_bus,
        )

    def _create_withdraw_request(
        self,
        amount=Decimal("50"),
        description="Test withdrawal",
        destination=None,
    ):
        """Create WithdrawRequest"""
        from microservices.wallet_service.models import WithdrawRequest
        return WithdrawRequest(
            amount=amount,
            description=description,
            destination=destination,
        )

    @pytest.mark.asyncio
    async def test_withdraw_success(self):
        """GOLDEN: Valid withdrawal succeeds"""
        from microservices.wallet_service.models import (
            WalletBalance,
            WalletTransaction,
            TransactionType,
            WalletType,
        )

        mock_repo = AsyncMock()
        mock_repo.get_wallet = AsyncMock(return_value=WalletBalance(
            wallet_id="wallet_456",
            user_id="user_789",
            balance=Decimal("500"),
            locked_balance=Decimal("0"),
            available_balance=Decimal("500"),
            currency="CREDIT",
            wallet_type=WalletType.FIAT,
            last_updated=datetime.now(timezone.utc),
        ))
        mock_repo.withdraw = AsyncMock(return_value=WalletTransaction(
            transaction_id="txn_123",
            wallet_id="wallet_456",
            user_id="user_789",
            transaction_type=TransactionType.WITHDRAW,
            amount=Decimal("50"),
            balance_before=Decimal("500"),
            balance_after=Decimal("450"),
            created_at=datetime.now(timezone.utc),
        ))

        service = self._create_service(repository=mock_repo)
        request = self._create_withdraw_request()

        result = await service.withdraw("wallet_456", request)

        assert result.success is True
        assert result.balance == Decimal("450")

    @pytest.mark.asyncio
    async def test_withdraw_insufficient_balance_fails(self):
        """GOLDEN: Withdrawal with insufficient balance fails"""
        from microservices.wallet_service.models import WalletBalance, WalletType

        mock_repo = AsyncMock()
        mock_repo.get_wallet = AsyncMock(return_value=WalletBalance(
            wallet_id="wallet_456",
            user_id="user_789",
            balance=Decimal("30"),
            locked_balance=Decimal("0"),
            available_balance=Decimal("30"),
            currency="CREDIT",
            wallet_type=WalletType.FIAT,
            last_updated=datetime.now(timezone.utc),
        ))
        mock_repo.withdraw = AsyncMock(return_value=None)  # Insufficient balance

        service = self._create_service(repository=mock_repo)
        request = self._create_withdraw_request(amount=Decimal("50"))

        result = await service.withdraw("wallet_456", request)

        assert result.success is False
        assert "insufficient" in result.message.lower() or "failed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_withdraw_from_nonexistent_wallet_fails(self):
        """GOLDEN: Withdrawal from non-existent wallet fails"""
        mock_repo = AsyncMock()
        mock_repo.get_wallet = AsyncMock(return_value=None)

        service = self._create_service(repository=mock_repo)
        request = self._create_withdraw_request()

        result = await service.withdraw("nonexistent_wallet", request)

        assert result.success is False
        assert "not found" in result.message.lower()


class TestWalletServiceConsume:
    """
    Golden: WalletService consumption operations
    """

    def _create_service(self, repository=None, event_bus=None):
        """Create WalletService with mock dependencies"""
        from microservices.wallet_service.wallet_service import WalletService
        return WalletService(
            repository=repository or MagicMock(),
            event_bus=event_bus,
        )

    def _create_consume_request(
        self,
        amount=Decimal("25"),
        description="API usage",
        usage_record_id=12345,
    ):
        """Create ConsumeRequest"""
        from microservices.wallet_service.models import ConsumeRequest
        return ConsumeRequest(
            amount=amount,
            description=description,
            usage_record_id=usage_record_id,
        )

    @pytest.mark.asyncio
    async def test_consume_success(self):
        """GOLDEN: Valid consumption succeeds"""
        from microservices.wallet_service.models import WalletTransaction, TransactionType

        mock_repo = AsyncMock()
        mock_repo.consume = AsyncMock(return_value=WalletTransaction(
            transaction_id="txn_123",
            wallet_id="wallet_456",
            user_id="user_789",
            transaction_type=TransactionType.CONSUME,
            amount=Decimal("25"),
            balance_before=Decimal("500"),
            balance_after=Decimal("475"),
            created_at=datetime.now(timezone.utc),
        ))

        service = self._create_service(repository=mock_repo)
        request = self._create_consume_request()

        result = await service.consume("wallet_456", request)

        assert result.success is True
        assert result.balance == Decimal("475")

    @pytest.mark.asyncio
    async def test_consume_insufficient_balance_fails(self):
        """GOLDEN: Consumption with insufficient balance fails"""
        mock_repo = AsyncMock()
        mock_repo.consume = AsyncMock(return_value=None)  # Insufficient balance

        service = self._create_service(repository=mock_repo)
        request = self._create_consume_request(amount=Decimal("1000"))

        result = await service.consume("wallet_456", request)

        assert result.success is False
        assert "insufficient" in result.message.lower()


class TestWalletServiceTransfer:
    """
    Golden: WalletService transfer operations
    """

    def _create_service(self, repository=None, event_bus=None):
        """Create WalletService with mock dependencies"""
        from microservices.wallet_service.wallet_service import WalletService
        return WalletService(
            repository=repository or MagicMock(),
            event_bus=event_bus,
        )

    def _create_transfer_request(
        self,
        to_wallet_id="wallet_dest_789",
        amount=Decimal("100"),
        description="Transfer to friend",
    ):
        """Create TransferRequest"""
        from microservices.wallet_service.models import TransferRequest
        return TransferRequest(
            to_wallet_id=to_wallet_id,
            amount=amount,
            description=description,
        )

    @pytest.mark.asyncio
    async def test_transfer_success(self):
        """GOLDEN: Valid transfer succeeds"""
        from microservices.wallet_service.models import WalletTransaction, TransactionType

        from_txn = WalletTransaction(
            transaction_id="txn_from_123",
            wallet_id="wallet_source",
            user_id="user_1",
            transaction_type=TransactionType.TRANSFER,
            amount=Decimal("100"),
            balance_before=Decimal("500"),
            balance_after=Decimal("400"),
            created_at=datetime.now(timezone.utc),
        )
        to_txn = WalletTransaction(
            transaction_id="txn_to_456",
            wallet_id="wallet_dest_789",
            user_id="user_2",
            transaction_type=TransactionType.TRANSFER,
            amount=Decimal("100"),
            balance_before=Decimal("200"),
            balance_after=Decimal("300"),
            created_at=datetime.now(timezone.utc),
        )

        mock_repo = AsyncMock()
        mock_repo.transfer = AsyncMock(return_value=(from_txn, to_txn))

        service = self._create_service(repository=mock_repo)
        request = self._create_transfer_request()

        result = await service.transfer("wallet_source", request)

        assert result.success is True
        assert result.balance == Decimal("400")

    @pytest.mark.asyncio
    async def test_transfer_insufficient_balance_fails(self):
        """GOLDEN: Transfer with insufficient balance fails"""
        mock_repo = AsyncMock()
        mock_repo.transfer = AsyncMock(return_value=None)  # Transfer failed

        service = self._create_service(repository=mock_repo)
        request = self._create_transfer_request(amount=Decimal("10000"))

        result = await service.transfer("wallet_source", request)

        assert result.success is False
        assert "failed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_transfer_publishes_event(self):
        """GOLDEN: Successful transfer publishes event"""
        from microservices.wallet_service.models import WalletTransaction, TransactionType

        from_txn = WalletTransaction(
            transaction_id="txn_from_123",
            wallet_id="wallet_source",
            user_id="user_1",
            transaction_type=TransactionType.TRANSFER,
            amount=Decimal("100"),
            balance_before=Decimal("500"),
            balance_after=Decimal("400"),
            created_at=datetime.now(timezone.utc),
        )
        to_txn = WalletTransaction(
            transaction_id="txn_to_456",
            wallet_id="wallet_dest",
            user_id="user_2",
            transaction_type=TransactionType.TRANSFER,
            amount=Decimal("100"),
            balance_before=Decimal("200"),
            balance_after=Decimal("300"),
            created_at=datetime.now(timezone.utc),
        )

        mock_repo = AsyncMock()
        mock_repo.transfer = AsyncMock(return_value=(from_txn, to_txn))

        mock_event_bus = AsyncMock()
        mock_event_bus.publish_event = AsyncMock()

        service = self._create_service(repository=mock_repo, event_bus=mock_event_bus)
        request = self._create_transfer_request(to_wallet_id="wallet_dest")

        result = await service.transfer("wallet_source", request)

        assert result.success is True
        mock_event_bus.publish_event.assert_called_once()


class TestWalletServiceRefund:
    """
    Golden: WalletService refund operations
    """

    def _create_service(self, repository=None, event_bus=None):
        """Create WalletService with mock dependencies"""
        from microservices.wallet_service.wallet_service import WalletService
        return WalletService(
            repository=repository or MagicMock(),
            event_bus=event_bus,
        )

    def _create_refund_request(
        self,
        original_transaction_id="txn_original_123",
        amount=None,  # None = full refund
        reason="Customer requested refund",
    ):
        """Create RefundRequest"""
        from microservices.wallet_service.models import RefundRequest
        return RefundRequest(
            original_transaction_id=original_transaction_id,
            amount=amount,
            reason=reason,
        )

    @pytest.mark.asyncio
    async def test_refund_success(self):
        """GOLDEN: Valid refund succeeds"""
        from microservices.wallet_service.models import WalletTransaction, TransactionType

        mock_repo = AsyncMock()
        mock_repo.refund = AsyncMock(return_value=WalletTransaction(
            transaction_id="txn_refund_456",
            wallet_id="wallet_123",
            user_id="user_789",
            transaction_type=TransactionType.REFUND,
            amount=Decimal("50"),
            balance_before=Decimal("400"),
            balance_after=Decimal("450"),
            created_at=datetime.now(timezone.utc),
        ))

        service = self._create_service(repository=mock_repo)
        request = self._create_refund_request()

        result = await service.refund("txn_original_123", request)

        assert result.success is True
        assert result.balance == Decimal("450")

    @pytest.mark.asyncio
    async def test_refund_invalid_transaction_fails(self):
        """GOLDEN: Refund for invalid transaction fails"""
        mock_repo = AsyncMock()
        mock_repo.refund = AsyncMock(return_value=None)  # Transaction not found

        service = self._create_service(repository=mock_repo)
        request = self._create_refund_request(original_transaction_id="invalid_txn")

        result = await service.refund("invalid_txn", request)

        assert result.success is False


class TestWalletServiceBalance:
    """
    Golden: WalletService balance operations
    """

    def _create_service(self, repository=None):
        """Create WalletService with mock dependencies"""
        from microservices.wallet_service.wallet_service import WalletService
        return WalletService(repository=repository or MagicMock())

    @pytest.mark.asyncio
    async def test_get_wallet_success(self):
        """GOLDEN: Get wallet returns wallet details"""
        from microservices.wallet_service.models import WalletBalance, WalletType

        mock_repo = AsyncMock()
        mock_repo.get_wallet = AsyncMock(return_value=WalletBalance(
            wallet_id="wallet_123",
            user_id="user_456",
            balance=Decimal("1000"),
            locked_balance=Decimal("50"),
            available_balance=Decimal("950"),
            currency="CREDIT",
            wallet_type=WalletType.FIAT,
            last_updated=datetime.now(timezone.utc),
        ))

        service = self._create_service(repository=mock_repo)

        result = await service.get_wallet("wallet_123")

        assert result is not None
        assert result.wallet_id == "wallet_123"
        assert result.balance == Decimal("1000")
        assert result.available_balance == Decimal("950")

    @pytest.mark.asyncio
    async def test_get_wallet_not_found(self):
        """GOLDEN: Get non-existent wallet returns None"""
        mock_repo = AsyncMock()
        mock_repo.get_wallet = AsyncMock(return_value=None)

        service = self._create_service(repository=mock_repo)

        result = await service.get_wallet("nonexistent_wallet")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_balance_success(self):
        """GOLDEN: Get balance returns balance response"""
        from microservices.wallet_service.models import WalletBalance, WalletType

        mock_repo = AsyncMock()
        mock_repo.get_wallet = AsyncMock(return_value=WalletBalance(
            wallet_id="wallet_123",
            user_id="user_456",
            balance=Decimal("1000"),
            locked_balance=Decimal("50"),
            available_balance=Decimal("950"),
            currency="CREDIT",
            wallet_type=WalletType.FIAT,
            last_updated=datetime.now(timezone.utc),
        ))

        service = self._create_service(repository=mock_repo)

        result = await service.get_balance("wallet_123")

        assert result.success is True
        assert result.balance == Decimal("1000")

    @pytest.mark.asyncio
    async def test_get_balance_not_found(self):
        """GOLDEN: Get balance for non-existent wallet fails"""
        mock_repo = AsyncMock()
        mock_repo.get_wallet = AsyncMock(return_value=None)

        service = self._create_service(repository=mock_repo)

        result = await service.get_balance("nonexistent_wallet")

        assert result.success is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_get_user_wallets(self):
        """GOLDEN: Get user wallets returns list of wallets"""
        from microservices.wallet_service.models import WalletBalance, WalletType

        wallets = [
            WalletBalance(
                wallet_id="wallet_1",
                user_id="user_456",
                balance=Decimal("1000"),
                locked_balance=Decimal("0"),
                available_balance=Decimal("1000"),
                currency="CREDIT",
                wallet_type=WalletType.FIAT,
                last_updated=datetime.now(timezone.utc),
            ),
            WalletBalance(
                wallet_id="wallet_2",
                user_id="user_456",
                balance=Decimal("500"),
                locked_balance=Decimal("0"),
                available_balance=Decimal("500"),
                currency="ETH",
                wallet_type=WalletType.CRYPTO,
                last_updated=datetime.now(timezone.utc),
            ),
        ]

        mock_repo = AsyncMock()
        mock_repo.get_user_wallets = AsyncMock(return_value=wallets)

        service = self._create_service(repository=mock_repo)

        result = await service.get_user_wallets("user_456")

        assert len(result) == 2
        assert result[0].wallet_id == "wallet_1"
        assert result[1].wallet_id == "wallet_2"


class TestWalletServiceTransactions:
    """
    Golden: WalletService transaction history operations
    """

    def _create_service(self, repository=None):
        """Create WalletService with mock dependencies"""
        from microservices.wallet_service.wallet_service import WalletService
        return WalletService(repository=repository or MagicMock())

    @pytest.mark.asyncio
    async def test_get_transactions_success(self):
        """GOLDEN: Get transactions returns filtered list"""
        from microservices.wallet_service.models import (
            WalletTransaction,
            TransactionType,
            TransactionFilter,
        )

        transactions = [
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
            WalletTransaction(
                transaction_id="txn_2",
                wallet_id="wallet_123",
                user_id="user_456",
                transaction_type=TransactionType.CONSUME,
                amount=Decimal("25"),
                balance_before=Decimal("100"),
                balance_after=Decimal("75"),
                created_at=datetime.now(timezone.utc),
            ),
        ]

        mock_repo = AsyncMock()
        mock_repo.get_transactions = AsyncMock(return_value=transactions)

        service = self._create_service(repository=mock_repo)

        filter_params = TransactionFilter(wallet_id="wallet_123", limit=50, offset=0)
        result = await service.get_transactions(filter_params)

        assert len(result) == 2
        assert result[0].transaction_id == "txn_1"
        assert result[1].transaction_type == TransactionType.CONSUME

    @pytest.mark.asyncio
    async def test_get_transactions_empty(self):
        """GOLDEN: Get transactions with no results returns empty list"""
        from microservices.wallet_service.models import TransactionFilter

        mock_repo = AsyncMock()
        mock_repo.get_transactions = AsyncMock(return_value=[])

        service = self._create_service(repository=mock_repo)

        filter_params = TransactionFilter(wallet_id="empty_wallet", limit=50, offset=0)
        result = await service.get_transactions(filter_params)

        assert result == []


class TestWalletServiceStatistics:
    """
    Golden: WalletService statistics operations
    """

    def _create_service(self, repository=None):
        """Create WalletService with mock dependencies"""
        from microservices.wallet_service.wallet_service import WalletService
        return WalletService(repository=repository or MagicMock())

    @pytest.mark.asyncio
    async def test_get_statistics_success(self):
        """GOLDEN: Get statistics returns aggregated data"""
        from microservices.wallet_service.models import WalletStatistics

        mock_repo = AsyncMock()
        mock_repo.get_wallet_statistics = AsyncMock(return_value=WalletStatistics(
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

        service = self._create_service(repository=mock_repo)

        result = await service.get_statistics("wallet_123")

        assert result is not None
        assert result.wallet_id == "wallet_123"
        assert result.transaction_count == 47

    @pytest.mark.asyncio
    async def test_get_statistics_not_found(self):
        """GOLDEN: Get statistics for non-existent wallet returns None"""
        mock_repo = AsyncMock()
        mock_repo.get_wallet_statistics = AsyncMock(return_value=None)

        service = self._create_service(repository=mock_repo)

        result = await service.get_statistics("nonexistent_wallet")

        assert result is None
