"""
Component Tests for Points API

Tests points earning, redemption, and balance endpoints.
"""

import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))


class TestEarnPointsEndpoint:
    """Tests for POST /api/v1/memberships/points/earn endpoint"""

    def test_earn_points_success(self, client, sample_membership):
        """Test earning points successfully"""
        response = client.post(
            "/api/v1/memberships/points/earn",
            json={
                "user_id": "test_user_123",
                "points_amount": 500,
                "source": "order_completed"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["points_earned"] == 500

    def test_earn_points_with_reference(self, client, sample_membership):
        """Test earning points with reference ID"""
        response = client.post(
            "/api/v1/memberships/points/earn",
            json={
                "user_id": "test_user_123",
                "points_amount": 200,
                "source": "order",
                "reference_id": "order_12345"
            }
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_earn_points_with_description(self, client, sample_membership):
        """Test earning points with description"""
        response = client.post(
            "/api/v1/memberships/points/earn",
            json={
                "user_id": "test_user_123",
                "points_amount": 100,
                "source": "bonus",
                "description": "Birthday bonus"
            }
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_earn_points_no_membership(self, client):
        """Test earning points without membership fails"""
        response = client.post(
            "/api/v1/memberships/points/earn",
            json={
                "user_id": "nonexistent_user",
                "points_amount": 100,
                "source": "test"
            }
        )

        assert response.status_code == 404

    def test_earn_points_zero_amount(self, client, sample_membership):
        """Test earning 0 points fails validation"""
        response = client.post(
            "/api/v1/memberships/points/earn",
            json={
                "user_id": "test_user_123",
                "points_amount": 0,
                "source": "test"
            }
        )

        assert response.status_code == 422

    def test_earn_points_negative_amount(self, client, sample_membership):
        """Test earning negative points fails validation"""
        response = client.post(
            "/api/v1/memberships/points/earn",
            json={
                "user_id": "test_user_123",
                "points_amount": -100,
                "source": "test"
            }
        )

        assert response.status_code == 422

    def test_earn_points_missing_source(self, client, sample_membership):
        """Test earning points without source fails"""
        response = client.post(
            "/api/v1/memberships/points/earn",
            json={
                "user_id": "test_user_123",
                "points_amount": 100
            }
        )

        assert response.status_code == 422


class TestRedeemPointsEndpoint:
    """Tests for POST /api/v1/memberships/points/redeem endpoint"""

    def test_redeem_points_success(self, client, sample_membership):
        """Test redeeming points successfully"""
        response = client.post(
            "/api/v1/memberships/points/redeem",
            json={
                "user_id": "test_user_123",
                "points_amount": 500,
                "reward_code": "DISCOUNT_10"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["points_redeemed"] == 500
        assert data["points_balance"] == 500  # 1000 - 500

    def test_redeem_all_points(self, client, sample_membership):
        """Test redeeming all points"""
        response = client.post(
            "/api/v1/memberships/points/redeem",
            json={
                "user_id": "test_user_123",
                "points_amount": 1000,
                "reward_code": "FULL_REDEEM"
            }
        )

        assert response.status_code == 200
        assert response.json()["points_balance"] == 0

    def test_redeem_insufficient_points(self, client, sample_membership):
        """Test redeeming more points than available"""
        response = client.post(
            "/api/v1/memberships/points/redeem",
            json={
                "user_id": "test_user_123",
                "points_amount": 2000,  # Only has 1000
                "reward_code": "BIG_DISCOUNT"
            }
        )

        assert response.status_code == 402  # Payment Required
        assert "insufficient" in response.json()["detail"].lower()

    def test_redeem_no_membership(self, client):
        """Test redeeming without membership"""
        response = client.post(
            "/api/v1/memberships/points/redeem",
            json={
                "user_id": "nonexistent",
                "points_amount": 100,
                "reward_code": "DISCOUNT"
            }
        )

        assert response.status_code == 404

    def test_redeem_zero_points(self, client, sample_membership):
        """Test redeeming 0 points fails validation"""
        response = client.post(
            "/api/v1/memberships/points/redeem",
            json={
                "user_id": "test_user_123",
                "points_amount": 0,
                "reward_code": "DISCOUNT"
            }
        )

        assert response.status_code == 422


class TestGetPointsBalanceEndpoint:
    """Tests for GET /api/v1/memberships/points/balance endpoint"""

    def test_get_balance_success(self, client, sample_membership):
        """Test getting points balance"""
        response = client.get(
            "/api/v1/memberships/points/balance",
            params={"user_id": "test_user_123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["balance"]["points_balance"] == 1000

    def test_get_balance_includes_tier(self, client, sample_membership):
        """Test balance includes tier information"""
        response = client.get(
            "/api/v1/memberships/points/balance",
            params={"user_id": "test_user_123"}
        )

        assert response.status_code == 200
        assert response.json()["balance"]["tier_code"] == "bronze"

    def test_get_balance_no_membership(self, client):
        """Test getting balance without membership"""
        response = client.get(
            "/api/v1/memberships/points/balance",
            params={"user_id": "nonexistent"}
        )

        assert response.status_code == 404

    def test_get_balance_missing_user_id(self, client):
        """Test getting balance without user_id"""
        response = client.get("/api/v1/memberships/points/balance")

        assert response.status_code == 422

    def test_get_balance_with_organization(self, client, mock_repository):
        """Test getting balance with organization"""
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            mock_repository.create_membership(
                user_id="org_balance_user",
                tier_code="bronze",
                organization_id="org_123",
                points_balance=2000
            )
        )

        response = client.get(
            "/api/v1/memberships/points/balance",
            params={
                "user_id": "org_balance_user",
                "organization_id": "org_123"
            }
        )

        assert response.status_code == 200
        assert response.json()["balance"]["points_balance"] == 2000


class TestPointsWithTierMultiplier:
    """Tests for points earning with tier multipliers"""

    def test_gold_tier_multiplier(self, client, gold_membership):
        """Test gold tier gets 1.5x multiplier"""
        response = client.post(
            "/api/v1/memberships/points/earn",
            json={
                "user_id": "gold_user_123",
                "points_amount": 1000,
                "source": "order"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["multiplier"] == 1.5
        assert data["points_earned"] == 1500
