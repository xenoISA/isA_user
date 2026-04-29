from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from core.nats_client import Event
from microservices.telemetry_service.models import TelemetryDataPoint
from microservices.telemetry_service.realtime import RealtimeAuthenticationError
from microservices.telemetry_service.telemetry_service import TelemetryService

pytestmark = [pytest.mark.component, pytest.mark.asyncio]


class FakeEventBus:
    def __init__(self) -> None:
        self.published: list[dict] = []

    async def publish_event(self, event, subject=None, metadata=None) -> bool:
        self.published.append(
            {"event": event, "subject": subject, "metadata": metadata}
        )
        return True


class FakeWebSocket:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.messages.append(payload)


@pytest.fixture
def service_with_repo():
    repo = AsyncMock()
    event_bus = FakeEventBus()

    with patch(
        "microservices.telemetry_service.telemetry_service.TelemetryRepository",
        return_value=repo,
    ):
        service = TelemetryService(event_bus=event_bus)

    service.repository = repo
    return service, repo, event_bus


async def test_subscribe_real_time_persists_subscription_and_returns_connect_token(
    service_with_repo,
):
    service, repo, _event_bus = service_with_repo
    now = datetime.now(timezone.utc)
    repo.create_real_time_subscription = AsyncMock(
        return_value={
            "subscription_id": "sub_123",
            "created_at": now,
            "expires_at": now + timedelta(hours=24),
            "metadata": {
                "connect_token_expires_at": (now + timedelta(hours=1)).isoformat()
            },
        }
    )

    result = await service.subscribe_real_time(
        "usr_123",
        {
            "device_ids": ["dev_123"],
            "metric_names": ["temperature"],
            "tags": {"site": "lab"},
            "max_frequency": 500,
        },
    )

    assert result["subscription_id"] == "sub_123"
    assert result["websocket_url"] == "/ws/telemetry/sub_123"
    assert result["connect_token"]
    repo.create_real_time_subscription.assert_awaited_once()


async def test_notify_real_time_subscribers_publishes_realtime_delivery_event(
    service_with_repo,
):
    service, repo, event_bus = service_with_repo
    repo.list_matching_real_time_subscriptions = AsyncMock(
        return_value=[
            {
                "subscription_id": "sub_123",
                "websocket_id": "ws_123",
                "device_ids": ["dev_123"],
                "metric_names": ["temperature"],
                "tags": {"site": "lab"},
                "max_frequency": 500,
            }
        ]
    )

    data_point = TelemetryDataPoint(
        timestamp=datetime.now(timezone.utc),
        metric_name="temperature",
        value=21.5,
        unit="C",
        tags={"site": "lab"},
    )

    await service._notify_real_time_subscribers("dev_123", data_point)

    assert len(event_bus.published) == 1
    assert event_bus.published[0]["subject"] == "telemetry.realtime.deliver"


async def test_handle_realtime_delivery_event_sends_payload_to_bound_socket(
    service_with_repo,
):
    service, repo, _event_bus = service_with_repo
    socket = FakeWebSocket()
    service.realtime_connections = {"sub_123": socket}
    service.realtime_connection_ids = {"sub_123": "ws_123"}
    repo.record_real_time_delivery = AsyncMock(return_value=True)

    event = Event(
        event_type="telemetry.realtime.delivery",
        source="telemetry_service",
        data={
            "subscription_id": "sub_123",
            "websocket_id": "ws_123",
            "device_id": "dev_123",
            "data_points": [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metric_name": "temperature",
                    "value": 21.5,
                    "unit": "C",
                    "tags": {"site": "lab"},
                    "metadata": {},
                }
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequence_number": 42,
        },
    )

    handled = await service.handle_realtime_delivery_event(event)

    assert handled is True
    assert socket.messages[0]["subscription_id"] == "sub_123"
    repo.record_real_time_delivery.assert_awaited_once_with("sub_123", "ws_123")


async def test_prepare_realtime_websocket_rejects_invalid_connect_token(
    service_with_repo,
):
    service, repo, _event_bus = service_with_repo
    now = datetime.now(timezone.utc)
    repo.get_real_time_subscription = AsyncMock(
        return_value={
            "subscription_id": "sub_123",
            "user_id": "usr_123",
            "active": True,
            "expires_at": now + timedelta(hours=24),
            "metadata": {
                "connect_token_hash": "expected-hash",
                "connect_token_expires_at": (now + timedelta(hours=1)).isoformat(),
            },
        }
    )

    with pytest.raises(RealtimeAuthenticationError):
        await service.prepare_realtime_websocket("sub_123", "wrong-token")
