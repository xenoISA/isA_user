"""
Association Service
A-MEM-style memory cross-linking using vector similarity and LLM classification.

At extraction time, new memories are linked to related existing memories
using the memory_associations table (migration 008). Inspired by A-MEM's
Zettelkasten approach.
"""

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from typing import Dict, List, Optional, Any

import os
from isa_model.inference_client import AsyncISAModel
from isa_common import AsyncQdrantClient

from .association_repository import AssociationRepository

logger = logging.getLogger(__name__)

# Valid association types (excludes "unrelated" — those are never stored)
VALID_ASSOCIATION_TYPES = {"similar_to", "elaborates", "elaborated_by", "contradicts"}

# Qdrant collection names by memory type
COLLECTION_MAP = {
    "factual": "factual_memories",
    "procedural": "procedural_memories",
    "episodic": "episodic_memories",
    "semantic": "semantic_memories",
    "working": "working_memories",
}


def get_reverse_association_type(association_type: str) -> str:
    """
    Get the reverse direction of an association type for bidirectional links.

    - similar_to <-> similar_to  (symmetric)
    - contradicts <-> contradicts (symmetric)
    - elaborates <-> elaborated_by
    """
    reverse_map = {
        "similar_to": "similar_to",
        "contradicts": "contradicts",
        "elaborates": "elaborated_by",
        "elaborated_by": "elaborates",
    }
    return reverse_map.get(association_type, association_type)


class AssociationService:
    """
    Service for creating and querying A-MEM-style memory associations.

    Workflow:
    1. find_related_memories  — vector search across all Qdrant collections
    2. create_associations    — LLM classifies candidates, stores links
    3. get_related_memories   — query existing cross-links
    """

    def __init__(
        self,
        repository: Optional[AssociationRepository] = None,
        qdrant_client: Optional[AsyncQdrantClient] = None,
        model_url: Optional[str] = None,
    ):
        self.repository = repository or AssociationRepository()

        self.qdrant = qdrant_client or AsyncQdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", 6333)),
            user_id="memory_service",
        )

        self.model_url = model_url or os.getenv("ISA_MODEL_URL", "http://localhost:8082")

        # Map of memory_type -> sub-service (set externally by MemoryService)
        self._memory_service_map: Dict[str, Any] = {}

        logger.info("AssociationService initialized")

    def _get_model_client(self):
        """Create a new ISA Model async client"""
        return AsyncISAModel(base_url=self.model_url)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def find_related_memories(
        self,
        memory_id: str,
        memory_type: str,
        user_id: str,
        embedding: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search Qdrant for top-k similar existing memories across all types.

        Args:
            memory_id: ID of the newly created memory (excluded from results)
            memory_type: Type of the new memory
            user_id: User ID for filtering
            embedding: Vector embedding of the new memory
            top_k: Number of candidates to return

        Returns:
            List of candidate dicts with id, memory_type, content, score
        """
        candidates: List[Dict[str, Any]] = []

        filter_conditions = {
            "must": [
                {"field": "user_id", "match": {"keyword": user_id}}
            ]
        }

        # Search all Qdrant collections in parallel
        async def _search_collection(mem_type: str, collection_name: str):
            try:
                async with self.qdrant:
                    return mem_type, await self.qdrant.search_with_filter(
                        collection_name=collection_name,
                        vector=embedding,
                        filter_conditions=filter_conditions,
                        limit=top_k,
                        score_threshold=0.3,
                        with_payload=True,
                    )
            except Exception as e:
                logger.warning(f"Error searching {collection_name}: {e}")
                return mem_type, None

        search_results = await asyncio.gather(
            *[
                _search_collection(mt, cn)
                for mt, cn in COLLECTION_MAP.items()
            ]
        )

        for mem_type, results in search_results:
            for r in (results or []):
                rid = str(r["id"])
                # Exclude the source memory itself
                if rid == memory_id and mem_type == memory_type:
                    continue
                candidates.append({
                    "id": rid,
                    "memory_type": mem_type,
                    "score": r.get("score", 0.0),
                    "payload": r.get("payload", {}),
                })

        # Sort by score descending and take top_k
        candidates.sort(key=lambda c: c["score"], reverse=True)
        candidates = candidates[:top_k]

        # Batch-fetch content from PostgreSQL (one query per memory type)
        enriched = await self._batch_fetch_memory_content(candidates, user_id)

        return enriched

    async def create_associations(
        self,
        source_memory_id: str,
        source_type: str,
        source_content: str,
        candidates: List[Dict[str, Any]],
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Use LLM to classify candidates and store associations.

        Args:
            source_memory_id: ID of the source memory
            source_type: Type of the source memory
            source_content: Content of the source memory
            candidates: List of candidate dicts from find_related_memories
            user_id: User ID

        Returns:
            Dict with created_count and association_ids
        """
        if not candidates:
            return {"created_count": 0, "association_ids": []}

        try:
            # Ask LLM to classify relationships
            classifications = await self._classify_associations(
                source_content=source_content,
                source_type=source_type,
                candidates=candidates,
            )

            created_count = 0
            association_ids = []

            for classification in classifications:
                assoc_type = classification.get("association_type")
                target_id = classification.get("target_memory_id")
                target_type = classification.get("target_memory_type")
                strength = classification.get("strength", 0.5)

                if not assoc_type or assoc_type not in VALID_ASSOCIATION_TYPES:
                    continue
                if not target_id:
                    continue

                # Resolve target_type from candidates if not in classification
                if not target_type:
                    for c in candidates:
                        if c["id"] == target_id:
                            target_type = c["memory_type"]
                            break
                if not target_type:
                    continue

                # Create forward association (source -> target)
                forward_id = str(uuid.uuid4())
                await self.repository.create({
                    "id": forward_id,
                    "user_id": user_id,
                    "source_memory_type": source_type,
                    "source_memory_id": source_memory_id,
                    "target_memory_type": target_type,
                    "target_memory_id": target_id,
                    "association_type": assoc_type,
                    "strength": strength,
                    "auto_discovered": True,
                    "confirmation_count": 0,
                })

                # Create reverse association (target -> source)
                reverse_type = get_reverse_association_type(assoc_type)
                reverse_id = str(uuid.uuid4())
                await self.repository.create({
                    "id": reverse_id,
                    "user_id": user_id,
                    "source_memory_type": target_type,
                    "source_memory_id": target_id,
                    "target_memory_type": source_type,
                    "target_memory_id": source_memory_id,
                    "association_type": reverse_type,
                    "strength": strength,
                    "auto_discovered": True,
                    "confirmation_count": 0,
                })

                created_count += 1
                association_ids.append(forward_id)

                logger.info(
                    f"Created association: {source_memory_id}({source_type}) "
                    f"--[{assoc_type}]--> {target_id}({target_type}) "
                    f"strength={strength}"
                )

            return {"created_count": created_count, "association_ids": association_ids}

        except Exception as e:
            logger.error(f"Error creating associations: {e}")
            return {"created_count": 0, "association_ids": []}

    async def get_related_memories(
        self,
        memory_id: str,
        memory_type: str,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve cross-linked memories for a given memory.

        Queries both directions of associations and resolves the "other" memory.

        Args:
            memory_id: Memory ID to find related memories for
            memory_type: Memory type
            user_id: User ID

        Returns:
            List of dicts with related memory info, association type, and strength
        """
        associations = await self.repository.get_bidirectional_associations(
            memory_id=memory_id,
            memory_type=memory_type,
            user_id=user_id,
        )

        if not associations:
            return []

        # Collect related memory references
        related_refs = []
        for assoc in associations:
            if (assoc["source_memory_id"] == memory_id
                    and assoc["source_memory_type"] == memory_type):
                related_refs.append({
                    "id": assoc["target_memory_id"],
                    "memory_type": assoc["target_memory_type"],
                })
            else:
                related_refs.append({
                    "id": assoc["source_memory_id"],
                    "memory_type": assoc["source_memory_type"],
                })

        # Batch-fetch all related memory content (one query per type)
        content_map = await self._batch_fetch_content_map(related_refs, user_id)

        results = []
        for assoc, ref in zip(associations, related_refs):
            results.append({
                "association_id": assoc.get("id"),
                "related_memory_id": ref["id"],
                "related_memory_type": ref["memory_type"],
                "association_type": assoc.get("association_type"),
                "strength": assoc.get("strength", 0.5),
                "content": content_map.get((ref["id"], ref["memory_type"])),
                "created_at": assoc.get("created_at"),
            })

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_memory_content(
        self, memory_id: str, memory_type: str, user_id: str
    ) -> Optional[str]:
        """Fetch memory content from the appropriate sub-service repository."""
        service = self._memory_service_map.get(memory_type)
        if not service:
            return None
        try:
            memory = await service.repository.get_by_id(memory_id, user_id)
            if memory:
                return memory.get("content")
        except Exception as e:
            logger.warning(f"Error fetching content for {memory_type}/{memory_id}: {e}")
        return None

    async def _batch_fetch_memory_content(
        self,
        candidates: List[Dict[str, Any]],
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Batch-fetch content for candidates, grouping by memory_type to avoid N+1.

        Returns only candidates where content was successfully fetched.
        """
        content_map = await self._batch_fetch_content_map(candidates, user_id)

        enriched = []
        for c in candidates:
            content = content_map.get((c["id"], c["memory_type"]))
            if content:
                c["content"] = content
                enriched.append(c)
        return enriched

    async def _batch_fetch_content_map(
        self,
        refs: List[Dict[str, Any]],
        user_id: str,
    ) -> Dict[tuple, Optional[str]]:
        """
        Fetch content for a list of memory references, batched by type.

        Groups IDs by memory_type, issues one concurrent query per type,
        and returns a dict mapping (memory_id, memory_type) -> content.
        """
        # Group IDs by memory type
        ids_by_type: Dict[str, List[str]] = defaultdict(list)
        for ref in refs:
            ids_by_type[ref["memory_type"]].append(ref["id"])

        content_map: Dict[tuple, Optional[str]] = {}

        async def _fetch_type(mem_type: str, mem_ids: List[str]):
            service = self._memory_service_map.get(mem_type)
            if not service:
                return
            try:
                # Use batch method if available, otherwise fall back to individual
                repo = service.repository
                if hasattr(repo, "get_by_ids"):
                    memories = await repo.get_by_ids(mem_ids, user_id)
                    for m in (memories or []):
                        mid = m.get("id")
                        if mid:
                            content_map[(mid, mem_type)] = m.get("content")
                else:
                    # Fallback: concurrent individual fetches within this type
                    results = await asyncio.gather(
                        *[repo.get_by_id(mid, user_id) for mid in mem_ids],
                        return_exceptions=True,
                    )
                    for mid, result in zip(mem_ids, results):
                        if isinstance(result, Exception):
                            logger.warning(
                                f"Error fetching {mem_type}/{mid}: {result}"
                            )
                        elif result:
                            content_map[(mid, mem_type)] = result.get("content")
            except Exception as e:
                logger.warning(f"Error batch-fetching {mem_type}: {e}")

        await asyncio.gather(
            *[_fetch_type(mt, ids) for mt, ids in ids_by_type.items()]
        )

        return content_map

    async def _classify_associations(
        self,
        source_content: str,
        source_type: str,
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to classify relationships between source memory and candidates.

        Returns list of dicts with target_memory_id, target_memory_type,
        association_type, and strength.
        """
        candidate_descriptions = []
        for i, c in enumerate(candidates):
            candidate_descriptions.append(
                f"  Candidate {i+1}: id={c['id']}, type={c['memory_type']}, "
                f"content=\"{c.get('content', 'N/A')[:200]}\", "
                f"similarity_score={c.get('score', 0.0):.2f}"
            )

        candidates_text = "\n".join(candidate_descriptions)

        system_prompt = """You are a memory association classifier. Given a source memory and candidate related memories, classify each relationship.

For each candidate, decide:
- association_type: one of "similar_to", "elaborates", "contradicts", or "unrelated"
  - similar_to: memories about the same topic or closely related information
  - elaborates: the candidate adds detail, context, or explanation to the source
  - contradicts: the candidate contains conflicting information
  - unrelated: no meaningful relationship (do NOT include these in output)
- strength: 0.0 to 1.0 indicating how strong the relationship is

Return ONLY valid JSON with an "associations" array. Only include non-unrelated associations.

Example:
{"associations": [
  {"target_memory_id": "id1", "target_memory_type": "factual", "association_type": "similar_to", "strength": 0.8},
  {"target_memory_id": "id2", "target_memory_type": "episodic", "association_type": "elaborates", "strength": 0.6}
]}"""

        user_prompt = f"""Source memory (type={source_type}):
"{source_content[:500]}"

Candidate memories:
{candidates_text}

Classify each candidate's relationship to the source memory. Return JSON only."""

        try:
            client = self._get_model_client()
            async with client:
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
                logger.warning("Empty LLM response for association classification")
                return []

            parsed = json.loads(content)
            associations = parsed.get("associations", [])

            # Filter to valid association types only
            valid = [
                a for a in associations
                if a.get("association_type") in VALID_ASSOCIATION_TYPES
            ]

            return valid

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM association response: {e}")
            return []
        except Exception as e:
            logger.error(f"Error in LLM association classification: {e}")
            return []
