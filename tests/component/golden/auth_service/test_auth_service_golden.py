"""
Auth Service Component Tests (Golden Tests)

Tests the AuthenticationService business logic with mocked dependencies.
Uses dependency injection - no real I/O operations.
"""
import pytest
from datetime import datetime, timezone, timedelta

from microservices.auth_service.auth_service import AuthenticationService
from .mocks import (
    MockJWTManager,
    MockAccountClient,
    MockNotificationClient,
    MockEventBus,
)


class TestAuthServiceTokenGeneration:
    """Test token generation functionality"""

    @pytest.fixture
    def jwt_manager(self):
        """Create mock JWT manager"""
        return MockJWTManager()

    @pytest.fixture
    def account_client(self):
        """Create mock account client"""
        client = MockAccountClient()
        # Pre-populate with a test user
        client.set_account(
            user_id="usr_test123",
            email="test@example.com",
            name="Test User",
        )
        return client

    @pytest.fixture
    def event_bus(self):
        """Create mock event bus"""
        return MockEventBus()

    @pytest.fixture
    def auth_service(self, jwt_manager, account_client, event_bus):
        """Create auth service with mocked dependencies"""
        return AuthenticationService(
            jwt_manager=jwt_manager,
            account_client=account_client,
            notification_client=None,  # Not needed for token tests
            event_bus=event_bus,
            config=None,
        )

    @pytest.mark.asyncio
    async def test_generate_dev_token_success(self, auth_service, jwt_manager):
        """Test successful dev token generation"""
        result = await auth_service.generate_dev_token(
            user_id="usr_test123",
            email="test@example.com",
            expires_in=3600,
        )

        assert result["success"] is True
        assert "token" in result
        assert result["user_id"] == "usr_test123"
        assert result["email"] == "test@example.com"
        assert result["expires_in"] == 3600
        assert result["token_type"] == "Bearer"
        assert result["provider"] == "isa_user"

        # Verify the token was created in JWT manager
        verify_result = jwt_manager.verify_token(result["token"])
        assert verify_result["valid"] is True
        assert verify_result["user_id"] == "usr_test123"

    @pytest.mark.asyncio
    async def test_generate_token_pair_success(self, auth_service, jwt_manager, event_bus):
        """Test successful token pair generation"""
        result = await auth_service.generate_token_pair(
            user_id="usr_test123",
            email="test@example.com",
            organization_id="org_456",
            permissions=["read", "write"],
        )

        assert result["success"] is True
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["user_id"] == "usr_test123"
        assert result["email"] == "test@example.com"
        assert result["token_type"] == "Bearer"
        assert result["provider"] == "isa_user"

        # Verify both tokens were created
        access_verify = jwt_manager.verify_token(result["access_token"])
        assert access_verify["valid"] is True

        refresh_verify = jwt_manager.verify_token(result["refresh_token"])
        assert refresh_verify["valid"] is True

        # Verify event was published
        events = event_bus.get_published_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "user.logged_in"

    @pytest.mark.asyncio
    async def test_generate_token_without_jwt_manager(self):
        """Test token generation fails gracefully without JWT manager"""
        auth_service = AuthenticationService(
            jwt_manager=None,  # No JWT manager
            account_client=None,
            notification_client=None,
            event_bus=None,
            config=None,
        )

        result = await auth_service.generate_dev_token(
            user_id="usr_test123",
            email="test@example.com",
        )

        assert result["success"] is False
        assert "JWT manager not available" in result["error"]

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, auth_service, jwt_manager):
        """Test successful token refresh"""
        # First generate a token pair
        token_pair = await auth_service.generate_token_pair(
            user_id="usr_test123",
            email="test@example.com",
        )

        # Now refresh using the refresh token
        result = await auth_service.refresh_access_token(token_pair["refresh_token"])

        assert result["success"] is True
        assert "access_token" in result
        assert result["token_type"] == "Bearer"
        assert result["provider"] == "isa_user"

        # Verify the new access token is valid
        verify_result = jwt_manager.verify_token(result["access_token"])
        assert verify_result["valid"] is True

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(self, auth_service):
        """Test refresh fails with invalid token"""
        result = await auth_service.refresh_access_token("invalid_token")

        assert result["success"] is False
        assert "error" in result


class TestAuthServiceTokenVerification:
    """Test token verification functionality"""

    @pytest.fixture
    def jwt_manager(self):
        """Create mock JWT manager"""
        return MockJWTManager()

    @pytest.fixture
    def auth_service(self, jwt_manager):
        """Create auth service with mocked JWT manager"""
        return AuthenticationService(
            jwt_manager=jwt_manager,
            account_client=None,
            notification_client=None,
            event_bus=None,
            config=None,
        )

    @pytest.mark.asyncio
    async def test_verify_valid_token(self, auth_service, jwt_manager):
        """Test verification of valid custom JWT token"""
        # Generate a token first
        from core.jwt_manager import TokenClaims, TokenScope, TokenType

        claims = TokenClaims(
            user_id="usr_test123",
            email="test@example.com",
            organization_id="org_456",
            scope=TokenScope.USER,
            token_type=TokenType.ACCESS,
            permissions=["read"],
            metadata={"test": "data"},
        )
        token = jwt_manager.create_access_token(claims)

        # Verify the token
        result = await auth_service.verify_token(token, provider="isa_user")

        assert result["valid"] is True
        assert result["provider"] == "isa_user"
        assert result["user_id"] == "usr_test123"
        assert result["email"] == "test@example.com"
        assert result["organization_id"] == "org_456"
        assert result["permissions"] == ["read"]

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self, auth_service):
        """Test verification of invalid token"""
        result = await auth_service.verify_token("invalid_token", provider="isa_user")

        assert result["valid"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_user_info_from_token(self, auth_service, jwt_manager):
        """Test extracting user info from token"""
        # Generate a token first
        from core.jwt_manager import TokenClaims, TokenScope, TokenType

        claims = TokenClaims(
            user_id="usr_test123",
            email="test@example.com",
            organization_id="org_456",
            scope=TokenScope.USER,
            token_type=TokenType.ACCESS,
            permissions=["read", "write"],
            metadata={},
        )
        token = jwt_manager.create_access_token(claims)

        # Extract user info
        result = await auth_service.get_user_info_from_token(token)

        assert result["success"] is True
        assert result["user_id"] == "usr_test123"
        assert result["email"] == "test@example.com"
        assert result["organization_id"] == "org_456"
        assert result["permissions"] == ["read", "write"]
        assert result["provider"] == "isa_user"


class TestAuthServiceRegistration:
    """Test user registration functionality"""

    @pytest.fixture
    def jwt_manager(self):
        """Create mock JWT manager"""
        return MockJWTManager()

    @pytest.fixture
    def account_client(self):
        """Create mock account client"""
        return MockAccountClient()

    @pytest.fixture
    def notification_client(self):
        """Create mock notification client"""
        return MockNotificationClient()

    @pytest.fixture
    def auth_service(self, jwt_manager, account_client, notification_client):
        """Create auth service with all mocked dependencies"""
        return AuthenticationService(
            jwt_manager=jwt_manager,
            account_client=account_client,
            notification_client=notification_client,
            event_bus=None,
            config=None,
        )

    @pytest.mark.asyncio
    async def test_start_registration_success(self, auth_service, notification_client):
        """Test successful registration start"""
        result = await auth_service.start_registration(
            email="newuser@example.com",
            password="SecurePass123!",
            name="New User",
        )

        assert "pending_registration_id" in result
        assert result["verification_required"] is True
        assert "expires_at" in result

        # Verify pending registration was created
        pending_id = result["pending_registration_id"]
        assert pending_id in auth_service._pending_registrations

        pending = auth_service._pending_registrations[pending_id]
        assert pending["email"] == "newuser@example.com"
        assert pending["name"] == "New User"
        assert "code" in pending

    @pytest.mark.asyncio
    async def test_verify_registration_success(self, auth_service, jwt_manager, account_client):
        """Test successful registration verification"""
        # Start registration
        start_result = await auth_service.start_registration(
            email="newuser@example.com",
            password="SecurePass123!",
            name="New User",
        )

        pending_id = start_result["pending_registration_id"]
        code = auth_service._pending_registrations[pending_id]["code"]

        # Verify registration
        verify_result = await auth_service.verify_registration(
            pending_registration_id=pending_id,
            code=code,
        )

        assert verify_result["success"] is True
        assert verify_result["user_id"].startswith("usr_")
        assert verify_result["email"] == "newuser@example.com"
        assert "access_token" in verify_result
        assert "refresh_token" in verify_result

        # Verify account was created
        user_id = verify_result["user_id"]
        account = await account_client.get_account_profile(user_id)
        assert account is not None
        assert account["email"] == "newuser@example.com"

        # Verify pending registration was cleaned up
        assert pending_id not in auth_service._pending_registrations

    @pytest.mark.asyncio
    async def test_verify_registration_invalid_code(self, auth_service):
        """Test registration verification with invalid code"""
        # Start registration
        start_result = await auth_service.start_registration(
            email="newuser@example.com",
            password="SecurePass123!",
        )

        pending_id = start_result["pending_registration_id"]

        # Verify with wrong code
        verify_result = await auth_service.verify_registration(
            pending_registration_id=pending_id,
            code="000000",  # Wrong code
        )

        assert verify_result["success"] is False
        assert "Invalid verification code" in verify_result["error"]

    @pytest.mark.asyncio
    async def test_verify_registration_expired(self, auth_service):
        """Test registration verification with expired registration"""
        # Start registration
        start_result = await auth_service.start_registration(
            email="newuser@example.com",
            password="SecurePass123!",
        )

        pending_id = start_result["pending_registration_id"]

        # Manually expire the registration
        auth_service._pending_registrations[pending_id]["expires_at"] = (
            datetime.now(timezone.utc) - timedelta(minutes=1)
        )

        code = auth_service._pending_registrations[pending_id]["code"]

        # Try to verify
        verify_result = await auth_service.verify_registration(
            pending_registration_id=pending_id,
            code=code,
        )

        assert verify_result["success"] is False
        assert "expired" in verify_result["error"].lower()

    @pytest.mark.asyncio
    async def test_verify_registration_not_found(self, auth_service):
        """Test registration verification with non-existent pending ID"""
        verify_result = await auth_service.verify_registration(
            pending_registration_id="invalid_id",
            code="123456",
        )

        assert verify_result["success"] is False
        assert "Invalid pending registration" in verify_result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
