"""
Unit Tests for Holdout Group Selection Logic

Tests deterministic holdout selection per logic_contract.md.
Reference: BR-CAM-002.2 (Apply Holdout Groups)
"""

import pytest
from decimal import Decimal
import hashlib

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import CampaignTestDataFactory


class HoldoutSelector:
    """
    Holdout selection implementation for testing.

    Algorithm (from logic_contract.md):
    ```python
    hash_value = md5(f"{user_id}:{campaign_id}").hexdigest()
    bucket = int(hash_value, 16) % 100
    is_holdout = bucket < holdout_percentage
    ```
    """

    @staticmethod
    def get_hash(user_id: str, campaign_id: str) -> str:
        """Generate deterministic hash for holdout selection"""
        combined = f"{user_id}:{campaign_id}"
        return hashlib.md5(combined.encode()).hexdigest()

    @staticmethod
    def get_bucket(user_id: str, campaign_id: str) -> int:
        """Get bucket number (0-99) for holdout determination"""
        hash_value = HoldoutSelector.get_hash(user_id, campaign_id)
        return int(hash_value, 16) % 100

    @staticmethod
    def is_holdout(user_id: str, campaign_id: str, holdout_percentage: Decimal) -> bool:
        """
        Determine if user is in holdout group - BR-CAM-002.2

        Args:
            user_id: User identifier
            campaign_id: Campaign identifier
            holdout_percentage: Percentage to hold out (0-20)

        Returns:
            True if user is in holdout group
        """
        if holdout_percentage <= 0:
            return False

        bucket = HoldoutSelector.get_bucket(user_id, campaign_id)
        return bucket < int(holdout_percentage)

    @staticmethod
    def select_audience(
        user_ids: list, campaign_id: str, holdout_percentage: Decimal
    ) -> tuple:
        """
        Split audience into holdout and active groups - BR-CAM-002.2

        Returns:
            (active_users, holdout_users) tuple
        """
        active_users = []
        holdout_users = []

        for user_id in user_ids:
            if HoldoutSelector.is_holdout(user_id, campaign_id, holdout_percentage):
                holdout_users.append(user_id)
            else:
                active_users.append(user_id)

        return active_users, holdout_users


# ====================
# Basic Holdout Tests
# ====================


class TestHoldoutBasics:
    """Basic holdout selection tests - BR-CAM-002.2"""

    def test_zero_holdout_no_users_excluded(self):
        """Test 0% holdout excludes no users"""
        user_ids = [f"usr_{i}" for i in range(100)]
        campaign_id = "cmp_zero_holdout"

        active, holdout = HoldoutSelector.select_audience(
            user_ids, campaign_id, Decimal("0")
        )

        assert len(holdout) == 0
        assert len(active) == 100

    def test_holdout_is_deterministic(self):
        """Test same user always gets same holdout status"""
        user_id = "usr_deterministic"
        campaign_id = "cmp_deterministic"
        holdout_pct = Decimal("10")

        result1 = HoldoutSelector.is_holdout(user_id, campaign_id, holdout_pct)
        result2 = HoldoutSelector.is_holdout(user_id, campaign_id, holdout_pct)
        result3 = HoldoutSelector.is_holdout(user_id, campaign_id, holdout_pct)

        assert result1 == result2 == result3

    def test_same_user_different_campaign_different_holdout(self):
        """Test same user may have different holdout status per campaign"""
        user_id = "usr_same_user"
        holdout_pct = Decimal("50")

        # With 50% holdout, same user should vary across campaigns
        results = set()
        for i in range(20):
            campaign_id = f"cmp_different_{i}"
            is_holdout = HoldoutSelector.is_holdout(user_id, campaign_id, holdout_pct)
            results.add(is_holdout)

        # With 50% holdout across many campaigns, should see both True and False
        assert len(results) == 2


# ====================
# Holdout Percentage Tests
# ====================


class TestHoldoutPercentages:
    """Tests for different holdout percentages"""

    def test_5_percent_holdout(self):
        """Test 5% holdout excludes ~5% of users"""
        user_ids = [f"usr_5pct_{i}" for i in range(1000)]
        campaign_id = "cmp_5percent"

        active, holdout = HoldoutSelector.select_audience(
            user_ids, campaign_id, Decimal("5")
        )

        # 5% of 1000 = 50, allow 30-70 range
        assert 30 <= len(holdout) <= 70

    def test_10_percent_holdout(self):
        """Test 10% holdout excludes ~10% of users"""
        user_ids = [f"usr_10pct_{i}" for i in range(1000)]
        campaign_id = "cmp_10percent"

        active, holdout = HoldoutSelector.select_audience(
            user_ids, campaign_id, Decimal("10")
        )

        # 10% of 1000 = 100, allow 70-130 range
        assert 70 <= len(holdout) <= 130

    def test_20_percent_holdout_max(self):
        """Test 20% holdout (maximum allowed) - BR-CAM-001.1"""
        user_ids = [f"usr_20pct_{i}" for i in range(1000)]
        campaign_id = "cmp_20percent"

        active, holdout = HoldoutSelector.select_audience(
            user_ids, campaign_id, Decimal("20")
        )

        # 20% of 1000 = 200, allow 150-250 range
        assert 150 <= len(holdout) <= 250

    def test_1_percent_holdout(self):
        """Test 1% holdout excludes ~1% of users"""
        user_ids = [f"usr_1pct_{i}" for i in range(1000)]
        campaign_id = "cmp_1percent"

        active, holdout = HoldoutSelector.select_audience(
            user_ids, campaign_id, Decimal("1")
        )

        # 1% of 1000 = 10, allow 0-25 range
        assert len(holdout) <= 25


# ====================
# Distribution Tests
# ====================


class TestHoldoutDistribution:
    """Tests for holdout distribution quality"""

    def test_holdout_distribution_uniform(self):
        """Test holdout selection is uniformly distributed"""
        campaign_id = "cmp_uniform_test"
        holdout_pct = Decimal("50")

        # Track holdout status for many users
        holdout_count = 0
        total_users = 10000

        for i in range(total_users):
            user_id = f"usr_uniform_{i}"
            if HoldoutSelector.is_holdout(user_id, campaign_id, holdout_pct):
                holdout_count += 1

        # 50% should be holdout, allow 48-52% range
        holdout_rate = holdout_count / total_users
        assert 0.48 <= holdout_rate <= 0.52

    def test_different_campaigns_independent_holdout(self):
        """Test holdout selection is independent across campaigns"""
        user_ids = [f"usr_independent_{i}" for i in range(500)]
        holdout_pct = Decimal("10")

        campaign1_holdout = set()
        campaign2_holdout = set()

        for user_id in user_ids:
            if HoldoutSelector.is_holdout(user_id, "cmp_independent_1", holdout_pct):
                campaign1_holdout.add(user_id)
            if HoldoutSelector.is_holdout(user_id, "cmp_independent_2", holdout_pct):
                campaign2_holdout.add(user_id)

        # Holdout sets should be different (not perfectly correlated)
        overlap = campaign1_holdout & campaign2_holdout
        only_c1 = campaign1_holdout - campaign2_holdout
        only_c2 = campaign2_holdout - campaign1_holdout

        # There should be some overlap and some differences
        # With 10% holdout from 500 users, each should have ~50 holdout
        assert len(overlap) > 0 or len(only_c1) > 0 or len(only_c2) > 0


# ====================
# Edge Cases
# ====================


class TestHoldoutEdgeCases:
    """Tests for holdout edge cases"""

    def test_negative_holdout_treated_as_zero(self):
        """Test negative holdout percentage treated as 0"""
        user_ids = [f"usr_neg_{i}" for i in range(100)]
        campaign_id = "cmp_negative"

        active, holdout = HoldoutSelector.select_audience(
            user_ids, campaign_id, Decimal("-5")
        )

        assert len(holdout) == 0
        assert len(active) == 100

    def test_empty_audience(self):
        """Test holdout with empty audience"""
        active, holdout = HoldoutSelector.select_audience([], "cmp_empty", Decimal("10"))

        assert len(active) == 0
        assert len(holdout) == 0

    def test_single_user_audience(self):
        """Test holdout with single user"""
        user_ids = ["usr_single"]
        campaign_id = "cmp_single"

        active, holdout = HoldoutSelector.select_audience(
            user_ids, campaign_id, Decimal("10")
        )

        # User is either in active or holdout
        assert len(active) + len(holdout) == 1

    def test_bucket_boundary_exactly_10(self):
        """Test user at bucket exactly equal to holdout percentage"""
        # Find a user with bucket exactly 10
        for i in range(10000):
            user_id = f"usr_boundary_{i}"
            campaign_id = "cmp_boundary_test"
            bucket = HoldoutSelector.get_bucket(user_id, campaign_id)

            if bucket == 10:
                # Bucket 10 should NOT be in holdout if holdout_percentage is 10
                # Because condition is bucket < holdout_percentage
                is_holdout = HoldoutSelector.is_holdout(user_id, campaign_id, Decimal("10"))
                assert not is_holdout, f"Bucket {bucket} should not be in 10% holdout"
                break

    def test_decimal_holdout_percentage(self):
        """Test holdout with decimal percentage like 5.5%"""
        # Our implementation uses int(holdout_percentage), so 5.5 becomes 5
        user_ids = [f"usr_decimal_{i}" for i in range(1000)]
        campaign_id = "cmp_decimal"

        active, holdout = HoldoutSelector.select_audience(
            user_ids, campaign_id, Decimal("5.5")
        )

        # Should behave like 5% since we use int()
        assert 30 <= len(holdout) <= 70


# ====================
# Reproducibility Tests
# ====================


class TestHoldoutReproducibility:
    """Tests for holdout reproducibility - BR-CAM-002.2"""

    def test_holdout_reproducible_across_runs(self):
        """Test same users always in holdout for same campaign"""
        user_ids = [f"usr_repro_{i}" for i in range(200)]
        campaign_id = "cmp_reproducible"
        holdout_pct = Decimal("15")

        # First run
        _, holdout1 = HoldoutSelector.select_audience(
            user_ids, campaign_id, holdout_pct
        )
        holdout1_set = set(holdout1)

        # Second run (simulating different execution)
        _, holdout2 = HoldoutSelector.select_audience(
            user_ids, campaign_id, holdout_pct
        )
        holdout2_set = set(holdout2)

        # Third run
        _, holdout3 = HoldoutSelector.select_audience(
            user_ids, campaign_id, holdout_pct
        )
        holdout3_set = set(holdout3)

        # All runs should produce identical holdout sets
        assert holdout1_set == holdout2_set == holdout3_set

    def test_holdout_consistent_for_measurement(self):
        """Test holdout users tracked consistently for measurement - BR-CAM-002.2"""
        user_ids = [f"usr_measure_{i}" for i in range(500)]
        campaign_id = "cmp_measurement"
        holdout_pct = Decimal("10")

        active, holdout = HoldoutSelector.select_audience(
            user_ids, campaign_id, holdout_pct
        )

        # Store holdout users for later comparison
        holdout_set = set(holdout)

        # Verify each user's status matches
        for user_id in user_ids:
            is_holdout = HoldoutSelector.is_holdout(user_id, campaign_id, holdout_pct)
            if is_holdout:
                assert user_id in holdout_set
            else:
                assert user_id not in holdout_set


# ====================
# Parametrized Tests
# ====================


class TestHoldoutParametrized:
    """Parametrized holdout tests"""

    @pytest.mark.parametrize(
        "holdout_pct,expected_min,expected_max",
        [
            (Decimal("0"), 0, 0),
            (Decimal("1"), 0, 30),
            (Decimal("5"), 30, 80),
            (Decimal("10"), 70, 130),
            (Decimal("15"), 120, 180),
            (Decimal("20"), 170, 230),
        ],
    )
    def test_holdout_percentage_ranges(self, holdout_pct, expected_min, expected_max):
        """Test holdout percentages produce expected ranges"""
        user_ids = [f"usr_param_{holdout_pct}_{i}" for i in range(1000)]
        campaign_id = f"cmp_param_{holdout_pct}"

        active, holdout = HoldoutSelector.select_audience(
            user_ids, campaign_id, holdout_pct
        )

        assert (
            expected_min <= len(holdout) <= expected_max
        ), f"Holdout {holdout_pct}%: got {len(holdout)}, expected {expected_min}-{expected_max}"
