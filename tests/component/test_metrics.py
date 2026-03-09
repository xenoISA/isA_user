"""
L2 Component Tests for core/metrics.py

Tests setup_metrics with a real FastAPI app: endpoint exposure,
instrumentation of requests, and metric content via isa_common.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.metrics import setup_metrics


@pytest.fixture(scope="module")
def metrics_app():
    """Create a FastAPI app with observability enabled."""
    app = FastAPI()

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"status": "ok"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    setup_metrics(app, "test_service")
    return app


@pytest.fixture(scope="module")
def client(metrics_app):
    return TestClient(metrics_app)


class TestMetricsEndpoint:
    """Test /metrics endpoint exposure."""

    def test_metrics_endpoint_exists(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type(self, client):
        response = client.get("/metrics")
        content_type = response.headers["content-type"]
        assert "text/plain" in content_type or "openmetrics" in content_type

    def test_metrics_contains_process_info(self, client):
        response = client.get("/metrics")
        body = response.text
        assert "process_" in body or "python_" in body

    def test_metrics_contains_service_info(self, client):
        response = client.get("/metrics")
        body = response.text
        assert "isa_test_service_service_info" in body


class TestInstrumentation:
    """Test that HTTP requests are instrumented."""

    def test_request_generates_metrics(self, client):
        client.get("/api/v1/test")
        response = client.get("/metrics")
        body = response.text
        assert "http_request" in body

    def test_health_not_instrumented(self, client):
        for _ in range(5):
            client.get("/health")
        response = client.get("/metrics")
        body = response.text
        lines = [l for l in body.split("\n") if "/health" in l and "http_request" in l.lower()]
        assert len(lines) == 0


class TestSetupReturn:
    """Test that setup_metrics returns observability result."""

    def test_returns_dict(self):
        app = FastAPI()
        result = setup_metrics(app, "return_test_service")
        assert isinstance(result, dict)
        assert "metrics" in result
        assert "tracing" in result
        assert "logging" in result
