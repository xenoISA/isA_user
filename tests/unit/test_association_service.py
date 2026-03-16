"""
Unit tests for AssociationService — A-MEM-style memory cross-links

Tests the association service logic with fully mocked dependencies (repository, Qdrant, LLM).
No I/O required.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_repository():
    """Mock AssociationRepository"""
    repo = AsyncMock()
    repo.create = AsyncMock(return_value={"id": str(uuid.uuid4())})
    repo.get_associations_for_memory = AsyncMock(return_value=[])
    repo.get_bidirectional_associations = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_qdrant():
    """Mock Qdrant client with async context manager support"""
    qdrant = AsyncMock()
    qdrant.__aenter__ = AsyncMock(return_value=qdrant)
    qdrant.__aexit__ = AsyncMock(return_value=False)
    qdrant.search_with_filter = AsyncMock(return_value=[])
    return qdrant


@pytest.fixture
def mock_model_client():
    """Mock ISA Model client for LLM calls"""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    # Mock chat completion response
    mock_choice = MagicMock()
    mock_choice.message.content = '{"associations": []}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Mock embeddings response
    mock_embedding_data = MagicMock()
    mock_embedding_data.embedding = [0.1] * 1536
    mock_embedding_response = MagicMock()
    mock_embedding_response.data = [mock_embedding_data]
    client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

    return client


@pytest.fixture
def memory_service_map():
    """Mock memory service map for resolving memory types to services"""
    services = {}
    for mem_type in ["factual", "procedural", "episodic", "semantic", "working"]:
        svc = MagicMock()
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value={
            "id": f"mem-{mem_type}-1",
            "user_id": "user-123",
            "memory_type": mem_type,
            "content": f"Sample {mem_type} memory content",
            "importance_score": 0.7,
        })
        # get_by_ids returns a list of memories matching the requested IDs
        repo.get_by_ids = AsyncMock(side_effect=lambda ids, uid: [
            {"id": mid, "content": f"Content for {mid}", "memory_type": mem_type}
            for mid in ids
        ])
        svc.repository = repo
        services[mem_type] = svc
    return services


@pytest.fixture
def association_service(mock_repository, mock_qdrant, mock_model_client, memory_service_map):
    """Create AssociationService with all mocked dependencies"""
    from microservices.memory_service.association_service import AssociationService
    svc = AssociationService(
        repository=mock_repository,
        qdrant_client=mock_qdrant,
        model_url="http://mock-model:8082",
    )
    svc._memory_service_map = memory_service_map
    # Patch the ISA model client creation
    svc._get_model_client = MagicMock(return_value=mock_model_client)
    return svc


# ---------------------------------------------------------------------------
# Tests: find_related_memories
# ---------------------------------------------------------------------------

class TestFindRelatedMemories:
    """Test find_related_memories — Qdrant vector search for candidates"""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_similar_memories(self, association_service, mock_qdrant):
        """Should return empty list when Qdrant finds no matches"""
        mock_qdrant.search_with_filter.return_value = []

        result = await association_service.find_related_memories(
            memory_id="mem-1",
            memory_type="factual",
            user_id="user-123",
            embedding=[0.1] * 1536,
            top_k=5,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_candidates_from_multiple_collections(self, association_service, mock_qdrant):
        """Should search across all memory type collections"""
        mock_qdrant.search_with_filter.return_value = [
            {"id": "mem-2", "score": 0.85, "payload": {"user_id": "user-123"}},
            {"id": "mem-3", "score": 0.72, "payload": {"user_id": "user-123"}},
        ]

        # Mock content fetch to return content for found memories
        for svc in association_service._memory_service_map.values():
            svc.repository.get_by_id = AsyncMock(side_effect=lambda mid, **kw: {
                "id": mid, "content": f"content for {mid}", "memory_type": "factual",
            })

        result = await association_service.find_related_memories(
            memory_id="mem-1",
            memory_type="factual",
            user_id="user-123",
            embedding=[0.1] * 1536,
            top_k=5,
        )

        # Should have results from searching multiple collections
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_excludes_source_memory_from_same_collection(self, association_service, mock_qdrant):
        """Should not return the source memory from its own collection"""
        call_count = 0

        async def mock_search(collection_name, **kwargs):
            nonlocal call_count
            call_count += 1
            if collection_name == "factual_memories":
                # Source memory appears in its own collection
                return [
                    {"id": "mem-1", "score": 1.0, "payload": {"user_id": "user-123"}},
                    {"id": "mem-2", "score": 0.85, "payload": {"user_id": "user-123"}},
                ]
            return []  # Other collections return nothing

        mock_qdrant.search_with_filter = mock_search

        # Mock content fetch to return content for found memories
        for svc in association_service._memory_service_map.values():
            svc.repository.get_by_id = AsyncMock(side_effect=lambda mid, **kw: {
                "id": mid, "content": f"content for {mid}", "memory_type": "factual",
            })

        result = await association_service.find_related_memories(
            memory_id="mem-1",
            memory_type="factual",
            user_id="user-123",
            embedding=[0.1] * 1536,
            top_k=5,
        )

        ids = [r["id"] for r in result]
        assert "mem-1" not in ids
        assert "mem-2" in ids

    @pytest.mark.asyncio
    async def test_respects_top_k_limit(self, association_service, mock_qdrant):
        """Should limit results to top_k"""
        mock_qdrant.search_with_filter.return_value = [
            {"id": f"mem-{i}", "score": 0.9 - i * 0.1, "payload": {"user_id": "user-123"}}
            for i in range(2, 12)
        ]

        result = await association_service.find_related_memories(
            memory_id="mem-1",
            memory_type="factual",
            user_id="user-123",
            embedding=[0.1] * 1536,
            top_k=3,
        )

        assert len(result) <= 3


# ---------------------------------------------------------------------------
# Tests: create_associations
# ---------------------------------------------------------------------------

class TestCreateAssociations:
    """Test create_associations — LLM classification and DB storage"""

    @pytest.mark.asyncio
    async def test_creates_no_associations_when_llm_says_unrelated(
        self, association_service, mock_model_client, mock_repository
    ):
        """When LLM classifies all candidates as unrelated, no associations stored"""
        mock_choice = MagicMock()
        mock_choice.message.content = '{"associations": [{"target_memory_id": "mem-2", "association_type": "unrelated", "strength": 0.0}]}'
        mock_model_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        candidates = [
            {"id": "mem-2", "memory_type": "factual", "content": "Some content", "score": 0.7}
        ]

        result = await association_service.create_associations(
            source_memory_id="mem-1",
            source_type="factual",
            source_content="Source memory content",
            candidates=candidates,
            user_id="user-123",
        )

        assert result["created_count"] == 0
        mock_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_bidirectional_associations(
        self, association_service, mock_model_client, mock_repository
    ):
        """Should create both A->B and B->A associations"""
        mock_choice = MagicMock()
        mock_choice.message.content = '{"associations": [{"target_memory_id": "mem-2", "target_memory_type": "factual", "association_type": "similar_to", "strength": 0.8}]}'
        mock_model_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        candidates = [
            {"id": "mem-2", "memory_type": "factual", "content": "Related content", "score": 0.85}
        ]

        result = await association_service.create_associations(
            source_memory_id="mem-1",
            source_type="factual",
            source_content="Source content",
            candidates=candidates,
            user_id="user-123",
        )

        assert result["created_count"] == 1
        # Should have been called twice: forward + reverse
        assert mock_repository.create.call_count == 2

    @pytest.mark.asyncio
    async def test_supports_all_association_types(
        self, association_service, mock_model_client, mock_repository
    ):
        """Should handle similar_to, elaborates, and contradicts types"""
        mock_choice = MagicMock()
        mock_choice.message.content = '{"associations": [{"target_memory_id": "mem-2", "target_memory_type": "episodic", "association_type": "elaborates", "strength": 0.9}, {"target_memory_id": "mem-3", "target_memory_type": "semantic", "association_type": "contradicts", "strength": 0.6}]}'
        mock_model_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        candidates = [
            {"id": "mem-2", "memory_type": "episodic", "content": "Episode content", "score": 0.8},
            {"id": "mem-3", "memory_type": "semantic", "content": "Concept content", "score": 0.7},
        ]

        result = await association_service.create_associations(
            source_memory_id="mem-1",
            source_type="factual",
            source_content="Source content",
            candidates=candidates,
            user_id="user-123",
        )

        assert result["created_count"] == 2
        # 2 associations * 2 directions = 4 calls
        assert mock_repository.create.call_count == 4

    @pytest.mark.asyncio
    async def test_handles_llm_error_gracefully(
        self, association_service, mock_model_client, mock_repository
    ):
        """Should handle LLM errors without raising"""
        mock_model_client.chat.completions.create.side_effect = Exception("LLM error")

        candidates = [
            {"id": "mem-2", "memory_type": "factual", "content": "Content", "score": 0.8}
        ]

        result = await association_service.create_associations(
            source_memory_id="mem-1",
            source_type="factual",
            source_content="Source content",
            candidates=candidates,
            user_id="user-123",
        )

        assert result["created_count"] == 0
        mock_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_empty_candidates(
        self, association_service, mock_repository
    ):
        """Should return zero count for empty candidates"""
        result = await association_service.create_associations(
            source_memory_id="mem-1",
            source_type="factual",
            source_content="Source content",
            candidates=[],
            user_id="user-123",
        )

        assert result["created_count"] == 0


# ---------------------------------------------------------------------------
# Tests: get_related_memories
# ---------------------------------------------------------------------------

class TestGetRelatedMemories:
    """Test get_related_memories — retrieve cross-linked memories"""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_associations(
        self, association_service, mock_repository
    ):
        """Should return empty list when no associations exist"""
        mock_repository.get_bidirectional_associations.return_value = []

        result = await association_service.get_related_memories(
            memory_id="mem-1",
            memory_type="factual",
            user_id="user-123",
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_associated_memories_with_type_info(
        self, association_service, mock_repository, memory_service_map
    ):
        """Should return associations with memory content and relationship type"""
        mock_repository.get_bidirectional_associations.return_value = [
            {
                "id": "assoc-1",
                "source_memory_id": "mem-1",
                "source_memory_type": "factual",
                "target_memory_id": "mem-2",
                "target_memory_type": "episodic",
                "association_type": "similar_to",
                "strength": 0.85,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ]

        result = await association_service.get_related_memories(
            memory_id="mem-1",
            memory_type="factual",
            user_id="user-123",
        )

        assert len(result) == 1
        assert result[0]["association_type"] == "similar_to"
        assert result[0]["strength"] == 0.85

    @pytest.mark.asyncio
    async def test_resolves_correct_related_memory_id(
        self, association_service, mock_repository
    ):
        """When queried memory is the source, related = target and vice versa"""
        mock_repository.get_bidirectional_associations.return_value = [
            {
                "id": "assoc-1",
                "source_memory_id": "mem-1",
                "source_memory_type": "factual",
                "target_memory_id": "mem-2",
                "target_memory_type": "episodic",
                "association_type": "elaborates",
                "strength": 0.9,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": "assoc-2",
                "source_memory_id": "mem-3",
                "source_memory_type": "semantic",
                "target_memory_id": "mem-1",
                "target_memory_type": "factual",
                "association_type": "similar_to",
                "strength": 0.7,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ]

        result = await association_service.get_related_memories(
            memory_id="mem-1",
            memory_type="factual",
            user_id="user-123",
        )

        assert len(result) == 2
        related_ids = [r["related_memory_id"] for r in result]
        assert "mem-2" in related_ids
        assert "mem-3" in related_ids


# ---------------------------------------------------------------------------
# Tests: _classify_associations (LLM prompt logic)
# ---------------------------------------------------------------------------

class TestClassifyAssociations:
    """Test the LLM classification method"""

    @pytest.mark.asyncio
    async def test_parses_valid_llm_json_response(
        self, association_service, mock_model_client
    ):
        """Should parse well-formed LLM JSON response"""
        mock_choice = MagicMock()
        mock_choice.message.content = '{"associations": [{"target_memory_id": "mem-2", "target_memory_type": "factual", "association_type": "similar_to", "strength": 0.8}]}'
        mock_model_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        result = await association_service._classify_associations(
            source_content="The user's name is Alice",
            source_type="factual",
            candidates=[
                {"id": "mem-2", "memory_type": "factual", "content": "Alice lives in Tokyo", "score": 0.85}
            ],
        )

        assert len(result) == 1
        assert result[0]["association_type"] == "similar_to"

    @pytest.mark.asyncio
    async def test_filters_out_invalid_association_types(
        self, association_service, mock_model_client
    ):
        """Should ignore associations with unknown types"""
        mock_choice = MagicMock()
        mock_choice.message.content = '{"associations": [{"target_memory_id": "mem-2", "target_memory_type": "factual", "association_type": "some_random_type", "strength": 0.5}]}'
        mock_model_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        result = await association_service._classify_associations(
            source_content="Some content",
            source_type="factual",
            candidates=[
                {"id": "mem-2", "memory_type": "factual", "content": "Content", "score": 0.7}
            ],
        )

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_handles_malformed_llm_response(
        self, association_service, mock_model_client
    ):
        """Should return empty list on malformed JSON"""
        mock_choice = MagicMock()
        mock_choice.message.content = "This is not JSON"
        mock_model_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        result = await association_service._classify_associations(
            source_content="Source content",
            source_type="factual",
            candidates=[
                {"id": "mem-2", "memory_type": "factual", "content": "Content", "score": 0.8}
            ],
        )

        assert result == []


# ---------------------------------------------------------------------------
# Tests: AssociationRepository
# ---------------------------------------------------------------------------

class TestAssociationRepository:
    """Unit tests for the AssociationRepository model/data shapes"""

    def test_association_model_has_required_fields(self):
        """MemoryAssociation model should have all required fields"""
        from microservices.memory_service.models import MemoryAssociation

        assoc = MemoryAssociation(
            source_memory_id="mem-1",
            target_memory_id="mem-2",
            association_type="similar_to",
            strength=0.8,
            user_id="user-123",
        )

        assert assoc.source_memory_id == "mem-1"
        assert assoc.target_memory_id == "mem-2"
        assert assoc.association_type == "similar_to"
        assert assoc.strength == 0.8
        assert assoc.user_id == "user-123"

    def test_association_type_constants(self):
        """Should define valid association type constants"""
        from microservices.memory_service.association_service import VALID_ASSOCIATION_TYPES

        assert "similar_to" in VALID_ASSOCIATION_TYPES
        assert "elaborates" in VALID_ASSOCIATION_TYPES
        assert "contradicts" in VALID_ASSOCIATION_TYPES
        assert "unrelated" not in VALID_ASSOCIATION_TYPES


# ---------------------------------------------------------------------------
# Tests: Reverse association type logic
# ---------------------------------------------------------------------------

class TestReverseAssociationType:
    """Test the reverse association type mapping for bidirectional links"""

    def test_similar_to_is_symmetric(self):
        from microservices.memory_service.association_service import get_reverse_association_type
        assert get_reverse_association_type("similar_to") == "similar_to"

    def test_elaborates_reverses_to_elaborated_by(self):
        from microservices.memory_service.association_service import get_reverse_association_type
        assert get_reverse_association_type("elaborates") == "elaborated_by"

    def test_contradicts_is_symmetric(self):
        from microservices.memory_service.association_service import get_reverse_association_type
        assert get_reverse_association_type("contradicts") == "contradicts"

    def test_elaborated_by_reverses_to_elaborates(self):
        from microservices.memory_service.association_service import get_reverse_association_type
        assert get_reverse_association_type("elaborated_by") == "elaborates"
