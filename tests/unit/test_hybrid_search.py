"""
Unit tests for hybrid search — merging vector similarity and graph traversal results.

Tests the merge_hybrid_results function in isolation (L1 Unit).
No I/O, no mocks needed — pure function testing.
"""

import pytest

from microservices.memory_service.hybrid_search import merge_hybrid_results


# ---------------------------------------------------------------------------
# Fixtures — reusable result sets
# ---------------------------------------------------------------------------

def _vec(memory_id: str, score: float, content: str = "") -> dict:
    """Helper to build a vector search result dict."""
    return {
        "memory_id": memory_id,
        "content": content or f"vector-content-{memory_id}",
        "similarity_score": score,
        "memory_type": "factual",
    }


def _graph(memory_id: str, score: float, content: str = "") -> dict:
    """Helper to build a graph traversal result dict."""
    return {
        "memory_id": memory_id,
        "content": content or f"graph-content-{memory_id}",
        "relevance_score": score,
        "memory_type": "semantic",
    }


# ---------------------------------------------------------------------------
# Test: merge with both vector and graph results
# ---------------------------------------------------------------------------

class TestHybridMerge:
    """Test the core merge logic with both result sets present."""

    def test_merge_basic(self):
        """Both sources contribute distinct results with correct weighted scores."""
        vector = [_vec("v1", 0.9), _vec("v2", 0.7)]
        graph = [_graph("g1", 0.8), _graph("g2", 0.6)]

        merged = merge_hybrid_results(vector, graph, vector_weight=0.6, graph_weight=0.4)

        ids = [r["memory_id"] for r in merged]
        assert "v1" in ids
        assert "v2" in ids
        assert "g1" in ids
        assert "g2" in ids
        assert len(merged) == 4

    def test_results_sorted_by_final_score_descending(self):
        """Merged results must be sorted by final_score descending."""
        vector = [_vec("v1", 1.0), _vec("v2", 0.3)]
        graph = [_graph("g1", 1.0), _graph("g2", 0.2)]

        merged = merge_hybrid_results(vector, graph, vector_weight=0.6, graph_weight=0.4)

        scores = [r["final_score"] for r in merged]
        assert scores == sorted(scores, reverse=True)

    def test_final_score_values(self):
        """Verify exact weighted score computation."""
        vector = [_vec("v1", 1.0)]
        graph = [_graph("g1", 1.0)]

        merged = merge_hybrid_results(vector, graph, vector_weight=0.6, graph_weight=0.4)

        v1 = next(r for r in merged if r["memory_id"] == "v1")
        g1 = next(r for r in merged if r["memory_id"] == "g1")

        # v1: vector_weight * normalized_score(0.5) = 0.6 * 0.5 = 0.3 (single result normalizes to 0.5)
        assert v1["final_score"] == pytest.approx(0.3)
        # g1: graph_weight * normalized_score(0.5) = 0.4 * 0.5 = 0.2
        assert g1["final_score"] == pytest.approx(0.2)

    def test_each_result_has_final_score_field(self):
        """Every result dict must include a 'final_score' key."""
        vector = [_vec("v1", 0.5)]
        graph = [_graph("g1", 0.5)]

        merged = merge_hybrid_results(vector, graph)

        for r in merged:
            assert "final_score" in r


# ---------------------------------------------------------------------------
# Test: vector-only fallback when graph unavailable
# ---------------------------------------------------------------------------

class TestVectorOnlyFallback:
    """Graph results are empty — vector results should still come through."""

    def test_empty_graph_results(self):
        vector = [_vec("v1", 0.9), _vec("v2", 0.7)]

        merged = merge_hybrid_results(vector, [], vector_weight=0.6, graph_weight=0.4)

        assert len(merged) == 2
        ids = [r["memory_id"] for r in merged]
        assert "v1" in ids
        assert "v2" in ids

    def test_fallback_source_tagged_vector(self):
        """When only vector results, all should be tagged source='vector'."""
        vector = [_vec("v1", 0.9)]

        merged = merge_hybrid_results(vector, [])

        assert all(r["source"] == "vector" for r in merged)

    def test_fallback_scores_use_vector_weight(self):
        """Scores should still be scaled by vector_weight even without graph."""
        vector = [_vec("v1", 1.0)]

        merged = merge_hybrid_results(vector, [], vector_weight=0.6, graph_weight=0.4)

        assert merged[0]["final_score"] == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Test: graph-only fallback when vector unavailable
# ---------------------------------------------------------------------------

class TestGraphOnlyFallback:
    """Vector results are empty — graph results should still come through."""

    def test_empty_vector_results(self):
        graph = [_graph("g1", 0.8)]

        merged = merge_hybrid_results([], graph, vector_weight=0.6, graph_weight=0.4)

        assert len(merged) == 1
        assert merged[0]["memory_id"] == "g1"

    def test_fallback_source_tagged_graph(self):
        graph = [_graph("g1", 0.8)]

        merged = merge_hybrid_results([], graph)

        assert all(r["source"] == "graph" for r in merged)


# ---------------------------------------------------------------------------
# Test: weight configuration
# ---------------------------------------------------------------------------

class TestWeightConfiguration:
    """Verify configurable weight behavior."""

    def test_default_weights(self):
        """Default weights should be 0.6 vector, 0.4 graph."""
        vector = [_vec("v1", 1.0)]
        graph = [_graph("g1", 1.0)]

        merged = merge_hybrid_results(vector, graph)

        v1 = next(r for r in merged if r["memory_id"] == "v1")
        g1 = next(r for r in merged if r["memory_id"] == "g1")
        # Single result normalizes to 0.5 (neutral), so 0.6 * 0.5 = 0.3
        assert v1["final_score"] == pytest.approx(0.3)
        assert g1["final_score"] == pytest.approx(0.2)

    def test_equal_weights(self):
        """50/50 weighting should produce equal scores for identical inputs."""
        vector = [_vec("v1", 1.0)]
        graph = [_graph("g1", 1.0)]

        merged = merge_hybrid_results(vector, graph, vector_weight=0.5, graph_weight=0.5)

        v1 = next(r for r in merged if r["memory_id"] == "v1")
        g1 = next(r for r in merged if r["memory_id"] == "g1")
        # Single result normalizes to 0.5, so 0.5 * 0.5 = 0.25
        assert v1["final_score"] == pytest.approx(0.25)
        assert g1["final_score"] == pytest.approx(0.25)

    def test_full_vector_weight(self):
        """With 1.0 vector weight and 0.0 graph, graph results get score 0."""
        vector = [_vec("v1", 0.8)]
        graph = [_graph("g1", 0.9)]

        merged = merge_hybrid_results(vector, graph, vector_weight=1.0, graph_weight=0.0)

        v1 = next(r for r in merged if r["memory_id"] == "v1")
        g1 = next(r for r in merged if r["memory_id"] == "g1")
        # Single result normalizes to 0.5, so v1 = 1.0 * 0.5 = 0.5
        assert v1["final_score"] == pytest.approx(0.5)
        assert g1["final_score"] == pytest.approx(0.0)

    def test_full_graph_weight(self):
        """With 0.0 vector weight and 1.0 graph, vector results get score 0."""
        vector = [_vec("v1", 0.8)]
        graph = [_graph("g1", 0.9)]

        merged = merge_hybrid_results(vector, graph, vector_weight=0.0, graph_weight=1.0)

        v1 = next(r for r in merged if r["memory_id"] == "v1")
        g1 = next(r for r in merged if r["memory_id"] == "g1")
        assert v1["final_score"] == pytest.approx(0.0)
        # Single result normalizes to 0.5, so g1 = 1.0 * 0.5 = 0.5
        assert g1["final_score"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Test: deduplication (same memory found by both vector and graph)
# ---------------------------------------------------------------------------

class TestDeduplication:
    """Same memory_id appears in both vector and graph results."""

    def test_duplicate_merged_into_one(self):
        """Duplicate memory_id should appear exactly once in output."""
        vector = [_vec("shared", 0.9)]
        graph = [_graph("shared", 0.8)]

        merged = merge_hybrid_results(vector, graph, vector_weight=0.6, graph_weight=0.4)

        ids = [r["memory_id"] for r in merged]
        assert ids.count("shared") == 1

    def test_duplicate_tagged_both(self):
        """Deduplicated result should be tagged source='both'."""
        vector = [_vec("shared", 0.9)]
        graph = [_graph("shared", 0.8)]

        merged = merge_hybrid_results(vector, graph, vector_weight=0.6, graph_weight=0.4)

        shared = next(r for r in merged if r["memory_id"] == "shared")
        assert shared["source"] == "both"

    def test_duplicate_combined_score(self):
        """Deduplicated result should get combined weighted score."""
        vector = [_vec("shared", 1.0)]
        graph = [_graph("shared", 1.0)]

        merged = merge_hybrid_results(vector, graph, vector_weight=0.6, graph_weight=0.4)

        shared = next(r for r in merged if r["memory_id"] == "shared")
        # 0.6 * 0.5 + 0.4 * 0.5 = 0.5 (single results normalize to 0.5)
        assert shared["final_score"] == pytest.approx(0.5)

    def test_mixed_duplicates_and_unique(self):
        """Mix of shared and unique results should all appear correctly."""
        vector = [_vec("shared", 0.9), _vec("v-only", 0.7)]
        graph = [_graph("shared", 0.8), _graph("g-only", 0.6)]

        merged = merge_hybrid_results(vector, graph, vector_weight=0.6, graph_weight=0.4)

        ids = [r["memory_id"] for r in merged]
        assert len(merged) == 3  # shared + v-only + g-only
        assert "shared" in ids
        assert "v-only" in ids
        assert "g-only" in ids


# ---------------------------------------------------------------------------
# Test: result source tagging
# ---------------------------------------------------------------------------

class TestSourceTagging:
    """Every result must have a 'source' field: 'vector', 'graph', or 'both'."""

    def test_vector_only_tagged(self):
        vector = [_vec("v1", 0.9)]
        graph = [_graph("g1", 0.8)]

        merged = merge_hybrid_results(vector, graph)

        v1 = next(r for r in merged if r["memory_id"] == "v1")
        assert v1["source"] == "vector"

    def test_graph_only_tagged(self):
        vector = [_vec("v1", 0.9)]
        graph = [_graph("g1", 0.8)]

        merged = merge_hybrid_results(vector, graph)

        g1 = next(r for r in merged if r["memory_id"] == "g1")
        assert g1["source"] == "graph"

    def test_both_tagged(self):
        vector = [_vec("shared", 0.9)]
        graph = [_graph("shared", 0.8)]

        merged = merge_hybrid_results(vector, graph)

        shared = next(r for r in merged if r["memory_id"] == "shared")
        assert shared["source"] == "both"

    def test_all_results_have_source(self):
        vector = [_vec("v1", 0.9), _vec("shared", 0.7)]
        graph = [_graph("g1", 0.8), _graph("shared", 0.6)]

        merged = merge_hybrid_results(vector, graph)

        for r in merged:
            assert r["source"] in ("vector", "graph", "both")


# ---------------------------------------------------------------------------
# Test: empty results from one or both sources
# ---------------------------------------------------------------------------

class TestEmptyResults:
    """Edge cases: no results at all, or one side empty."""

    def test_both_empty(self):
        merged = merge_hybrid_results([], [])
        assert merged == []

    def test_vector_empty_graph_populated(self):
        graph = [_graph("g1", 0.8)]

        merged = merge_hybrid_results([], graph)

        assert len(merged) == 1
        assert merged[0]["source"] == "graph"

    def test_graph_empty_vector_populated(self):
        vector = [_vec("v1", 0.9)]

        merged = merge_hybrid_results(vector, [])

        assert len(merged) == 1
        assert merged[0]["source"] == "vector"


# ---------------------------------------------------------------------------
# Test: score normalization
# ---------------------------------------------------------------------------

class TestScoreNormalization:
    """Scores from each source should be normalized to [0, 1] before weighting."""

    def test_normalization_within_vector_set(self):
        """When max vector score is 0.5, it should be normalized to 1.0 internally."""
        vector = [_vec("v1", 0.5), _vec("v2", 0.25)]
        graph = []

        merged = merge_hybrid_results(vector, graph, vector_weight=1.0, graph_weight=0.0)

        v1 = next(r for r in merged if r["memory_id"] == "v1")
        v2 = next(r for r in merged if r["memory_id"] == "v2")
        # Min-max normalization: v1=(0.5-0.25)/(0.5-0.25)=1.0, v2=(0.25-0.25)/(0.5-0.25)=0.0
        assert v1["final_score"] == pytest.approx(1.0)
        assert v2["final_score"] == pytest.approx(0.0)

    def test_single_result_normalization(self):
        """A single result should get neutral normalized score of 0.5."""
        vector = [_vec("v1", 0.3)]
        graph = []

        merged = merge_hybrid_results(vector, graph, vector_weight=1.0, graph_weight=0.0)

        assert merged[0]["final_score"] == pytest.approx(0.5)

    def test_all_equal_scores_normalization(self):
        """When all scores are equal, all should normalize to 0.5 (neutral)."""
        vector = [_vec("v1", 0.5), _vec("v2", 0.5)]
        graph = []

        merged = merge_hybrid_results(vector, graph, vector_weight=1.0, graph_weight=0.0)

        for r in merged:
            assert r["final_score"] == pytest.approx(0.5)
