"""Unit tests for the resilient telemetry WS client SDK helper (#351).

L1 — pure-function and pure-state coverage. No network, no event loop
beyond what asyncio.run already provides for coroutine helpers.
"""

from __future__ import annotations

import json
import math
from typing import Any, List
from unittest.mock import AsyncMock

import pytest

from microservices.telemetry_service.clients.ws_resilient_client import (
    ReplicaEndpoint,
    ResilientTelemetryWebSocket,
    WS_CODE_GOING_AWAY,
    compute_backoff_delay,
    discover_replicas,
)


class TestComputeBackoffDelay:
    """The reconnect schedule is exponential with bounded jitter and a cap."""

    def test_first_attempt_uses_base(self) -> None:
        delay = compute_backoff_delay(0, base_seconds=0.5, max_seconds=30.0, jitter=0)
        assert delay == 0.5

    def test_doubles_each_attempt_below_cap(self) -> None:
        # No jitter — deterministic exponential.
        delays = [
            compute_backoff_delay(i, base_seconds=0.5, max_seconds=30.0, jitter=0)
            for i in range(4)
        ]
        assert delays == [0.5, 1.0, 2.0, 4.0]

    def test_caps_at_max_seconds(self) -> None:
        # 0.5 * 2**10 = 512 — must clamp to 30.
        delay = compute_backoff_delay(10, base_seconds=0.5, max_seconds=30.0, jitter=0)
        assert delay == 30.0

    def test_jitter_stays_within_cap(self) -> None:
        # Even a huge attempt number with jitter must not exceed max_seconds.
        for _ in range(50):
            delay = compute_backoff_delay(
                20, base_seconds=0.5, max_seconds=30.0, jitter=0.5
            )
            assert 0.0 <= delay <= 30.0

    def test_negative_attempt_rejected(self) -> None:
        with pytest.raises(ValueError):
            compute_backoff_delay(-1)

    def test_curve_reaches_cap_within_seven_attempts(self) -> None:
        """Acceptance: 0.5 * 2**6 = 32 > cap, so attempt 6 must be capped."""
        delay = compute_backoff_delay(6, base_seconds=0.5, max_seconds=30.0, jitter=0)
        assert math.isclose(delay, 30.0)


class FakeConsul:
    def __init__(self, instances: List[dict]) -> None:
        self._instances = instances

    def discover_service(self, service_name: str) -> List[dict]:
        return list(self._instances)


class FailingConsul:
    def discover_service(self, service_name: str) -> List[dict]:
        raise RuntimeError("consul down")


class TestDiscoverReplicas:
    def test_returns_consul_endpoints_when_available(self) -> None:
        consul = FakeConsul(
            [
                {"address": "10.0.0.1", "port": 8225},
                {"address": "10.0.0.2", "port": 8225},
            ]
        )
        endpoints = discover_replicas(consul)
        assert endpoints == [
            ReplicaEndpoint(address="10.0.0.1", port=8225, scheme="ws"),
            ReplicaEndpoint(address="10.0.0.2", port=8225, scheme="ws"),
        ]

    def test_falls_back_when_consul_returns_empty(self) -> None:
        fallback = [ReplicaEndpoint(address="telemetry", port=8225)]
        endpoints = discover_replicas(FakeConsul([]), fallback=fallback)
        assert endpoints == fallback

    def test_falls_back_when_consul_raises(self) -> None:
        fallback = [ReplicaEndpoint(address="telemetry", port=8225)]
        endpoints = discover_replicas(FailingConsul(), fallback=fallback)
        assert endpoints == fallback

    def test_no_consul_no_fallback_returns_empty(self) -> None:
        assert discover_replicas(None) == []


class FakeSocket:
    """Minimal duck-typed websocket for the resilient client."""

    def __init__(self, frames: List[str]) -> None:
        self._frames = list(frames)
        self.closed = False

    async def recv(self) -> str:
        if not self._frames:
            raise ConnectionError("socket closed")
        return self._frames.pop(0)

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
class TestResilientWebSocketStream:
    async def test_first_frame_populates_session_id_and_cursor(self) -> None:
        connected_frame = json.dumps(
            {
                "type": "subscription.connected",
                "subscription_id": "sub_abc",
                "session_id": "sub_abc.ws_xyz",
                "cursor": {
                    "subscription_id": "sub_abc",
                    "last_event_at": "2026-05-04T00:00:00+00:00",
                    "sequence_number": 7,
                },
                "retry_after": 5,
            }
        )
        data_frame = json.dumps({"type": "telemetry.data", "value": 21.5})

        sleeps: List[float] = []

        async def fake_sleep(delay: float) -> None:
            sleeps.append(delay)

        sock = FakeSocket([connected_frame, data_frame])
        factory = AsyncMock(return_value=sock)

        client = ResilientTelemetryWebSocket(
            subscription_id="sub_abc",
            connect_token="opaque",
            fallback_replicas=[ReplicaEndpoint(address="t", port=8225)],
            websocket_factory=factory,
            sleeper=fake_sleep,
        )

        async with client:
            received: List[Any] = []
            agen = client.stream()
            received.append(await agen.__anext__())
            received.append(await agen.__anext__())
            await agen.aclose()

        assert received[0]["type"] == "subscription.connected"
        assert client.session_id == "sub_abc.ws_xyz"
        assert client.cursor and client.cursor["sequence_number"] == 7
        assert factory.await_count == 1
        assert sleeps == []  # No reconnects in the happy path.

    async def test_reconnects_via_fallback_when_socket_drops(self) -> None:
        first_connected = json.dumps(
            {
                "type": "subscription.connected",
                "session_id": "first",
                "cursor": {"sequence_number": 1},
                "retry_after": 0,
            }
        )
        second_connected = json.dumps(
            {
                "type": "subscription.connected",
                "session_id": "second",
                "cursor": {"sequence_number": 2},
            }
        )

        # First socket yields one connected frame, then raises (simulating
        # a 1001 going-away). Second socket yields one connected frame.
        sock_a = FakeSocket([first_connected])
        sock_b = FakeSocket([second_connected])
        factory = AsyncMock(side_effect=[sock_a, sock_b])

        sleeps: List[float] = []

        async def fake_sleep(delay: float) -> None:
            sleeps.append(delay)

        client = ResilientTelemetryWebSocket(
            subscription_id="sub_abc",
            connect_token="opaque",
            fallback_replicas=[
                ReplicaEndpoint(address="t1", port=8225),
                ReplicaEndpoint(address="t2", port=8225),
            ],
            websocket_factory=factory,
            sleeper=fake_sleep,
        )

        async with client:
            agen = client.stream()
            first = await agen.__anext__()
            second = await agen.__anext__()
            await agen.aclose()

        assert first["session_id"] == "first"
        assert second["session_id"] == "second"
        assert factory.await_count == 2
        # Exactly one reconnect-induced sleep happened.
        assert len(sleeps) == 1

    async def test_close_is_idempotent_when_no_socket(self) -> None:
        client = ResilientTelemetryWebSocket(
            subscription_id="sub",
            connect_token="t",
            websocket_factory=AsyncMock(),
        )
        # Should not raise even though we never connected.
        await client.close()
        await client.close()


def test_replica_endpoint_url_includes_subscription_and_token() -> None:
    endpoint = ReplicaEndpoint(address="10.0.0.1", port=8225, scheme="wss")
    url = endpoint.url_for("sub_123", "tok-abc")
    assert url == "wss://10.0.0.1:8225/ws/telemetry/sub_123?token=tok-abc"


def test_going_away_constant_matches_rfc_6455() -> None:
    # Sanity check — RFC 6455 §7.4.1 reserves 1001 for endpoint going away.
    assert WS_CODE_GOING_AWAY == 1001
