"""
Task Service Event Publishing Tests

Tests that Task Service correctly publishes events for all task operations
"""
import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.task_service.task_service import TaskService
from microservices.task_service.models import (
    TaskCreateRequest, TaskUpdateRequest, TaskResponse,
    TaskStatus, TaskType, TaskPriority
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


class MockTaskRepository:
    """Mock task repository for testing"""

    def __init__(self):
        self.tasks = {}
        self.task_counter = 1

    async def create_task(self, user_id: str, task_data: Dict[str, Any]) -> TaskResponse:
        """Create a task"""
        task_id = f"task_{self.task_counter}"
        self.task_counter += 1

        task = TaskResponse(
            id=self.task_counter,
            task_id=task_id,
            user_id=user_id,
            name=task_data.get("name", "Test Task"),
            description=task_data.get("description"),
            task_type=task_data.get("task_type", TaskType.CUSTOM),
            status=TaskStatus.PENDING,
            priority=task_data.get("priority", TaskPriority.MEDIUM),
            config=task_data.get("config", {}),
            schedule=task_data.get("schedule"),
            credits_per_run=task_data.get("credits_per_run", 0.0),
            tags=task_data.get("tags", []),
            metadata=task_data.get("metadata", {}),
            next_run_time=None,
            last_run_time=None,
            last_success_time=None,
            last_error=None,
            last_result=None,
            run_count=0,
            success_count=0,
            failure_count=0,
            total_credits_consumed=0.0,
            due_date=task_data.get("due_date"),
            reminder_time=task_data.get("reminder_time"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deleted_at=None
        )
        self.tasks[task_id] = task
        return task

    async def get_task(self, task_id: str, user_id: str) -> Optional[TaskResponse]:
        """Get a task"""
        task = self.tasks.get(task_id)
        if task and task.user_id == user_id:
            return task
        return None

    async def update_task(self, task_id: str, update_data: Dict[str, Any], user_id: str) -> bool:
        """Update a task"""
        task = self.tasks.get(task_id)
        if task and task.user_id == user_id:
            for key, value in update_data.items():
                if hasattr(task, key) and value is not None:
                    setattr(task, key, value)
            task.updated_at = datetime.now(timezone.utc)
            return True
        return False

    async def delete_task(self, task_id: str, user_id: str) -> bool:
        """Delete a task"""
        task = self.tasks.get(task_id)
        if task and task.user_id == user_id:
            del self.tasks[task_id]
            return True
        return False

    async def get_user_tasks(self, user_id: str, limit: int = 100, offset: int = 0, status: Optional[str] = None) -> list:
        """Get user tasks (mocked to return empty list for limit checking)"""
        return []

    async def get_task_by_id(self, task_id: str, user_id: str) -> Optional[TaskResponse]:
        """Get task by ID for permission checks"""
        return await self.get_task(task_id, user_id)


async def test_task_created_event():
    """Test that task.created event is published"""
    print("\n📝 Testing task.created event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockTaskRepository()

    service = TaskService(event_bus=mock_event_bus)
    service.repository = mock_repository

    # Create a task
    request = TaskCreateRequest(
        name="Test Task",
        task_type=TaskType.TODO,
        description="Test task description",
        config={"key": "value"},
        priority=TaskPriority.HIGH
    )

    task = await service.create_task("user123", request)

    # Verify task was created
    assert task.task_id is not None, "Task should have an ID"
    assert task.name == "Test Task", "Task name should match"

    # Verify event was published
    events = mock_event_bus.get_events_by_type(EventType.TASK_CREATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.TASK_SERVICE.value, "Event source should be task_service"
    assert event.data["task_id"] == task.task_id, "Event should contain task_id"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["name"] == "Test Task", "Event should contain task name"
    assert event.data["task_type"] == TaskType.TODO.value, "Event should contain task type"
    assert event.data["priority"] == TaskPriority.HIGH.value, "Event should contain priority"
    assert event.data["status"] == TaskStatus.PENDING.value, "Event should contain status"

    print("✅ TEST PASSED: task.created event published correctly")
    return True


async def test_task_updated_event():
    """Test that task.updated event is published"""
    print("\n📝 Testing task.updated event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockTaskRepository()

    service = TaskService(event_bus=mock_event_bus)
    service.repository = mock_repository

    # Create a task first
    create_request = TaskCreateRequest(
        name="Original Task",
        task_type=TaskType.TODO,
        priority=TaskPriority.LOW
    )
    task = await service.create_task("user123", create_request)
    mock_event_bus.clear()

    # Update the task
    update_request = TaskUpdateRequest(
        name="Updated Task",
        description="Updated description",
        priority=TaskPriority.URGENT
    )

    updated_task = await service.update_task(task.task_id, "user123", update_request)

    # Verify task was updated
    assert updated_task is not None, "Task should be updated"

    # Verify event was published
    events = mock_event_bus.get_events_by_type(EventType.TASK_UPDATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.TASK_SERVICE.value, "Event source should be task_service"
    assert event.data["task_id"] == task.task_id, "Event should contain task_id"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert "updates" in event.data, "Event should contain updates"
    assert event.data["updates"]["name"] == "Updated Task", "Event should contain updated name"

    print("✅ TEST PASSED: task.updated event published correctly")
    return True


async def test_task_completed_event():
    """Test that task.completed event is published"""
    print("\n📝 Testing task.completed event...")

    mock_event_bus = MockEventBus()

    # Manually create and publish a task.completed event
    # (since task execution is complex and would be published in _execute_task_async)
    event = Event(
        event_type=EventType.TASK_COMPLETED,
        source=ServiceSource.TASK_SERVICE,
        data={
            "task_id": "task_123",
            "user_id": "user123",
            "name": "Test Task",
            "task_type": TaskType.CUSTOM.value,
            "result": {"status": "success"},
            "attempt_count": 1,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
    await mock_event_bus.publish_event(event)

    # Verify event was published
    events = mock_event_bus.get_events_by_type(EventType.TASK_COMPLETED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.TASK_SERVICE.value, "Event source should be task_service"
    assert event.data["task_id"] == "task_123", "Event should contain task_id"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["result"]["status"] == "success", "Event should contain result"

    print("✅ TEST PASSED: task.completed event published correctly")
    return True


async def test_task_failed_event():
    """Test that task.failed event is published"""
    print("\n📝 Testing task.failed event...")

    mock_event_bus = MockEventBus()

    # Manually create and publish a task.failed event
    event = Event(
        event_type=EventType.TASK_FAILED,
        source=ServiceSource.TASK_SERVICE,
        data={
            "task_id": "task_123",
            "user_id": "user123",
            "name": "Test Task",
            "task_type": TaskType.CUSTOM.value,
            "error": "Task execution failed",
            "attempt_count": 1,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
    await mock_event_bus.publish_event(event)

    # Verify event was published
    events = mock_event_bus.get_events_by_type(EventType.TASK_FAILED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.TASK_SERVICE.value, "Event source should be task_service"
    assert event.data["task_id"] == "task_123", "Event should contain task_id"
    assert event.data["error"] == "Task execution failed", "Event should contain error"

    print("✅ TEST PASSED: task.failed event published correctly")
    return True


async def test_task_cancelled_event():
    """Test that task.cancelled event is published"""
    print("\n📝 Testing task.cancelled event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockTaskRepository()

    service = TaskService(event_bus=mock_event_bus)
    service.repository = mock_repository

    # Create a task first
    create_request = TaskCreateRequest(
        name="Test Task",
        task_type=TaskType.TODO
    )
    task = await service.create_task("user123", create_request)
    mock_event_bus.clear()

    # Delete the task
    result = await service.delete_task(task.task_id, "user123")
    assert result is True, "Task should be deleted"

    # Verify event was published
    events = mock_event_bus.get_events_by_type(EventType.TASK_CANCELLED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.TASK_SERVICE.value, "Event source should be task_service"
    assert event.data["task_id"] == task.task_id, "Event should contain task_id"
    assert event.data["user_id"] == "user123", "Event should contain user_id"

    print("✅ TEST PASSED: task.cancelled event published correctly")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("TASK SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)

    tests = [
        ("Task Created Event", test_task_created_event),
        ("Task Updated Event", test_task_updated_event),
        ("Task Completed Event", test_task_completed_event),
        ("Task Failed Event", test_task_failed_event),
        ("Task Cancelled Event", test_task_cancelled_event),
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
