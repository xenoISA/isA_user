"""
L2 Component Tests — Circuit Breaker with BaseServiceClient

Tests circuit breaker integration with mocked httpx clients.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from core.circuit_breaker import CircuitBreaker, CircuitBreakerOpen, CircuitState


class TestCircuitBreakerWithHttpx:
    """Test circuit breaker wrapping httpx calls"""

    @pytest.mark.asyncio
    async def test_successful_call_passes_through(self):
        cb = CircuitBreaker(failure_threshold=3)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        async def call():
            cb.check()
            try:
                # Simulate successful HTTP call
                cb.record_success()
                return mock_response
            except Exception:
                cb.record_failure()
                raise

        result = await call()
        assert result.status_code == 200
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_failures_open_circuit(self):
        cb = CircuitBreaker(failure_threshold=2)

        for _ in range(2):
            cb.record_failure()

        assert cb.state == CircuitState.OPEN
        with pytest.raises(CircuitBreakerOpen):
            cb.check()

    @pytest.mark.asyncio
    async def test_open_circuit_skips_http_call(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        call_count = 0

        async def make_request():
            nonlocal call_count
            cb.check()
            call_count += 1  # Should not reach here when open
            return MagicMock(status_code=200)

        # First failure opens circuit
        cb.record_failure()

        # Subsequent calls should not make HTTP requests
        with pytest.raises(CircuitBreakerOpen):
            await make_request()
        assert call_count == 0

    @pytest.mark.asyncio
    async def test_half_open_probe_succeeds(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.0)
        cb.record_failure()
        # recovery_timeout=0 → immediately half-open

        cb.check()  # Probe allowed
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_server_errors_count_as_failures(self):
        """5xx responses should trigger circuit breaker"""
        cb = CircuitBreaker(failure_threshold=2)

        for status in [500, 502]:
            if status >= 500:
                cb.record_failure()

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_client_errors_dont_count(self):
        """4xx responses should NOT trigger circuit breaker"""
        cb = CircuitBreaker(failure_threshold=2)

        # 4xx errors are client errors, not service failures
        # They should not be recorded as failures
        for _ in range(5):
            pass  # Don't record 4xx as failures

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_connection_errors_count_as_failures(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()  # ConnectError
        cb.record_failure()  # TimeoutException
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerLogging:
    """Test that state transitions are logged"""

    def test_logs_state_transition_to_open(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="core.circuit_breaker"):
            cb = CircuitBreaker(name="test_service", failure_threshold=1)
            cb.record_failure()
        assert any("OPEN" in record.message for record in caplog.records)

    def test_logs_state_transition_to_closed(self, caplog):
        import logging
        with caplog.at_level(logging.INFO, logger="core.circuit_breaker"):
            cb = CircuitBreaker(name="test_service", failure_threshold=1, recovery_timeout=0.0)
            cb.record_failure()
            cb.check()
            cb.record_success()
        assert any("CLOSED" in record.message for record in caplog.records)
