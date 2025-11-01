"""
Invitation Service Client Example

Professional client for invitation management operations.
Shows how other services can integrate with the invitation service.
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Invitation:
    """Invitation data"""
    invitation_id: str
    organization_id: str
    email: str
    role: str
    status: str
    invitation_token: str
    invited_by: str
    expires_at: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class InvitationDetail:
    """Detailed invitation data with organization info"""
    invitation_id: str
    organization_id: str
    organization_name: str
    email: str
    role: str
    status: str
    inviter_name: Optional[str] = None
    inviter_email: Optional[str] = None
    organization_domain: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: Optional[str] = None


class InvitationClient:
    """Professional Invitation Service Client"""

    def __init__(
        self,
        base_url: str = "http://localhost:8213",
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
                "User-Agent": "invitation-client/1.0",
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

    # ============ Invitation Management ============

    async def create_invitation(
        self,
        organization_id: str,
        user_id: str,
        email: str,
        role: str = "member",
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create organization invitation

        Args:
            organization_id: Organization ID
            user_id: User ID (inviter)
            email: Email to invite
            role: Member role (member, admin, owner)
            message: Optional personal message

        Returns:
            Invitation details
        """
        payload = {
            "email": email,
            "role": role
        }
        if message:
            payload["message"] = message

        return await self._make_request(
            "POST",
            f"/api/v1/organizations/{organization_id}/invitations",
            user_id=user_id,
            json=payload
        )

    async def get_invitation(
        self,
        invitation_token: str
    ) -> InvitationDetail:
        """
        Get invitation by token

        Args:
            invitation_token: Invitation token

        Returns:
            InvitationDetail object
        """
        result = await self._make_request(
            "GET",
            f"/api/v1/invitations/{invitation_token}"
        )
        return InvitationDetail(**result)

    async def accept_invitation(
        self,
        invitation_token: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Accept organization invitation

        Args:
            invitation_token: Invitation token
            user_id: User ID accepting invitation

        Returns:
            Acceptance confirmation
        """
        payload = {
            "invitation_token": invitation_token,
            "user_id": user_id
        }

        return await self._make_request(
            "POST",
            "/api/v1/invitations/accept",
            user_id=user_id,
            json=payload
        )

    async def get_organization_invitations(
        self,
        organization_id: str,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get all invitations for an organization

        Args:
            organization_id: Organization ID
            user_id: User ID (must have admin access)
            limit: Results limit
            offset: Results offset

        Returns:
            List of invitations
        """
        params = {
            "limit": limit,
            "offset": offset
        }

        return await self._make_request(
            "GET",
            f"/api/v1/organizations/{organization_id}/invitations",
            user_id=user_id,
            params=params
        )

    async def cancel_invitation(
        self,
        invitation_id: str,
        user_id: str
    ) -> bool:
        """
        Cancel pending invitation

        Args:
            invitation_id: Invitation ID
            user_id: User ID (inviter or admin)

        Returns:
            True if cancelled
        """
        result = await self._make_request(
            "DELETE",
            f"/api/v1/invitations/{invitation_id}",
            user_id=user_id
        )
        return "cancelled" in result.get("message", "").lower() or "success" in result.get("message", "").lower()

    async def resend_invitation(
        self,
        invitation_id: str,
        user_id: str
    ) -> bool:
        """
        Resend invitation email

        Args:
            invitation_id: Invitation ID
            user_id: User ID (inviter or admin)

        Returns:
            True if resent
        """
        result = await self._make_request(
            "POST",
            f"/api/v1/invitations/{invitation_id}/resend",
            user_id=user_id
        )
        return "resent" in result.get("message", "").lower() or "success" in result.get("message", "").lower()

    async def expire_old_invitations(self) -> Dict[str, Any]:
        """
        Expire old pending invitations (admin endpoint)

        Returns:
            Expiration summary
        """
        return await self._make_request(
            "POST",
            "/api/v1/admin/expire-invitations"
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
    print("Invitation Service Client Examples")
    print("=" * 70)

    async with InvitationClient() as client:
        # Use unique test data
        test_org_id = f"example_org_{int(datetime.now().timestamp())}"
        test_inviter_id = f"example_inviter_{int(datetime.now().timestamp())}"
        test_user_id = f"example_user_{int(datetime.now().timestamp())}"
        test_email = f"invited_{int(datetime.now().timestamp())}@example.com"

        try:
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
            print(f"  Description: {info.get('description', 'N/A')}")

            # Example 3: Create Invitation
            print("\n3. Create Invitation")
            print("-" * 70)
            print(f"  Organization: {test_org_id}")
            print(f"  Inviting: {test_email}")
            print(f"  Note: This may fail if organization service is not running")
            print(f"        or if the organization doesn't exist.")

            try:
                invitation = await client.create_invitation(
                    organization_id=test_org_id,
                    user_id=test_inviter_id,
                    email=test_email,
                    role="member",
                    message="Welcome to our team!"
                )
                invitation_id = invitation.get('invitation_id')
                invitation_token = invitation.get('invitation_token', '')
                print(f"✓ Invitation created: {invitation_id}")
                print(f"  Email: {invitation['email']}")
                print(f"  Role: {invitation['role']}")
                print(f"  Status: {invitation['status']}")
                print(f"  Token (first 20 chars): {invitation_token[:20]}...")

                # Example 4: Get Invitation Details
                print("\n4. Get Invitation Details")
                print("-" * 70)
                invitation_detail = await client.get_invitation(invitation_token)
                print(f"✓ Invitation retrieved: {invitation_detail.invitation_id}")
                print(f"  Organization: {invitation_detail.organization_name}")
                print(f"  Inviter: {invitation_detail.inviter_name or 'N/A'}")
                print(f"  Status: {invitation_detail.status}")

                # Example 5: Get Organization Invitations
                print("\n5. Get Organization Invitations")
                print("-" * 70)
                invitations = await client.get_organization_invitations(
                    organization_id=test_org_id,
                    user_id=test_inviter_id,
                    limit=10
                )
                print(f"✓ Total invitations: {invitations['total']}")
                print(f"  Showing {len(invitations.get('invitations', []))} invitations")
                for inv in invitations.get('invitations', [])[:3]:
                    print(f"  - {inv['email']} ({inv['status']})")

                # Example 6: Resend Invitation
                print("\n6. Resend Invitation")
                print("-" * 70)
                resent = await client.resend_invitation(
                    invitation_id=invitation_id,
                    user_id=test_inviter_id
                )
                if resent:
                    print(f"✓ Invitation resent successfully")
                else:
                    print(f"✗ Failed to resend invitation")

                # Example 7: Accept Invitation
                print("\n7. Accept Invitation")
                print("-" * 70)
                print(f"  User accepting: {test_user_id}")
                accepted = await client.accept_invitation(
                    invitation_token=invitation_token,
                    user_id=test_user_id
                )
                print(f"✓ Invitation accepted")
                print(f"  Organization: {accepted['organization_name']}")
                print(f"  User ID: {accepted['user_id']}")
                print(f"  Role: {accepted['role']}")

                # Example 8: Cancel Invitation (will fail if already accepted)
                print("\n8. Cancel Invitation")
                print("-" * 70)
                try:
                    cancelled = await client.cancel_invitation(
                        invitation_id=invitation_id,
                        user_id=test_inviter_id
                    )
                    if cancelled:
                        print(f"✓ Invitation cancelled")
                    else:
                        print(f"✗ Failed to cancel invitation")
                except Exception as e:
                    print(f"⚠ Cannot cancel (expected - already accepted): {e}")

            except Exception as e:
                print(f"⚠ Integration test failed: {e}")
                print(f"  This is expected if:")
                print(f"  - Organization service is not running")
                print(f"  - Test organization doesn't exist")
                print(f"  - User doesn't have permissions")

            # Example 9: Expire Old Invitations
            print("\n9. Expire Old Invitations (Admin)")
            print("-" * 70)
            expired = await client.expire_old_invitations()
            print(f"✓ Expired {expired['expired_count']} old invitations")

            # Show Client Metrics
            print("\n10. Client Performance Metrics")
            print("-" * 70)
            metrics = client.get_metrics()
            print(f"Total requests: {metrics['total_requests']}")
            print(f"Total errors: {metrics['total_errors']}")
            print(f"Error rate: {metrics['error_rate']:.2%}")

            print("\n" + "=" * 70)
            print("Examples completed!")
            print("=" * 70)

        except Exception as e:
            print(f"\n⚠ Error running examples: {e}")
            print("Make sure the invitation service is running on port 8213")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
