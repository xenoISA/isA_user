"""
Task Service Event Subscription Tests

Tests that Task Service correctly handles incoming events:
- user.deleted: Cancel all user's tasks
"""
import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import List

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.task_service.events.handlers import TaskEventHandler
from microservices.task_service.models import TaskResponse, TaskStatus, TaskType, TaskPriority


class MockTaskRepository:
    """Mock task repository for testing event handlers"""

    def __init__(self):
        self.tasks = {}
        self.task_counter = 1

    def add_task(self, user_id: str, name: str, status: TaskStatus = TaskStatus.PENDING) -> str:
        """Helper to add a task for testing"""
        task_id = f"task_{self.task_counter}"
        self.task_counter += 1

        task = TaskResponse(
            id=self.task_counter,
            task_id=task_id,
            user_id=user_id,
            name=name,
            description=None,
            task_type=TaskType.CUSTOM,
            status=status,
            priority=TaskPriority.MEDIUM,
            config={},
            schedule=None,
            credits_per_run=0.0,
            tags=[],
            metadata={},
            next_run_time=None,
            last_run_time=None,
            last_success_time=None,
            last_error=None,
            last_result=None,
            run_count=0,
            success_count=0,
            failure_count=0,
            total_credits_consumed=0.0,
            due_date=None,
            reminder_time=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deleted_at=None
        )
        self.tasks[task_id] = task
        return task_id

    async def cancel_user_tasks(self, user_id: str) -> int:
        """Cancel all pending/scheduled tasks for a user"""
        count = 0
        for task in self.tasks.values():
            if task.user_id == user_id and task.status in [TaskStatus.PENDING, TaskStatus.SCHEDULED]:
                task.status = TaskStatus.CANCELLED
                task.updated_at = datetime.now(timezone.utc)
                count += 1
        return count

    def get_tasks_by_user(self, user_id: str) -> List[TaskResponse]:
        """Get all tasks for a user"""
        return [task for task in self.tasks.values() if task.user_id == user_id]

    def get_cancelled_count(self, user_id: str) -> int:
        """Get count of cancelled tasks for a user"""
        return len([
            task for task in self.tasks.values()
            if task.user_id == user_id and task.status == TaskStatus.CANCELLED
        ])


async def test_handle_user_deleted():
    """Test handling user.deleted event cancels all user's tasks"""
    print("\n📝 Testing user.deleted event handler...")

    mock_repository = MockTaskRepository()
    event_handler = TaskEventHandler(mock_repository)

    # Create some tasks for the user
    mock_repository.add_task("user123", "Task 1", TaskStatus.PENDING)
    mock_repository.add_task("user123", "Task 2", TaskStatus.SCHEDULED)
    mock_repository.add_task("user123", "Task 3", TaskStatus.RUNNING)  # Should not be cancelled
    mock_repository.add_task("user456", "Other Task", TaskStatus.PENDING)  # Different user

    # Create user.deleted event
    event_data = {
        "user_id": "user123",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle the event
    result = await event_handler.handle_user_deleted(event_data)

    # Verify success
    assert result is True, "Handler should return True on success"

    # Check that only pending/scheduled tasks were cancelled
    cancelled_count = mock_repository.get_cancelled_count("user123")
    assert cancelled_count == 2, f"Should cancel 2 tasks, cancelled {cancelled_count}"

    # Verify running task was not cancelled
    user_tasks = mock_repository.get_tasks_by_user("user123")
    running_tasks = [t for t in user_tasks if t.status == TaskStatus.RUNNING]
    assert len(running_tasks) == 1, "Running task should not be cancelled"

    # Verify other user's tasks were not affected
    other_user_tasks = mock_repository.get_tasks_by_user("user456")
    assert len(other_user_tasks) == 1, "Other user should still have 1 task"
    assert other_user_tasks[0].status == TaskStatus.PENDING, "Other user's task should still be pending"

    print("✅ TEST PASSED: user.deleted event handled correctly")
    return True


async def test_handle_user_deleted_no_tasks():
    """Test handling user.deleted event when user has no tasks"""
    print("\n📝 Testing user.deleted with no tasks...")

    mock_repository = MockTaskRepository()
    event_handler = TaskEventHandler(mock_repository)

    event_data = {
        "user_id": "user_with_no_tasks",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle the event
    result = await event_handler.handle_user_deleted(event_data)

    # Should succeed even with no tasks
    assert result is True, "Handler should return True even with no tasks"
    assert mock_repository.get_cancelled_count("user_with_no_tasks") == 0, "No tasks should be cancelled"

    print("✅ TEST PASSED: user.deleted with no tasks handled correctly")
    return True


async def test_handle_user_deleted_missing_user_id():
    """Test handling user.deleted event with missing user_id"""
    print("\n📝 Testing user.deleted with missing user_id...")

    mock_repository = MockTaskRepository()
    event_handler = TaskEventHandler(mock_repository)

    event_data = {
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle the event
    result = await event_handler.handle_user_deleted(event_data)

    # Should return False for invalid data
    assert result is False, "Handler should return False for missing user_id"

    print("✅ TEST PASSED: user.deleted with missing user_id handled correctly")
    return True


async def test_handle_event_routing():
    """Test that handle_event correctly routes to user.deleted handler"""
    print("\n📝 Testing event routing...")

    mock_repository = MockTaskRepository()
    event_handler = TaskEventHandler(mock_repository)

    # Create a task
    mock_repository.add_task("user123", "Test Task", TaskStatus.PENDING)

    # Create event
    event = Event(
        event_type=EventType.USER_DELETED,
        source=ServiceSource.AUTH_SERVICE,
        data={
            "user_id": "user123",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Handle the event
    result = await event_handler.handle_event(event)

    # Verify it was routed correctly
    assert result is True, "Event should be routed and handled successfully"
    assert mock_repository.get_cancelled_count("user123") == 1, "Task should be cancelled"

    print("✅ TEST PASSED: event routing works correctly")
    return True


async def test_handle_unknown_event():
    """Test handling unknown event type"""
    print("\n📝 Testing unknown event handling...")

    mock_repository = MockTaskRepository()
    event_handler = TaskEventHandler(mock_repository)

    # Create a mock event object with unknown type
    class MockEvent:
        def __init__(self):
            self.type = "unknown.event"
            self.source = ServiceSource.AUTH_SERVICE.value
            self.data = {}

    event = MockEvent()

    # Handle the event
    result = await event_handler.handle_event(event)

    # Should return False for unknown event
    assert result is False, "Handler should return False for unknown event type"

    print("✅ TEST PASSED: unknown event handled correctly")
    return True


async def test_get_subscriptions():
    """Test that handler returns correct subscription list"""
    print("\n📝 Testing subscription list...")

    mock_repository = MockTaskRepository()
    event_handler = TaskEventHandler(mock_repository)

    subscriptions = event_handler.get_subscriptions()

    # Should subscribe to user.deleted
    assert EventType.USER_DELETED.value in subscriptions, "Should subscribe to user.deleted"
    assert len(subscriptions) == 1, f"Should have 1 subscription, got {len(subscriptions)}"

    print("✅ TEST PASSED: subscription list is correct")
    return True


async def test_handle_user_deleted_multiple_users():
    """Test handling user.deleted for multiple users"""
    print("\n📝 Testing user.deleted for multiple users...")

    mock_repository = MockTaskRepository()
    event_handler = TaskEventHandler(mock_repository)

    # Create tasks for multiple users
    mock_repository.add_task("user1", "User1 Task 1", TaskStatus.PENDING)
    mock_repository.add_task("user1", "User1 Task 2", TaskStatus.PENDING)
    mock_repository.add_task("user2", "User2 Task 1", TaskStatus.PENDING)
    mock_repository.add_task("user3", "User3 Task 1", TaskStatus.PENDING)

    # Delete user1
    event_data = {
        "user_id": "user1",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    result = await event_handler.handle_user_deleted(event_data)
    assert result is True, "Should handle user1 deletion"
    assert mock_repository.get_cancelled_count("user1") == 2, "Should cancel 2 tasks for user1"

    # Verify other users' tasks are not affected
    assert mock_repository.get_cancelled_count("user2") == 0, "User2 tasks should not be cancelled"
    assert mock_repository.get_cancelled_count("user3") == 0, "User3 tasks should not be cancelled"

    # Delete user2
    event_data = {
        "user_id": "user2",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    result = await event_handler.handle_user_deleted(event_data)
    assert result is True, "Should handle user2 deletion"
    assert mock_repository.get_cancelled_count("user2") == 1, "Should cancel 1 task for user2"

    # Verify user3's tasks are still not affected
    assert mock_repository.get_cancelled_count("user3") == 0, "User3 tasks should still not be cancelled"

    print("✅ TEST PASSED: multiple user deletions handled correctly")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("TASK SERVICE EVENT SUBSCRIPTION TEST SUITE")
    print("="*80)

    tests = [
        ("User Deleted Event Handler", test_handle_user_deleted),
        ("User Deleted With No Tasks", test_handle_user_deleted_no_tasks),
        ("User Deleted Missing User ID", test_handle_user_deleted_missing_user_id),
        ("Event Routing", test_handle_event_routing),
        ("Unknown Event Handling", test_handle_unknown_event),
        ("Subscription List", test_get_subscriptions),
        ("Multiple User Deletions", test_handle_user_deleted_multiple_users),
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
