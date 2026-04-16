"""
Account Repository - Async Version

Data access layer for account management operations.
Uses AsyncPostgresClient for true non-blocking database access.

Note: Account service is the identity anchor only.
Subscription data is managed by subscription_service.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging
import asyncio
import json
import uuid
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager
from google.protobuf.json_format import MessageToDict
from .models import User, AdminNote
from .protocols import DuplicateEntryError, UserNotFoundError

logger = logging.getLogger(__name__)

# Legacy aliases for backward compatibility
UserNotFoundException = UserNotFoundError
DuplicateEntryException = DuplicateEntryError


class AccountRepository:
    """
    Account-specific repository layer

    Database operations for account management using PostgresClient with gRPC.
    This repository handles identity data only - no subscription data.
    """

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("account_service")

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
            database=os.getenv("POSTGRES_DB", "isa_platform"),
            username=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            user_id='account_service',
            min_pool_size=1,
            max_pool_size=2,
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
        preferences = row.get('preferences', {})
        if hasattr(preferences, 'fields'):
            preferences = MessageToDict(preferences)
        elif not preferences:
            preferences = {}

        # Parse admin_roles (JSONB column, may be None, list, or string)
        admin_roles = row.get('admin_roles')
        if isinstance(admin_roles, str):
            try:
                admin_roles = json.loads(admin_roles)
            except (json.JSONDecodeError, TypeError):
                admin_roles = None
        elif hasattr(admin_roles, 'fields'):
            admin_roles = MessageToDict(admin_roles)

        return User(
            user_id=row["user_id"],
            email=row.get("email"),
            name=row.get("name"),
            is_active=row.get("is_active", True),
            admin_roles=admin_roles if admin_roles else None,
            preferences=preferences,
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )

    async def get_account_by_id(self, user_id: str) -> Optional[User]:
        """Get account by user ID"""
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.users_table} WHERE user_id = $1 AND is_active = TRUE",
                    params=[user_id]
                )

            if result:
                return self._row_to_user(result)
            return None

        except Exception as e:
            logger.error(f"Failed to get account by ID {user_id}: {e}")
            return None

    async def get_account_by_id_include_inactive(self, user_id: str) -> Optional[User]:
        """Get account by user ID including inactive accounts"""
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.users_table} WHERE user_id = $1",
                    params=[user_id]
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
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.users_table} WHERE email = $1 AND is_active = TRUE",
                    params=[email]
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
        name: str
    ) -> User:
        """
        Ensure user account exists, create if not found

        Note: No subscription_plan parameter - subscription is managed by subscription_service
        """
        try:
            existing_user = await self.get_account_by_id(user_id)
            if existing_user:
                logger.info(f"Account already exists: {user_id}")
                return existing_user

            email_user = await self.get_account_by_email(email)
            if email_user:
                raise DuplicateEntryException(f"Email {email} already exists for different user")

            async with self.db:
                await self.db.execute(
                    f"""INSERT INTO {self.schema}.{self.users_table}
                        (user_id, email, name, is_active, preferences)
                        VALUES ($1, $2, $3, $4, $5)""",
                    params=[user_id, email, name, True, {}]
                )

            logger.info(f"New account created: {user_id}")
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
            existing_account = await self.get_account_by_id(user_id)
            if not existing_account:
                raise UserNotFoundException(f"Account not found: {user_id}")

            # Only allow updating identity fields, not subscription
            allowed_fields = ['name', 'email']
            filtered_update = {k: v for k, v in update_data.items() if k in allowed_fields and v is not None}

            if not filtered_update:
                return existing_account

            set_parts = []
            values = []
            for i, (field, value) in enumerate(filtered_update.items(), start=1):
                set_parts.append(f"{field} = ${i}")
                values.append(value)

            set_parts.append(f"updated_at = ${len(values) + 1}")
            values.append(datetime.now(tz=timezone.utc))
            values.append(user_id)

            set_clause = ", ".join(set_parts)

            async with self.db:
                await self.db.execute(
                    f"UPDATE {self.schema}.{self.users_table} SET {set_clause} WHERE user_id = ${len(values)}",
                    params=values
                )

            return await self.get_account_by_id(user_id)

        except Exception as e:
            logger.error(f"Failed to update account profile {user_id}: {e}")
            return None

    async def activate_account(self, user_id: str) -> bool:
        """Activate user account"""
        try:
            now = datetime.now(tz=timezone.utc)

            async with self.db:
                await self.db.execute(
                    f"UPDATE {self.schema}.{self.users_table} SET is_active = TRUE, updated_at = $1 WHERE user_id = $2",
                    params=[now, user_id]
                )

            return True

        except Exception as e:
            logger.error(f"Failed to activate account {user_id}: {e}")
            return False

    async def deactivate_account(self, user_id: str) -> bool:
        """Deactivate user account"""
        try:
            now = datetime.now(tz=timezone.utc)

            async with self.db:
                await self.db.execute(
                    f"UPDATE {self.schema}.{self.users_table} SET is_active = FALSE, updated_at = $1 WHERE user_id = $2",
                    params=[now, user_id]
                )

            return True

        except Exception as e:
            logger.error(f"Failed to deactivate account {user_id}: {e}")
            return False

    async def update_account_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update account preferences"""
        try:
            existing_account = await self.get_account_by_id(user_id)
            if not existing_account:
                return False

            current_prefs = getattr(existing_account, 'preferences', {})
            updated_prefs = {**current_prefs, **preferences}

            now = datetime.now(tz=timezone.utc)

            async with self.db:
                await self.db.execute(
                    f"UPDATE {self.schema}.{self.users_table} SET preferences = $1, updated_at = $2 WHERE user_id = $3",
                    params=[updated_prefs, now, user_id]
                )

            return True

        except Exception as e:
            logger.error(f"Failed to update account preferences {user_id}: {e}")
            return False

    async def get_custom_instructions(self, user_id: str) -> str:
        """Get user's custom instructions from preferences (#260)"""
        account = await self.get_account_by_id(user_id)
        if not account:
            raise UserNotFoundError(f"Account not found: {user_id}")
        prefs = getattr(account, 'preferences', {}) or {}
        return prefs.get('custom_instructions', '')

    async def set_custom_instructions(self, user_id: str, instructions: str) -> bool:
        """Set user's custom instructions in preferences (#260)"""
        return await self.update_account_preferences(user_id, {'custom_instructions': instructions})

    async def delete_account(self, user_id: str) -> bool:
        """Delete account (soft delete by deactivating)"""
        return await self.deactivate_account(user_id)

    async def list_accounts(
        self,
        limit: int = 50,
        offset: int = 0,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[User]:
        """List accounts with pagination (no subscription filter)"""
        try:
            conditions = []
            params = []
            param_count = 1

            if is_active is not None:
                conditions.append(f"is_active = ${param_count}")
                params.append(is_active)
                param_count += 1

            if search is not None:
                conditions.append(f"(name ILIKE ${param_count} OR email ILIKE ${param_count})")
                params.append(f"%{search}%")
                param_count += 1

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            params.append(limit)
            params.append(offset)

            query = f"""
                SELECT * FROM {self.schema}.{self.users_table}
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count} OFFSET ${param_count + 1}
            """

            async with self.db:
                rows = await self.db.query(query, params=params)

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

            async with self.db:
                rows = await self.db.query(sql, params=[search_pattern, limit])

            users = []
            if rows:
                for row in rows:
                    users.append(self._row_to_user(row))

            return users

        except Exception as e:
            logger.error(f"Failed to search accounts: {e}")
            return []

    async def get_account_stats(self) -> Dict[str, Any]:
        """Get account statistics - using concurrent queries"""
        try:
            async with self.db:
                # Run all stats queries concurrently for better performance
                results = await asyncio.gather(
                    self.db.query_row(f"SELECT COUNT(*) as total FROM {self.schema}.{self.users_table}"),
                    self.db.query_row(f"SELECT COUNT(*) as active FROM {self.schema}.{self.users_table} WHERE is_active = TRUE"),
                    self.db.query_row(f"SELECT COUNT(*) as count FROM {self.schema}.{self.users_table} WHERE created_at >= NOW() - INTERVAL '7 days'"),
                    self.db.query_row(f"SELECT COUNT(*) as count FROM {self.schema}.{self.users_table} WHERE created_at >= NOW() - INTERVAL '30 days'"),
                )

            total_row, active_row, recent_7d_row, recent_30d_row = results
            total_accounts = total_row['total'] if total_row else 0
            active_accounts = active_row['active'] if active_row else 0
            inactive_accounts = total_accounts - active_accounts

            return {
                "total_accounts": total_accounts,
                "active_accounts": active_accounts,
                "inactive_accounts": inactive_accounts,
                "recent_registrations_7d": recent_7d_row['count'] if recent_7d_row else 0,
                "recent_registrations_30d": recent_30d_row['count'] if recent_30d_row else 0
            }

        except Exception as e:
            logger.error(f"Failed to get account stats: {e}")
            return {
                "total_accounts": 0,
                "active_accounts": 0,
                "inactive_accounts": 0,
                "recent_registrations_7d": 0,
                "recent_registrations_30d": 0
            }

    async def get_accounts_by_ids(self, user_ids: List[str]) -> List[User]:
        """Get multiple accounts by IDs"""
        if not user_ids:
            return []

        try:
            placeholders = ", ".join([f"${i+1}" for i in range(len(user_ids))])
            sql = f"""
                SELECT * FROM {self.schema}.{self.users_table}
                WHERE user_id IN ({placeholders}) AND is_active = TRUE
            """

            async with self.db:
                rows = await self.db.query(sql, params=user_ids)

            users = []
            if rows:
                for row in rows:
                    users.append(self._row_to_user(row))

            return users

        except Exception as e:
            logger.error(f"Failed to get accounts by IDs: {e}")
            return []

    async def update_admin_roles(self, user_id: str, admin_roles: Optional[List[str]]) -> Optional[User]:
        """Update admin roles for a user account (JSONB column)"""
        try:
            existing = await self.get_account_by_id_include_inactive(user_id)
            if not existing:
                raise UserNotFoundException(f"Account not found: {user_id}")

            now = datetime.now(tz=timezone.utc)
            # Store as JSON — None clears admin roles
            roles_json = json.dumps(admin_roles) if admin_roles else None

            async with self.db:
                await self.db.execute(
                    f"UPDATE {self.schema}.{self.users_table} SET admin_roles = $1, updated_at = $2 WHERE user_id = $3",
                    params=[roles_json, now, user_id]
                )

            return await self.get_account_by_id_include_inactive(user_id)

        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to update admin roles for {user_id}: {e}")
            return None

    # --- Admin management methods (#193) ---

    async def get_account_detail(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get full account detail including status metadata and notes (admin view).

        Returns a dict with user fields plus account_status, status_reason, and notes.
        """
        try:
            user = await self.get_account_by_id_include_inactive(user_id)
            if not user:
                return None

            # Fetch account_status and status_reason from admin_status table
            account_status = "active"
            status_reason = None
            try:
                async with self.db:
                    status_row = await self.db.query_row(
                        f"SELECT status, reason FROM {self.schema}.admin_account_status WHERE user_id = $1",
                        params=[user_id]
                    )
                if status_row:
                    account_status = status_row.get("status", "active")
                    status_reason = status_row.get("reason")
            except Exception:
                # Table may not exist yet; derive from is_active
                account_status = "active" if user.is_active else "suspended"

            # Fetch admin notes
            notes: List[AdminNote] = []
            try:
                async with self.db:
                    note_rows = await self.db.query(
                        f"SELECT * FROM {self.schema}.admin_notes WHERE user_id = $1 ORDER BY created_at DESC",
                        params=[user_id]
                    )
                if note_rows:
                    for row in note_rows:
                        notes.append(AdminNote(
                            note_id=row["note_id"],
                            user_id=row["user_id"],
                            author_id=row["author_id"],
                            note=row["note"],
                            created_at=row["created_at"],
                        ))
            except Exception:
                # Table may not exist yet; return empty notes
                pass

            return {
                "user_id": user.user_id,
                "email": user.email,
                "name": user.name,
                "is_active": user.is_active,
                "account_status": account_status,
                "status_reason": status_reason,
                "admin_roles": user.admin_roles,
                "preferences": user.preferences,
                "notes": notes,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            }

        except Exception as e:
            logger.error(f"Failed to get account detail for {user_id}: {e}")
            return None

    async def update_account_status(
        self, user_id: str, status: str, reason: Optional[str] = None
    ) -> bool:
        """Update account status (active/suspended/banned) with reason.

        Persists status in admin_account_status table and sets is_active accordingly.
        """
        try:
            existing = await self.get_account_by_id_include_inactive(user_id)
            if not existing:
                raise UserNotFoundException(f"Account not found: {user_id}")

            now = datetime.now(tz=timezone.utc)
            is_active = status == "active"

            # Update is_active on the users table
            async with self.db:
                await self.db.execute(
                    f"UPDATE {self.schema}.{self.users_table} SET is_active = $1, updated_at = $2 WHERE user_id = $3",
                    params=[is_active, now, user_id]
                )

            # Upsert into admin_account_status
            try:
                async with self.db:
                    await self.db.execute(
                        f"""INSERT INTO {self.schema}.admin_account_status (user_id, status, reason, updated_at)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (user_id) DO UPDATE SET status = $2, reason = $3, updated_at = $4""",
                        params=[user_id, status, reason, now]
                    )
            except Exception as e:
                # Table may not exist; log and continue (is_active was still updated)
                logger.warning(f"Could not upsert admin_account_status for {user_id}: {e}")

            logger.info(f"Account status updated: {user_id} -> {status}")
            return True

        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to update account status for {user_id}: {e}")
            return False

    async def add_admin_note(
        self, user_id: str, author_id: str, note: str
    ) -> Optional[AdminNote]:
        """Add an internal support/admin note to an account."""
        try:
            existing = await self.get_account_by_id_include_inactive(user_id)
            if not existing:
                raise UserNotFoundException(f"Account not found: {user_id}")

            note_id = f"note_{uuid.uuid4().hex[:12]}"
            now = datetime.now(tz=timezone.utc)

            async with self.db:
                await self.db.execute(
                    f"""INSERT INTO {self.schema}.admin_notes (note_id, user_id, author_id, note, created_at)
                        VALUES ($1, $2, $3, $4, $5)""",
                    params=[note_id, user_id, author_id, note, now]
                )

            return AdminNote(
                note_id=note_id,
                user_id=user_id,
                author_id=author_id,
                note=note,
                created_at=now,
            )

        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to add admin note for {user_id}: {e}")
            return None

    async def get_total_account_count(
        self,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> int:
        """Get total account count with optional filters (for pagination)"""
        try:
            conditions = []
            params = []
            param_count = 1

            if is_active is not None:
                conditions.append(f"is_active = ${param_count}")
                params.append(is_active)
                param_count += 1

            if search is not None:
                conditions.append(f"(name ILIKE ${param_count} OR email ILIKE ${param_count})")
                params.append(f"%{search}%")
                param_count += 1

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f"SELECT COUNT(*) as total FROM {self.schema}.{self.users_table} {where_clause}"

            async with self.db:
                result = await self.db.query_row(query, params=params)

            return result["total"] if result else 0

        except Exception as e:
            logger.error(f"Failed to get total account count: {e}")
            return 0
