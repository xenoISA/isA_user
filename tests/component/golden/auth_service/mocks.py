"""
Mock implementations for Auth Service testing

These mocks implement the protocols defined in auth_service.protocols
for use in component testing without real I/O dependencies.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta


class MockJWTManager:
    """
    Mock JWT Manager implementing JWTManagerProtocol.

    Used for component tests - no real JWT operations needed.
    """

    def __init__(self):
        self._should_fail = False
        self._fail_message = ""
        self._tokens = {}  # Store generated tokens for verification

    def set_failure(self, message: str = "Mock JWT failure"):
        """Configure mock to fail on next operation"""
        self._should_fail = True
        self._fail_message = message

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token"""
        if self._should_fail:
            self._should_fail = False
            return {"valid": False, "error": self._fail_message}

        # Check if token exists in our store
        if token in self._tokens:
            token_data = self._tokens[token]
            # Check if expired
            if token_data.get("expires_at"):
                if isinstance(token_data["expires_at"], str):
                    expires_at = datetime.fromisoformat(token_data["expires_at"])
                else:
                    expires_at = token_data["expires_at"]

                if expires_at < datetime.now(timezone.utc):
                    return {"valid": False, "error": "Token expired"}

            return {
                "valid": True,
                "user_id": token_data.get("user_id"),
                "email": token_data.get("email"),
                "organization_id": token_data.get("organization_id"),
                "permissions": token_data.get("permissions", []),
                "metadata": token_data.get("metadata", {}),
                "expires_at": token_data.get("expires_at"),
                "issued_at": token_data.get("issued_at"),
                "jti": token,
                "payload": token_data,
            }
        else:
            return {"valid": False, "error": "Token not found"}

    def create_access_token(self, claims: Any, expires_delta: Any = None) -> str:
        """Create access token"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        # Generate a mock token (just a simple identifier)
        import uuid
        token = f"mock_access_{uuid.uuid4().hex[:16]}"

        # Calculate expiration
        if expires_delta:
            expires_at = datetime.now(timezone.utc) + expires_delta
        else:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Store token data
        self._tokens[token] = {
            "user_id": claims.user_id,
            "email": claims.email,
            "organization_id": claims.organization_id,
            "permissions": claims.permissions,
            "metadata": claims.metadata,
            "expires_at": expires_at,
            "issued_at": datetime.now(timezone.utc),
            "token_type": "access",
        }

        return token

    def create_token_pair(self, claims: Any) -> Dict[str, Any]:
        """Create access and refresh token pair"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        import uuid
        access_token = f"mock_access_{uuid.uuid4().hex[:16]}"
        refresh_token = f"mock_refresh_{uuid.uuid4().hex[:16]}"

        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        # Store both tokens
        token_data = {
            "user_id": claims.user_id,
            "email": claims.email,
            "organization_id": claims.organization_id,
            "permissions": claims.permissions,
            "metadata": claims.metadata,
            "issued_at": datetime.now(timezone.utc),
        }

        self._tokens[access_token] = {**token_data, "expires_at": expires_at, "token_type": "access"}
        self._tokens[refresh_token] = {
            **token_data,
            "expires_at": refresh_expires_at,
            "token_type": "refresh",
        }

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 3600,
        }

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        if self._should_fail:
            self._should_fail = False
            return {"success": False, "error": self._fail_message}

        # Verify refresh token
        result = self.verify_token(refresh_token)
        if not result.get("valid"):
            return {"success": False, "error": "Invalid refresh token"}

        # Generate new access token
        import uuid
        new_access_token = f"mock_access_{uuid.uuid4().hex[:16]}"

        token_data = self._tokens[refresh_token]
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        self._tokens[new_access_token] = {
            "user_id": token_data["user_id"],
            "email": token_data["email"],
            "organization_id": token_data.get("organization_id"),
            "permissions": token_data.get("permissions", []),
            "metadata": token_data.get("metadata", {}),
            "expires_at": expires_at,
            "issued_at": datetime.now(timezone.utc),
            "token_type": "access",
        }

        return {
            "success": True,
            "access_token": new_access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
        }


class MockAccountClient:
    """
    Mock Account Service Client implementing AccountClientProtocol.

    Used for component tests - no real HTTP calls needed.
    """

    def __init__(self):
        self._accounts = {}
        self._should_fail = False
        self._fail_message = ""

    def set_account(self, user_id: str, email: str, name: str, **kwargs):
        """Add an account to the mock store"""
        self._accounts[user_id] = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "is_active": kwargs.get("is_active", True),
            "created_at": kwargs.get("created_at", datetime.now(timezone.utc)),
            **kwargs,
        }

    def set_failure(self, message: str = "Mock account client failure"):
        """Configure mock to fail on next operation"""
        self._should_fail = True
        self._fail_message = message

    async def get_account_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get account profile from account service"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        return self._accounts.get(user_id)

    async def ensure_account(
        self, user_id: str, email: str, name: str, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Ensure account exists in account service"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        # If account exists, return it
        if user_id in self._accounts:
            return self._accounts[user_id]

        # Otherwise create it
        account = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            **kwargs,
        }
        self._accounts[user_id] = account
        return account


class MockNotificationClient:
    """
    Mock Notification Service Client implementing NotificationClientProtocol.

    Used for component tests - no real email sending needed.
    """

    def __init__(self):
        self.sent_emails = []
        self._should_fail = False
        self._fail_message = ""

    def set_failure(self, message: str = "Mock notification client failure"):
        """Configure mock to fail on next operation"""
        self._should_fail = True
        self._fail_message = message

    async def send_email(
        self,
        recipient_email: str,
        subject: str,
        content: str,
        html_content: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send email notification"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        # Record the email
        self.sent_emails.append({
            "recipient_email": recipient_email,
            "subject": subject,
            "content": content,
            "html_content": html_content,
            "timestamp": datetime.now(timezone.utc),
            **kwargs,
        })
        return True

    def get_sent_emails(self):
        """Get all sent emails"""
        return self.sent_emails.copy()

    def clear_sent_emails(self):
        """Clear sent emails list"""
        self.sent_emails.clear()


class MockEventBus:
    """
    Mock Event Bus implementing EventBusProtocol.

    Used for component tests - no real event publishing needed.
    """

    def __init__(self):
        self.published_events = []
        self._should_fail = False
        self._fail_message = ""

    def set_failure(self, message: str = "Mock event bus failure"):
        """Configure mock to fail on next operation"""
        self._should_fail = True
        self._fail_message = message

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        if self._should_fail:
            self._should_fail = False
            raise Exception(self._fail_message)

        # Store the event - handle both dict and object types
        event_data = {
            "event": event,
            "timestamp": datetime.now(timezone.utc),
        }

        # Extract event_type for easier testing
        # Try multiple approaches since Event objects may use 'type' or 'event_type'
        if isinstance(event, dict):
            event_data["event_type"] = event.get("event_type") or event.get("type")
        elif hasattr(event, 'type'):
            # Event objects from nats_client use 'type' attribute
            event_data["event_type"] = event.type
        elif hasattr(event, 'event_type'):
            event_type_val = event.event_type
            # Handle enum values
            if hasattr(event_type_val, 'value'):
                event_data["event_type"] = event_type_val.value
            else:
                event_data["event_type"] = str(event_type_val)

        self.published_events.append(event_data)

    def get_published_events(self):
        """Get all published events"""
        return self.published_events.copy()

    def clear_published_events(self):
        """Clear published events list"""
        self.published_events.clear()
