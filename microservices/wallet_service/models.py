"""
Wallet Service Models

Defines data models for digital wallet operations with blockchain integration support
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class TransactionType(str, Enum):
    """Transaction types for wallet operations"""
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    CONSUME = "consume"
    REFUND = "refund"
    TRANSFER = "transfer"
    REWARD = "reward"
    FEE = "fee"
    BLOCKCHAIN_IN = "blockchain_in"
    BLOCKCHAIN_OUT = "blockchain_out"


class WalletType(str, Enum):
    """Wallet types supporting different asset classes"""
    FIAT = "fiat"  # Traditional credits/points
    CRYPTO = "crypto"  # Blockchain-based tokens
    HYBRID = "hybrid"  # Both fiat and crypto


class BlockchainNetwork(str, Enum):
    """Supported blockchain networks"""
    ETHEREUM = "ethereum"
    BINANCE_SMART_CHAIN = "bsc"
    POLYGON = "polygon"
    ISA_CHAIN = "isa_chain"  # Custom blockchain
    TESTNET = "testnet"


class WalletBalance(BaseModel):
    """Wallet balance information"""
    model_config = ConfigDict(from_attributes=True)
    
    wallet_id: str
    user_id: str
    balance: Decimal = Field(decimal_places=8, ge=0)
    locked_balance: Decimal = Field(decimal_places=8, ge=0, default=Decimal(0))
    available_balance: Decimal = Field(decimal_places=8, ge=0)
    currency: str = "CREDIT"  # Can be CREDIT, TOKEN, ETH, etc.
    wallet_type: WalletType = WalletType.FIAT
    last_updated: datetime
    
    # Blockchain fields (optional)
    blockchain_address: Optional[str] = None
    blockchain_network: Optional[BlockchainNetwork] = None
    on_chain_balance: Optional[Decimal] = None
    sync_status: Optional[str] = None  # synced, pending, error


class WalletTransaction(BaseModel):
    """Wallet transaction record"""
    model_config = ConfigDict(from_attributes=True)
    
    transaction_id: str
    wallet_id: str
    user_id: str
    transaction_type: TransactionType
    amount: Decimal = Field(decimal_places=8)
    balance_before: Decimal = Field(decimal_places=8)
    balance_after: Decimal = Field(decimal_places=8)
    fee: Decimal = Field(decimal_places=8, default=Decimal(0))
    
    # Transaction details
    description: Optional[str] = None
    reference_id: Optional[str] = None  # External reference (e.g., payment ID)
    usage_record_id: Optional[int] = None  # Link to usage tracking
    
    # Transfer fields
    from_wallet_id: Optional[str] = None
    to_wallet_id: Optional[str] = None
    
    # Blockchain fields
    blockchain_tx_hash: Optional[str] = None
    blockchain_network: Optional[BlockchainNetwork] = None
    blockchain_status: Optional[str] = None  # pending, confirmed, failed
    blockchain_confirmations: Optional[int] = None
    gas_fee: Optional[Decimal] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: Optional[datetime] = None


class WalletCreate(BaseModel):
    """Create new wallet request"""
    user_id: str
    wallet_type: WalletType = WalletType.FIAT
    initial_balance: Decimal = Field(decimal_places=8, ge=0, default=Decimal(0))
    currency: str = "CREDIT"
    blockchain_network: Optional[BlockchainNetwork] = None
    blockchain_address: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WalletUpdate(BaseModel):
    """Update wallet request"""
    blockchain_address: Optional[str] = None
    blockchain_network: Optional[BlockchainNetwork] = None
    metadata: Optional[Dict[str, Any]] = None


class TransactionCreate(BaseModel):
    """Create transaction request"""
    wallet_id: str
    user_id: str
    transaction_type: TransactionType
    amount: Decimal = Field(decimal_places=8, gt=0)
    description: Optional[str] = None
    reference_id: Optional[str] = None
    usage_record_id: Optional[int] = None
    
    # Transfer specific
    to_wallet_id: Optional[str] = None
    
    # Blockchain specific
    blockchain_tx_hash: Optional[str] = None
    blockchain_network: Optional[BlockchainNetwork] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DepositRequest(BaseModel):
    """Deposit funds to wallet"""
    amount: Decimal = Field(decimal_places=8, gt=0)
    description: Optional[str] = None
    reference_id: Optional[str] = None  # Payment reference
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WithdrawRequest(BaseModel):
    """Withdraw funds from wallet"""
    amount: Decimal = Field(decimal_places=8, gt=0)
    description: Optional[str] = None
    destination: Optional[str] = None  # Blockchain address or bank account
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConsumeRequest(BaseModel):
    """Consume credits/tokens from wallet"""
    amount: Decimal = Field(decimal_places=8, gt=0)
    description: Optional[str] = None
    usage_record_id: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TransferRequest(BaseModel):
    """Transfer between wallets"""
    to_wallet_id: str
    amount: Decimal = Field(decimal_places=8, gt=0)
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RefundRequest(BaseModel):
    """Refund transaction"""
    original_transaction_id: str
    amount: Optional[Decimal] = Field(decimal_places=8, gt=0, default=None)  # None = full refund
    reason: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BlockchainSyncRequest(BaseModel):
    """Sync wallet with blockchain"""
    wallet_id: str
    blockchain_network: BlockchainNetwork
    blockchain_address: str
    force_sync: bool = False


class WalletStatistics(BaseModel):
    """Wallet usage statistics"""
    wallet_id: str
    user_id: str
    current_balance: Decimal
    total_deposits: Decimal
    total_withdrawals: Decimal
    total_consumed: Decimal
    total_refunded: Decimal
    total_transfers_in: Decimal
    total_transfers_out: Decimal
    transaction_count: int
    
    # Blockchain stats
    blockchain_transactions: Optional[int] = None
    total_gas_fees: Optional[Decimal] = None
    
    # Time-based stats
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    daily_average: Optional[Decimal] = None
    monthly_average: Optional[Decimal] = None


class TransactionFilter(BaseModel):
    """Filter criteria for transaction queries"""
    wallet_id: Optional[str] = None
    user_id: Optional[str] = None
    transaction_type: Optional[TransactionType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    blockchain_network: Optional[BlockchainNetwork] = None
    blockchain_status: Optional[str] = None
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)


class WalletResponse(BaseModel):
    """Standard wallet operation response"""
    success: bool
    message: str
    wallet_id: Optional[str] = None
    balance: Optional[Decimal] = None
    transaction_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class BlockchainIntegration(BaseModel):
    """Blockchain integration configuration"""
    network: BlockchainNetwork
    rpc_url: str
    chain_id: int
    contract_address: Optional[str] = None  # Token contract
    abi: Optional[Dict[str, Any]] = None
    private_key_encrypted: Optional[str] = None  # Encrypted private key
    gas_price_strategy: str = "medium"  # low, medium, high, custom
    confirmation_blocks: int = 3
    webhook_url: Optional[str] = None  # For transaction notifications


# ====================
# Credit Account Models
# ====================
# Reference: /docs/design/billing-credit-subscription-design.md
# 1 Credit = $0.00001 USD (100,000 Credits = $1)

class CreditType(str, Enum):
    """Credit types with different expiration policies"""
    PURCHASED = "purchased"        # Never expires, priority 100
    BONUS = "bonus"                # May expire, priority 200
    REFERRAL = "referral"          # May expire, priority 200
    PROMOTIONAL = "promotional"    # May expire, priority 300


class CreditTransactionType(str, Enum):
    """Credit transaction types"""
    CREDIT_PURCHASE = "credit_purchase"      # Purchasing credits with USD
    CREDIT_CONSUME = "credit_consume"        # Using credits for services
    CREDIT_REFUND = "credit_refund"          # Refunding credits
    CREDIT_EXPIRE = "credit_expire"          # Credits expired
    CREDIT_TRANSFER = "credit_transfer"      # Transfer between accounts
    CREDIT_BONUS = "credit_bonus"            # Bonus credit allocation


class CreditAccount(BaseModel):
    """Credit account model - stores purchased/bonus credits"""
    id: Optional[int] = None
    credit_account_id: str = Field(..., description="Unique credit account ID")

    # Owner
    user_id: str
    organization_id: Optional[str] = None
    wallet_id: Optional[str] = None

    # Credit Type
    credit_type: CreditType

    # Balance (in credits - 1 Credit = $0.00001 USD)
    balance: int = Field(default=0, ge=0, description="Current balance in credits")
    total_credited: int = Field(default=0, ge=0, description="Total credits ever added")
    total_consumed: int = Field(default=0, ge=0, description="Total credits ever consumed")

    # Expiration
    expires_at: Optional[datetime] = None  # NULL = never expires
    is_expired: bool = False

    # Purchase info
    purchase_amount_usd: Optional[Decimal] = None
    payment_transaction_id: Optional[str] = None

    # Priority (lower = consumed first)
    consumption_priority: int = Field(default=100, description="Lower = consumed first")

    # Status
    is_active: bool = True

    # Metadata
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreditTransaction(BaseModel):
    """Credit transaction model - audit trail for credit operations"""
    id: Optional[int] = None
    transaction_id: str = Field(..., description="Unique transaction ID")

    # Account reference
    credit_account_id: str
    user_id: str
    organization_id: Optional[str] = None

    # Transaction details
    transaction_type: CreditTransactionType
    credits_amount: int = Field(..., description="Positive=add, Negative=deduct")
    balance_before: int
    balance_after: int

    # USD equivalent
    usd_equivalent: Optional[Decimal] = None  # credits_amount * 0.00001

    # Reference
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None

    # Usage details
    service_type: Optional[str] = None
    usage_record_id: Optional[str] = None

    # Payment details
    payment_method: Optional[str] = None
    payment_transaction_id: Optional[str] = None

    # Description
    description: Optional[str] = None
    status: str = "completed"

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None


# ====================
# Credit Request/Response Models
# ====================

class PurchaseCreditsRequest(BaseModel):
    """Request to purchase credits"""
    user_id: str
    organization_id: Optional[str] = None
    credits_amount: int = Field(..., gt=0, description="Credits to purchase")
    payment_method_id: str
    metadata: Optional[Dict[str, Any]] = None


class PurchaseCreditsResponse(BaseModel):
    """Response after purchasing credits"""
    success: bool
    message: str
    credit_account_id: Optional[str] = None
    credits_purchased: int = 0
    usd_amount: Optional[Decimal] = None
    payment_transaction_id: Optional[str] = None
    new_balance: int = 0


class ConsumeCreditsRequest(BaseModel):
    """Request to consume credits"""
    user_id: str
    organization_id: Optional[str] = None
    credits_amount: int = Field(..., gt=0, description="Credits to consume")
    service_type: str
    usage_record_id: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ConsumeCreditsResponse(BaseModel):
    """Response after consuming credits"""
    success: bool
    message: str
    credits_consumed: int = 0
    credits_remaining: int = 0
    consumed_from: Optional[str] = None  # subscription, purchased, bonus
    transaction_id: Optional[str] = None


class CreditBalanceResponse(BaseModel):
    """Credit balance response"""
    success: bool
    message: str
    user_id: str
    organization_id: Optional[str] = None

    # Total balance
    total_credits: int = 0
    total_usd_equivalent: Decimal = Decimal("0")

    # Breakdown by type
    purchased_credits: int = 0
    bonus_credits: int = 0
    referral_credits: int = 0
    promotional_credits: int = 0

    # Accounts
    credit_accounts: List[CreditAccount] = Field(default_factory=list)


class CreditHistoryResponse(BaseModel):
    """Credit transaction history response"""
    success: bool
    message: str
    transactions: List[CreditTransaction] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50