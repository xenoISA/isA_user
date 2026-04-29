from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any


class RealtimeError(Exception):
    """Base realtime streaming error."""


class RealtimeUnavailableError(RealtimeError):
    """Realtime delivery cannot be used in the current runtime."""


class RealtimeAuthenticationError(RealtimeError):
    """Websocket connection token is invalid or expired."""


class RealtimeSubscriptionNotFoundError(RealtimeError):
    """Subscription does not exist or is no longer active."""


class RealtimeUnsupportedFilterError(RealtimeError):
    """A requested filter cannot be enforced safely."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_connect_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_connect_token(token: str, expected_hash: str | None) -> bool:
    if not token or not expected_hash:
        return False
    token_hash = hash_connect_token(token)
    return hmac.compare_digest(token_hash, expected_hash)


def parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    raise TypeError(f"Unsupported datetime value: {value!r}")


def subscription_matches_tags(
    requested_tags: dict[str, str] | None, data_point_tags: dict[str, str] | None
) -> bool:
    if not requested_tags:
        return True
    if not data_point_tags:
        return False
    for key, expected_value in requested_tags.items():
        if data_point_tags.get(key) != expected_value:
            return False
    return True
