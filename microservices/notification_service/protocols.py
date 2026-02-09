"""
Notification Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime


class NotificationServiceError(Exception):
    """Base exception for notification service errors"""
    pass


class NotificationNotFoundError(NotificationServiceError):
    """Notification resource not found"""
    pass


class TemplateNotFoundError(NotificationServiceError):
    """Template not found"""
    pass


class NotificationValidationError(NotificationServiceError):
    """Notification data validation error"""
    pass


@runtime_checkable
class NotificationRepositoryProtocol(Protocol):
    """
    Interface for Notification Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    # Template operations
    async def create_template(self, template: Any) -> Any:
        """Create a notification template"""
        ...

    async def get_template(self, template_id: str) -> Optional[Any]:
        """Get template by ID"""
        ...

    async def list_templates(
        self,
        type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Any]:
        """List templates"""
        ...

    async def update_template(self, template_id: str, updates: Dict) -> bool:
        """Update a template"""
        ...

    # Notification operations
    async def create_notification(self, notification: Any) -> Any:
        """Create a notification"""
        ...

    async def get_notification(self, notification_id: str) -> Optional[Any]:
        """Get notification by ID"""
        ...

    async def update_notification_status(
        self,
        notification_id: str,
        status: Any,
        error_message: Optional[str] = None,
        provider_message_id: Optional[str] = None
    ) -> bool:
        """Update notification status"""
        ...

    # Batch operations
    async def create_batch(self, batch: Any) -> Any:
        """Create a notification batch"""
        ...

    async def update_batch_stats(
        self,
        batch_id: str,
        sent_count: int = 0,
        delivered_count: int = 0,
        failed_count: int = 0,
        completed: bool = False
    ) -> bool:
        """Update batch statistics"""
        ...

    # In-app notification operations
    async def create_in_app_notification(self, notification: Any) -> Any:
        """Create an in-app notification"""
        ...

    async def list_user_in_app_notifications(
        self,
        user_id: str,
        is_read: Optional[bool] = None,
        is_archived: Optional[bool] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Any]:
        """List user's in-app notifications"""
        ...

    async def mark_notification_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as read"""
        ...

    async def mark_notification_as_archived(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as archived"""
        ...

    async def get_unread_count(self, user_id: str) -> int:
        """Get unread notification count for user"""
        ...

    # Push subscription operations
    async def register_push_subscription(self, subscription: Any) -> Any:
        """Register a push subscription"""
        ...

    async def get_user_push_subscriptions(
        self,
        user_id: str,
        platform: Optional[Any] = None,
        is_active: bool = True
    ) -> List[Any]:
        """Get user's push subscriptions"""
        ...

    async def unsubscribe_push(self, user_id: str, device_token: str) -> bool:
        """Unsubscribe from push"""
        ...

    async def update_push_last_used(self, user_id: str, device_token: str) -> bool:
        """Update push subscription last used time"""
        ...

    # Stats
    async def get_notification_stats(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get notification statistics"""
        ...

    async def get_pending_notifications(self, limit: int = 50) -> List[Any]:
        """Get pending notifications for processing"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...


@runtime_checkable
class AccountClientProtocol(Protocol):
    """Interface for Account Service Client"""

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information"""
        ...

    async def close(self) -> None:
        """Close the client"""
        ...


@runtime_checkable
class OrganizationClientProtocol(Protocol):
    """Interface for Organization Service Client"""

    async def get_organization(self, org_id: str) -> Optional[Dict[str, Any]]:
        """Get organization information"""
        ...

    async def get_organization_members(self, org_id: str) -> List[str]:
        """Get organization member IDs"""
        ...

    async def close(self) -> None:
        """Close the client"""
        ...


@runtime_checkable
class EmailClientProtocol(Protocol):
    """Interface for Email Client (e.g., Resend)"""

    async def post(self, url: str, json: Dict = None, **kwargs) -> Any:
        """Send HTTP POST request"""
        ...

    async def aclose(self) -> None:
        """Close the client"""
        ...
