"""
Wallet Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable
from datetime import datetime
from decimal import Decimal

# Import only models (no I/O dependencies)
from .models import (
    WalletBalance,
    WalletTransaction,
    WalletCreate,
    WalletUpdate,
    TransactionFilter,
    WalletStatistics,
    TransactionType,
    WalletType,
)


# ============================================================================
# Custom Exceptions - defined here to avoid importing repository
# ============================================================================

class WalletNotFoundError(Exception):
    """Wallet not found error"""
    pass


class InsufficientBalanceError(Exception):
    """Insufficient balance for the requested operation"""
    pass


class DuplicateWalletError(Exception):
    """User already has a wallet of this type"""
    pass


class TransactionNotFoundError(Exception):
    """Transaction not found error"""
    pass


class InvalidTransactionError(Exception):
    """Invalid transaction error"""
    pass


class WalletFrozenError(Exception):
    """Wallet is frozen and cannot perform operations"""
    pass


# ============================================================================
# Repository Protocols
# ============================================================================

@runtime_checkable
class WalletRepositoryProtocol(Protocol):
    """
    Interface for Wallet Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    # Wallet Operations
    async def create_wallet(self, wallet_data: WalletCreate) -> Optional[WalletBalance]:
        """Create a new wallet for user"""
        ...

    async def get_wallet(self, wallet_id: str) -> Optional[WalletBalance]:
        """Get wallet by ID"""
        ...

    async def get_user_wallets(
        self, user_id: str, wallet_type: Optional[WalletType] = None
    ) -> List[WalletBalance]:
        """Get all wallets for a user, optionally filtered by type"""
        ...

    async def get_primary_wallet(self, user_id: str) -> Optional[WalletBalance]:
        """Get user's primary fiat wallet"""
        ...

    async def update_balance(
        self, wallet_id: str, amount: Decimal, operation: str = "add"
    ) -> Optional[Decimal]:
        """Update wallet balance (add or subtract)"""
        ...

    async def deactivate_wallet(self, wallet_id: str) -> bool:
        """Deactivate/freeze a wallet"""
        ...

    async def update_wallet_metadata(
        self, wallet_id: str, metadata: Dict[str, Any]
    ) -> bool:
        """Update wallet metadata"""
        ...

    # Transaction Operations
    async def deposit(
        self,
        wallet_id: str,
        amount: Decimal,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> Optional[WalletTransaction]:
        """Deposit funds to wallet"""
        ...

    async def withdraw(
        self,
        wallet_id: str,
        amount: Decimal,
        description: Optional[str] = None,
        destination: Optional[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> Optional[WalletTransaction]:
        """Withdraw funds from wallet"""
        ...

    async def consume(
        self,
        wallet_id: str,
        amount: Decimal,
        description: Optional[str] = None,
        usage_record_id: Optional[int] = None,
        metadata: Dict[str, Any] = None,
    ) -> Optional[WalletTransaction]:
        """Consume credits from wallet"""
        ...

    async def refund(
        self,
        original_transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: str = "Refund",
        metadata: Dict[str, Any] = None,
    ) -> Optional[WalletTransaction]:
        """Refund a previous transaction"""
        ...

    async def transfer(
        self,
        from_wallet_id: str,
        to_wallet_id: str,
        amount: Decimal,
        description: Optional[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> Optional[Tuple[WalletTransaction, WalletTransaction]]:
        """Transfer funds between wallets"""
        ...

    async def get_transactions(
        self, filter_params: TransactionFilter
    ) -> List[WalletTransaction]:
        """Get filtered transaction history"""
        ...

    async def get_statistics(
        self,
        wallet_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Optional[WalletStatistics]:
        """Get wallet statistics"""
        ...

    async def anonymize_user_transactions(self, user_id: str) -> int:
        """Anonymize user transactions for GDPR compliance"""
        ...


# ============================================================================
# Client Protocols
# ============================================================================

@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> bool:
        """Publish an event"""
        ...

    async def subscribe_to_events(
        self, pattern: str, handler: Any, durable: Optional[str] = None
    ) -> None:
        """Subscribe to events matching a pattern"""
        ...


@runtime_checkable
class AccountClientProtocol(Protocol):
    """Interface for Account Service Client"""

    async def get_account(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get account by user ID"""
        ...

    async def validate_user_exists(self, user_id: str) -> bool:
        """Validate that a user exists"""
        ...


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Exceptions
    "WalletNotFoundError",
    "InsufficientBalanceError",
    "DuplicateWalletError",
    "TransactionNotFoundError",
    "InvalidTransactionError",
    "WalletFrozenError",
    # Protocols
    "WalletRepositoryProtocol",
    "EventBusProtocol",
    "AccountClientProtocol",
]
