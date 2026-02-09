"""
Crypto Payment Models

Defines chains, tokens, and crypto payment data structures.
Supports mainstream chains and tokens.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class Chain(str, Enum):
    """Supported blockchain networks"""
    # Layer 1
    ETHEREUM = "ethereum"
    BITCOIN = "bitcoin"
    SOLANA = "solana"

    # Layer 2 / Sidechains
    POLYGON = "polygon"
    BASE = "base"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"

    # Other
    AVALANCHE = "avalanche"
    BNB_CHAIN = "bnb_chain"


class Token(str, Enum):
    """Supported tokens/cryptocurrencies"""
    # Native tokens
    ETH = "ETH"
    BTC = "BTC"
    SOL = "SOL"
    MATIC = "MATIC"
    AVAX = "AVAX"
    BNB = "BNB"

    # Stablecoins
    USDC = "USDC"
    USDT = "USDT"
    DAI = "DAI"

    # Coinbase-specific
    PUSDC = "PUSDC"  # Polygon USDC


class CryptoPaymentStatus(str, Enum):
    """Crypto payment status"""
    PENDING = "pending"          # Waiting for payment
    DETECTED = "detected"        # Payment detected, waiting confirmations
    CONFIRMED = "confirmed"      # Payment confirmed on chain
    COMPLETED = "completed"      # Payment completed and credited
    EXPIRED = "expired"          # Payment window expired
    FAILED = "failed"            # Payment failed
    UNDERPAID = "underpaid"      # Partial payment received
    OVERPAID = "overpaid"        # More than required received
    REFUNDED = "refunded"        # Payment refunded


class CryptoProvider(str, Enum):
    """Crypto payment providers"""
    COINBASE_COMMERCE = "coinbase_commerce"
    CIRCLE = "circle"
    MOONPAY = "moonpay"
    DIRECT_WEB3 = "direct_web3"  # For future direct blockchain integration


# Chain configuration
CHAIN_CONFIG: Dict[Chain, Dict[str, Any]] = {
    Chain.ETHEREUM: {
        "chain_id": 1,
        "name": "Ethereum",
        "native_token": Token.ETH,
        "block_time": 12,
        "confirmations_required": 12,
        "explorer": "https://etherscan.io",
    },
    Chain.POLYGON: {
        "chain_id": 137,
        "name": "Polygon",
        "native_token": Token.MATIC,
        "block_time": 2,
        "confirmations_required": 128,
        "explorer": "https://polygonscan.com",
    },
    Chain.BASE: {
        "chain_id": 8453,
        "name": "Base",
        "native_token": Token.ETH,
        "block_time": 2,
        "confirmations_required": 12,
        "explorer": "https://basescan.org",
    },
    Chain.ARBITRUM: {
        "chain_id": 42161,
        "name": "Arbitrum One",
        "native_token": Token.ETH,
        "block_time": 0.25,
        "confirmations_required": 12,
        "explorer": "https://arbiscan.io",
    },
    Chain.OPTIMISM: {
        "chain_id": 10,
        "name": "Optimism",
        "native_token": Token.ETH,
        "block_time": 2,
        "confirmations_required": 12,
        "explorer": "https://optimistic.etherscan.io",
    },
    Chain.SOLANA: {
        "chain_id": None,
        "name": "Solana",
        "native_token": Token.SOL,
        "block_time": 0.4,
        "confirmations_required": 32,
        "explorer": "https://solscan.io",
    },
    Chain.BITCOIN: {
        "chain_id": None,
        "name": "Bitcoin",
        "native_token": Token.BTC,
        "block_time": 600,
        "confirmations_required": 3,
        "explorer": "https://blockstream.info",
    },
    Chain.AVALANCHE: {
        "chain_id": 43114,
        "name": "Avalanche C-Chain",
        "native_token": Token.AVAX,
        "block_time": 2,
        "confirmations_required": 12,
        "explorer": "https://snowtrace.io",
    },
    Chain.BNB_CHAIN: {
        "chain_id": 56,
        "name": "BNB Chain",
        "native_token": Token.BNB,
        "block_time": 3,
        "confirmations_required": 15,
        "explorer": "https://bscscan.com",
    },
}

# Token configuration
TOKEN_CONFIG: Dict[Token, Dict[str, Any]] = {
    Token.ETH: {
        "name": "Ethereum",
        "decimals": 18,
        "is_native": True,
        "chains": [Chain.ETHEREUM, Chain.BASE, Chain.ARBITRUM, Chain.OPTIMISM],
    },
    Token.BTC: {
        "name": "Bitcoin",
        "decimals": 8,
        "is_native": True,
        "chains": [Chain.BITCOIN],
    },
    Token.SOL: {
        "name": "Solana",
        "decimals": 9,
        "is_native": True,
        "chains": [Chain.SOLANA],
    },
    Token.USDC: {
        "name": "USD Coin",
        "decimals": 6,
        "is_native": False,
        "chains": [Chain.ETHEREUM, Chain.POLYGON, Chain.BASE, Chain.ARBITRUM, Chain.OPTIMISM, Chain.SOLANA, Chain.AVALANCHE],
    },
    Token.USDT: {
        "name": "Tether USD",
        "decimals": 6,
        "is_native": False,
        "chains": [Chain.ETHEREUM, Chain.POLYGON, Chain.ARBITRUM, Chain.OPTIMISM, Chain.BNB_CHAIN, Chain.AVALANCHE],
    },
    Token.DAI: {
        "name": "Dai Stablecoin",
        "decimals": 18,
        "is_native": False,
        "chains": [Chain.ETHEREUM, Chain.POLYGON, Chain.ARBITRUM, Chain.OPTIMISM],
    },
    Token.MATIC: {
        "name": "Polygon",
        "decimals": 18,
        "is_native": True,
        "chains": [Chain.POLYGON],
    },
    Token.AVAX: {
        "name": "Avalanche",
        "decimals": 18,
        "is_native": True,
        "chains": [Chain.AVALANCHE],
    },
    Token.BNB: {
        "name": "BNB",
        "decimals": 18,
        "is_native": True,
        "chains": [Chain.BNB_CHAIN],
    },
}


class CryptoPaymentRequest(BaseModel):
    """Request to create a crypto payment"""
    user_id: str = Field(..., description="User ID")
    organization_id: Optional[str] = None
    amount: Decimal = Field(..., gt=0, description="Amount in fiat currency")
    currency: str = Field(default="USD", description="Fiat currency code")
    description: Optional[str] = None

    # Optional: specify preferred chains/tokens
    preferred_chains: Optional[List[Chain]] = None
    preferred_tokens: Optional[List[Token]] = None

    # Metadata
    order_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    # Redirect URLs (for hosted checkout)
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CryptoPayment(BaseModel):
    """Crypto payment record"""
    id: Optional[str] = None
    payment_id: str = Field(..., description="Internal payment ID")
    user_id: str
    organization_id: Optional[str] = None

    # Payment details
    fiat_amount: Decimal = Field(..., description="Original fiat amount")
    fiat_currency: str = Field(default="USD")
    crypto_amount: Optional[Decimal] = None
    token: Optional[Token] = None
    chain: Optional[Chain] = None

    # Status
    status: CryptoPaymentStatus = CryptoPaymentStatus.PENDING

    # Provider info
    provider: CryptoProvider
    provider_payment_id: Optional[str] = None
    provider_checkout_url: Optional[str] = None
    provider_response: Optional[Dict[str, Any]] = None

    # Blockchain info
    wallet_address: Optional[str] = None
    tx_hash: Optional[str] = None
    confirmations: int = 0

    # Timing
    expires_at: Optional[datetime] = None
    detected_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Metadata
    description: Optional[str] = None
    order_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CryptoPaymentResponse(BaseModel):
    """Response for crypto payment creation"""
    payment_id: str
    status: CryptoPaymentStatus
    checkout_url: Optional[str] = None
    wallet_address: Optional[str] = None

    # Payment options
    supported_tokens: List[Dict[str, Any]] = []

    # Amounts (if known)
    fiat_amount: Decimal
    fiat_currency: str
    crypto_amounts: Optional[Dict[str, Decimal]] = None  # token -> amount

    # Expiration
    expires_at: Optional[datetime] = None

    # For direct payments
    qr_code_url: Optional[str] = None


class CryptoWebhookEvent(BaseModel):
    """Webhook event from crypto provider"""
    provider: CryptoProvider
    event_type: str
    payment_id: str
    provider_payment_id: str
    status: CryptoPaymentStatus

    # Transaction details
    chain: Optional[Chain] = None
    token: Optional[Token] = None
    crypto_amount: Optional[Decimal] = None
    tx_hash: Optional[str] = None
    confirmations: Optional[int] = None

    # Raw data
    raw_data: Dict[str, Any] = {}

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CryptoRefundRequest(BaseModel):
    """Request to refund a crypto payment"""
    payment_id: str
    amount: Optional[Decimal] = None  # None = full refund
    reason: str
    wallet_address: str = Field(..., description="Recipient wallet address")
    requested_by: str


class CryptoRefund(BaseModel):
    """Crypto refund record"""
    id: Optional[str] = None
    refund_id: str
    payment_id: str
    user_id: str

    # Refund details
    fiat_amount: Decimal
    crypto_amount: Optional[Decimal] = None
    token: Optional[Token] = None
    chain: Optional[Chain] = None

    # Status
    status: CryptoPaymentStatus

    # Transaction
    wallet_address: str
    tx_hash: Optional[str] = None

    # Metadata
    reason: str
    requested_by: str

    # Timestamps
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


__all__ = [
    # Enums
    "Chain",
    "Token",
    "CryptoPaymentStatus",
    "CryptoProvider",
    # Config
    "CHAIN_CONFIG",
    "TOKEN_CONFIG",
    # Models
    "CryptoPaymentRequest",
    "CryptoPayment",
    "CryptoPaymentResponse",
    "CryptoWebhookEvent",
    "CryptoRefundRequest",
    "CryptoRefund",
]
