"""
Unit tests for MMR (Maximal Marginal Relevance) re-ranking algorithm.

Tests the standalone MMR re-ranker used in the memory search pipeline.
"""

import pytest
import math
from typing import List


class TestCosineSimlarity:
    """L1 Unit tests for cosine similarity helper"""

    def test_identical_vectors(self):
        from microservices.memory_service.mmr_reranker import cosine_similarity
        vec = [1.0, 0.0, 0.0]
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        from microservices.memory_service.mmr_reranker import cosine_similarity
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        from microservices.memory_service.mmr_reranker import cosine_similarity
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self):
        from microservices.memory_service.mmr_reranker import cosine_similarity
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_both_zero_vectors(self):
        from microservices.memory_service.mmr_reranker import cosine_similarity
        a = [0.0, 0.0]
        b = [0.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_real_valued_vectors(self):
        from microservices.memory_service.mmr_reranker import cosine_similarity
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        # Manual: dot=32, |a|=sqrt(14), |b|=sqrt(77), cos=32/sqrt(1078)
        expected = 32.0 / math.sqrt(14 * 77)
        assert cosine_similarity(a, b) == pytest.approx(expected, abs=1e-6)


class TestMMRRerank:
    """L1 Unit tests for MMR re-ranking algorithm"""

    def test_empty_documents(self):
        from microservices.memory_service.mmr_reranker import mmr_rerank
        result = mmr_rerank(
            query_embedding=[1.0, 0.0],
            doc_embeddings=[],
            doc_scores=[],
            lambda_param=0.5,
            top_k=10,
        )
        assert result == []

    def test_single_document(self):
        from microservices.memory_service.mmr_reranker import mmr_rerank
        result = mmr_rerank(
            query_embedding=[1.0, 0.0],
            doc_embeddings=[[1.0, 0.0]],
            doc_scores=[0.9],
            lambda_param=0.5,
            top_k=10,
        )
        assert result == [0]

    def test_top_k_limits_output(self):
        from microservices.memory_service.mmr_reranker import mmr_rerank
        embeddings = [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]]
        scores = [0.9, 0.8, 0.7]
        result = mmr_rerank(
            query_embedding=[1.0, 0.0],
            doc_embeddings=embeddings,
            doc_scores=scores,
            lambda_param=0.5,
            top_k=2,
        )
        assert len(result) == 2

    def test_lambda_1_pure_relevance(self):
        """With lambda=1.0, MMR should return docs in order of their original scores (pure relevance)"""
        from microservices.memory_service.mmr_reranker import mmr_rerank
        # Three docs with decreasing relevance scores
        embeddings = [[1.0, 0.0], [0.9, 0.1], [0.1, 0.9]]
        scores = [0.9, 0.7, 0.5]
        result = mmr_rerank(
            query_embedding=[1.0, 0.0],
            doc_embeddings=embeddings,
            doc_scores=scores,
            lambda_param=1.0,
            top_k=3,
        )
        # Should be in original score order
        assert result == [0, 1, 2]

    def test_lambda_0_pure_diversity(self):
        """With lambda=0.0, MMR should maximize diversity (minimize similarity to selected docs)"""
        from microservices.memory_service.mmr_reranker import mmr_rerank
        # Two very similar docs and one very different
        embeddings = [[1.0, 0.0], [0.99, 0.01], [0.0, 1.0]]
        scores = [0.9, 0.85, 0.8]
        result = mmr_rerank(
            query_embedding=[1.0, 0.0],
            doc_embeddings=embeddings,
            doc_scores=scores,
            lambda_param=0.0,
            top_k=3,
        )
        # First pick is arbitrary (all have 0 relevance weight), but after first pick,
        # the most diverse doc should come sooner
        # After selecting first doc (index 0, highest score ties broken by iteration order),
        # the diverse doc [0.0, 1.0] (index 2) should come before the similar doc [0.99, 0.01] (index 1)
        assert result[0] == 0  # First selected (no diversity penalty yet, all score 0 except first iteration)

    def test_diversity_effect(self):
        """MMR with moderate lambda should promote diverse results over redundant ones"""
        from microservices.memory_service.mmr_reranker import mmr_rerank
        # Doc 0 and Doc 1 are very similar (both close to [1,0])
        # Doc 2 is very different ([0,1]) but has slightly lower relevance
        embeddings = [[1.0, 0.0], [0.99, 0.01], [0.0, 1.0]]
        scores = [0.9, 0.89, 0.85]
        result = mmr_rerank(
            query_embedding=[1.0, 0.0],
            doc_embeddings=embeddings,
            doc_scores=scores,
            lambda_param=0.5,
            top_k=3,
        )
        # First should be the most relevant doc
        assert result[0] == 0
        # Second should prefer diversity: doc 2 ([0,1]) is very different from doc 0 ([1,0]),
        # while doc 1 is almost identical to doc 0
        assert result[1] == 2

    def test_all_indices_returned(self):
        """All document indices should appear exactly once"""
        from microservices.memory_service.mmr_reranker import mmr_rerank
        n = 5
        embeddings = [[float(i == j) for j in range(n)] for i in range(n)]
        scores = [0.9 - 0.1 * i for i in range(n)]
        result = mmr_rerank(
            query_embedding=[1.0] * n,
            doc_embeddings=embeddings,
            doc_scores=scores,
            lambda_param=0.5,
            top_k=n,
        )
        assert sorted(result) == list(range(n))

    def test_top_k_greater_than_docs(self):
        """top_k larger than number of docs should return all docs"""
        from microservices.memory_service.mmr_reranker import mmr_rerank
        embeddings = [[1.0, 0.0], [0.0, 1.0]]
        scores = [0.9, 0.8]
        result = mmr_rerank(
            query_embedding=[1.0, 0.0],
            doc_embeddings=embeddings,
            doc_scores=scores,
            lambda_param=0.5,
            top_k=100,
        )
        assert len(result) == 2


class TestApplyMMRReranking:
    """L1 Unit tests for apply_mmr_reranking helper that operates on search result dicts"""

    def test_no_results(self):
        from microservices.memory_service.mmr_reranker import apply_mmr_reranking
        result = apply_mmr_reranking([], [1.0, 0.0], lambda_param=0.5, top_k=10)
        assert result == []

    def test_results_without_embeddings_returned_unchanged(self):
        """If results don't have embeddings, return them as-is (fallback)"""
        from microservices.memory_service.mmr_reranker import apply_mmr_reranking
        results = [
            {"id": "a", "similarity_score": 0.9},
            {"id": "b", "similarity_score": 0.8},
        ]
        output = apply_mmr_reranking(results, [1.0, 0.0], lambda_param=0.5, top_k=10)
        assert len(output) == 2
        # Should be same order (fallback)
        assert output[0]["id"] == "a"

    def test_reranking_with_embeddings(self):
        """Results with embeddings should be re-ranked"""
        from microservices.memory_service.mmr_reranker import apply_mmr_reranking
        results = [
            {"id": "a", "similarity_score": 0.9, "embedding": [1.0, 0.0]},
            {"id": "b", "similarity_score": 0.89, "embedding": [0.99, 0.01]},
            {"id": "c", "similarity_score": 0.85, "embedding": [0.0, 1.0]},
        ]
        output = apply_mmr_reranking(results, [1.0, 0.0], lambda_param=0.5, top_k=3)
        assert len(output) == 3
        # First should be most relevant
        assert output[0]["id"] == "a"
        # Second should prefer diverse doc c over redundant doc b
        assert output[1]["id"] == "c"

    def test_mmr_score_added_to_results(self):
        """Results should include mmr_score and mmr_rank fields"""
        from microservices.memory_service.mmr_reranker import apply_mmr_reranking
        results = [
            {"id": "a", "similarity_score": 0.9, "embedding": [1.0, 0.0]},
            {"id": "b", "similarity_score": 0.8, "embedding": [0.0, 1.0]},
        ]
        output = apply_mmr_reranking(results, [1.0, 0.0], lambda_param=0.5, top_k=10)
        assert "mmr_rank" in output[0]
        assert output[0]["mmr_rank"] == 1
        assert output[1]["mmr_rank"] == 2

    def test_top_k_limits_results(self):
        """apply_mmr_reranking should respect top_k"""
        from microservices.memory_service.mmr_reranker import apply_mmr_reranking
        results = [
            {"id": "a", "similarity_score": 0.9, "embedding": [1.0, 0.0]},
            {"id": "b", "similarity_score": 0.8, "embedding": [0.0, 1.0]},
            {"id": "c", "similarity_score": 0.7, "embedding": [0.5, 0.5]},
        ]
        output = apply_mmr_reranking(results, [1.0, 0.0], lambda_param=0.5, top_k=2)
        assert len(output) == 2

    def test_embeddings_stripped_from_output(self):
        """Embeddings should be removed from output to keep response size small"""
        from microservices.memory_service.mmr_reranker import apply_mmr_reranking
        results = [
            {"id": "a", "similarity_score": 0.9, "embedding": [1.0, 0.0]},
        ]
        output = apply_mmr_reranking(results, [1.0, 0.0], lambda_param=0.5, top_k=10)
        assert "embedding" not in output[0]

    def test_lambda_boundary_zero(self):
        """Lambda=0 should work without error"""
        from microservices.memory_service.mmr_reranker import apply_mmr_reranking
        results = [
            {"id": "a", "similarity_score": 0.9, "embedding": [1.0, 0.0]},
            {"id": "b", "similarity_score": 0.8, "embedding": [0.0, 1.0]},
        ]
        output = apply_mmr_reranking(results, [1.0, 0.0], lambda_param=0.0, top_k=10)
        assert len(output) == 2

    def test_lambda_boundary_one(self):
        """Lambda=1 should work without error and preserve relevance order"""
        from microservices.memory_service.mmr_reranker import apply_mmr_reranking
        results = [
            {"id": "a", "similarity_score": 0.9, "embedding": [1.0, 0.0]},
            {"id": "b", "similarity_score": 0.8, "embedding": [0.0, 1.0]},
            {"id": "c", "similarity_score": 0.7, "embedding": [0.5, 0.5]},
        ]
        output = apply_mmr_reranking(results, [1.0, 0.0], lambda_param=1.0, top_k=10)
        # Pure relevance order
        assert output[0]["id"] == "a"
        assert output[1]["id"] == "b"
        assert output[2]["id"] == "c"
