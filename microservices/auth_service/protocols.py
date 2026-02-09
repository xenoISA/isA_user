"""
Authentication Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, Optional, Protocol, runtime_checkable

# Import only models (no I/O dependencies)
from .models import AuthUser, AuthSession


# Custom exceptions - defined here to avoid importing repository

class AuthenticationError(Exception):
    """Base authentication error"""
    pass


class InvalidTokenError(AuthenticationError):
    """Invalid or expired token"""
    pass


class UserNotFoundError(AuthenticationError):
    """User not found in auth system"""
    pass


class SessionNotFoundError(AuthenticationError):
    """Session not found or expired"""
    pass


class RegistrationError(AuthenticationError):
    """Registration failed"""
    pass


class VerificationError(AuthenticationError):
    """Verification failed"""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Invalid email or password"""
    pass


class AccountDisabledError(AuthenticationError):
    """Account is disabled"""
    pass


@runtime_checkable
class AuthRepositoryProtocol(Protocol):
    """
    Interface for Auth Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    async def get_user_by_id(self, user_id: str) -> Optional[AuthUser]:
        """Get user by ID"""
        ...

    async def get_user_by_email(self, email: str) -> Optional[AuthUser]:
        """Get user by email"""
        ...

    async def create_user(self, user_data: Dict[str, Any]) -> Optional[AuthUser]:
        """Create new user"""
        ...

    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user information"""
        ...

    async def create_session(self, session_data: Dict[str, Any]) -> Optional[AuthSession]:
        """Create authentication session"""
        ...

    async def get_session(self, session_id: str) -> Optional[AuthSession]:
        """Get session information"""
        ...

    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp"""
        ...

    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate session"""
        ...

    async def check_connection(self) -> bool:
        """Check database connection"""
        ...

    async def get_user_for_login(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user with password hash for login verification"""
        ...

    async def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        ...

    async def set_password_hash(self, user_id: str, password_hash: str) -> bool:
        """Set user's password hash"""
        ...

    async def set_email_verified(self, user_id: str, verified: bool = True) -> bool:
        """Set user's email verification status"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...


@runtime_checkable
class AccountClientProtocol(Protocol):
    """Interface for Account Service Client - no I/O imports"""

    async def get_account_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get account profile from account service"""
        ...

    async def ensure_account(
        self, user_id: str, email: str, name: str
    ) -> Optional[Dict[str, Any]]:
        """Ensure account exists in account service"""
        ...


@runtime_checkable
class NotificationClientProtocol(Protocol):
    """Interface for Notification Service Client - no I/O imports"""

    async def send_email(
        self,
        recipient_email: str,
        subject: str,
        content: str,
        html_content: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send email notification"""
        ...


@runtime_checkable
class JWTManagerProtocol(Protocol):
    """Interface for JWT Manager - no I/O imports"""

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token"""
        ...

    def create_access_token(self, claims: Any, expires_delta: Any = None) -> str:
        """Create access token"""
        ...

    def create_token_pair(self, claims: Any) -> Dict[str, Any]:
        """Create access and refresh token pair"""
        ...

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        ...
