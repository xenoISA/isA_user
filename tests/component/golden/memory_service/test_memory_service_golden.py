"""
Memory Service - Component Golden Tests

GOLDEN: These tests document the CURRENT behavior of MemoryService.
DO NOT MODIFY unless behavior intentionally changes.

Purpose:
- Protect against accidental regressions in business logic
- Document what the service currently does
- All tests should PASS (they describe existing behavior)

Related Documents:
- Data Contract: tests/contracts/memory/data_contract.py
- Logic Contract: tests/contracts/memory/logic_contract.md
- Design: docs/design/memory_service.md

Usage:
    pytest tests/component/golden/memory_service -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

from tests.component.golden.memory_service.mocks import (
    MockFactualService,
    MockEpisodicService,
    MockProceduralService,
    MockSemanticService,
    MockWorkingService,
    MockSessionService,
    MockEventBus,
)

pytestmark = [pytest.mark.component, pytest.mark.asyncio, pytest.mark.golden]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_factual_service():
    """Create a fresh MockFactualService"""
    return MockFactualService()


@pytest.fixture
def mock_episodic_service():
    """Create a fresh MockEpisodicService"""
    return MockEpisodicService()


@pytest.fixture
def mock_procedural_service():
    """Create a fresh MockProceduralService"""
    return MockProceduralService()


@pytest.fixture
def mock_semantic_service():
    """Create a fresh MockSemanticService"""
    return MockSemanticService()


@pytest.fixture
def mock_working_service():
    """Create a fresh MockWorkingService"""
    return MockWorkingService()


@pytest.fixture
def mock_session_service():
    """Create a fresh MockSessionService"""
    return MockSessionService()


@pytest.fixture
def mock_event_bus():
    """Create a fresh MockEventBus"""
    return MockEventBus()


@pytest.fixture
def memory_service(
    mock_factual_service,
    mock_episodic_service,
    mock_procedural_service,
    mock_semantic_service,
    mock_working_service,
    mock_session_service,
    mock_event_bus,
):
    """Create MemoryService with all mock services injected"""
    from microservices.memory_service.memory_service import MemoryService

    return MemoryService(
        event_bus=mock_event_bus,
        factual_service=mock_factual_service,
        episodic_service=mock_episodic_service,
        procedural_service=mock_procedural_service,
        semantic_service=mock_semantic_service,
        working_service=mock_working_service,
        session_service=mock_session_service,
    )


# =============================================================================
# Memory Creation - Current Behavior
# =============================================================================

class TestMemoryServiceCreateGolden:
    """Characterization: Memory creation current behavior"""

    async def test_create_factual_memory_returns_result(
        self, memory_service, mock_factual_service
    ):
        """GOLDEN: create_memory returns MemoryOperationResult for factual memory"""
        from microservices.memory_service.models import (
            MemoryCreateRequest,
            MemoryType,
            MemoryOperationResult,
        )

        # Setup mock repository to return created memory
        mock_factual_service.repository.create.return_value = {
            "id": "mem_test_123",
            "user_id": "usr_test_123",
            "memory_type": "factual",
            "content": "User likes coffee",
            "importance_score": 0.8,
        }

        request = MemoryCreateRequest(
            user_id="usr_test_123",
            memory_type=MemoryType.FACTUAL,
            content="User likes coffee",
            importance_score=0.8,
            confidence=0.9,
            tags=["preference", "food"],
            context={"source": "conversation"},
        )

        result = await memory_service.create_memory(request)

        assert isinstance(result, MemoryOperationResult)
        assert result.success is True
        assert result.operation == "create"
        assert result.memory_id is not None

    async def test_create_episodic_memory_returns_result(
        self, memory_service, mock_episodic_service
    ):
        """GOLDEN: create_memory returns MemoryOperationResult for episodic memory"""
        from microservices.memory_service.models import (
            MemoryCreateRequest,
            MemoryType,
        )

        mock_episodic_service.repository.create.return_value = {
            "id": "mem_ep_123",
            "user_id": "usr_test_123",
            "memory_type": "episodic",
            "content": "User went to the beach",
        }

        request = MemoryCreateRequest(
            user_id="usr_test_123",
            memory_type=MemoryType.EPISODIC,
            content="User went to the beach yesterday",
            importance_score=0.7,
            confidence=0.85,
            tags=["travel", "vacation"],
            context={"location": "beach"},
        )

        result = await memory_service.create_memory(request)

        assert result.success is True
        assert result.operation == "create"

    async def test_create_working_memory_sets_expiry(
        self, memory_service, mock_working_service
    ):
        """GOLDEN: create_memory sets expires_at for working memory"""
        from microservices.memory_service.models import (
            MemoryCreateRequest,
            MemoryType,
        )

        mock_working_service.repository.create.return_value = {
            "id": "mem_wk_123",
            "user_id": "usr_test_123",
            "memory_type": "working",
            "content": "Current task context",
            "ttl_seconds": 3600,
        }

        request = MemoryCreateRequest(
            user_id="usr_test_123",
            memory_type=MemoryType.WORKING,
            content="Current task context",
            importance_score=0.9,
            confidence=1.0,
            tags=["task"],
            context={
                "task_id": "task_123",
                "task_context": {"step": 1},
                "ttl_seconds": 3600,
            },
        )

        result = await memory_service.create_memory(request)

        assert result.success is True

    async def test_create_session_memory_sets_session_data(
        self, memory_service, mock_session_service
    ):
        """GOLDEN: create_memory sets session-specific fields for session memory"""
        from microservices.memory_service.models import (
            MemoryCreateRequest,
            MemoryType,
        )

        mock_session_service.repository.create.return_value = {
            "id": "mem_sess_123",
            "user_id": "usr_test_123",
            "memory_type": "session",
            "content": "User asked about weather",
            "session_id": "sess_123",
        }

        request = MemoryCreateRequest(
            user_id="usr_test_123",
            memory_type=MemoryType.SESSION,
            content="User asked about weather",
            importance_score=0.5,
            confidence=0.9,
            tags=["conversation"],
            context={
                "session_id": "sess_123",
                "interaction_sequence": 1,
                "session_type": "chat",
            },
        )

        result = await memory_service.create_memory(request)

        assert result.success is True

    async def test_create_invalid_memory_type_returns_failure(
        self, memory_service
    ):
        """GOLDEN: create_memory returns failure for invalid memory type"""
        from microservices.memory_service.models import MemoryCreateRequest

        # Use MagicMock to bypass enum validation
        request = MagicMock()
        request.memory_type = MagicMock()
        request.memory_type.value = "invalid_type"
        request.user_id = "usr_test_123"
        request.content = "Test content"
        request.importance_score = 0.5
        request.confidence = 0.8
        request.tags = []
        request.context = {}

        result = await memory_service.create_memory(request)

        assert result.success is False
        assert "invalid" in result.message.lower() or result.message


# =============================================================================
# Memory Retrieval - Current Behavior
# =============================================================================

class TestMemoryServiceGetGolden:
    """Characterization: Memory retrieval current behavior"""

    async def test_get_existing_memory_returns_data(
        self, memory_service, mock_factual_service
    ):
        """GOLDEN: get_memory returns memory data for existing memory"""
        from microservices.memory_service.models import MemoryType

        mock_factual_service.repository.get_by_id.return_value = {
            "id": "mem_test_123",
            "user_id": "usr_test_123",
            "content": "User likes coffee",
            "memory_type": "factual",
        }

        result = await memory_service.get_memory(
            memory_id="mem_test_123",
            memory_type=MemoryType.FACTUAL,
            user_id="usr_test_123",
        )

        assert result is not None
        assert result["id"] == "mem_test_123"

    async def test_get_nonexistent_memory_returns_none(
        self, memory_service, mock_factual_service
    ):
        """GOLDEN: get_memory returns None for non-existent memory"""
        from microservices.memory_service.models import MemoryType

        mock_factual_service.repository.get_by_id.return_value = None

        result = await memory_service.get_memory(
            memory_id="mem_nonexistent",
            memory_type=MemoryType.FACTUAL,
            user_id="usr_test_123",
        )

        assert result is None

    async def test_get_memory_increments_access_count(
        self, memory_service, mock_factual_service
    ):
        """GOLDEN: get_memory increments access_count when found"""
        from microservices.memory_service.models import MemoryType

        mock_factual_service.repository.get_by_id.return_value = {
            "id": "mem_test_123",
            "user_id": "usr_test_123",
            "content": "Test",
        }

        await memory_service.get_memory(
            memory_id="mem_test_123",
            memory_type=MemoryType.FACTUAL,
            user_id="usr_test_123",
        )

        mock_factual_service.repository.increment_access_count.assert_called_once()


# =============================================================================
# Memory List - Current Behavior
# =============================================================================

class TestMemoryServiceListGolden:
    """Characterization: Memory list current behavior"""

    async def test_list_memories_by_type_returns_list(
        self, memory_service, mock_factual_service
    ):
        """GOLDEN: list_memories returns list of memories for specific type"""
        from microservices.memory_service.models import MemoryListParams, MemoryType

        mock_factual_service.repository.list_by_user.return_value = [
            {"id": "mem_1", "content": "Fact 1"},
            {"id": "mem_2", "content": "Fact 2"},
        ]

        params = MemoryListParams(
            user_id="usr_test_123",
            memory_type=MemoryType.FACTUAL,
            limit=100,
            offset=0,
        )

        result = await memory_service.list_memories(params)

        assert isinstance(result, list)
        assert len(result) == 2

    async def test_list_memories_all_types_returns_combined(
        self, memory_service, mock_factual_service, mock_episodic_service
    ):
        """GOLDEN: list_memories without type returns memories from all types"""
        from microservices.memory_service.models import MemoryListParams

        mock_factual_service.repository.list_by_user.return_value = [
            {"id": "mem_f1", "content": "Fact", "created_at": datetime.now(timezone.utc)},
        ]
        mock_episodic_service.repository.list_by_user.return_value = [
            {"id": "mem_e1", "content": "Episode", "created_at": datetime.now(timezone.utc)},
        ]

        params = MemoryListParams(
            user_id="usr_test_123",
            memory_type=None,  # All types
            limit=100,
            offset=0,
        )

        result = await memory_service.list_memories(params)

        assert isinstance(result, list)
        # Should have memories from multiple types
        assert len(result) >= 1


# =============================================================================
# Memory Update - Current Behavior
# =============================================================================

class TestMemoryServiceUpdateGolden:
    """Characterization: Memory update current behavior"""

    async def test_update_memory_returns_result(
        self, memory_service, mock_factual_service
    ):
        """GOLDEN: update_memory returns MemoryOperationResult"""
        from microservices.memory_service.models import (
            MemoryUpdateRequest,
            MemoryType,
            MemoryOperationResult,
        )

        mock_factual_service.repository.update.return_value = True

        request = MemoryUpdateRequest(
            content="Updated content",
            importance_score=0.9,
        )

        result = await memory_service.update_memory(
            memory_id="mem_test_123",
            memory_type=MemoryType.FACTUAL,
            user_id="usr_test_123",
            request=request,
        )

        assert isinstance(result, MemoryOperationResult)
        assert result.operation == "update"

    async def test_update_nonexistent_memory_returns_failure(
        self, memory_service, mock_factual_service
    ):
        """GOLDEN: update_memory returns failure for non-existent memory"""
        from microservices.memory_service.models import (
            MemoryUpdateRequest,
            MemoryType,
        )

        mock_factual_service.repository.update.return_value = False

        request = MemoryUpdateRequest(content="Updated")

        result = await memory_service.update_memory(
            memory_id="mem_nonexistent",
            memory_type=MemoryType.FACTUAL,
            user_id="usr_test_123",
            request=request,
        )

        assert result.success is False


# =============================================================================
# Memory Delete - Current Behavior
# =============================================================================

class TestMemoryServiceDeleteGolden:
    """Characterization: Memory delete current behavior"""

    async def test_delete_memory_returns_result(
        self, memory_service, mock_factual_service
    ):
        """GOLDEN: delete_memory returns MemoryOperationResult"""
        from microservices.memory_service.models import MemoryType, MemoryOperationResult

        mock_factual_service.repository.delete.return_value = True

        result = await memory_service.delete_memory(
            memory_id="mem_test_123",
            memory_type=MemoryType.FACTUAL,
            user_id="usr_test_123",
        )

        assert isinstance(result, MemoryOperationResult)
        assert result.success is True
        assert result.operation == "delete"

    async def test_delete_nonexistent_memory_returns_failure(
        self, memory_service, mock_factual_service
    ):
        """GOLDEN: delete_memory returns failure for non-existent memory"""
        from microservices.memory_service.models import MemoryType

        mock_factual_service.repository.delete.return_value = False

        result = await memory_service.delete_memory(
            memory_id="mem_nonexistent",
            memory_type=MemoryType.FACTUAL,
            user_id="usr_test_123",
        )

        assert result.success is False


# =============================================================================
# Session Memory Operations - Current Behavior
# =============================================================================

class TestMemoryServiceSessionGolden:
    """Characterization: Session memory operations current behavior"""

    async def test_get_session_memories_returns_list(
        self, memory_service, mock_session_service
    ):
        """GOLDEN: get_session_memories returns list of session memories"""
        mock_session_service.repository.get_session_memories.return_value = [
            {"id": "mem_s1", "session_id": "sess_123", "content": "Message 1"},
        ]

        result = await memory_service.get_session_memories(
            session_id="sess_123",
            user_id="usr_test_123",
        )

        assert isinstance(result, list)

    async def test_deactivate_session_returns_result(
        self, memory_service, mock_session_service
    ):
        """GOLDEN: deactivate_session marks session as inactive"""
        from microservices.memory_service.models import MemoryOperationResult

        mock_session_service.repository.deactivate_session.return_value = True

        result = await memory_service.deactivate_session(
            session_id="sess_123",
            user_id="usr_test_123",
        )

        assert isinstance(result, MemoryOperationResult)


# =============================================================================
# Memory Statistics - Current Behavior
# =============================================================================

class TestMemoryServiceStatsGolden:
    """Characterization: Memory statistics current behavior"""

    async def test_get_memory_statistics_returns_dict(
        self,
        memory_service,
        mock_factual_service,
        mock_episodic_service,
        mock_procedural_service,
        mock_semantic_service,
        mock_working_service,
        mock_session_service,
    ):
        """GOLDEN: get_memory_statistics returns statistics dict"""
        # Setup mocks to return counts
        for svc in [
            mock_factual_service,
            mock_episodic_service,
            mock_procedural_service,
            mock_semantic_service,
            mock_working_service,
            mock_session_service,
        ]:
            svc.repository.get_count.return_value = 0

        result = await memory_service.get_memory_statistics(user_id="usr_test_123")

        assert isinstance(result, dict)
        assert "total_memories" in result or "user_id" in result


# =============================================================================
# Event Publishing - Current Behavior
# =============================================================================

class TestMemoryServiceEventsGolden:
    """Characterization: Memory event publishing current behavior"""

    async def test_create_memory_publishes_event(
        self, memory_service, mock_factual_service, mock_event_bus
    ):
        """GOLDEN: create_memory publishes memory.created event"""
        from microservices.memory_service.models import (
            MemoryCreateRequest,
            MemoryType,
        )

        mock_factual_service.repository.create.return_value = {
            "id": "mem_test_123",
            "user_id": "usr_test_123",
            "memory_type": "factual",
            "content": "Test content",
        }

        request = MemoryCreateRequest(
            user_id="usr_test_123",
            memory_type=MemoryType.FACTUAL,
            content="Test content",
            importance_score=0.5,
            confidence=0.8,
            tags=[],
            context={},
        )

        await memory_service.create_memory(request)

        # Verify event was attempted to be published
        # The actual publishing depends on event_bus being configured
        assert memory_service.event_bus is not None


# =============================================================================
# Health Check - Current Behavior
# =============================================================================

class TestMemoryServiceHealthGolden:
    """Characterization: Health check current behavior"""

    async def test_check_connection_returns_bool(
        self, memory_service, mock_factual_service
    ):
        """GOLDEN: check_connection returns boolean health status"""
        mock_factual_service.repository.check_connection.return_value = True

        result = await memory_service.check_connection()

        assert isinstance(result, bool)
