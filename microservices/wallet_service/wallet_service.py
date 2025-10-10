"""
Wallet Service Business Logic

Handles wallet operations, transaction management, and blockchain integration
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import uuid

from .models import (
    WalletBalance, WalletTransaction, WalletCreate, WalletUpdate,
    DepositRequest, WithdrawRequest, ConsumeRequest, TransferRequest,
    RefundRequest, BlockchainSyncRequest, TransactionFilter,
    WalletStatistics, WalletResponse, TransactionType, WalletType,
    BlockchainNetwork, BlockchainIntegration
)
from .wallet_repository import WalletRepository
from core.consul_registry import ConsulRegistry

logger = logging.getLogger(__name__)


class WalletService:
    """Main wallet service for managing digital assets"""

    def __init__(self):
        self.repository = WalletRepository()
        self.consul = None
        self._init_consul()

    def _init_consul(self):
        """Initialize Consul registry for service discovery"""
        try:
            from core.config_manager import ConfigManager
            config_manager = ConfigManager("wallet_service")
            config = config_manager.get_service_config()

            if config.consul_enabled:
                self.consul = ConsulRegistry(
                    service_name=config.service_name,
                    service_port=config.service_port,
                    consul_host=config.consul_host,
                    consul_port=config.consul_port
                )
                logger.info("Consul service discovery initialized for wallet service")
        except Exception as e:
            logger.warning(f"Failed to initialize Consul: {e}, will use fallback URLs")

    async def validate_user_exists(self, user_id: str) -> bool:
        """Validate user exists via account service API using Consul discovery"""
        try:
            import httpx

            # Use Consul discovery with fallback
            if self.consul:
                account_service_url = self.consul.get_service_address(
                    "account_service",
                    fallback_url="http://localhost:8201"
                )
            else:
                account_service_url = "http://localhost:8201"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{account_service_url}/api/v1/accounts/profile/{user_id}",
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Could not validate user {user_id}: {e}")
            # In microservices, we often proceed even if validation fails
            # This maintains service autonomy
            return True  # Assume valid if service is down
    
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