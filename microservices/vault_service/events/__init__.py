"""
Vault Service Event Handlers

事件处理器 - 订阅其他服务的事件

Standard Structure:
- models.py: Event data models (Pydantic)
- handlers.py: Event handlers (subscribe to events from other services)
- publishers.py: Event publishers (publish events to other services)
"""

# Event Handlers
from .handlers import get_event_handlers, handle_user_deleted

# Event Models
from .models import (
    UserDeletedEventData,
    VaultSecretAccessedEventData,
    VaultSecretCreatedEventData,
    VaultSecretDeletedEventData,
    VaultSecretSharedEventData,
)

# Event Publishers
from .publishers import (
    publish_secret_accessed,
    publish_secret_created,
    publish_secret_deleted,
    publish_secret_shared,
)

__all__ = [
    # Event Handlers
    "get_event_handlers",
    "handle_user_deleted",
    # Event Models
    "UserDeletedEventData",
    "VaultSecretCreatedEventData",
    "VaultSecretAccessedEventData",
    "VaultSecretDeletedEventData",
    "VaultSecretSharedEventData",
    # Event Publishers
    "publish_secret_created",
    "publish_secret_accessed",
    "publish_secret_deleted",
    "publish_secret_shared",
]
