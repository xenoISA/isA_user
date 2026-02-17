"""
Authentication Service - Pure Authentication Service with Dependency Injection

Handles identity authentication only, authorization is handled separately
Uses custom self-issued JWT tokens (isA_user provider)

This service uses dependency injection for all external dependencies:
- JWT Manager is injected (not created at import time)
- Account client is injected (not created at import time)
- Notification client is injected (not created at import time)
- Event bus is injected (optional)
"""

import logging
from typing import TYPE_CHECKING, Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
import uuid
import secrets

# Import protocols (no I/O dependencies) - NOT the concrete implementations!
from .protocols import (
    AccountClientProtocol,
    NotificationClientProtocol,
    JWTManagerProtocol,
    EventBusProtocol,
    AuthRepositoryProtocol,
    AuthenticationError,
    InvalidTokenError,
    RegistrationError,
    VerificationError,
    InvalidCredentialsError,
    AccountDisabledError,
)
from .models import AuthProvider

# Type checking imports (not executed at runtime)
if TYPE_CHECKING:
    from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class AuthenticationService:
    """
    Pure Authentication Service - Custom JWT Implementation with DI

    All external dependencies are injected for testability.
    """

    def __init__(
        self,
        jwt_manager: Optional[JWTManagerProtocol] = None,
        account_client: Optional[AccountClientProtocol] = None,
        notification_client: Optional[NotificationClientProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        auth_repository: Optional[AuthRepositoryProtocol] = None,
        oauth_client_repository: Optional[Any] = None,
        config: Optional["ConfigManager"] = None,
    ):
        """
        Initialize authentication service with injected dependencies.

        Args:
            jwt_manager: JWT manager for token operations (inject mock for testing)
            account_client: Account service client (inject mock for testing)
            notification_client: Notification service client (inject mock for testing)
            event_bus: Event bus for publishing events (optional)
            auth_repository: Auth repository for database operations (inject mock for testing)
            oauth_client_repository: OAuth client repository for machine-to-machine auth
            config: Configuration manager (optional, for backwards compatibility)
        """
        # Store injected dependencies
        self.jwt_manager = jwt_manager
        self.account_client = account_client
        self.notification_client = notification_client
        self.event_bus = event_bus
        self.auth_repository = auth_repository
        self.oauth_client_repository = oauth_client_repository

        # Auth0 configuration (for OAuth integration)
        self.auth0_domain = (
            config.auth0_domain if config and hasattr(config, 'auth0_domain') else "your-auth0-domain.auth0.com"
        )
        self.auth0_audience = (
            config.auth0_audience if config and hasattr(config, 'auth0_audience') else ""
        )
        self.auth0_algorithms = ["RS256"]

        # HTTP client for Auth0 verification (lazy loaded)
        self._http_client = None

        # In-memory pending registration store (replace with DB/Redis in production)
        self._pending_registrations: Dict[str, Dict[str, Any]] = {}

        logger.info("Auth service initialized with dependency injection")

    @property
    def http_client(self):
        """Lazy load HTTP client for Auth0 verification"""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(timeout=10.0)
        return self._http_client

    async def verify_token(
        self, token: str, provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify JWT Token

        Args:
            token: JWT token to verify
            provider: Optional provider hint (auth0, isa_user, local)

        Returns:
            Dictionary with verification result
        """
        try:
            # Auto-detect provider if not specified
            if not provider:
                provider = self._detect_provider(token)

            # Route to appropriate verification method
            if provider in (AuthProvider.ISA_USER.value, AuthProvider.LOCAL.value):
                return await self._verify_custom_jwt(token)
            elif provider == AuthProvider.AUTH0.value:
                return await self._verify_auth0_token(token)
            else:
                return {"valid": False, "error": f"Unsupported provider: {provider}"}

        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return {"valid": False, "error": str(e)}

    async def _verify_auth0_token(self, token: str) -> Dict[str, Any]:
        """Verify Auth0 JWT Token"""
        try:
            import jwt

            # Get Auth0 public key
            jwks_url = f"https://{self.auth0_domain}/.well-known/jwks.json"
            jwks_response = await self.http_client.get(jwks_url)
            jwks = jwks_response.json()

            # Decode token header to get kid
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")

            # Find corresponding public key
            public_key = None
            for key in jwks["keys"]:
                if key["kid"] == kid:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break

            if not public_key:
                return {"valid": False, "error": "Public key not found"}

            # Verify token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=self.auth0_algorithms,
                audience=self.auth0_audience,
                issuer=f"https://{self.auth0_domain}/",
            )

            return {
                "valid": True,
                "provider": "auth0",
                "payload": payload,
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "expires_at": datetime.fromtimestamp(
                    payload.get("exp", 0), tz=timezone.utc
                ),
            }

        except Exception as e:
            import jwt
            if isinstance(e, jwt.ExpiredSignatureError):
                return {"valid": False, "error": "Token expired"}
            elif isinstance(e, jwt.InvalidTokenError):
                return {"valid": False, "error": f"Invalid token: {str(e)}"}
            else:
                return {"valid": False, "error": str(e)}

    async def _verify_custom_jwt(self, token: str) -> Dict[str, Any]:
        """Verify custom isA_user JWT Token"""
        try:
            if not self.jwt_manager:
                return {"valid": False, "error": "JWT manager not available"}

            # Use JWT manager for verification
            result = self.jwt_manager.verify_token(token)

            if not result.get("valid"):
                return result

            # Return standardized format
            return {
                "valid": True,
                "provider": "isa_user",
                "payload": result.get("payload"),
                "user_id": result.get("user_id"),
                "email": result.get("email"),
                "organization_id": result.get("organization_id"),
                "scope": result.get("scope"),
                "permissions": result.get("permissions", []),
                "metadata": result.get("metadata", {}),
                "expires_at": result.get("expires_at"),
                "issued_at": result.get("issued_at"),
                "jti": result.get("jti"),
            }

        except Exception as e:
            logger.error(f"Custom JWT verification failed: {e}")
            return {"valid": False, "error": f"Invalid token: {str(e)}"}

    def _detect_provider(self, token: str) -> str:
        """Auto-detect token provider from issuer"""
        try:
            import jwt
            payload = jwt.decode(token, options={"verify_signature": False})
            issuer = payload.get("iss", "")

            # Check issuer
            if issuer == "isA_user":
                return AuthProvider.ISA_USER.value
            elif "auth0.com" in issuer:
                return AuthProvider.AUTH0.value
            else:
                # Default to custom JWT
                return AuthProvider.ISA_USER.value

        except:
            return AuthProvider.ISA_USER.value

    # ============================================
    # Registration & Identity Verification (email)
    # ============================================

    async def start_registration(
        self, email: str, password: str, name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Begin a registration flow: create a pending registration and send a code.

        Args:
            email: User email
            password: User password
            name: Optional display name

        Returns:
            Dictionary with pending registration info

        Notes:
            - Stores a verification code in-memory with TTL.
            - Does NOT create an account until verification succeeds.
            - Password is not persisted yet; replace with secure credential storage later.
        """
        # Normalize email
        normalized_email = email.strip().lower()

        # Generate a short verification code and pending ID
        verification_code = f"{secrets.randbelow(1000000):06d}"
        pending_id = uuid.uuid4().hex

        # Set expiration (10 minutes)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        self._pending_registrations[pending_id] = {
            "email": normalized_email,
            "password": password,  # placeholder; do not persist in prod without hashing
            "name": name or normalized_email.split("@")[0],
            "code": verification_code,
            "expires_at": expires_at,
            "verified": False,
        }

        # Send email with verification code via notification service
        if self.notification_client:
            try:
                # Get the base URL and send notification
                from microservices.notification_service.clients.notification_client import (
                    NotificationServiceClient,
                )

                if isinstance(self.notification_client, NotificationServiceClient):
                    payload = {
                        "type": "email",
                        "recipient_email": normalized_email,
                        "subject": "Your verification code",
                        "content": f"Your verification code is {verification_code}. It expires in 10 minutes.",
                        "html_content": f"<p>Your verification code is <b>{verification_code}</b>. It expires in 10 minutes.</p>",
                        "priority": "high",
                        "metadata": {
                            "category": "user_registration",
                            "pending_registration_id": pending_id,
                        },
                        "tags": ["registration", "verification"],
                    }
                    base_url = self.notification_client._get_base_url()
                    resp = await self.notification_client.client.post(
                        f"{base_url}/api/v1/notifications/send", json=payload
                    )
                    resp.raise_for_status()
            except Exception as e:
                logger.warning(f"Failed to send verification email: {e}")
                # Continue; caller can still verify using the code

        return {
            "pending_registration_id": pending_id,
            "verification_required": True,
            "expires_at": expires_at.isoformat(),
        }

    async def verify_registration(
        self, pending_registration_id: str, code: str
    ) -> Dict[str, Any]:
        """
        Verify a pending registration and create account in Account Service.

        Args:
            pending_registration_id: Pending registration ID
            code: Verification code

        Returns:
            Dictionary with verification result and tokens

        On success:
            - Creates a new user in account_service using ensure endpoint
            - Binds identity notionally (future: persist credentials)
            - Returns user_id and a token pair for immediate session
        """
        record = self._pending_registrations.get(pending_registration_id)
        if not record:
            return {"success": False, "error": "Invalid pending registration"}

        # Expiry check
        if record["expires_at"] < datetime.now(timezone.utc):
            # Cleanup expired
            del self._pending_registrations[pending_registration_id]
            return {"success": False, "error": "Verification expired"}

        # Code check
        if str(code).strip() != str(record["code"]).strip():
            return {"success": False, "error": "Invalid verification code"}

        email = record["email"]
        name = record["name"]
        password = record.get("password")

        # Generate a new user_id (auth as ID authority)
        user_id = f"usr_{uuid.uuid4().hex}"

        # Hash password for storage
        password_hash = None
        if password:
            from .password_utils import hash_password
            password_hash = hash_password(password)

        # Store user in auth repository with password hash
        if self.auth_repository:
            try:
                user_data = {
                    "user_id": user_id,
                    "email": email,
                    "name": name,
                    "password_hash": password_hash,
                    "email_verified": True,
                }
                await self.auth_repository.create_user(user_data)
                logger.info(f"Created auth user {user_id} with password hash")
            except Exception as e:
                logger.error(f"Failed to create auth user: {e}")
                return {"success": False, "error": "User creation failed"}

        # Create the account in Account Service via ensure endpoint
        if self.account_client:
            try:
                # Try to call ensure_account if it exists (protocol method)
                if hasattr(self.account_client, 'ensure_account'):
                    account = await self.account_client.ensure_account(
                        user_id=user_id,
                        email=email,
                        name=name,
                    )
                else:
                    # Fall back to HTTP call for real AccountServiceClient
                    from microservices.account_service.client import AccountServiceClient

                    if isinstance(self.account_client, AccountServiceClient):
                        base_url = self.account_client._get_base_url()
                        response = await self.account_client.client.post(
                            f"{base_url}/api/v1/accounts/ensure",
                            json={
                                "user_id": user_id,
                                "email": email,
                                "name": name,
                            },
                        )
                        response.raise_for_status()
                        account = response.json()
                    else:
                        # Using protocol mock - just create minimal account dict
                        account = {
                            "user_id": user_id,
                            "email": email,
                            "name": name,
                        }
            except Exception as e:
                logger.error(f"Failed to create account during verification: {e}")
                return {"success": False, "error": "Account creation failed"}
        else:
            # No account client - just create minimal account dict
            account = {"user_id": user_id, "email": email, "name": name}

        # Mark verified and cleanup
        record["verified"] = True
        del self._pending_registrations[pending_registration_id]

        # Issue tokens
        token_pair = await self.generate_token_pair(
            user_id=user_id,
            email=email,
            organization_id=None,
            permissions=[],
            metadata={"registration": "email_code"},
        )

        if not token_pair.get("success"):
            return {
                "success": False,
                "error": token_pair.get("error", "Token issuance failed"),
            }

        return {
            "success": True,
            "user_id": user_id,
            "email": email,
            "account": account,
            "access_token": token_pair["access_token"],
            "refresh_token": token_pair["refresh_token"],
            "expires_in": token_pair["expires_in"],
            "token_type": token_pair["token_type"],
        }

    # ============================================
    # Token Generation
    # ============================================

    async def generate_dev_token(
        self,
        user_id: str,
        email: str,
        expires_in: int = 3600,
        organization_id: Optional[str] = None,
        permissions: Optional[list] = None,
        metadata: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Generate development token using custom JWT manager

        Args:
            user_id: User ID
            email: User email
            expires_in: Token expiration in seconds
            organization_id: Optional organization ID
            permissions: Optional list of permissions
            metadata: Optional metadata dictionary

        Returns:
            Dictionary with token and metadata
        """
        try:
            if not self.jwt_manager:
                return {"success": False, "error": "JWT manager not available"}

            # Validate user exists in Account Service (optional in dev mode)
            if self.account_client:
                try:
                    user_account = await self.account_client.get_account_profile(user_id)
                    if user_account:
                        logger.info(
                            f"User {user_id} validated via Account Service for dev token"
                        )
                    else:
                        logger.warning(
                            f"User {user_id} not found in Account Service - proceeding anyway (dev/test mode)"
                        )
                except Exception as e:
                    logger.warning(f"Failed to validate user via Account Service: {e}")

            # Import TokenClaims from core.jwt_manager
            from core.jwt_manager import TokenClaims, TokenScope, TokenType

            claims = TokenClaims(
                user_id=user_id,
                email=email,
                organization_id=organization_id,
                scope=TokenScope.USER,
                token_type=TokenType.ACCESS,
                permissions=permissions or [],
                metadata=metadata or {},
            )

            token = self.jwt_manager.create_access_token(
                claims, expires_delta=timedelta(seconds=expires_in)
            )

            return {
                "success": True,
                "token": token,
                "expires_in": expires_in,
                "user_id": user_id,
                "email": email,
                "token_type": "Bearer",
                "provider": "isa_user",
            }

        except Exception as e:
            logger.error(f"Token generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def generate_token_pair(
        self,
        user_id: str,
        email: str,
        organization_id: Optional[str] = None,
        permissions: Optional[list] = None,
        metadata: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Generate both access and refresh tokens

        Args:
            user_id: User ID
            email: User email
            organization_id: Optional organization ID
            permissions: Optional list of permissions
            metadata: Optional metadata dictionary

        Returns:
            Dictionary with access_token, refresh_token, and metadata
        """
        try:
            if not self.jwt_manager:
                return {"success": False, "error": "JWT manager not available"}

            # Validate user exists in Account Service (optional)
            if self.account_client:
                try:
                    user_account = await self.account_client.get_account_profile(user_id)
                    if user_account:
                        logger.info(f"User {user_id} validated via Account Service")
                    else:
                        logger.warning(
                            f"User {user_id} not found in Account Service - proceeding anyway (dev/test mode)"
                        )
                except Exception as e:
                    logger.warning(f"Failed to validate user via Account Service: {e}")

            # Import TokenClaims from core.jwt_manager
            from core.jwt_manager import TokenClaims, TokenScope, TokenType

            claims = TokenClaims(
                user_id=user_id,
                email=email,
                organization_id=organization_id,
                scope=TokenScope.USER,
                token_type=TokenType.ACCESS,
                permissions=permissions or [],
                metadata=metadata or {},
            )

            token_pair = self.jwt_manager.create_token_pair(claims)

            # Publish user.logged_in event
            if self.event_bus:
                try:
                    # Try to import Event classes, fall back to dict if not available
                    try:
                        from core.nats_client import Event

                        event = Event(
                            event_type="user.logged_in",
                            source="auth_service",
                            data={
                                "user_id": user_id,
                                "email": email,
                                "organization_id": organization_id,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "provider": "isa_user",
                            },
                            metadata={
                                "permissions": ",".join(permissions) if permissions else "",
                                "has_organization": str(organization_id is not None),
                            },
                        )
                    except ImportError:
                        # Fall back to simple dict-based event for testing
                        event = {
                            "event_type": "user.logged_in",
                            "source": "auth_service",
                            "data": {
                                "user_id": user_id,
                                "email": email,
                                "organization_id": organization_id,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "provider": "isa_user",
                            },
                            "metadata": {
                                "permissions": ",".join(permissions) if permissions else "",
                                "has_organization": str(organization_id is not None),
                            },
                        }

                    await self.event_bus.publish_event(event)
                    logger.info(f"Published user.logged_in event for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to publish user.logged_in event: {e}")
                    # Don't fail the login if event publishing fails

            return {
                "success": True,
                "access_token": token_pair["access_token"],
                "refresh_token": token_pair["refresh_token"],
                "token_type": token_pair["token_type"],
                "expires_in": int(token_pair["expires_in"]),
                "user_id": user_id,
                "email": email,
                "provider": "isa_user",
            }

        except Exception as e:
            logger.error(f"Token pair generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dictionary with new access token or error
        """
        try:
            if not self.jwt_manager:
                return {"success": False, "error": "JWT manager not available"}

            result = self.jwt_manager.refresh_access_token(refresh_token)

            if result.get("success"):
                return {
                    "success": True,
                    "access_token": result["access_token"],
                    "token_type": result["token_type"],
                    "expires_in": result["expires_in"],
                    "provider": "isa_user",
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Token refresh failed"),
                }

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return {"success": False, "error": str(e)}

    async def issue_client_credentials_token(
        self,
        *,
        client_id: str,
        client_secret: str,
        scope: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Issue OAuth2 access token via client_credentials grant."""
        try:
            if not self.jwt_manager:
                return {
                    "success": False,
                    "error": "JWT manager not available",
                    "error_code": "server_error",
                }
            if not self.oauth_client_repository:
                return {
                    "success": False,
                    "error": "OAuth client repository not available",
                    "error_code": "server_error",
                }

            client = await self.oauth_client_repository.verify_client_credentials(
                client_id, client_secret
            )
            if not client:
                return {
                    "success": False,
                    "error": "Invalid client credentials",
                    "error_code": "invalid_client",
                }

            allowed_scopes = set(client.get("allowed_scopes") or [])
            requested_scopes = set((scope or "").split()) if scope else set()
            if requested_scopes and not requested_scopes.issubset(allowed_scopes):
                return {
                    "success": False,
                    "error": "Requested scope is not allowed",
                    "error_code": "invalid_scope",
                }

            granted_scopes = requested_scopes if requested_scopes else allowed_scopes
            ttl_seconds = max(300, min(int(client.get("token_ttl_seconds", 3600)), 86400))

            from core.jwt_manager import TokenClaims, TokenScope, TokenType

            claims = TokenClaims(
                user_id=f"client:{client_id}",
                email=None,
                organization_id=client.get("organization_id"),
                scope=TokenScope.SERVICE,
                token_type=TokenType.ACCESS,
                permissions=sorted(granted_scopes),
                metadata={
                    "client_id": client_id,
                    "client_name": client.get("client_name"),
                    "grant_type": "client_credentials",
                    "aud": "a2a",
                },
            )
            token = self.jwt_manager.create_access_token(
                claims,
                expires_delta=timedelta(seconds=ttl_seconds),
            )

            return {
                "success": True,
                "access_token": token,
                "token_type": "Bearer",
                "expires_in": ttl_seconds,
                "scope": " ".join(sorted(granted_scopes)),
                "client_id": client_id,
            }

        except Exception as e:
            logger.error(f"Client credentials token issuance failed: {e}")
            return {
                "success": False,
                "error": "Token issuance failed",
                "error_code": "server_error",
            }

    async def verify_access_token_for_resource(
        self,
        token: str,
        required_scopes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Verify access token and enforce optional scope checks for resource APIs."""
        verification = await self.verify_token(token, provider=AuthProvider.ISA_USER.value)
        if not verification.get("valid"):
            return verification

        payload = verification.get("payload", {}) or {}
        if payload.get("type") != "access":
            return {"valid": False, "error": "Invalid token type"}

        token_scopes = set(verification.get("permissions", []) or [])
        required = set(required_scopes or [])
        if required and not required.issubset(token_scopes):
            return {"valid": False, "error": "Insufficient scope"}

        return verification

    # ============================================
    # Login (Email + Password)
    # ============================================

    async def login(
        self,
        email: str,
        password: str,
        organization_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Authenticate user with email and password.

        Args:
            email: User email
            password: User password
            organization_id: Optional organization context

        Returns:
            Dictionary with tokens on success, or error on failure
        """
        try:
            # Normalize email
            normalized_email = email.strip().lower()

            # Check repository is available
            if not self.auth_repository:
                return {"success": False, "error": "Auth repository not available"}

            # Get user with password hash
            user = await self.auth_repository.get_user_for_login(normalized_email)

            if not user:
                logger.warning(f"Login failed: user not found for email {normalized_email}")
                return {"success": False, "error": "Invalid email or password"}

            # Check if account is active
            if not user.get("is_active", True):
                logger.warning(f"Login failed: account disabled for user {user['user_id']}")
                return {"success": False, "error": "Account is disabled"}

            # Check if password is set
            password_hash = user.get("password_hash")
            if not password_hash:
                logger.warning(f"Login failed: no password set for user {user['user_id']}")
                return {"success": False, "error": "Password not set. Please use password reset."}

            # Verify password
            from .password_utils import verify_password
            if not verify_password(password, password_hash):
                logger.warning(f"Login failed: invalid password for user {user['user_id']}")
                return {"success": False, "error": "Invalid email or password"}

            # Update last login timestamp
            await self.auth_repository.update_last_login(user["user_id"])

            # Generate token pair
            token_pair = await self.generate_token_pair(
                user_id=user["user_id"],
                email=user["email"],
                organization_id=organization_id,
                permissions=[],
                metadata={"login_method": "email_password"},
            )

            if not token_pair.get("success"):
                return {
                    "success": False,
                    "error": token_pair.get("error", "Token generation failed"),
                }

            logger.info(f"Login successful for user {user['user_id']}")

            return {
                "success": True,
                "user_id": user["user_id"],
                "email": user["email"],
                "name": user.get("name"),
                "access_token": token_pair["access_token"],
                "refresh_token": token_pair["refresh_token"],
                "expires_in": token_pair["expires_in"],
                "token_type": token_pair["token_type"],
            }

        except Exception as e:
            logger.error(f"Login failed with exception: {e}")
            return {"success": False, "error": "Login failed"}

    async def get_user_info_from_token(self, token: str) -> Dict[str, Any]:
        """
        Extract user information from token

        Args:
            token: JWT token

        Returns:
            Dictionary with user information
        """
        verification_result = await self.verify_token(token)

        if not verification_result.get("valid"):
            return {"success": False, "error": verification_result.get("error")}

        return {
            "success": True,
            "user_id": verification_result.get("user_id"),
            "email": verification_result.get("email"),
            "organization_id": verification_result.get("organization_id"),
            "permissions": verification_result.get("permissions", []),
            "provider": verification_result.get("provider"),
            "expires_at": verification_result.get("expires_at"),
        }

    async def close(self):
        """Close HTTP client and cleanup resources"""
        if self._http_client:
            await self._http_client.aclose()
