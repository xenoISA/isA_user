"""
L2 Component Tests for core/graceful_shutdown.py

Tests GracefulShutdown integrated with FastAPI middleware,
mocking HTTP requests to verify request draining and 503 responses.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from core.graceful_shutdown import GracefulShutdown, shutdown_middleware


class TestShutdownMiddleware:
    """Test the ASGI middleware for request tracking and rejection."""

    def _make_app(self, gs: GracefulShutdown) -> FastAPI:
        app = FastAPI()
        app.add_middleware(shutdown_middleware, shutdown_manager=gs)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        @app.get("/slow")
        async def slow_endpoint():
            await asyncio.sleep(0.5)
            return {"status": "ok"}

        return app

    @pytest.mark.asyncio
    async def test_normal_request_passes_through(self):
        gs = GracefulShutdown("test_service")
        app = self._make_app(gs)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_request_during_shutdown_returns_503(self):
        gs = GracefulShutdown("test_service")
        app = self._make_app(gs)
        gs.initiate_shutdown()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")
            assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_middleware_tracks_in_flight(self):
        gs = GracefulShutdown("test_service")
        app = self._make_app(gs)

        in_flight_during_request = None

        @app.get("/check-inflight")
        async def check_inflight():
            nonlocal in_flight_during_request
            in_flight_during_request = gs.in_flight_count
            return {"in_flight": in_flight_during_request}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/check-inflight")

        # During request, in_flight should have been >= 1
        assert in_flight_during_request >= 1
        # After request, should be back to 0
        assert gs.in_flight_count == 0

    @pytest.mark.asyncio
    async def test_health_endpoint_allowed_during_shutdown(self):
        gs = GracefulShutdown("test_service")
        app = self._make_app(gs)

        @app.get("/health")
        async def health():
            return {"status": "shutting_down"}

        gs.initiate_shutdown()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            # Health endpoints should still respond during shutdown
            assert response.status_code == 200


class TestFullShutdownFlow:
    """Test the complete shutdown flow: signal -> drain -> cleanup."""

    @pytest.mark.asyncio
    async def test_full_shutdown_sequence(self):
        gs = GracefulShutdown("test_service", grace_period=2.0)
        cleanup_called = False

        async def cleanup():
            nonlocal cleanup_called
            cleanup_called = True

        gs.add_cleanup("test", cleanup)

        # Simulate: initiate shutdown -> drain -> cleanup
        gs.initiate_shutdown()
        assert gs.is_shutting_down is True

        await gs.wait_for_drain()
        await gs.run_cleanups()

        assert cleanup_called is True
