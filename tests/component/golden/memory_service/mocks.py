"""
Memory Service - Mock Dependencies (Golden)

Mock implementations for component golden testing.
These mocks simulate external dependencies (repositories, event bus)
without requiring real infrastructure.

Usage:
    from tests.component.golden.memory_service.mocks import (
        MockMemoryRepository,
        MockEventBus,
        MockFactualService,
        MockEpisodicService,
    )
"""

from unittest.mock import AsyncMock, MagicMock
from typing import Optional, Dict, Any, List


class MockMemoryRepository:
    """
    Mock memory repository for golden component testing.

    Simple mock that allows tests to override return_value for each method.
    Create methods return the input data by default.
    """

    def __init__(self):
        # Standard CRUD methods
        self.create = AsyncMock(side_effect=lambda x: x)
        self.get_by_id = AsyncMock(return_value=None)
        self.update = AsyncMock(return_value=True)
        self.delete = AsyncMock(return_value=True)
        self.list_by_user = AsyncMock(return_value=[])
        self.increment_access_count = AsyncMock(return_value=True)
        self.get_count = AsyncMock(return_value=0)
        self.check_connection = AsyncMock(return_value=True)

        # Memory-specific search methods
        self.search_by_subject = AsyncMock(return_value=[])
        self.search_by_fact_type = AsyncMock(return_value=[])
        self.search_by_domain = AsyncMock(return_value=[])
        self.search_by_skill_type = AsyncMock(return_value=[])
        self.search_by_category = AsyncMock(return_value=[])
        self.search_by_concept_type = AsyncMock(return_value=[])
        self.search_by_timeframe = AsyncMock(return_value=[])
        self.search_by_event_type = AsyncMock(return_value=[])
        self.get_active_memories = AsyncMock(return_value=[])
        self.cleanup_expired_memories = AsyncMock(return_value=0)
        self.get_session_memories = AsyncMock(return_value=[])
        self.get_session_summary = AsyncMock(return_value=None)
        self.deactivate_session = AsyncMock(return_value=True)


class MockFactualService:
    """Mock Factual Memory Service"""

    def __init__(self):
        self.repository = MockMemoryRepository()
        self.store_factual_memory = AsyncMock()


class MockEpisodicService:
    """Mock Episodic Memory Service"""

    def __init__(self):
        self.repository = MockMemoryRepository()
        self.store_episodic_memory = AsyncMock()


class MockProceduralService:
    """Mock Procedural Memory Service"""

    def __init__(self):
        self.repository = MockMemoryRepository()
        self.store_procedural_memory = AsyncMock()


class MockSemanticService:
    """Mock Semantic Memory Service"""

    def __init__(self):
        self.repository = MockMemoryRepository()
        self.store_semantic_memory = AsyncMock()


class MockWorkingService:
    """Mock Working Memory Service"""

    def __init__(self):
        self.repository = MockMemoryRepository()


class MockSessionService:
    """Mock Session Memory Service"""

    def __init__(self):
        self.repository = MockMemoryRepository()


class MockEventBus:
    """Mock NATS event bus for golden component testing."""

    def __init__(self):
        self.published_events: List[Any] = []
        self.publish = AsyncMock(side_effect=self._publish)
        self.publish_event = AsyncMock(side_effect=self._publish)

    async def _publish(self, event: Any) -> None:
        """Track published event"""
        self.published_events.append(event)

    def get_published_events(self, event_type: Optional[str] = None) -> List[Any]:
        """Get published events, optionally filtered by type"""
        if event_type is None:
            return self.published_events
        return [
            e for e in self.published_events
            if hasattr(e, 'type') and e.type == event_type
            or isinstance(e, dict) and e.get('type') == event_type
        ]

    def assert_event_published(self, event_type: str) -> None:
        """Assert that an event of given type was published"""
        events = self.get_published_events(event_type)
        assert len(events) > 0, f"Expected event '{event_type}' to be published"

    def clear(self):
        """Clear all published events"""
        self.published_events.clear()
