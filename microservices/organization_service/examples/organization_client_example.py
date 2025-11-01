"""
Organization Service Client Example

Professional client for organization management, member management, and family sharing operations.
Shows how other services can integrate with the organization service.
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Organization:
    """Organization data"""
    organization_id: str
    name: str
    billing_email: str
    plan: str
    status: str
    member_count: int
    credits_pool: float
    settings: Dict[str, Any]
    domain: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class OrganizationMember:
    """Organization member data"""
    user_id: str
    organization_id: str
    role: str
    status: str
    permissions: List[str]
    joined_at: str


@dataclass
class SharingResource:
    """Family sharing resource data"""
    sharing_id: str
    organization_id: str
    resource_type: str
    resource_id: str
    created_by: str
    status: str
    created_at: str
    resource_name: Optional[str] = None
    share_with_all_members: bool = False
    default_permission: str = "read_write"
    total_members_shared: int = 0
    quota_settings: Optional[Dict[str, Any]] = None
    restrictions: Optional[Dict[str, Any]] = None
    expires_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class OrganizationClient:
    """Professional Organization Service Client"""

    def __init__(
        self,
        base_url: str = "http://localhost:8212",
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
                "User-Agent": "organization-client/1.0",
                "Accept": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        headers = kwargs.pop('headers', {})
        if user_id:
            headers['X-User-Id'] = user_id

        last_exception = None
        for attempt in range(self.max_retries):
            try:
                self.request_count += 1
                response = await self.client.request(
                    method,
                    endpoint,
                    headers=headers,
                    **kwargs
                )
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

    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        return await self._make_request("GET", "/health")

    async def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        return await self._make_request("GET", "/info")

    # ============ Organization Management ============

    async def create_organization(
        self,
        user_id: str,
        name: str,
        billing_email: str,
        plan: str = "free",
        domain: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Organization:
        """Create a new organization"""
        payload = {
            "name": name,
            "billing_email": billing_email,
            "plan": plan
        }
        if domain:
            payload["domain"] = domain
        if settings:
            payload["settings"] = settings

        result = await self._make_request(
            "POST",
            "/api/v1/organizations",
            user_id=user_id,
            json=payload
        )
        return Organization(**result)

    async def get_organization(
        self,
        organization_id: str,
        user_id: str
    ) -> Organization:
        """Get organization details"""
        result = await self._make_request(
            "GET",
            f"/api/v1/organizations/{organization_id}",
            user_id=user_id
        )
        return Organization(**result)

    async def update_organization(
        self,
        organization_id: str,
        user_id: str,
        name: Optional[str] = None,
        billing_email: Optional[str] = None,
        plan: Optional[str] = None,
        domain: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Organization:
        """Update organization details"""
        payload = {}
        if name is not None:
            payload["name"] = name
        if billing_email is not None:
            payload["billing_email"] = billing_email
        if plan is not None:
            payload["plan"] = plan
        if domain is not None:
            payload["domain"] = domain
        if settings is not None:
            payload["settings"] = settings

        if not payload:
            raise ValueError("At least one field must be provided for update")

        result = await self._make_request(
            "PUT",
            f"/api/v1/organizations/{organization_id}",
            user_id=user_id,
            json=payload
        )
        return Organization(**result)

    async def delete_organization(
        self,
        organization_id: str,
        user_id: str
    ) -> bool:
        """Delete organization"""
        result = await self._make_request(
            "DELETE",
            f"/api/v1/organizations/{organization_id}",
            user_id=user_id
        )
        return "deleted" in result.get("message", "").lower()

    async def get_user_organizations(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get all organizations for a user"""
        return await self._make_request(
            "GET",
            "/api/v1/users/organizations",
            user_id=user_id
        )

    # ============ Member Management ============

    async def add_member(
        self,
        organization_id: str,
        user_id: str,
        member_user_id: str,
        role: str = "member",
        permissions: Optional[List[str]] = None
    ) -> OrganizationMember:
        """Add member to organization"""
        payload = {
            "user_id": member_user_id,
            "role": role
        }
        if permissions:
            payload["permissions"] = permissions

        result = await self._make_request(
            "POST",
            f"/api/v1/organizations/{organization_id}/members",
            user_id=user_id,
            json=payload
        )
        return OrganizationMember(**result)

    async def get_members(
        self,
        organization_id: str,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        role: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get organization members"""
        params = {
            "limit": limit,
            "offset": offset
        }
        if role:
            params["role"] = role

        return await self._make_request(
            "GET",
            f"/api/v1/organizations/{organization_id}/members",
            user_id=user_id,
            params=params
        )

    async def update_member(
        self,
        organization_id: str,
        user_id: str,
        member_user_id: str,
        role: Optional[str] = None,
        status: Optional[str] = None,
        permissions: Optional[List[str]] = None
    ) -> OrganizationMember:
        """Update organization member"""
        payload = {}
        if role is not None:
            payload["role"] = role
        if status is not None:
            payload["status"] = status
        if permissions is not None:
            payload["permissions"] = permissions

        if not payload:
            raise ValueError("At least one field must be provided for update")

        result = await self._make_request(
            "PUT",
            f"/api/v1/organizations/{organization_id}/members/{member_user_id}",
            user_id=user_id,
            json=payload
        )
        return OrganizationMember(**result)

    async def remove_member(
        self,
        organization_id: str,
        user_id: str,
        member_user_id: str
    ) -> bool:
        """Remove member from organization"""
        result = await self._make_request(
            "DELETE",
            f"/api/v1/organizations/{organization_id}/members/{member_user_id}",
            user_id=user_id
        )
        return "removed" in result.get("message", "").lower()

    # ============ Context Switching ============

    async def switch_context(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Switch user context to organization or individual"""
        payload = {
            "organization_id": organization_id
        }
        return await self._make_request(
            "POST",
            "/api/v1/organizations/context",
            user_id=user_id,
            json=payload
        )

    # ============ Statistics ============

    async def get_organization_stats(
        self,
        organization_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get organization statistics"""
        return await self._make_request(
            "GET",
            f"/api/v1/organizations/{organization_id}/stats",
            user_id=user_id
        )

    async def get_organization_usage(
        self,
        organization_id: str,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get organization usage statistics"""
        params = {}
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()

        return await self._make_request(
            "GET",
            f"/api/v1/organizations/{organization_id}/usage",
            user_id=user_id,
            params=params if params else None
        )

    # ============ Family Sharing ============

    async def create_sharing(
        self,
        organization_id: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        name: str,
        description: Optional[str] = None,
        member_permissions: Optional[Dict[str, Dict[str, bool]]] = None
    ) -> SharingResource:
        """Create family sharing resource"""
        payload = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "name": name
        }
        if description:
            payload["description"] = description
        if member_permissions:
            payload["member_permissions"] = member_permissions

        result = await self._make_request(
            "POST",
            f"/api/v1/organizations/{organization_id}/sharing",
            user_id=user_id,
            json=payload
        )
        return SharingResource(**result)

    async def get_sharing(
        self,
        organization_id: str,
        sharing_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get sharing resource details"""
        return await self._make_request(
            "GET",
            f"/api/v1/organizations/{organization_id}/sharing/{sharing_id}",
            user_id=user_id
        )

    async def update_sharing(
        self,
        organization_id: str,
        sharing_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None
    ) -> SharingResource:
        """Update sharing resource"""
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if status is not None:
            payload["status"] = status

        if not payload:
            raise ValueError("At least one field must be provided for update")

        result = await self._make_request(
            "PUT",
            f"/api/v1/organizations/{organization_id}/sharing/{sharing_id}",
            user_id=user_id,
            json=payload
        )
        return SharingResource(**result)

    async def delete_sharing(
        self,
        organization_id: str,
        sharing_id: str,
        user_id: str
    ) -> bool:
        """Delete sharing resource"""
        result = await self._make_request(
            "DELETE",
            f"/api/v1/organizations/{organization_id}/sharing/{sharing_id}",
            user_id=user_id
        )
        return "deleted" in result.get("message", "").lower()

    async def list_sharings(
        self,
        organization_id: str,
        user_id: str,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List organization sharing resources"""
        params = {
            "limit": limit,
            "offset": offset
        }
        if resource_type:
            params["resource_type"] = resource_type
        if status:
            params["status"] = status

        return await self._make_request(
            "GET",
            f"/api/v1/organizations/{organization_id}/sharing",
            user_id=user_id,
            params=params
        )

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
    print("Organization Service Client Examples")
    print("=" * 70)

    async with OrganizationClient() as client:
        # Use a unique test user ID
        test_user_id = f"example_user_{int(datetime.now().timestamp())}"
        test_member_id = f"example_member_{int(datetime.now().timestamp())}"

        # Example 1: Health Check
        print("\n1. Health Check")
        print("-" * 70)
        health = await client.health_check()
        print(f"✓ Service: {health['service']}")
        print(f"  Status: {health['status']}")
        print(f"  Port: {health['port']}")

        # Example 2: Get Service Info
        print("\n2. Service Information")
        print("-" * 70)
        info = await client.get_service_info()
        print(f"✓ Service: {info['service']}")
        print(f"  Version: {info['version']}")
        print(f"  Capabilities: {', '.join(k for k, v in info['capabilities'].items() if v)}")

        # Example 3: Create Organization
        print("\n3. Create Organization")
        print("-" * 70)
        org = await client.create_organization(
            user_id=test_user_id,
            name=f"Example Organization {int(datetime.now().timestamp())}",
            billing_email="billing@example.com",
            plan="professional",
            settings={
                "allow_external_sharing": True,
                "require_2fa": False
            }
        )
        print(f"✓ Organization created: {org.organization_id}")
        print(f"  Name: {org.name}")
        print(f"  Plan: {org.plan}")
        print(f"  Credits: {org.credits_pool}")

        # Example 4: Get Organization
        print("\n4. Get Organization Details")
        print("-" * 70)
        org_details = await client.get_organization(org.organization_id, test_user_id)
        print(f"✓ Retrieved organization: {org_details.name}")
        print(f"  Status: {org_details.status}")
        print(f"  Member Count: {org_details.member_count}")

        # Example 5: Update Organization
        print("\n5. Update Organization")
        print("-" * 70)
        updated_org = await client.update_organization(
            organization_id=org.organization_id,
            user_id=test_user_id,
            name="Updated Example Organization",
            settings={
                "allow_external_sharing": False,
                "require_2fa": True
            }
        )
        print(f"✓ Organization updated: {updated_org.name}")
        print(f"  Settings updated: require_2fa={updated_org.settings.get('require_2fa')}")

        # Example 6: Get User Organizations
        print("\n6. Get User Organizations")
        print("-" * 70)
        user_orgs = await client.get_user_organizations(test_user_id)
        print(f"✓ Total organizations: {user_orgs['total']}")
        print(f"  Organizations:")
        for o in user_orgs['organizations'][:3]:
            print(f"  - {o['name']} ({o['plan']})")

        # Example 7: Add Member
        print("\n7. Add Organization Member")
        print("-" * 70)
        member = await client.add_member(
            organization_id=org.organization_id,
            user_id=test_user_id,
            member_user_id=test_member_id,
            role="member",
            permissions=["read", "write"]
        )
        print(f"✓ Member added: {member.user_id}")
        print(f"  Role: {member.role}")
        print(f"  Permissions: {', '.join(member.permissions)}")

        # Example 8: Get Members
        print("\n8. Get Organization Members")
        print("-" * 70)
        members = await client.get_members(org.organization_id, test_user_id, limit=10)
        print(f"✓ Total members: {members['total']}")
        print(f"  Members:")
        for m in members['members'][:3]:
            print(f"  - {m['user_id']} ({m['role']})")

        # Example 9: Update Member
        print("\n9. Update Member Role")
        print("-" * 70)
        updated_member = await client.update_member(
            organization_id=org.organization_id,
            user_id=test_user_id,
            member_user_id=test_member_id,
            role="admin",
            permissions=["read", "write", "delete"]
        )
        print(f"✓ Member updated: {updated_member.user_id}")
        print(f"  New Role: {updated_member.role}")

        # Example 10: Switch Context
        print("\n10. Switch Organization Context")
        print("-" * 70)
        context = await client.switch_context(test_user_id, org.organization_id)
        print(f"✓ Context switched: {context['context_type']}")
        print(f"  Organization: {context.get('organization_name', 'N/A')}")
        print(f"  User Role: {context.get('user_role', 'N/A')}")

        # Example 11: Create Family Sharing
        print("\n11. Create Family Sharing Resource")
        print("-" * 70)
        sharing = await client.create_sharing(
            organization_id=org.organization_id,
            user_id=test_user_id,
            resource_type="album",
            resource_id=f"album_{int(datetime.now().timestamp())}",
            name="Family Vacation Photos",
            description="Photos from our 2024 vacation",
            member_permissions={
                test_member_id: {
                    "can_view": True,
                    "can_edit": False,
                    "can_delete": False,
                    "can_share": False
                }
            }
        )
        print(f"✓ Sharing created: {sharing.sharing_id}")
        print(f"  Resource Type: {sharing.resource_type}")
        print(f"  Resource ID: {sharing.resource_id}")

        # Example 12: Get Sharing Details
        print("\n12. Get Sharing Resource Details")
        print("-" * 70)
        sharing_details = await client.get_sharing(
            organization_id=org.organization_id,
            sharing_id=sharing.sharing_id,
            user_id=test_user_id
        )
        print(f"✓ Sharing retrieved: {sharing_details['sharing']['sharing_id']}")
        print(f"  Status: {sharing_details['sharing']['status']}")
        print(f"  Created by: {sharing_details['sharing']['created_by']}")

        # Example 13: List Sharings
        print("\n13. List Organization Sharings")
        print("-" * 70)
        sharings = await client.list_sharings(
            organization_id=org.organization_id,
            user_id=test_user_id,
            limit=10
        )
        print(f"✓ Found {len(sharings)} sharing resources")
        for s in sharings[:3]:
            print(f"  - {s['resource_id']} ({s['resource_type']})")

        # Example 14: Get Organization Stats
        print("\n14. Get Organization Statistics")
        print("-" * 70)
        stats = await client.get_organization_stats(org.organization_id, test_user_id)
        print(f"✓ Organization: {stats['name']}")
        print(f"  Member Count: {stats['member_count']}")
        print(f"  Active Members: {stats['active_members']}")
        print(f"  Credits Pool: {stats['credits_pool']}")

        # Example 15: Remove Member
        print("\n15. Remove Organization Member")
        print("-" * 70)
        removed = await client.remove_member(
            organization_id=org.organization_id,
            user_id=test_user_id,
            member_user_id=test_member_id
        )
        print(f"✓ Member removed: {removed}")

        # Example 16: Delete Sharing
        print("\n16. Delete Sharing Resource")
        print("-" * 70)
        sharing_deleted = await client.delete_sharing(
            organization_id=org.organization_id,
            sharing_id=sharing.sharing_id,
            user_id=test_user_id
        )
        print(f"✓ Sharing deleted: {sharing_deleted}")

        # Example 17: Delete Organization
        print("\n17. Delete Organization")
        print("-" * 70)
        deleted = await client.delete_organization(org.organization_id, test_user_id)
        print(f"✓ Organization deleted: {deleted}")

        # Show Client Metrics
        print("\n18. Client Performance Metrics")
        print("-" * 70)
        metrics = client.get_metrics()
        print(f"Total requests: {metrics['total_requests']}")
        print(f"Total errors: {metrics['total_errors']}")
        print(f"Error rate: {metrics['error_rate']:.2%}")

        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
