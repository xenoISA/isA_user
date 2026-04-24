"""Sharing Service data contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ShareCreateRequestContract(BaseModel):
    """Contract for share creation requests."""

    permissions: str = Field(default="view_only")
    expires_in_hours: Optional[int] = Field(None, ge=1, le=8760)


class ShareResponseContract(BaseModel):
    """Contract for share-link responses."""

    id: str
    session_id: str
    owner_id: str
    share_token: str
    share_url: str
    permissions: str
    expires_at: Optional[datetime] = None
    access_count: int = Field(default=0, ge=0)
    created_at: Optional[datetime] = None


class ShareListResponseContract(BaseModel):
    """Contract for share list responses."""

    shares: List[ShareResponseContract]
    total: int = Field(ge=0)


class SharedSessionResponseContract(BaseModel):
    """Contract for public shared-session responses."""

    session_id: str
    session_summary: str = ""
    permissions: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    message_count: int = Field(default=0, ge=0)
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None


class SharingTestDataFactory:
    """Factory helpers for sharing-service tests."""

    @staticmethod
    def make_create_request(**overrides) -> ShareCreateRequestContract:
        payload = {"permissions": "view_only", "expires_in_hours": 24}
        payload.update(overrides)
        return ShareCreateRequestContract(**payload)

    @staticmethod
    def make_share_response(**overrides) -> ShareResponseContract:
        now = datetime.now(timezone.utc)
        payload = {
            "id": f"shr_{uuid4().hex[:24]}",
            "session_id": "sess_shared_001",
            "owner_id": "usr_owner_001",
            "share_token": "share_token_abc123",
            "share_url": "https://app.isa.dev/s/share_token_abc123",
            "permissions": "view_only",
            "expires_at": now + timedelta(hours=24),
            "access_count": 0,
            "created_at": now,
        }
        payload.update(overrides)
        return ShareResponseContract(**payload)
