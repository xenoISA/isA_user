"""
Common/Shared Fixtures

Base factories and generators used across multiple services.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional


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


def make_timestamp() -> str:
    """Generate current UTC timestamp"""
    return datetime.now(timezone.utc).isoformat()
