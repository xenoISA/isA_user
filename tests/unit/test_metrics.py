"""
L1 Unit Tests for core/metrics.py

Tests the observability wrapper: path exclusion logic,
domain-specific metric definitions using isa_common.
"""

import pytest

from core.metrics import (
    EXCLUDED_PATHS,
    _should_instrument,
    AUTH_FAILURES,
    BUSINESS_OPERATIONS,
    REQUEST_PAYLOAD_SIZE,
)


class TestShouldInstrument:
    """Test path exclusion logic."""

    def test_regular_path_instrumented(self):
        assert _should_instrument("/api/v1/tasks") is True

    def test_health_excluded(self):
        assert _should_instrument("/health") is False

    def test_health_detailed_excluded(self):
        assert _should_instrument("/health/detailed") is False

    def test_metrics_excluded(self):
        assert _should_instrument("/metrics") is False

    def test_health_subpath_excluded(self):
        assert _should_instrument("/health/ready") is False

    def test_root_path_instrumented(self):
        assert _should_instrument("/") is True

    def test_similar_path_not_excluded(self):
        assert _should_instrument("/healthy") is True
        assert _should_instrument("/api/v1/metrics-data") is True

    def test_ready_excluded(self):
        assert _should_instrument("/ready") is False

    def test_live_excluded(self):
        assert _should_instrument("/live") is False


class TestCustomMetrics:
    """Test that domain-specific metrics are created via isa_common."""

    def test_auth_failures_has_labels(self):
        labeled = AUTH_FAILURES.labels(service="test", method="token")
        assert labeled is not None

    def test_business_operations_has_labels(self):
        labeled = BUSINESS_OPERATIONS.labels(service="test", operation="create", status="ok")
        assert labeled is not None

    def test_request_payload_has_labels(self):
        labeled = REQUEST_PAYLOAD_SIZE.labels(service="test")
        assert labeled is not None


class TestExcludedPaths:
    """Test excluded paths configuration."""

    def test_health_in_excluded(self):
        assert "/health" in EXCLUDED_PATHS

    def test_health_detailed_in_excluded(self):
        assert "/health/detailed" in EXCLUDED_PATHS

    def test_metrics_in_excluded(self):
        assert "/metrics" in EXCLUDED_PATHS

    def test_ready_in_excluded(self):
        assert "/ready" in EXCLUDED_PATHS

    def test_live_in_excluded(self):
        assert "/live" in EXCLUDED_PATHS
