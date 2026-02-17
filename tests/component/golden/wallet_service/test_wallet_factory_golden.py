"""
Wallet Service Factory Component Tests

Tests the factory module for creating service instances with proper dependency injection.
Verifies the DI pattern works correctly for production and testing scenarios.

Usage:
    pytest tests/component/golden/wallet_service/test_wallet_factory_golden.py -v
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

pytestmark = [pytest.mark.component, pytest.mark.golden]


class TestWalletServiceFactory:
    """
    Golden: Factory functions for WalletService creation
    """

    def test_create_wallet_service_with_defaults(self):
        """GOLDEN: create_wallet_service returns configured WalletService"""
        with patch('microservices.wallet_service.factory.WalletRepository') as MockRepo:
            with patch('microservices.wallet_service.factory.AccountClient') as MockClient:
                MockRepo.return_value = MagicMock()
                MockClient.return_value = MagicMock()

                from microservices.wallet_service.factory import create_wallet_service

                service = create_wallet_service()

                assert service is not None
                assert service.repository is not None
                assert service.account_client is not None

    def test_create_wallet_service_with_custom_dependencies(self):
        """GOLDEN: create_wallet_service accepts custom dependencies"""
        with patch('microservices.wallet_service.factory.WalletRepository') as MockRepo:
            MockRepo.return_value = MagicMock()

            from microservices.wallet_service.factory import create_wallet_service

            custom_event_bus = MagicMock()
            custom_account_client = MagicMock()

            service = create_wallet_service(
                event_bus=custom_event_bus,
                account_client=custom_account_client,
            )

            assert service is not None
            assert service.event_bus == custom_event_bus
            assert service.account_client == custom_account_client

    def test_create_wallet_service_with_config(self):
        """GOLDEN: create_wallet_service accepts config parameter"""
        with patch('microservices.wallet_service.factory.WalletRepository') as MockRepo:
            with patch('microservices.wallet_service.factory.AccountClient') as MockClient:
                MockRepo.return_value = MagicMock()
                MockClient.return_value = MagicMock()

                from microservices.wallet_service.factory import create_wallet_service

                mock_config = MagicMock()
                service = create_wallet_service(config=mock_config)

                assert service is not None
                MockRepo.assert_called_once_with(config=mock_config)


class TestWalletRepositoryFactory:
    """
    Golden: Factory functions for WalletRepository creation
    """

    def test_create_wallet_repository(self):
        """GOLDEN: create_wallet_repository returns configured WalletRepository"""
        with patch('microservices.wallet_service.factory.WalletRepository') as MockRepo:
            MockRepo.return_value = MagicMock()

            from microservices.wallet_service.factory import create_wallet_repository

            repository = create_wallet_repository()

            assert repository is not None
            MockRepo.assert_called_once()

    def test_create_wallet_repository_with_config(self):
        """GOLDEN: create_wallet_repository accepts config parameter"""
        with patch('microservices.wallet_service.factory.WalletRepository') as MockRepo:
            MockRepo.return_value = MagicMock()

            from microservices.wallet_service.factory import create_wallet_repository

            mock_config = MagicMock()
            repository = create_wallet_repository(config=mock_config)

            assert repository is not None
            MockRepo.assert_called_once_with(config=mock_config)


class TestWalletServiceDependencyInjection:
    """
    Golden: Dependency injection pattern for WalletService
    """

    def test_service_with_mock_repository(self):
        """GOLDEN: WalletService works with injected mock repository"""
        from microservices.wallet_service.wallet_service import WalletService

        mock_repo = MagicMock()
        service = WalletService(repository=mock_repo)

        assert service.repository == mock_repo
        assert service.repo == mock_repo  # Backward compat alias

    def test_service_with_mock_event_bus(self):
        """GOLDEN: WalletService works with injected mock event_bus"""
        from microservices.wallet_service.wallet_service import WalletService

        mock_repo = MagicMock()
        mock_event_bus = MagicMock()
        service = WalletService(repository=mock_repo, event_bus=mock_event_bus)

        assert service.event_bus == mock_event_bus

    def test_service_with_mock_account_client(self):
        """GOLDEN: WalletService works with injected mock account_client"""
        from microservices.wallet_service.wallet_service import WalletService

        mock_repo = MagicMock()
        mock_account_client = MagicMock()
        service = WalletService(repository=mock_repo, account_client=mock_account_client)

        assert service.account_client == mock_account_client

    def test_service_accepts_all_dependencies(self):
        """GOLDEN: WalletService accepts all dependencies at once"""
        from microservices.wallet_service.wallet_service import WalletService

        mock_repo = MagicMock()
        mock_event_bus = MagicMock()
        mock_account_client = MagicMock()

        service = WalletService(
            repository=mock_repo,
            event_bus=mock_event_bus,
            account_client=mock_account_client,
        )

        assert service.repository == mock_repo
        assert service.event_bus == mock_event_bus
        assert service.account_client == mock_account_client


class TestWalletProtocols:
    """
    Golden: Protocol interfaces for WalletService dependencies
    """

    def test_repository_protocol_has_required_methods(self):
        """GOLDEN: WalletRepositoryProtocol defines required methods"""
        from microservices.wallet_service.protocols import WalletRepositoryProtocol
        import inspect

        # Get all method names from protocol
        methods = [
            name for name, method in inspect.getmembers(WalletRepositoryProtocol)
            if not name.startswith('_') and callable(method)
        ]

        # Verify required methods exist
        expected_methods = [
            'create_wallet',
            'get_wallet',
            'get_user_wallets',
            'deposit',
            'withdraw',
            'consume',
            'transfer',
            'refund',
            'get_transactions',
            'get_wallet_statistics',
        ]

        for method in expected_methods:
            assert hasattr(WalletRepositoryProtocol, method), f"Missing method: {method}"

    def test_account_client_protocol_has_required_methods(self):
        """GOLDEN: AccountClientProtocol defines required methods"""
        from microservices.wallet_service.protocols import AccountClientProtocol
        import inspect

        # Verify required methods
        assert hasattr(AccountClientProtocol, 'get_account')
        assert hasattr(AccountClientProtocol, 'validate_user_exists')

    def test_event_bus_protocol_has_required_methods(self):
        """GOLDEN: EventBusProtocol defines required methods"""
        from microservices.wallet_service.protocols import EventBusProtocol

        # Verify required methods
        assert hasattr(EventBusProtocol, 'publish_event')


class TestWalletServiceIntegrationReadiness:
    """
    Golden: WalletService integration with real dependencies
    """

    @pytest.mark.asyncio
    async def test_service_deposit_with_mock_chain(self):
        """GOLDEN: Deposit operation works through full mock chain"""
        from microservices.wallet_service.wallet_service import WalletService
        from microservices.wallet_service.models import (
            DepositRequest,
            WalletTransaction,
            TransactionType,
        )

        # Setup mock repository
        mock_repo = AsyncMock()
        mock_repo.deposit = AsyncMock(return_value=WalletTransaction(
            transaction_id="txn_test_123",
            wallet_id="wallet_test_456",
            user_id="user_test_789",
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal("100"),
            balance_before=Decimal("0"),
            balance_after=Decimal("100"),
            created_at=datetime.now(timezone.utc),
        ))

        # Setup mock event bus
        mock_event_bus = AsyncMock()
        mock_event_bus.publish_event = AsyncMock()

        # Create service with mocks
        service = WalletService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        # Execute deposit
        request = DepositRequest(
            amount=Decimal("100"),
            description="Test deposit",
            reference_id="payment_123",
        )

        result = await service.deposit("wallet_test_456", request)

        # Verify full chain executed
        assert result.success is True
        mock_repo.deposit.assert_called_once()
        mock_event_bus.publish_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_transfer_with_mock_chain(self):
        """GOLDEN: Transfer operation works through full mock chain"""
        from microservices.wallet_service.wallet_service import WalletService
        from microservices.wallet_service.models import (
            TransferRequest,
            WalletTransaction,
            TransactionType,
        )

        # Setup mock transactions
        from_txn = WalletTransaction(
            transaction_id="txn_from_123",
            wallet_id="wallet_source",
            user_id="user_1",
            transaction_type=TransactionType.TRANSFER,
            amount=Decimal("50"),
            balance_before=Decimal("200"),
            balance_after=Decimal("150"),
            created_at=datetime.now(timezone.utc),
        )
        to_txn = WalletTransaction(
            transaction_id="txn_to_456",
            wallet_id="wallet_dest",
            user_id="user_2",
            transaction_type=TransactionType.TRANSFER,
            amount=Decimal("50"),
            balance_before=Decimal("100"),
            balance_after=Decimal("150"),
            created_at=datetime.now(timezone.utc),
        )

        # Setup mock repository
        mock_repo = AsyncMock()
        mock_repo.transfer = AsyncMock(return_value=(from_txn, to_txn))

        # Setup mock event bus
        mock_event_bus = AsyncMock()
        mock_event_bus.publish_event = AsyncMock()

        # Create service with mocks
        service = WalletService(
            repository=mock_repo,
            event_bus=mock_event_bus,
        )

        # Execute transfer
        request = TransferRequest(
            to_wallet_id="wallet_dest",
            amount=Decimal("50"),
            description="Test transfer",
        )

        result = await service.transfer("wallet_source", request)

        # Verify full chain executed
        assert result.success is True
        assert result.balance == Decimal("150")
        mock_repo.transfer.assert_called_once()
        mock_event_bus.publish_event.assert_called_once()


class TestDataContractValidation:
    """
    Golden: Validation using data contracts
    """

    def test_wallet_create_contract_validation(self):
        """GOLDEN: WalletCreateRequestContract validates correctly"""
        from tests.contracts.wallet.data_contract import (
            WalletCreateRequestContract,
            WalletTestDataFactory,
        )

        # Valid request
        request = WalletTestDataFactory.make_create_wallet_request()
        assert request.user_id is not None
        assert request.wallet_type in ["fiat", "crypto", "hybrid"]
        assert request.initial_balance >= Decimal("0")

    def test_deposit_contract_validation(self):
        """GOLDEN: DepositRequestContract validates correctly"""
        from tests.contracts.wallet.data_contract import (
            DepositRequestContract,
            WalletTestDataFactory,
        )

        # Valid request
        request = WalletTestDataFactory.make_deposit_request()
        assert request.amount > Decimal("0")

    def test_invalid_deposit_zero_amount_rejected(self):
        """GOLDEN: DepositRequestContract rejects zero amount"""
        from tests.contracts.wallet.data_contract import DepositRequestContract
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DepositRequestContract(
                amount=Decimal("0"),
                description="Invalid",
            )

    def test_refund_contract_requires_reason(self):
        """GOLDEN: RefundRequestContract requires reason"""
        from tests.contracts.wallet.data_contract import RefundRequestContract
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RefundRequestContract(
                original_transaction_id="txn_123",
                # Missing reason
            )
