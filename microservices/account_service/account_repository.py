"""
Account Repository

Data access layer for account management operations.
Migrated to use PostgresClient with gRPC.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient
from google.protobuf.json_format import MessageToDict
from .models import User, SubscriptionStatus

logger = logging.getLogger(__name__)

class UserNotFoundException(Exception):
    """User not found exception"""
    pass

class DuplicateEntryException(Exception):
    """Duplicate entry exception"""
    pass


class AccountRepository:
    """
    Account-specific repository layer

    Database operations for account management using PostgresClient with gRPC.
    """

    def __init__(self):
        self.db = PostgresClient(
            host='isa-postgres-grpc',
            port=50061,
            user_id='account_service'
        )
        self.schema = "account"
        self.users_table = "users"

    def _convert_proto_jsonb(self, jsonb_raw):
        """Convert proto JSONB to Python dict"""
        if hasattr(jsonb_raw, 'fields'):
            return MessageToDict(jsonb_raw)
        return jsonb_raw if jsonb_raw else {}

    def _row_to_user(self, row: Dict[str, Any]) -> User:
        """Convert database row to User model"""
        # Handle preferences JSONB conversion
        preferences = row.get('preferences', {})
        if hasattr(preferences, 'fields'):
            preferences = MessageToDict(preferences)
        elif not preferences:
            preferences = {}

        return User(
            user_id=row["user_id"],
            email=row.get("email"),
            name=row.get("name"),
            subscription_status=SubscriptionStatus(row.get("subscription_status", "free")),
            is_active=row.get("is_active", True),
            preferences=preferences,
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )

    async def get_account_by_id(self, user_id: str) -> Optional[User]:
        """Get account by user ID"""
        try:
            with self.db:
                result = self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.users_table} WHERE user_id = $1 AND is_active = TRUE",
                    [user_id],
                    schema=self.schema
                )

            if result:
                return self._row_to_user(result)
            return None

        except Exception as e:
            logger.error(f"Failed to get account by ID {user_id}: {e}")
            return None

    async def get_account_by_email(self, email: str) -> Optional[User]:
        """Get account by email"""
        try:
            with self.db:
                result = self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.users_table} WHERE email = $1 AND is_active = TRUE",
                    [email],
                    schema=self.schema
                )

            if result:
                return self._row_to_user(result)
            return None

        except Exception as e:
            logger.error(f"Failed to get account by email {email}: {e}")
            return None

    async def ensure_account_exists(
        self,
        user_id: str,
        email: str,
        name: str,
        subscription_plan: SubscriptionStatus = SubscriptionStatus.FREE
    ) -> User:
        """
        Ensure user account exists, create if not found

        Following auth_service pattern for database operations
        """
        try:
            # First try to get existing user
            existing_user = await self.get_account_by_id(user_id)
            if existing_user:
                logger.info(f"Account already exists: {user_id}")
                return existing_user

            # Check for email conflicts
            email_user = await self.get_account_by_email(email)
            if email_user:
                raise DuplicateEntryException(f"Email {email} already exists for different user")

            # Create new user - let database set timestamps
            new_user_data = {
                "user_id": user_id,
                "email": email,
                "name": name,
                "subscription_status": subscription_plan.value,
                "is_active": True,
                "preferences": {}  # Empty dict, not string
            }

            with self.db:
                count = self.db.insert_into(self.users_table, [new_user_data], schema=self.schema)

            if count is not None and count > 0:
                logger.info(f"New account created: {user_id}")
                # Re-query to get the complete record with timestamps
                created_user = await self.get_account_by_id(user_id)
                if created_user:
                    return created_user

            raise Exception("Failed to create user account")

        except DuplicateEntryException:
            raise
        except Exception as e:
            logger.error(f"Error ensuring account exists: {e}")
            raise

    async def update_account_profile(self, user_id: str, update_data: Dict[str, Any]) -> Optional[User]:
        """Update account profile information"""
        try:
            # Check if account exists
            existing_account = await self.get_account_by_id(user_id)
            if not existing_account:
                raise UserNotFoundException(f"Account not found: {user_id}")

            # Filter allowed fields
            allowed_fields = ['name', 'email', 'subscription_status']
            filtered_update = {k: v for k, v in update_data.items() if k in allowed_fields and v is not None}

            if not filtered_update:
                return existing_account  # No updates needed

            # Build SET clause
            set_parts = []
            values = []
            for i, (field, value) in enumerate(filtered_update.items(), start=1):
                set_parts.append(f"{field} = ${i}")
                values.append(value)

            # Add updated_at
            set_parts.append(f"updated_at = ${len(values) + 1}")
            values.append(datetime.now(tz=timezone.utc))
            values.append(user_id)  # For WHERE clause

            set_clause = ", ".join(set_parts)

            with self.db:
                self.db.execute(
                    f"UPDATE {self.schema}.{self.users_table} SET {set_clause} WHERE user_id = ${len(values)}",
                    values,
                    schema=self.schema
                )

            # Return updated user
            return await self.get_account_by_id(user_id)

        except Exception as e:
            logger.error(f"Failed to update account profile {user_id}: {e}")
            return None

    async def activate_account(self, user_id: str) -> bool:
        """Activate user account"""
        try:
            now = datetime.now(tz=timezone.utc)

            with self.db:
                self.db.execute(
                    f"UPDATE {self.schema}.{self.users_table} SET is_active = TRUE, updated_at = $1 WHERE user_id = $2",
                    [now, user_id],
                    schema=self.schema
                )

            return True

        except Exception as e:
            logger.error(f"Failed to activate account {user_id}: {e}")
            return False

    async def deactivate_account(self, user_id: str) -> bool:
        """Deactivate user account"""
        try:
            now = datetime.now(tz=timezone.utc)

            with self.db:
                self.db.execute(
                    f"UPDATE {self.schema}.{self.users_table} SET is_active = FALSE, updated_at = $1 WHERE user_id = $2",
                    [now, user_id],
                    schema=self.schema
                )

            return True

        except Exception as e:
            logger.error(f"Failed to deactivate account {user_id}: {e}")
            return False

    async def update_account_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update account preferences"""
        try:
            # Get current preferences and merge with new ones
            existing_account = await self.get_account_by_id(user_id)
            if not existing_account:
                return False

            current_prefs = getattr(existing_account, 'preferences', {})
            updated_prefs = {**current_prefs, **preferences}

            now = datetime.now(tz=timezone.utc)

            with self.db:
                self.db.execute(
                    f"UPDATE {self.schema}.{self.users_table} SET preferences = $1, updated_at = $2 WHERE user_id = $3",
                    [updated_prefs, now, user_id],
                    schema=self.schema
                )

            return True

        except Exception as e:
            logger.error(f"Failed to update account preferences {user_id}: {e}")
            return False

    async def delete_account(self, user_id: str) -> bool:
        """Delete account (soft delete by deactivating)"""
        return await self.deactivate_account(user_id)

    async def list_accounts(
        self,
        limit: int = 50,
        offset: int = 0,
        is_active: Optional[bool] = None,
        subscription_status: Optional[SubscriptionStatus] = None,
        search: Optional[str] = None
    ) -> List[User]:
        """List accounts with pagination"""
        try:
            # Build query conditions
            conditions = []
            params = []
            param_count = 1

            if is_active is not None:
                conditions.append(f"is_active = ${param_count}")
                params.append(is_active)
                param_count += 1

            if subscription_status is not None:
                conditions.append(f"subscription_status = ${param_count}")
                params.append(subscription_status.value)
                param_count += 1

            if search is not None:
                conditions.append(f"(name ILIKE ${param_count} OR email ILIKE ${param_count})")
                params.append(f"%{search}%")
                param_count += 1

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            # Add pagination
            params.append(limit)
            params.append(offset)

            query = f"""
                SELECT * FROM {self.schema}.{self.users_table}
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count} OFFSET ${param_count + 1}
            """

            with self.db:
                rows = self.db.query(query, params, schema=self.schema)

            users = []
            if rows:
                for row in rows:
                    users.append(self._row_to_user(row))

            return users

        except Exception as e:
            logger.error(f"Failed to list accounts: {e}")
            return []

    async def search_accounts(self, query: str, limit: int = 50) -> List[User]:
        """Search accounts by name or email"""
        try:
            search_pattern = f"%{query}%"

            sql = f"""
                SELECT * FROM {self.schema}.{self.users_table}
                WHERE (name ILIKE $1 OR email ILIKE $1) AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT $2
            """

            with self.db:
                rows = self.db.query(sql, [search_pattern, limit], schema=self.schema)

            users = []
            if rows:
                for row in rows:
                    users.append(self._row_to_user(row))

            return users

        except Exception as e:
            logger.error(f"Failed to search accounts: {e}")
            return []

    async def get_account_stats(self) -> Dict[str, Any]:
        """Get account statistics"""
        try:
            # Get total and active counts
            with self.db:
                total_row = self.db.query_row(
                    f"SELECT COUNT(*) as total FROM {self.schema}.{self.users_table}",
                    [],
                    schema=self.schema
                )
                active_row = self.db.query_row(
                    f"SELECT COUNT(*) as active FROM {self.schema}.{self.users_table} WHERE is_active = TRUE",
                    [],
                    schema=self.schema
                )
                subscription_rows = self.db.query(
                    f"SELECT subscription_status, COUNT(*) as count FROM {self.schema}.{self.users_table} GROUP BY subscription_status",
                    [],
                    schema=self.schema
                )

            total_accounts = total_row['total'] if total_row else 0
            active_accounts = active_row['active'] if active_row else 0
            inactive_accounts = total_accounts - active_accounts

            accounts_by_subscription = {}
            if subscription_rows:
                for row in subscription_rows:
                    accounts_by_subscription[row['subscription_status']] = row['count']

            return {
                "total_accounts": total_accounts,
                "active_accounts": active_accounts,
                "inactive_accounts": inactive_accounts,
                "accounts_by_subscription": accounts_by_subscription,
                "recent_registrations_7d": 0,  # Would need more complex query
                "recent_registrations_30d": 0  # Would need more complex query
            }

        except Exception as e:
            logger.error(f"Failed to get account stats: {e}")
            return {
                "total_accounts": 0,
                "active_accounts": 0,
                "inactive_accounts": 0,
                "accounts_by_subscription": {},
                "recent_registrations_7d": 0,
                "recent_registrations_30d": 0
            }
