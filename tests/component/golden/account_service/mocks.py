"""
Account Service - Mock Dependencies

Mock implementations for component testing.
Returns User model objects as expected by the service.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import uuid

# Import the actual models used by the service
from microservices.account_service.models import User


class MockAccountRepository:
    """Mock account repository for component testing

    Implements AccountRepositoryProtocol interface.
    Returns User model objects, not dicts.
    """

    def __init__(self):
        self._data: Dict[str, User] = {}
        self._email_index: Dict[str, str] = {}  # email -> user_id
        self._stats: Dict[str, int] = {}
        self._error: Optional[Exception] = None
        self._call_log: List[Dict] = []

    def set_user(
        self,
        user_id: str,
        email: str,
        name: str,
        is_active: bool = True,
        preferences: Optional[Dict] = None,
        created_at: Optional[datetime] = None
    ):
        """Add a user to the mock repository"""
        user = User(
            user_id=user_id,
            email=email,
            name=name,
            is_active=is_active,
            preferences=preferences or {},
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        self._data[user_id] = user
        self._email_index[email] = user_id

    def set_stats(
        self,
        total_accounts: int = 0,
        active_accounts: int = 0,
        inactive_accounts: int = 0,
        recent_registrations_7d: int = 0,
        recent_registrations_30d: int = 0
    ):
        """Set service statistics"""
        self._stats = {
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "inactive_accounts": inactive_accounts,
            "recent_registrations_7d": recent_registrations_7d,
            "recent_registrations_30d": recent_registrations_30d
        }

    def set_error(self, error: Exception):
        """Set an error to be raised on operations"""
        self._error = error

    def _log_call(self, method: str, **kwargs):
        """Log method calls for assertions"""
        self._call_log.append({"method": method, "kwargs": kwargs})

    def assert_called(self, method: str):
        """Assert that a method was called"""
        called_methods = [c["method"] for c in self._call_log]
        assert method in called_methods, f"Expected {method} to be called, but got {called_methods}"

    def assert_called_with(self, method: str, **kwargs):
        """Assert that a method was called with specific kwargs"""
        for call in self._call_log:
            if call["method"] == method:
                for key, value in kwargs.items():
                    assert key in call["kwargs"], f"Expected kwarg {key} not found"
                    assert call["kwargs"][key] == value, f"Expected {key}={value}, got {call['kwargs'][key]}"
                return
        raise AssertionError(f"Expected {method} to be called with {kwargs}")

    async def ensure_account_exists(
        self,
        user_id: str,
        email: str,
        name: str,
    ) -> User:
        """Ensure account exists, return User object"""
        self._log_call("ensure_account_exists", user_id=user_id, email=email, name=name)

        # Check for duplicate email with different user_id
        if email in self._email_index and self._email_index[email] != user_id:
            from microservices.account_service.protocols import DuplicateEntryError
            raise DuplicateEntryError(f"Email {email} already exists")

        if user_id in self._data:
            return self._data[user_id]

        # Create new user
        user = User(
            user_id=user_id,
            email=email,
            name=name,
            is_active=True,
            preferences={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        self._data[user_id] = user
        self._email_index[email] = user_id
        return user

    async def get_account_by_id(self, user_id: str) -> Optional[User]:
        """Get account by ID (active only)"""
        self._log_call("get_account_by_id", user_id=user_id)
        user = self._data.get(user_id)
        if user and user.is_active:
            return user
        return None

    async def get_account_by_id_include_inactive(self, user_id: str) -> Optional[User]:
        """Get account by ID including inactive"""
        self._log_call("get_account_by_id_include_inactive", user_id=user_id)
        return self._data.get(user_id)

    async def get_account_by_email(self, email: str) -> Optional[User]:
        """Get account by email"""
        self._log_call("get_account_by_email", email=email)
        user_id = self._email_index.get(email)
        if user_id:
            return self._data.get(user_id)
        return None

    async def update_account_profile(
        self, user_id: str, update_data: Dict[str, Any]
    ) -> Optional[User]:
        """Update account profile"""
        self._log_call("update_account_profile", user_id=user_id, update_data=update_data)
        if user_id not in self._data:
            return None

        user = self._data[user_id]
        # Create updated user with new data
        updated_user = User(
            user_id=user.user_id,
            email=update_data.get("email", user.email),
            name=update_data.get("name", user.name),
            is_active=user.is_active,
            preferences=update_data.get("preferences", user.preferences),
            created_at=user.created_at,
            updated_at=datetime.now(timezone.utc)
        )
        self._data[user_id] = updated_user
        return updated_user

    async def update_account_preferences(
        self, user_id: str, preferences: Dict[str, Any]
    ) -> bool:
        """Update account preferences"""
        self._log_call("update_account_preferences", user_id=user_id, preferences=preferences)
        if user_id not in self._data:
            return False

        user = self._data[user_id]
        current_prefs = user.preferences.copy()
        current_prefs.update(preferences)

        # Create updated user
        updated_user = User(
            user_id=user.user_id,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            preferences=current_prefs,
            created_at=user.created_at,
            updated_at=datetime.now(timezone.utc)
        )
        self._data[user_id] = updated_user
        return True

    async def delete_account(self, user_id: str) -> bool:
        """Delete account (soft delete)"""
        self._log_call("delete_account", user_id=user_id)
        if user_id not in self._data:
            return False

        user = self._data[user_id]
        # Soft delete - mark as inactive
        updated_user = User(
            user_id=user.user_id,
            email=user.email,
            name=user.name,
            is_active=False,
            preferences=user.preferences,
            created_at=user.created_at,
            updated_at=datetime.now(timezone.utc)
        )
        self._data[user_id] = updated_user
        return True

    async def deactivate_account(self, user_id: str) -> bool:
        """Deactivate account"""
        self._log_call("deactivate_account", user_id=user_id)
        if user_id not in self._data:
            return False

        user = self._data[user_id]
        updated_user = User(
            user_id=user.user_id,
            email=user.email,
            name=user.name,
            is_active=False,
            preferences=user.preferences,
            created_at=user.created_at,
            updated_at=datetime.now(timezone.utc)
        )
        self._data[user_id] = updated_user
        return True

    async def activate_account(self, user_id: str) -> bool:
        """Activate account"""
        self._log_call("activate_account", user_id=user_id)
        if user_id not in self._data:
            return False

        user = self._data[user_id]
        updated_user = User(
            user_id=user.user_id,
            email=user.email,
            name=user.name,
            is_active=True,
            preferences=user.preferences,
            created_at=user.created_at,
            updated_at=datetime.now(timezone.utc)
        )
        self._data[user_id] = updated_user
        return True

    async def list_accounts(
        self,
        limit: int = 50,
        offset: int = 0,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[User]:
        """List accounts with pagination"""
        self._log_call("list_accounts", limit=limit, offset=offset, is_active=is_active, search=search)

        results = []
        for user in self._data.values():
            # Filter by active status
            if is_active is not None and user.is_active != is_active:
                continue
            # Filter by search
            if search:
                search_lower = search.lower()
                if not (search_lower in (user.name or "").lower() or
                        search_lower in (user.email or "").lower()):
                    continue
            results.append(user)

        # Apply pagination
        return results[offset:offset + limit]

    async def search_accounts(self, query: str, limit: int = 50) -> List[User]:
        """Search accounts by name or email"""
        self._log_call("search_accounts", query=query, limit=limit)

        results = []
        query_lower = query.lower()
        for user in self._data.values():
            if not user.is_active:
                continue
            if (query_lower in (user.name or "").lower() or
                query_lower in (user.email or "").lower()):
                results.append(user)
                if len(results) >= limit:
                    break
        return results

    async def get_account_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        self._log_call("get_account_stats")
        if self._error:
            raise self._error
        if self._stats:
            return self._stats

        # Calculate from data
        total = len(self._data)
        active = sum(1 for u in self._data.values() if u.is_active)

        return {
            "total_accounts": total,
            "active_accounts": active,
            "inactive_accounts": total - active,
            "recent_registrations_7d": 0,
            "recent_registrations_30d": 0
        }

    async def get_accounts_by_ids(self, user_ids: List[str]) -> List[User]:
        """Get multiple accounts by IDs"""
        self._log_call("get_accounts_by_ids", user_ids=user_ids)
        results = []
        for user_id in user_ids:
            if user_id in self._data and self._data[user_id].is_active:
                results.append(self._data[user_id])
        return results


class MockEventBus:
    """Mock NATS event bus"""

    def __init__(self):
        self.published_events: List[Any] = []
        self._call_log: List[Dict] = []

    async def publish(self, event: Any):
        """Publish event"""
        self._call_log.append({"method": "publish", "event": event})
        self.published_events.append(event)

    async def publish_event(self, event: Any):
        """Publish event (alias)"""
        await self.publish(event)

    def assert_published(self, event_type: str = None):
        """Assert that an event was published"""
        assert len(self.published_events) > 0, "No events were published"
        if event_type:
            event_types = [getattr(e, "event_type", str(e)) for e in self.published_events]
            assert event_type in str(event_types), f"Expected {event_type} event, got {event_types}"

    def get_published_events(self) -> List[Any]:
        """Get all published events"""
        return self.published_events
