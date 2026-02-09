"""
Auth Service Fixtures

Factories for auth service test data.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import uuid

from .common import make_user_id, make_device_id, make_org_id, make_email


def make_api_key_id() -> str:
    """Generate a unique API key ID"""
    return f"key_{uuid.uuid4().hex[:12]}"


def make_api_key() -> str:
    """Generate a mock API key"""
    return f"isa_{uuid.uuid4().hex}"


def make_token_verification_request(
    token: str = "mock_jwt_token",
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a token verification request"""
    request = {"token": token}
    if provider:
        request["provider"] = provider
    return request


def make_dev_token_request(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    expires_in: int = 3600,
    subscription_level: str = "free",
    organization_id: Optional[str] = None,
    permissions: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a dev token request"""
    return {
        "user_id": user_id or make_user_id(),
        "email": email or make_email(),
        "expires_in": expires_in,
        "subscription_level": subscription_level,
        "organization_id": organization_id,
        "permissions": permissions,
        "metadata": metadata,
    }


def make_token_pair_request(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    organization_id: Optional[str] = None,
    permissions: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a token pair request"""
    return {
        "user_id": user_id or make_user_id(),
        "email": email or make_email(),
        "organization_id": organization_id,
        "permissions": permissions,
        "metadata": metadata,
    }


def make_refresh_token_request(
    refresh_token: str = "mock_refresh_token",
) -> Dict[str, Any]:
    """Create a refresh token request"""
    return {"refresh_token": refresh_token}


def make_api_key_verification_request(
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an API key verification request"""
    return {"api_key": api_key or make_api_key()}


def make_api_key_create_request(
    organization_id: Optional[str] = None,
    name: str = "Test API Key",
    permissions: Optional[List[str]] = None,
    expires_days: Optional[int] = None,
) -> Dict[str, Any]:
    """Create an API key creation request"""
    return {
        "organization_id": organization_id or make_org_id(),
        "name": name,
        "permissions": permissions or [],
        "expires_days": expires_days,
    }


def make_device_registration_request(
    device_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    device_name: Optional[str] = None,
    device_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    expires_days: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a device registration request"""
    return {
        "device_id": device_id or make_device_id(),
        "organization_id": organization_id or make_org_id(),
        "device_name": device_name or "Test Device",
        "device_type": device_type or "emo_frame",
        "metadata": metadata or {},
        "expires_days": expires_days,
    }


def make_device_auth_request(
    device_id: Optional[str] = None,
    device_secret: str = "mock_device_secret",
) -> Dict[str, Any]:
    """Create a device auth request"""
    return {
        "device_id": device_id or make_device_id(),
        "device_secret": device_secret,
    }


def make_registration_request(
    email: Optional[str] = None,
    password: str = "StrongP@ss123",
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a user registration request"""
    return {
        "email": email or make_email(),
        "password": password,
        "name": name or "Test User",
    }


def make_registration_verify_request(
    pending_registration_id: str = "pending_123",
    code: str = "123456",
) -> Dict[str, Any]:
    """Create a registration verify request"""
    return {
        "pending_registration_id": pending_registration_id,
        "code": code,
    }
