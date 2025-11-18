"""
Account Service Events Module

Event-driven architecture for account lifecycle and profile management.
Follows the standard event-driven architecture pattern.
"""

from .handlers import get_event_handlers
from .models import (
    UserCreatedEventData,
    UserDeletedEventData,
    UserProfileUpdatedEventData,
    UserStatusChangedEventData,
    UserSubscriptionChangedEventData,
    create_user_created_event_data,
    create_user_deleted_event_data,
    create_user_profile_updated_event_data,
    create_user_status_changed_event_data,
    create_user_subscription_changed_event_data,
)
from .publishers import (
    publish_user_created,
    publish_user_deleted,
    publish_user_profile_updated,
    publish_user_status_changed,
    publish_user_subscription_changed,
)

__all__ = [
    # Handlers
    "get_event_handlers",
    # Models
    "UserCreatedEventData",
    "UserProfileUpdatedEventData",
    "UserDeletedEventData",
    "UserSubscriptionChangedEventData",
    "UserStatusChangedEventData",
    "create_user_created_event_data",
    "create_user_profile_updated_event_data",
    "create_user_deleted_event_data",
    "create_user_subscription_changed_event_data",
    "create_user_status_changed_event_data",
    # Publishers
    "publish_user_created",
    "publish_user_profile_updated",
    "publish_user_deleted",
    "publish_user_subscription_changed",
    "publish_user_status_changed",
]
