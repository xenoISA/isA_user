"""
Component Tests for Benefits API

Tests benefits listing and usage endpoints.
"""

import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))


class TestGetBenefitsEndpoint:
    """Tests for GET /api/v1/memberships/{membership_id}/benefits endpoint"""

    def test_get_benefits_success(self, client, gold_membership):
        """Test getting benefits"""
        response = client.get(
            f"/api/v1/memberships/{gold_membership.membership_id}/benefits"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["benefits"]) > 0
        assert data["tier_code"] == "gold"

    def test_get_benefits_not_found(self, client):
        """Test getting benefits for non-existent membership"""
        response = client.get("/api/v1/memberships/nonexistent/benefits")

        assert response.status_code == 404

    def test_get_benefits_bronze_tier(self, client, sample_membership):
        """Test getting benefits for bronze tier"""
        response = client.get(
            f"/api/v1/memberships/{sample_membership.membership_id}/benefits"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tier_code"] == "bronze"

    def test_benefits_include_usage_info(self, client, gold_membership):
        """Test benefits include usage information"""
        response = client.get(
            f"/api/v1/memberships/{gold_membership.membership_id}/benefits"
        )

        assert response.status_code == 200
        data = response.json()
        for benefit in data["benefits"]:
            assert "used_count" in benefit
            assert "is_available" in benefit


class TestUseBenefitEndpoint:
    """Tests for POST /api/v1/memberships/{membership_id}/benefits/use endpoint"""

    def test_use_benefit_success(self, client, gold_membership):
        """Test using a benefit"""
        response = client.post(
            f"/api/v1/memberships/{gold_membership.membership_id}/benefits/use",
            json={"benefit_code": "FREE_SHIPPING"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["benefit_code"] == "FREE_SHIPPING"

    def test_use_benefit_not_found(self, client):
        """Test using benefit with non-existent membership"""
        response = client.post(
            "/api/v1/memberships/nonexistent/benefits/use",
            json={"benefit_code": "FREE_SHIPPING"}
        )

        assert response.status_code == 404

    def test_use_benefit_not_available(self, client, sample_membership):
        """Test using benefit not available at tier"""
        response = client.post(
            f"/api/v1/memberships/{sample_membership.membership_id}/benefits/use",
            json={"benefit_code": "EARLY_ACCESS"}  # Not available for bronze
        )

        assert response.status_code == 403
        assert "not available" in response.json()["detail"].lower()

    def test_use_benefit_missing_code(self, client, gold_membership):
        """Test using benefit without code"""
        response = client.post(
            f"/api/v1/memberships/{gold_membership.membership_id}/benefits/use",
            json={}
        )

        assert response.status_code == 422

    def test_use_benefit_returns_remaining(self, client, mock_repository):
        """Test benefit usage returns remaining uses"""
        import asyncio
        membership = asyncio.get_event_loop().run_until_complete(
            mock_repository.create_membership(
                user_id="remaining_test_user",
                tier_code="silver"
            )
        )

        response = client.post(
            f"/api/v1/memberships/{membership.membership_id}/benefits/use",
            json={"benefit_code": "FREE_SHIPPING"}  # Limit 3 for silver
        )

        assert response.status_code == 200
        data = response.json()
        assert data["remaining_uses"] == 2

    def test_use_benefit_limit_exceeded(self, client, mock_repository):
        """Test benefit usage limit exceeded"""
        import asyncio
        membership = asyncio.get_event_loop().run_until_complete(
            mock_repository.create_membership(
                user_id="limit_test_user",
                tier_code="silver"
            )
        )

        # Use benefit 3 times (limit is 3)
        for i in range(3):
            response = client.post(
                f"/api/v1/memberships/{membership.membership_id}/benefits/use",
                json={"benefit_code": "FREE_SHIPPING"}
            )
            assert response.status_code == 200

        # 4th use should fail
        response = client.post(
            f"/api/v1/memberships/{membership.membership_id}/benefits/use",
            json={"benefit_code": "FREE_SHIPPING"}
        )

        assert response.status_code == 403
        assert "limit exceeded" in response.json()["detail"].lower()


class TestBenefitTypes:
    """Tests for different benefit types"""

    def test_service_benefit(self, client, gold_membership):
        """Test service type benefit available"""
        response = client.get(
            f"/api/v1/memberships/{gold_membership.membership_id}/benefits"
        )

        assert response.status_code == 200
        service_benefits = [b for b in response.json()["benefits"] if b["benefit_type"] == "service"]
        assert len(service_benefits) > 0

    def test_discount_benefit(self, client, gold_membership):
        """Test discount type benefit available"""
        response = client.get(
            f"/api/v1/memberships/{gold_membership.membership_id}/benefits"
        )

        assert response.status_code == 200
        discount_benefits = [b for b in response.json()["benefits"] if b["benefit_type"] == "discount"]
        assert len(discount_benefits) > 0

    def test_access_benefit(self, client, gold_membership):
        """Test access type benefit available"""
        response = client.get(
            f"/api/v1/memberships/{gold_membership.membership_id}/benefits"
        )

        assert response.status_code == 200
        access_benefits = [b for b in response.json()["benefits"] if b["benefit_type"] == "access"]
        assert len(access_benefits) > 0
