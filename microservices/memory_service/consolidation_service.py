"""
Memory Consolidation Service

Periodic pipeline promoting frequently-accessed episodic memories into semantic
knowledge. Mirrors human memory consolidation — episodic experiences that are
accessed repeatedly and have aged sufficiently are clustered by similarity,
summarized by an LLM, and stored as semantic memories.

Pipeline steps:
  1. Find candidates: episodic memories with access_count >= N, age > M days, not yet consolidated
  2. Cluster candidates by embedding similarity (Qdrant)
  3. For each cluster, summarize via LLM into a semantic concept
  4. Store new semantic memory
  5. Tag original episodics as "consolidated"
  6. Create bidirectional associations between new semantic and source episodics

Fixes #118
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

from isa_model.inference_client import AsyncISAModel

if TYPE_CHECKING:
    from .episodic_service import EpisodicMemoryService
    from .semantic_service import SemanticMemoryService
    from .association_service import AssociationService

logger = logging.getLogger(__name__)


# ==================== Configuration ====================


@dataclass
class ConsolidationConfig:
    """Configuration for the consolidation pipeline."""

    min_access_count: int = 5
    """Minimum access_count for an episodic memory to be a candidate."""

    min_age_days: int = 7
    """Minimum age (in days) for an episodic memory to be a candidate."""

    max_cluster_size: int = 10
    """Maximum number of episodics in a single cluster."""

    similarity_threshold: float = 0.7
    """Minimum embedding similarity to group memories in the same cluster."""


# ==================== Consolidation Prompt ====================

CONSOLIDATION_SYSTEM_PROMPT = """You are a memory consolidation expert. Given these related personal experiences/events, extract the general knowledge or principle they represent.

Experiences:
{formatted_episodes}

Produce a single semantic memory with:
- concept_type: the type of knowledge (principle, pattern, preference, skill, etc.)
- definition: a concise statement of the general knowledge
- category: the domain (personal, professional, health, social, etc.)
- properties: key attributes as a dict
- related_concepts: list of related concept names

Return as JSON."""


# ==================== Service ====================


class ConsolidationService:
    """
    Service for consolidating episodic memories into semantic knowledge.

    Designed for dependency injection — accepts sub-services and config.
    """

    def __init__(
        self,
        episodic_service: "EpisodicMemoryService",
        semantic_service: "SemanticMemoryService",
        association_service: "AssociationService",
        config: Optional[ConsolidationConfig] = None,
        model_url: Optional[str] = None,
    ):
        self.episodic_service = episodic_service
        self.semantic_service = semantic_service
        self.association_service = association_service
        self.config = config or ConsolidationConfig()
        self.model_url = model_url or "http://localhost:8082"

        logger.info("ConsolidationService initialized")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def find_consolidation_candidates(
        self,
        user_id: str,
        config: Optional[ConsolidationConfig] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find episodic memories eligible for consolidation.

        Criteria:
          - access_count >= min_access_count
          - created_at < now - min_age_days
          - NOT already tagged with "consolidated"

        Args:
            user_id: User whose memories to scan.
            config: Override config (uses self.config if None).

        Returns:
            List of candidate episodic memory dicts.
        """
        cfg = config or self.config
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=cfg.min_age_days)

        candidates = await self.episodic_service.repository.query_candidates(
            user_id=user_id,
            min_access_count=cfg.min_access_count,
            max_created_at=cutoff_date,
            exclude_tag="consolidated",
        )

        logger.info(
            f"Found {len(candidates)} consolidation candidates for user {user_id} "
            f"(min_access={cfg.min_access_count}, min_age={cfg.min_age_days}d)"
        )
        return candidates

    async def cluster_related_episodics(
        self,
        candidates: List[Dict[str, Any]],
        config: Optional[ConsolidationConfig] = None,
    ) -> List[List[Dict[str, Any]]]:
        """
        Group candidate episodic memories into clusters by embedding similarity.

        Uses a greedy union-find approach:
          - For each candidate, find similar candidates via Qdrant
          - Merge into the same cluster if similarity >= threshold
          - Respect max_cluster_size

        Args:
            candidates: List of episodic memory dicts (must include 'id' and 'embedding').
            config: Override config.

        Returns:
            List of clusters (each cluster is a list of memory dicts).
        """
        cfg = config or self.config

        if not candidates:
            return []

        # Build a lookup by ID
        mem_by_id: Dict[str, Dict[str, Any]] = {m["id"]: m for m in candidates}
        candidate_ids = set(mem_by_id.keys())

        # Union-Find for clustering
        parent: Dict[str, str] = {mid: mid for mid in candidate_ids}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        # For each candidate, find similar ones via Qdrant
        for mem in candidates:
            embedding = mem.get("embedding")
            if not embedding:
                continue

            try:
                filter_conditions = {
                    "must": [
                        {"field": "user_id", "match": {"keyword": mem["user_id"]}}
                    ]
                }

                async with self.episodic_service.qdrant:
                    search_results = await self.episodic_service.qdrant.search_with_filter(
                        collection_name="episodic_memories",
                        vector=embedding,
                        filter_conditions=filter_conditions,
                        limit=cfg.max_cluster_size,
                        score_threshold=cfg.similarity_threshold,
                        with_payload=True,
                    )

                for result in (search_results or []):
                    rid = str(result["id"])
                    if rid in candidate_ids and rid != mem["id"]:
                        union(mem["id"], rid)

            except Exception as e:
                logger.warning(f"Error during clustering search for {mem['id']}: {e}")

        # Group by root
        clusters_map: Dict[str, List[Dict[str, Any]]] = {}
        for mid in candidate_ids:
            root = find(mid)
            clusters_map.setdefault(root, []).append(mem_by_id[mid])

        # Enforce max_cluster_size by splitting large clusters
        clusters: List[List[Dict[str, Any]]] = []
        for cluster_members in clusters_map.values():
            while len(cluster_members) > cfg.max_cluster_size:
                clusters.append(cluster_members[: cfg.max_cluster_size])
                cluster_members = cluster_members[cfg.max_cluster_size :]
            if cluster_members:
                clusters.append(cluster_members)

        logger.info(f"Created {len(clusters)} clusters from {len(candidates)} candidates")
        return clusters

    async def consolidate_cluster(
        self,
        cluster: List[Dict[str, Any]],
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Consolidate a single cluster of episodic memories into one semantic memory.

        Steps:
          a. Call LLM to summarize the cluster into a semantic concept
          b. Store the new semantic memory (PostgreSQL + Qdrant)
          c. Tag original episodics with "consolidated"
          d. Create bidirectional associations between new semantic and source episodics

        Args:
            cluster: List of episodic memory dicts.
            user_id: User ID.

        Returns:
            Dict with success, semantic_memory_id, source_episodic_ids.
        """
        source_ids = [m["id"] for m in cluster]

        try:
            # Step a: LLM summarization
            llm_result = await self._summarize_cluster(cluster)
            if not llm_result:
                return {
                    "success": False,
                    "semantic_memory_id": None,
                    "source_episodic_ids": source_ids,
                    "error": "LLM summarization failed",
                }

            # Step b: Create semantic memory
            semantic_id = str(uuid.uuid4())
            definition = llm_result.get("definition", "")
            content = definition  # Use definition as content

            # Generate embedding for the new semantic memory
            embedding = await self.semantic_service._generate_embedding(content)

            memory_data = {
                "id": semantic_id,
                "user_id": user_id,
                "memory_type": "semantic",
                "content": content,
                "concept_type": llm_result.get("concept_type", "consolidated"),
                "definition": definition,
                "properties": llm_result.get("properties", {}),
                "abstraction_level": "high",
                "related_concepts": llm_result.get("related_concepts", []),
                "category": llm_result.get("category", "general"),
                "importance_score": 0.7,  # Consolidated memories are important
                "confidence": 0.8,
                "access_count": 0,
                "tags": ["consolidated_from_episodic"],
                "context": {
                    "source_episodic_ids": source_ids,
                    "consolidation_date": datetime.now(timezone.utc).isoformat(),
                },
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }

            await self.semantic_service.repository.create(memory_data)

            # Store embedding in Qdrant
            if embedding:
                try:
                    async with self.semantic_service.qdrant:
                        await self.semantic_service.qdrant.upsert_points(
                            "semantic_memories",
                            [
                                {
                                    "id": semantic_id,
                                    "vector": embedding,
                                    "payload": {
                                        "user_id": user_id,
                                        "concept_type": llm_result.get("concept_type", "consolidated"),
                                        "category": llm_result.get("category", "general"),
                                        "abstraction_level": "high",
                                        "created_at": datetime.now(timezone.utc).isoformat(),
                                    },
                                }
                            ],
                        )
                except Exception as e:
                    logger.warning(f"Failed to store semantic embedding in Qdrant: {e}")

            # Step c: Tag original episodics as consolidated
            for ep_mem in cluster:
                existing_tags = list(ep_mem.get("tags", []))
                if "consolidated" not in existing_tags:
                    existing_tags.append("consolidated")
                try:
                    await self.episodic_service.repository.update(
                        ep_mem["id"],
                        {"tags": existing_tags},
                        user_id,
                    )
                except Exception as e:
                    logger.warning(f"Failed to tag episodic {ep_mem['id']} as consolidated: {e}")

            # Step d: Create bidirectional associations
            for ep_id in source_ids:
                try:
                    # Forward: semantic -> episodic (consolidated_from)
                    forward_id = str(uuid.uuid4())
                    await self.association_service.repository.create({
                        "id": forward_id,
                        "user_id": user_id,
                        "source_memory_type": "semantic",
                        "source_memory_id": semantic_id,
                        "target_memory_type": "episodic",
                        "target_memory_id": ep_id,
                        "association_type": "consolidated_from",
                        "strength": 1.0,
                        "auto_discovered": True,
                        "confirmation_count": 0,
                    })

                    # Reverse: episodic -> semantic (consolidated_into)
                    reverse_id = str(uuid.uuid4())
                    await self.association_service.repository.create({
                        "id": reverse_id,
                        "user_id": user_id,
                        "source_memory_type": "episodic",
                        "source_memory_id": ep_id,
                        "target_memory_type": "semantic",
                        "target_memory_id": semantic_id,
                        "association_type": "consolidated_into",
                        "strength": 1.0,
                        "auto_discovered": True,
                        "confirmation_count": 0,
                    })
                except Exception as e:
                    logger.warning(
                        f"Failed to create association for episodic {ep_id}: {e}"
                    )

            logger.info(
                f"Consolidated {len(source_ids)} episodics into semantic {semantic_id}"
            )

            return {
                "success": True,
                "semantic_memory_id": semantic_id,
                "source_episodic_ids": source_ids,
            }

        except Exception as e:
            logger.error(f"Error consolidating cluster: {e}", exc_info=True)
            return {
                "success": False,
                "semantic_memory_id": None,
                "source_episodic_ids": source_ids,
                "error": str(e),
            }

    async def run_consolidation(
        self,
        user_id: Optional[str] = None,
        config: Optional[ConsolidationConfig] = None,
    ) -> Dict[str, Any]:
        """
        Run the full consolidation pipeline.

        Steps:
          1. Find consolidation candidates
          2. Cluster related episodics
          3. Consolidate each cluster
          4. Return summary

        Args:
            user_id: If provided, only consolidate this user's memories.
            config: Override default config.

        Returns:
            Dict with consolidated_count, new_semantic_ids, source_episodic_ids.
        """
        cfg = config or self.config
        result = {
            "consolidated_count": 0,
            "new_semantic_ids": [],
            "source_episodic_ids": [],
        }

        if not user_id:
            logger.warning("run_consolidation called without user_id — skipping")
            return result

        # Step 1: Find candidates
        candidates = await self.find_consolidation_candidates(user_id, cfg)
        if not candidates:
            logger.info(f"No consolidation candidates for user {user_id}")
            return result

        # Step 2: Cluster
        clusters = await self.cluster_related_episodics(candidates, cfg)
        if not clusters:
            return result

        # Step 3: Consolidate each cluster
        for cluster in clusters:
            cluster_result = await self.consolidate_cluster(cluster, user_id)
            if cluster_result["success"]:
                result["consolidated_count"] += 1
                result["new_semantic_ids"].append(cluster_result["semantic_memory_id"])
                result["source_episodic_ids"].extend(cluster_result["source_episodic_ids"])

        logger.info(
            f"Consolidation complete for user {user_id}: "
            f"{result['consolidated_count']} clusters consolidated, "
            f"{len(result['source_episodic_ids'])} episodics processed"
        )

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _summarize_cluster(
        self, cluster: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to summarize a cluster of episodic memories into a semantic concept.

        Returns:
            Parsed JSON dict with concept_type, definition, category, properties, related_concepts.
            None on failure.
        """
        # Format episodes for the prompt
        formatted_episodes = []
        for i, mem in enumerate(cluster, 1):
            episode_text = f"{i}. {mem.get('content', 'No content')}"
            if mem.get("event_type"):
                episode_text += f" [type: {mem['event_type']}]"
            if mem.get("location"):
                episode_text += f" [location: {mem['location']}]"
            if mem.get("episode_date"):
                episode_text += f" [date: {mem['episode_date']}]"
            formatted_episodes.append(episode_text)

        episodes_text = "\n".join(formatted_episodes)

        system_prompt = CONSOLIDATION_SYSTEM_PROMPT.format(
            formatted_episodes=episodes_text
        )

        user_prompt = (
            f"Consolidate these {len(cluster)} experiences into a single semantic memory.\n\n"
            f"Experiences:\n{episodes_text}\n\n"
            "Return JSON with: concept_type, definition, category, properties, related_concepts"
        )

        try:
            async with AsyncISAModel(base_url=self.model_url) as client:
                response = await client.chat.completions.create(
                    model="gpt-4.1-nano",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    provider="openai",
                )

            content = response.choices[0].message.content
            if not content or not content.strip():
                logger.warning("Empty LLM response for consolidation")
                return None

            parsed = json.loads(content)
            return parsed

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM consolidation response: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in LLM consolidation: {e}")
            return None
