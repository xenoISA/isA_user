"""L1 Unit — Sharing service Pydantic models"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from microservices.sharing_service.models import (
    Share,
    ShareCreateRequest,
    ShareListResponse,
    SharePermission,
    ShareResponse,
    SharedSessionResponse,
    ShareCreatedEventData,
    ShareAccessedEventData,
    ShareRevokedEventData,
)

pytestmark = pytest.mark.unit


class TestSharePermission:
    def test_enum_values(self):
        assert SharePermission.VIEW_ONLY == "view_only"
        assert SharePermission.CAN_COMMENT == "can_comment"
        assert SharePermission.CAN_EDIT == "can_edit"

    def test_enum_membership(self):
        assert len(SharePermission) == 3


class TestShareCreateRequest:
    def test_defaults(self):
        req = ShareCreateRequest()
        assert req.permissions == SharePermission.VIEW_ONLY
        assert req.expires_in_hours is None

    def test_custom_permissions(self):
        req = ShareCreateRequest(permissions=SharePermission.CAN_EDIT)
        assert req.permissions == SharePermission.CAN_EDIT

    def test_valid_expiry(self):
        req = ShareCreateRequest(expires_in_hours=24)
        assert req.expires_in_hours == 24

    def test_expiry_min_bound(self):
        with pytest.raises(ValidationError):
            ShareCreateRequest(expires_in_hours=0)

    def test_expiry_max_bound(self):
        with pytest.raises(ValidationError):
            ShareCreateRequest(expires_in_hours=8761)

    def test_expiry_at_max(self):
        req = ShareCreateRequest(expires_in_hours=8760)
        assert req.expires_in_hours == 8760


class TestShare:
    def test_valid_share(self):
        share = Share(
            id="share-1",
            session_id="sess-1",
            owner_id="user-1",
            share_token="abc123token",
        )
        assert share.permissions == SharePermission.VIEW_ONLY
        assert share.access_count == 0
        assert share.expires_at is None

    def test_share_from_attributes(self):
        data = {
            "id": "share-1",
            "session_id": "sess-1",
            "owner_id": "user-1",
            "share_token": "abc",
            "permissions": "can_comment",
            "access_count": 5,
            "created_at": datetime(2026, 1, 1),
        }
        share = Share.model_validate(data)
        assert share.permissions == "can_comment"
        assert share.access_count == 5


class TestShareResponse:
    def test_includes_share_url(self):
        resp = ShareResponse(
            id="s1",
            session_id="sess-1",
            owner_id="user-1",
            share_token="tok",
            share_url="https://app.isa.dev/s/tok",
            permissions="view_only",
        )
        assert resp.share_url == "https://app.isa.dev/s/tok"
        assert resp.access_count == 0


class TestSharedSessionResponse:
    def test_defaults(self):
        resp = SharedSessionResponse(session_id="sess-1", permissions="view_only")
        assert resp.messages == []
        assert resp.message_count == 0
        assert resp.permissions == "view_only"

    def test_with_messages(self):
        resp = SharedSessionResponse(
            session_id="sess-1",
            permissions="view_only",
            messages=[{"role": "user", "content": "hello"}],
            message_count=1,
        )
        assert len(resp.messages) == 1


class TestShareListResponse:
    def test_empty_list(self):
        resp = ShareListResponse(shares=[], total=0)
        assert resp.total == 0

    def test_with_shares(self):
        share = ShareResponse(
            id="s1",
            session_id="sess-1",
            owner_id="user-1",
            share_token="tok",
            share_url="https://app.isa.dev/s/tok",
            permissions="view_only",
        )
        resp = ShareListResponse(shares=[share], total=1)
        assert resp.total == 1


class TestEventDataModels:
    def test_share_created_event(self):
        event = ShareCreatedEventData(
            share_id="s1",
            session_id="sess-1",
            owner_id="user-1",
            share_token="tok",
            permissions="view_only",
            timestamp="2026-01-01T00:00:00Z",
        )
        assert event.expires_at is None

    def test_share_accessed_event(self):
        event = ShareAccessedEventData(
            share_id="s1",
            session_id="sess-1",
            share_token="tok",
            access_count=3,
            timestamp="2026-01-01T00:00:00Z",
        )
        assert event.access_count == 3

    def test_share_revoked_event(self):
        event = ShareRevokedEventData(
            share_id="s1",
            session_id="sess-1",
            owner_id="user-1",
            share_token="tok",
            timestamp="2026-01-01T00:00:00Z",
        )
        assert event.owner_id == "user-1"
