"""
Account Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

# Import only models (no I/O dependencies)
from .models import User


class DuplicateEntryError(Exception):
    """Duplicate entry error - defined here to avoid importing repository"""
    pass


class UserNotFoundError(Exception):
    """User not found error - defined here to avoid importing repository"""
    pass


@runtime_checkable
class AccountRepositoryProtocol(Protocol):
    """
    Interface for Account Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    async def get_account_by_id(self, user_id: str) -> Optional[User]:
        """Get account by user ID"""
        ...

    async def get_account_by_id_include_inactive(self, user_id: str) -> Optional[User]:
        """Get account by user ID including inactive accounts"""
        ...

    async def get_account_by_email(self, email: str) -> Optional[User]:
        """Get account by email"""
        ...

    async def ensure_account_exists(
        self, user_id: str, email: str, name: str
    ) -> User:
        """Ensure user account exists, create if not found"""
        ...

    async def update_account_profile(
        self, user_id: str, update_data: Dict[str, Any]
    ) -> Optional[User]:
        """Update account profile information"""
        ...

    async def update_account_preferences(
        self, user_id: str, preferences: Dict[str, Any]
    ) -> bool:
        """Update account preferences"""
        ...

    async def activate_account(self, user_id: str) -> bool:
        """Activate user account"""
        ...

    async def deactivate_account(self, user_id: str) -> bool:
        """Deactivate user account"""
        ...

    async def delete_account(self, user_id: str) -> bool:
        """Delete account (soft delete)"""
        ...

    async def list_accounts(
        self,
        limit: int = 50,
        offset: int = 0,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[User]:
        """List accounts with pagination"""
        ...

    async def search_accounts(self, query: str, limit: int = 50) -> List[User]:
        """Search accounts by name or email"""
        ...

    async def get_account_stats(self) -> Dict[str, Any]:
        """Get account statistics"""
        ...

    async def get_accounts_by_ids(self, user_ids: List[str]) -> List[User]:
        """Get multiple accounts by IDs"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...


@runtime_checkable
class SubscriptionClientProtocol(Protocol):
    """Interface for Subscription Service Client"""

    async def get_or_create_subscription(
        self, user_id: str, tier_code: str
    ) -> Optional[Dict[str, Any]]:
        """Get or create subscription for user"""
        ...
