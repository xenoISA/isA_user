"""
L4 API — sharing_service route aliases and public snapshot contract.
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, PROJECT_ROOT)

from microservices.sharing_service import main as sharing_main
from microservices.sharing_service.models import ShareResponse, SharedSessionResponse


class FakeSharingService:
    def __init__(self):
        self.create_share = AsyncMock(
            return_value=ShareResponse(
                id="share-1",
                session_id="sess-1",
                owner_id="user-1",
                share_token="token-1",
                share_url="https://app.isa.dev/s/token-1",
                permissions="view_only",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        )
        self.access_share = AsyncMock(
            return_value=SharedSessionResponse(
                session_id="sess-1",
                session_summary="Frozen summary",
                permissions="view_only",
                messages=[{"id": "msg-1", "role": "user", "content": "hello"}],
                message_count=1,
            )
        )
        self.revoke_session_share = AsyncMock(return_value=True)


def test_singular_create_share_route_alias_uses_owner_query():
    service = FakeSharingService()
    sharing_main.app.dependency_overrides[sharing_main.get_sharing_service] = lambda: service

    try:
        client = TestClient(sharing_main.app)
        response = client.post(
            "/api/v1/sessions/sess-1/share?user_id=user-1",
            json={"permissions": "view_only", "share_until_message_id": "msg-1"},
        )
    finally:
        sharing_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["share_token"] == "token-1"
    service.create_share.assert_awaited_once()
    session_id, owner_id, request = service.create_share.await_args.args
    assert session_id == "sess-1"
    assert owner_id == "user-1"
    assert request.share_until_message_id == "msg-1"


def test_public_shared_route_alias_returns_read_only_snapshot():
    service = FakeSharingService()
    sharing_main.app.dependency_overrides[sharing_main.get_sharing_service] = lambda: service

    try:
        client = TestClient(sharing_main.app)
        response = client.get("/api/v1/shared/token-1")
    finally:
        sharing_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["session_summary"] == "Frozen summary"
    assert response.json()["messages"] == [
        {"id": "msg-1", "role": "user", "content": "hello"}
    ]
    service.access_share.assert_awaited_once_with("token-1")


def test_session_scoped_revoke_route_requires_token_and_owner():
    service = FakeSharingService()
    sharing_main.app.dependency_overrides[sharing_main.get_sharing_service] = lambda: service

    try:
        client = TestClient(sharing_main.app)
        response = client.delete(
            "/api/v1/sessions/sess-1/share?share_token=token-1&user_id=user-1"
        )
    finally:
        sharing_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["message"] == "Share link revoked successfully"
    service.revoke_session_share.assert_awaited_once_with(
        "sess-1", "token-1", "user-1"
    )
