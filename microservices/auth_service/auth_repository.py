"""
Authentication Repository - Async Version

Data access layer for authentication operations using AsyncPostgresClient.
Handles database operations for user authentication, sessions, and provider mappings.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class AuthRepository:
    """Authentication repository - async data access layer"""

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("auth_service")

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
            user_id='auth-service'
        )
        self.schema = "auth"
        self.users_table = "users"
        self.sessions_table = "user_sessions"

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information by user ID"""
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.users_table} WHERE user_id = $1 AND is_active = TRUE",
                    params=[user_id]
                )

            if result:
                return {
                    "user_id": result["user_id"],
                    "email": result["email"],
                    "name": result.get("name"),
                    "subscription_status": result.get("subscription_status"),
                    "is_active": result["is_active"],
                    "created_at": result["created_at"],
                    "updated_at": result["updated_at"]
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get user by ID: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user information by email"""
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.users_table} WHERE email = $1 AND is_active = TRUE",
                    params=[email]
                )

            if result:
                return {
                    "user_id": result["user_id"],
                    "email": result["email"],
                    "name": result.get("name"),
                    "subscription_status": result.get("subscription_status"),
                    "is_active": result["is_active"],
                    "email_verified": result.get("email_verified", False),
                    "created_at": result["created_at"],
                    "updated_at": result["updated_at"]
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get user by email: {e}")
            return None

    async def get_user_for_login(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user with password hash for login verification"""
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT user_id, email, name, password_hash, email_verified, is_active "
                    f"FROM {self.schema}.{self.users_table} WHERE email = $1",
                    params=[email]
                )

            if result:
                return {
                    "user_id": result["user_id"],
                    "email": result["email"],
                    "name": result.get("name"),
                    "password_hash": result.get("password_hash"),
                    "email_verified": result.get("email_verified", False),
                    "is_active": result.get("is_active", True)
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get user for login: {e}")
            return None

    async def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        try:
            now = datetime.now(timezone.utc)

            async with self.db:
                result = await self.db.execute(
                    f"UPDATE {self.schema}.{self.users_table} SET last_login = $1, updated_at = $1 WHERE user_id = $2",
                    params=[now, user_id]
                )

            return result is not None and result > 0

        except Exception as e:
            logger.error(f"Failed to update last login: {e}")
            return False

    async def set_password_hash(self, user_id: str, password_hash: str) -> bool:
        """Set user's password hash"""
        try:
            now = datetime.now(timezone.utc)

            async with self.db:
                result = await self.db.execute(
                    f"UPDATE {self.schema}.{self.users_table} SET password_hash = $1, updated_at = $2 WHERE user_id = $3",
                    params=[password_hash, now, user_id]
                )

            return result is not None and result > 0

        except Exception as e:
            logger.error(f"Failed to set password hash: {e}")
            return False

    async def set_email_verified(self, user_id: str, verified: bool = True) -> bool:
        """Set user's email verification status"""
        try:
            now = datetime.now(timezone.utc)

            async with self.db:
                result = await self.db.execute(
                    f"UPDATE {self.schema}.{self.users_table} SET email_verified = $1, updated_at = $2 WHERE user_id = $3",
                    params=[verified, now, user_id]
                )

            return result is not None and result > 0

        except Exception as e:
            logger.error(f"Failed to set email verified: {e}")
            return False

    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create new user"""
        try:
            now = datetime.now(timezone.utc)

            query = f"""
                INSERT INTO {self.schema}.{self.users_table}
                (user_id, email, name, password_hash, email_verified, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            params = [
                user_data["user_id"],
                user_data["email"],
                user_data.get("name"),
                user_data.get("password_hash"),
                user_data.get("email_verified", False),
                True,
                now,
                now
            ]

            async with self.db:
                count = await self.db.execute(query, params=params)

            if count and count > 0:
                return await self.get_user_by_email(user_data["email"])
            return None

        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise

    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user information"""
        try:
            now = datetime.now(timezone.utc)

            async with self.db:
                result = await self.db.execute(
                    f"UPDATE {self.schema}.{self.users_table} SET updated_at = $1 WHERE user_id = $2",
                    params=[now, user_id]
                )

            return result is not None and result > 0

        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            raise

    async def create_session(self, session_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create authentication session"""
        try:
            now = datetime.now(timezone.utc)

            query = f"""
                INSERT INTO {self.schema}.{self.sessions_table}
                (session_id, user_id, access_token, refresh_token, expires_at, is_active, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """
            params = [
                session_data["session_id"],
                session_data["user_id"],
                session_data.get("access_token"),
                session_data.get("refresh_token"),
                session_data.get("expires_at"),
                True,
                now
            ]

            async with self.db:
                count = await self.db.execute(query, params=params)

            if count and count > 0:
                session_data["created_at"] = now
                session_data["is_active"] = True
                return session_data
            return None

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.sessions_table} WHERE session_id = $1 AND is_active = TRUE",
                    params=[session_id]
                )

            if result:
                # Check if session is expired
                expires_at = result.get("expires_at")
                if expires_at:
                    if isinstance(expires_at, str):
                        expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    if expires_at < datetime.now(timezone.utc):
                        return None
                return result
            return None

        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None

    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp"""
        try:
            now = datetime.now(timezone.utc)

            async with self.db:
                result = await self.db.execute(
                    f"UPDATE {self.schema}.{self.sessions_table} SET last_activity = $1 WHERE session_id = $2",
                    params=[now, session_id]
                )

            return result is not None and result > 0

        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")
            raise

    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate session"""
        try:
            now = datetime.now(timezone.utc)

            async with self.db:
                result = await self.db.execute(
                    f"UPDATE {self.schema}.{self.sessions_table} SET is_active = FALSE, invalidated_at = $1 WHERE session_id = $2",
                    params=[now, session_id]
                )

            return result is not None and result > 0

        except Exception as e:
            logger.error(f"Failed to invalidate session: {e}")
            raise

    async def check_connection(self) -> bool:
        """Check database connection"""
        try:
            async with self.db:
                result = await self.db.query_row("SELECT 1 as connected", params=[])
            return result is not None
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
