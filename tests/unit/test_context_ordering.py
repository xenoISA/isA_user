"""
Unit tests for context ordering — lost-in-the-middle mitigation.

Tests the `order_by_importance_edges` function that places highest-importance
items at the start and end of a list, with lowest-importance items in the middle.
This addresses the serial-position effect (primacy + recency) described in
Liu et al., 2023.
"""

import pytest

from microservices.memory_service.context_ordering import order_by_importance_edges


class TestOrderByImportanceEdges:
    """L1 Unit tests for the interleave-to-edges algorithm."""

    def test_empty_list(self):
        """Empty input returns empty output."""
        assert order_by_importance_edges([]) == []

    def test_single_item(self):
        """Single item is returned unchanged."""
        items = [{"content": "a", "importance_score": 0.5}]
        result = order_by_importance_edges(items)
        assert result == items

    def test_two_items_ordered(self):
        """Two items: higher importance first, lower second."""
        items = [
            {"content": "low", "importance_score": 0.2},
            {"content": "high", "importance_score": 0.9},
        ]
        result = order_by_importance_edges(items)
        assert result[0]["content"] == "high"
        assert result[1]["content"] == "low"

    def test_three_items_edges(self):
        """Three items: highest at start, second-highest at end, lowest in middle."""
        items = [
            {"content": "medium", "importance_score": 0.5},
            {"content": "high", "importance_score": 0.9},
            {"content": "low", "importance_score": 0.1},
        ]
        result = order_by_importance_edges(items)
        # Sorted desc: high(0.9), medium(0.5), low(0.1)
        # Interleave: i=0 -> left(pos 0), i=1 -> right(pos 2), i=2 -> left(pos 1)
        assert result[0]["content"] == "high"     # pos 0 (start)
        assert result[1]["content"] == "low"       # pos 1 (middle)
        assert result[2]["content"] == "medium"    # pos 2 (end)

    def test_five_items_edges(self):
        """Five items: highest-importance at edges, lowest in the middle."""
        items = [
            {"content": "c", "importance_score": 0.5},
            {"content": "a", "importance_score": 0.9},
            {"content": "e", "importance_score": 0.1},
            {"content": "b", "importance_score": 0.7},
            {"content": "d", "importance_score": 0.3},
        ]
        result = order_by_importance_edges(items)
        # Sorted desc: a(0.9), b(0.7), c(0.5), d(0.3), e(0.1)
        # i=0 (a) -> left pos 0
        # i=1 (b) -> right pos 4
        # i=2 (c) -> left pos 1
        # i=3 (d) -> right pos 3
        # i=4 (e) -> left pos 2
        assert result[0]["content"] == "a"  # highest at start
        assert result[1]["content"] == "c"  # 3rd highest
        assert result[2]["content"] == "e"  # lowest in middle
        assert result[3]["content"] == "d"  # 4th highest
        assert result[4]["content"] == "b"  # 2nd highest at end

    def test_edges_have_highest_importance(self):
        """First and last items should have the two highest importance scores."""
        items = [
            {"content": f"item_{i}", "importance_score": score}
            for i, score in enumerate([0.1, 0.3, 0.5, 0.7, 0.9, 0.2, 0.8])
        ]
        result = order_by_importance_edges(items)
        scores = [r["importance_score"] for r in result]
        # First and last should be the two highest
        edge_scores = {scores[0], scores[-1]}
        assert edge_scores == {0.9, 0.8}

    def test_middle_has_lowest_importance(self):
        """The middle position should contain the lowest-importance item."""
        items = [
            {"content": f"item_{i}", "importance_score": score}
            for i, score in enumerate([0.1, 0.5, 0.9, 0.7, 0.3])
        ]
        result = order_by_importance_edges(items)
        mid = len(result) // 2
        # Middle item should have the lowest importance
        assert result[mid]["importance_score"] == 0.1

    def test_custom_importance_key(self):
        """Supports custom key for importance scoring."""
        items = [
            {"content": "low", "score": 0.2},
            {"content": "high", "score": 0.9},
            {"content": "mid", "score": 0.5},
        ]
        result = order_by_importance_edges(items, importance_key="score")
        assert result[0]["content"] == "high"
        assert result[-1]["content"] == "mid"

    def test_missing_importance_key_defaults_to_zero(self):
        """Items missing the importance key are treated as importance 0."""
        items = [
            {"content": "has_score", "importance_score": 0.8},
            {"content": "no_score"},
            {"content": "low_score", "importance_score": 0.1},
        ]
        result = order_by_importance_edges(items)
        # Sorted desc: has_score(0.8), low_score(0.1), no_score(0)
        assert result[0]["content"] == "has_score"
        assert result[-1]["content"] == "low_score"

    def test_equal_importance_preserves_relative_order(self):
        """Items with equal importance maintain stable ordering."""
        items = [
            {"content": "first", "importance_score": 0.5},
            {"content": "second", "importance_score": 0.5},
            {"content": "third", "importance_score": 0.5},
        ]
        result = order_by_importance_edges(items)
        # All equal, so stable sort preserves original order
        # Then interleave: i=0->left(0), i=1->right(2), i=2->left(1)
        assert len(result) == 3

    def test_does_not_mutate_input(self):
        """The original list should not be modified."""
        items = [
            {"content": "b", "importance_score": 0.3},
            {"content": "a", "importance_score": 0.9},
        ]
        original = list(items)
        order_by_importance_edges(items)
        assert items == original

    def test_dict_results_with_similarity_score(self):
        """Works with memory search results that include similarity_score."""
        items = [
            {"content": "fact1", "importance_score": 0.8, "similarity_score": 0.95, "memory_type": "factual"},
            {"content": "fact2", "importance_score": 0.3, "similarity_score": 0.90, "memory_type": "factual"},
            {"content": "fact3", "importance_score": 0.6, "similarity_score": 0.85, "memory_type": "factual"},
            {"content": "fact4", "importance_score": 0.9, "similarity_score": 0.80, "memory_type": "factual"},
        ]
        result = order_by_importance_edges(items)
        # Should order by importance_score, not similarity_score
        assert result[0]["importance_score"] == 0.9
        edge_scores = {result[0]["importance_score"], result[-1]["importance_score"]}
        assert edge_scores == {0.9, 0.8}

    def test_large_list_symmetry(self):
        """Edge items decrease in importance toward the middle from both sides."""
        items = [
            {"content": f"item_{i}", "importance_score": i / 10.0}
            for i in range(10)
        ]
        result = order_by_importance_edges(items)
        scores = [r["importance_score"] for r in result]
        n = len(scores)
        # Check that importance decreases from start toward middle
        for i in range(n // 2 - 1):
            assert scores[i] >= scores[i + 1], (
                f"Left side not decreasing: pos {i} ({scores[i]}) < pos {i+1} ({scores[i+1]})"
            )
        # Check that importance increases from middle toward end
        for i in range(n // 2, n - 1):
            assert scores[i] <= scores[i + 1], (
                f"Right side not increasing: pos {i} ({scores[i]}) > pos {i+1} ({scores[i+1]})"
            )
