"""
L1 Unit Tests for core/graceful_shutdown.py

Tests the GracefulShutdown class: signal handling, request tracking,
drain logic, cleanup execution, and structured logging.
"""

import asyncio
import signal
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.graceful_shutdown import GracefulShutdown


class TestGracefulShutdownInit:
    """Test initialization and configuration."""

    def test_default_grace_period(self):
        gs = GracefulShutdown("test_service")
        assert gs.service_name == "test_service"
        assert gs.grace_period == 30.0

    def test_custom_grace_period(self):
        gs = GracefulShutdown("test_service", grace_period=10.0)
        assert gs.grace_period == 10.0

    def test_initial_state(self):
        gs = GracefulShutdown("test_service")
        assert gs.is_shutting_down is False
        assert gs.in_flight_count == 0


class TestRequestTracking:
    """Test in-flight request tracking."""

    def test_track_request_increments(self):
        gs = GracefulShutdown("test_service")
        gs.track_request_start()
        assert gs.in_flight_count == 1
        gs.track_request_start()
        assert gs.in_flight_count == 2

    def test_track_request_decrements(self):
        gs = GracefulShutdown("test_service")
        gs.track_request_start()
        gs.track_request_start()
        gs.track_request_end()
        assert gs.in_flight_count == 1

    def test_track_request_does_not_go_negative(self):
        gs = GracefulShutdown("test_service")
        gs.track_request_end()
        assert gs.in_flight_count == 0


class TestCleanupRegistration:
    """Test cleanup callback registration and execution."""

    @pytest.mark.asyncio
    async def test_add_cleanup(self):
        gs = GracefulShutdown("test_service")
        cleanup_fn = AsyncMock()
        gs.add_cleanup("nats", cleanup_fn)
        assert len(gs._cleanups) == 1
        assert gs._cleanups[0] == ("nats", cleanup_fn)

    @pytest.mark.asyncio
    async def test_multiple_cleanups_run_in_order(self):
        gs = GracefulShutdown("test_service")
        call_order = []

        async def cleanup_a():
            call_order.append("a")

        async def cleanup_b():
            call_order.append("b")

        gs.add_cleanup("first", cleanup_a)
        gs.add_cleanup("second", cleanup_b)
        await gs.run_cleanups()

        assert call_order == ["a", "b"]

    @pytest.mark.asyncio
    async def test_sync_cleanup_supported(self):
        gs = GracefulShutdown("test_service")
        called = False

        def sync_cleanup():
            nonlocal called
            called = True

        gs.add_cleanup("sync", sync_cleanup)
        await gs.run_cleanups()
        assert called is True

    @pytest.mark.asyncio
    async def test_cleanup_failure_does_not_stop_others(self):
        gs = GracefulShutdown("test_service")
        second_called = False

        async def failing_cleanup():
            raise RuntimeError("cleanup failed")

        async def second_cleanup():
            nonlocal second_called
            second_called = True

        gs.add_cleanup("failing", failing_cleanup)
        gs.add_cleanup("second", second_cleanup)
        await gs.run_cleanups()

        assert second_called is True

    @pytest.mark.asyncio
    async def test_cleanup_timeout(self):
        gs = GracefulShutdown("test_service")

        async def slow_cleanup():
            await asyncio.sleep(10)

        gs.add_cleanup("slow", slow_cleanup)
        # Should not hang — each cleanup has a per-item timeout (5s default)
        await asyncio.wait_for(gs.run_cleanups(), timeout=7.0)


class TestDrainLogic:
    """Test request draining with grace period."""

    @pytest.mark.asyncio
    async def test_drain_completes_when_no_requests(self):
        gs = GracefulShutdown("test_service", grace_period=1.0)
        await asyncio.wait_for(gs.wait_for_drain(), timeout=2.0)

    @pytest.mark.asyncio
    async def test_drain_waits_for_in_flight(self):
        gs = GracefulShutdown("test_service", grace_period=5.0)
        gs.track_request_start()

        async def finish_request():
            await asyncio.sleep(0.2)
            gs.track_request_end()

        asyncio.create_task(finish_request())
        await asyncio.wait_for(gs.wait_for_drain(), timeout=2.0)
        assert gs.in_flight_count == 0

    @pytest.mark.asyncio
    async def test_drain_respects_grace_period(self):
        gs = GracefulShutdown("test_service", grace_period=0.3)
        gs.track_request_start()  # Never finished

        await asyncio.wait_for(gs.wait_for_drain(), timeout=2.0)
        # Should have exited after grace period even with in-flight request
        assert gs.in_flight_count == 1


class TestShutdownInitiation:
    """Test shutdown signal handling."""

    def test_initiate_shutdown_sets_flag(self):
        gs = GracefulShutdown("test_service")
        gs.initiate_shutdown()
        assert gs.is_shutting_down is True

    def test_initiate_shutdown_idempotent(self):
        gs = GracefulShutdown("test_service")
        gs.initiate_shutdown()
        gs.initiate_shutdown()
        assert gs.is_shutting_down is True


class TestStructuredLogging:
    """Test that shutdown sequence produces structured log messages."""

    @pytest.mark.asyncio
    async def test_drain_logs_start_and_completion(self, caplog):
        gs = GracefulShutdown("test_service", grace_period=1.0)
        with caplog.at_level(logging.INFO):
            await gs.wait_for_drain()

        messages = [r.message for r in caplog.records]
        assert any("drain" in m.lower() or "shutdown" in m.lower() for m in messages)

    @pytest.mark.asyncio
    async def test_cleanup_logs_each_step(self, caplog):
        gs = GracefulShutdown("test_service")
        gs.add_cleanup("nats", AsyncMock())
        gs.add_cleanup("postgres", AsyncMock())

        with caplog.at_level(logging.INFO):
            await gs.run_cleanups()

        messages = " ".join(r.message for r in caplog.records)
        assert "nats" in messages
        assert "postgres" in messages
