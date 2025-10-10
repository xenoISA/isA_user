"""
Authentication Repository - Data access layer for authentication operations
Handles database operations for user authentication, sessions, and provider mappings

Uses Supabase client for consistency with other microservices
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class AuthRepository:
    """Authentication repository - data access layer"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        # Table names
        self.users_table = "users"
        self.sessions_table = "user_sessions"
        self.provider_mappings_table = "provider_user_mappings"
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information by user ID"""
        try:
            result = self.supabase.table(self.users_table).select("*").eq("user_id", user_id).eq("is_active", True).single().execute()
            
            if result.data:
                return {
                    "user_id": result.data["user_id"],
                    "auth0_id": result.data.get("auth0_id"),
                    "email": result.data["email"],
                    "name": result.data.get("name"),
                    "subscription_status": result.data.get("subscription_status"),
                    "is_active": result.data["is_active"],
                    "created_at": result.data["created_at"],
                    "updated_at": result.data["updated_at"]
                }
            return None
                
        except Exception as e:
            if "No rows found" in str(e):
                return None
            logger.error(f"Failed to get user by ID: {e}")
            raise
    
    async def get_user_by_auth0_id(self, auth0_id: str) -> Optional[Dict[str, Any]]:
        """Get user information by Auth0 ID"""
        try:
            result = self.supabase.table(self.users_table).select("*").eq("auth0_id", auth0_id).eq("is_active", True).single().execute()
            
            if result.data:
                return {
                    "user_id": result.data["user_id"],
                    "auth0_id": result.data["auth0_id"],
                    "email": result.data["email"],
                    "name": result.data.get("name"),
                    "subscription_status": result.data.get("subscription_status"),
                    "is_active": result.data["is_active"],
                    "created_at": result.data["created_at"],
                    "updated_at": result.data["updated_at"]
                }
            return None
                
        except Exception as e:
            if "No rows found" in str(e):
                return None
            logger.error(f"Failed to get user by Auth0 ID: {e}")
            raise
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user information by email"""
        try:
            result = self.supabase.table(self.users_table).select("*").eq("email", email).eq("is_active", True).single().execute()
            
            if result.data:
                return {
                    "user_id": result.data["user_id"],
                    "auth0_id": result.data.get("auth0_id"),
                    "email": result.data["email"],
                    "name": result.data.get("name"),
                    "subscription_status": result.data.get("subscription_status"),
                    "is_active": result.data["is_active"],
                    "created_at": result.data["created_at"],
                    "updated_at": result.data["updated_at"]
                }
            return None
                
        except Exception as e:
            if "No rows found" in str(e):
                return None
            logger.error(f"Failed to get user by email: {e}")
            raise
    
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create new user"""
        try:
            now = datetime.now(timezone.utc).isoformat()
            user_data["created_at"] = now
            user_data["updated_at"] = now
            user_data["is_active"] = True
            
            result = self.supabase.table(self.users_table).insert(user_data).execute()
            
            if result.data:
                return result.data[0]
            return None
                
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise
    
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user information"""
        try:
            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            result = self.supabase.table(self.users_table).update(update_data).eq("user_id", user_id).execute()
            
            return len(result.data) > 0 if result.data else False
                
        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            raise
    
    async def get_or_create_provider_mapping(self, provider: str, provider_user_id: str, email: str) -> Dict[str, Any]:
        """Get or create provider user mapping"""
        try:
            # First try to get existing mapping
            result = self.supabase.table(self.provider_mappings_table).select("*").eq("provider", provider).eq("provider_user_id", provider_user_id).single().execute()
            
            if result.data:
                return result.data
            
            # Create new mapping
            new_mapping = {
                "provider": provider,
                "provider_user_id": provider_user_id,
                "email": email,
                "internal_user_id": f"{provider}|{provider_user_id}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table(self.provider_mappings_table).insert(new_mapping).execute()
            
            if result.data:
                return result.data[0]
            
            raise Exception("Failed to create provider mapping")
                
        except Exception as e:
            if "No rows found" not in str(e):
                logger.error(f"Failed to get/create provider mapping: {e}")
            
            # Try to create if not found
            try:
                new_mapping = {
                    "provider": provider,
                    "provider_user_id": provider_user_id,
                    "email": email,
                    "internal_user_id": f"{provider}|{provider_user_id}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                result = self.supabase.table(self.provider_mappings_table).insert(new_mapping).execute()
                
                if result.data:
                    return result.data[0]
            except:
                pass
            
            raise
    
    async def create_session(self, session_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create authentication session"""
        try:
            session_data["created_at"] = datetime.now(timezone.utc).isoformat()
            session_data["is_active"] = True
            
            result = self.supabase.table(self.sessions_table).insert(session_data).execute()
            
            if result.data:
                return result.data[0]
            return None
                
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        try:
            result = self.supabase.table(self.sessions_table).select("*").eq("session_id", session_id).eq("is_active", True).single().execute()
            
            if result.data:
                # Check if session is expired
                if result.data.get("expires_at"):
                    expires_at = datetime.fromisoformat(result.data["expires_at"].replace('Z', '+00:00'))
                    if expires_at < datetime.now(timezone.utc):
                        return None
                return result.data
            return None
                
        except Exception as e:
            if "No rows found" in str(e):
                return None
            logger.error(f"Failed to get session: {e}")
            raise
    
    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp"""
        try:
            update_data = {
                "last_activity": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table(self.sessions_table).update(update_data).eq("session_id", session_id).execute()
            
            return len(result.data) > 0 if result.data else False
                
        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")
            raise
    
    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate session"""
        try:
            update_data = {
                "is_active": False,
                "invalidated_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table(self.sessions_table).update(update_data).eq("session_id", session_id).execute()
            
            return len(result.data) > 0 if result.data else False
                
        except Exception as e:
            logger.error(f"Failed to invalidate session: {e}")
            raise
    
    async def check_connection(self) -> bool:
        """Check database connection"""
        try:
            result = self.supabase.table(self.users_table).select("count").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False