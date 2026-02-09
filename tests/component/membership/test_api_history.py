"""
Component Tests for History API

Tests history retrieval endpoints.
"""

import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))


class TestGetHistoryEndpoint:
    """Tests for GET /api/v1/memberships/{membership_id}/history endpoint"""

    def test_get_history_success(self, client, sample_membership, mock_repository):
        """Test getting history"""
        # Add some history
        import asyncio
        from microservices.membership_service.models import PointAction

        asyncio.get_event_loop().run_until_complete(
            mock_repository.add_history(
                sample_membership.membership_id,
                PointAction.POINTS_EARNED,
                points_change=100
            )
        )

        response = client.get(
            f"/api/v1/memberships/{sample_membership.membership_id}/history"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["history"]) >= 1

    def test_get_history_filter_by_action(self, client, sample_membership, mock_repository):
        """Test filtering history by action"""
        import asyncio
        from microservices.membership_service.models import PointAction

        # Add different action types
        asyncio.get_event_loop().run_until_complete(
            mock_repository.add_history(
                sample_membership.membership_id,
                PointAction.POINTS_EARNED,
                points_change=100
            )
        )
        asyncio.get_event_loop().run_until_complete(
            mock_repository.add_history(
                sample_membership.membership_id,
                PointAction.POINTS_REDEEMED,
                points_change=-50
            )
        )

        response = client.get(
            f"/api/v1/memberships/{sample_membership.membership_id}/history",
            params={"action": "points_earned"}
        )

        assert response.status_code == 200
        data = response.json()
        for entry in data["history"]:
            assert entry["action"] == "points_earned"

    def test_get_history_pagination(self, client, sample_membership, mock_repository):
        """Test history pagination"""
        import asyncio
        from microservices.membership_service.models import PointAction

        # Add many history entries
        for i in range(15):
            asyncio.get_event_loop().run_until_complete(
                mock_repository.add_history(
                    sample_membership.membership_id,
                    PointAction.POINTS_EARNED,
                    points_change=i * 10
                )
            )

        response = client.get(
            f"/api/v1/memberships/{sample_membership.membership_id}/history",
            params={"page": 1, "page_size": 5}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["history"]) == 5
        assert data["page"] == 1
        assert data["page_size"] == 5

    def test_get_history_total_count(self, client, sample_membership, mock_repository):
        """Test history returns total count"""
        import asyncio
        from microservices.membership_service.models import PointAction

        for i in range(10):
            asyncio.get_event_loop().run_until_complete(
                mock_repository.add_history(
                    sample_membership.membership_id,
                    PointAction.POINTS_EARNED,
                    points_change=100
                )
            )

        response = client.get(
            f"/api/v1/memberships/{sample_membership.membership_id}/history"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 10


class TestHistoryEntryDetails:
    """Tests for history entry details"""

    def test_history_includes_points_change(self, client, sample_membership, mock_repository):
        """Test history includes points change"""
        import asyncio
        from microservices.membership_service.models import PointAction

        asyncio.get_event_loop().run_until_complete(
            mock_repository.add_history(
                sample_membership.membership_id,
                PointAction.POINTS_EARNED,
                points_change=500
            )
        )

        response = client.get(
            f"/api/v1/memberships/{sample_membership.membership_id}/history"
        )

        assert response.status_code == 200
        data = response.json()
        earned = [h for h in data["history"] if h["action"] == "points_earned"]
        assert len(earned) > 0
        assert earned[0]["points_change"] == 500

    def test_history_includes_action_type(self, client, sample_membership, mock_repository):
        """Test history includes action type"""
        import asyncio
        from microservices.membership_service.models import PointAction

        asyncio.get_event_loop().run_until_complete(
            mock_repository.add_history(
                sample_membership.membership_id,
                PointAction.TIER_UPGRADED,
                previous_tier="bronze",
                new_tier="silver"
            )
        )

        response = client.get(
            f"/api/v1/memberships/{sample_membership.membership_id}/history"
        )

        assert response.status_code == 200
        data = response.json()
        upgraded = [h for h in data["history"] if h["action"] == "tier_upgraded"]
        assert len(upgraded) > 0
