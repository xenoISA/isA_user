from __future__ import annotations

import importlib
import json
import sys
from types import ModuleType
from types import SimpleNamespace

import pytest


class _NoopMetric:
    def labels(self, *args, **kwargs):
        return self

    def inc(self, *args, **kwargs):
        return None

    def observe(self, *args, **kwargs):
        return None


def _install_isa_common_observability_stubs():
    if "isa_common.observability" not in sys.modules:
        observability = ModuleType("isa_common.observability")
        observability.setup_observability = lambda *args, **kwargs: {
            "metrics": False,
            "logging": False,
            "tracing": False,
        }
        sys.modules["isa_common.observability"] = observability

    if "isa_common.metrics" not in sys.modules:
        metrics = ModuleType("isa_common.metrics")
        metrics.setup_metrics = lambda *args, **kwargs: {
            "metrics": False,
            "logging": False,
            "tracing": False,
        }
        metrics.create_counter = lambda *args, **kwargs: _NoopMetric()
        metrics.create_histogram = lambda *args, **kwargs: _NoopMetric()
        metrics.create_gauge = lambda *args, **kwargs: _NoopMetric()
        metrics.metrics_text = lambda: b""
        sys.modules["isa_common.metrics"] = metrics


_install_isa_common_observability_stubs()

billing_main = importlib.import_module("microservices.billing_service.main")


class AsyncHealthyDB:
    async def health_check(self):
        return True


class AsyncUnhealthyDB:
    async def health_check(self):
        return None


@pytest.mark.asyncio
async def test_health_check_awaits_async_database_health():
    original_repository = billing_main.repository
    billing_main.repository = SimpleNamespace(db=AsyncHealthyDB())
    try:
        response = await billing_main.health_check()
    finally:
        billing_main.repository = original_repository

    body = json.loads(response.body)
    assert response.status_code == 200
    assert body["status"] == "degraded"
    assert body["dependencies"]["postgres"]["status"] == "healthy"
    assert body["dependencies"]["nats"]["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_health_check_reports_unhealthy_when_async_database_fails():
    original_repository = billing_main.repository
    billing_main.repository = SimpleNamespace(db=AsyncUnhealthyDB())
    try:
        response = await billing_main.health_check()
    finally:
        billing_main.repository = original_repository

    body = json.loads(response.body)
    assert response.status_code == 503
    assert body["status"] == "unhealthy"
    assert body["dependencies"]["postgres"]["status"] == "unhealthy"
