"""
Authentication Service Models

Domain models for authentication service.
Handles user identities, sessions, and authentication-related entities.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import datetime
from enum import Enum
import json


class AuthProvider(str, Enum):
    """Authentication Providers"""
    AUTH0 = "auth0"
    ISA_USER = "isa_user"  # Custom JWT provider (primary)
    LOCAL = "local"  # Alias for isa_user


class AuthUser(BaseModel):
    """
    Auth User model (stored in auth.users table)

    Minimal user identity for authentication purposes.
    Full profile is managed by account_service.
    """
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    subscription_status: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuthSession(BaseModel):
    """
    Authentication session model (stored in auth.user_sessions table)
    """
    session_id: str
    user_id: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    invalidated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Request Models

class TokenVerificationRequest(BaseModel):
    """Token verification request"""
    token: str = Field(..., description="JWT token")
    provider: Optional[str] = Field(None, description="Provider: auth0, isa_user, local")


class DevTokenRequest(BaseModel):
    """Development token generation request"""
    user_id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    expires_in: int = Field(3600, ge=1, le=86400, description="Expiration time in seconds")
    subscription_level: Optional[str] = Field("free", description="User subscription level")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    permissions: Optional[List[str]] = Field(default=None, description="Permission list")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class TokenPairRequest(BaseModel):
    """Token pair generation request (access + refresh)"""
    user_id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    permissions: Optional[List[str]] = Field(default=None, description="Permission list")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str = Field(..., description="Refresh token")


class RegistrationRequest(BaseModel):
    """User registration request (email + password)"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="User password")
    name: Optional[str] = Field(None, description="Display name")


class RegistrationVerifyRequest(BaseModel):
    """Verify registration code"""
    pending_registration_id: str = Field(..., description="Pending registration ID")
    code: str = Field(..., description="Verification code")


# Response Models

class TokenVerificationResponse(BaseModel):
    """Token verification response"""
    valid: bool
    provider: Optional[str] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    subscription_level: Optional[str] = None
    organization_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None


class TokenResponse(BaseModel):
    """Token generation response"""
    success: bool
    token: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    provider: str = "isa_user"
    error: Optional[str] = None


class RegistrationStartResponse(BaseModel):
    """Registration start response"""
    pending_registration_id: str
    verification_required: bool = True
    expires_at: str


class RegistrationVerifyResponse(BaseModel):
    """Registration verification response"""
    success: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_in: Optional[int] = None
    error: Optional[str] = None


class UserInfoResponse(BaseModel):
    """User info extracted from token"""
    user_id: str
    email: str
    organization_id: Optional[str] = None
    permissions: List[str] = []
    provider: str
    expires_at: Optional[datetime] = None


# Export all models
__all__ = [
    'AuthProvider', 'AuthUser', 'AuthSession',
    'TokenVerificationRequest', 'DevTokenRequest', 'TokenPairRequest',
    'RefreshTokenRequest', 'RegistrationRequest', 'RegistrationVerifyRequest',
    'TokenVerificationResponse', 'TokenResponse', 'RegistrationStartResponse',
    'RegistrationVerifyResponse', 'UserInfoResponse'
]
