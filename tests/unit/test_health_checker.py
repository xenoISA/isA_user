"""
Unit & Component tests for core/health_checker.py — check_database_health()

L1 Unit: No-db-url path (pure logic, no I/O)
L2 Component: Mocked asyncpg connection (healthy + unhealthy + timeout)
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.health_checker import HealthStatus, ServiceHealthChecker


# ---------------------------------------------------------------------------
# L1 Unit — no database configured
# ---------------------------------------------------------------------------

class TestCheckDatabaseHealthNoUrl:
    """When db_url is None, should return HEALTHY with informational message."""

    @pytest.mark.asyncio
    async def test_returns_healthy_when_no_url(self):
        checker = ServiceHealthChecker("test_svc")
        result = await checker.check_database_health(db_url=None)

        assert result.status == HealthStatus.HEALTHY
        assert result.name == "database"
        assert result.error_message == "No database configured"

    @pytest.mark.asyncio
    async def test_response_time_is_zero_when_no_url(self):
        checker = ServiceHealthChecker("test_svc")
        result = await checker.check_database_health(db_url=None)

        assert result.response_time == 0


# ---------------------------------------------------------------------------
# L2 Component — mocked asyncpg (healthy case)
# ---------------------------------------------------------------------------

class TestCheckDatabaseHealthHealthy:
    """When the database responds to SELECT 1, should return HEALTHY."""

    @pytest.mark.asyncio
    async def test_returns_healthy_on_successful_query(self):
        checker = ServiceHealthChecker("test_svc")

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.close = AsyncMock()

        with patch("core.health_checker.asyncpg") as mock_asyncpg:
            mock_asyncpg.connect = AsyncMock(return_value=mock_conn)
            result = await checker.check_database_health(
                db_url="postgresql://localhost/testdb"
            )

        assert result.status == HealthStatus.HEALTHY
        assert result.name == "database"
        assert result.error_message is None
        assert result.response_time >= 0
        assert isinstance(result.last_check, datetime)

    @pytest.mark.asyncio
    async def test_executes_select_1(self):
        checker = ServiceHealthChecker("test_svc")

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.close = AsyncMock()

        with patch("core.health_checker.asyncpg") as mock_asyncpg:
            mock_asyncpg.connect = AsyncMock(return_value=mock_conn)
            await checker.check_database_health(
                db_url="postgresql://localhost/testdb"
            )

        mock_conn.fetchval.assert_called_once_with("SELECT 1")

    @pytest.mark.asyncio
    async def test_closes_connection_after_check(self):
        checker = ServiceHealthChecker("test_svc")

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.close = AsyncMock()

        with patch("core.health_checker.asyncpg") as mock_asyncpg:
            mock_asyncpg.connect = AsyncMock(return_value=mock_conn)
            await checker.check_database_health(
                db_url="postgresql://localhost/testdb"
            )

        mock_conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# L2 Component — mocked asyncpg (unhealthy cases)
# ---------------------------------------------------------------------------

class TestCheckDatabaseHealthUnhealthy:
    """When the database is unreachable, should return UNHEALTHY."""

    @pytest.mark.asyncio
    async def test_returns_unhealthy_on_connection_error(self):
        checker = ServiceHealthChecker("test_svc")

        with patch("core.health_checker.asyncpg") as mock_asyncpg:
            mock_asyncpg.connect = AsyncMock(
                side_effect=OSError("Connection refused")
            )
            result = await checker.check_database_health(
                db_url="postgresql://localhost/testdb"
            )

        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection refused" in result.error_message
        assert isinstance(result.last_check, datetime)

    @pytest.mark.asyncio
    async def test_returns_unhealthy_on_timeout(self):
        checker = ServiceHealthChecker("test_svc")

        with patch("core.health_checker.asyncpg") as mock_asyncpg:
            mock_asyncpg.connect = AsyncMock(
                side_effect=asyncio.TimeoutError()
            )
            result = await checker.check_database_health(
                db_url="postgresql://localhost/testdb", timeout=1.0
            )

        assert result.status == HealthStatus.UNHEALTHY
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_returns_unhealthy_on_query_failure(self):
        checker = ServiceHealthChecker("test_svc")

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(
            side_effect=Exception("relation does not exist")
        )
        mock_conn.close = AsyncMock()

        with patch("core.health_checker.asyncpg") as mock_asyncpg:
            mock_asyncpg.connect = AsyncMock(return_value=mock_conn)
            result = await checker.check_database_health(
                db_url="postgresql://localhost/testdb"
            )

        assert result.status == HealthStatus.UNHEALTHY
        assert "relation does not exist" in result.error_message


# ---------------------------------------------------------------------------
# L2 Component — configurable timeout
# ---------------------------------------------------------------------------

class TestCheckDatabaseHealthTimeout:
    """Timeout parameter should be forwarded to asyncpg.connect."""

    @pytest.mark.asyncio
    async def test_default_timeout_is_5_seconds(self):
        checker = ServiceHealthChecker("test_svc")

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.close = AsyncMock()

        with patch("core.health_checker.asyncpg") as mock_asyncpg:
            mock_asyncpg.connect = AsyncMock(return_value=mock_conn)
            await checker.check_database_health(
                db_url="postgresql://localhost/testdb"
            )

        mock_asyncpg.connect.assert_called_once_with(
            "postgresql://localhost/testdb", timeout=5.0
        )

    @pytest.mark.asyncio
    async def test_custom_timeout(self):
        checker = ServiceHealthChecker("test_svc")

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.close = AsyncMock()

        with patch("core.health_checker.asyncpg") as mock_asyncpg:
            mock_asyncpg.connect = AsyncMock(return_value=mock_conn)
            await checker.check_database_health(
                db_url="postgresql://localhost/testdb", timeout=2.0
            )

        mock_asyncpg.connect.assert_called_once_with(
            "postgresql://localhost/testdb", timeout=2.0
        )


# ---------------------------------------------------------------------------
# L2 Component — connection close safety
# ---------------------------------------------------------------------------

class TestCheckDatabaseHealthConnectionCleanup:
    """Connection must be closed even when the query fails."""

    @pytest.mark.asyncio
    async def test_closes_connection_on_query_error(self):
        checker = ServiceHealthChecker("test_svc")

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=Exception("boom"))
        mock_conn.close = AsyncMock()

        with patch("core.health_checker.asyncpg") as mock_asyncpg:
            mock_asyncpg.connect = AsyncMock(return_value=mock_conn)
            await checker.check_database_health(
                db_url="postgresql://localhost/testdb"
            )

        mock_conn.close.assert_called_once()
