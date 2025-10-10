"""
Wallet Repository Implementation

Handles all wallet and transaction database operations using Supabase
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import json
import logging

# Database client setup
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database.supabase_client import get_supabase_client
from .models import (
    WalletBalance, WalletTransaction, WalletCreate,
    TransactionCreate, TransactionType, WalletType,
    BlockchainNetwork, TransactionFilter, WalletStatistics
)

logger = logging.getLogger(__name__)


class WalletRepository:
    """Repository for wallet operations"""
    
    def __init__(self):
        self.client = get_supabase_client()
        self.wallets_table = "wallets"
        self.transactions_table = "wallet_transactions"
        
    async def create_wallet(self, wallet_data: WalletCreate) -> Optional[WalletBalance]:
        """Create a new wallet for user"""
        try:
            wallet_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            # Create wallet record
            wallet_dict = {
                'wallet_id': wallet_id,
                'user_id': wallet_data.user_id,
                'balance': float(wallet_data.initial_balance),
                'locked_balance': 0.0,
                'currency': wallet_data.currency,
                'wallet_type': wallet_data.wallet_type.value,
                'blockchain_address': wallet_data.blockchain_address,
                'blockchain_network': wallet_data.blockchain_network.value if wallet_data.blockchain_network else None,
                'metadata': wallet_data.metadata,
                'created_at': now.isoformat(),
                'updated_at': now.isoformat()
            }
            
            result = self.client.table(self.wallets_table).insert(wallet_dict).execute()
            
            if result.data:
                # Create initial transaction if balance > 0
                if wallet_data.initial_balance > 0:
                    await self._create_transaction(
                        TransactionCreate(
                            wallet_id=wallet_id,
                            user_id=wallet_data.user_id,
                            transaction_type=TransactionType.DEPOSIT,
                            amount=wallet_data.initial_balance,
                            description="Initial wallet funding",
                            metadata={"initial_funding": True}
                        ),
                        balance_before=Decimal(0),
                        balance_after=wallet_data.initial_balance
                    )
                
                return self._dict_to_wallet_balance(result.data[0])
                
        except Exception as e:
            logger.error(f"Error creating wallet: {e}")
            return None
            
    async def get_wallet(self, wallet_id: str) -> Optional[WalletBalance]:
        """Get wallet by ID"""
        try:
            result = self.client.table(self.wallets_table).select('*').eq('wallet_id', wallet_id).execute()
            
            if result.data and len(result.data) > 0:
                return self._dict_to_wallet_balance(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error getting wallet {wallet_id}: {e}")
            return None
            
    async def get_user_wallets(self, user_id: str, wallet_type: Optional[WalletType] = None) -> List[WalletBalance]:
        """Get all wallets for a user"""
        try:
            query = self.client.table(self.wallets_table).select('*').eq('user_id', user_id)
            
            if wallet_type:
                query = query.eq('wallet_type', wallet_type.value)
                
            query = query.order('created_at', desc=True)
            result = query.execute()
            
            wallets = []
            if result.data:
                for wallet_dict in result.data:
                    wallet = self._dict_to_wallet_balance(wallet_dict)
                    if wallet:
                        wallets.append(wallet)
            return wallets
        except Exception as e:
            logger.error(f"Error getting user wallets: {e}")
            return []
            
    async def get_primary_wallet(self, user_id: str) -> Optional[WalletBalance]:
        """Get user's primary fiat wallet"""
        wallets = await self.get_user_wallets(user_id, WalletType.FIAT)
        return wallets[0] if wallets else None
        
    async def update_balance(self, wallet_id: str, amount: Decimal, operation: str = "add") -> Optional[Decimal]:
        """Update wallet balance"""
        try:
            # Get current wallet
            wallet = await self.get_wallet(wallet_id)
            if not wallet:
                return None
                
            if operation == "add":
                new_balance = wallet.balance + amount
            elif operation == "subtract":
                if wallet.balance < amount:
                    return None
                new_balance = wallet.balance - amount
            else:
                raise ValueError(f"Invalid operation: {operation}")
                
            # Update wallet
            result = self.client.table(self.wallets_table).update({
                'balance': float(new_balance),
                'updated_at': datetime.utcnow().isoformat()
            }).eq('wallet_id', wallet_id).execute()
            
            if result.data:
                return new_balance
            return None
            
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
            return None
            
    async def deposit(
        self,
        wallet_id: str,
        amount: Decimal,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[WalletTransaction]:
        """Deposit funds to wallet"""
        try:
            # Get current balance
            wallet = await self.get_wallet(wallet_id)
            if not wallet:
                return None
                
            # Update balance
            new_balance = await self.update_balance(wallet_id, amount, "add")
            if new_balance is None:
                return None
                
            # Create transaction record
            transaction = await self._create_transaction(
                TransactionCreate(
                    wallet_id=wallet_id,
                    user_id=wallet.user_id,
                    transaction_type=TransactionType.DEPOSIT,
                    amount=amount,
                    description=description or f"Deposit: {amount}",
                    reference_id=reference_id,
                    metadata=metadata or {}
                ),
                balance_before=wallet.balance,
                balance_after=new_balance
            )
            
            return transaction
        except Exception as e:
            logger.error(f"Error depositing funds: {e}")
            return None
            
    async def withdraw(
        self,
        wallet_id: str,
        amount: Decimal,
        description: Optional[str] = None,
        destination: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[WalletTransaction]:
        """Withdraw funds from wallet"""
        try:
            # Get current balance
            wallet = await self.get_wallet(wallet_id)
            if not wallet or wallet.available_balance < amount:
                return None
                
            # Update balance
            new_balance = await self.update_balance(wallet_id, amount, "subtract")
            if new_balance is None:
                return None
                
            # Create transaction record
            if destination and metadata:
                metadata["destination"] = destination
            elif destination:
                metadata = {"destination": destination}
                
            transaction = await self._create_transaction(
                TransactionCreate(
                    wallet_id=wallet_id,
                    user_id=wallet.user_id,
                    transaction_type=TransactionType.WITHDRAW,
                    amount=amount,
                    description=description or f"Withdrawal: {amount}",
                    metadata=metadata or {}
                ),
                balance_before=wallet.balance,
                balance_after=new_balance
            )
            
            return transaction
        except Exception as e:
            logger.error(f"Error withdrawing funds: {e}")
            return None
            
    async def consume(
        self,
        wallet_id: str,
        amount: Decimal,
        description: Optional[str] = None,
        usage_record_id: Optional[int] = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[WalletTransaction]:
        """Consume credits from wallet"""
        try:
            # Get current balance
            wallet = await self.get_wallet(wallet_id)
            if not wallet or wallet.available_balance < amount:
                return None
                
            # Update balance
            new_balance = await self.update_balance(wallet_id, amount, "subtract")
            if new_balance is None:
                return None
                
            # Create transaction record
            transaction = await self._create_transaction(
                TransactionCreate(
                    wallet_id=wallet_id,
                    user_id=wallet.user_id,
                    transaction_type=TransactionType.CONSUME,
                    amount=amount,
                    description=description or f"Consumed: {amount}",
                    usage_record_id=usage_record_id,
                    metadata=metadata or {}
                ),
                balance_before=wallet.balance,
                balance_after=new_balance
            )
            
            return transaction
        except Exception as e:
            logger.error(f"Error consuming credits: {e}")
            return None
            
    async def refund(
        self,
        original_transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: str = "Refund",
        metadata: Dict[str, Any] = None
    ) -> Optional[WalletTransaction]:
        """Refund a previous transaction"""
        try:
            # Get original transaction
            result = self.client.table(self.transactions_table).select('*').eq('transaction_id', original_transaction_id).execute()
            
            if not result.data or len(result.data) == 0:
                return None
                
            original = result.data[0]
            
            # Determine refund amount
            refund_amount = amount or Decimal(str(original['amount']))
            if refund_amount > Decimal(str(original['amount'])):
                return None
                
            # Get wallet
            wallet = await self.get_wallet(original['wallet_id'])
            if not wallet:
                return None
                
            # Update balance (add back)
            new_balance = await self.update_balance(wallet.wallet_id, refund_amount, "add")
            if new_balance is None:
                return None
                
            # Create refund transaction
            refund_metadata = metadata or {}
            refund_metadata.update({
                "original_transaction_id": original_transaction_id,
                "refund_reason": reason
            })
            
            transaction = await self._create_transaction(
                TransactionCreate(
                    wallet_id=wallet.wallet_id,
                    user_id=wallet.user_id,
                    transaction_type=TransactionType.REFUND,
                    amount=refund_amount,
                    description=f"Refund: {reason}",
                    reference_id=original_transaction_id,
                    metadata=refund_metadata
                ),
                balance_before=wallet.balance,
                balance_after=new_balance
            )
            
            return transaction
        except Exception as e:
            logger.error(f"Error processing refund: {e}")
            return None
            
    async def get_transactions(self, filter_params: TransactionFilter) -> List[WalletTransaction]:
        """Get filtered transaction history"""
        try:
            query = self.client.table(self.transactions_table).select('*')
            
            if filter_params.wallet_id:
                query = query.eq('wallet_id', filter_params.wallet_id)
                
            if filter_params.user_id:
                query = query.eq('user_id', filter_params.user_id)
                
            if filter_params.transaction_type:
                query = query.eq('transaction_type', filter_params.transaction_type.value)
                
            if filter_params.start_date:
                query = query.gte('created_at', filter_params.start_date.isoformat())
                
            if filter_params.end_date:
                query = query.lte('created_at', filter_params.end_date.isoformat())
                
            if filter_params.min_amount:
                query = query.gte('amount', float(filter_params.min_amount))
                
            if filter_params.max_amount:
                query = query.lte('amount', float(filter_params.max_amount))
                
            # Add ordering and pagination
            query = query.order('created_at', desc=True).range(
                filter_params.offset,
                filter_params.offset + filter_params.limit - 1
            )
            
            result = query.execute()
            
            transactions = []
            if result.data:
                for tx_dict in result.data:
                    transaction = self._dict_to_transaction(tx_dict)
                    if transaction:
                        transactions.append(transaction)
            return transactions
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []
            
    async def get_statistics(
        self,
        wallet_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[WalletStatistics]:
        """Get wallet statistics"""
        try:
            # Get wallet
            wallet = await self.get_wallet(wallet_id)
            if not wallet:
                return None
                
            # Get transactions for statistics
            filter_params = TransactionFilter(
                wallet_id=wallet_id,
                start_date=start_date,
                end_date=end_date,
                limit=1000  # Get more transactions for statistics
            )
            transactions = await self.get_transactions(filter_params)
            
            # Calculate statistics
            stats = {
                'total_deposits': Decimal(0),
                'total_withdrawals': Decimal(0),
                'total_consumed': Decimal(0),
                'total_refunded': Decimal(0),
                'total_transfers_in': Decimal(0),
                'total_transfers_out': Decimal(0),
                'transaction_count': len(transactions),
                'blockchain_transactions': 0,
                'total_gas_fees': Decimal(0)
            }
            
            for tx in transactions:
                if tx.transaction_type == TransactionType.DEPOSIT:
                    stats['total_deposits'] += tx.amount
                elif tx.transaction_type == TransactionType.WITHDRAW:
                    stats['total_withdrawals'] += tx.amount
                elif tx.transaction_type == TransactionType.CONSUME:
                    stats['total_consumed'] += tx.amount
                elif tx.transaction_type == TransactionType.REFUND:
                    stats['total_refunded'] += tx.amount
                elif tx.transaction_type == TransactionType.TRANSFER:
                    if tx.metadata and tx.metadata.get('direction') == 'in':
                        stats['total_transfers_in'] += tx.amount
                    else:
                        stats['total_transfers_out'] += tx.amount
                        
                if tx.blockchain_tx_hash:
                    stats['blockchain_transactions'] += 1
                if tx.gas_fee:
                    stats['total_gas_fees'] += tx.gas_fee
                    
            return WalletStatistics(
                wallet_id=wallet_id,
                user_id=wallet.user_id,
                current_balance=wallet.balance,
                total_deposits=stats['total_deposits'],
                total_withdrawals=stats['total_withdrawals'],
                total_consumed=stats['total_consumed'],
                total_refunded=stats['total_refunded'],
                total_transfers_in=stats['total_transfers_in'],
                total_transfers_out=stats['total_transfers_out'],
                transaction_count=stats['transaction_count'],
                blockchain_transactions=stats['blockchain_transactions'],
                total_gas_fees=stats['total_gas_fees'],
                period_start=start_date,
                period_end=end_date
            )
        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return None
            
    async def _create_transaction(
        self,
        transaction_data: TransactionCreate,
        balance_before: Decimal,
        balance_after: Decimal
    ) -> Optional[WalletTransaction]:
        """Create transaction record"""
        try:
            transaction_id = str(uuid.uuid4())
            
            transaction_dict = {
                'transaction_id': transaction_id,
                'wallet_id': transaction_data.wallet_id,
                'user_id': transaction_data.user_id,
                'transaction_type': transaction_data.transaction_type.value,
                'amount': float(transaction_data.amount),
                'balance_before': float(balance_before),
                'balance_after': float(balance_after),
                'fee_amount': 0.0,
                'description': transaction_data.description,
                'reference_id': transaction_data.reference_id,
                'reference_type': 'usage' if transaction_data.usage_record_id else None,
                'to_wallet_id': transaction_data.to_wallet_id,
                'blockchain_txn_hash': transaction_data.blockchain_tx_hash,
                'metadata': transaction_data.metadata,
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = self.client.table(self.transactions_table).insert(transaction_dict).execute()
            
            if result.data:
                return self._dict_to_transaction(result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return None
            
    def _dict_to_wallet_balance(self, data: Dict[str, Any]) -> WalletBalance:
        """Convert database dict to WalletBalance model"""
        return WalletBalance(
            wallet_id=data['wallet_id'],
            user_id=data['user_id'],
            balance=Decimal(str(data['balance'])),
            locked_balance=Decimal(str(data.get('locked_balance', 0))),
            available_balance=Decimal(str(data['balance'])) - Decimal(str(data.get('locked_balance', 0))),
            currency=data['currency'],
            wallet_type=WalletType(data['wallet_type']),
            last_updated=datetime.fromisoformat(data['updated_at']),
            blockchain_address=data.get('blockchain_address'),
            blockchain_network=BlockchainNetwork(data['blockchain_network']) if data.get('blockchain_network') else None,
            on_chain_balance=Decimal(str(data['on_chain_balance'])) if data.get('on_chain_balance') else None,
            sync_status=data.get('sync_status')
        )
        
    def _dict_to_transaction(self, data: Dict[str, Any]) -> WalletTransaction:
        """Convert database dict to WalletTransaction model"""
        return WalletTransaction(
            transaction_id=data['transaction_id'],
            wallet_id=data['wallet_id'],
            user_id=data['user_id'],
            transaction_type=TransactionType(data['transaction_type']),
            amount=Decimal(str(data['amount'])),
            balance_before=Decimal(str(data['balance_before'])),
            balance_after=Decimal(str(data['balance_after'])),
            fee=Decimal(str(data.get('fee_amount', 0))),
            description=data.get('description'),
            reference_id=data.get('reference_id'),
            usage_record_id=data.get('reference_id') if data.get('reference_type') == 'usage' else None,
            from_wallet_id=data.get('from_wallet_id'),
            to_wallet_id=data.get('to_wallet_id'),
            blockchain_tx_hash=data.get('blockchain_txn_hash'),
            blockchain_network=None,  # Not stored in current schema
            blockchain_status=data.get('status'),
            blockchain_confirmations=data.get('blockchain_confirmation_count'),
            gas_fee=Decimal(str(data['fee_amount'])) if data.get('fee_amount') else None,
            metadata=data.get('metadata', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )