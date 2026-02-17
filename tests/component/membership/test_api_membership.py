"""
Component Tests for Membership Management API

Tests get, list, cancel, suspend, reactivate endpoints.
"""

import pytest
from fastapi.testclient import TestClient
import asyncio

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))


class TestGetMembershipEndpoint:
    """Tests for GET /api/v1/memberships/{membership_id} endpoint"""

    def test_get_membership_success(self, client, sample_membership):
        """Test getting membership by ID"""
        response = client.get(
            f"/api/v1/memberships/{sample_membership.membership_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["membership"]["membership_id"] == sample_membership.membership_id

    def test_get_membership_not_found(self, client):
        """Test getting non-existent membership"""
        response = client.get("/api/v1/memberships/nonexistent_id")

        assert response.status_code == 404


class TestGetMembershipByUserEndpoint:
    """Tests for GET /api/v1/memberships/user/{user_id} endpoint"""

    def test_get_by_user_success(self, client, sample_membership):
        """Test getting membership by user ID"""
        response = client.get("/api/v1/memberships/user/test_user_123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["membership"]["user_id"] == "test_user_123"

    def test_get_by_user_not_found(self, client):
        """Test getting membership for user without membership"""
        response = client.get("/api/v1/memberships/user/nonexistent_user")

        assert response.status_code == 404


class TestListMembershipsEndpoint:
    """Tests for GET /api/v1/memberships endpoint"""

    def test_list_memberships_success(self, client, sample_membership, gold_membership):
        """Test listing memberships"""
        response = client.get("/api/v1/memberships")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["memberships"]) >= 2

    def test_list_by_user(self, client, sample_membership):
        """Test listing by user ID"""
        response = client.get(
            "/api/v1/memberships",
            params={"user_id": "test_user_123"}
        )

        assert response.status_code == 200
        data = response.json()
        for m in data["memberships"]:
            assert m["user_id"] == "test_user_123"

    def test_list_by_tier(self, client, gold_membership):
        """Test listing by tier"""
        response = client.get(
            "/api/v1/memberships",
            params={"tier_code": "gold"}
        )

        assert response.status_code == 200
        data = response.json()
        for m in data["memberships"]:
            assert m["tier_code"] == "gold"

    def test_list_pagination(self, client, mock_repository):
        """Test listing with pagination"""
        # Create multiple memberships
        for i in range(10):
            asyncio.get_event_loop().run_until_complete(
                mock_repository.create_membership(
                    user_id=f"page_user_{i}",
                    tier_code="bronze"
                )
            )

        response = client.get(
            "/api/v1/memberships",
            params={"page": 1, "page_size": 5}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["memberships"]) == 5
        assert data["page"] == 1
        assert data["page_size"] == 5


class TestCancelMembershipEndpoint:
    """Tests for POST /api/v1/memberships/{membership_id}/cancel endpoint"""

    def test_cancel_membership_success(self, client, sample_membership):
        """Test canceling membership"""
        response = client.post(
            f"/api/v1/memberships/{sample_membership.membership_id}/cancel",
            json={"reason": "Moving to another service"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["membership"]["status"] == "canceled"

    def test_cancel_not_found(self, client):
        """Test canceling non-existent membership"""
        response = client.post(
            "/api/v1/memberships/nonexistent/cancel",
            json={"reason": "Test"}
        )

        assert response.status_code == 404

    def test_cancel_with_feedback(self, client, sample_membership):
        """Test canceling with feedback"""
        response = client.post(
            f"/api/v1/memberships/{sample_membership.membership_id}/cancel",
            json={
                "reason": "Moving",
                "feedback": "Great service!"
            }
        )

        assert response.status_code == 200

    def test_cancel_forfeit_points(self, client, sample_membership):
        """Test canceling with points forfeiture"""
        response = client.post(
            f"/api/v1/memberships/{sample_membership.membership_id}/cancel",
            json={
                "reason": "Account closure",
                "forfeit_points": True
            }
        )

        assert response.status_code == 200


class TestSuspendMembershipEndpoint:
    """Tests for PUT /api/v1/memberships/{membership_id}/suspend endpoint"""

    def test_suspend_membership_success(self, client, sample_membership):
        """Test suspending membership"""
        response = client.put(
            f"/api/v1/memberships/{sample_membership.membership_id}/suspend",
            json={"reason": "Policy violation"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["membership"]["status"] == "suspended"

    def test_suspend_not_found(self, client):
        """Test suspending non-existent membership"""
        response = client.put(
            "/api/v1/memberships/nonexistent/suspend",
            json={"reason": "Test"}
        )

        assert response.status_code == 404

    def test_suspend_with_duration(self, client, sample_membership):
        """Test suspending with duration"""
        response = client.put(
            f"/api/v1/memberships/{sample_membership.membership_id}/suspend",
            json={
                "reason": "Temporary suspension",
                "duration_days": 30
            }
        )

        assert response.status_code == 200

    def test_suspend_missing_reason(self, client, sample_membership):
        """Test suspending without reason fails"""
        response = client.put(
            f"/api/v1/memberships/{sample_membership.membership_id}/suspend",
            json={}
        )

        assert response.status_code == 422


class TestReactivateMembershipEndpoint:
    """Tests for PUT /api/v1/memberships/{membership_id}/reactivate endpoint"""

    def test_reactivate_suspended_success(self, client, sample_membership, mock_repository):
        """Test reactivating suspended membership"""
        # First suspend
        from microservices.membership_service.models import MembershipStatus
        asyncio.get_event_loop().run_until_complete(
            mock_repository.update_status(
                sample_membership.membership_id,
                MembershipStatus.SUSPENDED
            )
        )

        response = client.put(
            f"/api/v1/memberships/{sample_membership.membership_id}/reactivate"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["membership"]["status"] == "active"

    def test_reactivate_not_found(self, client):
        """Test reactivating non-existent membership"""
        response = client.put("/api/v1/memberships/nonexistent/reactivate")

        assert response.status_code == 404

    def test_reactivate_active_fails(self, client, sample_membership):
        """Test reactivating already active membership fails"""
        response = client.put(
            f"/api/v1/memberships/{sample_membership.membership_id}/reactivate"
        )

        assert response.status_code == 400
