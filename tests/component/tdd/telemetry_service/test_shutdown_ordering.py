"""Component test for the telemetry_service graceful shutdown ordering (#351).

Regression: in the original PR the lifespan called `drain_realtime_websockets()`
BEFORE `microservice.shutdown()`, which is the call that deregisters the pod
from Consul. Result: drained clients reconnect through stale Consul SRV and
can land back on the dying pod.

This test asserts the corrected ordering — Consul deregister MUST happen
before WebSocket drain.
"""

from __future__ import annotations

from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest


pytestmark = [pytest.mark.component, pytest.mark.asyncio]


async def test_shutdown_deregisters_consul_before_draining_websockets() -> None:
    """The lifespan teardown must call `microservice.shutdown()` (which
    deregisters from Consul) BEFORE `drain_realtime_websockets`. Otherwise
    drained clients reconnect via stale Consul SRV and bounce back to the
    dying pod."""
    from microservices.telemetry_service import main as telemetry_main

    call_log: List[str] = []

    # Stub the GracefulShutdown surface so we don't install signal handlers.
    fake_shutdown_manager = MagicMock()

    async def _wait_for_drain() -> None:
        call_log.append("wait_for_drain")

    fake_shutdown_manager.wait_for_drain = _wait_for_drain
    fake_shutdown_manager.initiate_shutdown = MagicMock(
        side_effect=lambda: call_log.append("initiate_shutdown")
    )
    fake_shutdown_manager.install_signal_handlers = MagicMock()

    # Stub the microservice instance: shutdown() represents Consul deregister.
    fake_microservice = MagicMock()
    fake_microservice.service = MagicMock()
    fake_microservice.service.instance_id = "test-instance"

    async def _shutdown() -> None:
        call_log.append("microservice_shutdown_consul_deregister")

    async def _initialize(event_bus: Any = None) -> None:
        call_log.append("microservice_initialize")

    async def _drain(retry_after_seconds: int = 5, close_code: int = 1001) -> int:
        call_log.append("drain_realtime_websockets")
        return 0

    fake_microservice.shutdown = _shutdown
    fake_microservice.initialize = _initialize
    fake_microservice.service.drain_realtime_websockets = _drain

    # Stub get_event_bus to return None (event bus optional in tests).
    async def _no_event_bus(_name: str) -> None:
        return None

    with patch.object(
        telemetry_main, "shutdown_manager", fake_shutdown_manager
    ), patch.object(telemetry_main, "microservice", fake_microservice), patch.object(
        telemetry_main, "get_event_bus", _no_event_bus
    ):
        # Build a fake FastAPI-shaped app to satisfy the lifespan contextmanager.
        app = MagicMock()

        async with telemetry_main.lifespan(app):
            pass  # exiting triggers shutdown branch

    # --- Assertions ---
    # Consul deregister must precede WS drain.
    assert "microservice_shutdown_consul_deregister" in call_log
    assert "drain_realtime_websockets" in call_log
    deregister_idx = call_log.index("microservice_shutdown_consul_deregister")
    drain_idx = call_log.index("drain_realtime_websockets")
    assert deregister_idx < drain_idx, (
        f"Shutdown order wrong — Consul deregister ({deregister_idx}) must "
        f"come before WS drain ({drain_idx}). Full log: {call_log}"
    )

    # initiate_shutdown must be the very first teardown action.
    assert call_log[0] == "microservice_initialize"
    assert "initiate_shutdown" in call_log
    initiate_idx = call_log.index("initiate_shutdown")
    assert initiate_idx < deregister_idx
    assert initiate_idx < drain_idx

    # wait_for_drain must come AFTER WS drain (so HTTP traffic settles last).
    assert call_log.index("wait_for_drain") > drain_idx
