"""
Graceful Shutdown Manager for isA_user Microservices

Provides shared SIGTERM/SIGINT handling, in-flight request draining,
and ordered cleanup execution for all FastAPI microservices.

Usage:
    from core.graceful_shutdown import GracefulShutdown, shutdown_middleware

    shutdown_manager = GracefulShutdown("account_service", grace_period=30.0)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        shutdown_manager.install_signal_handlers()
        # ... startup code ...
        shutdown_manager.add_cleanup("nats", event_bus.close)
        shutdown_manager.add_cleanup("postgres", db.close)

        yield

        shutdown_manager.initiate_shutdown()
        await shutdown_manager.wait_for_drain()
        await shutdown_manager.run_cleanups()

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)
"""

import asyncio
import logging
import signal
from typing import Any, Callable, List, Tuple, Union

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Per-cleanup timeout in seconds
_CLEANUP_TIMEOUT = 5.0


class GracefulShutdown:
    """
    Manages graceful shutdown for a microservice.

    Tracks in-flight requests, enforces a grace period for draining,
    and runs registered cleanup callbacks in order.
    """

    def __init__(self, service_name: str, grace_period: float = 30.0):
        self.service_name = service_name
        self.grace_period = grace_period
        self._shutting_down = False
        self._in_flight = 0
        self._cleanups: List[Tuple[str, Callable]] = []
        self._consul_registry = None

    @property
    def is_shutting_down(self) -> bool:
        return self._shutting_down

    def set_consul_registry(self, registry) -> None:
        """Register the Consul registry so shutdown can deregister before rejecting traffic."""
        self._consul_registry = registry

    @property
    def in_flight_count(self) -> int:
        return self._in_flight

    def initiate_shutdown(self) -> None:
        """Mark the service as shutting down.

        Deregisters from Consul first (if registered) so traffic stops
        being routed before we start rejecting requests with 503.
        """
        if not self._shutting_down:
            # Deregister from Consul BEFORE rejecting requests,
            # so load balancers stop sending traffic to this instance.
            if self._consul_registry:
                try:
                    self._consul_registry.deregister()
                    logger.info(f"[{self.service_name}] Deregistered from Consul")
                except Exception as e:
                    logger.error(f"[{self.service_name}] Failed to deregister from Consul: {e}")

            self._shutting_down = True
            logger.info(
                f"[{self.service_name}] Shutdown initiated "
                f"(grace_period={self.grace_period}s, in_flight={self._in_flight})"
            )

    def track_request_start(self) -> None:
        self._in_flight += 1

    def track_request_end(self) -> None:
        if self._in_flight > 0:
            self._in_flight -= 1

    def add_cleanup(self, name: str, fn: Callable) -> None:
        """Register a cleanup callback (async or sync). Runs in registration order."""
        self._cleanups.append((name, fn))

    async def wait_for_drain(self) -> None:
        """Wait for in-flight requests to complete, up to the grace period."""
        logger.info(
            f"[{self.service_name}] Draining in-flight requests "
            f"(count={self._in_flight}, timeout={self.grace_period}s)"
        )

        elapsed = 0.0
        interval = 0.1
        while self._in_flight > 0 and elapsed < self.grace_period:
            await asyncio.sleep(interval)
            elapsed += interval

        if self._in_flight > 0:
            logger.warning(
                f"[{self.service_name}] Grace period expired with "
                f"{self._in_flight} in-flight requests still active"
            )
        else:
            logger.info(f"[{self.service_name}] All requests drained successfully")

    async def run_cleanups(self) -> None:
        """Execute all registered cleanup callbacks in order."""
        logger.info(
            f"[{self.service_name}] Running {len(self._cleanups)} cleanup(s)"
        )
        for name, fn in self._cleanups:
            try:
                result = fn()
                if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                    await asyncio.wait_for(result, timeout=_CLEANUP_TIMEOUT)
                logger.info(f"[{self.service_name}] Cleanup completed: {name}")
            except asyncio.TimeoutError:
                logger.warning(
                    f"[{self.service_name}] Cleanup timed out: {name} "
                    f"(>{_CLEANUP_TIMEOUT}s)"
                )
            except Exception as e:
                logger.error(
                    f"[{self.service_name}] Cleanup failed: {name}: {e}"
                )
        logger.info(f"[{self.service_name}] Shutdown complete")

    def install_signal_handlers(self) -> None:
        """Install SIGTERM/SIGINT handlers that initiate graceful shutdown.

        Also resets shutdown state so that uvicorn's hot-reload cycle
        (which triggers lifespan shutdown then re-runs lifespan startup)
        starts fresh rather than staying stuck in shutting_down=True.
        """
        self._shutting_down = False
        self._in_flight = 0
        self._cleanups = []
        try:
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, self._handle_signal, sig)
            logger.info(
                f"[{self.service_name}] Signal handlers installed "
                f"(SIGTERM, SIGINT)"
            )
        except (NotImplementedError, RuntimeError):
            # Fallback for environments where loop signal handlers aren't supported
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, lambda s, f: self._handle_signal(s))
            logger.info(
                f"[{self.service_name}] Signal handlers installed (fallback mode)"
            )

    def _handle_signal(self, signum: signal.Signals) -> None:
        sig_name = signal.Signals(signum).name
        logger.info(
            f"[{self.service_name}] Received {sig_name}, "
            f"initiating graceful shutdown"
        )
        self.initiate_shutdown()


# Health-check paths that should respond even during shutdown
_HEALTH_PATHS = frozenset({"/health", "/health/", "/health/detailed"})


class _ShutdownMiddleware(BaseHTTPMiddleware):
    """Middleware that tracks in-flight requests and rejects new ones during shutdown."""

    def __init__(self, app: Any, shutdown_manager: GracefulShutdown):
        super().__init__(app)
        self.shutdown_manager = shutdown_manager

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allow health endpoints during shutdown
        if path in _HEALTH_PATHS or path.endswith("/health"):
            return await call_next(request)

        if self.shutdown_manager.is_shutting_down:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Service is shutting down",
                    "service": self.shutdown_manager.service_name,
                },
            )

        self.shutdown_manager.track_request_start()
        try:
            return await call_next(request)
        finally:
            self.shutdown_manager.track_request_end()


def shutdown_middleware(app: Any, shutdown_manager: GracefulShutdown):
    """Factory for adding shutdown middleware via app.add_middleware()."""
    return _ShutdownMiddleware(app, shutdown_manager=shutdown_manager)
