"""
L1 Unit Tests for core/metrics.py

Tests the Prometheus metrics setup: path exclusion logic,
custom metric definitions, and setup_metrics configuration.
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


class TestCustomMetrics:
    """Test that custom metrics are properly defined."""

    def test_auth_failures_counter_exists(self):
        assert AUTH_FAILURES._name == "auth_failures"
        assert "service" in AUTH_FAILURES._labelnames
        assert "method" in AUTH_FAILURES._labelnames

    def test_business_operations_counter_exists(self):
        assert BUSINESS_OPERATIONS._name == "business_operations"
        assert "service" in BUSINESS_OPERATIONS._labelnames
        assert "operation" in BUSINESS_OPERATIONS._labelnames
        assert "status" in BUSINESS_OPERATIONS._labelnames

    def test_request_payload_histogram_exists(self):
        assert REQUEST_PAYLOAD_SIZE._name == "http_request_content_length_bytes"
        assert "service" in REQUEST_PAYLOAD_SIZE._labelnames


class TestExcludedPaths:
    """Test excluded paths configuration."""

    def test_health_in_excluded(self):
        assert "/health" in EXCLUDED_PATHS

    def test_health_detailed_in_excluded(self):
        assert "/health/detailed" in EXCLUDED_PATHS

    def test_metrics_in_excluded(self):
        assert "/metrics" in EXCLUDED_PATHS
