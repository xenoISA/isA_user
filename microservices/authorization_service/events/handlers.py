"""
Authorization Service Event Handlers

Handles events from other services to maintain authorization data consistency
"""

import logging
import json
from typing import Dict, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class AuthorizationEventHandlers:
    """Event handlers for authorization service"""

    def __init__(self, authorization_service):
        """
        Initialize event handlers

        Args:
            authorization_service: Instance of AuthorizationService
        """
        self.authorization_service = authorization_service
        self.repository = authorization_service.repository

    def get_event_handler_map(self) -> Dict[str, Callable]:
        """
        Get mapping of event types to handler functions

        Returns:
            Dictionary mapping event types to handler functions
        """
        return {
            "user.deleted": self.handle_user_deleted,
            "organization.deleted": self.handle_organization_deleted,
            "organization.member_added": self.handle_org_member_added,
            "organization.member_removed": self.handle_org_member_removed,
        }

    async def handle_user_deleted(self, event_data: dict):
        """
        Handle user.deleted event - cleanup all permissions for deleted user

        Event data expected:
        {
            "user_id": "user123",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        """
        try:
            user_id = event_data.get("user_id")
            if not user_id:
                logger.error("user.deleted event missing user_id")
                return

            logger.info(f"Handling user.deleted event for user: {user_id}")

            # Get all user permissions
            from ..models import ResourceType
            permissions = await self.repository.list_user_permissions(user_id)

            # Revoke all permissions
            revoked_count = 0
            for permission in permissions:
                try:
                    success = await self.repository.revoke_user_permission(
                        user_id=user_id,
                        resource_type=permission.resource_type,
                        resource_name=permission.resource_name
                    )
                    if success:
                        revoked_count += 1
                except Exception as e:
                    logger.error(f"Failed to revoke permission {permission.resource_type}:{permission.resource_name}: {e}")

            logger.info(f"Cleaned up {revoked_count} permissions for deleted user {user_id}")

        except Exception as e:
            logger.error(f"Error handling user.deleted event: {e}")

    async def handle_organization_deleted(self, event_data: dict):
        """
        Handle organization.deleted event - cleanup all organization permissions

        Event data expected:
        {
            "organization_id": "org123",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        """
        try:
            organization_id = event_data.get("organization_id")
            if not organization_id:
                logger.error("organization.deleted event missing organization_id")
                return

            logger.info(f"Handling organization.deleted event for org: {organization_id}")

            # Delete all organization-level permissions
            try:
                deleted_org_perms = await self.repository.delete_organization_permissions(organization_id)
                logger.info(f"Deleted {deleted_org_perms} organization permission records")
            except Exception as e:
                logger.error(f"Failed to delete organization permissions: {e}")

            # Revoke all user permissions granted by this organization
            try:
                revoked_user_perms = await self.repository.revoke_permissions_by_organization(organization_id)
                logger.info(f"Revoked {revoked_user_perms} user permissions from org {organization_id}")
            except Exception as e:
                logger.error(f"Failed to revoke user permissions: {e}")

            logger.info(f"Cleaned up permissions for deleted organization {organization_id}")

        except Exception as e:
            logger.error(f"Error handling organization.deleted event: {e}")

    async def handle_org_member_added(self, event_data: dict):
        """
        Handle organization.member_added event - auto-grant organization permissions to new member

        Event data expected:
        {
            "organization_id": "org123",
            "user_id": "user456",
            "role": "member",
            "added_by": "user123",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        """
        try:
            organization_id = event_data.get("organization_id")
            user_id = event_data.get("user_id")
            role = event_data.get("role", "member")
            added_by = event_data.get("added_by", "system")

            if not organization_id or not user_id:
                logger.error("organization.member_added event missing required fields")
                return

            logger.info(f"Handling organization.member_added: org={organization_id}, user={user_id}, role={role}")

            # Get organization's configured permissions
            org_permissions = await self.repository.list_organization_permissions(organization_id)

            if not org_permissions:
                logger.info(f"No organization permissions configured for {organization_id}")
                return

            # Grant each organization permission to the new member
            granted_count = 0
            for org_perm in org_permissions:
                try:
                    from ..models import UserPermissionRecord, PermissionSource

                    # Check if permission already exists
                    existing = await self.repository.get_user_permission(
                        user_id=user_id,
                        resource_type=org_perm.resource_type,
                        resource_name=org_perm.resource_name
                    )

                    if existing:
                        logger.debug(f"Permission already exists: {org_perm.resource_type}:{org_perm.resource_name}")
                        continue

                    # Create user permission record
                    user_permission = UserPermissionRecord(
                        user_id=user_id,
                        resource_type=org_perm.resource_type,
                        resource_name=org_perm.resource_name,
                        access_level=org_perm.access_level,
                        permission_source=PermissionSource.ORGANIZATION,
                        granted_by_user_id=added_by,
                        organization_id=organization_id,
                        is_active=True
                    )

                    result = await self.repository.grant_user_permission(user_permission)
                    if result:
                        granted_count += 1
                        logger.debug(f"Granted permission: {org_perm.resource_type}:{org_perm.resource_name}")

                except Exception as e:
                    logger.error(f"Failed to grant permission {org_perm.resource_type}:{org_perm.resource_name}: {e}")

            logger.info(f"Auto-granted {granted_count} organization permissions to user {user_id}")

        except Exception as e:
            logger.error(f"Error handling organization.member_added event: {e}")

    async def handle_org_member_removed(self, event_data: dict):
        """
        Handle organization.member_removed event - revoke organization permissions from removed member

        Event data expected:
        {
            "organization_id": "org123",
            "user_id": "user456",
            "removed_by": "user123",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        """
        try:
            organization_id = event_data.get("organization_id")
            user_id = event_data.get("user_id")

            if not organization_id or not user_id:
                logger.error("organization.member_removed event missing required fields")
                return

            logger.info(f"Handling organization.member_removed: org={organization_id}, user={user_id}")

            # Get all user permissions
            user_permissions = await self.repository.list_user_permissions(user_id)

            # Filter permissions that came from this organization
            from ..models import PermissionSource

            revoked_count = 0
            for permission in user_permissions:
                # Only revoke permissions that were granted by organization membership
                # Check if permission source is ORGANIZATION and matches the organization_id
                if permission.permission_source == PermissionSource.ORGANIZATION:
                    # Note: We'd need to store organization_id with the permission to properly filter
                    # For now, revoke all organization-sourced permissions (conservative approach)
                    try:
                        success = await self.repository.revoke_user_permission(
                            user_id=user_id,
                            resource_type=permission.resource_type,
                            resource_name=permission.resource_name
                        )
                        if success:
                            revoked_count += 1
                            logger.debug(f"Revoked permission: {permission.resource_type}:{permission.resource_name}")
                    except Exception as e:
                        logger.error(f"Failed to revoke permission {permission.resource_type}:{permission.resource_name}: {e}")

            logger.info(f"Revoked {revoked_count} organization permissions from user {user_id}")

        except Exception as e:
            logger.error(f"Error handling organization.member_removed event: {e}")
