"""
Credit Service Data Repository

Data access layer - PostgreSQL + gRPC (Async)
Implements CreditRepositoryProtocol from protocols.py
"""

import logging
import os
import sys
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import json
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class CreditRepository:
    """Credit service data repository - PostgreSQL (Async)"""

    def __init__(self, config: Optional[ConfigManager] = None):
        # Use config_manager for service discovery
        if config is None:
            config = ConfigManager("credit_service")

        # Discover PostgreSQL service
        # Priority: environment variable → Consul → localhost fallback
        host, port = config.discover_service(
            service_name='postgres_service',
            default_host='localhost',
            default_port=5432,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            user_id="credit_service"
        )
        self.schema = "credit"
        self.accounts_table = "credit_accounts"
        self.transactions_table = "credit_transactions"
        self.campaigns_table = "credit_campaigns"
        self.allocations_table = "credit_allocations"

    async def initialize(self):
        """Initialize database connection"""
        logger.info("Credit repository initialized with PostgreSQL")

    async def close(self):
        """Close database connection"""
        logger.info("Credit repository database connection closed")

    # ====================
    # Credit Account Management
    # ====================

    async def create_account(self, account_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new credit account"""
        try:
            account_id = account_data.get("account_id") or f"cred_acc_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.accounts_table} (
                    account_id, user_id, organization_id, credit_type, balance,
                    total_allocated, total_consumed, total_expired, currency,
                    expiration_policy, expiration_days, is_active, metadata,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                RETURNING *
            '''

            params = [
                account_id,
                account_data.get("user_id"),
                account_data.get("organization_id"),
                account_data.get("credit_type"),
                account_data.get("balance", 0),
                account_data.get("total_allocated", 0),
                account_data.get("total_consumed", 0),
                account_data.get("total_expired", 0),
                account_data.get("currency", "CREDIT"),
                account_data.get("expiration_policy", "fixed_days"),
                account_data.get("expiration_days", 90),
                account_data.get("is_active", True),
                json.dumps(account_data.get("metadata", {})),
                now,
                now
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_dict(results[0])
            else:
                raise Exception("Failed to create credit account")

        except Exception as e:
            logger.error(f"Error creating credit account: {e}", exc_info=True)
            raise

    async def get_account_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get account by ID"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.accounts_table}
                WHERE account_id = $1
            '''

            async with self.db:
                result = await self.db.query_row(query, params=[account_id])

            if result:
                return self._row_to_dict(result)
            return None

        except Exception as e:
            logger.error(f"Error getting credit account {account_id}: {e}")
            raise

    async def get_account_by_user_type(self, user_id: str, credit_type: str) -> Optional[Dict[str, Any]]:
        """Get account by user and type"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.accounts_table}
                WHERE user_id = $1 AND credit_type = $2
            '''

            async with self.db:
                result = await self.db.query_row(query, params=[user_id, credit_type])

            if result:
                return self._row_to_dict(result)
            return None

        except Exception as e:
            logger.error(f"Error getting account for user {user_id}, type {credit_type}: {e}")
            raise

    async def get_user_accounts(self, user_id: str, filters: Dict) -> List[Dict[str, Any]]:
        """Get all accounts for user"""
        try:
            conditions = ["user_id = $1"]
            params = [user_id]
            param_count = 1

            if filters.get("credit_type"):
                param_count += 1
                conditions.append(f"credit_type = ${param_count}")
                params.append(filters["credit_type"])

            if filters.get("is_active") is not None:
                param_count += 1
                conditions.append(f"is_active = ${param_count}")
                params.append(filters["is_active"])

            if filters.get("organization_id"):
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(filters["organization_id"])

            where_clause = " AND ".join(conditions)

            query = f'''
                SELECT * FROM {self.schema}.{self.accounts_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
            '''

            async with self.db:
                results = await self.db.query(query, params=params)

            return [self._row_to_dict(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting user accounts for {user_id}: {e}")
            raise

    async def update_account_balance(self, account_id: str, balance_delta: int) -> bool:
        """Update account balance atomically"""
        try:
            now = datetime.now(timezone.utc)

            # Atomic update with balance delta
            query = f'''
                UPDATE {self.schema}.{self.accounts_table}
                SET balance = balance + $1,
                    total_allocated = CASE WHEN $1 > 0 THEN total_allocated + $1 ELSE total_allocated END,
                    total_consumed = CASE WHEN $1 < 0 THEN total_consumed + ABS($1) ELSE total_consumed END,
                    updated_at = $2
                WHERE account_id = $3 AND balance + $1 >= 0
                RETURNING balance
            '''

            params = [balance_delta, now, account_id]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                logger.info(f"Updated account {account_id} balance by {balance_delta}")
                return True
            else:
                logger.warning(f"Failed to update account {account_id} - insufficient balance or not found")
                return False

        except Exception as e:
            logger.error(f"Error updating account balance: {e}")
            raise

    # ====================
    # Transaction Management
    # ====================

    async def create_transaction(self, txn_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create transaction record"""
        try:
            transaction_id = txn_data.get("transaction_id") or f"cred_txn_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.transactions_table} (
                    transaction_id, account_id, user_id, transaction_type, amount,
                    balance_before, balance_after, reference_id, reference_type,
                    description, metadata, expires_at, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING *
            '''

            params = [
                transaction_id,
                txn_data.get("account_id"),
                txn_data.get("user_id"),
                txn_data.get("transaction_type"),
                txn_data.get("amount"),
                txn_data.get("balance_before"),
                txn_data.get("balance_after"),
                txn_data.get("reference_id"),
                txn_data.get("reference_type"),
                txn_data.get("description"),
                json.dumps(txn_data.get("metadata", {})),
                txn_data.get("expires_at"),
                now
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                logger.info(f"Created transaction {transaction_id}")
                return self._row_to_dict(results[0])
            else:
                raise Exception("Failed to create transaction")

        except Exception as e:
            logger.error(f"Error creating transaction: {e}", exc_info=True)
            raise

    async def get_user_transactions(self, user_id: str, filters: Dict) -> List[Dict[str, Any]]:
        """Get transactions for user"""
        try:
            conditions = ["user_id = $1"]
            params = [user_id]
            param_count = 1

            if filters.get("account_id"):
                param_count += 1
                conditions.append(f"account_id = ${param_count}")
                params.append(filters["account_id"])

            if filters.get("transaction_type"):
                param_count += 1
                conditions.append(f"transaction_type = ${param_count}")
                params.append(filters["transaction_type"])

            if filters.get("start_date"):
                param_count += 1
                conditions.append(f"created_at >= ${param_count}")
                params.append(filters["start_date"])

            if filters.get("end_date"):
                param_count += 1
                conditions.append(f"created_at <= ${param_count}")
                params.append(filters["end_date"])

            if filters.get("reference_type"):
                param_count += 1
                conditions.append(f"reference_type = ${param_count}")
                params.append(filters["reference_type"])

            where_clause = " AND ".join(conditions)

            limit = filters.get("limit", 100)
            offset = filters.get("offset", 0)

            query = f'''
                SELECT * FROM {self.schema}.{self.transactions_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            '''

            params.extend([limit, offset])

            async with self.db:
                results = await self.db.query(query, params=params)

            return [self._row_to_dict(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting user transactions for {user_id}: {e}")
            raise

    # ====================
    # Allocation Management
    # ====================

    async def create_allocation(self, alloc_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create allocation record"""
        try:
            allocation_id = alloc_data.get("allocation_id") or f"cred_alloc_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.allocations_table} (
                    allocation_id, campaign_id, user_id, account_id, transaction_id,
                    amount, status, expires_at, expired_amount, consumed_amount,
                    metadata, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING *
            '''

            params = [
                allocation_id,
                alloc_data.get("campaign_id"),
                alloc_data.get("user_id"),
                alloc_data.get("account_id"),
                alloc_data.get("transaction_id"),
                alloc_data.get("amount"),
                alloc_data.get("status", "completed"),
                alloc_data.get("expires_at"),
                alloc_data.get("expired_amount", 0),
                alloc_data.get("consumed_amount", 0),
                json.dumps(alloc_data.get("metadata", {})),
                now,
                now
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                logger.info(f"Created allocation {allocation_id}")
                return self._row_to_dict(results[0])
            else:
                raise Exception("Failed to create allocation")

        except Exception as e:
            logger.error(f"Error creating allocation: {e}", exc_info=True)
            raise

    async def get_expiring_allocations(self, before: datetime) -> List[Dict[str, Any]]:
        """Get allocations expiring before date"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.allocations_table}
                WHERE expires_at <= $1
                  AND status = 'completed'
                  AND (amount - consumed_amount - expired_amount) > 0
                ORDER BY expires_at ASC
            '''

            async with self.db:
                results = await self.db.query(query, params=[before])

            return [self._row_to_dict(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting expiring allocations: {e}")
            raise

    async def update_allocation_consumed(self, allocation_id: str, consumed_amount: int) -> bool:
        """Update allocation consumed amount"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                UPDATE {self.schema}.{self.allocations_table}
                SET consumed_amount = consumed_amount + $1,
                    updated_at = $2
                WHERE allocation_id = $3
                RETURNING allocation_id
            '''

            params = [consumed_amount, now, allocation_id]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                logger.info(f"Updated allocation {allocation_id} consumed amount by {consumed_amount}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error updating allocation consumed amount: {e}")
            raise

    async def update_allocation_expired(self, allocation_id: str, expired_amount: int) -> bool:
        """Update allocation expired amount"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                UPDATE {self.schema}.{self.allocations_table}
                SET expired_amount = expired_amount + $1,
                    updated_at = $2
                WHERE allocation_id = $3
                RETURNING allocation_id
            '''

            params = [expired_amount, now, allocation_id]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                logger.info(f"Updated allocation {allocation_id} expired amount by {expired_amount}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error updating allocation expired amount: {e}")
            raise

    async def get_user_allocations(self, user_id: str, filters: Dict) -> List[Dict[str, Any]]:
        """Get allocations for user"""
        try:
            conditions = ["user_id = $1"]
            params = [user_id]
            param_count = 1

            if filters.get("campaign_id"):
                param_count += 1
                conditions.append(f"campaign_id = ${param_count}")
                params.append(filters["campaign_id"])

            if filters.get("status"):
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(filters["status"])

            if filters.get("active_only"):
                conditions.append(f"(amount - consumed_amount - expired_amount) > 0")

            where_clause = " AND ".join(conditions)

            query = f'''
                SELECT * FROM {self.schema}.{self.allocations_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
            '''

            async with self.db:
                results = await self.db.query(query, params=params)

            return [self._row_to_dict(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting user allocations for {user_id}: {e}")
            raise

    # ====================
    # Campaign Management
    # ====================

    async def create_campaign(self, campaign_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create campaign"""
        try:
            campaign_id = campaign_data.get("campaign_id") or f"camp_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.campaigns_table} (
                    campaign_id, name, description, credit_type, credit_amount,
                    total_budget, allocated_amount, eligibility_rules, allocation_rules,
                    start_date, end_date, expiration_days, max_allocations_per_user,
                    is_active, created_by, metadata, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                RETURNING *
            '''

            params = [
                campaign_id,
                campaign_data.get("name"),
                campaign_data.get("description"),
                campaign_data.get("credit_type"),
                campaign_data.get("credit_amount"),
                campaign_data.get("total_budget"),
                campaign_data.get("allocated_amount", 0),
                json.dumps(campaign_data.get("eligibility_rules", {})),
                json.dumps(campaign_data.get("allocation_rules", {})),
                campaign_data.get("start_date"),
                campaign_data.get("end_date"),
                campaign_data.get("expiration_days", 90),
                campaign_data.get("max_allocations_per_user", 1),
                campaign_data.get("is_active", True),
                campaign_data.get("created_by"),
                json.dumps(campaign_data.get("metadata", {})),
                now,
                now
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                logger.info(f"Created campaign {campaign_id}")
                return self._row_to_dict(results[0])
            else:
                raise Exception("Failed to create campaign")

        except Exception as e:
            logger.error(f"Error creating campaign: {e}", exc_info=True)
            raise

    async def get_campaign_by_id(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get campaign by ID"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.campaigns_table}
                WHERE campaign_id = $1
            '''

            async with self.db:
                result = await self.db.query_row(query, params=[campaign_id])

            if result:
                return self._row_to_dict(result)
            return None

        except Exception as e:
            logger.error(f"Error getting campaign {campaign_id}: {e}")
            raise

    async def update_campaign_budget(self, campaign_id: str, amount: int) -> bool:
        """Update campaign allocated_amount"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                UPDATE {self.schema}.{self.campaigns_table}
                SET allocated_amount = allocated_amount + $1,
                    updated_at = $2
                WHERE campaign_id = $3 AND (allocated_amount + $1) <= total_budget
                RETURNING campaign_id
            '''

            params = [amount, now, campaign_id]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                logger.info(f"Updated campaign {campaign_id} budget by {amount}")
                return True
            else:
                logger.warning(f"Failed to update campaign {campaign_id} - budget exceeded or not found")
                return False

        except Exception as e:
            logger.error(f"Error updating campaign budget: {e}")
            raise

    async def update_campaign(self, campaign_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update campaign fields"""
        try:
            now = datetime.now(timezone.utc)

            # Build dynamic SET clause
            set_clauses = []
            params = []
            param_count = 0

            for key, value in updates.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                if isinstance(value, dict):
                    params.append(json.dumps(value))
                else:
                    params.append(value)

            # Add updated_at
            param_count += 1
            set_clauses.append(f"updated_at = ${param_count}")
            params.append(now)

            # Add campaign_id
            param_count += 1
            params.append(campaign_id)

            set_clause = ", ".join(set_clauses)

            query = f'''
                UPDATE {self.schema}.{self.campaigns_table}
                SET {set_clause}
                WHERE campaign_id = ${param_count}
                RETURNING *
            '''

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                logger.info(f"Updated campaign {campaign_id}")
                return self._row_to_dict(results[0])
            return None

        except Exception as e:
            logger.error(f"Error updating campaign: {e}")
            raise

    async def get_active_campaigns(self, credit_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active campaigns"""
        try:
            now = datetime.now(timezone.utc)
            conditions = ["is_active = TRUE", f"start_date <= ${1}", f"end_date >= ${2}"]
            params = [now, now]
            param_count = 2

            if credit_type:
                param_count += 1
                conditions.append(f"credit_type = ${param_count}")
                params.append(credit_type)

            where_clause = " AND ".join(conditions)

            query = f'''
                SELECT * FROM {self.schema}.{self.campaigns_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
            '''

            async with self.db:
                results = await self.db.query(query, params=params)

            return [self._row_to_dict(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting active campaigns: {e}")
            raise

    async def get_user_campaign_allocations_count(self, user_id: str, campaign_id: str) -> int:
        """Get count of allocations for user in campaign"""
        try:
            query = f'''
                SELECT COUNT(*) as count FROM {self.schema}.{self.allocations_table}
                WHERE user_id = $1 AND campaign_id = $2
            '''

            async with self.db:
                result = await self.db.query_row(query, params=[user_id, campaign_id])

            if result:
                return result.get("count", 0)
            return 0

        except Exception as e:
            logger.error(f"Error getting user campaign allocations count: {e}")
            return 0

    # ====================
    # Balance and Statistics
    # ====================

    async def get_aggregated_balance(self, user_id: str) -> Dict[str, int]:
        """Get aggregated balance by credit type"""
        try:
            query = f'''
                SELECT credit_type, SUM(balance) as total_balance
                FROM {self.schema}.{self.accounts_table}
                WHERE user_id = $1 AND is_active = TRUE
                GROUP BY credit_type
            '''

            async with self.db:
                results = await self.db.query(query, params=[user_id])

            balance_dict = {}
            if results:
                for row in results:
                    credit_type = row.get("credit_type")
                    total_balance = row.get("total_balance", 0)
                    balance_dict[credit_type] = int(total_balance)

            return balance_dict

        except Exception as e:
            logger.error(f"Error getting aggregated balance for user {user_id}: {e}")
            return {}

    async def get_available_credits_fifo(self, account_id: str) -> List[Dict[str, Any]]:
        """Get available credits in FIFO order (by expires_at) for consumption"""
        try:
            query = f'''
                SELECT a.allocation_id, a.amount, a.consumed_amount, a.expired_amount,
                       a.expires_at, a.created_at,
                       (a.amount - a.consumed_amount - a.expired_amount) as available
                FROM {self.schema}.{self.allocations_table} a
                WHERE a.account_id = $1
                  AND a.status = 'completed'
                  AND (a.amount - a.consumed_amount - a.expired_amount) > 0
                  AND (a.expires_at IS NULL OR a.expires_at > $2)
                ORDER BY a.expires_at ASC NULLS LAST, a.created_at ASC
            '''

            async with self.db:
                results = await self.db.query(query, params=[account_id, datetime.now(timezone.utc)])

            return [self._row_to_dict(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting available credits FIFO for account {account_id}: {e}")
            raise

    # ====================
    # GDPR Compliance
    # ====================

    async def delete_user_data(self, user_id: str) -> int:
        """Delete all user data (GDPR)"""
        try:
            deleted_count = 0

            # Delete allocations
            query1 = f"DELETE FROM {self.schema}.{self.allocations_table} WHERE user_id = $1"
            async with self.db:
                results = await self.db.query(query1, params=[user_id])
                if results:
                    deleted_count += len(results)

            # Delete transactions
            query2 = f"DELETE FROM {self.schema}.{self.transactions_table} WHERE user_id = $1"
            async with self.db:
                results = await self.db.query(query2, params=[user_id])
                if results:
                    deleted_count += len(results)

            # Delete accounts
            query3 = f"DELETE FROM {self.schema}.{self.accounts_table} WHERE user_id = $1"
            async with self.db:
                results = await self.db.query(query3, params=[user_id])
                if results:
                    deleted_count += len(results)

            logger.info(f"Deleted {deleted_count} credit records for user {user_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting user data for {user_id}: {e}")
            raise

    # ====================
    # Helper Methods
    # ====================

    def _row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database row to dictionary"""
        if not row:
            return {}

        result = {}
        for key, value in row.items():
            # Convert datetime objects to ISO format strings
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            # Parse JSON strings back to dicts
            elif key in ("metadata", "eligibility_rules", "allocation_rules", "billing_metadata"):
                if isinstance(value, str):
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = {}
                else:
                    result[key] = value or {}
            else:
                result[key] = value

        return result


__all__ = ["CreditRepository"]
