"""
Session Service Component Tests — Starred Sessions (#268)

Tests star/unstar business logic with mocked dependencies.
"""

import pytest
from unittest.mock import AsyncMock

from microservices.session_service.session_service import SessionService
from microservices.session_service.models import SessionCreateRequest
from microservices.session_service.protocols import SessionNotFoundError
from tests.component.golden.session_service.mocks import (
    MockSessionRepository,
    MockSessionMessageRepository,
)
from tests.component.mocks.nats_mock import MockEventBus


@pytest.fixture
def session_repo():
    return MockSessionRepository()


@pytest.fixture
def message_repo():
    return MockSessionMessageRepository()


@pytest.fixture
def event_bus():
    return MockEventBus()


@pytest.fixture
def account_client():
    client = AsyncMock()
    client.get_account_profile = AsyncMock(return_value={"user_id": "user1"})
    return client


@pytest.fixture
def service(session_repo, message_repo, event_bus, account_client):
    return SessionService(
        session_repo=session_repo,
        message_repo=message_repo,
        event_bus=event_bus,
        account_client=account_client,
    )


async def _create_session(service, user_id="user1"):
    req = SessionCreateRequest(user_id=user_id)
    resp = await service.create_session(req)
    return resp.session_id


class TestStarSession:
    @pytest.mark.asyncio
    async def test_star_session(self, service, event_bus):
        sid = await _create_session(service)
        resp = await service.star_session(sid, "user1")
        assert resp.is_starred is True
        assert resp.starred_at is not None
        event_bus.assert_event_published("session.starred", {"session_id": sid})

    @pytest.mark.asyncio
    async def test_star_is_idempotent(self, service):
        sid = await _create_session(service)
        await service.star_session(sid, "user1")
        resp = await service.star_session(sid, "user1")
        assert resp.is_starred is True

    @pytest.mark.asyncio
    async def test_star_nonexistent_session(self, service):
        with pytest.raises(SessionNotFoundError):
            await service.star_session("ghost", "user1")

    @pytest.mark.asyncio
    async def test_star_other_users_session(self, service):
        sid = await _create_session(service, "user1")
        with pytest.raises(SessionNotFoundError):
            await service.star_session(sid, "user2")


class TestUnstarSession:
    @pytest.mark.asyncio
    async def test_unstar_session(self, service, event_bus):
        sid = await _create_session(service)
        await service.star_session(sid, "user1")
        event_bus.clear()
        resp = await service.unstar_session(sid, "user1")
        assert resp.is_starred is False
        assert resp.starred_at is None
        event_bus.assert_event_published("session.unstarred", {"session_id": sid})

    @pytest.mark.asyncio
    async def test_unstar_already_unstarred(self, service):
        sid = await _create_session(service)
        resp = await service.unstar_session(sid, "user1")
        assert resp.is_starred is False

    @pytest.mark.asyncio
    async def test_unstar_nonexistent(self, service):
        with pytest.raises(SessionNotFoundError):
            await service.unstar_session("ghost", "user1")


class TestGetStarredSessions:
    @pytest.mark.asyncio
    async def test_get_starred_sessions(self, service):
        s1 = await _create_session(service)
        s2 = await _create_session(service)
        s3 = await _create_session(service)
        await service.star_session(s1, "user1")
        await service.star_session(s3, "user1")
        resp = await service.get_starred_sessions("user1")
        starred_ids = {s.session_id for s in resp.sessions}
        assert s1 in starred_ids
        assert s3 in starred_ids
        assert s2 not in starred_ids
        assert resp.total == 2

    @pytest.mark.asyncio
    async def test_get_starred_sessions_empty(self, service):
        await _create_session(service)
        resp = await service.get_starred_sessions("user1")
        assert resp.total == 0
        assert resp.sessions == []

    @pytest.mark.asyncio
    async def test_starred_sessions_scoped_to_user(self, service, account_client):
        s1 = await _create_session(service, "user1")
        account_client.get_account_profile = AsyncMock(
            return_value={"user_id": "user2"}
        )
        s2 = await _create_session(service, "user2")
        await service.star_session(s1, "user1")
        await service.star_session(s2, "user2")
        resp = await service.get_starred_sessions("user1")
        assert resp.total == 1
        assert resp.sessions[0].session_id == s1
