"""
Authorization Service Client

Client library for other microservices to interact with authorization service
"""

import httpx
from core.service_discovery import get_service_discovery
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class AuthorizationServiceClient:
    """Authorization Service HTTP client"""

    def __init__(self, base_url: str = None):
        """
        Initialize Authorization Service client

        Args:
            base_url: Authorization service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("authorization_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8203"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Access Control
    # =============================================================================

    async def check_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        permission: str,
        organization_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if user has permission to access resource

        Args:
            user_id: User ID
            resource_type: Resource type (e.g., "album", "file", "device")
            resource_id: Resource ID
            permission: Required permission (e.g., "read", "write", "delete")
            organization_id: Organization ID (optional)

        Returns:
            Access check result with has_access boolean

        Example:
            >>> client = AuthorizationServiceClient()
            >>> result = await client.check_access(
            ...     user_id="user123",
            ...     resource_type="album",
            ...     resource_id="album_456",
            ...     permission="write"
            ... )
            >>> if result['has_access']:
            ...     print("Access granted")
        """
        try:
            payload = {
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "permission": permission
            }

            if organization_id:
                payload["organization_id"] = organization_id

            response = await self.client.post(
                f"{self.base_url}/api/v1/authorization/check-access",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to check access: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error checking access: {e}")
            return None

    # =============================================================================
    # Permission Management
    # =============================================================================

    async def grant_permission(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        permissions: List[str],
        granted_by: str,
        organization_id: Optional[str] = None,
        expires_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Grant permissions to user for resource

        Args:
            user_id: User ID to grant permissions to
            resource_type: Resource type
            resource_id: Resource ID
            permissions: List of permissions to grant
            granted_by: User ID who is granting permissions
            organization_id: Organization ID (optional)
            expires_at: Expiration timestamp ISO format (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created permission grant

        Example:
            >>> result = await client.grant_permission(
            ...     user_id="user123",
            ...     resource_type="album",
            ...     resource_id="album_456",
            ...     permissions=["read", "write"],
            ...     granted_by="admin_user"
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "permissions": permissions,
                "granted_by": granted_by
            }

            if organization_id:
                payload["organization_id"] = organization_id
            if expires_at:
                payload["expires_at"] = expires_at
            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/authorization/grant",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to grant permission: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error granting permission: {e}")
            return None

    async def revoke_permission(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        permissions: Optional[List[str]] = None,
        revoked_by: Optional[str] = None
    ) -> bool:
        """
        Revoke permissions from user for resource

        Args:
            user_id: User ID
            resource_type: Resource type
            resource_id: Resource ID
            permissions: Specific permissions to revoke (if None, revoke all)
            revoked_by: User ID who is revoking permissions

        Returns:
            True if successful

        Example:
            >>> success = await client.revoke_permission(
            ...     user_id="user123",
            ...     resource_type="album",
            ...     resource_id="album_456",
            ...     permissions=["write"]
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id
            }

            if permissions:
                payload["permissions"] = permissions
            if revoked_by:
                payload["revoked_by"] = revoked_by

            response = await self.client.post(
                f"{self.base_url}/api/v1/authorization/revoke",
                json=payload
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to revoke permission: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error revoking permission: {e}")
            return False

    async def bulk_grant_permissions(
        self,
        grants: List[Dict[str, Any]],
        granted_by: str
    ) -> Optional[Dict[str, Any]]:
        """
        Grant multiple permissions in bulk

        Args:
            grants: List of permission grant dictionaries
            granted_by: User ID who is granting permissions

        Returns:
            Bulk grant result

        Example:
            >>> grants = [
            ...     {
            ...         "user_id": "user1",
            ...         "resource_type": "album",
            ...         "resource_id": "album1",
            ...         "permissions": ["read"]
            ...     },
            ...     {
            ...         "user_id": "user2",
            ...         "resource_type": "album",
            ...         "resource_id": "album1",
            ...         "permissions": ["read", "write"]
            ...     }
            ... ]
            >>> result = await client.bulk_grant_permissions(grants, "admin")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/authorization/bulk-grant",
                json={
                    "grants": grants,
                    "granted_by": granted_by
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to bulk grant permissions: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error bulk granting permissions: {e}")
            return None

    async def bulk_revoke_permissions(
        self,
        revocations: List[Dict[str, Any]],
        revoked_by: str
    ) -> Optional[Dict[str, Any]]:
        """
        Revoke multiple permissions in bulk

        Args:
            revocations: List of permission revocation dictionaries
            revoked_by: User ID who is revoking permissions

        Returns:
            Bulk revoke result

        Example:
            >>> revocations = [
            ...     {
            ...         "user_id": "user1",
            ...         "resource_type": "album",
            ...         "resource_id": "album1"
            ...     },
            ...     {
            ...         "user_id": "user2",
            ...         "resource_type": "file",
            ...         "resource_id": "file1"
            ...     }
            ... ]
            >>> result = await client.bulk_revoke_permissions(revocations, "admin")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/authorization/bulk-revoke",
                json={
                    "revocations": revocations,
                    "revoked_by": revoked_by
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to bulk revoke permissions: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error bulk revoking permissions: {e}")
            return None

    # =============================================================================
    # User Permission Queries
    # =============================================================================

    async def get_user_permissions(
        self,
        user_id: str,
        resource_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get all permissions for a user

        Args:
            user_id: User ID
            resource_type: Filter by resource type (optional)

        Returns:
            User permissions summary

        Example:
            >>> perms = await client.get_user_permissions("user123")
            >>> print(f"Total permissions: {perms['total_permissions']}")
            >>> for perm in perms['permissions']:
            ...     print(f"{perm['resource_type']}/{perm['resource_id']}: {perm['permissions']}")
        """
        try:
            params = {}
            if resource_type:
                params["resource_type"] = resource_type

            response = await self.client.get(
                f"{self.base_url}/api/v1/authorization/user-permissions/{user_id}",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get user permissions: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting user permissions: {e}")
            return None

    async def get_user_accessible_resources(
        self,
        user_id: str,
        resource_type: str,
        permission: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get all resources user can access

        Args:
            user_id: User ID
            resource_type: Resource type to filter
            permission: Required permission (optional)

        Returns:
            List of accessible resources

        Example:
            >>> resources = await client.get_user_accessible_resources(
            ...     user_id="user123",
            ...     resource_type="album",
            ...     permission="write"
            ... )
            >>> for resource in resources:
            ...     print(f"Album: {resource['resource_id']}")
        """
        try:
            params = {"resource_type": resource_type}
            if permission:
                params["permission"] = permission

            response = await self.client.get(
                f"{self.base_url}/api/v1/authorization/user-resources/{user_id}",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get accessible resources: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting accessible resources: {e}")
            return None

    # =============================================================================
    # Maintenance
    # =============================================================================

    async def cleanup_expired_permissions(self) -> Optional[Dict[str, Any]]:
        """
        Clean up expired permissions

        Returns:
            Cleanup result with count

        Example:
            >>> result = await client.cleanup_expired_permissions()
            >>> print(f"Cleaned up {result['cleaned_count']} permissions")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/authorization/cleanup-expired"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to cleanup permissions: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error cleaning up permissions: {e}")
            return None

    # =============================================================================
    # Service Information
    # =============================================================================

    async def get_service_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get authorization service statistics

        Returns:
            Service statistics

        Example:
            >>> stats = await client.get_service_stats()
            >>> print(f"Total permissions: {stats['total_permissions']}")
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/authorization/stats")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get service stats: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
            return None

    # =============================================================================
    # Health Check
    # =============================================================================

    async def health_check(self) -> bool:
        """
        Check service health status

        Returns:
            True if service is healthy
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False


__all__ = ["AuthorizationServiceClient"]
