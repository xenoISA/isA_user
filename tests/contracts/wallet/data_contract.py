"""
Wallet Service Data Contract

Defines canonical data structures for wallet service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for wallet service test data.

Credit System:
- 1 Credit = $0.00001 USD
- 100,000 Credits = $1 USD
"""

import uuid
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator

# Import from production models for type consistency
from microservices.wallet_service.models import (
    WalletType,
    TransactionType,
    BlockchainNetwork,
)


# ============================================================================
# Enums (mirroring production for testing)
# ============================================================================

class TestWalletType(str, Enum):
    """Wallet types for testing"""
    FIAT = "fiat"
    CRYPTO = "crypto"
    HYBRID = "hybrid"


class TestTransactionType(str, Enum):
    """Transaction types for testing"""
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    CONSUME = "consume"
    REFUND = "refund"
    TRANSFER = "transfer"
    REWARD = "reward"
    FEE = "fee"
    BLOCKCHAIN_IN = "blockchain_in"
    BLOCKCHAIN_OUT = "blockchain_out"


class TestBlockchainNetwork(str, Enum):
    """Blockchain networks for testing"""
    ETHEREUM = "ethereum"
    BINANCE_SMART_CHAIN = "bsc"
    POLYGON = "polygon"
    TESTNET = "testnet"


# ============================================================================
# Request Contracts (Input Schemas)
# ============================================================================

class WalletCreateRequestContract(BaseModel):
    """
    Contract: Wallet creation request schema

    Used for creating new wallets in tests.
    Maps to wallet service create endpoint.
    """
    user_id: str = Field(..., min_length=1, description="User ID (from account service)")
    wallet_type: str = Field(default="fiat", pattern="^(fiat|crypto|hybrid)$", description="Wallet type")
    initial_balance: Decimal = Field(default=Decimal("0"), ge=0, description="Initial balance")
    currency: str = Field(default="CREDIT", max_length=20, description="Currency code")
    blockchain_network: Optional[str] = Field(None, description="Blockchain network (for crypto wallets)")
    blockchain_address: Optional[str] = Field(None, description="Blockchain address")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_abc123def456",
                "wallet_type": "fiat",
                "initial_balance": "0",
                "currency": "CREDIT",
                "metadata": {}
            }
        }


class DepositRequestContract(BaseModel):
    """
    Contract: Deposit request schema

    Used for depositing funds to wallet in tests.
    """
    amount: Decimal = Field(..., gt=0, description="Deposit amount (must be positive)")
    description: Optional[str] = Field(None, max_length=500, description="Deposit description")
    reference_id: Optional[str] = Field(None, max_length=255, description="External reference (payment ID)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "amount": "100.00",
                "description": "Payment deposit",
                "reference_id": "payment_xyz123",
                "metadata": {"payment_method": "credit_card"}
            }
        }


class WithdrawRequestContract(BaseModel):
    """
    Contract: Withdraw request schema

    Used for withdrawing funds from wallet in tests.
    """
    amount: Decimal = Field(..., gt=0, description="Withdrawal amount (must be positive)")
    description: Optional[str] = Field(None, max_length=500, description="Withdrawal description")
    destination: Optional[str] = Field(None, max_length=255, description="Destination (bank/blockchain)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "amount": "50.00",
                "description": "Withdrawal to bank",
                "destination": "bank_account_xxx",
                "metadata": {}
            }
        }


class ConsumeRequestContract(BaseModel):
    """
    Contract: Consume request schema

    Used for consuming credits/tokens from wallet in tests.
    """
    amount: Decimal = Field(..., gt=0, description="Consumption amount (must be positive)")
    description: Optional[str] = Field(None, max_length=500, description="Consumption description")
    usage_record_id: Optional[int] = Field(None, description="Link to usage tracking record")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "amount": "25.50",
                "description": "API usage charge",
                "usage_record_id": 12345,
                "metadata": {"service": "ai_assistant"}
            }
        }


class TransferRequestContract(BaseModel):
    """
    Contract: Transfer request schema

    Used for transferring funds between wallets in tests.
    """
    to_wallet_id: str = Field(..., min_length=1, description="Destination wallet ID")
    amount: Decimal = Field(..., gt=0, description="Transfer amount (must be positive)")
    description: Optional[str] = Field(None, max_length=500, description="Transfer description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "to_wallet_id": "wallet_destination_xyz",
                "amount": "100.00",
                "description": "Transfer to friend",
                "metadata": {}
            }
        }


class RefundRequestContract(BaseModel):
    """
    Contract: Refund request schema

    Used for refunding previous transactions in tests.
    """
    original_transaction_id: str = Field(..., min_length=1, description="Original transaction to refund")
    amount: Optional[Decimal] = Field(None, gt=0, description="Refund amount (None = full refund)")
    reason: str = Field(..., min_length=1, max_length=500, description="Refund reason (required)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('reason')
    @classmethod
    def validate_reason(cls, v):
        if not v or not v.strip():
            raise ValueError("Refund reason is required")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "original_transaction_id": "txn_abc123",
                "amount": "50.00",
                "reason": "Customer requested refund",
                "metadata": {"refund_type": "partial"}
            }
        }


class TransactionFilterContract(BaseModel):
    """
    Contract: Transaction filter parameters schema

    Used for filtering transaction history in tests.
    """
    wallet_id: Optional[str] = Field(None, description="Filter by wallet ID")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    transaction_type: Optional[str] = Field(None, description="Filter by transaction type")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    min_amount: Optional[Decimal] = Field(None, ge=0, description="Minimum amount filter")
    max_amount: Optional[Decimal] = Field(None, ge=0, description="Maximum amount filter")
    limit: int = Field(default=50, ge=1, le=100, description="Results per page (max 100)")
    offset: int = Field(default=0, ge=0, description="Pagination offset")

    class Config:
        json_schema_extra = {
            "example": {
                "wallet_id": "wallet_abc123",
                "transaction_type": "deposit",
                "start_date": "2025-12-01T00:00:00Z",
                "end_date": "2025-12-31T23:59:59Z",
                "limit": 50,
                "offset": 0
            }
        }


class BlockchainSyncRequestContract(BaseModel):
    """
    Contract: Blockchain sync request schema

    Used for syncing wallet with blockchain in tests.
    """
    wallet_id: str = Field(..., min_length=1, description="Wallet ID to sync")
    blockchain_network: str = Field(..., description="Blockchain network")
    blockchain_address: str = Field(..., min_length=1, description="Blockchain address")
    force_sync: bool = Field(default=False, description="Force sync even if recently synced")

    class Config:
        json_schema_extra = {
            "example": {
                "wallet_id": "wallet_abc123",
                "blockchain_network": "ethereum",
                "blockchain_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
                "force_sync": False
            }
        }


# ============================================================================
# Response Contracts (Output Schemas)
# ============================================================================

class WalletBalanceResponseContract(BaseModel):
    """
    Contract: Wallet balance response schema

    Validates API response structure for wallet balance queries.
    """
    wallet_id: str = Field(..., description="Wallet ID")
    user_id: str = Field(..., description="Owner user ID")
    balance: Decimal = Field(..., ge=0, description="Current total balance")
    locked_balance: Decimal = Field(default=Decimal("0"), ge=0, description="Locked balance")
    available_balance: Decimal = Field(..., ge=0, description="Available balance (total - locked)")
    currency: str = Field(..., description="Currency code")
    wallet_type: str = Field(..., description="Wallet type")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    blockchain_address: Optional[str] = Field(None, description="Blockchain address")
    blockchain_network: Optional[str] = Field(None, description="Blockchain network")
    on_chain_balance: Optional[Decimal] = Field(None, description="On-chain balance")
    sync_status: Optional[str] = Field(None, description="Blockchain sync status")

    class Config:
        json_schema_extra = {
            "example": {
                "wallet_id": "wallet_abc123",
                "user_id": "user_xyz789",
                "balance": "1000.00000000",
                "locked_balance": "50.00000000",
                "available_balance": "950.00000000",
                "currency": "CREDIT",
                "wallet_type": "fiat",
                "last_updated": "2025-12-15T10:30:00Z"
            }
        }


class WalletTransactionResponseContract(BaseModel):
    """
    Contract: Wallet transaction response schema

    Validates API response structure for transaction records.
    """
    transaction_id: str = Field(..., description="Transaction ID")
    wallet_id: str = Field(..., description="Wallet ID")
    user_id: str = Field(..., description="User ID")
    transaction_type: str = Field(..., description="Transaction type")
    amount: Decimal = Field(..., description="Transaction amount")
    balance_before: Decimal = Field(..., description="Balance before transaction")
    balance_after: Decimal = Field(..., description="Balance after transaction")
    fee: Decimal = Field(default=Decimal("0"), description="Transaction fee")
    description: Optional[str] = Field(None, description="Transaction description")
    reference_id: Optional[str] = Field(None, description="External reference")
    usage_record_id: Optional[int] = Field(None, description="Usage record ID")
    from_wallet_id: Optional[str] = Field(None, description="Source wallet (for transfers)")
    to_wallet_id: Optional[str] = Field(None, description="Destination wallet (for transfers)")
    blockchain_tx_hash: Optional[str] = Field(None, description="Blockchain transaction hash")
    blockchain_network: Optional[str] = Field(None, description="Blockchain network")
    blockchain_status: Optional[str] = Field(None, description="Blockchain transaction status")
    blockchain_confirmations: Optional[int] = Field(None, description="Blockchain confirmations")
    gas_fee: Optional[Decimal] = Field(None, description="Gas fee (for blockchain transactions)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Transaction creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "txn_abc123",
                "wallet_id": "wallet_xyz789",
                "user_id": "user_123",
                "transaction_type": "deposit",
                "amount": "100.00000000",
                "balance_before": "900.00000000",
                "balance_after": "1000.00000000",
                "fee": "0.00000000",
                "description": "Payment deposit",
                "reference_id": "payment_xyz",
                "created_at": "2025-12-15T10:30:00Z"
            }
        }


class WalletResponseContract(BaseModel):
    """
    Contract: Standard wallet operation response schema

    Validates API response structure for wallet operations.
    """
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    wallet_id: Optional[str] = Field(None, description="Wallet ID")
    balance: Optional[Decimal] = Field(None, description="Current balance")
    transaction_id: Optional[str] = Field(None, description="Transaction ID (for operations)")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "wallet_id": "wallet_abc123",
                "balance": "1000.00000000",
                "transaction_id": "txn_xyz789",
                "data": {}
            }
        }


class WalletStatisticsResponseContract(BaseModel):
    """
    Contract: Wallet statistics response schema

    Validates API response structure for wallet statistics.
    """
    wallet_id: str = Field(..., description="Wallet ID")
    user_id: str = Field(..., description="User ID")
    current_balance: Decimal = Field(..., ge=0, description="Current balance")
    total_deposits: Decimal = Field(..., ge=0, description="Total deposits")
    total_withdrawals: Decimal = Field(..., ge=0, description="Total withdrawals")
    total_consumed: Decimal = Field(..., ge=0, description="Total consumed")
    total_refunded: Decimal = Field(..., ge=0, description="Total refunded")
    total_transfers_in: Decimal = Field(..., ge=0, description="Total transfers in")
    total_transfers_out: Decimal = Field(..., ge=0, description="Total transfers out")
    transaction_count: int = Field(..., ge=0, description="Total transaction count")
    blockchain_transactions: Optional[int] = Field(None, description="Blockchain transaction count")
    total_gas_fees: Optional[Decimal] = Field(None, description="Total gas fees")
    period_start: Optional[datetime] = Field(None, description="Statistics period start")
    period_end: Optional[datetime] = Field(None, description="Statistics period end")

    class Config:
        json_schema_extra = {
            "example": {
                "wallet_id": "wallet_abc123",
                "user_id": "user_xyz789",
                "current_balance": "1000.00",
                "total_deposits": "5000.00",
                "total_withdrawals": "1000.00",
                "total_consumed": "3000.00",
                "total_refunded": "200.00",
                "total_transfers_in": "500.00",
                "total_transfers_out": "700.00",
                "transaction_count": 47
            }
        }


class WalletListResponseContract(BaseModel):
    """
    Contract: Wallet list response schema

    Validates API response structure for listing user wallets.
    """
    wallets: List[WalletBalanceResponseContract] = Field(..., description="List of wallets")
    count: int = Field(..., ge=0, description="Number of wallets")

    class Config:
        json_schema_extra = {
            "example": {
                "wallets": [
                    {
                        "wallet_id": "wallet_abc123",
                        "user_id": "user_xyz789",
                        "balance": "1000.00",
                        "currency": "CREDIT",
                        "wallet_type": "fiat"
                    }
                ],
                "count": 1
            }
        }


class TransactionListResponseContract(BaseModel):
    """
    Contract: Transaction list response schema

    Validates API response structure for transaction history.
    """
    transactions: List[WalletTransactionResponseContract] = Field(..., description="List of transactions")
    count: int = Field(..., ge=0, description="Number of transactions returned")
    limit: int = Field(..., ge=1, le=100, description="Results per page")
    offset: int = Field(..., ge=0, description="Pagination offset")

    class Config:
        json_schema_extra = {
            "example": {
                "transactions": [],
                "count": 0,
                "limit": 50,
                "offset": 0
            }
        }


class CreditBalanceResponseContract(BaseModel):
    """
    Contract: Credit balance response schema (backward compatibility)

    Validates API response structure for credit balance queries.
    """
    success: bool = Field(..., description="Operation success status")
    balance: float = Field(..., ge=0, description="Total balance")
    available_balance: float = Field(..., ge=0, description="Available balance")
    locked_balance: float = Field(default=0, ge=0, description="Locked balance")
    currency: str = Field(..., description="Currency code")
    wallet_id: str = Field(..., description="Wallet ID")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "balance": 1000.0,
                "available_balance": 950.0,
                "locked_balance": 50.0,
                "currency": "CREDIT",
                "wallet_id": "wallet_abc123"
            }
        }


class WalletServiceStatusContract(BaseModel):
    """
    Contract: Wallet service status response schema

    Validates API response structure for service health check.
    """
    service: str = Field(default="wallet_service", description="Service name")
    version: str = Field(..., description="Service version")
    status: str = Field(..., pattern="^(operational|degraded|down)$", description="Service status")
    capabilities: Dict[str, bool] = Field(..., description="Service capabilities")

    class Config:
        json_schema_extra = {
            "example": {
                "service": "wallet_service",
                "version": "1.0.0",
                "status": "operational",
                "capabilities": {
                    "wallet_management": True,
                    "transaction_management": True,
                    "blockchain_ready": True
                }
            }
        }


# ============================================================================
# Test Data Factory
# ============================================================================

class WalletTestDataFactory:
    """
    Factory for creating test data conforming to contracts.

    Provides methods to generate valid/invalid test data for all scenarios.
    """

    @staticmethod
    def make_wallet_id() -> str:
        """Generate unique test wallet ID"""
        return f"wallet_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate unique test user ID"""
        return f"user_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_transaction_id() -> str:
        """Generate unique test transaction ID"""
        return f"txn_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_payment_id() -> str:
        """Generate unique test payment reference ID"""
        return f"payment_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_balance() -> Decimal:
        """Generate random balance (0-10000)"""
        return Decimal(str(random.uniform(0, 10000))).quantize(Decimal("0.00000001"))

    @staticmethod
    def make_amount() -> Decimal:
        """Generate random positive amount (1-1000)"""
        return Decimal(str(random.uniform(1, 1000))).quantize(Decimal("0.00000001"))

    @staticmethod
    def make_small_amount() -> Decimal:
        """Generate small positive amount (0.01-10)"""
        return Decimal(str(random.uniform(0.01, 10))).quantize(Decimal("0.00000001"))

    @staticmethod
    def make_currency() -> str:
        """Generate random currency"""
        currencies = ["CREDIT", "USD", "TOKEN", "ETH"]
        return random.choice(currencies)

    @staticmethod
    def make_wallet_type() -> str:
        """Generate random wallet type"""
        types = ["fiat", "crypto", "hybrid"]
        return random.choice(types)

    @staticmethod
    def make_transaction_type() -> str:
        """Generate random transaction type"""
        types = ["deposit", "withdraw", "consume", "refund", "transfer", "reward"]
        return random.choice(types)

    @staticmethod
    def make_blockchain_network() -> str:
        """Generate random blockchain network"""
        networks = ["ethereum", "bsc", "polygon", "testnet"]
        return random.choice(networks)

    @staticmethod
    def make_blockchain_address() -> str:
        """Generate fake blockchain address"""
        return f"0x{uuid.uuid4().hex[:40]}"

    @staticmethod
    def make_description() -> str:
        """Generate random transaction description"""
        descriptions = [
            "Payment deposit",
            "API usage charge",
            "Monthly subscription",
            "Refund for order",
            "Transfer to friend",
            "Withdrawal to bank",
            "Bonus reward",
            "Service fee",
        ]
        return random.choice(descriptions)

    @staticmethod
    def make_refund_reason() -> str:
        """Generate random refund reason"""
        reasons = [
            "Customer requested refund",
            "Service not delivered",
            "Billing error",
            "Duplicate charge",
            "Account closure",
        ]
        return random.choice(reasons)

    @staticmethod
    def make_metadata() -> Dict[str, Any]:
        """Generate random metadata"""
        return {
            "source": random.choice(["web", "mobile", "api"]),
            "ip_address": f"192.168.{random.randint(0,255)}.{random.randint(0,255)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ========================================================================
    # Request Factories
    # ========================================================================

    @staticmethod
    def make_create_wallet_request(**overrides) -> WalletCreateRequestContract:
        """
        Create valid wallet creation request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            WalletCreateRequestContract with valid data
        """
        defaults = {
            "user_id": WalletTestDataFactory.make_user_id(),
            "wallet_type": "fiat",
            "initial_balance": Decimal("0"),
            "currency": "CREDIT",
            "metadata": {},
        }
        defaults.update(overrides)
        return WalletCreateRequestContract(**defaults)

    @staticmethod
    def make_deposit_request(**overrides) -> DepositRequestContract:
        """
        Create valid deposit request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            DepositRequestContract with valid data
        """
        defaults = {
            "amount": WalletTestDataFactory.make_amount(),
            "description": "Test deposit",
            "reference_id": WalletTestDataFactory.make_payment_id(),
            "metadata": {},
        }
        defaults.update(overrides)
        return DepositRequestContract(**defaults)

    @staticmethod
    def make_withdraw_request(**overrides) -> WithdrawRequestContract:
        """
        Create valid withdrawal request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            WithdrawRequestContract with valid data
        """
        defaults = {
            "amount": WalletTestDataFactory.make_amount(),
            "description": "Test withdrawal",
            "destination": None,
            "metadata": {},
        }
        defaults.update(overrides)
        return WithdrawRequestContract(**defaults)

    @staticmethod
    def make_consume_request(**overrides) -> ConsumeRequestContract:
        """
        Create valid consumption request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            ConsumeRequestContract with valid data
        """
        defaults = {
            "amount": WalletTestDataFactory.make_small_amount(),
            "description": "API usage charge",
            "usage_record_id": random.randint(1000, 99999),
            "metadata": {},
        }
        defaults.update(overrides)
        return ConsumeRequestContract(**defaults)

    @staticmethod
    def make_transfer_request(**overrides) -> TransferRequestContract:
        """
        Create valid transfer request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            TransferRequestContract with valid data
        """
        defaults = {
            "to_wallet_id": WalletTestDataFactory.make_wallet_id(),
            "amount": WalletTestDataFactory.make_amount(),
            "description": "Test transfer",
            "metadata": {},
        }
        defaults.update(overrides)
        return TransferRequestContract(**defaults)

    @staticmethod
    def make_refund_request(**overrides) -> RefundRequestContract:
        """
        Create valid refund request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            RefundRequestContract with valid data
        """
        defaults = {
            "original_transaction_id": WalletTestDataFactory.make_transaction_id(),
            "amount": None,  # Full refund
            "reason": WalletTestDataFactory.make_refund_reason(),
            "metadata": {},
        }
        defaults.update(overrides)
        return RefundRequestContract(**defaults)

    @staticmethod
    def make_transaction_filter(**overrides) -> TransactionFilterContract:
        """
        Create valid transaction filter with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            TransactionFilterContract with valid data
        """
        defaults = {
            "wallet_id": None,
            "user_id": None,
            "transaction_type": None,
            "start_date": None,
            "end_date": None,
            "limit": 50,
            "offset": 0,
        }
        defaults.update(overrides)
        return TransactionFilterContract(**defaults)

    # ========================================================================
    # Response Factories
    # ========================================================================

    @staticmethod
    def make_wallet_balance_response(**overrides) -> WalletBalanceResponseContract:
        """
        Create expected wallet balance response for assertions.

        Used in tests to validate API responses match contract.
        """
        balance = WalletTestDataFactory.make_balance()
        locked = Decimal("0")
        defaults = {
            "wallet_id": WalletTestDataFactory.make_wallet_id(),
            "user_id": WalletTestDataFactory.make_user_id(),
            "balance": balance,
            "locked_balance": locked,
            "available_balance": balance - locked,
            "currency": "CREDIT",
            "wallet_type": "fiat",
            "last_updated": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return WalletBalanceResponseContract(**defaults)

    @staticmethod
    def make_transaction_response(**overrides) -> WalletTransactionResponseContract:
        """
        Create expected transaction response for assertions.

        Used in tests to validate API responses match contract.
        """
        balance_before = WalletTestDataFactory.make_balance()
        amount = WalletTestDataFactory.make_small_amount()
        defaults = {
            "transaction_id": WalletTestDataFactory.make_transaction_id(),
            "wallet_id": WalletTestDataFactory.make_wallet_id(),
            "user_id": WalletTestDataFactory.make_user_id(),
            "transaction_type": "deposit",
            "amount": amount,
            "balance_before": balance_before,
            "balance_after": balance_before + amount,
            "fee": Decimal("0"),
            "description": WalletTestDataFactory.make_description(),
            "created_at": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return WalletTransactionResponseContract(**defaults)

    @staticmethod
    def make_wallet_response(**overrides) -> WalletResponseContract:
        """
        Create expected wallet operation response for assertions.

        Used in tests to validate API responses match contract.
        """
        defaults = {
            "success": True,
            "message": "Operation completed successfully",
            "wallet_id": WalletTestDataFactory.make_wallet_id(),
            "balance": WalletTestDataFactory.make_balance(),
            "transaction_id": WalletTestDataFactory.make_transaction_id(),
            "data": {},
        }
        defaults.update(overrides)
        return WalletResponseContract(**defaults)

    @staticmethod
    def make_statistics_response(**overrides) -> WalletStatisticsResponseContract:
        """
        Create expected wallet statistics response for assertions.

        Used in tests to validate API responses match contract.
        """
        balance = WalletTestDataFactory.make_balance()
        defaults = {
            "wallet_id": WalletTestDataFactory.make_wallet_id(),
            "user_id": WalletTestDataFactory.make_user_id(),
            "current_balance": balance,
            "total_deposits": balance * Decimal("2"),
            "total_withdrawals": balance * Decimal("0.5"),
            "total_consumed": balance * Decimal("0.3"),
            "total_refunded": balance * Decimal("0.1"),
            "total_transfers_in": balance * Decimal("0.2"),
            "total_transfers_out": balance * Decimal("0.2"),
            "transaction_count": random.randint(10, 100),
        }
        defaults.update(overrides)
        return WalletStatisticsResponseContract(**defaults)

    @staticmethod
    def make_service_status(**overrides) -> WalletServiceStatusContract:
        """
        Create expected service status response for assertions.

        Used in tests to validate API responses match contract.
        """
        defaults = {
            "service": "wallet_service",
            "version": "1.0.0",
            "status": "operational",
            "capabilities": {
                "wallet_management": True,
                "transaction_management": True,
                "blockchain_ready": True,
            },
        }
        defaults.update(overrides)
        return WalletServiceStatusContract(**defaults)

    # ========================================================================
    # Invalid Data Generators (for negative testing)
    # ========================================================================

    @staticmethod
    def make_invalid_create_wallet_missing_user_id() -> dict:
        """Generate create request missing required user_id"""
        return {
            "wallet_type": "fiat",
            "initial_balance": "0",
            "currency": "CREDIT",
        }

    @staticmethod
    def make_invalid_create_wallet_invalid_type() -> dict:
        """Generate create request with invalid wallet type"""
        return {
            "user_id": WalletTestDataFactory.make_user_id(),
            "wallet_type": "invalid_type",
            "initial_balance": "0",
            "currency": "CREDIT",
        }

    @staticmethod
    def make_invalid_create_wallet_negative_balance() -> dict:
        """Generate create request with negative initial balance"""
        return {
            "user_id": WalletTestDataFactory.make_user_id(),
            "wallet_type": "fiat",
            "initial_balance": "-100",
            "currency": "CREDIT",
        }

    @staticmethod
    def make_invalid_deposit_zero_amount() -> dict:
        """Generate deposit request with zero amount"""
        return {
            "amount": "0",
            "description": "Invalid deposit",
        }

    @staticmethod
    def make_invalid_deposit_negative_amount() -> dict:
        """Generate deposit request with negative amount"""
        return {
            "amount": "-100",
            "description": "Invalid deposit",
        }

    @staticmethod
    def make_invalid_withdraw_zero_amount() -> dict:
        """Generate withdrawal request with zero amount"""
        return {
            "amount": "0",
            "description": "Invalid withdrawal",
        }

    @staticmethod
    def make_invalid_consume_negative_amount() -> dict:
        """Generate consume request with negative amount"""
        return {
            "amount": "-50",
            "description": "Invalid consumption",
        }

    @staticmethod
    def make_invalid_transfer_missing_destination() -> dict:
        """Generate transfer request missing destination wallet"""
        return {
            "amount": "100",
            "description": "Invalid transfer",
        }

    @staticmethod
    def make_invalid_transfer_same_wallet() -> dict:
        """Generate transfer request with same source and destination"""
        wallet_id = WalletTestDataFactory.make_wallet_id()
        return {
            "to_wallet_id": wallet_id,
            "amount": "100",
            "description": "Self transfer",
        }

    @staticmethod
    def make_invalid_refund_missing_reason() -> dict:
        """Generate refund request missing required reason"""
        return {
            "original_transaction_id": WalletTestDataFactory.make_transaction_id(),
            "amount": "50",
            # Missing reason
        }

    @staticmethod
    def make_invalid_refund_empty_reason() -> dict:
        """Generate refund request with empty reason"""
        return {
            "original_transaction_id": WalletTestDataFactory.make_transaction_id(),
            "amount": "50",
            "reason": "   ",  # Whitespace only
        }

    @staticmethod
    def make_invalid_filter_excessive_limit() -> dict:
        """Generate filter with excessive limit"""
        return {
            "wallet_id": WalletTestDataFactory.make_wallet_id(),
            "limit": 1000,  # Invalid - max is 100
            "offset": 0,
        }

    @staticmethod
    def make_invalid_filter_negative_offset() -> dict:
        """Generate filter with negative offset"""
        return {
            "wallet_id": WalletTestDataFactory.make_wallet_id(),
            "limit": 50,
            "offset": -1,  # Invalid - must be >= 0
        }


# ============================================================================
# Request Builders (for complex test scenarios)
# ============================================================================

class WalletCreateRequestBuilder:
    """
    Builder pattern for creating complex wallet creation requests.

    Example:
        request = (
            WalletCreateRequestBuilder()
            .with_user_id("user_123")
            .with_wallet_type("crypto")
            .with_initial_balance(Decimal("100"))
            .with_blockchain("ethereum", "0x123...")
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "user_id": WalletTestDataFactory.make_user_id(),
            "wallet_type": "fiat",
            "initial_balance": Decimal("0"),
            "currency": "CREDIT",
            "metadata": {},
        }

    def with_user_id(self, user_id: str) -> "WalletCreateRequestBuilder":
        """Set user ID"""
        self._data["user_id"] = user_id
        return self

    def with_wallet_type(self, wallet_type: str) -> "WalletCreateRequestBuilder":
        """Set wallet type"""
        self._data["wallet_type"] = wallet_type
        return self

    def with_initial_balance(self, balance: Decimal) -> "WalletCreateRequestBuilder":
        """Set initial balance"""
        self._data["initial_balance"] = balance
        return self

    def with_currency(self, currency: str) -> "WalletCreateRequestBuilder":
        """Set currency"""
        self._data["currency"] = currency
        return self

    def with_blockchain(self, network: str, address: str) -> "WalletCreateRequestBuilder":
        """Set blockchain details"""
        self._data["blockchain_network"] = network
        self._data["blockchain_address"] = address
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "WalletCreateRequestBuilder":
        """Set metadata"""
        self._data["metadata"] = metadata
        return self

    def build(self) -> WalletCreateRequestContract:
        """Build the final request"""
        return WalletCreateRequestContract(**self._data)


class DepositRequestBuilder:
    """
    Builder pattern for creating complex deposit requests.

    Example:
        request = (
            DepositRequestBuilder()
            .with_amount(Decimal("500"))
            .with_description("Payment from Stripe")
            .with_reference_id("pi_12345")
            .with_metadata({"payment_method": "card"})
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "amount": WalletTestDataFactory.make_amount(),
            "description": None,
            "reference_id": None,
            "metadata": {},
        }

    def with_amount(self, amount: Decimal) -> "DepositRequestBuilder":
        """Set deposit amount"""
        self._data["amount"] = amount
        return self

    def with_description(self, description: str) -> "DepositRequestBuilder":
        """Set description"""
        self._data["description"] = description
        return self

    def with_reference_id(self, reference_id: str) -> "DepositRequestBuilder":
        """Set external reference ID"""
        self._data["reference_id"] = reference_id
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "DepositRequestBuilder":
        """Set metadata"""
        self._data["metadata"] = metadata
        return self

    def build(self) -> DepositRequestContract:
        """Build the final request"""
        return DepositRequestContract(**self._data)


class TransferRequestBuilder:
    """
    Builder pattern for creating complex transfer requests.

    Example:
        request = (
            TransferRequestBuilder()
            .with_destination("wallet_dest_123")
            .with_amount(Decimal("100"))
            .with_description("Gift to friend")
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "to_wallet_id": WalletTestDataFactory.make_wallet_id(),
            "amount": WalletTestDataFactory.make_amount(),
            "description": None,
            "metadata": {},
        }

    def with_destination(self, to_wallet_id: str) -> "TransferRequestBuilder":
        """Set destination wallet ID"""
        self._data["to_wallet_id"] = to_wallet_id
        return self

    def with_amount(self, amount: Decimal) -> "TransferRequestBuilder":
        """Set transfer amount"""
        self._data["amount"] = amount
        return self

    def with_description(self, description: str) -> "TransferRequestBuilder":
        """Set description"""
        self._data["description"] = description
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "TransferRequestBuilder":
        """Set metadata"""
        self._data["metadata"] = metadata
        return self

    def build(self) -> TransferRequestContract:
        """Build the final request"""
        return TransferRequestContract(**self._data)


class RefundRequestBuilder:
    """
    Builder pattern for creating complex refund requests.

    Example:
        request = (
            RefundRequestBuilder()
            .for_transaction("txn_123")
            .with_partial_amount(Decimal("50"))
            .with_reason("Customer request")
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "original_transaction_id": WalletTestDataFactory.make_transaction_id(),
            "amount": None,
            "reason": WalletTestDataFactory.make_refund_reason(),
            "metadata": {},
        }

    def for_transaction(self, transaction_id: str) -> "RefundRequestBuilder":
        """Set original transaction ID"""
        self._data["original_transaction_id"] = transaction_id
        return self

    def with_full_refund(self) -> "RefundRequestBuilder":
        """Set full refund (amount = None)"""
        self._data["amount"] = None
        return self

    def with_partial_amount(self, amount: Decimal) -> "RefundRequestBuilder":
        """Set partial refund amount"""
        self._data["amount"] = amount
        return self

    def with_reason(self, reason: str) -> "RefundRequestBuilder":
        """Set refund reason"""
        self._data["reason"] = reason
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "RefundRequestBuilder":
        """Set metadata"""
        self._data["metadata"] = metadata
        return self

    def build(self) -> RefundRequestContract:
        """Build the final request"""
        return RefundRequestContract(**self._data)


class TransactionFilterBuilder:
    """
    Builder pattern for creating complex transaction filters.

    Example:
        filter = (
            TransactionFilterBuilder()
            .for_wallet("wallet_123")
            .of_type("deposit")
            .in_date_range(start_date, end_date)
            .with_pagination(page=1, page_size=20)
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "wallet_id": None,
            "user_id": None,
            "transaction_type": None,
            "start_date": None,
            "end_date": None,
            "min_amount": None,
            "max_amount": None,
            "limit": 50,
            "offset": 0,
        }

    def for_wallet(self, wallet_id: str) -> "TransactionFilterBuilder":
        """Filter by wallet ID"""
        self._data["wallet_id"] = wallet_id
        return self

    def for_user(self, user_id: str) -> "TransactionFilterBuilder":
        """Filter by user ID"""
        self._data["user_id"] = user_id
        return self

    def of_type(self, transaction_type: str) -> "TransactionFilterBuilder":
        """Filter by transaction type"""
        self._data["transaction_type"] = transaction_type
        return self

    def in_date_range(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None
    ) -> "TransactionFilterBuilder":
        """Filter by date range"""
        self._data["start_date"] = start
        self._data["end_date"] = end
        return self

    def in_amount_range(
        self, min_amount: Optional[Decimal] = None, max_amount: Optional[Decimal] = None
    ) -> "TransactionFilterBuilder":
        """Filter by amount range"""
        self._data["min_amount"] = min_amount
        self._data["max_amount"] = max_amount
        return self

    def with_pagination(self, page: int = 1, page_size: int = 50) -> "TransactionFilterBuilder":
        """Set pagination parameters"""
        self._data["limit"] = page_size
        self._data["offset"] = (page - 1) * page_size
        return self

    def build(self) -> TransactionFilterContract:
        """Build the final filter"""
        return TransactionFilterContract(**self._data)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "TestWalletType",
    "TestTransactionType",
    "TestBlockchainNetwork",

    # Request Contracts
    "WalletCreateRequestContract",
    "DepositRequestContract",
    "WithdrawRequestContract",
    "ConsumeRequestContract",
    "TransferRequestContract",
    "RefundRequestContract",
    "TransactionFilterContract",
    "BlockchainSyncRequestContract",

    # Response Contracts
    "WalletBalanceResponseContract",
    "WalletTransactionResponseContract",
    "WalletResponseContract",
    "WalletStatisticsResponseContract",
    "WalletListResponseContract",
    "TransactionListResponseContract",
    "CreditBalanceResponseContract",
    "WalletServiceStatusContract",

    # Factory
    "WalletTestDataFactory",

    # Builders
    "WalletCreateRequestBuilder",
    "DepositRequestBuilder",
    "TransferRequestBuilder",
    "RefundRequestBuilder",
    "TransactionFilterBuilder",
]
