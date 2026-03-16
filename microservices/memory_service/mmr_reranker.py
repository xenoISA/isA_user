"""
MMR (Maximal Marginal Relevance) Re-ranking Module

Implements lightweight MMR re-ranking for memory search results.
Promotes diversity in search results while maintaining relevance.

Algorithm:
    MMR = arg max [lambda * Sim(doc, query) - (1 - lambda) * max(Sim(doc, selected_docs))]

References:
    Carbonell & Goldstein, 1998 — "The Use of MMR, Diversity-Based Reranking
    for Reordering Documents and Producing Summaries"
"""

import logging
import math
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine similarity in [-1.0, 1.0], or 0.0 if either vector is zero.
    """
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def mmr_rerank(
    query_embedding: List[float],
    doc_embeddings: List[List[float]],
    doc_scores: List[float],
    lambda_param: float = 0.5,
    top_k: int = 10,
) -> List[int]:
    """
    MMR re-ranking: iteratively select documents that are relevant to the query
    but diverse from already-selected documents.

    Args:
        query_embedding: The query vector (unused for relevance since we use doc_scores,
                         but available for future direct similarity computation).
        doc_embeddings: List of document embedding vectors.
        doc_scores: Original relevance scores for each document (e.g., from Qdrant).
        lambda_param: Trade-off between relevance (1.0) and diversity (0.0).
        top_k: Maximum number of documents to select.

    Returns:
        List of document indices in MMR-ranked order.
    """
    if not doc_embeddings:
        return []

    n = len(doc_embeddings)
    selected: List[int] = []
    remaining = list(range(n))

    while len(selected) < top_k and remaining:
        best_score = -math.inf
        best_idx = -1

        for idx in remaining:
            relevance = lambda_param * doc_scores[idx]

            diversity_penalty = 0.0
            if selected:
                max_sim = max(
                    cosine_similarity(doc_embeddings[idx], doc_embeddings[s])
                    for s in selected
                )
                diversity_penalty = (1.0 - lambda_param) * max_sim

            mmr_score = relevance - diversity_penalty

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        selected.append(best_idx)
        remaining.remove(best_idx)

    return selected


def apply_mmr_reranking(
    results: List[Dict[str, Any]],
    query_embedding: List[float],
    lambda_param: float = 0.5,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Apply MMR re-ranking to a list of search result dicts.

    Each result dict is expected to have:
      - 'similarity_score': float  (original relevance score)
      - 'embedding': List[float]   (document embedding, optional)

    If embeddings are missing from results, returns them unchanged (fallback).

    Args:
        results: List of search result dicts from the vector search pipeline.
        query_embedding: The query embedding vector.
        lambda_param: MMR lambda (0=diversity, 1=relevance).
        top_k: Max results to return.

    Returns:
        Re-ranked list of result dicts with 'mmr_rank' added and 'embedding' removed.
    """
    if not results:
        return []

    # Check if embeddings are available
    embeddings = [r.get("embedding") for r in results]
    has_embeddings = all(e is not None and len(e) > 0 for e in embeddings)

    if not has_embeddings:
        # Fallback: return as-is without re-ranking
        logger.warning("MMR re-ranking skipped: embeddings not available in results")
        output = []
        for i, r in enumerate(results):
            entry = {k: v for k, v in r.items() if k != "embedding"}
            entry["mmr_rank"] = i + 1
            output.append(entry)
        return output

    scores = [r.get("similarity_score", 0.0) for r in results]

    ranked_indices = mmr_rerank(
        query_embedding=query_embedding,
        doc_embeddings=embeddings,
        doc_scores=scores,
        lambda_param=lambda_param,
        top_k=top_k,
    )

    # Build output: re-ordered results with mmr_rank, without embedding
    output = []
    for rank, idx in enumerate(ranked_indices, start=1):
        entry = {k: v for k, v in results[idx].items() if k != "embedding"}
        entry["mmr_rank"] = rank
        output.append(entry)

    return output
