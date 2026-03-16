"""
Hybrid Search — Merge vector similarity and graph traversal results.

Combines Qdrant vector search results with Neo4j graph traversal results
using configurable weights. Handles deduplication, score normalization,
and source tagging.

Algorithm:
    1. Normalize scores within each result set to [0, 1]
    2. Compute final_score = vector_weight * norm_vector_score + graph_weight * norm_graph_score
    3. Deduplicate by memory_id (keep combined score, tag as "both")
    4. Sort by final_score descending
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def _normalize_scores(scores: List[float]) -> List[float]:
    """
    Normalize a list of scores to [0, 1] range using min-max normalization.

    If all scores are equal (or single element), returns all 1.0.
    """
    if not scores:
        return []

    max_score = max(scores)
    min_score = min(scores)
    spread = max_score - min_score

    if spread == 0.0:
        return [0.5] * len(scores)

    return [(s - min_score) / spread for s in scores]


def merge_hybrid_results(
    vector_results: List[dict],
    graph_results: List[dict],
    vector_weight: float = 0.6,
    graph_weight: float = 0.4,
) -> List[dict]:
    """
    Merge vector and graph results with weighted scoring.

    Args:
        vector_results: Results from Qdrant vector similarity search.
            Expected keys: memory_id, similarity_score, plus any metadata.
        graph_results: Results from Neo4j graph traversal.
            Expected keys: memory_id, relevance_score, plus any metadata.
        vector_weight: Weight for vector similarity scores (default 0.6).
        graph_weight: Weight for graph traversal scores (default 0.4).

    Returns:
        Merged, deduplicated list of result dicts sorted by final_score descending.
        Each result includes: memory_id, final_score, source ("vector"/"graph"/"both").
    """
    if not vector_results and not graph_results:
        return []

    # --- Validate and normalize weights ---
    vector_weight = max(0.0, vector_weight)
    graph_weight = max(0.0, graph_weight)
    total = vector_weight + graph_weight
    if total > 0:
        vector_weight /= total
        graph_weight /= total
    else:
        vector_weight, graph_weight = 0.5, 0.5

    # --- Step 1: Normalize scores within each set ---

    vec_raw_scores = [r.get("similarity_score", 0.0) for r in vector_results]
    graph_raw_scores = [r.get("relevance_score", 0.0) for r in graph_results]

    vec_norm = _normalize_scores(vec_raw_scores)
    graph_norm = _normalize_scores(graph_raw_scores)

    # --- Step 2: Build per-memory_id entries ---

    # Dict keyed by memory_id → accumulated result
    merged: Dict[str, dict] = {}

    for i, result in enumerate(vector_results):
        mid = result.get("memory_id")
        if not mid:
            continue
        weighted_score = vector_weight * vec_norm[i]

        entry = {**result, "final_score": weighted_score, "source": "vector"}
        # Remove raw similarity_score from output (replaced by final_score)
        entry.pop("similarity_score", None)
        merged[mid] = entry

    for i, result in enumerate(graph_results):
        mid = result.get("memory_id")
        if not mid:
            continue
        weighted_score = graph_weight * graph_norm[i]

        if mid in merged:
            # --- Step 3: Deduplicate — combine scores, tag as "both" ---
            merged[mid]["final_score"] += weighted_score
            merged[mid]["source"] = "both"
        else:
            entry = {**result, "final_score": weighted_score, "source": "graph"}
            entry.pop("relevance_score", None)
            merged[mid] = entry

    # --- Step 4: Sort by final_score descending ---

    results = sorted(merged.values(), key=lambda r: r["final_score"], reverse=True)

    return results
