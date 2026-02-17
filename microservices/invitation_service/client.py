"""
Invitation Service Client

Client library for other microservices to interact with invitation service
"""

import httpx
from core.service_discovery import get_service_discovery
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class InvitationServiceClient:
    """Invitation Service HTTP client"""

    def __init__(self, base_url: str = None):
        """
        Initialize Invitation Service client

        Args:
            base_url: Invitation service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("invitation_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8211"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Invitation Management
    # =============================================================================

    async def create_invitation(
        self,
        organization_id: str,
        inviter_user_id: str,
        email: str,
        role: str = "member",
        message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create organization invitation

        Args:
            organization_id: Organization ID
            inviter_user_id: User ID creating the invitation
            email: Invitee email address
            role: Member role (default: member)
            message: Optional personal message

        Returns:
            Created invitation

        Example:
            >>> client = InvitationServiceClient()
            >>> invitation = await client.create_invitation(
            ...     organization_id="org123",
            ...     inviter_user_id="user456",
            ...     email="newmember@example.com",
            ...     role="member"
            ... )
        """
        try:
            payload = {
                "email": email,
                "role": role
            }

            if message:
                payload["message"] = message

            response = await self.client.post(
                f"{self.base_url}/api/v1/organizations/{organization_id}/invitations",
                json=payload,
                headers={"X-User-Id": inviter_user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create invitation: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating invitation: {e}")
            return None

    async def get_invitation_by_token(
        self,
        invitation_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get invitation details by token

        Args:
            invitation_token: Invitation token

        Returns:
            Invitation details

        Example:
            >>> invitation = await client.get_invitation_by_token("token_abc123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/invitations/{invitation_token}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get invitation: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting invitation: {e}")
            return None

    async def accept_invitation(
        self,
        invitation_token: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Accept organization invitation

        Args:
            invitation_token: Invitation token
            user_id: User ID accepting the invitation

        Returns:
            Accept result

        Example:
            >>> result = await client.accept_invitation("token_abc123", "user789")
        """
        try:
            payload = {
                "invitation_token": invitation_token,
                "user_id": user_id
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/invitations/accept",
                json=payload,
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to accept invitation: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error accepting invitation: {e}")
            return None

    async def get_organization_invitations(
        self,
        organization_id: str,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Get organization invitations

        Args:
            organization_id: Organization ID
            user_id: User ID making request
            limit: Result limit (default: 100)
            offset: Pagination offset (default: 0)

        Returns:
            Invitation list

        Example:
            >>> invitations = await client.get_organization_invitations("org123", "user456")
        """
        try:
            params = {"limit": limit, "offset": offset}

            response = await self.client.get(
                f"{self.base_url}/api/v1/organizations/{organization_id}/invitations",
                params=params,
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get organization invitations: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting organization invitations: {e}")
            return None

    async def cancel_invitation(
        self,
        invitation_id: str,
        user_id: str
    ) -> bool:
        """
        Cancel invitation

        Args:
            invitation_id: Invitation ID
            user_id: User ID canceling the invitation

        Returns:
            True if successful

        Example:
            >>> success = await client.cancel_invitation("inv123", "user456")
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/invitations/{invitation_id}",
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to cancel invitation: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error canceling invitation: {e}")
            return False

    async def resend_invitation(
        self,
        invitation_id: str,
        user_id: str
    ) -> bool:
        """
        Resend invitation email

        Args:
            invitation_id: Invitation ID
            user_id: User ID resending the invitation

        Returns:
            True if successful

        Example:
            >>> success = await client.resend_invitation("inv123", "user456")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/invitations/{invitation_id}/resend",
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to resend invitation: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error resending invitation: {e}")
            return False

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


__all__ = ["InvitationServiceClient"]
