"""
Authorization Service Events Module

Event-driven architecture for authorization and permission management.
Follows the standard event-driven architecture pattern.
"""

from .handlers import AuthorizationEventHandlers
from .models import (
    BulkPermissionsGrantedEventData,
    BulkPermissionsRevokedEventData,
    PermissionGrantedEventData,
    PermissionRevokedEventData,
    create_bulk_permissions_granted_event_data,
    create_bulk_permissions_revoked_event_data,
    create_permission_granted_event_data,
    create_permission_revoked_event_data,
)
from .publishers import (
    publish_bulk_permissions_granted,
    publish_bulk_permissions_revoked,
    publish_permission_granted,
    publish_permission_revoked,
)

__all__ = [
    # Handlers
    "AuthorizationEventHandlers",
    # Models
    "PermissionGrantedEventData",
    "PermissionRevokedEventData",
    "BulkPermissionsGrantedEventData",
    "BulkPermissionsRevokedEventData",
    "create_permission_granted_event_data",
    "create_permission_revoked_event_data",
    "create_bulk_permissions_granted_event_data",
    "create_bulk_permissions_revoked_event_data",
    # Publishers
    "publish_permission_granted",
    "publish_permission_revoked",
    "publish_bulk_permissions_granted",
    "publish_bulk_permissions_revoked",
]
