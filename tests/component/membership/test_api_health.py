"""
Component Tests for Health Check API

Tests health and info endpoints.
"""

import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))


class TestHealthEndpoint:
    """Tests for /health endpoint"""

    def test_health_check_success(self, client):
        """Test health check endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["service"] == "membership_service"
        assert "version" in data
        assert "dependencies" in data

    def test_health_includes_port(self, client):
        """Test health includes port"""
        response = client.get("/health")

        assert response.status_code == 200
        assert "port" in response.json()


class TestServiceInfoEndpoint:
    """Tests for /api/v1/memberships/info endpoint"""

    def test_service_info_success(self, client):
        """Test service info endpoint"""
        response = client.get("/api/v1/memberships/info")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "membership_service"
        assert data["version"] == "1.0.0"
        assert "capabilities" in data
        assert len(data["capabilities"]) > 0

    def test_service_info_includes_description(self, client):
        """Test service info includes description"""
        response = client.get("/api/v1/memberships/info")

        assert response.status_code == 200
        assert "description" in response.json()


class TestStatsEndpoint:
    """Tests for GET /api/v1/memberships/stats endpoint"""

    def test_get_stats_success(self, client):
        """Test getting stats"""
        response = client.get("/api/v1/memberships/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_memberships" in data
        assert "active_memberships" in data
        assert "tier_distribution" in data

    def test_stats_with_data(self, client, sample_membership, gold_membership):
        """Test stats with membership data"""
        response = client.get("/api/v1/memberships/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_memberships"] >= 2
        assert data["active_memberships"] >= 2
