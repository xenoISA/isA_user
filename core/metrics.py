"""
Prometheus Metrics & Observability for isA_user Microservices

Thin wrapper around isa_common observability clients. Provides:
- setup_metrics(): one-liner to enable metrics, tracing, and logging
- Domain-specific metrics: AUTH_FAILURES, BUSINESS_OPERATIONS, REQUEST_PAYLOAD_SIZE

Usage:
    from core.metrics import setup_metrics

    app = FastAPI(...)
    setup_metrics(app, "task_service")
"""

import logging

from isa_common.observability import setup_observability
from isa_common.metrics import create_counter, create_histogram

logger = logging.getLogger(__name__)

# Paths excluded from metrics instrumentation (handled by isa_common)
EXCLUDED_PATHS = frozenset({"/health", "/health/detailed", "/metrics", "/ready", "/live"})

# Domain-specific metrics (re-created with standardized naming via isa_common)
AUTH_FAILURES = create_counter(
    "auth_failures_total",
    "Total authentication failures",
    ["service", "method"],
)

BUSINESS_OPERATIONS = create_counter(
    "business_operations_total",
    "Business operation counter for domain-specific tracking",
    ["service", "operation", "status"],
)

REQUEST_PAYLOAD_SIZE = create_histogram(
    "http_request_content_length_bytes",
    "HTTP request payload size in bytes",
    ["service"],
    buckets=[100, 1_000, 10_000, 100_000, 1_000_000],
)


def _should_instrument(path: str) -> bool:
    """Return True if the path should be instrumented."""
    for excluded in EXCLUDED_PATHS:
        if path == excluded or path.startswith(excluded + "/"):
            return False
    return True


def setup_metrics(app, service_name: str, version: str = "unknown"):
    """
    Attach full observability stack (metrics, tracing, logging) to a FastAPI app.

    Delegates to isa_common.setup_observability() for standardized setup:
    - Prometheus metrics with /metrics endpoint
    - OpenTelemetry tracing to Tempo
    - Structured logging to Loki

    Args:
        app: The FastAPI application instance.
        service_name: Name of the microservice (used in metric labels).
        version: Service version string.

    Returns:
        Dict indicating which pillars were enabled.
    """
    result = setup_observability(
        app,
        service_name=service_name,
        version=version,
    )

    logger.info(f"[{service_name}] Observability enabled: {result}")
    return result


__all__ = [
    "AUTH_FAILURES",
    "BUSINESS_OPERATIONS",
    "REQUEST_PAYLOAD_SIZE",
    "setup_metrics",
]
