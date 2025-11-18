"""
Memory Service Event Publishing Tests

Tests that Memory Service correctly publishes events for all memory operations
"""
import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.memory_service.memory_service import MemoryService
from microservices.memory_service.models import (
    MemoryType, MemoryCreateRequest, MemoryUpdateRequest,
    MemoryOperationResult
)


class MockEventBus:
    """Mock event bus for testing"""

    def __init__(self):
        self.published_events = []

    async def publish_event(self, event: Event):
        """Mock publish event"""
        self.published_events.append(event)

    def get_events_by_type(self, event_type: str):
        """Get events by type"""
        return [e for e in self.published_events if e.type == event_type]

    def clear(self):
        """Clear published events"""
        self.published_events = []


class MockMemoryRepository:
    """Mock memory repository for testing"""

    def __init__(self):
        self.memories = {}

    async def create(self, memory_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create memory"""
        memory_id = memory_data["id"]
        self.memories[memory_id] = {
            **memory_data,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        return self.memories[memory_id]

    async def update(self, memory_id: str, updates: Dict[str, Any], user_id: str) -> bool:
        """Update memory"""
        if memory_id in self.memories and self.memories[memory_id]["user_id"] == user_id:
            self.memories[memory_id].update(updates)
            self.memories[memory_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            return True
        return False

    async def delete(self, memory_id: str, user_id: str) -> bool:
        """Delete memory"""
        if memory_id in self.memories and self.memories[memory_id]["user_id"] == user_id:
            del self.memories[memory_id]
            return True
        return False


class MockFactualService:
    """Mock factual memory service"""

    async def store_factual_memory(self, user_id: str, dialog_content: str, importance_score: float) -> MemoryOperationResult:
        return MemoryOperationResult(
            success=True,
            operation="store_factual",
            message="Factual memories stored",
            count=2
        )


class MockEpisodicService:
    """Mock episodic memory service"""

    async def store_episodic_memory(self, user_id: str, dialog_content: str, importance_score: float) -> MemoryOperationResult:
        return MemoryOperationResult(
            success=True,
            operation="store_episodic",
            message="Episodic memories stored",
            count=3
        )


class MockProceduralService:
    """Mock procedural memory service"""

    async def store_procedural_memory(self, user_id: str, dialog_content: str, importance_score: float) -> MemoryOperationResult:
        return MemoryOperationResult(
            success=True,
            operation="store_procedural",
            message="Procedural memories stored",
            count=1
        )


class MockSemanticService:
    """Mock semantic memory service"""

    async def store_semantic_memory(self, user_id: str, dialog_content: str, importance_score: float) -> MemoryOperationResult:
        return MemoryOperationResult(
            success=True,
            operation="store_semantic",
            message="Semantic memories stored",
            count=2
        )


class MockSessionService:
    """Mock session memory service"""

    def __init__(self):
        self.repository = MockSessionRepository()


class MockSessionRepository:
    """Mock session repository"""

    async def deactivate_session(self, user_id: str, session_id: str) -> bool:
        return True


async def test_memory_created_event():
    """Test that memory.created event is published"""
    print("\n📝 Testing memory.created event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockMemoryRepository()

    service = MemoryService(event_bus=mock_event_bus)
    service.factual_service.repository = mock_repository

    # Create memory request
    request = MemoryCreateRequest(
        user_id="user123",
        memory_type=MemoryType.FACTUAL,
        content="User likes Python programming",
        importance_score=0.8,
        confidence=0.9,
        tags=["programming", "preferences"],
        context={"subject": "programming"}
    )

    result = await service.create_memory(request)

    # Check memory was created
    assert result.success is True, "Memory should be created successfully"
    assert result.memory_id is not None, "Memory ID should be returned"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.MEMORY_CREATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.MEMORY_SERVICE.value, "Event source should be memory_service"
    assert event.data["memory_id"] == result.memory_id, "Event should contain memory_id"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["memory_type"] == MemoryType.FACTUAL.value, "Event should contain memory_type"
    assert event.data["importance_score"] == 0.8, "Event should contain importance_score"

    print("✅ TEST PASSED: memory.created event published correctly")
    return True


async def test_memory_updated_event():
    """Test that memory.updated event is published"""
    print("\n📝 Testing memory.updated event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockMemoryRepository()

    service = MemoryService(event_bus=mock_event_bus)
    service.factual_service.repository = mock_repository

    # Create a memory first
    memory_data = {
        "id": "mem_123",
        "user_id": "user123",
        "memory_type": "factual",
        "content": "Original content",
        "importance_score": 0.5
    }
    await mock_repository.create(memory_data)
    mock_event_bus.clear()

    # Update memory
    update_request = MemoryUpdateRequest(
        content="Updated content",
        importance_score=0.9
    )

    result = await service.update_memory(
        memory_id="mem_123",
        memory_type=MemoryType.FACTUAL,
        request=update_request,
        user_id="user123"
    )

    # Check memory was updated
    assert result.success is True, "Memory should be updated successfully"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.MEMORY_UPDATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.MEMORY_SERVICE.value, "Event source should be memory_service"
    assert event.data["memory_id"] == "mem_123", "Event should contain memory_id"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert "content" in event.data["updated_fields"], "Event should show content was updated"
    assert "importance_score" in event.data["updated_fields"], "Event should show importance_score was updated"

    print("✅ TEST PASSED: memory.updated event published correctly")
    return True


async def test_memory_deleted_event():
    """Test that memory.deleted event is published"""
    print("\n📝 Testing memory.deleted event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockMemoryRepository()

    service = MemoryService(event_bus=mock_event_bus)
    service.factual_service.repository = mock_repository

    # Create a memory first
    memory_data = {
        "id": "mem_456",
        "user_id": "user123",
        "memory_type": "factual",
        "content": "Memory to delete"
    }
    await mock_repository.create(memory_data)
    mock_event_bus.clear()

    # Delete memory
    result = await service.delete_memory(
        memory_id="mem_456",
        memory_type=MemoryType.FACTUAL,
        user_id="user123"
    )

    # Check memory was deleted
    assert result.success is True, "Memory should be deleted successfully"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.MEMORY_DELETED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.MEMORY_SERVICE.value, "Event source should be memory_service"
    assert event.data["memory_id"] == "mem_456", "Event should contain memory_id"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["memory_type"] == MemoryType.FACTUAL.value, "Event should contain memory_type"

    print("✅ TEST PASSED: memory.deleted event published correctly")
    return True


async def test_factual_memory_stored_event():
    """Test that memory.factual.stored event is published"""
    print("\n📝 Testing memory.factual.stored event...")

    mock_event_bus = MockEventBus()
    service = MemoryService(event_bus=mock_event_bus)
    service.factual_service = MockFactualService()

    result = await service.store_factual_memory(
        user_id="user123",
        dialog_content="I love Python programming and machine learning",
        importance_score=0.7
    )

    # Check operation succeeded
    assert result.success is True, "Factual memory storage should succeed"
    assert result.count == 2, "Should extract 2 factual memories"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.FACTUAL_MEMORY_STORED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.MEMORY_SERVICE.value, "Event source should be memory_service"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["count"] == 2, "Event should contain count"
    assert event.data["importance_score"] == 0.7, "Event should contain importance_score"

    print("✅ TEST PASSED: memory.factual.stored event published correctly")
    return True


async def test_episodic_memory_stored_event():
    """Test that memory.episodic.stored event is published"""
    print("\n📝 Testing memory.episodic.stored event...")

    mock_event_bus = MockEventBus()
    service = MemoryService(event_bus=mock_event_bus)
    service.episodic_service = MockEpisodicService()

    result = await service.store_episodic_memory(
        user_id="user123",
        dialog_content="We discussed the new project yesterday at the coffee shop",
        importance_score=0.6
    )

    # Check operation succeeded
    assert result.success is True, "Episodic memory storage should succeed"
    assert result.count == 3, "Should extract 3 episodic memories"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.EPISODIC_MEMORY_STORED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.MEMORY_SERVICE.value, "Event source should be memory_service"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["count"] == 3, "Event should contain count"

    print("✅ TEST PASSED: memory.episodic.stored event published correctly")
    return True


async def test_procedural_memory_stored_event():
    """Test that memory.procedural.stored event is published"""
    print("\n📝 Testing memory.procedural.stored event...")

    mock_event_bus = MockEventBus()
    service = MemoryService(event_bus=mock_event_bus)
    service.procedural_service = MockProceduralService()

    result = await service.store_procedural_memory(
        user_id="user123",
        dialog_content="To deploy the app, run docker-compose up -d",
        importance_score=0.8
    )

    # Check operation succeeded
    assert result.success is True, "Procedural memory storage should succeed"
    assert result.count == 1, "Should extract 1 procedural memory"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.PROCEDURAL_MEMORY_STORED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.MEMORY_SERVICE.value, "Event source should be memory_service"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["count"] == 1, "Event should contain count"

    print("✅ TEST PASSED: memory.procedural.stored event published correctly")
    return True


async def test_semantic_memory_stored_event():
    """Test that memory.semantic.stored event is published"""
    print("\n📝 Testing memory.semantic.stored event...")

    mock_event_bus = MockEventBus()
    service = MemoryService(event_bus=mock_event_bus)
    service.semantic_service = MockSemanticService()

    result = await service.store_semantic_memory(
        user_id="user123",
        dialog_content="Machine learning is a subset of artificial intelligence",
        importance_score=0.7
    )

    # Check operation succeeded
    assert result.success is True, "Semantic memory storage should succeed"
    assert result.count == 2, "Should extract 2 semantic memories"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.SEMANTIC_MEMORY_STORED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.MEMORY_SERVICE.value, "Event source should be memory_service"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["count"] == 2, "Event should contain count"

    print("✅ TEST PASSED: memory.semantic.stored event published correctly")
    return True


async def test_session_memory_deactivated_event():
    """Test that memory.session.deactivated event is published"""
    print("\n📝 Testing memory.session.deactivated event...")

    mock_event_bus = MockEventBus()
    service = MemoryService(event_bus=mock_event_bus)
    service.session_service = MockSessionService()

    result = await service.deactivate_session(
        user_id="user123",
        session_id="session_789"
    )

    # Check operation succeeded
    assert result.success is True, "Session deactivation should succeed"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.SESSION_MEMORY_DEACTIVATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.MEMORY_SERVICE.value, "Event source should be memory_service"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["session_id"] == "session_789", "Event should contain session_id"

    print("✅ TEST PASSED: memory.session.deactivated event published correctly")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("MEMORY SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)

    tests = [
        ("Memory Created Event", test_memory_created_event),
        ("Memory Updated Event", test_memory_updated_event),
        ("Memory Deleted Event", test_memory_deleted_event),
        ("Factual Memory Stored Event", test_factual_memory_stored_event),
        ("Episodic Memory Stored Event", test_episodic_memory_stored_event),
        ("Procedural Memory Stored Event", test_procedural_memory_stored_event),
        ("Semantic Memory Stored Event", test_semantic_memory_stored_event),
        ("Session Memory Deactivated Event", test_session_memory_deactivated_event),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} total")
    print("="*80)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
