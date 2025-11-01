"""
Authentication Service - Pure Authentication Service
Handles identity authentication only, authorization is handled separately

Uses custom self-issued JWT tokens (isA_user provider)
"""

import jwt
import httpx
import logging
import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import uuid
import secrets
from enum import Enum

# Add parent directory to path for core imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from core.jwt_manager import (
    JWTManager,
    get_jwt_manager,
    TokenClaims,
    TokenType,
    TokenScope
)
from core.nats_client import Event, EventType, ServiceSource

# Import Account Service Client for user validation
from microservices.account_service.client import AccountServiceClient
from microservices.notification_service.client import NotificationServiceClient

logger = logging.getLogger(__name__)

class AuthProvider(Enum):
    """Authentication Providers"""
    AUTH0 = "auth0"
    ISA_USER = "isa_user"  # Custom JWT provider (primary)
    LOCAL = "local"  # Alias for isa_user

class AuthenticationService:
    """Pure Authentication Service - Custom JWT Implementation"""

    def __init__(self, config=None, event_bus=None):
        """
        Initialize authentication service

        Args:
            config: ServiceConfig object from ConfigManager (optional for backwards compatibility)
            event_bus: NATSEventBus instance for event publishing (optional)
        """
        import os

        # Auth0 configuration (for OAuth integration)
        self.auth0_domain = config.auth0_domain if config and config.auth0_domain else "your-auth0-domain.auth0.com"
        self.auth0_audience = config.auth0_audience if config and config.auth0_audience else ""
        self.auth0_algorithms = ["RS256"]

        # Custom JWT Manager - PRIMARY AUTH METHOD
        jwt_secret = (
            config.local_jwt_secret if config and config.local_jwt_secret else
            os.getenv("JWT_SECRET") or
            None
        )

        jwt_expiry = config.jwt_expiration if config and hasattr(config, 'jwt_expiration') else 3600

        self.jwt_manager = get_jwt_manager(
            secret_key=jwt_secret,
            algorithm="HS256",
            issuer="isA_user",
            access_token_expiry=jwt_expiry,
            refresh_token_expiry=604800  # 7 days
        )

        # HTTP client for Auth0 verification
        self.http_client = httpx.AsyncClient(timeout=10.0)

        # Event bus for publishing authentication events
        self.event_bus = event_bus

        # Account Service Client for user validation
        self.account_client = AccountServiceClient()
        # Notification Service Client for sending verification emails
        self.notification_client = NotificationServiceClient()

        logger.info("Auth service initialized with custom JWT and Account Service integration")
        # In-memory pending registration store (replace with DB/Redis in production)
        self._pending_registrations: Dict[str, Dict[str, Any]] = {}
    
    async def verify_token(self, token: str, provider: Optional[str] = None) -> Dict[str, Any]:
        """Verify JWT Token"""
        try:
            # Auto-detect provider if not specified
            if not provider:
                provider = self._detect_provider(token)

            # Route to appropriate verification method
            if provider == AuthProvider.ISA_USER.value or provider == AuthProvider.LOCAL.value:
                return await self._verify_custom_jwt(token)
            elif provider == AuthProvider.AUTH0.value:
                return await self._verify_auth0_token(token)
            else:
                return {
                    "valid": False,
                    "error": f"Unsupported provider: {provider}"
                }

        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def _verify_auth0_token(self, token: str) -> Dict[str, Any]:
        """Verify Auth0 JWT Token"""
        try:
            # 获取Auth0公钥
            jwks_url = f"https://{self.auth0_domain}/.well-known/jwks.json"
            jwks_response = await self.http_client.get(jwks_url)
            jwks = jwks_response.json()
            
            # 解码token头部获取kid
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            
            # 找到对应的公钥
            public_key = None
            for key in jwks["keys"]:
                if key["kid"] == kid:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break
            
            if not public_key:
                return {"valid": False, "error": "Public key not found"}
            
            # 验证token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=self.auth0_algorithms,
                audience=self.auth0_audience,
                issuer=f"https://{self.auth0_domain}/"
            )
            
            return {
                "valid": True,
                "provider": "auth0",
                "payload": payload,
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc)
            }
            
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": f"Invalid token: {str(e)}"}
    
    async def _verify_custom_jwt(self, token: str) -> Dict[str, Any]:
        """Verify custom isA_user JWT Token"""
        try:
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
                "jti": result.get("jti")
            }

        except Exception as e:
            logger.error(f"Custom JWT verification failed: {e}")
            return {"valid": False, "error": f"Invalid token: {str(e)}"}

    # ============================================
    # Registration & Identity Verification (email)
    # ============================================
    async def start_registration(self, email: str, password: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Begin a registration flow: create a pending registration and send a code.

        Notes:
        - Stores a verification code in-memory with TTL.
        - Does NOT create an account until verification succeeds.
        - Password is not persisted yet; replace with secure credential storage later.
        """
        # Normalize email
        normalized_email = email.strip().lower()

        # Basic rate/risk hooks could be added here

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
            "verified": False
        }

        # Send email with verification code via notification service
        try:
            async with self.notification_client as notif:
                payload = {
                    "type": "email",
                    "recipient_email": normalized_email,
                    "subject": "Your verification code",
                    "content": f"Your verification code is {verification_code}. It expires in 10 minutes.",
                    "html_content": f"<p>Your verification code is <b>{verification_code}</b>. It expires in 10 minutes.</p>",
                    "priority": "high",
                    "metadata": {
                        "category": "user_registration",
                        "pending_registration_id": pending_id
                    },
                    "tags": ["registration", "verification"]
                }
                # Direct POST to support recipient_email per notification service models
                resp = await notif.client.post(
                    f"{notif.base_url}/api/v1/notifications/send",
                    json=payload
                )
                resp.raise_for_status()
        except Exception as e:
            logger.warning(f"Failed to send verification email: {e}")
            # Continue; caller can still verify using the code

        return {
            "pending_registration_id": pending_id,
            "verification_required": True,
            "expires_at": expires_at.isoformat()
        }

    async def verify_registration(self, pending_registration_id: str, code: str) -> Dict[str, Any]:
        """Verify a pending registration and create account in Account Service.

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

        # Generate a new user_id (auth as ID authority)
        user_id = f"usr_{uuid.uuid4().hex}"

        # Create the account in Account Service via ensure endpoint
        try:
            async with self.account_client as client:
                # Call ensure endpoint directly to avoid client payload mismatch
                response = await client.client.post(
                    f"{client.base_url}/api/v1/accounts/ensure",
                    json={
                        "user_id": user_id,
                        "email": email,
                        "name": name,
                        "subscription_plan": "free"
                    }
                )
                response.raise_for_status()
                account = response.json()
        except Exception as e:
            logger.error(f"Failed to create account during verification: {e}")
            return {"success": False, "error": "Account creation failed"}

        # Mark verified and cleanup
        record["verified"] = True
        del self._pending_registrations[pending_registration_id]

        # Issue tokens
        token_pair = await self.generate_token_pair(
            user_id=user_id,
            email=email,
            organization_id=None,
            permissions=[],
            metadata={"registration": "email_code"}
        )

        if not token_pair.get("success"):
            return {"success": False, "error": token_pair.get("error", "Token issuance failed")}

        return {
            "success": True,
            "user_id": user_id,
            "email": email,
            "account": account,
            "access_token": token_pair["access_token"],
            "refresh_token": token_pair["refresh_token"],
            "expires_in": token_pair["expires_in"],
            "token_type": token_pair["token_type"]
        }

    def _detect_provider(self, token: str) -> str:
        """Auto-detect token provider"""
        try:
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
    
    async def generate_dev_token(
        self,
        user_id: str,
        email: str,
        expires_in: int = 3600,
        organization_id: Optional[str] = None,
        permissions: Optional[list] = None,
        metadata: Optional[dict] = None
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
            # Validate user exists in Account Service (synchronous dependency)
            # Note: In development mode, we allow token generation even if user not found
            try:
                async with self.account_client as client:
                    user_account = await client.get_account_profile(user_id)
                    if not user_account:
                        logger.warning(f"User {user_id} not found in Account Service - proceeding anyway (dev/test mode)")
                    else:
                        logger.info(f"User {user_id} validated via Account Service for dev token")
            except Exception as e:
                logger.warning(f"Failed to validate user via Account Service: {e}")
                logger.info(f"Proceeding with dev token generation despite Account Service validation failure")

            claims = TokenClaims(
                user_id=user_id,
                email=email,
                organization_id=organization_id,
                scope=TokenScope.USER,
                token_type=TokenType.ACCESS,
                permissions=permissions or [],
                metadata=metadata or {}
            )

            token = self.jwt_manager.create_access_token(
                claims,
                expires_delta=timedelta(seconds=expires_in)
            )

            return {
                "success": True,
                "token": token,
                "expires_in": expires_in,
                "user_id": user_id,
                "email": email,
                "token_type": "Bearer",
                "provider": "isa_user"
            }

        except Exception as e:
            logger.error(f"Token generation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_token_pair(
        self,
        user_id: str,
        email: str,
        organization_id: Optional[str] = None,
        permissions: Optional[list] = None,
        metadata: Optional[dict] = None
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
            # Validate user exists in Account Service (synchronous dependency)
            # Note: In production, you may want to enforce strict validation
            try:
                async with self.account_client as client:
                    user_account = await client.get_account_profile(user_id)
                    if not user_account:
                        logger.warning(f"User {user_id} not found in Account Service - proceeding anyway (dev/test mode)")
                    else:
                        logger.info(f"User {user_id} validated via Account Service")
            except Exception as e:
                logger.warning(f"Failed to validate user via Account Service: {e}")
                logger.info(f"Proceeding with token generation despite Account Service validation failure")

            claims = TokenClaims(
                user_id=user_id,
                email=email,
                organization_id=organization_id,
                scope=TokenScope.USER,
                token_type=TokenType.ACCESS,
                permissions=permissions or [],
                metadata=metadata or {}
            )

            token_pair = self.jwt_manager.create_token_pair(claims)

            # Publish user.logged_in event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.USER_LOGGED_IN,
                        source=ServiceSource.AUTH_SERVICE,
                        data={
                            "user_id": user_id,
                            "email": email,
                            "organization_id": organization_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "provider": "isa_user"
                        },
                        metadata={
                            "permissions": ",".join(permissions) if permissions else "",
                            "has_organization": str(organization_id is not None)
                        }
                    )
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
                "provider": "isa_user"
            }

        except Exception as e:
            logger.error(f"Token pair generation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dictionary with new access token or error
        """
        try:
            result = self.jwt_manager.refresh_access_token(refresh_token)

            if result.get("success"):
                return {
                    "success": True,
                    "access_token": result["access_token"],
                    "token_type": result["token_type"],
                    "expires_in": result["expires_in"],
                    "provider": "isa_user"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Token refresh failed")
                }

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_user_info_from_token(self, token: str) -> Dict[str, Any]:
        """Extract user information from token"""
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
            "expires_at": verification_result.get("expires_at")
        }

    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()