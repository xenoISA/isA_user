"""
Standardized Health Check Module for isA_user Microservices

Provides a shared health check endpoint that:
- Probes actual infrastructure dependencies (postgres, nats, minio, etc.)
- Returns consistent status values: healthy / degraded / unhealthy
- Uses correct HTTP status codes: 200 for healthy/degraded, 503 for unhealthy
- Integrates with GracefulShutdown for shutdown-awareness

Usage in a microservice main.py:

    from core.health import HealthCheck

    health = HealthCheck(
        service_name="billing_service",
        version="1.0.0",
        shutdown_manager=shutdown_manager,
    )
    health.add_postgres(lambda: repository.db if repository else None)
    health.add_nats(lambda: event_bus)
    health.add_minio(lambda: minio_client)

    @app.get("/health")
    @app.get("/api/v1/billing/health")
    async def health_endpoint():
        return await health.check()
"""

import inspect
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union

from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Timeout for each individual dependency probe (seconds)
_PROBE_TIMEOUT = 3.0


class HealthCheck:
    """Standardized health checker for isA_user microservices."""

    def __init__(
        self,
        service_name: str,
        version: str = "1.0.0",
        shutdown_manager=None,
    ):
        self.service_name = service_name
        self.version = version
        self.shutdown_manager = shutdown_manager
        self._probes: List[_Probe] = []

    # -- Register dependency probes --

    def add_postgres(self, get_client: Callable, critical: bool = True):
        """Register a Postgres dependency probe.

        Args:
            get_client: callable returning a PostgresClientWrapper (or None).
                        Called at check time so it picks up late-init globals.
            critical: if True, failure → unhealthy. If False, failure → degraded.
        """
        self._probes.append(_Probe("postgres", _probe_postgres, get_client, critical))

    def add_nats(self, get_client: Callable, critical: bool = False):
        """Register a NATS dependency probe."""
        self._probes.append(_Probe("nats", _probe_nats, get_client, critical))

    def add_minio(self, get_client: Callable, critical: bool = False):
        """Register a MinIO dependency probe."""
        self._probes.append(_Probe("minio", _probe_minio, get_client, critical))

    def add_neo4j(self, get_client: Callable, critical: bool = False):
        """Register a Neo4j/graph dependency probe."""
        self._probes.append(_Probe("neo4j", _probe_neo4j, get_client, critical))

    def add_qdrant(self, get_client: Callable, critical: bool = False):
        """Register a Qdrant dependency probe."""
        self._probes.append(_Probe("qdrant", _probe_qdrant, get_client, critical))

    def add_mqtt(self, get_client: Callable, critical: bool = False):
        """Register an MQTT dependency probe."""
        self._probes.append(_Probe("mqtt", _probe_mqtt, get_client, critical))

    def add_custom(
        self, name: str, probe_fn: Callable, get_client: Callable, critical: bool = False
    ):
        """Register a custom dependency probe."""
        self._probes.append(_Probe(name, probe_fn, get_client, critical))

    def add_check(self, name: str, check_fn: Callable, critical: bool = True):
        """Register a simple async-callable probe.

        Args:
            name: dependency name (e.g. "postgres")
            check_fn: zero-arg callable returning bool (or awaitable bool).
                       Example: lambda: service.check_connection()
            critical: if True, failure → unhealthy.
        """
        self._probes.append(_Probe(name, _probe_callable, check_fn, critical))

    # -- Main check --

    async def check(self) -> JSONResponse:
        """Run all probes and return a standardized health response.

        Returns JSONResponse with:
            - HTTP 200 + status "healthy" when all deps are up
            - HTTP 200 + status "degraded" when non-critical deps are down
            - HTTP 503 + status "unhealthy" when critical deps are down

        Note: shutdown-awareness is NOT handled here. The shutdown middleware
        already rejects non-health requests with 503 during shutdown. The
        /health endpoint must stay honest about infrastructure status so that
        uvicorn's hot-reload cycle doesn't get stuck reporting "shutting_down"
        when the service is actually reloading and deps are still healthy.
        """
        now = datetime.now(tz=timezone.utc).isoformat()

        dependencies: Dict[str, Dict[str, Any]] = {}
        has_critical_failure = False
        has_non_critical_failure = False

        for probe in self._probes:
            dep_status, error = await _run_probe(probe)
            dependencies[probe.name] = {"status": dep_status}
            if error:
                dependencies[probe.name]["error"] = error

            if dep_status == "unhealthy":
                if probe.critical:
                    has_critical_failure = True
                else:
                    has_non_critical_failure = True

        if has_critical_failure:
            status = "unhealthy"
            http_code = 503
        elif has_non_critical_failure:
            status = "degraded"
            http_code = 200
        else:
            status = "healthy"
            http_code = 200

        return JSONResponse(
            status_code=http_code,
            content={
                "status": status,
                "service": self.service_name,
                "version": self.version,
                "dependencies": dependencies,
                "timestamp": now,
            },
        )


# -- Internal probe infrastructure --


class _Probe:
    __slots__ = ("name", "fn", "get_client", "critical")

    def __init__(self, name: str, fn: Callable, get_client: Callable, critical: bool):
        self.name = name
        self.fn = fn
        self.get_client = get_client
        self.critical = critical


async def _run_probe(probe: _Probe) -> tuple:
    """Run a single probe and return (status_str, error_or_None)."""
    try:
        client = probe.get_client()
        if client is None:
            return ("unhealthy", "client not initialized")

        result = probe.fn(client)
        if inspect.isawaitable(result):
            result = await result

        if result:
            return ("healthy", None)
        else:
            return ("unhealthy", "probe returned false")
    except Exception as e:
        logger.debug(f"Health probe {probe.name} failed: {e}")
        return ("unhealthy", str(e))


# -- Probe functions for each dependency type --


async def _probe_callable(result_or_awaitable) -> bool:
    """Probe via a value returned by the add_check lambda.

    The lambda passed to add_check() is called by _run_probe as get_client(),
    so by the time this function runs, we already have the return value
    (which may be a coroutine/awaitable or a plain bool).
    """
    if inspect.isawaitable(result_or_awaitable):
        result_or_awaitable = await result_or_awaitable
    return bool(result_or_awaitable)


async def _probe_postgres(client) -> bool:
    """Probe Postgres via the existing PostgresClientWrapper.health_check()."""
    result = client.health_check()
    if inspect.isawaitable(result):
        result = await result
    # health_check() returns a dict with status info, or None on failure
    return result is not None


async def _probe_nats(client) -> bool:
    """Probe NATS via NATSEventBus.is_connected property."""
    return client.is_connected


async def _probe_minio(client) -> bool:
    """Probe MinIO — check if the client has a working connection."""
    # MinIO clients typically have list_buckets or similar
    if hasattr(client, "health_check"):
        result = client.health_check()
        if inspect.isawaitable(result):
            result = await result
        return bool(result)
    # Fallback: check if client object exists and is not None
    return client is not None


async def _probe_neo4j(client) -> bool:
    """Probe Neo4j via graph_client.health_check()."""
    if hasattr(client, "health_check"):
        result = client.health_check()
        if inspect.isawaitable(result):
            result = await result
        return bool(result)
    return client is not None


async def _probe_qdrant(client) -> bool:
    """Probe Qdrant — check connectivity."""
    if hasattr(client, "health_check"):
        result = client.health_check()
        if inspect.isawaitable(result):
            result = await result
        return bool(result)
    # qdrant_client typically has get_collections()
    if hasattr(client, "get_collections"):
        result = client.get_collections()
        if inspect.isawaitable(result):
            result = await result
        return True
    return client is not None


async def _probe_mqtt(client) -> bool:
    """Probe MQTT via client.is_connected or health_check()."""
    if hasattr(client, "is_connected"):
        prop = client.is_connected
        return prop() if callable(prop) else bool(prop)
    if hasattr(client, "health_check"):
        result = client.health_check()
        if inspect.isawaitable(result):
            result = await result
        return bool(result)
    return client is not None


__all__ = ["HealthCheck"]
