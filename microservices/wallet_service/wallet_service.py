"""
Wallet Service Business Logic

Handles wallet operations, transaction management, and blockchain integration.

Uses dependency injection for testability:
- Repository is injected, not created at import time
- Event publishers are lazily loaded
"""

from typing import TYPE_CHECKING, Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
import uuid

from core.nats_client import Event

from .models import (
    WalletBalance, WalletTransaction, WalletCreate, WalletUpdate,
    DepositRequest, WithdrawRequest, ConsumeRequest, TransferRequest,
    RefundRequest, BlockchainSyncRequest, TransactionFilter,
    WalletStatistics, WalletResponse, TransactionType, WalletType,
    BlockchainNetwork, BlockchainIntegration
)

# Import protocols (no I/O dependencies) - NOT the concrete repository!
from .protocols import (
    WalletRepositoryProtocol,
    EventBusProtocol,
    AccountClientProtocol,
    WalletNotFoundError,
    InsufficientBalanceError,
    DuplicateWalletError,
)

# Type checking imports (not executed at runtime)
if TYPE_CHECKING:
    from core.config_manager import ConfigManager
    from core.nats_client import Event

logger = logging.getLogger(__name__)


class WalletServiceError(Exception):
    """Base exception for wallet service errors"""
    pass


class WalletValidationError(WalletServiceError):
    """Validation error"""
    pass


class WalletService:
    """
    Main wallet service for managing digital assets.

    Handles all business operations while delegating
    data access to the repository layer.
    """

    def __init__(
        self,
        repository: Optional[WalletRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        account_client: Optional[AccountClientProtocol] = None,
    ):
        """
        Initialize service with injected dependencies.

        Args:
            repository: Repository (inject mock for testing)
            event_bus: Event bus for publishing events
            account_client: Account service client for user validation
        """
        self.repository = repository  # Will be set by factory if None
        self.repo = repository  # Alias for backward compatibility
        self.event_bus = event_bus
        self.account_client = account_client
        self._event_publishers_loaded = False

    def _lazy_load_event_publishers(self):
        """Lazy load event publishers to avoid import-time I/O"""
        if not self._event_publishers_loaded:
            try:
                from .events.publishers import (
                    publish_wallet_created,
                    publish_deposit_completed,
                    publish_tokens_deducted,
                )
                self._publish_wallet_created = publish_wallet_created
                self._publish_deposit_completed = publish_deposit_completed
                self._publish_tokens_deducted = publish_tokens_deducted
            except ImportError:
                self._publish_wallet_created = None
                self._publish_deposit_completed = None
                self._publish_tokens_deducted = None
            self._event_publishers_loaded = True

    async def validate_user_exists(self, user_id: str) -> bool:
        """Validate user exists via account service"""
        if not self.account_client:
            logger.warning("Account client not configured, skipping user validation")
            return True

        try:
            user = await self.account_client.get_account(user_id)
            return user is not None
        except Exception as e:
            logger.warning(f"Failed to validate user: {e}")
            return True  # Allow operation to proceed if validation fails
    
    async def create_wallet(self, wallet_data: WalletCreate) -> WalletResponse:
        """Create a new wallet for user"""
        try:
            # Check if user already has a wallet of this type
            existing_wallets = await self.repository.get_user_wallets(
                wallet_data.user_id, wallet_data.wallet_type
            )
            
            if existing_wallets and wallet_data.wallet_type == WalletType.FIAT:
                # User can only have one fiat wallet
                return WalletResponse(
                    success=False,
                    message="User already has a fiat wallet",
                    wallet_id=existing_wallets[0].wallet_id,
                    balance=existing_wallets[0].balance
                )
                
            # Create wallet
            wallet = await self.repository.create_wallet(wallet_data)

            if wallet:
                # Publish wallet.created event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type="wallet.created",
                            source="wallet_service",
                            data={
                                "wallet_id": wallet.wallet_id,
                                "user_id": wallet.user_id,
                                "wallet_type": wallet.wallet_type.value,
                                "currency": wallet.currency,
                                "balance": float(wallet.balance),
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                        logger.info(f"Published wallet.created event for wallet {wallet.wallet_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish wallet.created event: {e}")

                # Future: blockchain wallet preparation

                return WalletResponse(
                    success=True,
                    message="Wallet created successfully",
                    wallet_id=wallet.wallet_id,
                    balance=wallet.balance,
                    data={"wallet": wallet.model_dump()}
                )
            else:
                return WalletResponse(
                    success=False,
                    message="Failed to create wallet"
                )
                
        except Exception as e:
            logger.error(f"Error creating wallet: {e}")
            return WalletResponse(
                success=False,
                message=f"Error creating wallet: {str(e)}"
            )
            
    async def get_wallet(self, wallet_id: str) -> Optional[WalletBalance]:
        """Get wallet details"""
        return await self.repository.get_wallet(wallet_id)
        
    async def get_user_wallets(self, user_id: str) -> List[WalletBalance]:
        """Get all wallets for a user"""
        return await self.repository.get_user_wallets(user_id)
        
    async def get_balance(self, wallet_id: str) -> WalletResponse:
        """Get wallet balance"""
        try:
            wallet = await self.repository.get_wallet(wallet_id)
            
            if wallet:
                # Future: blockchain sync
                    
                return WalletResponse(
                    success=True,
                    message="Balance retrieved successfully",
                    wallet_id=wallet.wallet_id,
                    balance=wallet.available_balance,
                    data={
                        "balance": float(wallet.balance),
                        "locked_balance": float(wallet.locked_balance),
                        "available_balance": float(wallet.available_balance),
                        "currency": wallet.currency,
                        "on_chain_balance": float(wallet.on_chain_balance) if wallet.on_chain_balance else None
                    }
                )
            else:
                return WalletResponse(
                    success=False,
                    message="Wallet not found"
                )
                
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return WalletResponse(
                success=False,
                message=f"Error getting balance: {str(e)}"
            )
            
    async def deposit(self, wallet_id: str, request: DepositRequest) -> WalletResponse:
        """Deposit funds to wallet"""
        try:
            transaction = await self.repository.deposit(
                wallet_id=wallet_id,
                amount=request.amount,
                description=request.description,
                reference_id=request.reference_id,
                metadata=request.metadata
            )

            if transaction:
                # Publish wallet.deposited event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type="wallet.deposited",
                            source="wallet_service",
                            data={
                                "wallet_id": wallet_id,
                                "user_id": transaction.user_id,
                                "transaction_id": transaction.transaction_id,
                                "amount": float(request.amount),
                                "balance_before": float(transaction.balance_before),
                                "balance_after": float(transaction.balance_after),
                                "description": request.description,
                                "reference_id": request.reference_id,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                        logger.info(f"Published wallet.deposited event for wallet {wallet_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish wallet.deposited event: {e}")

                return WalletResponse(
                    success=True,
                    message=f"Deposited {request.amount} successfully",
                    wallet_id=wallet_id,
                    balance=transaction.balance_after,
                    transaction_id=transaction.transaction_id,
                    data={"transaction": transaction.model_dump()}
                )
            else:
                return WalletResponse(
                    success=False,
                    message="Failed to deposit funds"
                )
                
        except Exception as e:
            logger.error(f"Error depositing funds: {e}")
            return WalletResponse(
                success=False,
                message=f"Error depositing funds: {str(e)}"
            )
            
    async def withdraw(self, wallet_id: str, request: WithdrawRequest) -> WalletResponse:
        """Withdraw funds from wallet"""
        try:
            # Check if blockchain withdrawal
            wallet = await self.repository.get_wallet(wallet_id)
            if not wallet:
                return WalletResponse(success=False, message="Wallet not found")
                
            # Process withdrawal
            transaction = await self.repository.withdraw(
                wallet_id=wallet_id,
                amount=request.amount,
                description=request.description,
                destination=request.destination,
                metadata=request.metadata
            )

            if transaction:
                # Publish wallet.withdrawn event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type="wallet.withdrawn",
                            source="wallet_service",
                            data={
                                "wallet_id": wallet_id,
                                "user_id": transaction.user_id,
                                "transaction_id": transaction.transaction_id,
                                "amount": float(request.amount),
                                "balance_before": float(transaction.balance_before),
                                "balance_after": float(transaction.balance_after),
                                "destination": request.destination,
                                "description": request.description,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                        logger.info(f"Published wallet.withdrawn event for wallet {wallet_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish wallet.withdrawn event: {e}")

                # Future: blockchain transfer

                return WalletResponse(
                    success=True,
                    message=f"Withdrew {request.amount} successfully",
                    wallet_id=wallet_id,
                    balance=transaction.balance_after,
                    transaction_id=transaction.transaction_id,
                    data={"transaction": transaction.model_dump()}
                )
            else:
                return WalletResponse(
                    success=False,
                    message="Insufficient balance or withdrawal failed"
                )
                
        except Exception as e:
            logger.error(f"Error withdrawing funds: {e}")
            return WalletResponse(
                success=False,
                message=f"Error withdrawing funds: {str(e)}"
            )
            
    async def consume(self, wallet_id: str, request: ConsumeRequest) -> WalletResponse:
        """Consume credits/tokens from wallet"""
        try:
            # For backward compatibility, also accept user_id and find primary wallet
            if not wallet_id:
                return WalletResponse(
                    success=False,
                    message="Wallet ID required"
                )
                
            transaction = await self.repository.consume(
                wallet_id=wallet_id,
                amount=request.amount,
                description=request.description,
                usage_record_id=request.usage_record_id,
                metadata=request.metadata
            )

            if transaction:
                # Publish wallet.consumed event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type="wallet.consumed",
                            source="wallet_service",
                            data={
                                "wallet_id": wallet_id,
                                "user_id": transaction.user_id,
                                "transaction_id": transaction.transaction_id,
                                "amount": float(request.amount),
                                "balance_before": float(transaction.balance_before),
                                "balance_after": float(transaction.balance_after),
                                "description": request.description,
                                "usage_record_id": request.usage_record_id,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                        logger.info(f"Published wallet.consumed event for wallet {wallet_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish wallet.consumed event: {e}")

                return WalletResponse(
                    success=True,
                    message=f"Consumed {request.amount} successfully",
                    wallet_id=wallet_id,
                    balance=transaction.balance_after,
                    transaction_id=transaction.transaction_id,
                    data={
                        "transaction": transaction.model_dump(),
                        "remaining_balance": float(transaction.balance_after)
                    }
                )
            else:
                return WalletResponse(
                    success=False,
                    message="Insufficient balance"
                )
                
        except Exception as e:
            logger.error(f"Error consuming credits: {e}")
            return WalletResponse(
                success=False,
                message=f"Error consuming credits: {str(e)}"
            )
            
    async def consume_by_user(self, user_id: str, request: ConsumeRequest) -> WalletResponse:
        """Consume credits from user's primary wallet (backward compatibility)"""
        try:
            # Get user's primary fiat wallet
            wallet = await self.repository.get_primary_wallet(user_id)
            if not wallet:
                # Create default wallet if doesn't exist
                create_result = await self.create_wallet(
                    WalletCreate(
                        user_id=user_id,
                        wallet_type=WalletType.FIAT,
                        initial_balance=Decimal(0),
                        currency="CREDIT"
                    )
                )
                if not create_result.success:
                    return create_result
                wallet = await self.repository.get_primary_wallet(user_id)
                
            return await self.consume(wallet.wallet_id, request)
            
        except Exception as e:
            logger.error(f"Error consuming credits for user: {e}")
            return WalletResponse(
                success=False,
                message=f"Error consuming credits: {str(e)}"
            )
            
    async def refund(self, original_transaction_id: str, request: RefundRequest) -> WalletResponse:
        """Refund a previous transaction"""
        try:
            transaction = await self.repository.refund(
                original_transaction_id=original_transaction_id,
                amount=request.amount,
                reason=request.reason,
                metadata=request.metadata
            )

            if transaction:
                # Publish wallet.refunded event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type="wallet.refunded",
                            source="wallet_service",
                            data={
                                "wallet_id": transaction.wallet_id,
                                "user_id": transaction.user_id,
                                "transaction_id": transaction.transaction_id,
                                "original_transaction_id": original_transaction_id,
                                "amount": float(transaction.amount),
                                "balance_before": float(transaction.balance_before),
                                "balance_after": float(transaction.balance_after),
                                "reason": request.reason,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                        logger.info(f"Published wallet.refunded event for transaction {original_transaction_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish wallet.refunded event: {e}")

                return WalletResponse(
                    success=True,
                    message=f"Refunded {transaction.amount} successfully",
                    wallet_id=transaction.wallet_id,
                    balance=transaction.balance_after,
                    transaction_id=transaction.transaction_id,
                    data={"transaction": transaction.model_dump()}
                )
            else:
                return WalletResponse(
                    success=False,
                    message="Failed to process refund"
                )
                
        except Exception as e:
            logger.error(f"Error processing refund: {e}")
            return WalletResponse(
                success=False,
                message=f"Error processing refund: {str(e)}"
            )
            
    async def transfer(self, from_wallet_id: str, request: TransferRequest) -> WalletResponse:
        """Transfer funds between wallets"""
        try:
            result = await self.repository.transfer(
                from_wallet_id=from_wallet_id,
                to_wallet_id=request.to_wallet_id,
                amount=request.amount,
                description=request.description,
                metadata=request.metadata
            )

            if result:
                from_transaction, to_transaction = result

                # Publish wallet.transferred event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type="wallet.transferred",
                            source="wallet_service",
                            data={
                                "from_wallet_id": from_wallet_id,
                                "to_wallet_id": request.to_wallet_id,
                                "from_user_id": from_transaction.user_id,
                                "to_user_id": to_transaction.user_id,
                                "amount": float(request.amount),
                                "from_transaction_id": from_transaction.transaction_id,
                                "to_transaction_id": to_transaction.transaction_id,
                                "from_balance_after": float(from_transaction.balance_after),
                                "to_balance_after": float(to_transaction.balance_after),
                                "description": request.description,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                        logger.info(f"Published wallet.transferred event: {from_wallet_id} → {request.to_wallet_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish wallet.transferred event: {e}")

                return WalletResponse(
                    success=True,
                    message=f"Transferred {request.amount} successfully",
                    wallet_id=from_wallet_id,
                    balance=from_transaction.balance_after,
                    transaction_id=from_transaction.transaction_id,
                    data={
                        "from_transaction": from_transaction.model_dump(),
                        "to_transaction": to_transaction.model_dump()
                    }
                )
            else:
                return WalletResponse(
                    success=False,
                    message="Transfer failed - check balance and wallet IDs"
                )
                
        except Exception as e:
            logger.error(f"Error processing transfer: {e}")
            return WalletResponse(
                success=False,
                message=f"Error processing transfer: {str(e)}"
            )
            
    async def get_transactions(
        self,
        filter_params: TransactionFilter
    ) -> List[WalletTransaction]:
        """Get filtered transaction history"""
        return await self.repository.get_transactions(filter_params)
        
    async def get_user_transactions(
        self,
        user_id: str,
        transaction_type: Optional[TransactionType] = None,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[WalletTransaction]:
        """Get user's transaction history across all wallets"""
        filter_params = TransactionFilter(
            user_id=user_id,
            transaction_type=transaction_type,
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date
        )
        return await self.repository.get_transactions(filter_params)
        
    async def get_statistics(
        self,
        wallet_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[WalletStatistics]:
        """Get wallet statistics"""
        return await self.repository.get_statistics(wallet_id, start_date, end_date)
        
    async def get_user_statistics(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get aggregated statistics for all user wallets"""
        try:
            wallets = await self.repository.get_user_wallets(user_id)
            
            total_stats = {
                "total_balance": Decimal(0),
                "total_deposits": Decimal(0),
                "total_withdrawals": Decimal(0),
                "total_consumed": Decimal(0),
                "total_refunded": Decimal(0),
                "transaction_count": 0,
                "wallets": []
            }
            
            for wallet in wallets:
                stats = await self.repository.get_statistics(
                    wallet.wallet_id, start_date, end_date
                )
                if stats:
                    total_stats["total_balance"] += wallet.balance
                    total_stats["total_deposits"] += stats.total_deposits
                    total_stats["total_withdrawals"] += stats.total_withdrawals
                    total_stats["total_consumed"] += stats.total_consumed
                    total_stats["total_refunded"] += stats.total_refunded
                    total_stats["transaction_count"] += stats.transaction_count
                    total_stats["wallets"].append({
                        "wallet_id": wallet.wallet_id,
                        "wallet_type": wallet.wallet_type.value,
                        "currency": wallet.currency,
                        "balance": float(wallet.balance),
                        "statistics": stats.model_dump()
                    })
                    
            return total_stats
            
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {}
            
    async def sync_blockchain(self, request: BlockchainSyncRequest) -> WalletResponse:
        """Sync wallet with blockchain"""
        try:
            wallet = await self.repository.get_wallet(request.wallet_id)
            if not wallet:
                return WalletResponse(success=False, message="Wallet not found")
                
            # Update blockchain info if needed
            if request.blockchain_address != wallet.blockchain_address:
                # Update wallet with new blockchain address
                wallet.blockchain_address = request.blockchain_address
                wallet.blockchain_network = request.blockchain_network
                
            # Future: blockchain sync
            result = None
            
            if result:
                return WalletResponse(
                    success=True,
                    message="Blockchain sync completed",
                    wallet_id=wallet.wallet_id,
                    balance=wallet.balance,
                    data=result
                )
            else:
                return WalletResponse(
                    success=False,
                    message="Blockchain sync failed"
                )
                
        except Exception as e:
            logger.error(f"Error syncing blockchain: {e}")
            return WalletResponse(
                success=False,
                message=f"Error syncing blockchain: {str(e)}"
            )
            
    # Future: blockchain wallet preparation methods will be added here
            
    # Future: blockchain sync methods will be added here
            
    # Future: blockchain transfer methods will be added here