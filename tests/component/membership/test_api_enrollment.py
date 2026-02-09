"""
Component Tests for Membership Enrollment API

Tests enrollment endpoints with mocked dependencies.
"""

import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))


class TestEnrollmentEndpoint:
    """Tests for POST /api/v1/memberships endpoint"""

    def test_enroll_membership_success(self, client):
        """Test successful enrollment"""
        response = client.post(
            "/api/v1/memberships",
            json={"user_id": "new_user_123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["membership"]["user_id"] == "new_user_123"
        assert data["membership"]["tier_code"] == "bronze"

    def test_enroll_with_promo_code(self, client):
        """Test enrollment with promo code"""
        response = client.post(
            "/api/v1/memberships",
            json={
                "user_id": "promo_user",
                "promo_code": "WELCOME100"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["enrollment_bonus"] == 100
        assert data["membership"]["points_balance"] == 100

    def test_enroll_with_organization(self, client):
        """Test enrollment with organization"""
        response = client.post(
            "/api/v1/memberships",
            json={
                "user_id": "org_user",
                "organization_id": "org_123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["membership"]["organization_id"] == "org_123"

    def test_enroll_with_enrollment_source(self, client):
        """Test enrollment with source tracking"""
        response = client.post(
            "/api/v1/memberships",
            json={
                "user_id": "source_user",
                "enrollment_source": "mobile_app"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["membership"]["enrollment_source"] == "mobile_app"

    def test_enroll_with_metadata(self, client):
        """Test enrollment with metadata"""
        response = client.post(
            "/api/v1/memberships",
            json={
                "user_id": "meta_user",
                "metadata": {"campaign": "summer2025"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["membership"]["metadata"]["campaign"] == "summer2025"

    def test_enroll_duplicate_fails(self, client):
        """Test duplicate enrollment fails with 409"""
        # First enrollment
        client.post("/api/v1/memberships", json={"user_id": "dup_user"})

        # Second enrollment should fail
        response = client.post(
            "/api/v1/memberships",
            json={"user_id": "dup_user"}
        )

        assert response.status_code == 409
        assert "already has active" in response.json()["detail"].lower()

    def test_enroll_missing_user_id(self, client):
        """Test enrollment without user_id fails"""
        response = client.post(
            "/api/v1/memberships",
            json={}
        )

        assert response.status_code == 422  # Validation error

    def test_enroll_empty_user_id(self, client):
        """Test enrollment with empty user_id fails"""
        response = client.post(
            "/api/v1/memberships",
            json={"user_id": ""}
        )

        assert response.status_code == 422


class TestEnrollmentValidation:
    """Tests for enrollment input validation"""

    def test_promo_code_max_length(self, client):
        """Test promo code respects max length"""
        response = client.post(
            "/api/v1/memberships",
            json={
                "user_id": "length_user",
                "promo_code": "A" * 100  # Very long promo code
            }
        )

        # Should fail validation
        assert response.status_code == 422

    def test_enrollment_source_max_length(self, client):
        """Test enrollment source respects max length"""
        response = client.post(
            "/api/v1/memberships",
            json={
                "user_id": "source_length_user",
                "enrollment_source": "A" * 100
            }
        )

        # Should fail validation
        assert response.status_code == 422

    def test_user_id_min_length(self, client):
        """Test user_id requires minimum length"""
        response = client.post(
            "/api/v1/memberships",
            json={"user_id": ""}
        )

        assert response.status_code == 422


class TestEnrollmentPromos:
    """Tests for different promo codes"""

    def test_welcome100_promo(self, client):
        """Test WELCOME100 promo gives 100 points"""
        response = client.post(
            "/api/v1/memberships",
            json={"user_id": "w100_user", "promo_code": "WELCOME100"}
        )

        assert response.status_code == 200
        assert response.json()["enrollment_bonus"] == 100

    def test_welcome500_promo(self, client):
        """Test WELCOME500 promo gives 500 points"""
        response = client.post(
            "/api/v1/memberships",
            json={"user_id": "w500_user", "promo_code": "WELCOME500"}
        )

        assert response.status_code == 200
        assert response.json()["enrollment_bonus"] == 500

    def test_vip1000_promo(self, client):
        """Test VIP1000 promo gives 1000 points"""
        response = client.post(
            "/api/v1/memberships",
            json={"user_id": "vip_user", "promo_code": "VIP1000"}
        )

        assert response.status_code == 200
        assert response.json()["enrollment_bonus"] == 1000

    def test_invalid_promo_gives_zero(self, client):
        """Test invalid promo code gives 0 bonus"""
        response = client.post(
            "/api/v1/memberships",
            json={"user_id": "invalid_promo_user", "promo_code": "NOTREAL"}
        )

        assert response.status_code == 200
        assert response.json()["enrollment_bonus"] == 0

    def test_lowercase_promo(self, client):
        """Test lowercase promo code works"""
        response = client.post(
            "/api/v1/memberships",
            json={"user_id": "lower_promo_user", "promo_code": "welcome100"}
        )

        assert response.status_code == 200
        assert response.json()["enrollment_bonus"] == 100
