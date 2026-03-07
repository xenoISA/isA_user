"""
Prometheus Metrics Middleware for isA_user Microservices

Shared metrics instrumentation using prometheus-fastapi-instrumentator.
Provides standard HTTP metrics (request count, latency histogram, error rate)
and a `/metrics` endpoint for Prometheus scraping.

Usage:
    from core.metrics import setup_metrics

    app = FastAPI(...)
    setup_metrics(app, "task_service")
"""

import logging

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Info

logger = logging.getLogger(__name__)

# Paths excluded from metrics instrumentation
EXCLUDED_PATHS = frozenset({"/health", "/health/detailed", "/metrics"})

# Shared custom metrics
SERVICE_INFO = Info("service", "Service metadata")

AUTH_FAILURES = Counter(
    "auth_failures_total",
    "Total authentication failures",
    ["service", "method"],
)

BUSINESS_OPERATIONS = Counter(
    "business_operations_total",
    "Business operation counter for domain-specific tracking",
    ["service", "operation", "status"],
)

REQUEST_PAYLOAD_SIZE = Histogram(
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


def setup_metrics(app: FastAPI, service_name: str) -> Instrumentator:
    """
    Attach Prometheus metrics instrumentation and /metrics endpoint to a FastAPI app.

    Args:
        app: The FastAPI application instance.
        service_name: Name of the microservice (used in metric labels).

    Returns:
        The configured Instrumentator instance.
    """
    SERVICE_INFO.info({"service_name": service_name})

    instrumentator = Instrumentator(
        excluded_handlers=["/health", "/health/detailed", "/metrics"],
    )

    instrumentator.instrument(app)
    instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)

    logger.info(f"[{service_name}] Prometheus metrics enabled on /metrics")
    return instrumentator


__all__ = [
    "AUTH_FAILURES",
    "BUSINESS_OPERATIONS",
    "REQUEST_PAYLOAD_SIZE",
    "setup_metrics",
]
