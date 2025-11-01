"""
Organization Service Client

Client library for other microservices to interact with organization service
"""

import httpx
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class OrganizationServiceClient:
    """Organization Service HTTP client"""

    def __init__(self, base_url: str = None, use_internal_auth: bool = True):
        """
        Initialize Organization Service client

        Args:
            base_url: Organization service base URL, defaults to service discovery
            use_internal_auth: 使用内部服务认证 (默认 True，用于服务间调用)
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("organization_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8212"

        # 设置默认 headers（包括内部服务认证）
        default_headers = {}
        if use_internal_auth:
            from core.internal_service_auth import InternalServiceAuth
            default_headers.update(InternalServiceAuth.get_internal_service_headers())
            logger.debug("Using internal service authentication for organization service calls")

        self.client = httpx.AsyncClient(timeout=30.0, headers=default_headers)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Organization Management
    # =============================================================================

    async def create_organization(
        self,
        user_id: str,
        org_name: str,
        org_type: str = "family",
        description: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create new organization

        Args:
            user_id: Creator user ID
            org_name: Organization name
            org_type: Organization type (family, team, etc.)
            description: Description (optional)
            settings: Organization settings (optional)

        Returns:
            Created organization

        Example:
            >>> client = OrganizationServiceClient()
            >>> org = await client.create_organization(
            ...     user_id="user123",
            ...     org_name="Smith Family",
            ...     org_type="family"
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "org_name": org_name,
                "org_type": org_type
            }

            if description:
                payload["description"] = description
            if settings:
                payload["settings"] = settings

            response = await self.client.post(
                f"{self.base_url}/api/v1/organizations",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create organization: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating organization: {e}")
            return None

    async def get_organization(
        self,
        organization_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get organization by ID

        Args:
            organization_id: Organization ID
            user_id: User ID making request

        Returns:
            Organization data

        Example:
            >>> org = await client.get_organization("org123", "user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/organizations/{organization_id}",
                headers={"user-id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get organization: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting organization: {e}")
            return None

    async def get_user_organizations(
        self,
        user_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get user's organizations

        Args:
            user_id: User ID

        Returns:
            List of organizations

        Example:
            >>> orgs = await client.get_user_organizations("user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/users/organizations",
                headers={"user-id": user_id}
            )
            response.raise_for_status()
            result = response.json()
            return result.get("organizations", [])

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get user organizations: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting user organizations: {e}")
            return None

    # =============================================================================
    # Organization Members
    # =============================================================================

    async def add_member(
        self,
        organization_id: str,
        user_id: str,
        member_user_id: str,
        role: str = "member"
    ) -> Optional[Dict[str, Any]]:
        """
        Add member to organization

        Args:
            organization_id: Organization ID
            user_id: User ID adding the member
            member_user_id: User ID to add
            role: Member role

        Returns:
            Member data

        Example:
            >>> member = await client.add_member(
            ...     organization_id="org123",
            ...     user_id="user123",
            ...     member_user_id="user456",
            ...     role="member"
            ... )
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/organizations/{organization_id}/members",
                json={
                    "member_user_id": member_user_id,
                    "role": role
                },
                headers={"user-id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to add member: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error adding member: {e}")
            return None

    async def get_members(
        self,
        organization_id: str,
        user_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get organization members

        Args:
            organization_id: Organization ID
            user_id: User ID making request

        Returns:
            List of members

        Example:
            >>> members = await client.get_members("org123", "user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/organizations/{organization_id}/members",
                headers={"user-id": user_id}
            )
            response.raise_for_status()
            result = response.json()
            return result.get("members", [])

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get members: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting members: {e}")
            return None

    # =============================================================================
    # Resource Sharing (for albums, files, etc.)
    # =============================================================================

    async def create_sharing(
        self,
        organization_id: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        resource_name: str,
        share_with_all_members: bool = True,
        shared_with_members: Optional[List[str]] = None,
        default_permission: str = "read_write",
        custom_permissions: Optional[Dict[str, str]] = None,
        quota_settings: Optional[Dict[str, Any]] = None,
        restrictions: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create resource sharing within organization

        Args:
            organization_id: Organization ID
            user_id: User creating the share
            resource_type: Type of resource (album, file, folder, etc.)
            resource_id: Resource identifier
            resource_name: Resource name
            share_with_all_members: Share with all members
            shared_with_members: Specific member IDs (optional)
            default_permission: Default permission level
            custom_permissions: Custom per-user permissions (optional)
            quota_settings: Quota settings (optional)
            restrictions: Access restrictions (optional)

        Returns:
            Created sharing resource

        Example:
            >>> share = await client.create_sharing(
            ...     organization_id="org123",
            ...     user_id="user123",
            ...     resource_type="album",
            ...     resource_id="album_456",
            ...     resource_name="Family Vacation 2024",
            ...     share_with_all_members=True,
            ...     default_permission="read_write"
            ... )
        """
        try:
            payload = {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "resource_name": resource_name,
                "share_with_all_members": share_with_all_members,
                "default_permission": default_permission,
                "quota_settings": quota_settings or {},
                "restrictions": restrictions or {}
            }

            if shared_with_members:
                payload["shared_with_members"] = shared_with_members
            if custom_permissions:
                payload["custom_permissions"] = custom_permissions

            response = await self.client.post(
                f"{self.base_url}/api/v1/organizations/{organization_id}/sharing",
                json=payload,
                headers={"user-id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create sharing: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating sharing: {e}")
            return None

    async def get_sharing(
        self,
        organization_id: str,
        sharing_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get sharing resource details

        Args:
            organization_id: Organization ID
            sharing_id: Sharing resource ID
            user_id: User ID making request

        Returns:
            Sharing resource details

        Example:
            >>> share = await client.get_sharing("org123", "share_789", "user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/organizations/{organization_id}/sharing/{sharing_id}",
                headers={"user-id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get sharing: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting sharing: {e}")
            return None

    async def update_sharing(
        self,
        organization_id: str,
        sharing_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update sharing resource

        Args:
            organization_id: Organization ID
            sharing_id: Sharing resource ID
            user_id: User ID making request
            updates: Update data

        Returns:
            Updated sharing resource

        Example:
            >>> updated = await client.update_sharing(
            ...     organization_id="org123",
            ...     sharing_id="share_789",
            ...     user_id="user123",
            ...     updates={"default_permission": "read_only"}
            ... )
        """
        try:
            response = await self.client.put(
                f"{self.base_url}/api/v1/organizations/{organization_id}/sharing/{sharing_id}",
                json=updates,
                headers={"user-id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update sharing: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error updating sharing: {e}")
            return None

    async def delete_sharing(
        self,
        organization_id: str,
        sharing_id: str,
        user_id: str
    ) -> bool:
        """
        Delete/revoke sharing resource

        Args:
            organization_id: Organization ID
            sharing_id: Sharing resource ID
            user_id: User ID making request

        Returns:
            True if successful

        Example:
            >>> success = await client.delete_sharing("org123", "share_789", "user123")
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/organizations/{organization_id}/sharing/{sharing_id}",
                headers={"user-id": user_id}
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete sharing: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deleting sharing: {e}")
            return False

    async def list_shared_resources(
        self,
        organization_id: str,
        user_id: str,
        resource_type: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        List shared resources in organization

        Args:
            organization_id: Organization ID
            user_id: User ID making request
            resource_type: Filter by resource type (optional)

        Returns:
            List of shared resources

        Example:
            >>> resources = await client.list_shared_resources(
            ...     organization_id="org123",
            ...     user_id="user123",
            ...     resource_type="album"
            ... )
        """
        try:
            params = {}
            if resource_type:
                params["resource_type"] = resource_type

            response = await self.client.get(
                f"{self.base_url}/api/v1/organizations/{organization_id}/sharing",
                params=params,
                headers={"user-id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list shared resources: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing shared resources: {e}")
            return None

    async def get_member_shared_resources(
        self,
        organization_id: str,
        member_user_id: str,
        user_id: str,
        resource_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get shared resources accessible to a specific member

        Args:
            organization_id: Organization ID
            member_user_id: Member user ID
            user_id: User ID making request
            resource_type: Filter by resource type (optional)

        Returns:
            Member's shared resources

        Example:
            >>> resources = await client.get_member_shared_resources(
            ...     organization_id="org123",
            ...     member_user_id="user456",
            ...     user_id="user123",
            ...     resource_type="album"
            ... )
        """
        try:
            params = {}
            if resource_type:
                params["resource_type"] = resource_type

            response = await self.client.get(
                f"{self.base_url}/api/v1/organizations/{organization_id}/members/{member_user_id}/shared-resources",
                params=params,
                headers={"user-id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get member shared resources: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting member shared resources: {e}")
            return None

    async def check_access(
        self,
        resource_type: str,
        resource_id: str,
        user_id: str,
        required_permission: str = "read"
    ) -> bool:
        """
        Check if user has access to shared resource

        Args:
            resource_type: Resource type
            resource_id: Resource ID
            user_id: User ID
            required_permission: Required permission level

        Returns:
            True if user has access

        Example:
            >>> has_access = await client.check_access(
            ...     resource_type="album",
            ...     resource_id="album_456",
            ...     user_id="user123",
            ...     required_permission="read"
            ... )
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/sharing/check-access",
                json={
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "user_id": user_id,
                    "required_permission": required_permission
                }
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("has_access", False)
            return False

        except Exception as e:
            logger.error(f"Error checking access: {e}")
            return False

    # =============================================================================
    # Statistics
    # =============================================================================

    async def get_organization_stats(
        self,
        organization_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get organization statistics

        Args:
            organization_id: Organization ID
            user_id: User ID making request

        Returns:
            Organization statistics

        Example:
            >>> stats = await client.get_organization_stats("org123", "user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/organizations/{organization_id}/stats",
                headers={"user-id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get organization stats: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting organization stats: {e}")
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


__all__ = ["OrganizationServiceClient"]
