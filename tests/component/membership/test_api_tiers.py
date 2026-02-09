"""
Component Tests for Tier API

Tests tier status and progress endpoints.
"""

import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))


class TestGetTierStatusEndpoint:
    """Tests for GET /api/v1/memberships/{membership_id}/tier endpoint"""

    def test_get_tier_status_success(self, client, sample_membership):
        """Test getting tier status"""
        response = client.get(
            f"/api/v1/memberships/{sample_membership.membership_id}/tier"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["current_tier"]["tier_code"] == "bronze"
        assert data["tier_progress"] is not None

    def test_get_tier_status_not_found(self, client):
        """Test getting tier status for non-existent membership"""
        response = client.get("/api/v1/memberships/nonexistent/tier")

        assert response.status_code == 404

    def test_tier_includes_multiplier(self, client, gold_membership):
        """Test tier status includes multiplier"""
        response = client.get(
            f"/api/v1/memberships/{gold_membership.membership_id}/tier"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["current_tier"]["point_multiplier"] == 1.5

    def test_tier_includes_threshold(self, client, gold_membership):
        """Test tier status includes threshold"""
        response = client.get(
            f"/api/v1/memberships/{gold_membership.membership_id}/tier"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["current_tier"]["qualification_threshold"] == 20000

    def test_tier_includes_progress(self, client, sample_membership):
        """Test tier status includes progress"""
        response = client.get(
            f"/api/v1/memberships/{sample_membership.membership_id}/tier"
        )

        assert response.status_code == 200
        data = response.json()
        progress = data["tier_progress"]
        assert "current_tier_points" in progress
        assert "next_tier_threshold" in progress
        assert "points_to_next_tier" in progress
        assert "progress_percentage" in progress

    def test_tier_includes_benefits(self, client, gold_membership):
        """Test tier status includes benefits"""
        response = client.get(
            f"/api/v1/memberships/{gold_membership.membership_id}/tier"
        )

        assert response.status_code == 200
        data = response.json()
        assert "benefits" in data
        assert len(data["benefits"]) > 0


class TestTierProgression:
    """Tests for tier progression"""

    def test_bronze_progress_to_silver(self, client, sample_membership):
        """Test progress from bronze to silver"""
        response = client.get(
            f"/api/v1/memberships/{sample_membership.membership_id}/tier"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tier_progress"]["next_tier_threshold"] == 5000

    def test_diamond_at_max(self, client, mock_repository):
        """Test diamond tier at max progress"""
        import asyncio
        membership = asyncio.get_event_loop().run_until_complete(
            mock_repository.create_membership(
                user_id="diamond_user",
                tier_code="diamond",
                tier_points=150000
            )
        )

        response = client.get(
            f"/api/v1/memberships/{membership.membership_id}/tier"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tier_progress"]["points_to_next_tier"] == 0
        assert data["tier_progress"]["progress_percentage"] == 100.0
