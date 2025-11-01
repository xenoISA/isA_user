"""
Authorization Service Client Example

Professional client for resource authorization and permission management operations with caching and performance optimizations.
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Resource types that can be authorized"""
    MCP_TOOL = "mcp_tool"
    PROMPT = "prompt"
    RESOURCE = "resource"
    API_ENDPOINT = "api_endpoint"
    DATABASE = "database"
    FILE_STORAGE = "file_storage"
    COMPUTE = "compute"
    AI_MODEL = "ai_model"


class AccessLevel(str, Enum):
    """Access levels for resources"""
    NONE = "none"
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"
    OWNER = "owner"


class PermissionSource(str, Enum):
    """Source of permission grant"""
    SUBSCRIPTION = "subscription"
    ORGANIZATION = "organization"
    ADMIN_GRANT = "admin_grant"
    SYSTEM_DEFAULT = "system_default"


@dataclass
class ResourceAccessResponse:
    """Resource access check response"""
    has_access: bool
    user_access_level: str
    permission_source: str
    subscription_tier: Optional[str]
    organization_plan: Optional[str]
    reason: str
    expires_at: Optional[str]
    metadata: Optional[Dict[str, Any]]


@dataclass
class UserPermissionSummary:
    """User permission summary"""
    user_id: str
    subscription_tier: str
    organization_id: Optional[str]
    organization_plan: Optional[str]
    total_permissions: int
    permissions_by_type: Dict[str, int]
    permissions_by_source: Dict[str, int]
    permissions_by_level: Dict[str, int]
    expires_soon_count: int


class AuthorizationClient:
    """Professional Authorization Service Client"""

    def __init__(
        self,
        base_url: str = "http://localhost:8204",
        timeout: float = 10.0,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.client: Optional[httpx.AsyncClient] = None
        self.request_count = 0
        self.error_count = 0

    async def __aenter__(self):
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=60.0
        )
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            limits=limits,
            headers={
                "User-Agent": "authorization-client/1.0",
                "Accept": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                self.request_count += 1
                response = await self.client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                last_exception = e
                if 400 <= e.response.status_code < 500:
                    self.error_count += 1
                    try:
                        error_detail = e.response.json()
                        raise Exception(error_detail.get("detail", str(e)))
                    except:
                        raise Exception(str(e))
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.2 * (2 ** attempt))
            except Exception as e:
                last_exception = e
                self.error_count += 1
                raise
        self.error_count += 1
        raise Exception(f"Request failed after {self.max_retries} attempts: {last_exception}")

    async def check_resource_access(
        self,
        user_id: str,
        resource_type: ResourceType,
        resource_name: str,
        required_access_level: AccessLevel = AccessLevel.READ_ONLY,
        organization_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ResourceAccessResponse:
        """Check if user has access to a specific resource"""
        payload = {
            "user_id": user_id,
            "resource_type": resource_type.value,
            "resource_name": resource_name,
            "required_access_level": required_access_level.value
        }
        if organization_id:
            payload["organization_id"] = organization_id
        if context:
            payload["context"] = context

        result = await self._make_request(
            "POST",
            "/api/v1/authorization/check-access",
            json=payload
        )

        return ResourceAccessResponse(**result)

    async def grant_permission(
        self,
        user_id: str,
        resource_type: ResourceType,
        resource_name: str,
        access_level: AccessLevel,
        permission_source: PermissionSource = PermissionSource.ADMIN_GRANT,
        granted_by_user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        expires_at: Optional[str] = None,
        reason: Optional[str] = None
    ) -> bool:
        """Grant resource permission to user"""
        payload = {
            "user_id": user_id,
            "resource_type": resource_type.value,
            "resource_name": resource_name,
            "access_level": access_level.value,
            "permission_source": permission_source.value
        }
        if granted_by_user_id:
            payload["granted_by_user_id"] = granted_by_user_id
        if organization_id:
            payload["organization_id"] = organization_id
        if expires_at:
            payload["expires_at"] = expires_at
        if reason:
            payload["reason"] = reason

        result = await self._make_request(
            "POST",
            "/api/v1/authorization/grant",
            json=payload
        )

        return "successfully" in result.get("message", "")

    async def revoke_permission(
        self,
        user_id: str,
        resource_type: ResourceType,
        resource_name: str,
        revoked_by_user_id: Optional[str] = None,
        reason: Optional[str] = None
    ) -> bool:
        """Revoke resource permission from user"""
        payload = {
            "user_id": user_id,
            "resource_type": resource_type.value,
            "resource_name": resource_name
        }
        if revoked_by_user_id:
            payload["revoked_by_user_id"] = revoked_by_user_id
        if reason:
            payload["reason"] = reason

        result = await self._make_request(
            "POST",
            "/api/v1/authorization/revoke",
            json=payload
        )

        return "successfully" in result.get("message", "")

    async def get_user_permissions(self, user_id: str) -> UserPermissionSummary:
        """Get comprehensive permission summary for user"""
        result = await self._make_request(
            "GET",
            f"/api/v1/authorization/user-permissions/{user_id}"
        )

        return UserPermissionSummary(**result)

    async def list_user_accessible_resources(
        self,
        user_id: str,
        resource_type: Optional[ResourceType] = None
    ) -> List[Dict[str, Any]]:
        """List all resources accessible to a user"""
        params = {}
        if resource_type:
            params["resource_type"] = resource_type.value

        result = await self._make_request(
            "GET",
            f"/api/v1/authorization/user-resources/{user_id}",
            params=params
        )

        return result.get("accessible_resources", [])

    async def bulk_grant_permissions(
        self,
        operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Grant multiple permissions in bulk"""
        result = await self._make_request(
            "POST",
            "/api/v1/authorization/bulk-grant",
            json={"operations": operations}
        )

        return result

    async def bulk_revoke_permissions(
        self,
        operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Revoke multiple permissions in bulk"""
        result = await self._make_request(
            "POST",
            "/api/v1/authorization/bulk-revoke",
            json={"operations": operations}
        )

        return result

    async def cleanup_expired_permissions(self) -> int:
        """Clean up expired permissions (admin operation)"""
        result = await self._make_request(
            "POST",
            "/api/v1/authorization/cleanup-expired"
        )

        return result.get("cleaned_count", 0)

    async def get_service_stats(self) -> Dict[str, Any]:
        """Get authorization service statistics"""
        return await self._make_request("GET", "/api/v1/authorization/stats")

    async def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        return await self._make_request("GET", "/api/v1/authorization/info")

    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        return await self._make_request("GET", "/health")

    async def detailed_health_check(self) -> Dict[str, Any]:
        """Detailed health check with dependencies"""
        return await self._make_request("GET", "/health/detailed")

    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics"""
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0
        }


# Example Usage
async def main():
    print("=" * 70)
    print("Authorization Service Client Examples")
    print("=" * 70)

    async with AuthorizationClient() as client:
        # Example 1: Health Check
        print("\n1. Health Check")
        print("-" * 70)
        health = await client.health_check()
        print(f" Service: {health['service']}")
        print(f"  Status: {health['status']}")
        print(f"  Port: {health['port']}")

        # Example 2: Detailed Health Check
        print("\n2. Detailed Health Check")
        print("-" * 70)
        detailed_health = await client.detailed_health_check()
        print(f" Service: {detailed_health['service']}")
        print(f"  Status: {detailed_health['status']}")
        print(f"  Database: {'' if detailed_health.get('database_connected') else ''}")

        # Example 3: Service Info
        print("\n3. Get Service Information")
        print("-" * 70)
        info = await client.get_service_info()
        print(f" Service: {info['service']}")
        print(f"  Version: {info['version']}")
        print(f"  Capabilities: {', '.join(info['capabilities'].keys())}")

        # Example 4: Service Stats
        print("\n4. Get Service Statistics")
        print("-" * 70)
        stats = await client.get_service_stats()
        print(f" Statistics:")
        for key, value in stats['statistics'].items():
            print(f"  {key}: {value}")

        # Use a real test user from database
        test_user_id = "test_user_2"  # Replace with actual user_id
        test_resource_type = ResourceType.API_ENDPOINT
        test_resource_name = f"example_resource_{int(datetime.now().timestamp())}"

        # Example 5: Check Access (Before Grant)
        print("\n5. Check Resource Access (Before Grant)")
        print("-" * 70)
        access = await client.check_resource_access(
            user_id=test_user_id,
            resource_type=test_resource_type,
            resource_name=test_resource_name,
            required_access_level=AccessLevel.READ_ONLY
        )
        print(f" Has access: {access.has_access}")
        print(f"  User access level: {access.user_access_level}")
        print(f"  Reason: {access.reason}")

        # Example 6: Grant Permission
        print("\n6. Grant Resource Permission")
        print("-" * 70)
        granted = await client.grant_permission(
            user_id=test_user_id,
            resource_type=test_resource_type,
            resource_name=test_resource_name,
            access_level=AccessLevel.READ_WRITE,
            permission_source=PermissionSource.ADMIN_GRANT,
            granted_by_user_id="admin_user",
            reason="Example permission grant"
        )
        print(f" Permission granted: {granted}")

        # Example 7: Check Access (After Grant)
        print("\n7. Check Resource Access (After Grant)")
        print("-" * 70)
        access_after = await client.check_resource_access(
            user_id=test_user_id,
            resource_type=test_resource_type,
            resource_name=test_resource_name,
            required_access_level=AccessLevel.READ_ONLY
        )
        print(f" Has access: {access_after.has_access}")
        print(f"  User access level: {access_after.user_access_level}")
        print(f"  Permission source: {access_after.permission_source}")

        # Example 8: Get User Permissions Summary
        print("\n8. Get User Permission Summary")
        print("-" * 70)
        summary = await client.get_user_permissions(test_user_id)
        print(f" User: {summary.user_id}")
        print(f"  Total permissions: {summary.total_permissions}")
        print(f"  Subscription: {summary.subscription_tier}")
        print(f"  Permissions by type:")
        for ptype, count in summary.permissions_by_type.items():
            print(f"    {ptype}: {count}")

        # Example 9: List User Accessible Resources
        print("\n9. List User Accessible Resources")
        print("-" * 70)
        resources = await client.list_user_accessible_resources(
            user_id=test_user_id,
            resource_type=test_resource_type
        )
        print(f" Accessible resources: {len(resources)}")
        for resource in resources[:3]:
            print(f"  - {resource['resource_name']} ({resource['access_level']})")

        # Example 10: Bulk Grant Permissions
        print("\n10. Bulk Grant Permissions")
        print("-" * 70)
        bulk_resource_1 = f"bulk_resource_1_{int(datetime.now().timestamp())}"
        bulk_resource_2 = f"bulk_resource_2_{int(datetime.now().timestamp())}"

        bulk_operations = [
            {
                "user_id": test_user_id,
                "resource_type": test_resource_type.value,
                "resource_name": bulk_resource_1,
                "access_level": AccessLevel.READ_ONLY.value,
                "permission_source": PermissionSource.ADMIN_GRANT.value,
                "granted_by_user_id": "admin_user"
            },
            {
                "user_id": test_user_id,
                "resource_type": test_resource_type.value,
                "resource_name": bulk_resource_2,
                "access_level": AccessLevel.READ_WRITE.value,
                "permission_source": PermissionSource.ADMIN_GRANT.value,
                "granted_by_user_id": "admin_user"
            }
        ]

        bulk_result = await client.bulk_grant_permissions(bulk_operations)
        print(f" Total operations: {bulk_result['total_operations']}")
        print(f"  Successful: {bulk_result['successful']}")
        print(f"  Failed: {bulk_result['failed']}")

        # Example 11: Revoke Permission
        print("\n11. Revoke Resource Permission")
        print("-" * 70)
        revoked = await client.revoke_permission(
            user_id=test_user_id,
            resource_type=test_resource_type,
            resource_name=test_resource_name,
            revoked_by_user_id="admin_user",
            reason="Example cleanup"
        )
        print(f" Permission revoked: {revoked}")

        # Example 12: Check Access (After Revoke)
        print("\n12. Check Resource Access (After Revoke)")
        print("-" * 70)
        access_revoked = await client.check_resource_access(
            user_id=test_user_id,
            resource_type=test_resource_type,
            resource_name=test_resource_name,
            required_access_level=AccessLevel.READ_ONLY
        )
        print(f" Has access: {access_revoked.has_access}")
        print(f"  Reason: {access_revoked.reason}")

        # Example 13: Bulk Revoke Permissions
        print("\n13. Bulk Revoke Permissions")
        print("-" * 70)
        bulk_revoke_operations = [
            {
                "user_id": test_user_id,
                "resource_type": test_resource_type.value,
                "resource_name": bulk_resource_1
            },
            {
                "user_id": test_user_id,
                "resource_type": test_resource_type.value,
                "resource_name": bulk_resource_2
            }
        ]

        bulk_revoke_result = await client.bulk_revoke_permissions(bulk_revoke_operations)
        print(f" Total operations: {bulk_revoke_result['total_operations']}")
        print(f"  Successful: {bulk_revoke_result['successful']}")
        print(f"  Failed: {bulk_revoke_result['failed']}")

        # Example 14: Cleanup Expired Permissions
        print("\n14. Cleanup Expired Permissions (Admin)")
        print("-" * 70)
        cleaned = await client.cleanup_expired_permissions()
        print(f" Cleaned up: {cleaned} expired permissions")

        # Show Client Metrics
        print("\n15. Client Performance Metrics")
        print("-" * 70)
        metrics = client.get_metrics()
        print(f"Total requests: {metrics['total_requests']}")
        print(f"Total errors: {metrics['total_errors']}")
        print(f"Error rate: {metrics['error_rate']:.2%}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
