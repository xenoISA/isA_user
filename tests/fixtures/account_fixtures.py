"""
Account Service Fixtures

Factories for account service test data.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .common import make_user_id, make_email


def make_account(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    name: str = "Test User",
    is_active: bool = True,
    preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create an account dict for testing"""
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


def make_account_update_request(
    name: Optional[str] = None,
    phone: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an account update request (partial)"""
    request = {}
    if name is not None:
        request["name"] = name
    if phone is not None:
        request["phone"] = phone
    if avatar_url is not None:
        request["avatar_url"] = avatar_url
    return request


def make_preferences_update(
    language: Optional[str] = None,
    theme: Optional[str] = None,
    timezone: Optional[str] = None,
    notifications_enabled: Optional[bool] = None,
) -> Dict[str, Any]:
    """Create a preferences update request"""
    prefs = {}
    if language is not None:
        prefs["language"] = language
    if theme is not None:
        prefs["theme"] = theme
    if timezone is not None:
        prefs["timezone"] = timezone
    if notifications_enabled is not None:
        prefs["notifications_enabled"] = notifications_enabled
    return prefs
