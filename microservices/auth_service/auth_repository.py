"""
Authentication Repository - Data access layer for authentication operations
Handles database operations for user authentication, sessions, and provider mappings

Uses PostgresClient for direct PostgreSQL access
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient

logger = logging.getLogger(__name__)

class AuthRepository:
    """Authentication repository - data access layer"""

    def __init__(self):
        # TODO: Use Consul service discovery instead of hardcoded host/port
        self.db = PostgresClient(host='isa-postgres-grpc', port=50061, user_id='auth-service')
        # Table names (auth schema)
        self.schema = "auth"
        self.users_table = "users"
        self.sessions_table = "user_sessions"
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information by user ID"""
        try:
            with self.db:
                result = self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.users_table} WHERE user_id = $1 AND is_active = TRUE",
                    [user_id],
                    schema=self.schema
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
            with self.db:
                result = self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.users_table} WHERE email = $1 AND is_active = TRUE",
                    [email],
                    schema=self.schema
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
            logger.error(f"Failed to get user by email: {e}")
            return None

    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create new user"""
        try:
            now = datetime.now(timezone.utc)
            user_data["created_at"] = now
            user_data["updated_at"] = now
            user_data["is_active"] = True

            with self.db:
                count = self.db.insert_into(self.users_table, [user_data], schema=self.schema)

            if count > 0:
                # Fetch the created user
                return await self.get_user_by_email(user_data["email"])
            return None

        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise

    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user information"""
        try:
            update_data["updated_at"] = datetime.now(timezone.utc)

            with self.db:
                result = self.db.execute(
                    f"UPDATE {self.schema}.{self.users_table} SET updated_at = $1 WHERE user_id = $2",
                    [update_data["updated_at"], user_id],
                    schema=self.schema
                )

            return result > 0

        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            raise

    async def create_session(self, session_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create authentication session"""
        try:
            session_data["created_at"] = datetime.now(timezone.utc)
            session_data["is_active"] = True

            with self.db:
                count = self.db.insert_into(self.sessions_table, [session_data], schema=self.schema)

            if count > 0:
                return session_data
            return None

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        try:
            with self.db:
                result = self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.sessions_table} WHERE session_id = $1 AND is_active = TRUE",
                    [session_id],
                    schema=self.schema
                )

            if result:
                # Check if session is expired
                if result.get("expires_at"):
                    expires_at = result["expires_at"]
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

            with self.db:
                result = self.db.execute(
                    f"UPDATE {self.schema}.{self.sessions_table} SET last_activity = $1 WHERE session_id = $2",
                    [now, session_id],
                    schema=self.schema
                )

            return result > 0

        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")
            raise

    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate session"""
        try:
            now = datetime.now(timezone.utc)

            with self.db:
                result = self.db.execute(
                    f"UPDATE {self.schema}.{self.sessions_table} SET is_active = FALSE, invalidated_at = $1 WHERE session_id = $2",
                    [now, session_id],
                    schema=self.schema
                )

            return result > 0

        except Exception as e:
            logger.error(f"Failed to invalidate session: {e}")
            raise

    async def check_connection(self) -> bool:
        """Check database connection"""
        try:
            with self.db:
                health = self.db.health_check()
            return health and health.get('healthy', False)
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False