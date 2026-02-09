"""
Password Utilities for Authentication Service

Provides secure password hashing and verification using bcrypt.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Bcrypt work factor (12 is a good balance of security and performance)
BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hash string
    """
    import bcrypt
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: Plain text password to verify
        password_hash: Bcrypt hash to verify against

    Returns:
        True if password matches, False otherwise
    """
    try:
        import bcrypt
        return bcrypt.checkpw(
            password.encode('utf-8'),
            password_hash.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False


def is_password_strong(password: str, min_length: int = 8) -> tuple[bool, Optional[str]]:
    """
    Check if password meets minimum security requirements.

    Args:
        password: Password to check
        min_length: Minimum required length (default 8)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters"

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)

    if not (has_upper and has_lower and has_digit):
        return False, "Password must contain uppercase, lowercase, and a number"

    return True, None
