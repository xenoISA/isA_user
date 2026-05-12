"""
FalkorDB-backed memory graph adapter.

This module keeps user memory graph ownership inside memory_service. It is a
local graph boundary over isa_common.AsyncFalkorClient, not an isA_Data proxy.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_GRAPH = "memory_graph"
_DEFAULT_TIMEOUT_MS = 1500


def _optional_int(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning("Ignoring invalid Falkor port value: %s", value)
        return None


def _clamp_limit(value: int, *, default: int = 10, maximum: int = 100) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, maximum))


def _clamp_depth(value: int, *, default: int = 1, maximum: int = 5) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, maximum))


def _node_properties(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        if isinstance(value.get("properties"), dict):
            return value["properties"]
        return value
    props = getattr(value, "properties", None)
    return props if isinstance(props, dict) else {}


class MemoryGraphAdapter:
    """
    Memory-domain graph adapter backed by FalkorDB.

    The public methods intentionally mirror the legacy GraphClient shape so
    endpoint wiring can move from isA_Data HTTP calls to this local adapter in a
    small follow-up change.
    """

    def __init__(
        self,
        *,
        client: Any = None,
        client_factory: Optional[Callable[..., Any]] = None,
        graph_name: Optional[str] = None,
        timeout_ms: Optional[int] = None,
    ):
        self._client = client
        self._client_factory = client_factory
        self.graph_name = (
            graph_name
            or os.getenv("MEMORY_GRAPH_NAME")
            or os.getenv("FALKOR_GRAPH")
            or _DEFAULT_GRAPH
        )
        self.host = os.getenv("FALKOR_HOST") or os.getenv("FALKORDB_HOST")
        self.port = _optional_int(
            os.getenv("FALKOR_PORT") or os.getenv("FALKORDB_PORT")
        )
        self.timeout_ms = int(
            os.getenv("MEMORY_GRAPH_TIMEOUT_MS", str(timeout_ms or _DEFAULT_TIMEOUT_MS))
        )

    async def _get_client(self):
        if self._client is None:
            factory = self._client_factory
            if factory is None:
                from isa_common import AsyncFalkorClient

                factory = AsyncFalkorClient
            kwargs = {"graph": self.graph_name}
            if self.host:
                kwargs["host"] = self.host
            if self.port:
                kwargs["port"] = self.port
            self._client = factory(**kwargs)
        return self._client

    async def _reset_client(self) -> None:
        client = self._client
        self._client = None
        if client is not None and hasattr(client, "close"):
            try:
                await client.close()
            except Exception as exc:
                logger.debug("Memory graph client close after failure failed: %s", exc)

    async def health_check(self) -> bool:
        """Return True when FalkorDB is reachable for the memory graph."""
        try:
            client = await self._get_client()
            result = await client.health_check()
            healthy = bool(result and result.get("healthy"))
            if not healthy:
                await self._reset_client()
            return healthy
        except Exception as exc:
            logger.debug("Memory graph health check failed: %s", exc)
            await self._reset_client()
            return False

    async def search_entities(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
        entity_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Search memory graph entities for a single user."""
        try:
            client = await self._get_client()
            effective_limit = _clamp_limit(limit)
            normalized_types = [t for t in (entity_types or []) if t]
            cypher = (
                "MATCH (e:MemoryEntity) "
                "WHERE e.user_id = $user_id "
                "  AND ($entity_types IS NULL OR e.type IN $entity_types) "
                "  AND (toLower(coalesce(e.name, '')) CONTAINS toLower($query) "
                "       OR toLower(coalesce(e.canonical_name, '')) CONTAINS toLower($query) "
                "       OR toLower(coalesce(e.content, '')) CONTAINS toLower($query)) "
                "RETURN e.id AS id, e.name AS name, e.type AS type, "
                "       e.memory_id AS memory_id, e.content AS content, "
                "       coalesce(e.relevance_score, 1.0) AS relevance_score, "
                "       properties(e) AS properties "
                "ORDER BY relevance_score DESC "
                "LIMIT $limit"
            )
            rows = await client.query(
                cypher,
                params={
                    "query": query,
                    "user_id": user_id,
                    "entity_types": normalized_types or None,
                    "limit": effective_limit,
                },
                graph=self.graph_name,
                timeout_ms=self.timeout_ms,
                read_only=True,
            )
            entities = [self._entity_from_row(row) for row in rows or []]
            return {"entities": entities, "total": len(entities)}
        except Exception as exc:
            logger.warning("Memory graph entity search failed: %s", exc)
            await self._reset_client()
            return {"entities": [], "total": 0, "error": str(exc)}

    async def get_entity_neighbors(
        self,
        entity_id: str,
        max_depth: int = 1,
        relationship_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Return neighboring memory graph entities."""
        depth = _clamp_depth(max_depth)
        try:
            client = await self._get_client()
            normalized_types = [t for t in (relationship_types or []) if t]
            cypher = (
                f"MATCH p = (e:MemoryEntity {{id: $entity_id}})-[*1..{depth}]-(n:MemoryEntity) "
                "WHERE $relationship_types IS NULL "
                "   OR any(rel IN relationships(p) WHERE type(rel) IN $relationship_types) "
                "RETURN DISTINCT n.id AS id, n.name AS name, n.type AS type, "
                "       n.memory_id AS memory_id, n.content AS content, "
                "       length(p) AS depth, [rel IN relationships(p) | type(rel)] AS relationship_path, "
                "       properties(n) AS properties "
                "ORDER BY depth ASC "
                "LIMIT $limit"
            )
            rows = await client.query(
                cypher,
                params={
                    "entity_id": entity_id,
                    "relationship_types": normalized_types or None,
                    "limit": 100,
                },
                graph=self.graph_name,
                timeout_ms=self.timeout_ms,
                read_only=True,
            )
            neighbors = [self._neighbor_from_row(row) for row in rows or []]
            return {"neighbors": neighbors, "entity_id": entity_id}
        except Exception as exc:
            logger.warning("Memory graph neighbor lookup failed: %s", exc)
            await self._reset_client()
            return {"neighbors": [], "entity_id": entity_id, "error": str(exc)}

    async def traverse_graph(
        self,
        start_entity: str,
        relationship_types: List[str],
        max_depth: int = 2,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform a bounded traversal from a memory graph entity."""
        depth = _clamp_depth(max_depth, default=2)
        try:
            client = await self._get_client()
            normalized_types = [t for t in (relationship_types or []) if t]
            cypher = (
                f"MATCH path = (start:MemoryEntity)-[*1..{depth}]-(target:MemoryEntity) "
                "WHERE (start.id = $start_entity OR start.name = $start_entity) "
                "  AND ($user_id IS NULL OR start.user_id = $user_id) "
                "  AND ($relationship_types IS NULL "
                "       OR any(rel IN relationships(path) WHERE type(rel) IN $relationship_types)) "
                "RETURN [node IN nodes(path) | properties(node)] AS nodes, "
                "       [rel IN relationships(path) | type(rel)] AS relationships, "
                "       length(path) AS depth "
                "ORDER BY depth ASC "
                "LIMIT $limit"
            )
            rows = await client.query(
                cypher,
                params={
                    "start_entity": start_entity,
                    "relationship_types": normalized_types or None,
                    "user_id": user_id,
                    "limit": 100,
                },
                graph=self.graph_name,
                timeout_ms=self.timeout_ms,
                read_only=True,
            )
            paths = [
                {
                    "nodes": row.get("nodes", []),
                    "relationships": row.get("relationships", []),
                    "depth": row.get("depth", 0),
                }
                for row in rows or []
            ]
            return {"paths": paths, "total_paths": len(paths)}
        except Exception as exc:
            logger.warning("Memory graph traversal failed: %s", exc)
            await self._reset_client()
            return {"paths": [], "total_paths": 0, "error": str(exc)}

    async def close(self) -> None:
        client = self._client
        if client is not None and hasattr(client, "close"):
            await client.close()

    @staticmethod
    def _entity_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
        props = _node_properties(row.get("node") or row.get("properties") or row)
        return {
            "id": row.get("id") or props.get("id"),
            "name": row.get("name") or props.get("name"),
            "type": row.get("type") or props.get("type"),
            "memory_id": row.get("memory_id") or props.get("memory_id"),
            "content": row.get("content") or props.get("content"),
            "relevance_score": row.get(
                "relevance_score", props.get("relevance_score", 1.0)
            ),
            "properties": props,
        }

    @classmethod
    def _neighbor_from_row(cls, row: Dict[str, Any]) -> Dict[str, Any]:
        entity = cls._entity_from_row(row)
        entity["depth"] = row.get("depth", 1)
        entity["relationship_path"] = row.get("relationship_path", [])
        return entity
