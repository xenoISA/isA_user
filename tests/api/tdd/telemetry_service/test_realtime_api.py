from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient


class FakeRealtimeService:
    def __init__(self) -> None:
        self.connected: list[tuple[str, str]] = []
        self.disconnected: list[tuple[str, str]] = []

    async def subscribe_real_time(self, user_id: str, request: dict) -> dict:
        now = datetime.now(timezone.utc)
        return {
            "subscription_id": "sub_123",
            "message": "Subscription created successfully",
            "websocket_url": "/ws/telemetry/sub_123",
            "connect_token": "connect-token-123",
            "connect_token_expires_at": (now + timedelta(hours=1)).isoformat(),
            "expires_at": (now + timedelta(hours=24)).isoformat(),
        }

    async def unsubscribe_real_time(
        self, subscription_id: str, user_context: dict
    ) -> bool:
        return True

    async def prepare_realtime_websocket(
        self, subscription_id: str, connect_token: str
    ) -> dict:
        assert subscription_id == "sub_123"
        assert connect_token == "connect-token-123"
        return {
            "subscription_id": subscription_id,
            "websocket_id": "ws_123",
            "user_id": "usr_123",
        }

    async def register_realtime_websocket(
        self, subscription_id: str, websocket_id: str, websocket
    ) -> None:
        self.connected.append((subscription_id, websocket_id))

    async def unregister_realtime_websocket(
        self, subscription_id: str, websocket_id: str
    ) -> None:
        self.disconnected.append((subscription_id, websocket_id))


@pytest.fixture
def realtime_client():
    import microservices.telemetry_service.main as telemetry_main

    fake_service = FakeRealtimeService()

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    orig_lifespan = telemetry_main.app.router.lifespan_context
    orig_service = telemetry_main.microservice.service
    telemetry_main.app.router.lifespan_context = noop_lifespan
    telemetry_main.microservice.service = fake_service
    telemetry_main.app.dependency_overrides[telemetry_main.get_user_context] = lambda: {
        "user_id": "usr_123",
        "organization_id": None,
        "role": "user",
    }

    with TestClient(telemetry_main.app, raise_server_exceptions=False) as client:
        yield client, fake_service

    telemetry_main.app.router.lifespan_context = orig_lifespan
    telemetry_main.microservice.service = orig_service
    telemetry_main.app.dependency_overrides.clear()


def test_subscribe_returns_connect_token_and_expiry(realtime_client):
    client, _fake_service = realtime_client

    response = client.post(
        "/api/v1/telemetry/subscribe",
        json={"device_ids": ["dev_123"], "metric_names": ["temperature"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["subscription_id"] == "sub_123"
    assert body["connect_token"] == "connect-token-123"
    assert body["websocket_url"] == "/ws/telemetry/sub_123"
    assert "connect_token_expires_at" in body


def test_websocket_connect_sends_connection_ack(realtime_client):
    client, fake_service = realtime_client

    with client.websocket_connect(
        "/ws/telemetry/sub_123?token=connect-token-123"
    ) as ws:
        payload = ws.receive_json()

    assert payload["type"] == "subscription.connected"
    assert payload["subscription_id"] == "sub_123"
    assert "real-time data would be sent here" not in json.dumps(payload)
    assert fake_service.connected == [("sub_123", "ws_123")]
