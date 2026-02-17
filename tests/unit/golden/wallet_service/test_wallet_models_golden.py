"""
Unit Golden Tests: Wallet Service Models

Tests model validation and serialization for wallet operations, including
traditional wallet transactions and credit account management.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pydantic import ValidationError

from microservices.wallet_service.models import (
    # Enums
    TransactionType,
    WalletType,
    BlockchainNetwork,
    CreditType,
    CreditTransactionType,
    # Core Models
    WalletBalance,
    WalletTransaction,
    CreditAccount,
    CreditTransaction,
    # Request Models
    WalletCreate,
    WalletUpdate,
    TransactionCreate,
    DepositRequest,
    WithdrawRequest,
    ConsumeRequest,
    TransferRequest,
    RefundRequest,
    BlockchainSyncRequest,
    PurchaseCreditsRequest,
    ConsumeCreditsRequest,
    # Response Models
    WalletResponse,
    WalletStatistics,
    PurchaseCreditsResponse,
    ConsumeCreditsResponse,
    CreditBalanceResponse,
    CreditHistoryResponse,
    # Filter Models
    TransactionFilter,
    BlockchainIntegration,
)


class TestTransactionType:
    """Test TransactionType enum"""

    def test_transaction_type_values(self):
        """Test all transaction type values are defined"""
        assert TransactionType.DEPOSIT.value == "deposit"
        assert TransactionType.WITHDRAW.value == "withdraw"
        assert TransactionType.CONSUME.value == "consume"
        assert TransactionType.REFUND.value == "refund"
        assert TransactionType.TRANSFER.value == "transfer"
        assert TransactionType.REWARD.value == "reward"
        assert TransactionType.FEE.value == "fee"
        assert TransactionType.BLOCKCHAIN_IN.value == "blockchain_in"
        assert TransactionType.BLOCKCHAIN_OUT.value == "blockchain_out"

    def test_transaction_type_comparison(self):
        """Test transaction type comparison"""
        assert TransactionType.DEPOSIT.value == "deposit"
        assert TransactionType.DEPOSIT != TransactionType.WITHDRAW
        assert TransactionType.TRANSFER == TransactionType.TRANSFER


class TestWalletType:
    """Test WalletType enum"""

    def test_wallet_type_values(self):
        """Test all wallet type values"""
        assert WalletType.FIAT.value == "fiat"
        assert WalletType.CRYPTO.value == "crypto"
        assert WalletType.HYBRID.value == "hybrid"

    def test_wallet_type_comparison(self):
        """Test wallet type comparison"""
        assert WalletType.FIAT != WalletType.CRYPTO
        assert WalletType.CRYPTO == WalletType.CRYPTO


class TestBlockchainNetwork:
    """Test BlockchainNetwork enum"""

    def test_blockchain_network_values(self):
        """Test all blockchain network values"""
        assert BlockchainNetwork.ETHEREUM.value == "ethereum"
        assert BlockchainNetwork.BINANCE_SMART_CHAIN.value == "bsc"
        assert BlockchainNetwork.POLYGON.value == "polygon"
        assert BlockchainNetwork.ISA_CHAIN.value == "isa_chain"
        assert BlockchainNetwork.TESTNET.value == "testnet"


class TestCreditType:
    """Test CreditType enum"""

    def test_credit_type_values(self):
        """Test all credit type values"""
        assert CreditType.PURCHASED.value == "purchased"
        assert CreditType.BONUS.value == "bonus"
        assert CreditType.REFERRAL.value == "referral"
        assert CreditType.PROMOTIONAL.value == "promotional"

    def test_credit_type_priority_context(self):
        """Test credit type values for priority consumption"""
        # Document priority: PURCHASED=100, BONUS=200, REFERRAL=200, PROMOTIONAL=300
        assert CreditType.PURCHASED == CreditType.PURCHASED
        assert CreditType.BONUS != CreditType.PURCHASED


class TestCreditTransactionType:
    """Test CreditTransactionType enum"""

    def test_credit_transaction_type_values(self):
        """Test all credit transaction type values"""
        assert CreditTransactionType.CREDIT_PURCHASE.value == "credit_purchase"
        assert CreditTransactionType.CREDIT_CONSUME.value == "credit_consume"
        assert CreditTransactionType.CREDIT_REFUND.value == "credit_refund"
        assert CreditTransactionType.CREDIT_EXPIRE.value == "credit_expire"
        assert CreditTransactionType.CREDIT_TRANSFER.value == "credit_transfer"
        assert CreditTransactionType.CREDIT_BONUS.value == "credit_bonus"


class TestWalletBalance:
    """Test WalletBalance model"""

    def test_wallet_balance_creation_minimal(self):
        """Test wallet balance creation with minimal fields"""
        now = datetime.now(timezone.utc)

        balance = WalletBalance(
            wallet_id="wallet_123",
            user_id="user_456",
            balance=Decimal("100.50"),
            available_balance=Decimal("100.50"),
            last_updated=now,
        )

        assert balance.wallet_id == "wallet_123"
        assert balance.user_id == "user_456"
        assert balance.balance == Decimal("100.50")
        assert balance.locked_balance == Decimal("0")
        assert balance.available_balance == Decimal("100.50")
        assert balance.currency == "CREDIT"
        assert balance.wallet_type == WalletType.FIAT
        assert balance.blockchain_address is None

    def test_wallet_balance_with_locked_funds(self):
        """Test wallet balance with locked funds"""
        now = datetime.now(timezone.utc)

        balance = WalletBalance(
            wallet_id="wallet_123",
            user_id="user_456",
            balance=Decimal("1000.00"),
            locked_balance=Decimal("250.00"),
            available_balance=Decimal("750.00"),
            last_updated=now,
        )

        assert balance.balance == Decimal("1000.00")
        assert balance.locked_balance == Decimal("250.00")
        assert balance.available_balance == Decimal("750.00")

    def test_wallet_balance_with_blockchain_info(self):
        """Test wallet balance with blockchain integration"""
        now = datetime.now(timezone.utc)

        balance = WalletBalance(
            wallet_id="wallet_crypto_123",
            user_id="user_456",
            balance=Decimal("0.5"),
            available_balance=Decimal("0.5"),
            currency="ETH",
            wallet_type=WalletType.CRYPTO,
            blockchain_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            blockchain_network=BlockchainNetwork.ETHEREUM,
            on_chain_balance=Decimal("0.5"),
            sync_status="synced",
            last_updated=now,
        )

        assert balance.wallet_type == WalletType.CRYPTO
        assert balance.currency == "ETH"
        assert balance.blockchain_address == "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        assert balance.blockchain_network == BlockchainNetwork.ETHEREUM
        assert balance.on_chain_balance == Decimal("0.5")
        assert balance.sync_status == "synced"

    def test_wallet_balance_negative_validation(self):
        """Test that negative balance values raise ValidationError"""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            WalletBalance(
                wallet_id="wallet_123",
                user_id="user_456",
                balance=Decimal("-10.00"),
                available_balance=Decimal("0"),
                last_updated=now,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "balance" for err in errors)


class TestWalletTransaction:
    """Test WalletTransaction model"""

    def test_wallet_transaction_creation_minimal(self):
        """Test transaction creation with minimal fields"""
        now = datetime.now(timezone.utc)

        transaction = WalletTransaction(
            transaction_id="txn_123",
            wallet_id="wallet_456",
            user_id="user_789",
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal("50.00"),
            balance_before=Decimal("100.00"),
            balance_after=Decimal("150.00"),
            created_at=now,
        )

        assert transaction.transaction_id == "txn_123"
        assert transaction.wallet_id == "wallet_456"
        assert transaction.user_id == "user_789"
        assert transaction.transaction_type == TransactionType.DEPOSIT
        assert transaction.amount == Decimal("50.00")
        assert transaction.balance_before == Decimal("100.00")
        assert transaction.balance_after == Decimal("150.00")
        assert transaction.fee == Decimal("0")

    def test_wallet_transaction_with_fee(self):
        """Test transaction with fee"""
        now = datetime.now(timezone.utc)

        transaction = WalletTransaction(
            transaction_id="txn_fee_123",
            wallet_id="wallet_456",
            user_id="user_789",
            transaction_type=TransactionType.WITHDRAW,
            amount=Decimal("100.00"),
            fee=Decimal("2.50"),
            balance_before=Decimal("200.00"),
            balance_after=Decimal("97.50"),
            created_at=now,
        )

        assert transaction.amount == Decimal("100.00")
        assert transaction.fee == Decimal("2.50")
        assert transaction.balance_after == Decimal("97.50")

    def test_wallet_transaction_transfer(self):
        """Test transfer transaction between wallets"""
        now = datetime.now(timezone.utc)

        transaction = WalletTransaction(
            transaction_id="txn_transfer_123",
            wallet_id="wallet_from_123",
            user_id="user_789",
            transaction_type=TransactionType.TRANSFER,
            amount=Decimal("25.00"),
            balance_before=Decimal("100.00"),
            balance_after=Decimal("75.00"),
            from_wallet_id="wallet_from_123",
            to_wallet_id="wallet_to_456",
            description="Transfer to friend",
            created_at=now,
        )

        assert transaction.transaction_type == TransactionType.TRANSFER
        assert transaction.from_wallet_id == "wallet_from_123"
        assert transaction.to_wallet_id == "wallet_to_456"
        assert transaction.description == "Transfer to friend"

    def test_wallet_transaction_blockchain(self):
        """Test blockchain transaction"""
        now = datetime.now(timezone.utc)

        transaction = WalletTransaction(
            transaction_id="txn_blockchain_123",
            wallet_id="wallet_crypto_456",
            user_id="user_789",
            transaction_type=TransactionType.BLOCKCHAIN_OUT,
            amount=Decimal("0.1"),
            balance_before=Decimal("0.5"),
            balance_after=Decimal("0.39"),
            gas_fee=Decimal("0.01"),
            blockchain_tx_hash="0x1234567890abcdef",
            blockchain_network=BlockchainNetwork.ETHEREUM,
            blockchain_status="confirmed",
            blockchain_confirmations=12,
            created_at=now,
        )

        assert transaction.transaction_type == TransactionType.BLOCKCHAIN_OUT
        assert transaction.blockchain_tx_hash == "0x1234567890abcdef"
        assert transaction.blockchain_network == BlockchainNetwork.ETHEREUM
        assert transaction.blockchain_status == "confirmed"
        assert transaction.blockchain_confirmations == 12
        assert transaction.gas_fee == Decimal("0.01")

    def test_wallet_transaction_with_metadata(self):
        """Test transaction with metadata"""
        now = datetime.now(timezone.utc)
        metadata = {"order_id": "order_123", "product": "Premium Plan"}

        transaction = WalletTransaction(
            transaction_id="txn_meta_123",
            wallet_id="wallet_456",
            user_id="user_789",
            transaction_type=TransactionType.CONSUME,
            amount=Decimal("10.00"),
            balance_before=Decimal("100.00"),
            balance_after=Decimal("90.00"),
            reference_id="order_123",
            usage_record_id=12345,
            metadata=metadata,
            created_at=now,
        )

        assert transaction.reference_id == "order_123"
        assert transaction.usage_record_id == 12345
        assert transaction.metadata == metadata


class TestCreditAccount:
    """Test CreditAccount model"""

    def test_credit_account_creation_minimal(self):
        """Test credit account creation with minimal fields"""
        account = CreditAccount(
            credit_account_id="ca_123",
            user_id="user_456",
            credit_type=CreditType.PURCHASED,
        )

        assert account.credit_account_id == "ca_123"
        assert account.user_id == "user_456"
        assert account.credit_type == CreditType.PURCHASED
        assert account.balance == 0
        assert account.total_credited == 0
        assert account.total_consumed == 0
        assert account.is_expired is False
        assert account.is_active is True
        assert account.consumption_priority == 100

    def test_credit_account_purchased_with_balance(self):
        """Test purchased credit account with balance"""
        now = datetime.now(timezone.utc)

        account = CreditAccount(
            credit_account_id="ca_purchased_123",
            user_id="user_456",
            wallet_id="wallet_789",
            credit_type=CreditType.PURCHASED,
            balance=500000,
            total_credited=500000,
            total_consumed=0,
            purchase_amount_usd=Decimal("5.00"),
            payment_transaction_id="pay_123",
            consumption_priority=100,
            description="Purchased 500,000 credits ($5.00)",
            created_at=now,
        )

        assert account.credit_type == CreditType.PURCHASED
        assert account.balance == 500000
        assert account.purchase_amount_usd == Decimal("5.00")
        assert account.payment_transaction_id == "pay_123"
        assert account.consumption_priority == 100
        assert account.expires_at is None  # Never expires

    def test_credit_account_bonus_with_expiration(self):
        """Test bonus credit account with expiration"""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=30)

        account = CreditAccount(
            credit_account_id="ca_bonus_123",
            user_id="user_456",
            credit_type=CreditType.BONUS,
            balance=100000,
            total_credited=100000,
            total_consumed=0,
            expires_at=expires,
            consumption_priority=200,
            description="Welcome bonus credits",
            created_at=now,
        )

        assert account.credit_type == CreditType.BONUS
        assert account.balance == 100000
        assert account.expires_at == expires
        assert account.consumption_priority == 200
        assert account.is_expired is False

    def test_credit_account_promotional_expired(self):
        """Test promotional credit account that has expired"""
        now = datetime.now(timezone.utc)
        expired_date = now - timedelta(days=1)

        account = CreditAccount(
            credit_account_id="ca_promo_123",
            user_id="user_456",
            credit_type=CreditType.PROMOTIONAL,
            balance=0,
            total_credited=50000,
            total_consumed=50000,
            expires_at=expired_date,
            is_expired=True,
            is_active=False,
            consumption_priority=300,
            created_at=now - timedelta(days=60),
        )

        assert account.credit_type == CreditType.PROMOTIONAL
        assert account.is_expired is True
        assert account.is_active is False
        assert account.balance == 0

    def test_credit_account_with_organization(self):
        """Test credit account with organization ID"""
        account = CreditAccount(
            credit_account_id="ca_org_123",
            user_id="user_456",
            organization_id="org_789",
            credit_type=CreditType.PURCHASED,
            balance=1000000,
            total_credited=1000000,
        )

        assert account.organization_id == "org_789"
        assert account.balance == 1000000

    def test_credit_account_negative_balance_validation(self):
        """Test that negative balance raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            CreditAccount(
                credit_account_id="ca_invalid_123",
                user_id="user_456",
                credit_type=CreditType.PURCHASED,
                balance=-1000,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "balance" for err in errors)


class TestCreditTransaction:
    """Test CreditTransaction model"""

    def test_credit_transaction_purchase(self):
        """Test credit purchase transaction"""
        now = datetime.now(timezone.utc)

        transaction = CreditTransaction(
            transaction_id="ctx_123",
            credit_account_id="ca_456",
            user_id="user_789",
            transaction_type=CreditTransactionType.CREDIT_PURCHASE,
            credits_amount=500000,
            balance_before=0,
            balance_after=500000,
            usd_equivalent=Decimal("5.00"),
            payment_method="credit_card",
            payment_transaction_id="pay_123",
            description="Purchased 500,000 credits",
            created_at=now,
        )

        assert transaction.transaction_id == "ctx_123"
        assert transaction.transaction_type == CreditTransactionType.CREDIT_PURCHASE
        assert transaction.credits_amount == 500000
        assert transaction.balance_before == 0
        assert transaction.balance_after == 500000
        assert transaction.usd_equivalent == Decimal("5.00")
        assert transaction.payment_transaction_id == "pay_123"

    def test_credit_transaction_consume(self):
        """Test credit consumption transaction"""
        now = datetime.now(timezone.utc)

        transaction = CreditTransaction(
            transaction_id="ctx_consume_123",
            credit_account_id="ca_456",
            user_id="user_789",
            transaction_type=CreditTransactionType.CREDIT_CONSUME,
            credits_amount=-1000,
            balance_before=500000,
            balance_after=499000,
            usd_equivalent=Decimal("0.01"),
            service_type="photo_storage",
            usage_record_id="usage_123",
            reference_type="storage",
            reference_id="storage_123",
            description="Used credits for photo storage",
            created_at=now,
        )

        assert transaction.transaction_type == CreditTransactionType.CREDIT_CONSUME
        assert transaction.credits_amount == -1000
        assert transaction.balance_after == 499000
        assert transaction.service_type == "photo_storage"
        assert transaction.usage_record_id == "usage_123"

    def test_credit_transaction_refund(self):
        """Test credit refund transaction"""
        now = datetime.now(timezone.utc)

        transaction = CreditTransaction(
            transaction_id="ctx_refund_123",
            credit_account_id="ca_456",
            user_id="user_789",
            transaction_type=CreditTransactionType.CREDIT_REFUND,
            credits_amount=50000,
            balance_before=450000,
            balance_after=500000,
            usd_equivalent=Decimal("0.50"),
            reference_type="order",
            reference_id="order_123",
            description="Refund for cancelled order",
            created_at=now,
        )

        assert transaction.transaction_type == CreditTransactionType.CREDIT_REFUND
        assert transaction.credits_amount == 50000
        assert transaction.balance_after == 500000

    def test_credit_transaction_expire(self):
        """Test credit expiration transaction"""
        now = datetime.now(timezone.utc)

        transaction = CreditTransaction(
            transaction_id="ctx_expire_123",
            credit_account_id="ca_promo_456",
            user_id="user_789",
            transaction_type=CreditTransactionType.CREDIT_EXPIRE,
            credits_amount=-10000,
            balance_before=10000,
            balance_after=0,
            description="Promotional credits expired",
            status="completed",
            created_at=now,
        )

        assert transaction.transaction_type == CreditTransactionType.CREDIT_EXPIRE
        assert transaction.credits_amount == -10000
        assert transaction.balance_after == 0
        assert transaction.status == "completed"


class TestWalletCreate:
    """Test WalletCreate request model"""

    def test_wallet_create_minimal(self):
        """Test wallet creation request with minimal fields"""
        request = WalletCreate(
            user_id="user_123",
        )

        assert request.user_id == "user_123"
        assert request.wallet_type == WalletType.FIAT
        assert request.initial_balance == Decimal("0")
        assert request.currency == "CREDIT"
        assert request.blockchain_network is None

    def test_wallet_create_with_initial_balance(self):
        """Test wallet creation with initial balance"""
        request = WalletCreate(
            user_id="user_123",
            initial_balance=Decimal("100.00"),
            currency="CREDIT",
        )

        assert request.initial_balance == Decimal("100.00")
        assert request.currency == "CREDIT"

    def test_wallet_create_crypto(self):
        """Test crypto wallet creation"""
        request = WalletCreate(
            user_id="user_123",
            wallet_type=WalletType.CRYPTO,
            currency="ETH",
            blockchain_network=BlockchainNetwork.ETHEREUM,
            blockchain_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            metadata={"description": "Ethereum wallet"},
        )

        assert request.wallet_type == WalletType.CRYPTO
        assert request.currency == "ETH"
        assert request.blockchain_network == BlockchainNetwork.ETHEREUM
        assert request.blockchain_address == "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"

    def test_wallet_create_negative_balance_validation(self):
        """Test that negative initial balance raises ValidationError"""
        with pytest.raises(ValidationError):
            WalletCreate(
                user_id="user_123",
                initial_balance=Decimal("-50.00"),
            )


class TestWalletUpdate:
    """Test WalletUpdate request model"""

    def test_wallet_update_blockchain_info(self):
        """Test wallet update with blockchain information"""
        request = WalletUpdate(
            blockchain_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            blockchain_network=BlockchainNetwork.ETHEREUM,
        )

        assert request.blockchain_address == "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        assert request.blockchain_network == BlockchainNetwork.ETHEREUM

    def test_wallet_update_metadata(self):
        """Test wallet update with metadata"""
        metadata = {"label": "Main Wallet", "category": "personal"}
        request = WalletUpdate(metadata=metadata)

        assert request.metadata == metadata


class TestDepositRequest:
    """Test DepositRequest model"""

    def test_deposit_request_minimal(self):
        """Test deposit request with minimal fields"""
        request = DepositRequest(
            amount=Decimal("50.00"),
        )

        assert request.amount == Decimal("50.00")
        assert request.description is None
        assert request.reference_id is None

    def test_deposit_request_with_details(self):
        """Test deposit request with full details"""
        request = DepositRequest(
            amount=Decimal("100.00"),
            description="Payment received",
            reference_id="pay_123",
            metadata={"payment_method": "credit_card"},
        )

        assert request.amount == Decimal("100.00")
        assert request.description == "Payment received"
        assert request.reference_id == "pay_123"
        assert request.metadata == {"payment_method": "credit_card"}

    def test_deposit_request_zero_amount_validation(self):
        """Test that zero amount raises ValidationError"""
        with pytest.raises(ValidationError):
            DepositRequest(amount=Decimal("0"))

    def test_deposit_request_negative_amount_validation(self):
        """Test that negative amount raises ValidationError"""
        with pytest.raises(ValidationError):
            DepositRequest(amount=Decimal("-10.00"))


class TestWithdrawRequest:
    """Test WithdrawRequest model"""

    def test_withdraw_request_minimal(self):
        """Test withdraw request with minimal fields"""
        request = WithdrawRequest(
            amount=Decimal("25.00"),
        )

        assert request.amount == Decimal("25.00")
        assert request.description is None
        assert request.destination is None

    def test_withdraw_request_with_destination(self):
        """Test withdraw request with destination"""
        request = WithdrawRequest(
            amount=Decimal("100.00"),
            description="Withdraw to bank",
            destination="bank_account_123",
            metadata={"bank": "Chase", "account": "****1234"},
        )

        assert request.amount == Decimal("100.00")
        assert request.destination == "bank_account_123"
        assert request.metadata["bank"] == "Chase"

    def test_withdraw_request_blockchain_destination(self):
        """Test withdraw request to blockchain address"""
        request = WithdrawRequest(
            amount=Decimal("0.5"),
            description="Withdraw to wallet",
            destination="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        )

        assert request.destination == "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"


class TestTransferRequest:
    """Test TransferRequest model"""

    def test_transfer_request_minimal(self):
        """Test transfer request with minimal fields"""
        request = TransferRequest(
            to_wallet_id="wallet_to_123",
            amount=Decimal("30.00"),
        )

        assert request.to_wallet_id == "wallet_to_123"
        assert request.amount == Decimal("30.00")
        assert request.description is None

    def test_transfer_request_with_description(self):
        """Test transfer request with description"""
        request = TransferRequest(
            to_wallet_id="wallet_friend_456",
            amount=Decimal("50.00"),
            description="Payment for dinner",
            metadata={"occasion": "birthday"},
        )

        assert request.to_wallet_id == "wallet_friend_456"
        assert request.amount == Decimal("50.00")
        assert request.description == "Payment for dinner"
        assert request.metadata == {"occasion": "birthday"}

    def test_transfer_request_validation(self):
        """Test transfer request amount validation"""
        with pytest.raises(ValidationError):
            TransferRequest(
                to_wallet_id="wallet_123",
                amount=Decimal("0"),
            )


class TestRefundRequest:
    """Test RefundRequest model"""

    def test_refund_request_full_refund(self):
        """Test full refund request"""
        request = RefundRequest(
            original_transaction_id="txn_123",
            reason="Customer requested refund",
        )

        assert request.original_transaction_id == "txn_123"
        assert request.amount is None  # Full refund
        assert request.reason == "Customer requested refund"

    def test_refund_request_partial_refund(self):
        """Test partial refund request"""
        request = RefundRequest(
            original_transaction_id="txn_456",
            amount=Decimal("25.00"),
            reason="Partial refund for damaged item",
            metadata={"item": "product_123"},
        )

        assert request.original_transaction_id == "txn_456"
        assert request.amount == Decimal("25.00")
        assert request.reason == "Partial refund for damaged item"


class TestPurchaseCreditsRequest:
    """Test PurchaseCreditsRequest model"""

    def test_purchase_credits_request_minimal(self):
        """Test purchase credits request with minimal fields"""
        request = PurchaseCreditsRequest(
            user_id="user_123",
            credits_amount=500000,
            payment_method_id="pm_card_123",
        )

        assert request.user_id == "user_123"
        assert request.credits_amount == 500000
        assert request.payment_method_id == "pm_card_123"
        assert request.organization_id is None

    def test_purchase_credits_request_with_organization(self):
        """Test purchase credits for organization"""
        request = PurchaseCreditsRequest(
            user_id="user_123",
            organization_id="org_456",
            credits_amount=1000000,
            payment_method_id="pm_card_123",
            metadata={"plan": "business"},
        )

        assert request.organization_id == "org_456"
        assert request.credits_amount == 1000000
        assert request.metadata == {"plan": "business"}

    def test_purchase_credits_request_validation(self):
        """Test that zero or negative credits amount raises ValidationError"""
        with pytest.raises(ValidationError):
            PurchaseCreditsRequest(
                user_id="user_123",
                credits_amount=0,
                payment_method_id="pm_123",
            )


class TestConsumeCreditsRequest:
    """Test ConsumeCreditsRequest model"""

    def test_consume_credits_request_minimal(self):
        """Test consume credits request with minimal fields"""
        request = ConsumeCreditsRequest(
            user_id="user_123",
            credits_amount=1000,
            service_type="photo_storage",
        )

        assert request.user_id == "user_123"
        assert request.credits_amount == 1000
        assert request.service_type == "photo_storage"
        assert request.organization_id is None

    def test_consume_credits_request_with_details(self):
        """Test consume credits request with full details"""
        request = ConsumeCreditsRequest(
            user_id="user_123",
            organization_id="org_456",
            credits_amount=5000,
            service_type="ai_processing",
            usage_record_id="usage_789",
            description="AI photo enhancement",
            metadata={"photos": 10, "model": "v2"},
        )

        assert request.organization_id == "org_456"
        assert request.credits_amount == 5000
        assert request.service_type == "ai_processing"
        assert request.usage_record_id == "usage_789"
        assert request.description == "AI photo enhancement"


class TestWalletResponse:
    """Test WalletResponse model"""

    def test_wallet_response_success(self):
        """Test successful wallet response"""
        response = WalletResponse(
            success=True,
            message="Operation completed successfully",
            wallet_id="wallet_123",
            balance=Decimal("150.00"),
            transaction_id="txn_456",
        )

        assert response.success is True
        assert response.message == "Operation completed successfully"
        assert response.wallet_id == "wallet_123"
        assert response.balance == Decimal("150.00")
        assert response.transaction_id == "txn_456"

    def test_wallet_response_error(self):
        """Test error wallet response"""
        response = WalletResponse(
            success=False,
            message="Insufficient balance",
        )

        assert response.success is False
        assert response.message == "Insufficient balance"
        assert response.wallet_id is None
        assert response.balance is None

    def test_wallet_response_with_data(self):
        """Test wallet response with additional data"""
        data = {"fee": "2.50", "exchange_rate": "1.0"}
        response = WalletResponse(
            success=True,
            message="Transfer completed",
            wallet_id="wallet_123",
            balance=Decimal("97.50"),
            data=data,
        )

        assert response.data == data


class TestWalletStatistics:
    """Test WalletStatistics model"""

    def test_wallet_statistics_basic(self):
        """Test basic wallet statistics"""
        stats = WalletStatistics(
            wallet_id="wallet_123",
            user_id="user_456",
            current_balance=Decimal("250.00"),
            total_deposits=Decimal("500.00"),
            total_withdrawals=Decimal("150.00"),
            total_consumed=Decimal("100.00"),
            total_refunded=Decimal("20.00"),
            total_transfers_in=Decimal("50.00"),
            total_transfers_out=Decimal("70.00"),
            transaction_count=25,
        )

        assert stats.wallet_id == "wallet_123"
        assert stats.current_balance == Decimal("250.00")
        assert stats.total_deposits == Decimal("500.00")
        assert stats.total_withdrawals == Decimal("150.00")
        assert stats.transaction_count == 25

    def test_wallet_statistics_with_blockchain(self):
        """Test wallet statistics with blockchain data"""
        stats = WalletStatistics(
            wallet_id="wallet_crypto_123",
            user_id="user_456",
            current_balance=Decimal("0.5"),
            total_deposits=Decimal("1.0"),
            total_withdrawals=Decimal("0.4"),
            total_consumed=Decimal("0.1"),
            total_refunded=Decimal("0"),
            total_transfers_in=Decimal("0"),
            total_transfers_out=Decimal("0"),
            transaction_count=15,
            blockchain_transactions=10,
            total_gas_fees=Decimal("0.025"),
        )

        assert stats.blockchain_transactions == 10
        assert stats.total_gas_fees == Decimal("0.025")

    def test_wallet_statistics_with_period(self):
        """Test wallet statistics with time period"""
        start = datetime.now(timezone.utc) - timedelta(days=30)
        end = datetime.now(timezone.utc)

        stats = WalletStatistics(
            wallet_id="wallet_123",
            user_id="user_456",
            current_balance=Decimal("500.00"),
            total_deposits=Decimal("600.00"),
            total_withdrawals=Decimal("100.00"),
            total_consumed=Decimal("0"),
            total_refunded=Decimal("0"),
            total_transfers_in=Decimal("0"),
            total_transfers_out=Decimal("0"),
            transaction_count=20,
            period_start=start,
            period_end=end,
            daily_average=Decimal("16.67"),
            monthly_average=Decimal("500.00"),
        )

        assert stats.period_start == start
        assert stats.period_end == end
        assert stats.daily_average == Decimal("16.67")
        assert stats.monthly_average == Decimal("500.00")


class TestPurchaseCreditsResponse:
    """Test PurchaseCreditsResponse model"""

    def test_purchase_credits_response_success(self):
        """Test successful credits purchase response"""
        response = PurchaseCreditsResponse(
            success=True,
            message="Credits purchased successfully",
            credit_account_id="ca_123",
            credits_purchased=500000,
            usd_amount=Decimal("5.00"),
            payment_transaction_id="pay_456",
            new_balance=500000,
        )

        assert response.success is True
        assert response.credit_account_id == "ca_123"
        assert response.credits_purchased == 500000
        assert response.usd_amount == Decimal("5.00")
        assert response.payment_transaction_id == "pay_456"
        assert response.new_balance == 500000

    def test_purchase_credits_response_failure(self):
        """Test failed credits purchase response"""
        response = PurchaseCreditsResponse(
            success=False,
            message="Payment declined",
        )

        assert response.success is False
        assert response.message == "Payment declined"
        assert response.credits_purchased == 0
        assert response.new_balance == 0


class TestConsumeCreditsResponse:
    """Test ConsumeCreditsResponse model"""

    def test_consume_credits_response_success(self):
        """Test successful credits consumption response"""
        response = ConsumeCreditsResponse(
            success=True,
            message="Credits consumed successfully",
            credits_consumed=1000,
            credits_remaining=499000,
            consumed_from="purchased",
            transaction_id="ctx_123",
        )

        assert response.success is True
        assert response.credits_consumed == 1000
        assert response.credits_remaining == 499000
        assert response.consumed_from == "purchased"
        assert response.transaction_id == "ctx_123"

    def test_consume_credits_response_insufficient(self):
        """Test insufficient credits response"""
        response = ConsumeCreditsResponse(
            success=False,
            message="Insufficient credits",
            credits_remaining=500,
        )

        assert response.success is False
        assert response.message == "Insufficient credits"
        assert response.credits_consumed == 0
        assert response.credits_remaining == 500


class TestCreditBalanceResponse:
    """Test CreditBalanceResponse model"""

    def test_credit_balance_response_basic(self):
        """Test basic credit balance response"""
        response = CreditBalanceResponse(
            success=True,
            message="Balance retrieved successfully",
            user_id="user_123",
            total_credits=600000,
            total_usd_equivalent=Decimal("6.00"),
            purchased_credits=500000,
            bonus_credits=100000,
        )

        assert response.success is True
        assert response.user_id == "user_123"
        assert response.total_credits == 600000
        assert response.total_usd_equivalent == Decimal("6.00")
        assert response.purchased_credits == 500000
        assert response.bonus_credits == 100000

    def test_credit_balance_response_with_breakdown(self):
        """Test credit balance with full breakdown"""
        accounts = [
            CreditAccount(
                credit_account_id="ca_purchased_123",
                user_id="user_123",
                credit_type=CreditType.PURCHASED,
                balance=500000,
                total_credited=500000,
            ),
            CreditAccount(
                credit_account_id="ca_bonus_456",
                user_id="user_123",
                credit_type=CreditType.BONUS,
                balance=50000,
                total_credited=50000,
            ),
        ]

        response = CreditBalanceResponse(
            success=True,
            message="Balance retrieved",
            user_id="user_123",
            total_credits=550000,
            total_usd_equivalent=Decimal("5.50"),
            purchased_credits=500000,
            bonus_credits=50000,
            credit_accounts=accounts,
        )

        assert len(response.credit_accounts) == 2
        assert response.credit_accounts[0].credit_type == CreditType.PURCHASED
        assert response.credit_accounts[1].credit_type == CreditType.BONUS


class TestCreditHistoryResponse:
    """Test CreditHistoryResponse model"""

    def test_credit_history_response_empty(self):
        """Test empty credit history response"""
        response = CreditHistoryResponse(
            success=True,
            message="No transactions found",
            transactions=[],
            total=0,
            page=1,
            page_size=50,
        )

        assert response.success is True
        assert len(response.transactions) == 0
        assert response.total == 0
        assert response.page == 1

    def test_credit_history_response_with_transactions(self):
        """Test credit history with transactions"""
        now = datetime.now(timezone.utc)
        transactions = [
            CreditTransaction(
                transaction_id=f"ctx_{i}",
                credit_account_id="ca_123",
                user_id="user_456",
                transaction_type=CreditTransactionType.CREDIT_CONSUME,
                credits_amount=-1000,
                balance_before=500000 - (i * 1000),
                balance_after=500000 - ((i + 1) * 1000),
                created_at=now,
            )
            for i in range(3)
        ]

        response = CreditHistoryResponse(
            success=True,
            message="Transaction history retrieved",
            transactions=transactions,
            total=3,
            page=1,
            page_size=50,
        )

        assert len(response.transactions) == 3
        assert response.total == 3
        assert all(
            tx.transaction_type == CreditTransactionType.CREDIT_CONSUME
            for tx in response.transactions
        )


class TestTransactionFilter:
    """Test TransactionFilter model"""

    def test_transaction_filter_defaults(self):
        """Test transaction filter with defaults"""
        filter_model = TransactionFilter()

        assert filter_model.wallet_id is None
        assert filter_model.user_id is None
        assert filter_model.transaction_type is None
        assert filter_model.limit == 50
        assert filter_model.offset == 0

    def test_transaction_filter_with_criteria(self):
        """Test transaction filter with specific criteria"""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)

        filter_model = TransactionFilter(
            wallet_id="wallet_123",
            user_id="user_456",
            transaction_type=TransactionType.DEPOSIT,
            start_date=start,
            end_date=end,
            min_amount=Decimal("10.00"),
            max_amount=Decimal("100.00"),
            limit=20,
            offset=10,
        )

        assert filter_model.wallet_id == "wallet_123"
        assert filter_model.user_id == "user_456"
        assert filter_model.transaction_type == TransactionType.DEPOSIT
        assert filter_model.start_date == start
        assert filter_model.end_date == end
        assert filter_model.min_amount == Decimal("10.00")
        assert filter_model.limit == 20

    def test_transaction_filter_blockchain(self):
        """Test transaction filter for blockchain transactions"""
        filter_model = TransactionFilter(
            blockchain_network=BlockchainNetwork.ETHEREUM,
            blockchain_status="confirmed",
            limit=100,
        )

        assert filter_model.blockchain_network == BlockchainNetwork.ETHEREUM
        assert filter_model.blockchain_status == "confirmed"

    def test_transaction_filter_limit_validation(self):
        """Test limit validation (max 100)"""
        with pytest.raises(ValidationError):
            TransactionFilter(limit=101)

    def test_transaction_filter_offset_validation(self):
        """Test offset validation (non-negative)"""
        with pytest.raises(ValidationError):
            TransactionFilter(offset=-1)


class TestBlockchainIntegration:
    """Test BlockchainIntegration model"""

    def test_blockchain_integration_basic(self):
        """Test basic blockchain integration configuration"""
        config = BlockchainIntegration(
            network=BlockchainNetwork.ETHEREUM,
            rpc_url="https://mainnet.infura.io/v3/YOUR-PROJECT-ID",
            chain_id=1,
        )

        assert config.network == BlockchainNetwork.ETHEREUM
        assert config.rpc_url == "https://mainnet.infura.io/v3/YOUR-PROJECT-ID"
        assert config.chain_id == 1
        assert config.gas_price_strategy == "medium"
        assert config.confirmation_blocks == 3

    def test_blockchain_integration_with_contract(self):
        """Test blockchain integration with smart contract"""
        abi = {"abi": "contract_abi_here"}

        config = BlockchainIntegration(
            network=BlockchainNetwork.POLYGON,
            rpc_url="https://polygon-rpc.com",
            chain_id=137,
            contract_address="0x1234567890123456789012345678901234567890",
            abi=abi,
            gas_price_strategy="high",
            confirmation_blocks=12,
            webhook_url="https://api.example.com/webhook/blockchain",
        )

        assert config.network == BlockchainNetwork.POLYGON
        assert config.contract_address == "0x1234567890123456789012345678901234567890"
        assert config.abi == abi
        assert config.gas_price_strategy == "high"
        assert config.confirmation_blocks == 12
        assert config.webhook_url == "https://api.example.com/webhook/blockchain"

    def test_blockchain_integration_testnet(self):
        """Test blockchain integration for testnet"""
        config = BlockchainIntegration(
            network=BlockchainNetwork.TESTNET,
            rpc_url="https://testnet.example.com",
            chain_id=5,
            gas_price_strategy="low",
        )

        assert config.network == BlockchainNetwork.TESTNET
        assert config.gas_price_strategy == "low"


class TestBlockchainSyncRequest:
    """Test BlockchainSyncRequest model"""

    def test_blockchain_sync_request_basic(self):
        """Test basic blockchain sync request"""
        request = BlockchainSyncRequest(
            wallet_id="wallet_crypto_123",
            blockchain_network=BlockchainNetwork.ETHEREUM,
            blockchain_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        )

        assert request.wallet_id == "wallet_crypto_123"
        assert request.blockchain_network == BlockchainNetwork.ETHEREUM
        assert request.blockchain_address == "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        assert request.force_sync is False

    def test_blockchain_sync_request_force(self):
        """Test force blockchain sync request"""
        request = BlockchainSyncRequest(
            wallet_id="wallet_crypto_123",
            blockchain_network=BlockchainNetwork.POLYGON,
            blockchain_address="0xabcdef1234567890",
            force_sync=True,
        )

        assert request.force_sync is True


class TestTransactionCreate:
    """Test TransactionCreate request model"""

    def test_transaction_create_deposit(self):
        """Test creating deposit transaction"""
        request = TransactionCreate(
            wallet_id="wallet_123",
            user_id="user_456",
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal("100.00"),
            description="Payment deposit",
            reference_id="pay_789",
        )

        assert request.wallet_id == "wallet_123"
        assert request.user_id == "user_456"
        assert request.transaction_type == TransactionType.DEPOSIT
        assert request.amount == Decimal("100.00")

    def test_transaction_create_transfer(self):
        """Test creating transfer transaction"""
        request = TransactionCreate(
            wallet_id="wallet_from_123",
            user_id="user_456",
            transaction_type=TransactionType.TRANSFER,
            amount=Decimal("50.00"),
            to_wallet_id="wallet_to_789",
            description="Transfer to friend",
        )

        assert request.transaction_type == TransactionType.TRANSFER
        assert request.to_wallet_id == "wallet_to_789"

    def test_transaction_create_blockchain(self):
        """Test creating blockchain transaction"""
        request = TransactionCreate(
            wallet_id="wallet_crypto_123",
            user_id="user_456",
            transaction_type=TransactionType.BLOCKCHAIN_OUT,
            amount=Decimal("0.1"),
            blockchain_tx_hash="0xabcdef123456",
            blockchain_network=BlockchainNetwork.ETHEREUM,
            metadata={"gas_price": "50 gwei"},
        )

        assert request.transaction_type == TransactionType.BLOCKCHAIN_OUT
        assert request.blockchain_tx_hash == "0xabcdef123456"
        assert request.blockchain_network == BlockchainNetwork.ETHEREUM

    def test_transaction_create_amount_validation(self):
        """Test that zero or negative amount raises ValidationError"""
        with pytest.raises(ValidationError):
            TransactionCreate(
                wallet_id="wallet_123",
                user_id="user_456",
                transaction_type=TransactionType.DEPOSIT,
                amount=Decimal("0"),
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
