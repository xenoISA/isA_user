"""
Account Repository

Data access layer for account management operations.
Using Supabase client for consistency with other microservices.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database.supabase_client import get_supabase_client
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
    
    Database operations for account management using Supabase client.
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        # Table names
        self.users_table = "users"
        self.user_preferences_table = "user_preferences"
        
    async def get_account_by_id(self, user_id: str) -> Optional[User]:
        """Get account by user ID"""
        try:
            result = self.supabase.table(self.users_table).select("*").eq("user_id", user_id).eq("is_active", True).execute()
            
            if result.data and len(result.data) > 0:
                user_data = result.data[0]  # Get first (and should be only) result
                return User(
                    user_id=user_data["user_id"],
                    auth0_id=user_data.get("auth0_id"),
                    email=user_data["email"],
                    name=user_data.get("name"),
                    credits_remaining=user_data.get("credits_remaining", 0),
                    credits_total=user_data.get("credits_total", 0),
                    subscription_status=SubscriptionStatus(user_data.get("subscription_status", "free")),
                    is_active=user_data["is_active"],
                    created_at=user_data["created_at"],
                    updated_at=user_data["updated_at"]
                )
            return None
        except Exception as e:
            if "No rows found" in str(e):
                return None
            logger.error(f"Failed to get account by ID: {e}")
            raise UserNotFoundException(f"User {user_id} not found")
    
    async def get_account_by_auth0_id(self, auth0_id: str) -> Optional[User]:
        """Get account by Auth0 ID"""
        try:
            result = self.supabase.table(self.users_table).select("*").eq("auth0_id", auth0_id).eq("is_active", True).single().execute()
            
            if result.data:
                return User(
                    user_id=result.data["user_id"],
                    auth0_id=result.data.get("auth0_id"),
                    email=result.data["email"],
                    name=result.data.get("name"),
                    credits_remaining=result.data.get("credits_remaining", 0),
                    credits_total=result.data.get("credits_total", 0),
                    subscription_status=SubscriptionStatus(result.data.get("subscription_status", "free")),
                    is_active=result.data["is_active"],
                    created_at=result.data["created_at"],
                    updated_at=result.data["updated_at"]
                )
            return None
                
        except Exception as e:
            if "No rows found" in str(e):
                return None
            logger.error(f"Failed to get account by Auth0 ID {auth0_id}: {e}")
            return None
    
    async def get_account_by_email(self, email: str) -> Optional[User]:
        """Get account by email"""
        try:
            result = self.supabase.table(self.users_table).select("*").eq("email", email).eq("is_active", True).single().execute()
            
            if result.data:
                return User(
                    user_id=result.data["user_id"],
                    auth0_id=result.data.get("auth0_id"),
                    email=result.data["email"],
                    name=result.data.get("name"),
                    credits_remaining=result.data.get("credits_remaining", 0),
                    credits_total=result.data.get("credits_total", 0),
                    subscription_status=SubscriptionStatus(result.data.get("subscription_status", "free")),
                    is_active=result.data["is_active"],
                    created_at=result.data["created_at"],
                    updated_at=result.data["updated_at"]
                )
            return None
                
        except Exception as e:
            if "No rows found" in str(e):
                return None
            logger.error(f"Failed to get account by email {email}: {e}")
            return None
    
    async def ensure_account_exists(
        self, 
        user_id: str, 
        auth0_id: str, 
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
            
            # Check by auth0_id if different from user_id
            if auth0_id != user_id:
                auth0_user = await self.get_account_by_auth0_id(auth0_id)
                if auth0_user:
                    logger.info(f"Account found by auth0_id: {auth0_id}")
                    return auth0_user
            
            # Check for email conflicts
            email_user = await self.get_account_by_email(email)
            if email_user:
                raise DuplicateEntryException(f"Email {email} already exists for different user")
            
            # Create new user using Supabase client
            now = datetime.now(tz=timezone.utc)
            
            new_user_data = {
                "user_id": user_id,
                "auth0_id": auth0_id,
                "email": email,
                "name": name,
                "subscription_status": subscription_plan.value,
                "credits_remaining": 1000.0,  # Default credits
                "credits_total": 1000.0,  # Default total credits
                "is_active": True,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            result = self.supabase.table(self.users_table).insert(new_user_data).execute()
            
            if result.data and len(result.data) > 0:
                logger.info(f"New account created: {user_id}")
                return User(**result.data[0])
                    
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
            
            # Build update query dynamically
            update_fields = []
            values = []
            param_count = 1
            
            for field, value in update_data.items():
                if field in ['name', 'email', 'preferences']:
                    update_fields.append(f"{field} = ${param_count}")
                    values.append(value)
                    param_count += 1
            
            if not update_fields:
                return existing_account  # No updates needed
            
            # Add updated_at
            update_data["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
            
            # Update using Supabase client
            result = self.supabase.table(self.users_table).update(update_data).eq("user_id", user_id).execute()
            
            if result.data and len(result.data) > 0:
                return User(**result.data[0])
                    
            return None
            
        except Exception as e:
            logger.error(f"Failed to update account profile {user_id}: {e}")
            return None
    
    async def activate_account(self, user_id: str) -> bool:
        """Activate user account"""
        try:
            update_data = {
                "is_active": True,
                "updated_at": datetime.now(tz=timezone.utc).isoformat()
            }
            
            result = self.supabase.table(self.users_table).update(update_data).eq("user_id", user_id).execute()
            
            return result.data is not None and len(result.data) > 0
                
        except Exception as e:
            logger.error(f"Failed to activate account {user_id}: {e}")
            return False
    
    async def deactivate_account(self, user_id: str) -> bool:
        """Deactivate user account"""
        try:
            update_data = {
                "is_active": False,
                "updated_at": datetime.now(tz=timezone.utc).isoformat()
            }
            
            result = self.supabase.table(self.users_table).update(update_data).eq("user_id", user_id).execute()
            
            return result.data is not None and len(result.data) > 0
                
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
            
            update_data = {
                "preferences": updated_prefs,
                "updated_at": datetime.now(tz=timezone.utc).isoformat()
            }
            
            result = self.supabase.table(self.users_table).update(update_data).eq("user_id", user_id).execute()
            
            return result.data is not None and len(result.data) > 0
                
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
            # Build query using Supabase client
            query = self.supabase.table(self.users_table).select("*")
            
            # Apply filters
            if is_active is not None:
                query = query.eq("is_active", is_active)
            
            if subscription_status is not None:
                query = query.eq("subscription_status", subscription_status.value)
            
            if search is not None:
                # Use ilike for case-insensitive search
                query = query.or_(f"name.ilike.%{search}%,email.ilike.%{search}%")
            
            # Apply ordering and pagination
            query = query.order("created_at", desc=True).limit(limit).offset(offset)
            
            result = query.execute()
            
            users = []
            if result.data:
                for row in result.data:
                    users.append(User(
                        user_id=row["user_id"],
                        auth0_id=row.get("auth0_id"),
                        email=row["email"],
                        name=row.get("name"),
                        credits_remaining=row.get("credits_remaining", 0),
                        credits_total=row.get("credits_total", 0),
                        subscription_status=SubscriptionStatus(row.get("subscription_status", "free")),
                        is_active=row["is_active"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"]
                    ))
            
            return users
                
        except Exception as e:
            logger.error(f"Failed to list accounts: {e}")
            return []
    
    async def search_accounts(self, query: str, limit: int = 50) -> List[User]:
        """Search accounts by name or email"""
        try:
            # Use Supabase client for search
            result = (self.supabase.table(self.users_table)
                     .select("*")
                     .or_(f"name.ilike.%{query}%,email.ilike.%{query}%")
                     .eq("is_active", True)
                     .order("created_at", desc=True)
                     .limit(limit)
                     .execute())
            
            users = []
            if result.data:
                for row in result.data:
                    users.append(User(
                        user_id=row["user_id"],
                        auth0_id=row.get("auth0_id"),
                        email=row["email"],
                        name=row.get("name"),
                        credits_remaining=row.get("credits_remaining", 0),
                        credits_total=row.get("credits_total", 0),
                        subscription_status=SubscriptionStatus(row.get("subscription_status", "free")),
                        is_active=row["is_active"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"]
                    ))
            
            return users
                
        except Exception as e:
            logger.error(f"Failed to search accounts: {e}")
            return []
    
    async def get_account_stats(self) -> Dict[str, Any]:
        """Get account statistics"""
        try:
            # Get total counts using Supabase client
            total_result = self.supabase.table(self.users_table).select("*", count="exact").execute()
            total_accounts = total_result.count if total_result.count is not None else 0
            
            # Get active accounts count
            active_result = self.supabase.table(self.users_table).select("*", count="exact").eq("is_active", True).execute()
            active_accounts = active_result.count if active_result.count is not None else 0
            
            # Get inactive accounts count  
            inactive_accounts = total_accounts - active_accounts
            
            # Get subscription status counts
            all_users_result = self.supabase.table(self.users_table).select("subscription_status").execute()
            accounts_by_subscription = {}
            
            if all_users_result.data:
                for user in all_users_result.data:
                    status = user.get("subscription_status", "free")
                    accounts_by_subscription[status] = accounts_by_subscription.get(status, 0) + 1
            
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