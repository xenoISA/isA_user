"""
Graph Client — HTTP client for Neo4j knowledge graph queries via isA_Data

Provides synchronous (request-scoped) graph lookups:
- Entity search
- Neighbor traversal
- Multi-hop graph traversal
- Health check

Uses aiohttp with a 5-second timeout and graceful degradation.
Service discovery via Consul or DATA_SERVICE_URL env var fallback.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 5  # seconds
_DEFAULT_URL = "http://localhost:8300"


class GraphClient:
    """
    Async HTTP client for isA_Data graph endpoints.

    Graph building is async (NATS events) — this client is only for retrieval.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = _DEFAULT_TIMEOUT,
        consul_registry=None,
    ):
        self.base_url = base_url or os.getenv("DATA_SERVICE_URL", _DEFAULT_URL)
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._consul = consul_registry

    # ------------------------------------------------------------------
    # Entity search
    # ------------------------------------------------------------------

    async def search_entities(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
        entity_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Search for entities in the knowledge graph.

        Args:
            query: Search text
            user_id: Scope results to this user
            limit: Max results
            entity_types: Optional filter by entity type

        Returns:
            {"entities": [...], "total": int} or fallback with "error"
        """
        params: Dict[str, Any] = {
            "query": query,
            "user_id": user_id,
            "limit": limit,
        }
        if entity_types:
            params["entity_types"] = ",".join(entity_types)

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{self.base_url}/api/v1/graph/entities/search",
                    params=params,
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        body = await resp.text()
                        logger.warning(
                            "Graph entity search returned %d: %s", resp.status, body
                        )
                        return {"entities": [], "total": 0, "error": body}
        except Exception as exc:
            logger.warning("Graph entity search failed: %s", exc)
            return {"entities": [], "total": 0, "error": str(exc)}

    # ------------------------------------------------------------------
    # Neighbor traversal
    # ------------------------------------------------------------------

    async def get_entity_neighbors(
        self,
        entity_id: str,
        max_depth: int = 1,
        relationship_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get neighbors of an entity up to max_depth hops.

        Returns:
            {"neighbors": [...], "entity_id": str} or fallback
        """
        params: Dict[str, Any] = {
            "max_depth": max_depth,
        }
        if relationship_types:
            params["relationship_types"] = ",".join(relationship_types)

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{self.base_url}/api/v1/graph/entities/{entity_id}/neighbors",
                    params=params,
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        logger.warning(
                            "Graph neighbor lookup returned %d for %s",
                            resp.status,
                            entity_id,
                        )
                        return {"neighbors": [], "entity_id": entity_id}
        except Exception as exc:
            logger.warning("Graph neighbor lookup failed: %s", exc)
            return {"neighbors": [], "entity_id": entity_id, "error": str(exc)}

    # ------------------------------------------------------------------
    # Multi-hop traversal
    # ------------------------------------------------------------------

    async def traverse_graph(
        self,
        start_entity: str,
        relationship_types: List[str],
        max_depth: int = 2,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform a multi-hop traversal from a starting entity.

        Returns:
            {"paths": [...], "total_paths": int} or fallback
        """
        payload: Dict[str, Any] = {
            "start_entity": start_entity,
            "relationship_types": relationship_types,
            "max_depth": max_depth,
        }
        if user_id:
            payload["user_id"] = user_id

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/api/v1/graph/traverse",
                    json=payload,
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        body = await resp.text()
                        logger.warning(
                            "Graph traversal returned %d: %s", resp.status, body
                        )
                        return {"paths": [], "total_paths": 0, "error": body}
        except Exception as exc:
            logger.warning("Graph traversal failed: %s", exc)
            return {"paths": [], "total_paths": 0, "error": str(exc)}

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """
        Check if isA_Data graph service is reachable.

        Returns:
            True if healthy, False otherwise.
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{self.base_url}/api/v1/graph/health",
                ) as resp:
                    return resp.status == 200
        except Exception as exc:
            logger.debug("Graph health check failed: %s", exc)
            return False
