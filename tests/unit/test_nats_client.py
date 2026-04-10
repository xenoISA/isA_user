"""Unit tests for nats_client singleton async safety (Issue #95)"""

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import pytest


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton dict before each test"""
    import core.nats_client as mod
    mod._event_buses.clear()
    mod._event_bus_lock = asyncio.Lock()
    yield
    mod._event_buses.clear()


class TestGetEventBusConcurrency:
    """Verify that concurrent calls to get_event_bus return the same instance."""

    @pytest.mark.asyncio
    async def test_concurrent_calls_return_same_instance(self):
        """Multiple concurrent get_event_bus() calls must return the same object."""
        with patch("core.nats_client.NATSEventBus") as MockBus:
            instance = MagicMock()
            instance.connect = AsyncMock()
            MockBus.return_value = instance

            from core.nats_client import get_event_bus

            results = await asyncio.gather(
                get_event_bus("test_service"),
                get_event_bus("test_service"),
                get_event_bus("test_service"),
                get_event_bus("test_service"),
                get_event_bus("test_service"),
            )

            for r in results:
                assert r is instance

            MockBus.assert_called_once()
            instance.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_different_services_get_different_instances(self):
        """Different service names should produce separate event buses."""
        with patch("core.nats_client.NATSEventBus") as MockBus:
            def make_bus(**kw):
                m = MagicMock(name=kw.get("service_name", "?"))
                m.connect = AsyncMock()
                return m

            MockBus.side_effect = make_bus

            from core.nats_client import get_event_bus

            a = await get_event_bus("service_a")
            b = await get_event_bus("service_b")

            assert a is not b
            assert MockBus.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_cached_instance(self):
        """Second call returns cached instance without re-creating."""
        with patch("core.nats_client.NATSEventBus") as MockBus:
            instance = MagicMock()
            instance.connect = AsyncMock()
            MockBus.return_value = instance

            from core.nats_client import get_event_bus

            first = await get_event_bus("cached_svc")
            second = await get_event_bus("cached_svc")

            assert first is second
            MockBus.assert_called_once()


class TestConsumerNameSanitization:
    def test_sanitizes_wildcard_subject_fragments_for_durable_names(self):
        from core.nats_client import NATSEventBus

        assert (
            NATSEventBus._sanitize_consumer_name(
                "billing-billing-usage-recorded->-consumer-livee2e20260409e"
            )
            == "billing-billing-usage-recorded---consumer-livee2e20260409e"
        )

    def test_falls_back_to_consumer_for_all_invalid_names(self):
        from core.nats_client import NATSEventBus

        assert NATSEventBus._sanitize_consumer_name(">>>") == "consumer"
