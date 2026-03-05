"""Unit tests for postgres_client singleton async safety (Issue #95)"""

import asyncio
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton dict before each test"""
    import core.postgres_client as mod
    mod._postgres_clients.clear()
    mod._postgres_client_lock = asyncio.Lock()
    yield
    mod._postgres_clients.clear()


class TestGetPostgresClientConcurrency:
    """Verify that concurrent calls to get_postgres_client return the same instance."""

    @pytest.mark.asyncio
    async def test_concurrent_calls_return_same_instance(self):
        """Multiple concurrent get_postgres_client() calls must return the same object."""
        with patch("core.postgres_client.PostgresClientWrapper") as MockWrapper:
            instance = MagicMock()
            MockWrapper.return_value = instance

            from core.postgres_client import get_postgres_client

            results = await asyncio.gather(
                get_postgres_client("test_service"),
                get_postgres_client("test_service"),
                get_postgres_client("test_service"),
                get_postgres_client("test_service"),
                get_postgres_client("test_service"),
            )

            # All results must be the exact same object
            for r in results:
                assert r is instance

            # Constructor called exactly once
            MockWrapper.assert_called_once()

    @pytest.mark.asyncio
    async def test_different_services_get_different_instances(self):
        """Different service names should produce separate clients."""
        with patch("core.postgres_client.PostgresClientWrapper") as MockWrapper:
            MockWrapper.side_effect = lambda **kw: MagicMock(name=kw["service_name"])

            from core.postgres_client import get_postgres_client

            a = await get_postgres_client("service_a")
            b = await get_postgres_client("service_b")

            assert a is not b
            assert MockWrapper.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_cached_instance(self):
        """Second call returns cached instance without re-creating."""
        with patch("core.postgres_client.PostgresClientWrapper") as MockWrapper:
            instance = MagicMock()
            MockWrapper.return_value = instance

            from core.postgres_client import get_postgres_client

            first = await get_postgres_client("cached_svc")
            second = await get_postgres_client("cached_svc")

            assert first is second
            MockWrapper.assert_called_once()
