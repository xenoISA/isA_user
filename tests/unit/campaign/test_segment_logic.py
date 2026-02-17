"""
Unit Tests for Audience Segment Intersection Logic

Tests AND/OR segment logic per logic_contract.md.
Reference: BR-CAM-002.1 (Resolve Audience Segments)
"""

import pytest
from typing import Set, List

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import (
    SegmentType,
    CampaignAudience,
    CampaignTestDataFactory,
)


class AudienceResolver:
    """
    Audience segment resolution implementation for testing.

    Reference: BR-CAM-002.1 (Resolve Audience Segments)

    Logic:
    - Include segments use AND (intersection) by default
    - Multiple include groups can use OR (union)
    - Exclude segments are subtracted from result
    - Final = (Include1 AND Include2) OR (Include3) - Exclude
    """

    @staticmethod
    def resolve_segment(segment_id: str, segment_cache: dict = None) -> Set[str]:
        """
        Resolve a segment to a set of user IDs.
        In tests, we use a mock cache.
        """
        if segment_cache and segment_id in segment_cache:
            return set(segment_cache[segment_id])
        return set()

    @staticmethod
    def intersect_segments(segment_sets: List[Set[str]]) -> Set[str]:
        """
        Apply AND logic to multiple segments - BR-CAM-002.1

        Returns intersection of all sets.
        """
        if not segment_sets:
            return set()
        if len(segment_sets) == 1:
            return segment_sets[0]

        result = segment_sets[0].copy()
        for segment_set in segment_sets[1:]:
            result &= segment_set
        return result

    @staticmethod
    def union_segments(segment_sets: List[Set[str]]) -> Set[str]:
        """
        Apply OR logic to multiple segments - BR-CAM-002.1

        Returns union of all sets.
        """
        if not segment_sets:
            return set()

        result = set()
        for segment_set in segment_sets:
            result |= segment_set
        return result

    @staticmethod
    def subtract_segments(base: Set[str], exclude: Set[str]) -> Set[str]:
        """
        Subtract exclude segment from base - BR-CAM-002.1

        Returns base - exclude
        """
        return base - exclude

    @staticmethod
    def resolve_audiences(
        audiences: List[CampaignAudience], segment_cache: dict
    ) -> Set[str]:
        """
        Full audience resolution with include/exclude logic - BR-CAM-002.1

        Args:
            audiences: List of audience configurations
            segment_cache: Mock segment data {segment_id: [user_ids]}

        Returns:
            Final set of user IDs
        """
        include_sets = []
        exclude_sets = []

        for audience in audiences:
            if audience.segment_id:
                segment_users = AudienceResolver.resolve_segment(
                    audience.segment_id, segment_cache
                )
            else:
                segment_users = set()

            if audience.segment_type == SegmentType.INCLUDE:
                include_sets.append(segment_users)
            elif audience.segment_type == SegmentType.EXCLUDE:
                exclude_sets.append(segment_users)

        # Combine includes with AND logic (intersection)
        if include_sets:
            included = AudienceResolver.intersect_segments(include_sets)
        else:
            included = set()

        # Combine excludes with OR logic (union)
        excluded = AudienceResolver.union_segments(exclude_sets)

        # Final: included - excluded
        return AudienceResolver.subtract_segments(included, excluded)


# ====================
# Basic Intersection Tests
# ====================


class TestSegmentIntersection:
    """Tests for segment intersection (AND logic) - BR-CAM-002.1"""

    def test_intersect_two_segments_overlap(self):
        """Test intersection with overlapping segments"""
        set1 = {"usr_1", "usr_2", "usr_3", "usr_4"}
        set2 = {"usr_3", "usr_4", "usr_5", "usr_6"}

        result = AudienceResolver.intersect_segments([set1, set2])
        assert result == {"usr_3", "usr_4"}

    def test_intersect_two_segments_no_overlap(self):
        """Test intersection with no overlapping users"""
        set1 = {"usr_1", "usr_2"}
        set2 = {"usr_3", "usr_4"}

        result = AudienceResolver.intersect_segments([set1, set2])
        assert result == set()

    def test_intersect_three_segments(self):
        """Test intersection of three segments"""
        set1 = {"usr_1", "usr_2", "usr_3", "usr_4", "usr_5"}
        set2 = {"usr_2", "usr_3", "usr_4"}
        set3 = {"usr_3", "usr_4", "usr_6"}

        result = AudienceResolver.intersect_segments([set1, set2, set3])
        assert result == {"usr_3", "usr_4"}

    def test_intersect_single_segment(self):
        """Test intersection with single segment returns original"""
        set1 = {"usr_1", "usr_2", "usr_3"}

        result = AudienceResolver.intersect_segments([set1])
        assert result == set1

    def test_intersect_empty_list(self):
        """Test intersection with empty list returns empty set"""
        result = AudienceResolver.intersect_segments([])
        assert result == set()

    def test_intersect_with_empty_segment(self):
        """Test intersection with one empty segment returns empty"""
        set1 = {"usr_1", "usr_2"}
        set2 = set()

        result = AudienceResolver.intersect_segments([set1, set2])
        assert result == set()


# ====================
# Basic Union Tests
# ====================


class TestSegmentUnion:
    """Tests for segment union (OR logic) - BR-CAM-002.1"""

    def test_union_two_segments(self):
        """Test union of two segments"""
        set1 = {"usr_1", "usr_2"}
        set2 = {"usr_3", "usr_4"}

        result = AudienceResolver.union_segments([set1, set2])
        assert result == {"usr_1", "usr_2", "usr_3", "usr_4"}

    def test_union_overlapping_segments(self):
        """Test union with overlapping segments (no duplicates)"""
        set1 = {"usr_1", "usr_2", "usr_3"}
        set2 = {"usr_2", "usr_3", "usr_4"}

        result = AudienceResolver.union_segments([set1, set2])
        assert result == {"usr_1", "usr_2", "usr_3", "usr_4"}

    def test_union_three_segments(self):
        """Test union of three segments"""
        set1 = {"usr_1"}
        set2 = {"usr_2"}
        set3 = {"usr_3"}

        result = AudienceResolver.union_segments([set1, set2, set3])
        assert result == {"usr_1", "usr_2", "usr_3"}

    def test_union_empty_list(self):
        """Test union with empty list"""
        result = AudienceResolver.union_segments([])
        assert result == set()


# ====================
# Subtraction Tests
# ====================


class TestSegmentSubtraction:
    """Tests for segment subtraction (exclude logic) - BR-CAM-002.1"""

    def test_subtract_partial_overlap(self):
        """Test subtraction with partial overlap"""
        base = {"usr_1", "usr_2", "usr_3", "usr_4"}
        exclude = {"usr_3", "usr_4", "usr_5"}

        result = AudienceResolver.subtract_segments(base, exclude)
        assert result == {"usr_1", "usr_2"}

    def test_subtract_no_overlap(self):
        """Test subtraction with no overlap (nothing removed)"""
        base = {"usr_1", "usr_2"}
        exclude = {"usr_3", "usr_4"}

        result = AudienceResolver.subtract_segments(base, exclude)
        assert result == {"usr_1", "usr_2"}

    def test_subtract_full_overlap(self):
        """Test subtraction with full overlap (all removed)"""
        base = {"usr_1", "usr_2"}
        exclude = {"usr_1", "usr_2", "usr_3"}

        result = AudienceResolver.subtract_segments(base, exclude)
        assert result == set()

    def test_subtract_empty_exclude(self):
        """Test subtraction with empty exclude set"""
        base = {"usr_1", "usr_2", "usr_3"}
        exclude = set()

        result = AudienceResolver.subtract_segments(base, exclude)
        assert result == base


# ====================
# Full Audience Resolution Tests
# ====================


class TestFullAudienceResolution:
    """Tests for full audience resolution with include/exclude - BR-CAM-002.1"""

    @pytest.fixture
    def segment_cache(self):
        """Mock segment cache for testing"""
        return {
            "seg_premium_users": ["usr_1", "usr_2", "usr_3", "usr_4", "usr_5"],
            "seg_active_users": ["usr_2", "usr_3", "usr_4", "usr_6", "usr_7"],
            "seg_recent_purchasers": ["usr_3", "usr_4", "usr_8"],
            "seg_unsubscribed": ["usr_4", "usr_9"],
            "seg_churned": ["usr_5", "usr_10"],
        }

    def test_single_include_segment(self, segment_cache):
        """Test resolution with single include segment"""
        audiences = [
            CampaignAudience(
                audience_id="aud_1",
                segment_type=SegmentType.INCLUDE,
                segment_id="seg_premium_users",
            )
        ]

        result = AudienceResolver.resolve_audiences(audiences, segment_cache)
        assert result == {"usr_1", "usr_2", "usr_3", "usr_4", "usr_5"}

    def test_two_include_segments_intersection(self, segment_cache):
        """Test resolution with two include segments (AND)"""
        audiences = [
            CampaignAudience(
                audience_id="aud_1",
                segment_type=SegmentType.INCLUDE,
                segment_id="seg_premium_users",
            ),
            CampaignAudience(
                audience_id="aud_2",
                segment_type=SegmentType.INCLUDE,
                segment_id="seg_active_users",
            ),
        ]

        result = AudienceResolver.resolve_audiences(audiences, segment_cache)
        # Premium AND Active = {usr_2, usr_3, usr_4}
        assert result == {"usr_2", "usr_3", "usr_4"}

    def test_include_with_exclude(self, segment_cache):
        """Test resolution with include and exclude segments"""
        audiences = [
            CampaignAudience(
                audience_id="aud_1",
                segment_type=SegmentType.INCLUDE,
                segment_id="seg_premium_users",
            ),
            CampaignAudience(
                audience_id="aud_2",
                segment_type=SegmentType.EXCLUDE,
                segment_id="seg_unsubscribed",
            ),
        ]

        result = AudienceResolver.resolve_audiences(audiences, segment_cache)
        # Premium - Unsubscribed = {usr_1, usr_2, usr_3, usr_5} (usr_4 excluded)
        assert result == {"usr_1", "usr_2", "usr_3", "usr_5"}

    def test_two_includes_one_exclude(self, segment_cache):
        """Test resolution with two includes and one exclude"""
        audiences = [
            CampaignAudience(
                audience_id="aud_1",
                segment_type=SegmentType.INCLUDE,
                segment_id="seg_premium_users",
            ),
            CampaignAudience(
                audience_id="aud_2",
                segment_type=SegmentType.INCLUDE,
                segment_id="seg_active_users",
            ),
            CampaignAudience(
                audience_id="aud_3",
                segment_type=SegmentType.EXCLUDE,
                segment_id="seg_unsubscribed",
            ),
        ]

        result = AudienceResolver.resolve_audiences(audiences, segment_cache)
        # (Premium AND Active) - Unsubscribed = {usr_2, usr_3} (usr_4 excluded)
        assert result == {"usr_2", "usr_3"}

    def test_multiple_excludes(self, segment_cache):
        """Test resolution with multiple exclude segments (OR)"""
        audiences = [
            CampaignAudience(
                audience_id="aud_1",
                segment_type=SegmentType.INCLUDE,
                segment_id="seg_premium_users",
            ),
            CampaignAudience(
                audience_id="aud_2",
                segment_type=SegmentType.EXCLUDE,
                segment_id="seg_unsubscribed",
            ),
            CampaignAudience(
                audience_id="aud_3",
                segment_type=SegmentType.EXCLUDE,
                segment_id="seg_churned",
            ),
        ]

        result = AudienceResolver.resolve_audiences(audiences, segment_cache)
        # Premium - (Unsubscribed OR Churned) = {usr_1, usr_2, usr_3}
        # (usr_4 in unsubscribed, usr_5 in churned)
        assert result == {"usr_1", "usr_2", "usr_3"}

    def test_no_audiences_empty_result(self, segment_cache):
        """Test resolution with no audiences returns empty"""
        result = AudienceResolver.resolve_audiences([], segment_cache)
        assert result == set()

    def test_only_exclude_segments(self, segment_cache):
        """Test resolution with only exclude segments returns empty"""
        audiences = [
            CampaignAudience(
                audience_id="aud_1",
                segment_type=SegmentType.EXCLUDE,
                segment_id="seg_unsubscribed",
            ),
        ]

        result = AudienceResolver.resolve_audiences(audiences, segment_cache)
        # No includes means empty base, nothing to exclude from
        assert result == set()


# ====================
# Edge Cases
# ====================


class TestSegmentEdgeCases:
    """Tests for segment edge cases"""

    def test_unknown_segment_returns_empty(self):
        """Test unknown segment ID returns empty set"""
        result = AudienceResolver.resolve_segment(
            "seg_unknown", {"seg_known": ["usr_1"]}
        )
        assert result == set()

    def test_segment_with_none_cache(self):
        """Test segment resolution with None cache"""
        result = AudienceResolver.resolve_segment("seg_any", None)
        assert result == set()

    def test_large_segment_intersection(self):
        """Test intersection performance with large segments"""
        set1 = {f"usr_{i}" for i in range(10000)}
        set2 = {f"usr_{i}" for i in range(5000, 15000)}

        result = AudienceResolver.intersect_segments([set1, set2])
        # 5000-9999 = 5000 users
        assert len(result) == 5000

    def test_audience_without_segment_id(self):
        """Test audience without segment_id is treated as empty"""
        audiences = [
            CampaignAudience(
                audience_id="aud_1",
                segment_type=SegmentType.INCLUDE,
                segment_query={"field": "plan", "value": "premium"},  # Query instead of ID
            ),
        ]

        segment_cache = {"seg_premium": ["usr_1", "usr_2"]}
        result = AudienceResolver.resolve_audiences(audiences, segment_cache)
        # Without segment_id, no users are included
        assert result == set()


# ====================
# Parametrized Tests
# ====================


class TestSegmentLogicParametrized:
    """Parametrized segment logic tests"""

    @pytest.mark.parametrize(
        "sets,expected",
        [
            # Two sets with overlap
            ([{"a", "b", "c"}, {"b", "c", "d"}], {"b", "c"}),
            # Three sets with single common element
            ([{"a", "b"}, {"b", "c"}, {"b", "d"}], {"b"}),
            # All same elements
            ([{"a", "b"}, {"a", "b"}, {"a", "b"}], {"a", "b"}),
            # No common elements
            ([{"a"}, {"b"}, {"c"}], set()),
        ],
    )
    def test_intersection_scenarios(self, sets, expected):
        """Test various intersection scenarios"""
        result = AudienceResolver.intersect_segments(sets)
        assert result == expected

    @pytest.mark.parametrize(
        "sets,expected",
        [
            # Two sets
            ([{"a", "b"}, {"c", "d"}], {"a", "b", "c", "d"}),
            # Overlapping sets
            ([{"a", "b"}, {"b", "c"}], {"a", "b", "c"}),
            # Single set
            ([{"a", "b"}], {"a", "b"}),
        ],
    )
    def test_union_scenarios(self, sets, expected):
        """Test various union scenarios"""
        result = AudienceResolver.union_segments(sets)
        assert result == expected
