"""Component tests for WebSocket affinity + replica handoff (#351).

L2 — service-level coverage with mocked repository. Validates that:

1. `prepare_realtime_websocket` returns a session_id + cursor that lets a
   different replica resume the subscription from the prior cursor.
2. `drain_realtime_websockets` closes every live socket with code 1001
   (going away) and a `Retry-After` hint encoded in the close reason.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple
from unittest.mock import AsyncMock, patch

import pytest

from microservices.telemetry_service.realtime import hash_connect_token
from microservices.telemetry_service.telemetry_service import TelemetryService

pytestmark = [pytest.mark.component, pytest.mark.asyncio]


class FakeWebSocket:
    """Captures send_json + close calls for assertions."""

    def __init__(self) -> None:
        self.messages: List[Dict[str, Any]] = []
        self.closed_with: Tuple[int, str] | None = None
        self._closed = False

    async def send_json(self, payload: Dict[str, Any]) -> None:
        self.messages.append(payload)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed_with = (code, reason)
        self._closed = True


@pytest.fixture
def service():
    repo = AsyncMock()
    with patch(
        "microservices.telemetry_service.telemetry_service.TelemetryRepository",
        return_value=repo,
    ):
        svc = TelemetryService(event_bus=None)
    svc.repository = repo
    return svc, repo


async def test_prepare_websocket_returns_cursor_for_replica_handoff(service) -> None:
    """A new connection — even on a different replica — must be given the
    cursor of the prior connection so it can resume without dropping data."""
    svc, repo = service
    now = datetime.now(timezone.utc)
    last_delivery = now - timedelta(seconds=2)
    token = "opaque-connect-token"

    # Simulate the durable subscription state that survives replica handoff.
    repo.get_real_time_subscription = AsyncMock(
        return_value={
            "subscription_id": "sub_123",
            "user_id": "usr_1",
            "active": True,
            "expires_at": now + timedelta(hours=24),
            "last_sent": last_delivery,
            "metadata": {
                "connect_token_hash": hash_connect_token(token),
                "connect_token_expires_at": (now + timedelta(hours=1)).isoformat(),
                "last_delivery_at": last_delivery.isoformat(),
                "last_sequence_number": 42,
            },
        }
    )
    repo.bind_real_time_subscription_connection = AsyncMock(
        return_value={"subscription_id": "sub_123"}
    )

    session = await svc.prepare_realtime_websocket("sub_123", token)

    # Affinity ID must be stable + opaque so the LB can route on it.
    assert session["session_id"].startswith("sub_123.")
    assert session["session_id"] == f"sub_123.{session['websocket_id']}"
    # The cursor lets a different replica resume from where the prior left off.
    assert session["cursor"]["subscription_id"] == "sub_123"
    assert session["cursor"]["sequence_number"] == 42
    assert session["cursor"]["last_event_at"] == last_delivery.isoformat()


async def test_prepare_websocket_handoff_uses_subscription_id_only(service) -> None:
    """The cursor reconstruction must depend solely on `subscription_id` —
    no replica-local state — so handoff to a fresh replica works."""
    svc, repo = service
    now = datetime.now(timezone.utc)
    token = "tok"

    # Simulate a brand-new replica: zero local connection state.
    svc.realtime_connections = {}
    svc.realtime_connection_ids = {}

    last_delivery = now - timedelta(seconds=1)
    repo.get_real_time_subscription = AsyncMock(
        return_value={
            "subscription_id": "sub_xyz",
            "user_id": "u",
            "active": True,
            "expires_at": now + timedelta(hours=1),
            "last_sent": last_delivery,
            "metadata": {
                "connect_token_hash": hash_connect_token(token),
                "connect_token_expires_at": (now + timedelta(hours=1)).isoformat(),
                "last_delivery_at": last_delivery.isoformat(),
                "last_sequence_number": 99,
            },
        }
    )
    repo.bind_real_time_subscription_connection = AsyncMock(
        return_value={"subscription_id": "sub_xyz"}
    )

    session = await svc.prepare_realtime_websocket("sub_xyz", token)

    assert session["cursor"]["sequence_number"] == 99
    assert session["cursor"]["last_event_at"] == last_delivery.isoformat()


async def test_drain_realtime_websockets_closes_with_going_away(service) -> None:
    """Graceful drain must close every live socket with code 1001 and
    include a `Retry-After` hint in the close reason."""
    svc, repo = service
    repo.clear_real_time_subscription_connection = AsyncMock(return_value=True)

    sock_a = FakeWebSocket()
    sock_b = FakeWebSocket()
    svc.realtime_connections = {"sub_a": sock_a, "sub_b": sock_b}
    svc.realtime_connection_ids = {"sub_a": "ws_a", "sub_b": "ws_b"}
    svc.realtime_heartbeat_tasks = {}

    drained = await svc.drain_realtime_websockets(
        retry_after_seconds=7, close_code=1001
    )

    assert drained == 2
    for sock in (sock_a, sock_b):
        assert sock.closed_with is not None
        code, reason = sock.closed_with
        assert code == 1001
        assert "retry-after=7" in reason

    # After drain, the live-connection registries must be empty so a new
    # incoming connection cannot accidentally collide with a stale entry.
    assert svc.realtime_connections == {}
    assert svc.realtime_connection_ids == {}


async def test_drain_no_connections_is_noop(service) -> None:
    svc, _ = service
    svc.realtime_connections = {}
    svc.realtime_connection_ids = {}
    drained = await svc.drain_realtime_websockets()
    assert drained == 0
