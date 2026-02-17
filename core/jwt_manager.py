"""
Custom JWT Token Manager for isA_user Platform
Replaces Supabase JWT with self-issued tokens
"""

import jwt
import uuid
import secrets
import hashlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Token types"""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    DEVICE = "device"


class TokenScope(Enum):
    """Token scopes"""
    USER = "user"
    ADMIN = "admin"
    SERVICE = "service"
    DEVICE = "device"


@dataclass
class TokenClaims:
    """Standard token claims"""
    user_id: str
    email: Optional[str] = None
    organization_id: Optional[str] = None
    scope: TokenScope = TokenScope.USER
    token_type: TokenType = TokenType.ACCESS
    permissions: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []
        if self.metadata is None:
            self.metadata = {}


class JWTManager:
    """
    Custom JWT Token Manager

    Features:
    - Self-issued JWT tokens (no Supabase dependency)
    - Support for access tokens and refresh tokens
    - Token rotation and revocation
    - Multiple token types (user, service, device, API key)
    - Compatible with existing auth service patterns
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        issuer: str = "isA_user",
        access_token_expiry: int = 3600,  # 1 hour
        refresh_token_expiry: int = 604800,  # 7 days
    ):
        """
        Initialize JWT Manager

        Args:
            secret_key: Secret key for signing tokens (will auto-generate if not provided)
            algorithm: JWT algorithm (default: HS256)
            issuer: Token issuer identifier
            access_token_expiry: Access token expiry in seconds
            refresh_token_expiry: Refresh token expiry in seconds
        """
        import os

        # Get secret from environment or generate one
        self.secret_key = secret_key or os.getenv("JWT_SECRET") or self._generate_secret()
        self.algorithm = algorithm
        self.issuer = issuer
        self.access_token_expiry = access_token_expiry
        self.refresh_token_expiry = refresh_token_expiry

        # Warn if using default secret
        if not secret_key and not os.getenv("JWT_SECRET"):
            logger.warning(
                "No JWT_SECRET provided - using generated secret. "
                "This should ONLY be used in development!"
            )

    def _generate_secret(self) -> str:
        """Generate a secure random secret"""
        return secrets.token_urlsafe(64)

    def create_access_token(
        self,
        claims: TokenClaims,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create an access token

        Args:
            claims: Token claims
            expires_delta: Custom expiration time (optional)

        Returns:
            JWT access token string
        """
        now = datetime.now(tz=timezone.utc)
        expires = now + (expires_delta or timedelta(seconds=self.access_token_expiry))

        payload = {
            # Standard JWT claims
            "iss": self.issuer,  # Issuer
            "sub": claims.user_id,  # Subject (user_id)
            "iat": int(now.timestamp()),  # Issued at
            "exp": int(expires.timestamp()),  # Expiration
            "jti": str(uuid.uuid4()),  # JWT ID (unique identifier)

            # Custom claims
            "type": claims.token_type.value,
            "scope": claims.scope.value,
            "email": claims.email,
            "organization_id": claims.organization_id,
            "permissions": claims.permissions,
            "metadata": claims.metadata,
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        logger.debug(f"Created access token for user: {claims.user_id}, expires: {expires}")
        return token

    def create_refresh_token(
        self,
        claims: TokenClaims,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a refresh token

        Args:
            claims: Token claims
            expires_delta: Custom expiration time (optional)

        Returns:
            JWT refresh token string
        """
        now = datetime.now(tz=timezone.utc)
        expires = now + (expires_delta or timedelta(seconds=self.refresh_token_expiry))

        # Refresh tokens have minimal claims for security
        payload = {
            "iss": self.issuer,
            "sub": claims.user_id,
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
            "jti": str(uuid.uuid4()),
            "type": TokenType.REFRESH.value,
            "scope": claims.scope.value,
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        logger.debug(f"Created refresh token for user: {claims.user_id}, expires: {expires}")
        return token

    def create_token_pair(
        self,
        claims: TokenClaims,
        access_expires_delta: Optional[timedelta] = None,
        refresh_expires_delta: Optional[timedelta] = None
    ) -> Dict[str, str]:
        """
        Create both access and refresh tokens

        Args:
            claims: Token claims
            access_expires_delta: Custom access token expiration (optional)
            refresh_expires_delta: Custom refresh token expiration (optional)

        Returns:
            Dictionary with 'access_token' and 'refresh_token'
        """
        access_token = self.create_access_token(claims, access_expires_delta)
        refresh_token = self.create_refresh_token(claims, refresh_expires_delta)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": (access_expires_delta or timedelta(seconds=self.access_token_expiry)).total_seconds()
        }

    def verify_token(
        self,
        token: str,
        expected_type: Optional[TokenType] = None,
        verify_exp: bool = True
    ) -> Dict[str, Any]:
        """
        Verify and decode a JWT token

        Args:
            token: JWT token string
            expected_type: Expected token type (optional)
            verify_exp: Verify expiration (default: True)

        Returns:
            Dictionary with verification result and payload
        """
        try:
            # Decode and verify token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                options={"verify_exp": verify_exp}
            )

            # Check token type if specified
            if expected_type and payload.get("type") != expected_type.value:
                return {
                    "valid": False,
                    "error": f"Invalid token type. Expected {expected_type.value}, got {payload.get('type')}"
                }

            # Extract user information
            return {
                "valid": True,
                "payload": payload,
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "organization_id": payload.get("organization_id"),
                "scope": payload.get("scope"),
                "permissions": payload.get("permissions", []),
                "metadata": payload.get("metadata", {}),
                "token_type": payload.get("type"),
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc),
                "issued_at": datetime.fromtimestamp(payload.get("iat", 0), tz=timezone.utc),
                "jti": payload.get("jti")
            }

        except jwt.ExpiredSignatureError:
            return {
                "valid": False,
                "error": "Token has expired"
            }
        except jwt.InvalidIssuerError:
            return {
                "valid": False,
                "error": "Invalid token issuer"
            }
        except jwt.InvalidTokenError as e:
            return {
                "valid": False,
                "error": f"Invalid token: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Token verification failed: {e}", exc_info=True)
            return {
                "valid": False,
                "error": f"Token verification failed: {str(e)}"
            }

    def refresh_access_token(self, refresh_token: str, new_claims: Optional[TokenClaims] = None) -> Dict[str, Any]:
        """
        Create a new access token using a refresh token

        Args:
            refresh_token: Valid refresh token
            new_claims: Optional new claims (will use refresh token claims if not provided)

        Returns:
            Dictionary with new access token or error
        """
        # Verify refresh token
        result = self.verify_token(refresh_token, expected_type=TokenType.REFRESH)

        if not result.get("valid"):
            return {
                "success": False,
                "error": result.get("error", "Invalid refresh token")
            }

        # Create new claims from refresh token or use provided ones
        if not new_claims:
            new_claims = TokenClaims(
                user_id=result["user_id"],
                email=result.get("email"),
                organization_id=result.get("organization_id"),
                scope=TokenScope(result.get("scope", "user")),
                token_type=TokenType.ACCESS,
                permissions=result.get("permissions", []),
                metadata=result.get("metadata", {})
            )

        # Create new access token
        access_token = self.create_access_token(new_claims)

        return {
            "success": True,
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.access_token_expiry
        }

    def decode_without_verification(self, token: str) -> Dict[str, Any]:
        """
        Decode token without verification (for debugging/inspection)

        Args:
            token: JWT token string

        Returns:
            Decoded payload
        """
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception as e:
            logger.error(f"Failed to decode token: {e}")
            return {}

    def get_token_fingerprint(self, token: str) -> str:
        """
        Get a unique fingerprint for a token (for tracking/revocation)

        Args:
            token: JWT token string

        Returns:
            Token fingerprint (hash)
        """
        payload = self.decode_without_verification(token)
        jti = payload.get("jti", "")
        user_id = payload.get("sub", "")

        # Create fingerprint from jti + user_id
        fingerprint_data = f"{jti}:{user_id}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()


# Singleton instance for application-wide use
_jwt_manager_instance: Optional[JWTManager] = None


def get_jwt_manager(
    secret_key: Optional[str] = None,
    algorithm: str = "HS256",
    issuer: str = "isA_user",
    access_token_expiry: int = 3600,
    refresh_token_expiry: int = 604800,
) -> JWTManager:
    """
    Get or create JWT manager singleton instance

    Args:
        secret_key: Secret key for signing tokens
        algorithm: JWT algorithm
        issuer: Token issuer
        access_token_expiry: Access token expiry in seconds
        refresh_token_expiry: Refresh token expiry in seconds

    Returns:
        JWTManager instance
    """
    global _jwt_manager_instance

    if _jwt_manager_instance is None:
        _jwt_manager_instance = JWTManager(
            secret_key=secret_key,
            algorithm=algorithm,
            issuer=issuer,
            access_token_expiry=access_token_expiry,
            refresh_token_expiry=refresh_token_expiry
        )

    return _jwt_manager_instance
