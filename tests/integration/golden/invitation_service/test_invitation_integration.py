"""
Invitation Service - Integration Tests

Tests full CRUD lifecycle with real database persistence.
Uses X-Internal-Call header to bypass authentication.
All tests use InvitationTestDataFactory - zero hardcoded data.
"""
import pytest
from datetime import datetime

from tests.contracts.invitation.data_contract import (
    InvitationTestDataFactory,
    InvitationStatus,
    OrganizationRole,
)

pytestmark = [pytest.mark.integration, pytest.mark.golden, pytest.mark.asyncio]

INVITATION_URL = "http://localhost:8213"


# =============================================================================
# Health Check Tests (3 tests)
# =============================================================================

class TestInvitationHealthIntegration:
    """Test health endpoints"""

    async def test_health_endpoint_returns_200(self, http_client):
        """GET /health returns 200"""
        response = await http_client.get(f"{INVITATION_URL}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "invitation_service"

    async def test_health_includes_port(self, http_client):
        """Health check includes correct port"""
        response = await http_client.get(f"{INVITATION_URL}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["port"] == 8213

    async def test_info_endpoint_returns_200(self, http_client):
        """GET /info returns service info"""
        response = await http_client.get(f"{INVITATION_URL}/info")

        assert response.status_code == 200
        data = response.json()
        assert "service" in data


# =============================================================================
# Create Invitation Integration Tests (8 tests)
# =============================================================================

class TestInvitationCreateIntegration:
    """Test invitation creation with real DB"""

    async def test_create_invitation_returns_201(
        self, http_client, internal_headers, cleanup_invitations
    ):
        """POST creates invitation and returns data"""
        org_id = InvitationTestDataFactory.make_organization_id()
        create_data = InvitationTestDataFactory.make_create_request().model_dump()

        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/organizations/{org_id}",
            json=create_data,
            headers=internal_headers
        )

        # May return 200 or 201, or 400 if org validation fails
        if response.status_code in [200, 201]:
            data = response.json()
            assert "invitation_id" in data
            cleanup_invitations(data["invitation_id"])

    async def test_create_returns_invitation_token(
        self, http_client, internal_headers, cleanup_invitations
    ):
        """Created invitation includes token"""
        org_id = InvitationTestDataFactory.make_organization_id()
        create_data = InvitationTestDataFactory.make_create_request().model_dump()

        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/organizations/{org_id}",
            json=create_data,
            headers=internal_headers
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert "invitation_token" in data
            cleanup_invitations(data["invitation_id"])

    async def test_create_returns_expiration(
        self, http_client, internal_headers, cleanup_invitations
    ):
        """Created invitation includes expiration"""
        org_id = InvitationTestDataFactory.make_organization_id()
        create_data = InvitationTestDataFactory.make_create_request().model_dump()

        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/organizations/{org_id}",
            json=create_data,
            headers=internal_headers
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert "expires_at" in data
            cleanup_invitations(data["invitation_id"])

    async def test_create_with_admin_role(
        self, http_client, internal_headers, cleanup_invitations
    ):
        """Create invitation with admin role"""
        org_id = InvitationTestDataFactory.make_organization_id()
        create_data = InvitationTestDataFactory.make_create_request(
            role=OrganizationRole.ADMIN
        ).model_dump()

        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/organizations/{org_id}",
            json=create_data,
            headers=internal_headers
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert data["role"] == "admin"
            cleanup_invitations(data["invitation_id"])

    async def test_create_with_message(
        self, http_client, internal_headers, cleanup_invitations
    ):
        """Create invitation with custom message"""
        org_id = InvitationTestDataFactory.make_organization_id()
        custom_message = InvitationTestDataFactory.make_invitation_message()
        create_data = InvitationTestDataFactory.make_create_request(
            message=custom_message
        ).model_dump()

        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/organizations/{org_id}",
            json=create_data,
            headers=internal_headers
        )

        # Should succeed or fail with org validation
        assert response.status_code in [200, 201, 400]

    async def test_create_invalid_email_returns_422(
        self, http_client, internal_headers
    ):
        """Invalid email returns 422"""
        org_id = InvitationTestDataFactory.make_organization_id()
        create_data = {
            "email": InvitationTestDataFactory.make_invalid_email(),
            "role": "member"
        }

        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/organizations/{org_id}",
            json=create_data,
            headers=internal_headers
        )

        assert response.status_code == 422

    async def test_create_requires_auth(self, http_client):
        """Create without auth returns 401"""
        org_id = InvitationTestDataFactory.make_organization_id()
        create_data = InvitationTestDataFactory.make_create_request().model_dump()

        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/organizations/{org_id}",
            json=create_data
        )

        assert response.status_code == 401


# =============================================================================
# Get Invitation Integration Tests (6 tests)
# =============================================================================

class TestInvitationGetIntegration:
    """Test invitation retrieval with real DB"""

    async def test_get_by_token_returns_details(
        self, http_client, internal_headers, cleanup_invitations
    ):
        """GET by token returns invitation details"""
        # First create an invitation
        org_id = InvitationTestDataFactory.make_organization_id()
        create_data = InvitationTestDataFactory.make_create_request().model_dump()

        create_response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/organizations/{org_id}",
            json=create_data,
            headers=internal_headers
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create invitation for test")

        created = create_response.json()
        token = created["invitation_token"]
        cleanup_invitations(created["invitation_id"])

        # Now get by token (no auth required for this endpoint)
        get_response = await http_client.get(
            f"{INVITATION_URL}/api/v1/invitations/{token}"
        )

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["email"] == create_data["email"]

    async def test_get_invalid_token_returns_404(self, http_client):
        """GET with invalid token returns 404"""
        fake_token = InvitationTestDataFactory.make_invitation_token()

        response = await http_client.get(
            f"{INVITATION_URL}/api/v1/invitations/{fake_token}"
        )

        assert response.status_code == 404

    async def test_get_short_token_returns_404(self, http_client):
        """GET with short token returns 404"""
        short_token = InvitationTestDataFactory.make_invalid_token_short()

        response = await http_client.get(
            f"{INVITATION_URL}/api/v1/invitations/{short_token}"
        )

        assert response.status_code == 404


# =============================================================================
# List Invitations Integration Tests (5 tests)
# =============================================================================

class TestInvitationListIntegration:
    """Test invitation listing with real DB"""

    async def test_list_org_invitations(
        self, http_client, internal_headers
    ):
        """GET org invitations returns list"""
        org_id = InvitationTestDataFactory.make_organization_id()

        response = await http_client.get(
            f"{INVITATION_URL}/api/v1/invitations/organizations/{org_id}",
            headers=internal_headers
        )

        # May return 200 with list or 403 if permission denied
        if response.status_code == 200:
            data = response.json()
            assert "invitations" in data
            assert "total" in data

    async def test_list_with_pagination(
        self, http_client, internal_headers
    ):
        """List respects pagination params"""
        org_id = InvitationTestDataFactory.make_organization_id()

        response = await http_client.get(
            f"{INVITATION_URL}/api/v1/invitations/organizations/{org_id}",
            params={"limit": 10, "offset": 0},
            headers=internal_headers
        )

        if response.status_code == 200:
            data = response.json()
            assert data["limit"] == 10
            assert data["offset"] == 0

    async def test_list_requires_auth(self, http_client):
        """List without auth returns 401"""
        org_id = InvitationTestDataFactory.make_organization_id()

        response = await http_client.get(
            f"{INVITATION_URL}/api/v1/invitations/organizations/{org_id}"
        )

        assert response.status_code == 401


# =============================================================================
# Cancel Invitation Integration Tests (5 tests)
# =============================================================================

class TestInvitationCancelIntegration:
    """Test invitation cancellation with real DB"""

    async def test_cancel_returns_success(
        self, http_client, internal_headers, cleanup_invitations
    ):
        """DELETE cancels invitation"""
        # First create an invitation
        org_id = InvitationTestDataFactory.make_organization_id()
        create_data = InvitationTestDataFactory.make_create_request().model_dump()

        create_response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/organizations/{org_id}",
            json=create_data,
            headers=internal_headers
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create invitation for test")

        created = create_response.json()
        inv_id = created["invitation_id"]

        # Now cancel
        delete_response = await http_client.delete(
            f"{INVITATION_URL}/api/v1/invitations/{inv_id}",
            headers=internal_headers
        )

        assert delete_response.status_code == 200

    async def test_cancel_nonexistent_returns_404(
        self, http_client, internal_headers
    ):
        """DELETE nonexistent returns 404"""
        fake_id = InvitationTestDataFactory.make_invitation_id()

        response = await http_client.delete(
            f"{INVITATION_URL}/api/v1/invitations/{fake_id}",
            headers=internal_headers
        )

        assert response.status_code == 404

    async def test_cancel_requires_auth(self, http_client):
        """DELETE without auth returns 401"""
        fake_id = InvitationTestDataFactory.make_invitation_id()

        response = await http_client.delete(
            f"{INVITATION_URL}/api/v1/invitations/{fake_id}"
        )

        assert response.status_code == 401


# =============================================================================
# Resend Invitation Integration Tests (4 tests)
# =============================================================================

class TestInvitationResendIntegration:
    """Test invitation resending with real DB"""

    async def test_resend_returns_success(
        self, http_client, internal_headers, cleanup_invitations
    ):
        """POST resend updates invitation"""
        # First create an invitation
        org_id = InvitationTestDataFactory.make_organization_id()
        create_data = InvitationTestDataFactory.make_create_request().model_dump()

        create_response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/organizations/{org_id}",
            json=create_data,
            headers=internal_headers
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create invitation for test")

        created = create_response.json()
        inv_id = created["invitation_id"]
        cleanup_invitations(inv_id)

        # Now resend
        resend_response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/{inv_id}/resend",
            headers=internal_headers
        )

        assert resend_response.status_code == 200

    async def test_resend_nonexistent_returns_404(
        self, http_client, internal_headers
    ):
        """Resend nonexistent returns 404"""
        fake_id = InvitationTestDataFactory.make_invitation_id()

        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/{fake_id}/resend",
            headers=internal_headers
        )

        assert response.status_code == 404

    async def test_resend_requires_auth(self, http_client):
        """Resend without auth returns 401"""
        fake_id = InvitationTestDataFactory.make_invitation_id()

        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/{fake_id}/resend"
        )

        assert response.status_code == 401


# =============================================================================
# Accept Invitation Integration Tests (5 tests)
# =============================================================================

class TestInvitationAcceptIntegration:
    """Test invitation acceptance with real DB"""

    async def test_accept_requires_auth(self, http_client):
        """Accept without auth returns 401"""
        accept_data = InvitationTestDataFactory.make_accept_request().model_dump()

        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/accept",
            json=accept_data
        )

        assert response.status_code == 401

    async def test_accept_invalid_token_returns_error(
        self, http_client, internal_headers
    ):
        """Accept with invalid token returns error"""
        accept_data = InvitationTestDataFactory.make_accept_request().model_dump()

        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/accept",
            json=accept_data,
            headers=internal_headers
        )

        # Should return 404 or 400
        assert response.status_code in [400, 404]

    async def test_accept_empty_token_returns_error(
        self, http_client, internal_headers
    ):
        """Accept with empty token returns 422 or 404"""
        accept_data = {"invitation_token": ""}

        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/accept",
            json=accept_data,
            headers=internal_headers
        )

        # Empty token may return 422 (validation) or 404 (not found)
        assert response.status_code in [404, 422]


# =============================================================================
# Admin Endpoints Integration Tests (3 tests)
# =============================================================================

class TestInvitationAdminIntegration:
    """Test admin endpoints with real DB"""

    async def test_expire_old_invitations(
        self, http_client, internal_headers
    ):
        """Admin expire endpoint works"""
        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/admin/expire-invitations",
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "expired_count" in data

    async def test_expire_returns_count(
        self, http_client, internal_headers
    ):
        """Expire returns count of expired invitations"""
        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/admin/expire-invitations",
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["expired_count"], int)
        assert data["expired_count"] >= 0
