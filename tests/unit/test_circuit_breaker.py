"""
L1 Unit Tests — Circuit Breaker State Machine

Tests pure state transition logic with no I/O or mocks.
"""

import asyncio
import time

import pytest

from core.circuit_breaker import CircuitBreaker, CircuitBreakerOpen, CircuitState


class TestCircuitBreakerStates:
    """Test state transitions: CLOSED -> OPEN -> HALF_OPEN -> CLOSED"""

    def test_initial_state_is_closed(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
        assert cb.state == CircuitState.CLOSED

    def test_stays_closed_below_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 2

    def test_opens_at_failure_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_open_circuit_raises(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        with pytest.raises(CircuitBreakerOpen):
            cb.check()

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_transitions_to_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.0)
        cb.record_failure()
        # With recovery_timeout=0, state property immediately transitions to half-open
        assert cb.state == CircuitState.HALF_OPEN

    def test_stays_open_during_recovery_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_half_open_success_closes_circuit(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.0)
        cb.record_failure()
        # Now half-open (recovery_timeout=0)
        cb.check()  # Should not raise — allows one probe
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_half_open_failure_reopens_circuit(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        # Wait for recovery timeout to transition to half-open
        import time

        time.sleep(0.11)
        assert cb.state == CircuitState.HALF_OPEN
        cb.check()  # Allow probe
        cb.record_failure()
        # Should be open again with new recovery timeout
        assert cb._state == CircuitState.OPEN

    def test_half_open_limits_concurrent_probes(self):
        cb = CircuitBreaker(
            failure_threshold=1, recovery_timeout=0.0, half_open_max_calls=1
        )
        cb.record_failure()
        # First probe allowed
        cb.check()
        # Second probe should be rejected
        with pytest.raises(CircuitBreakerOpen):
            cb.check()


class TestCircuitBreakerConfig:
    """Test configuration validation"""

    def test_default_config(self):
        cb = CircuitBreaker()
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 30.0
        assert cb.half_open_max_calls == 1

    def test_custom_config(self):
        cb = CircuitBreaker(
            failure_threshold=10, recovery_timeout=60.0, half_open_max_calls=3
        )
        assert cb.failure_threshold == 10
        assert cb.recovery_timeout == 60.0
        assert cb.half_open_max_calls == 3

    def test_name_defaults_to_default(self):
        cb = CircuitBreaker()
        assert cb.name == "default"

    def test_custom_name(self):
        cb = CircuitBreaker(name="payment_service")
        assert cb.name == "payment_service"


class TestCircuitBreakerMetrics:
    """Test metrics and state info"""

    def test_metrics_initial(self):
        cb = CircuitBreaker(name="test")
        metrics = cb.metrics()
        assert metrics["name"] == "test"
        assert metrics["state"] == "closed"
        assert metrics["failure_count"] == 0
        assert metrics["success_count"] == 0

    def test_metrics_after_failures(self):
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        metrics = cb.metrics()
        assert metrics["failure_count"] == 2
        assert metrics["state"] == "closed"

    def test_metrics_when_open(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        metrics = cb.metrics()
        assert metrics["state"] == "open"
        assert "opened_at" in metrics
