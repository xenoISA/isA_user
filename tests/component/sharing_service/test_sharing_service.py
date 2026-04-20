"""
L2 Component — Sharing service business logic with mocked dependencies.

Tests SharingService methods with mocked ShareRepository, EventBus,
and SessionClient.
"""

import os
import sys
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, PROJECT_ROOT)

from microservices.sharing_service.models import (
    Share,
    ShareCreateRequest,
    SharePermission,
)
from microservices.sharing_service.protocols import (
    ShareExpiredError,
    ShareNotFoundError,
    SharePermissionError,
    ShareValidationError,
)
from microservices.sharing_service.factory import create_sharing_service_for_testing

pytestmark = pytest.mark.component


# ============================================================================
# Fixtures
# ============================================================================


def _make_share(
    share_id="share-1",
    session_id="sess-1",
    owner_id="user-1",
    share_token="test-token-abc",
    permissions="view_only",
    expires_at=None,
    access_count=0,
):
    return Share(
        id=share_id,
        session_id=session_id,
        owner_id=owner_id,
        share_token=share_token,
        permissions=permissions,
        expires_at=expires_at,
        access_count=access_count,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def mock_share_repo():
    repo = AsyncMock()
    repo.create_share = AsyncMock(return_value=_make_share())
    repo.get_by_token = AsyncMock(return_value=_make_share())
    repo.get_by_id = AsyncMock(return_value=_make_share())
    repo.get_session_shares = AsyncMock(return_value=[_make_share()])
    repo.delete_by_token = AsyncMock(return_value=True)
    repo.increment_access_count = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def mock_event_bus():
    bus = AsyncMock()
    bus.publish_event = AsyncMock()
    return bus


@pytest.fixture
def mock_session_client():
    client = AsyncMock()
    client.get_session = AsyncMock(
        return_value={
            "session_id": "sess-1",
            "user_id": "user-1",
            "status": "active",
            "session_summary": "Test session",
            "created_at": "2026-01-01T00:00:00Z",
            "last_activity": "2026-01-01T00:00:00Z",
        }
    )
    client.get_session_messages = AsyncMock(
        return_value=[
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
    )
    return client


@pytest.fixture
def sharing_service(mock_share_repo, mock_event_bus, mock_session_client):
    return create_sharing_service_for_testing(
        share_repo=mock_share_repo,
        event_bus=mock_event_bus,
        session_client=mock_session_client,
    )


# ============================================================================
# create_share
# ============================================================================


class TestCreateShare:
    @pytest.mark.asyncio
    async def test_create_share_success(self, sharing_service, mock_share_repo):
        request = ShareCreateRequest()
        result = await sharing_service.create_share("sess-1", "user-1", request)

        assert result.session_id == "sess-1"
        assert result.share_token == "test-token-abc"
        assert "isa.dev" in result.share_url
        mock_share_repo.create_share.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_share_with_expiry(self, sharing_service, mock_share_repo):
        request = ShareCreateRequest(expires_in_hours=24)
        result = await sharing_service.create_share("sess-1", "user-1", request)

        call_args = mock_share_repo.create_share.call_args[0][0]
        assert call_args["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_create_share_with_permissions(self, sharing_service, mock_share_repo):
        request = ShareCreateRequest(permissions=SharePermission.CAN_EDIT)
        result = await sharing_service.create_share("sess-1", "user-1", request)

        call_args = mock_share_repo.create_share.call_args[0][0]
        assert call_args["permissions"] == "can_edit"

    @pytest.mark.asyncio
    async def test_create_share_session_not_found(
        self, sharing_service, mock_session_client
    ):
        mock_session_client.get_session.return_value = None
        request = ShareCreateRequest()

        with pytest.raises(ShareValidationError, match="Session not found"):
            await sharing_service.create_share("bad-sess", "user-1", request)

    @pytest.mark.asyncio
    async def test_create_share_not_owner(
        self, sharing_service, mock_session_client
    ):
        mock_session_client.get_session.return_value = {
            "session_id": "sess-1",
            "user_id": "other-user",
        }
        request = ShareCreateRequest()

        with pytest.raises(SharePermissionError, match="only share your own"):
            await sharing_service.create_share("sess-1", "user-1", request)

    @pytest.mark.asyncio
    async def test_create_share_publishes_event(
        self, sharing_service, mock_event_bus
    ):
        request = ShareCreateRequest()
        await sharing_service.create_share("sess-1", "user-1", request)

        mock_event_bus.publish_event.assert_called_once()
        event = mock_event_bus.publish_event.call_args[0][0]
        assert event.type == "share.created"

    @pytest.mark.asyncio
    async def test_create_share_repo_failure(
        self, sharing_service, mock_share_repo
    ):
        mock_share_repo.create_share.return_value = None

        request = ShareCreateRequest()
        with pytest.raises(Exception):
            await sharing_service.create_share("sess-1", "user-1", request)


# ============================================================================
# access_share
# ============================================================================


class TestAccessShare:
    @pytest.mark.asyncio
    async def test_access_share_success(self, sharing_service):
        result = await sharing_service.access_share("test-token-abc")

        assert result.session_id == "sess-1"
        assert result.permissions == "view_only"
        assert result.message_count == 2

    @pytest.mark.asyncio
    async def test_access_share_increments_count(
        self, sharing_service, mock_share_repo
    ):
        await sharing_service.access_share("test-token-abc")
        mock_share_repo.increment_access_count.assert_called_once_with("share-1")

    @pytest.mark.asyncio
    async def test_access_share_not_found(
        self, sharing_service, mock_share_repo
    ):
        mock_share_repo.get_by_token.return_value = None

        with pytest.raises(ShareNotFoundError):
            await sharing_service.access_share("bad-token")

    @pytest.mark.asyncio
    async def test_access_share_expired(
        self, sharing_service, mock_share_repo
    ):
        expired_share = _make_share(
            expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc)
        )
        mock_share_repo.get_by_token.return_value = expired_share

        with pytest.raises(ShareExpiredError):
            await sharing_service.access_share("test-token-abc")

    @pytest.mark.asyncio
    async def test_access_share_not_expired(
        self, sharing_service, mock_share_repo
    ):
        future = datetime.now(timezone.utc) + timedelta(hours=24)
        valid_share = _make_share(expires_at=future)
        mock_share_repo.get_by_token.return_value = valid_share

        result = await sharing_service.access_share("test-token-abc")
        assert result.session_id == "sess-1"

    @pytest.mark.asyncio
    async def test_access_share_publishes_event(
        self, sharing_service, mock_event_bus
    ):
        await sharing_service.access_share("test-token-abc")

        mock_event_bus.publish_event.assert_called_once()
        event = mock_event_bus.publish_event.call_args[0][0]
        assert event.type == "share.accessed"

    @pytest.mark.asyncio
    async def test_access_share_session_deleted(
        self, sharing_service, mock_session_client
    ):
        mock_session_client.get_session.return_value = None

        with pytest.raises(Exception, match="no longer exists"):
            await sharing_service.access_share("test-token-abc")


# ============================================================================
# revoke_share
# ============================================================================


class TestRevokeShare:
    @pytest.mark.asyncio
    async def test_revoke_share_success(self, sharing_service, mock_share_repo):
        result = await sharing_service.revoke_share("test-token-abc", "user-1")
        assert result is True
        mock_share_repo.delete_by_token.assert_called_once_with("test-token-abc")

    @pytest.mark.asyncio
    async def test_revoke_share_not_found(
        self, sharing_service, mock_share_repo
    ):
        mock_share_repo.get_by_token.return_value = None

        with pytest.raises(ShareNotFoundError):
            await sharing_service.revoke_share("bad-token", "user-1")

    @pytest.mark.asyncio
    async def test_revoke_share_not_owner(self, sharing_service):
        with pytest.raises(SharePermissionError, match="owner"):
            await sharing_service.revoke_share("test-token-abc", "other-user")

    @pytest.mark.asyncio
    async def test_revoke_share_publishes_event(
        self, sharing_service, mock_event_bus
    ):
        await sharing_service.revoke_share("test-token-abc", "user-1")

        mock_event_bus.publish_event.assert_called_once()
        event = mock_event_bus.publish_event.call_args[0][0]
        assert event.type == "share.revoked"


# ============================================================================
# list_session_shares
# ============================================================================


class TestListSessionShares:
    @pytest.mark.asyncio
    async def test_list_shares_success(self, sharing_service):
        result = await sharing_service.list_session_shares("sess-1", "user-1")

        assert result.total == 1
        assert len(result.shares) == 1
        assert result.shares[0].share_token == "test-token-abc"

    @pytest.mark.asyncio
    async def test_list_shares_session_not_found(
        self, sharing_service, mock_session_client
    ):
        mock_session_client.get_session.return_value = None

        with pytest.raises(ShareValidationError, match="Session not found"):
            await sharing_service.list_session_shares("bad-sess", "user-1")

    @pytest.mark.asyncio
    async def test_list_shares_not_owner(
        self, sharing_service, mock_session_client
    ):
        mock_session_client.get_session.return_value = {
            "session_id": "sess-1",
            "user_id": "other-user",
        }

        with pytest.raises(SharePermissionError):
            await sharing_service.list_session_shares("sess-1", "user-1")

    @pytest.mark.asyncio
    async def test_list_shares_empty(
        self, sharing_service, mock_share_repo
    ):
        mock_share_repo.get_session_shares.return_value = []
        result = await sharing_service.list_session_shares("sess-1", "user-1")
        assert result.total == 0
        assert result.shares == []
