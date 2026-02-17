"""
Component tests for Auth Service registration
TDD approach - test first, then fix
"""
import pytest
from datetime import datetime, timezone

from microservices.auth_service.auth_service import AuthenticationService
from tests.component.golden.auth_service.mocks import MockJWTManager, MockAccountClient

pytestmark = [pytest.mark.component, pytest.mark.tdd]


class TestAuthServiceRegistrationAccountCreation:
    """Test that account creation works with mock clients"""

    @pytest.mark.asyncio
    async def test_registration_creates_account_via_protocol_method(self):
        """Test that registration uses the protocol's ensure_account method"""
        # Arrange
        jwt_manager = MockJWTManager()
        account_client = MockAccountClient()

        auth_service = AuthenticationService(
            jwt_manager=jwt_manager,
            account_client=account_client,
            notification_client=None,
            event_bus=None,
            config=None,
        )

        # Start registration
        start_result = await auth_service.start_registration(
            email="newuser@example.com",
            password="SecurePass123!",
            name="New User",
        )

        pending_id = start_result["pending_registration_id"]
        code = auth_service._pending_registrations[pending_id]["code"]

        # Act - Verify registration
        verify_result = await auth_service.verify_registration(
            pending_registration_id=pending_id,
            code=code,
        )

        # Assert
        assert verify_result["success"] is True
        user_id = verify_result["user_id"]

        # Account should be created in the mock client
        account = await account_client.get_account_profile(user_id)
        assert account is not None, "Account should be created via ensure_account"
        assert account["email"] == "newuser@example.com"
        assert account["name"] == "New User"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
