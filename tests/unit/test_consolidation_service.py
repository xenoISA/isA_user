"""
Unit tests for memory consolidation pipeline (episodic -> semantic promotion).

Tests the consolidation logic, candidate identification, clustering, LLM summarization,
and association creation. No I/O — all dependencies are mocked.

Fixes #118
"""

import json
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from microservices.memory_service.consolidation_service import (
    ConsolidationConfig,
    ConsolidationService,
)


# ==================== Helpers ====================


def _make_episodic_memory(
    memory_id=None,
    user_id="usr_test_001",
    content="Had a meeting with Alice about project X",
    access_count=10,
    created_at=None,
    tags=None,
    importance_score=0.5,
    embedding=None,
):
    """Create a test episodic memory dict."""
    if memory_id is None:
        memory_id = str(uuid.uuid4())
    if created_at is None:
        created_at = datetime.now(timezone.utc) - timedelta(days=30)
    if tags is None:
        tags = []
    if embedding is None:
        embedding = [0.1] * 1536
    return {
        "id": memory_id,
        "user_id": user_id,
        "memory_type": "episodic",
        "content": content,
        "event_type": "meeting",
        "location": "office",
        "participants": ["Alice"],
        "emotional_valence": 0.3,
        "vividness": 0.7,
        "importance_score": importance_score,
        "confidence": 0.8,
        "access_count": access_count,
        "tags": tags,
        "context": {},
        "created_at": created_at,
        "updated_at": created_at,
        "last_accessed_at": created_at,
        "embedding": embedding,
    }


def _make_mock_services():
    """Create mock episodic, semantic, and association services."""
    episodic_service = MagicMock()
    episodic_service.repository = AsyncMock()
    episodic_service.qdrant = AsyncMock()
    episodic_service._generate_embedding = AsyncMock(return_value=[0.1] * 1536)

    semantic_service = MagicMock()
    semantic_service.repository = AsyncMock()
    semantic_service.qdrant = AsyncMock()
    semantic_service._generate_embedding = AsyncMock(return_value=[0.2] * 1536)

    association_service = MagicMock()
    association_service.repository = AsyncMock()

    return episodic_service, semantic_service, association_service


def _make_consolidation_service(
    episodic_service=None,
    semantic_service=None,
    association_service=None,
    config=None,
    model_url="http://localhost:8082",
):
    """Create a ConsolidationService with mocked dependencies."""
    if episodic_service is None or semantic_service is None or association_service is None:
        ep, sem, assoc = _make_mock_services()
        episodic_service = episodic_service or ep
        semantic_service = semantic_service or sem
        association_service = association_service or assoc

    return ConsolidationService(
        episodic_service=episodic_service,
        semantic_service=semantic_service,
        association_service=association_service,
        config=config or ConsolidationConfig(),
        model_url=model_url,
    )


# ==================== L1: ConsolidationConfig tests ====================


class TestConsolidationConfig:
    """Test configuration defaults and custom values."""

    def test_default_values(self):
        config = ConsolidationConfig()
        assert config.min_access_count == 5
        assert config.min_age_days == 7
        assert config.max_cluster_size == 10
        assert config.similarity_threshold == 0.7

    def test_custom_values(self):
        config = ConsolidationConfig(
            min_access_count=10,
            min_age_days=14,
            max_cluster_size=20,
            similarity_threshold=0.8,
        )
        assert config.min_access_count == 10
        assert config.min_age_days == 14
        assert config.max_cluster_size == 20
        assert config.similarity_threshold == 0.8


# ==================== L2: Candidate Identification ====================


class TestFindConsolidationCandidates:
    """Test identification of episodic memories eligible for consolidation."""

    @pytest.mark.asyncio
    async def test_finds_candidates_above_access_threshold(self):
        """Memories with access_count >= min_access_count should be candidates."""
        ep_svc, sem_svc, assoc_svc = _make_mock_services()
        old_date = datetime.now(timezone.utc) - timedelta(days=30)

        eligible = _make_episodic_memory(access_count=10, created_at=old_date)
        ineligible = _make_episodic_memory(access_count=2, created_at=old_date)

        ep_svc.repository.query_candidates = AsyncMock(return_value=[eligible])

        svc = _make_consolidation_service(ep_svc, sem_svc, assoc_svc)
        candidates = await svc.find_consolidation_candidates("usr_test_001")

        assert len(candidates) == 1
        assert candidates[0]["access_count"] == 10

    @pytest.mark.asyncio
    async def test_finds_candidates_above_age_threshold(self):
        """Memories must be older than min_age_days."""
        ep_svc, sem_svc, assoc_svc = _make_mock_services()

        old = _make_episodic_memory(
            access_count=10,
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
        )
        ep_svc.repository.query_candidates = AsyncMock(return_value=[old])

        svc = _make_consolidation_service(ep_svc, sem_svc, assoc_svc)
        candidates = await svc.find_consolidation_candidates("usr_test_001")
        assert len(candidates) == 1

    @pytest.mark.asyncio
    async def test_excludes_already_consolidated(self):
        """Memories with 'consolidated' tag should be excluded."""
        ep_svc, sem_svc, assoc_svc = _make_mock_services()

        # The repository query should filter these out, so return empty
        ep_svc.repository.query_candidates = AsyncMock(return_value=[])

        svc = _make_consolidation_service(ep_svc, sem_svc, assoc_svc)
        candidates = await svc.find_consolidation_candidates("usr_test_001")
        assert len(candidates) == 0

    @pytest.mark.asyncio
    async def test_no_candidates_returns_empty(self):
        """When no memories meet criteria, return empty list."""
        ep_svc, sem_svc, assoc_svc = _make_mock_services()
        ep_svc.repository.query_candidates = AsyncMock(return_value=[])

        svc = _make_consolidation_service(ep_svc, sem_svc, assoc_svc)
        candidates = await svc.find_consolidation_candidates("usr_test_001")
        assert candidates == []


# ==================== L2: Clustering ====================


class TestClusterRelatedEpisodics:
    """Test grouping of related episodic memories by embedding similarity."""

    @pytest.mark.asyncio
    async def test_clusters_similar_memories(self):
        """Memories with similar embeddings should be grouped together."""
        ep_svc, sem_svc, assoc_svc = _make_mock_services()

        # Two similar memories (same embedding) and one different
        similar_embedding = [0.1] * 1536
        different_embedding = [0.9] * 1536

        mem_a = _make_episodic_memory(memory_id="a", embedding=similar_embedding, content="Meeting about project X")
        mem_b = _make_episodic_memory(memory_id="b", embedding=similar_embedding, content="Discussion about project X")
        mem_c = _make_episodic_memory(memory_id="c", embedding=different_embedding, content="Went to the gym")

        # Mock Qdrant search to return similar results
        ep_svc.qdrant.search_with_filter = AsyncMock(side_effect=[
            # For mem_a: b is similar, c is not
            [{"id": "b", "score": 0.95, "payload": {}}],
            # For mem_b: a is similar
            [{"id": "a", "score": 0.95, "payload": {}}],
            # For mem_c: nothing similar enough
            [],
        ])
        ep_svc.qdrant.__aenter__ = AsyncMock(return_value=ep_svc.qdrant)
        ep_svc.qdrant.__aexit__ = AsyncMock(return_value=None)

        svc = _make_consolidation_service(ep_svc, sem_svc, assoc_svc)
        clusters = await svc.cluster_related_episodics([mem_a, mem_b, mem_c])

        # Should have at least one cluster with a and b together
        assert len(clusters) >= 1
        cluster_ids = [[m["id"] for m in c] for c in clusters]
        assert any("a" in ids and "b" in ids for ids in cluster_ids)

    @pytest.mark.asyncio
    async def test_respects_max_cluster_size(self):
        """Clusters should not exceed max_cluster_size."""
        ep_svc, sem_svc, assoc_svc = _make_mock_services()

        config = ConsolidationConfig(max_cluster_size=2)
        memories = [_make_episodic_memory(memory_id=str(i)) for i in range(5)]

        # All memories are similar to each other
        ep_svc.qdrant.search_with_filter = AsyncMock(return_value=[
            {"id": str(j), "score": 0.9, "payload": {}} for j in range(5)
        ])
        ep_svc.qdrant.__aenter__ = AsyncMock(return_value=ep_svc.qdrant)
        ep_svc.qdrant.__aexit__ = AsyncMock(return_value=None)

        svc = _make_consolidation_service(ep_svc, sem_svc, assoc_svc, config=config)
        clusters = await svc.cluster_related_episodics(memories)

        for cluster in clusters:
            assert len(cluster) <= config.max_cluster_size

    @pytest.mark.asyncio
    async def test_single_memory_forms_own_cluster(self):
        """A single memory with no similar peers should form its own cluster."""
        ep_svc, sem_svc, assoc_svc = _make_mock_services()

        mem = _make_episodic_memory(memory_id="solo")
        ep_svc.qdrant.search_with_filter = AsyncMock(return_value=[])
        ep_svc.qdrant.__aenter__ = AsyncMock(return_value=ep_svc.qdrant)
        ep_svc.qdrant.__aexit__ = AsyncMock(return_value=None)

        svc = _make_consolidation_service(ep_svc, sem_svc, assoc_svc)
        clusters = await svc.cluster_related_episodics([mem])

        assert len(clusters) == 1
        assert len(clusters[0]) == 1
        assert clusters[0][0]["id"] == "solo"


# ==================== L2: LLM Summarization ====================


class TestConsolidateCluster:
    """Test LLM-driven summarization of episodic cluster into semantic memory."""

    @pytest.mark.asyncio
    async def test_creates_semantic_from_cluster(self):
        """Consolidating a cluster should produce a new semantic memory."""
        ep_svc, sem_svc, assoc_svc = _make_mock_services()

        cluster = [
            _make_episodic_memory(memory_id="ep1", content="Had coffee with Bob to discuss ML"),
            _make_episodic_memory(memory_id="ep2", content="Presented ML results to team"),
        ]

        llm_response = json.dumps({
            "concept_type": "pattern",
            "definition": "Regular engagement with ML work and team collaboration",
            "category": "professional",
            "properties": {"domain": "machine_learning", "frequency": "regular"},
            "related_concepts": ["machine learning", "team collaboration"],
        })

        # Mock the LLM call
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_response
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Mock embedding generation
        sem_svc._generate_embedding = AsyncMock(return_value=[0.3] * 1536)
        sem_svc.repository.create = AsyncMock(return_value=True)
        sem_svc.qdrant.upsert_points = AsyncMock(return_value=True)
        sem_svc.qdrant.__aenter__ = AsyncMock(return_value=sem_svc.qdrant)
        sem_svc.qdrant.__aexit__ = AsyncMock(return_value=None)

        # Mock episodic update for tagging
        ep_svc.repository.update = AsyncMock(return_value=True)

        # Mock association creation
        assoc_svc.repository.create = AsyncMock(return_value=True)

        svc = _make_consolidation_service(ep_svc, sem_svc, assoc_svc)

        with patch(
            "microservices.memory_service.consolidation_service.AsyncISAModel",
            return_value=mock_client,
        ):
            result = await svc.consolidate_cluster(cluster, "usr_test_001")

        assert result["success"] is True
        assert result["semantic_memory_id"] is not None
        assert len(result["source_episodic_ids"]) == 2

    @pytest.mark.asyncio
    async def test_tags_originals_as_consolidated(self):
        """After consolidation, source episodics should be tagged 'consolidated'."""
        ep_svc, sem_svc, assoc_svc = _make_mock_services()

        cluster = [
            _make_episodic_memory(memory_id="ep1", tags=[]),
            _make_episodic_memory(memory_id="ep2", tags=["important"]),
        ]

        llm_response = json.dumps({
            "concept_type": "pattern",
            "definition": "Test consolidation",
            "category": "test",
            "properties": {},
            "related_concepts": [],
        })

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_response
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        sem_svc._generate_embedding = AsyncMock(return_value=[0.3] * 1536)
        sem_svc.repository.create = AsyncMock(return_value=True)
        sem_svc.qdrant.upsert_points = AsyncMock(return_value=True)
        sem_svc.qdrant.__aenter__ = AsyncMock(return_value=sem_svc.qdrant)
        sem_svc.qdrant.__aexit__ = AsyncMock(return_value=None)

        ep_svc.repository.update = AsyncMock(return_value=True)
        assoc_svc.repository.create = AsyncMock(return_value=True)

        svc = _make_consolidation_service(ep_svc, sem_svc, assoc_svc)

        with patch(
            "microservices.memory_service.consolidation_service.AsyncISAModel",
            return_value=mock_client,
        ):
            await svc.consolidate_cluster(cluster, "usr_test_001")

        # Verify update was called for each episodic to add consolidated tag
        assert ep_svc.repository.update.call_count == 2
        for call in ep_svc.repository.update.call_args_list:
            args, kwargs = call
            update_data = args[1] if len(args) > 1 else kwargs.get("data", {})
            assert "consolidated" in update_data.get("tags", [])

    @pytest.mark.asyncio
    async def test_creates_associations_between_semantic_and_episodics(self):
        """Consolidated semantic should be linked to source episodics via associations."""
        ep_svc, sem_svc, assoc_svc = _make_mock_services()

        cluster = [
            _make_episodic_memory(memory_id="ep1"),
            _make_episodic_memory(memory_id="ep2"),
        ]

        llm_response = json.dumps({
            "concept_type": "pattern",
            "definition": "Test concept",
            "category": "test",
            "properties": {},
            "related_concepts": [],
        })

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_response
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        sem_svc._generate_embedding = AsyncMock(return_value=[0.3] * 1536)
        sem_svc.repository.create = AsyncMock(return_value=True)
        sem_svc.qdrant.upsert_points = AsyncMock(return_value=True)
        sem_svc.qdrant.__aenter__ = AsyncMock(return_value=sem_svc.qdrant)
        sem_svc.qdrant.__aexit__ = AsyncMock(return_value=None)

        ep_svc.repository.update = AsyncMock(return_value=True)
        assoc_svc.repository.create = AsyncMock(return_value=True)

        svc = _make_consolidation_service(ep_svc, sem_svc, assoc_svc)

        with patch(
            "microservices.memory_service.consolidation_service.AsyncISAModel",
            return_value=mock_client,
        ):
            result = await svc.consolidate_cluster(cluster, "usr_test_001")

        # Should create associations: 2 source episodics * 2 directions (forward + reverse)
        assert assoc_svc.repository.create.call_count == 4

    @pytest.mark.asyncio
    async def test_llm_failure_returns_error(self):
        """If LLM summarization fails, consolidation should return error."""
        ep_svc, sem_svc, assoc_svc = _make_mock_services()
        cluster = [_make_episodic_memory(memory_id="ep1")]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("LLM unavailable"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        svc = _make_consolidation_service(ep_svc, sem_svc, assoc_svc)

        with patch(
            "microservices.memory_service.consolidation_service.AsyncISAModel",
            return_value=mock_client,
        ):
            result = await svc.consolidate_cluster(cluster, "usr_test_001")

        assert result["success"] is False


# ==================== L2: Full Pipeline ====================


class TestRunConsolidation:
    """Test the full consolidation pipeline end-to-end (with mocked deps)."""

    @pytest.mark.asyncio
    async def test_full_pipeline_success(self):
        """Run consolidation should find candidates, cluster, consolidate, and return summary."""
        ep_svc, sem_svc, assoc_svc = _make_mock_services()

        old_date = datetime.now(timezone.utc) - timedelta(days=30)
        candidates = [
            _make_episodic_memory(memory_id="ep1", access_count=10, created_at=old_date),
            _make_episodic_memory(memory_id="ep2", access_count=8, created_at=old_date),
        ]

        ep_svc.repository.query_candidates = AsyncMock(return_value=candidates)

        # Mock qdrant for clustering — all similar
        ep_svc.qdrant.search_with_filter = AsyncMock(return_value=[
            {"id": "ep2", "score": 0.9, "payload": {}},
        ])
        ep_svc.qdrant.__aenter__ = AsyncMock(return_value=ep_svc.qdrant)
        ep_svc.qdrant.__aexit__ = AsyncMock(return_value=None)

        llm_response = json.dumps({
            "concept_type": "pattern",
            "definition": "Consolidated knowledge",
            "category": "professional",
            "properties": {},
            "related_concepts": [],
        })
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_response
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        sem_svc._generate_embedding = AsyncMock(return_value=[0.3] * 1536)
        sem_svc.repository.create = AsyncMock(return_value=True)
        sem_svc.qdrant.upsert_points = AsyncMock(return_value=True)
        sem_svc.qdrant.__aenter__ = AsyncMock(return_value=sem_svc.qdrant)
        sem_svc.qdrant.__aexit__ = AsyncMock(return_value=None)

        ep_svc.repository.update = AsyncMock(return_value=True)
        assoc_svc.repository.create = AsyncMock(return_value=True)

        svc = _make_consolidation_service(ep_svc, sem_svc, assoc_svc)

        with patch(
            "microservices.memory_service.consolidation_service.AsyncISAModel",
            return_value=mock_client,
        ):
            result = await svc.run_consolidation(user_id="usr_test_001")

        assert result["consolidated_count"] >= 1
        assert len(result["new_semantic_ids"]) >= 1
        assert len(result["source_episodic_ids"]) >= 1

    @pytest.mark.asyncio
    async def test_no_candidates_returns_zero_counts(self):
        """When no candidates exist, pipeline returns zero counts."""
        ep_svc, sem_svc, assoc_svc = _make_mock_services()
        ep_svc.repository.query_candidates = AsyncMock(return_value=[])

        svc = _make_consolidation_service(ep_svc, sem_svc, assoc_svc)
        result = await svc.run_consolidation(user_id="usr_test_001")

        assert result["consolidated_count"] == 0
        assert result["new_semantic_ids"] == []
        assert result["source_episodic_ids"] == []

    @pytest.mark.asyncio
    async def test_custom_config_passed_through(self):
        """Custom config values should be used during candidate search."""
        ep_svc, sem_svc, assoc_svc = _make_mock_services()
        ep_svc.repository.query_candidates = AsyncMock(return_value=[])

        config = ConsolidationConfig(min_access_count=20, min_age_days=30)
        svc = _make_consolidation_service(ep_svc, sem_svc, assoc_svc, config=config)
        result = await svc.run_consolidation(user_id="usr_test_001", config=config)

        # Verify query_candidates was called (with the right config via the service)
        ep_svc.repository.query_candidates.assert_called_once()
        assert result["consolidated_count"] == 0

    @pytest.mark.asyncio
    async def test_pipeline_with_single_candidate(self):
        """A single candidate should still be consolidated as its own cluster."""
        ep_svc, sem_svc, assoc_svc = _make_mock_services()

        old_date = datetime.now(timezone.utc) - timedelta(days=30)
        candidate = _make_episodic_memory(memory_id="solo", access_count=10, created_at=old_date)
        ep_svc.repository.query_candidates = AsyncMock(return_value=[candidate])

        # No similar memories found
        ep_svc.qdrant.search_with_filter = AsyncMock(return_value=[])
        ep_svc.qdrant.__aenter__ = AsyncMock(return_value=ep_svc.qdrant)
        ep_svc.qdrant.__aexit__ = AsyncMock(return_value=None)

        llm_response = json.dumps({
            "concept_type": "experience",
            "definition": "Single consolidated experience",
            "category": "personal",
            "properties": {},
            "related_concepts": [],
        })
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = llm_response
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        sem_svc._generate_embedding = AsyncMock(return_value=[0.3] * 1536)
        sem_svc.repository.create = AsyncMock(return_value=True)
        sem_svc.qdrant.upsert_points = AsyncMock(return_value=True)
        sem_svc.qdrant.__aenter__ = AsyncMock(return_value=sem_svc.qdrant)
        sem_svc.qdrant.__aexit__ = AsyncMock(return_value=None)

        ep_svc.repository.update = AsyncMock(return_value=True)
        assoc_svc.repository.create = AsyncMock(return_value=True)

        svc = _make_consolidation_service(ep_svc, sem_svc, assoc_svc)

        with patch(
            "microservices.memory_service.consolidation_service.AsyncISAModel",
            return_value=mock_client,
        ):
            result = await svc.run_consolidation(user_id="usr_test_001")

        assert result["consolidated_count"] == 1
        assert "solo" in result["source_episodic_ids"]


# ==================== L2: Consolidation Prompt ====================


class TestConsolidationPrompt:
    """Test that the LLM prompt is correctly formatted."""

    @pytest.mark.asyncio
    async def test_prompt_includes_episode_content(self):
        """The consolidation prompt should include content from all cluster episodes."""
        ep_svc, sem_svc, assoc_svc = _make_mock_services()

        cluster = [
            _make_episodic_memory(memory_id="ep1", content="Met Alice at cafe"),
            _make_episodic_memory(memory_id="ep2", content="Coffee with Alice again"),
        ]

        captured_prompt = None

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "concept_type": "pattern",
            "definition": "test",
            "category": "test",
            "properties": {},
            "related_concepts": [],
        })

        async def capture_create(**kwargs):
            nonlocal captured_prompt
            messages = kwargs.get("messages", [])
            for msg in messages:
                if msg.get("role") == "user":
                    captured_prompt = msg["content"]
            return mock_response

        mock_client.chat.completions.create = capture_create
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        sem_svc._generate_embedding = AsyncMock(return_value=[0.3] * 1536)
        sem_svc.repository.create = AsyncMock(return_value=True)
        sem_svc.qdrant.upsert_points = AsyncMock(return_value=True)
        sem_svc.qdrant.__aenter__ = AsyncMock(return_value=sem_svc.qdrant)
        sem_svc.qdrant.__aexit__ = AsyncMock(return_value=None)
        ep_svc.repository.update = AsyncMock(return_value=True)
        assoc_svc.repository.create = AsyncMock(return_value=True)

        svc = _make_consolidation_service(ep_svc, sem_svc, assoc_svc)

        with patch(
            "microservices.memory_service.consolidation_service.AsyncISAModel",
            return_value=mock_client,
        ):
            await svc.consolidate_cluster(cluster, "usr_test_001")

        assert captured_prompt is not None
        assert "Met Alice at cafe" in captured_prompt
        assert "Coffee with Alice again" in captured_prompt
