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