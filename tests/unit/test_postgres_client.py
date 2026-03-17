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


class TestPostgresClientPoolSize:
    """Verify that PostgresClientWrapper passes reduced pool sizes to AsyncPostgresClient.

    With 35 microservices sharing a single PostgreSQL instance (max_connections=100),
    the default min_pool_size=5/max_pool_size=20 causes pool exhaustion.
    Fixes #137.
    """

    def test_pool_sizes_passed_to_async_client(self):
        """PostgresClientWrapper must pass min/max pool sizes to AsyncPostgresClient."""
        with patch("core.postgres_client.AsyncPostgresClient") as MockClient, \
             patch("core.config_manager.ConfigManager") as MockConfig:
            MockConfig.return_value.discover_service.return_value = ("localhost", 5432)
            MockClient.return_value = MagicMock()

            from core.postgres_client import PostgresClientWrapper
            wrapper = PostgresClientWrapper(service_name="test_svc", password="test")

            call_kwargs = MockClient.call_args.kwargs
            assert "min_pool_size" in call_kwargs, \
                "min_pool_size must be passed to AsyncPostgresClient"
            assert "max_pool_size" in call_kwargs, \
                "max_pool_size must be passed to AsyncPostgresClient"

    def test_pool_sizes_fit_within_pg_limit(self):
        """Pool sizes must allow 35 services to fit within max_connections=100."""
        with patch("core.postgres_client.AsyncPostgresClient") as MockClient, \
             patch("core.config_manager.ConfigManager") as MockConfig:
            MockConfig.return_value.discover_service.return_value = ("localhost", 5432)
            MockClient.return_value = MagicMock()

            from core.postgres_client import PostgresClientWrapper
            wrapper = PostgresClientWrapper(service_name="test_svc", password="test")

            kwargs = MockClient.call_args.kwargs
            max_pool = kwargs.get("max_pool_size", 20)  # default is 20
            # 35 services * max_pool_size must be <= 100 (PG max_connections)
            assert 35 * max_pool <= 100, \
                f"35 services × max_pool_size={max_pool} = {35*max_pool} exceeds PG max_connections=100"
