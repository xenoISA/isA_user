"""
Test Object Factories

Factory functions for creating test objects.
Use these instead of hardcoding test data.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any


def make_user_id() -> str:
    """Generate a unique user ID"""
    return f"usr_test_{uuid.uuid4().hex[:12]}"


def make_device_id() -> str:
    """Generate a unique device ID"""
    return f"dev_test_{uuid.uuid4().hex[:12]}"


def make_org_id() -> str:
    """Generate a unique organization ID"""
    return f"org_test_{uuid.uuid4().hex[:12]}"


def make_email(prefix: Optional[str] = None) -> str:
    """Generate a unique email"""
    prefix = prefix or f"test_{uuid.uuid4().hex[:8]}"
    return f"{prefix}@example.com"


def make_user(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    name: str = "Test User",
    is_active: bool = True,
    preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a user dict for testing"""
    return {
        "user_id": user_id or make_user_id(),
        "email": email or make_email(),
        "name": name,
        "is_active": is_active,
        "preferences": preferences or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def make_account_ensure_request(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    name: str = "Test User",
) -> Dict[str, Any]:
    """Create an account ensure request"""
    return {
        "user_id": user_id or make_user_id(),
        "email": email or make_email(),
        "name": name,
    }


def make_album_id() -> str:
    """Generate a unique album ID"""
    return f"album_test_{uuid.uuid4().hex[:12]}"


def make_album(
    album_id: Optional[str] = None,
    name: str = "Test Album",
    user_id: Optional[str] = None,
    description: Optional[str] = None,
    auto_sync: bool = True,
    is_family_shared: bool = False,
    tags: Optional[list] = None,
) -> Dict[str, Any]:
    """Create an album dict for testing"""
    return {
        "album_id": album_id or make_album_id(),
        "name": name,
        "user_id": user_id or make_user_id(),
        "description": description,
        "auto_sync": auto_sync,
        "is_family_shared": is_family_shared,
        "tags": tags or [],
        "photo_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def make_album_create_request(
    name: Optional[str] = None,
    description: Optional[str] = None,
    auto_sync: bool = True,
    is_family_shared: bool = False,
    tags: Optional[list] = None,
) -> Dict[str, Any]:
    """Create an album creation request"""
    return {
        "name": name or f"Test Album {uuid.uuid4().hex[:8]}",
        "description": description,
        "auto_sync": auto_sync,
        "is_family_shared": is_family_shared,
        "tags": tags or [],
    }
