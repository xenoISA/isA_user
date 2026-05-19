"""Observability hooks for artifact_service upstream-fallback paths.

Centralises:
  * Sentry init (no-op when ``SENTRY_DSN`` is absent — dev/local stays silent)
  * The Prometheus counter ``artifact_service_upstream_fallback_total`` and a
    helper that records all three signals (counter ↑, Sentry capture, WARN log)
    in one call so the call sites stay readable.

Why a service-local module?
  The counter must be a module-level singleton — Prometheus' default registry
  rejects duplicate metric names from re-imports.  Each microservice owns its
  own counter (different metric prefix → no clash when both services scrape
  ``/metrics`` from the same Prometheus instance).

Wire-up (see ``main.py``)::

    from .observability import init_sentry
    init_sentry()  # called from the FastAPI lifespan

Usage in the fallback path::

    from .observability import record_upstream_fallback

    try:
        ...
    except Exception as e:
        record_upstream_fallback(
            operation="runtime_invoke",
            exc=e,
            prompt_len=len(request.prompt),
        )
        # ... return the stub ...

Dashboards (deferred — see PR description for #461):
  * Grafana panel: ``sum by (operation, reason) (rate(artifact_service_upstream_fallback_total[5m]))``
  * Sentry: filter ``service:artifact_service`` and group by
    ``tags.operation``.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger("microservices.artifact_service.observability")

# ---------------------------------------------------------------------------
# Prometheus counter (module singleton)
# ---------------------------------------------------------------------------
#
# We prefer the shared ``isa_common.metrics.create_counter`` helper when it's
# available (it routes to the same registry the rest of the service uses).
# Production ships isa_common.metrics; in the slim dev/test build we fall back
# to a local ``prometheus_client.Counter`` so tests can still assert on it.

try:  # pragma: no cover - exercised in production
    from isa_common.metrics import create_counter  # type: ignore[attr-defined]

    upstream_fallback_total = create_counter(
        "artifact_service_upstream_fallback_total",
        "Number of times an upstream LLM/MCP call failed and the service fell back to a deterministic stub.",
        ["operation", "reason"],
    )
except Exception:  # pragma: no cover - dev/test path
    try:
        from prometheus_client import Counter

        upstream_fallback_total = Counter(
            "artifact_service_upstream_fallback_total",
            "Number of times an upstream LLM/MCP call failed and the service fell back to a deterministic stub.",
            ["operation", "reason"],
        )
    except Exception:  # last-ditch no-op so import never breaks the service

        class _NoopCounter:
            def labels(self, *_args: Any, **_kwargs: Any) -> "_NoopCounter":
                return self

            def inc(self, *_args: Any, **_kwargs: Any) -> None:
                return None

        upstream_fallback_total = _NoopCounter()


# ---------------------------------------------------------------------------
# Sentry init
# ---------------------------------------------------------------------------

_SENTRY_READY = False


def init_sentry(service_name: str = "artifact_service") -> bool:
    """Initialise sentry-sdk if ``SENTRY_DSN`` is set.  No-op otherwise.

    Idempotent — safe to call multiple times in tests / reloader workflows.
    Returns ``True`` when Sentry was actually initialised.
    """
    global _SENTRY_READY
    if _SENTRY_READY:
        return True

    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        logger.debug("SENTRY_DSN not set, Sentry disabled for %s", service_name)
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("SENTRY_ENV", "dev"),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
            integrations=[FastApiIntegration()],
        )
        sentry_sdk.set_tag("service", service_name)
        _SENTRY_READY = True
        logger.info("Sentry initialised for %s (env=%s)", service_name, os.getenv("SENTRY_ENV", "dev"))
        return True
    except Exception as e:  # pragma: no cover - defensive; never crash startup
        logger.warning("Failed to initialise Sentry for %s: %s", service_name, e)
        return False


# ---------------------------------------------------------------------------
# Reason classification
# ---------------------------------------------------------------------------


def classify_reason(exc: BaseException) -> str:
    """Bucket the exception into a small, low-cardinality ``reason`` label.

    Prometheus best practice: label cardinality must stay bounded, so we map
    the wide universe of exceptions to one of ``Timeout|HTTPError|ConnectionError|ParseError|Other``.
    """
    name = type(exc).__name__.lower()
    if "timeout" in name:
        return "Timeout"
    if "connection" in name or isinstance(exc, ConnectionError):
        return "ConnectionError"
    if "http" in name or "status" in name:
        return "HTTPError"
    if "json" in name or "decode" in name or "parse" in name or "valueerror" in name:
        return "ParseError"
    return "Other"


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------


def record_upstream_fallback(
    *,
    operation: str,
    exc: BaseException,
    service_name: str = "artifact_service",
    prompt_len: Optional[int] = None,
    extra: Optional[dict] = None,
) -> str:
    """Record a fallback firing across all three observability channels.

    1. ``upstream_fallback_total{operation, reason}`` counter += 1
    2. ``sentry_sdk.capture_exception(exc)`` — no-op when DSN absent
    3. Structured WARN log so devs can grep without Sentry.

    Returns the resolved ``reason`` label so callers can include it in their
    own structured logs / response headers if they want to.
    """
    reason = classify_reason(exc)
    try:
        upstream_fallback_total.labels(operation=operation, reason=reason).inc()
    except Exception as counter_err:  # pragma: no cover - defensive
        logger.debug("counter inc failed: %s", counter_err)

    # Sentry — capture_exception is a no-op when the SDK never initialised, so
    # this stays safe in dev/local.  We import lazily so the module stays
    # importable even when sentry-sdk isn't installed (e.g. slim test env).
    try:
        import sentry_sdk  # noqa: WPS433 - intentional lazy import

        with sentry_sdk.push_scope() as scope:
            scope.set_tag("service", service_name)
            scope.set_tag("operation", operation)
            scope.set_tag("fallback_reason", reason)
            if prompt_len is not None:
                scope.set_extra("prompt_len", prompt_len)
            if extra:
                for k, v in extra.items():
                    scope.set_extra(k, v)
            sentry_sdk.capture_exception(exc)
    except Exception as sentry_err:  # pragma: no cover - defensive
        logger.debug("sentry capture failed: %s", sentry_err)

    logger.warning(
        "fallback_fired service=%s operation=%s reason=%s prompt_len=%s exc=%s",
        service_name,
        operation,
        reason,
        prompt_len if prompt_len is not None else "n/a",
        exc,
    )
    return reason
