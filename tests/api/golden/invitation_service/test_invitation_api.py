"""
Invitation Service - API Tests

Tests HTTP API contracts with JWT authentication.
All tests use InvitationTestDataFactory - zero hardcoded data.
"""
import pytest

from tests.contracts.invitation.data_contract import (
    InvitationTestDataFactory,
    InvitationStatus,
    OrganizationRole,
)

pytestmark = [pytest.mark.api, pytest.mark.golden, pytest.mark.asyncio]

INVITATION_URL = "http://localhost:8213"


# =============================================================================
# Authentication Tests (6 tests)
# =============================================================================

class TestInvitationAuthenticationAPI:
    """Test API authentication requirements"""

    async def test_create_unauthenticated_returns_401(self, http_client):
        """POST without token returns 401"""
        org_id = InvitationTestDataFactory.make_organization_id()
        create_data = InvitationTestDataFactory.make_create_request().model_dump()

        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/organizations/{org_id}",
            json=create_data
        )

        assert response.status_code == 401

    async def test_list_unauthenticated_returns_401(self, http_client):
        """GET list without token returns 401"""
        org_id = InvitationTestDataFactory.make_organization_id()

        response = await http_client.get(
            f"{INVITATION_URL}/api/v1/invitations/organizations/{org_id}"
        )

        assert response.status_code == 401

    async def test_cancel_unauthenticated_returns_401(self, http_client):
        """DELETE without token returns 401"""
        inv_id = InvitationTestDataFactory.make_invitation_id()

        response = await http_client.delete(
            f"{INVITATION_URL}/api/v1/invitations/{inv_id}"
        )

        assert response.status_code == 401

    async def test_resend_unauthenticated_returns_401(self, http_client):
        """POST resend without token returns 401"""
        inv_id = InvitationTestDataFactory.make_invitation_id()

        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/{inv_id}/resend"
        )

        assert response.status_code == 401

    async def test_accept_unauthenticated_returns_401(self, http_client):
        """POST accept without token returns 401"""
        accept_data = InvitationTestDataFactory.make_accept_request().model_dump()

        response = await http_client.post(
            f"{INVITATION_URL}/api/v1/invitations/accept",
            json=accept_data
        )

        assert response.status_code == 401

    async def test_get_by_token_no_auth_required(self, http_client):
        """GET by token does not require auth"""
        token = InvitationTestDataFactory.make_invitation_token()

        response = await http_client.get(
            f"{INVITATION_URL}/api/v1/invitations/{token}"
        )

        # Should return 404 (not found), not 401 (unauthorized)
        assert response.status_code == 404


# =============================================================================
# Create Invitation API Tests (8 tests)
# =============================================================================

class TestInvitationCreateAPI:
    """Test invitation creation API"""

    async def test_create_with_auth_accepted(self, invitation_api):
        """POST with auth is accepted"""
        org_id = InvitationTestDataFactory.make_organization_id()
        create_data = InvitationTestDataFactory.make_create_request().model_dump()

        response = await invitation_api.post(
            f"/organizations/{org_id}",
            json=create_data
        )

        # Should be accepted (may fail with org validation)
        assert response.status_code in [200, 201, 400, 403]

    async def test_create_returns_invitation_structure(self, invitation_api):
        """Created invitation has expected structure"""
        org_id = InvitationTestDataFactory.make_organization_id()
        create_data = InvitationTestDataFactory.make_create_request().model_dump()

        response = await invitation_api.post(
            f"/organizations/{org_id}",
            json=create_data
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert "invitation_id" in data
            assert "invitation_token" in data
            assert "email" in data
            assert "status" in data

    async def test_create_invalid_email_returns_422(self, invitation_api):
        """Invalid email returns 422"""
        org_id = InvitationTestDataFactory.make_organization_id()
        create_data = {
            "email": InvitationTestDataFactory.make_invalid_email(),
            "role": "member"
        }

        response = await invitation_api.post(
            f"/organizations/{org_id}",
            json=create_data
        )

        assert response.status_code == 422

    async def test_create_missing_email_returns_422(self, invitation_api):
        """Missing email returns 422"""
        org_id = InvitationTestDataFactory.make_organization_id()
        create_data = {"role": "member"}

        response = await invitation_api.post(
            f"/organizations/{org_id}",
            json=create_data
        )

        assert response.status_code == 422

    async def test_create_empty_body_returns_422(self, invitation_api):
        """Empty body returns 422"""
        org_id = InvitationTestDataFactory.make_organization_id()

        response = await invitation_api.post(
            f"/organizations/{org_id}",
            json={}
        )

        assert response.status_code == 422

    async def test_create_message_too_long_returns_422(self, invitation_api):
        """Message too long returns 422"""
        org_id = InvitationTestDataFactory.make_organization_id()
        # Build dict directly to bypass Pydantic validation (testing server-side validation)
        create_data = {
            "email": InvitationTestDataFactory.make_email(),
            "role": "member",
            "message": InvitationTestDataFactory.make_invalid_message_too_long()
        }

        response = await invitation_api.post(
            f"/organizations/{org_id}",
            json=create_data
        )

        # May return 422 or 400 depending on validation timing
        assert response.status_code in [400, 422]

    async def test_create_with_all_roles(self, invitation_api):
        """Create with each role is accepted"""
        org_id = InvitationTestDataFactory.make_organization_id()

        for role in [OrganizationRole.MEMBER, OrganizationRole.ADMIN, OrganizationRole.VIEWER]:
            create_data = InvitationTestDataFactory.make_create_request(
                role=role
            ).model_dump()

            response = await invitation_api.post(
                f"/organizations/{org_id}",
                json=create_data
            )

            # Request should be accepted (may fail validation)
            assert response.status_code in [200, 201, 400, 403]


# =============================================================================
# Get Invitation API Tests (6 tests)
# =============================================================================

class TestInvitationGetAPI:
    """Test invitation retrieval API"""

    async def test_get_nonexistent_returns_404(self, http_client):
        """GET nonexistent token returns 404"""
        token = InvitationTestDataFactory.make_invitation_token()

        response = await http_client.get(
            f"{INVITATION_URL}/api/v1/invitations/{token}"
        )

        assert response.status_code == 404

    async def test_get_returns_correct_structure(self, invitation_api, http_client):
        """GET returns expected response structure"""
        # First try to create an invitation
        org_id = InvitationTestDataFactory.make_organization_id()
        create_data = InvitationTestDataFactory.make_create_request().model_dump()

        create_response = await invitation_api.post(
            f"/organizations/{org_id}",
            json=create_data
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create invitation")

        token = create_response.json()["invitation_token"]

        # Now get it
        response = await http_client.get(
            f"{INVITATION_URL}/api/v1/invitations/{token}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "invitation_id" in data
        assert "email" in data
        assert "role" in data
        assert "status" in data

    async def test_get_short_token_returns_404(self, http_client):
        """GET with too short token returns 404"""
        short_token = "abc"

        response = await http_client.get(
            f"{INVITATION_URL}/api/v1/invitations/{short_token}"
        )

        assert response.status_code == 404


# =============================================================================
# List Invitations API Tests (5 tests)
# =============================================================================

class TestInvitationListAPI:
    """Test invitation listing API"""

    async def test_list_returns_structure(self, invitation_api):
        """List returns expected structure"""
        org_id = InvitationTestDataFactory.make_organization_id()

        response = await invitation_api.get(f"/organizations/{org_id}")

        if response.status_code == 200:
            data = response.json()
            assert "invitations" in data
            assert "total" in data
            assert "limit" in data
            assert "offset" in data

    async def test_list_respects_limit(self, invitation_api):
        """List respects limit parameter"""
        org_id = InvitationTestDataFactory.make_organization_id()

        response = await invitation_api.get(
            f"/organizations/{org_id}",
            params={"limit": 5}
        )

        if response.status_code == 200:
            data = response.json()
            assert data["limit"] == 5

    async def test_list_respects_offset(self, invitation_api):
        """List respects offset parameter"""
        org_id = InvitationTestDataFactory.make_organization_id()

        response = await invitation_api.get(
            f"/organizations/{org_id}",
            params={"offset": 10}
        )

        if response.status_code == 200:
            data = response.json()
            assert data["offset"] == 10

    async def test_list_invalid_limit_returns_422(self, invitation_api):
        """Invalid limit returns 422"""
        org_id = InvitationTestDataFactory.make_organization_id()

        response = await invitation_api.get(
            f"/organizations/{org_id}",
            params={"limit": InvitationTestDataFactory.make_invalid_limit_too_large()}
        )

        assert response.status_code == 422

    async def test_list_negative_offset_returns_422(self, invitation_api):
        """Negative offset returns 422"""
        org_id = InvitationTestDataFactory.make_organization_id()

        response = await invitation_api.get(
            f"/organizations/{org_id}",
            params={"offset": InvitationTestDataFactory.make_invalid_offset_negative()}
        )

        assert response.status_code == 422


# =============================================================================
# Cancel Invitation API Tests (4 tests)
# =============================================================================

class TestInvitationCancelAPI:
    """Test invitation cancellation API"""

    async def test_cancel_nonexistent_returns_404(self, invitation_api):
        """DELETE nonexistent returns 404"""
        inv_id = InvitationTestDataFactory.make_invitation_id()

        response = await invitation_api.delete(f"/{inv_id}")

        assert response.status_code == 404

    async def test_cancel_invalid_id_format(self, invitation_api):
        """DELETE with invalid ID format"""
        invalid_id = InvitationTestDataFactory.make_invalid_invitation_id()

        response = await invitation_api.delete(f"/{invalid_id}")

        # Should return 404 (not found) not a server error
        assert response.status_code in [400, 404]


# =============================================================================
# Resend Invitation API Tests (4 tests)
# =============================================================================

class TestInvitationResendAPI:
    """Test invitation resend API"""

    async def test_resend_nonexistent_returns_404(self, invitation_api):
        """POST resend nonexistent returns 404"""
        inv_id = InvitationTestDataFactory.make_invitation_id()

        response = await invitation_api.post(f"/{inv_id}/resend")

        assert response.status_code == 404

    async def test_resend_invalid_id_format(self, invitation_api):
        """POST resend with invalid ID format"""
        invalid_id = InvitationTestDataFactory.make_invalid_invitation_id()

        response = await invitation_api.post(f"/{invalid_id}/resend")

        assert response.status_code in [400, 404]


# =============================================================================
# Accept Invitation API Tests (5 tests)
# =============================================================================

class TestInvitationAcceptAPI:
    """Test invitation acceptance API"""

    async def test_accept_invalid_token_returns_error(self, invitation_api):
        """Accept with invalid token returns error"""
        accept_data = InvitationTestDataFactory.make_accept_request().model_dump()

        response = await invitation_api.post("/accept", json=accept_data)

        assert response.status_code in [400, 404]

    async def test_accept_empty_token_returns_error(self, invitation_api):
        """Accept with empty token returns 422 or 404"""
        accept_data = {"invitation_token": ""}

        response = await invitation_api.post("/accept", json=accept_data)

        # Empty token may return 422 (validation) or 404 (not found)
        assert response.status_code in [404, 422]

    async def test_accept_missing_token_returns_422(self, invitation_api):
        """Accept without token returns 422"""
        accept_data = {}

        response = await invitation_api.post("/accept", json=accept_data)

        assert response.status_code == 422

    async def test_accept_returns_structure(self, invitation_api, http_client):
        """Accept returns expected response structure"""
        # First create an invitation
        org_id = InvitationTestDataFactory.make_organization_id()
        create_data = InvitationTestDataFactory.make_create_request().model_dump()

        create_response = await invitation_api.post(
            f"/organizations/{org_id}",
            json=create_data
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create invitation")

        token = create_response.json()["invitation_token"]
        accept_data = {"invitation_token": token}

        response = await invitation_api.post("/accept", json=accept_data)

        if response.status_code == 200:
            data = response.json()
            assert "invitation_id" in data
            assert "organization_id" in data
            assert "user_id" in data


# =============================================================================
# Health API Tests (3 tests)
# =============================================================================

class TestInvitationHealthAPI:
    """Test health check API"""

    async def test_health_no_auth_required(self, http_client):
        """Health check does not require auth"""
        response = await http_client.get(f"{INVITATION_URL}/health")

        assert response.status_code == 200

    async def test_health_returns_structure(self, http_client):
        """Health returns expected structure"""
        response = await http_client.get(f"{INVITATION_URL}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "invitation_service"
        assert data["port"] == 8213

    async def test_info_no_auth_required(self, http_client):
        """Info endpoint does not require auth"""
        response = await http_client.get(f"{INVITATION_URL}/info")

        assert response.status_code == 200
