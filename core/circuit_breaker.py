"""
Circuit Breaker for Inter-Service HTTP Clients

States: CLOSED (normal) -> OPEN (fail-fast) -> HALF_OPEN (probe) -> CLOSED
Integrates with BaseServiceClient to protect against cascading failures.
"""

import logging
import time
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpen(Exception):
    """Raised when a call is attempted on an open circuit."""

    def __init__(self, name: str, recovery_seconds: float = 0):
        self.name = name
        self.recovery_seconds = recovery_seconds
        super().__init__(
            f"Circuit breaker '{name}' is OPEN. "
            f"Retry after {recovery_seconds:.1f}s."
        )


class CircuitBreaker:
    """
    Per-service circuit breaker with three states.

    Usage:
        cb = CircuitBreaker(name="account_service", failure_threshold=5)

        try:
            cb.check()               # Raises CircuitBreakerOpen if open
            response = await client.get(...)
            if response.status_code >= 500:
                cb.record_failure()
            else:
                cb.record_success()
        except (httpx.ConnectError, httpx.TimeoutException):
            cb.record_failure()
            raise
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._failure_count = 0
        self._success_count = 0
        self._state = CircuitState.CLOSED
        self._opened_at: Optional[float] = None
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info(
                    f"Circuit breaker '{self.name}' transitioned to HALF_OPEN "
                    f"after {elapsed:.1f}s"
                )
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def check(self) -> None:
        """Check if a request is allowed. Raises CircuitBreakerOpen if not."""
        current_state = self.state

        if current_state == CircuitState.CLOSED:
            return

        if current_state == CircuitState.OPEN:
            remaining = self.recovery_timeout - (time.monotonic() - self._opened_at)
            raise CircuitBreakerOpen(self.name, max(0, remaining))

        if current_state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerOpen(self.name, 0)
            self._half_open_calls += 1

    def record_success(self) -> None:
        """Record a successful call. Resets failure count, closes circuit if half-open."""
        if self._state == CircuitState.HALF_OPEN or self.state == CircuitState.HALF_OPEN:
            logger.info(
                f"Circuit breaker '{self.name}' transitioned to CLOSED "
                f"(probe succeeded)"
            )
        self._failure_count = 0
        self._success_count += 1
        self._state = CircuitState.CLOSED
        self._opened_at = None
        self._half_open_calls = 0

    def record_failure(self) -> None:
        """Record a failed call. Opens circuit if threshold reached."""
        self._failure_count += 1

        if self._state == CircuitState.HALF_OPEN or self.state == CircuitState.HALF_OPEN:
            # Half-open probe failed → reopen
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
            self._half_open_calls = 0
            logger.warning(
                f"Circuit breaker '{self.name}' re-opened "
                f"(half-open probe failed)"
            )
            return

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
            logger.warning(
                f"Circuit breaker '{self.name}' transitioned to OPEN "
                f"after {self._failure_count} failures"
            )

    def metrics(self) -> dict:
        """Return current circuit breaker metrics for observability."""
        result = {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
        }
        if self._opened_at is not None:
            result["opened_at"] = self._opened_at
        return result


__all__ = ["CircuitBreaker", "CircuitBreakerOpen", "CircuitState"]
