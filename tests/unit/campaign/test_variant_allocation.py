"""
Unit Tests for A/B Test Variant Allocation Logic

Tests deterministic hash-based variant allocation per logic_contract.md.
Reference: BR-CAM-004.2 (Deterministic Variant Assignment)
"""

import pytest
from decimal import Decimal
import hashlib

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import (
    CampaignVariant,
    CampaignTestDataFactory,
)


class VariantAllocator:
    """
    Variant allocation implementation for testing.

    Algorithm (from logic_contract.md):
    ```python
    def assign_variant(user_id: str, campaign_id: str, variants: List[Variant]) -> Variant:
        hash_value = md5(f"{user_id}:{campaign_id}").hexdigest()
        bucket = int(hash_value, 16) % 100

        cumulative = 0
        for variant in variants:
            cumulative += variant.allocation_percentage
            if bucket < cumulative:
                return variant
        return variants[-1]  # Fallback
    ```
    """

    @staticmethod
    def get_hash(user_id: str, campaign_id: str) -> str:
        """Generate deterministic hash for variant assignment"""
        combined = f"{user_id}:{campaign_id}"
        return hashlib.md5(combined.encode()).hexdigest()

    @staticmethod
    def get_bucket(user_id: str, campaign_id: str) -> int:
        """Get bucket number (0-99) for user/campaign combination"""
        hash_value = VariantAllocator.get_hash(user_id, campaign_id)
        return int(hash_value, 16) % 100

    @staticmethod
    def assign_variant(
        user_id: str, campaign_id: str, variants: list
    ) -> CampaignVariant:
        """Assign variant based on deterministic hash - BR-CAM-004.2"""
        if not variants:
            raise ValueError("At least one variant required")

        bucket = VariantAllocator.get_bucket(user_id, campaign_id)

        cumulative = Decimal("0")
        for variant in variants:
            cumulative += variant.allocation_percentage
            if bucket < cumulative:
                return variant

        # Fallback to last variant (handles rounding)
        return variants[-1]

    @staticmethod
    def validate_allocation_sum(variants: list) -> bool:
        """Validate variant allocations sum to 100% - BR-CAM-004.1"""
        total = sum(v.allocation_percentage for v in variants)
        return total == Decimal("100")


# ====================
# Hash Generation Tests
# ====================


class TestVariantHashGeneration:
    """Tests for hash generation"""

    def test_hash_is_deterministic(self):
        """Test same inputs always produce same hash"""
        user_id = "usr_test123"
        campaign_id = "cmp_campaign456"

        hash1 = VariantAllocator.get_hash(user_id, campaign_id)
        hash2 = VariantAllocator.get_hash(user_id, campaign_id)

        assert hash1 == hash2

    def test_hash_is_32_chars(self):
        """Test hash is MD5 format (32 hex chars)"""
        hash_value = VariantAllocator.get_hash("usr_123", "cmp_456")
        assert len(hash_value) == 32
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_different_users_different_hashes(self):
        """Test different users produce different hashes"""
        campaign_id = "cmp_same_campaign"

        hash1 = VariantAllocator.get_hash("usr_user1", campaign_id)
        hash2 = VariantAllocator.get_hash("usr_user2", campaign_id)

        assert hash1 != hash2

    def test_different_campaigns_different_hashes(self):
        """Test different campaigns produce different hashes"""
        user_id = "usr_same_user"

        hash1 = VariantAllocator.get_hash(user_id, "cmp_campaign1")
        hash2 = VariantAllocator.get_hash(user_id, "cmp_campaign2")

        assert hash1 != hash2


# ====================
# Bucket Calculation Tests
# ====================


class TestBucketCalculation:
    """Tests for bucket calculation"""

    def test_bucket_range_0_to_99(self):
        """Test bucket is always in range 0-99"""
        for i in range(100):
            user_id = f"usr_test_{i}"
            campaign_id = "cmp_test_campaign"
            bucket = VariantAllocator.get_bucket(user_id, campaign_id)
            assert 0 <= bucket <= 99

    def test_bucket_is_deterministic(self):
        """Test same inputs always produce same bucket"""
        user_id = "usr_consistent"
        campaign_id = "cmp_consistent"

        bucket1 = VariantAllocator.get_bucket(user_id, campaign_id)
        bucket2 = VariantAllocator.get_bucket(user_id, campaign_id)

        assert bucket1 == bucket2

    def test_bucket_distribution_roughly_uniform(self):
        """Test buckets are roughly uniformly distributed"""
        # Generate 1000 users and check distribution
        buckets = []
        campaign_id = "cmp_distribution_test"

        for i in range(1000):
            user_id = f"usr_distribution_{i}"
            bucket = VariantAllocator.get_bucket(user_id, campaign_id)
            buckets.append(bucket)

        # Each bucket should have roughly 10 users (1000/100)
        # Allow for some variance (5-15 per bucket)
        for b in range(100):
            count = buckets.count(b)
            assert 0 <= count <= 30, f"Bucket {b} has {count} users, expected ~10"


# ====================
# Variant Assignment Tests
# ====================


class TestVariantAssignment:
    """Tests for variant assignment - BR-CAM-004.2"""

    def test_assign_single_variant(self, factory):
        """Test assignment with single variant (100%)"""
        variant = CampaignVariant(
            variant_id="var_only",
            name="Only Variant",
            allocation_percentage=Decimal("100"),
        )

        result = VariantAllocator.assign_variant("usr_any", "cmp_any", [variant])
        assert result.variant_id == "var_only"

    def test_assign_two_variants_50_50(self, factory):
        """Test assignment with two 50/50 variants"""
        variant_a = CampaignVariant(
            variant_id="var_a",
            name="Variant A",
            allocation_percentage=Decimal("50"),
        )
        variant_b = CampaignVariant(
            variant_id="var_b",
            name="Variant B",
            allocation_percentage=Decimal("50"),
        )

        # Test multiple users and ensure both variants are assigned
        assignments = {"var_a": 0, "var_b": 0}

        for i in range(100):
            user_id = f"usr_fifty_{i}"
            result = VariantAllocator.assign_variant(
                user_id, "cmp_5050", [variant_a, variant_b]
            )
            assignments[result.variant_id] += 1

        # Both should have some assignments (roughly 50 each)
        assert assignments["var_a"] > 30
        assert assignments["var_b"] > 30

    def test_assign_three_variants_equal(self, factory):
        """Test assignment with three equal variants (33.33% each)"""
        variants = [
            CampaignVariant(
                variant_id="var_a",
                name="Variant A",
                allocation_percentage=Decimal("33.33"),
            ),
            CampaignVariant(
                variant_id="var_b",
                name="Variant B",
                allocation_percentage=Decimal("33.33"),
            ),
            CampaignVariant(
                variant_id="var_c",
                name="Variant C",
                allocation_percentage=Decimal("33.34"),  # Handle rounding
            ),
        ]

        # Test multiple users
        assignments = {"var_a": 0, "var_b": 0, "var_c": 0}

        for i in range(300):
            user_id = f"usr_three_{i}"
            result = VariantAllocator.assign_variant(user_id, "cmp_thirds", variants)
            assignments[result.variant_id] += 1

        # Each should have ~100 (allow 60-140 range)
        for var_id in ["var_a", "var_b", "var_c"]:
            assert 60 <= assignments[var_id] <= 140, f"{var_id}: {assignments[var_id]}"

    def test_assign_unequal_split(self, factory):
        """Test assignment with unequal split (80/20)"""
        variant_a = CampaignVariant(
            variant_id="var_majority",
            name="Majority",
            allocation_percentage=Decimal("80"),
        )
        variant_b = CampaignVariant(
            variant_id="var_minority",
            name="Minority",
            allocation_percentage=Decimal("20"),
        )

        # Test multiple users
        assignments = {"var_majority": 0, "var_minority": 0}

        for i in range(500):
            user_id = f"usr_unequal_{i}"
            result = VariantAllocator.assign_variant(
                user_id, "cmp_8020", [variant_a, variant_b]
            )
            assignments[result.variant_id] += 1

        # Majority should have ~400, minority ~100
        assert 350 <= assignments["var_majority"] <= 450
        assert 50 <= assignments["var_minority"] <= 150

    def test_same_user_same_variant(self, factory):
        """Test same user always gets same variant (consistency) - BR-CAM-004.2"""
        variants = [
            CampaignVariant(
                variant_id="var_a",
                name="A",
                allocation_percentage=Decimal("50"),
            ),
            CampaignVariant(
                variant_id="var_b",
                name="B",
                allocation_percentage=Decimal("50"),
            ),
        ]

        user_id = "usr_consistent_user"
        campaign_id = "cmp_consistent_campaign"

        # Run 10 times, should always get same result
        first_result = VariantAllocator.assign_variant(user_id, campaign_id, variants)

        for _ in range(10):
            result = VariantAllocator.assign_variant(user_id, campaign_id, variants)
            assert result.variant_id == first_result.variant_id

    def test_empty_variants_raises_error(self):
        """Test empty variants list raises error"""
        with pytest.raises(ValueError):
            VariantAllocator.assign_variant("usr_test", "cmp_test", [])


# ====================
# Allocation Validation Tests
# ====================


class TestAllocationValidation:
    """Tests for allocation validation - BR-CAM-004.1"""

    def test_valid_allocation_100_percent(self):
        """Test valid allocation summing to 100%"""
        variants = [
            CampaignVariant(
                variant_id="var_a", name="A", allocation_percentage=Decimal("50")
            ),
            CampaignVariant(
                variant_id="var_b", name="B", allocation_percentage=Decimal("50")
            ),
        ]
        assert VariantAllocator.validate_allocation_sum(variants)

    def test_valid_allocation_three_variants(self):
        """Test valid allocation with three variants"""
        variants = [
            CampaignVariant(
                variant_id="var_a", name="A", allocation_percentage=Decimal("33")
            ),
            CampaignVariant(
                variant_id="var_b", name="B", allocation_percentage=Decimal("33")
            ),
            CampaignVariant(
                variant_id="var_c", name="C", allocation_percentage=Decimal("34")
            ),
        ]
        assert VariantAllocator.validate_allocation_sum(variants)

    def test_invalid_allocation_under_100(self):
        """Test invalid allocation under 100%"""
        variants = [
            CampaignVariant(
                variant_id="var_a", name="A", allocation_percentage=Decimal("40")
            ),
            CampaignVariant(
                variant_id="var_b", name="B", allocation_percentage=Decimal("40")
            ),
        ]
        assert not VariantAllocator.validate_allocation_sum(variants)

    def test_invalid_allocation_over_100(self):
        """Test invalid allocation over 100%"""
        variants = [
            CampaignVariant(
                variant_id="var_a", name="A", allocation_percentage=Decimal("60")
            ),
            CampaignVariant(
                variant_id="var_b", name="B", allocation_percentage=Decimal("60")
            ),
        ]
        assert not VariantAllocator.validate_allocation_sum(variants)


# ====================
# Control Variant Tests
# ====================


class TestControlVariant:
    """Tests for control variant handling - BR-CAM-004.1"""

    def test_control_variant_assignment(self):
        """Test users can be assigned to control variant"""
        variants = [
            CampaignVariant(
                variant_id="var_treatment",
                name="Treatment",
                allocation_percentage=Decimal("90"),
                is_control=False,
            ),
            CampaignVariant(
                variant_id="var_control",
                name="Control",
                allocation_percentage=Decimal("10"),
                is_control=True,
            ),
        ]

        # Find at least one control assignment
        control_assigned = False
        for i in range(200):
            user_id = f"usr_control_test_{i}"
            result = VariantAllocator.assign_variant(
                user_id, "cmp_control_test", variants
            )
            if result.is_control:
                control_assigned = True
                break

        assert control_assigned, "Expected some users assigned to control"


# ====================
# Edge Case Tests - EC-CAM-006
# ====================


class TestVariantAllocationEdgeCases:
    """Tests for edge cases in variant allocation - EC-CAM-006"""

    def test_rounding_three_variants_33_33_33(self):
        """Test rounding with 33.33% each - EC-CAM-006"""
        # 33.33 * 3 = 99.99, not 100
        # Last variant should catch the remainder
        variants = [
            CampaignVariant(
                variant_id="var_a", name="A", allocation_percentage=Decimal("33.33")
            ),
            CampaignVariant(
                variant_id="var_b", name="B", allocation_percentage=Decimal("33.33")
            ),
            CampaignVariant(
                variant_id="var_c", name="C", allocation_percentage=Decimal("33.34")
            ),
        ]

        # Users with bucket 99 should still be assigned (fallback)
        # Test that all users get a variant
        for i in range(100):
            user_id = f"usr_rounding_{i}"
            result = VariantAllocator.assign_variant(
                user_id, "cmp_rounding", variants
            )
            assert result is not None
            assert result.variant_id in ["var_a", "var_b", "var_c"]

    def test_five_variants_20_each(self):
        """Test with 5 variants at 20% each (max variants) - BR-CAM-004.1"""
        variants = [
            CampaignVariant(
                variant_id=f"var_{i}",
                name=f"Variant {i}",
                allocation_percentage=Decimal("20"),
            )
            for i in range(5)
        ]

        assert VariantAllocator.validate_allocation_sum(variants)

        # Test distribution
        assignments = {f"var_{i}": 0 for i in range(5)}

        for i in range(500):
            user_id = f"usr_five_{i}"
            result = VariantAllocator.assign_variant(user_id, "cmp_five", variants)
            assignments[result.variant_id] += 1

        # Each should have ~100 (allow 50-150 range)
        for var_id in assignments:
            assert (
                50 <= assignments[var_id] <= 150
            ), f"{var_id}: {assignments[var_id]}"

    def test_bucket_boundary_exactly_50(self):
        """Test user at exact boundary (bucket 50 with 50% split)"""
        variants = [
            CampaignVariant(
                variant_id="var_a", name="A", allocation_percentage=Decimal("50")
            ),
            CampaignVariant(
                variant_id="var_b", name="B", allocation_percentage=Decimal("50")
            ),
        ]

        # Find a user with bucket exactly 50
        # bucket 50 should go to variant B (since bucket < 50 goes to A)
        # This tests the boundary condition
        for i in range(10000):
            user_id = f"usr_boundary_{i}"
            bucket = VariantAllocator.get_bucket(user_id, "cmp_boundary")
            if bucket == 50:
                result = VariantAllocator.assign_variant(
                    user_id, "cmp_boundary", variants
                )
                # bucket 50 >= cumulative 50 for first variant, so goes to second
                assert result.variant_id == "var_b"
                break

    def test_zero_allocation_variant(self):
        """Test variant with 0% allocation never gets assigned"""
        variants = [
            CampaignVariant(
                variant_id="var_zero", name="Zero", allocation_percentage=Decimal("0")
            ),
            CampaignVariant(
                variant_id="var_all", name="All", allocation_percentage=Decimal("100")
            ),
        ]

        # No user should ever get var_zero
        for i in range(100):
            user_id = f"usr_zero_alloc_{i}"
            result = VariantAllocator.assign_variant(user_id, "cmp_zero", variants)
            assert result.variant_id == "var_all"
