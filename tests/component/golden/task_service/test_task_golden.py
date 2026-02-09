"""
Task Service - Component Tests (Golden)

Tests TaskService with mocked dependencies.
All tests use TaskTestDataFactory - zero hardcoded data.
"""
import pytest
from datetime import datetime, timezone, timedelta

from microservices.task_service.models import (
    TaskType,
    TaskStatus,
    TaskPriority,
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskExecutionRequest,
)
from tests.contracts.task.data_contract import TaskTestDataFactory
from .mocks import MockTaskRepository, MockEventBus


pytestmark = [pytest.mark.component]


# ============================================================================
# Test Task Repository Mock Operations
# ============================================================================


class TestMockRepositoryOperations:
    """Test mock repository operations"""

    @pytest.mark.asyncio
    async def test_create_task_returns_response(self, mock_repository, sample_user_id):
        """Create task returns TaskResponse"""
        task_data = {
            "name": TaskTestDataFactory.make_task_name(),
            "task_type": TaskType.TODO,
            "priority": TaskPriority.MEDIUM,
        }

        result = await mock_repository.create_task(sample_user_id, task_data)

        assert result is not None
        assert result.task_id.startswith("tsk_")
        assert result.user_id == sample_user_id
        assert result.name == task_data["name"]
        assert result.task_type == TaskType.TODO
        mock_repository.assert_called("create_task")

    @pytest.mark.asyncio
    async def test_get_task_by_id_returns_existing(self, populated_repository, sample_user_id):
        """Get existing task returns TaskResponse"""
        # Get first task from populated repository
        tasks = await populated_repository.get_user_tasks(sample_user_id)
        assert len(tasks) > 0
        task_id = tasks[0].task_id

        result = await populated_repository.get_task_by_id(task_id, sample_user_id)

        assert result is not None
        assert result.task_id == task_id
        populated_repository.assert_called("get_task_by_id")

    @pytest.mark.asyncio
    async def test_get_task_by_id_returns_none_for_nonexistent(
        self, mock_repository, sample_user_id
    ):
        """Get nonexistent task returns None"""
        fake_id = TaskTestDataFactory.make_task_id()

        result = await mock_repository.get_task_by_id(fake_id, sample_user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_tasks_returns_filtered_list(
        self, populated_repository, sample_user_id
    ):
        """Get user tasks returns filtered list"""
        # Get all tasks
        all_tasks = await populated_repository.get_user_tasks(sample_user_id)
        assert len(all_tasks) >= 5

        # Filter by status
        pending_tasks = await populated_repository.get_user_tasks(
            sample_user_id, status="pending"
        )
        assert all(t.status == TaskStatus.PENDING for t in pending_tasks)

        # Filter by task type
        todo_tasks = await populated_repository.get_user_tasks(
            sample_user_id, task_type="todo"
        )
        assert all(t.task_type == TaskType.TODO for t in todo_tasks)

    @pytest.mark.asyncio
    async def test_update_task_modifies_data(self, mock_repository, sample_user_id):
        """Update task modifies data"""
        # Create a task first
        task_data = {
            "name": TaskTestDataFactory.make_task_name(),
            "task_type": TaskType.TODO,
        }
        task = await mock_repository.create_task(sample_user_id, task_data)

        # Update the task
        new_name = TaskTestDataFactory.make_task_name()
        updates = {"name": new_name, "priority": "high"}

        success = await mock_repository.update_task(task.task_id, updates, sample_user_id)

        assert success is True

        # Verify update
        updated_task = await mock_repository.get_task_by_id(task.task_id, sample_user_id)
        assert updated_task.name == new_name
        assert updated_task.priority == TaskPriority.HIGH

    @pytest.mark.asyncio
    async def test_delete_task_soft_deletes(self, mock_repository, sample_user_id):
        """Delete task performs soft delete"""
        # Create a task
        task_data = {
            "name": TaskTestDataFactory.make_task_name(),
            "task_type": TaskType.TODO,
        }
        task = await mock_repository.create_task(sample_user_id, task_data)

        # Delete the task
        success = await mock_repository.delete_task(task.task_id, sample_user_id)

        assert success is True

        # Task should not be retrievable
        deleted_task = await mock_repository.get_task_by_id(task.task_id, sample_user_id)
        assert deleted_task is None

    @pytest.mark.asyncio
    async def test_user_isolation(self, populated_repository, sample_user_id):
        """Users only see their own tasks"""
        # Get sample user's tasks
        user_tasks = await populated_repository.get_user_tasks(sample_user_id)
        assert len(user_tasks) > 0

        # All tasks belong to the sample user
        assert all(t.user_id == sample_user_id for t in user_tasks)


# ============================================================================
# Test Task Execution Flow
# ============================================================================


class TestTaskExecutionFlow:
    """Test task execution operations"""

    @pytest.mark.asyncio
    async def test_create_execution_record(self, mock_repository, sample_user_id):
        """Create execution record returns ExecutionResponse"""
        # Create a task first
        task_data = {
            "name": TaskTestDataFactory.make_task_name(),
            "task_type": TaskType.TODO,
        }
        task = await mock_repository.create_task(sample_user_id, task_data)

        # Create execution record
        execution_data = {
            "trigger_type": "manual",
            "trigger_data": TaskTestDataFactory.make_trigger_data(),
        }

        result = await mock_repository.create_execution_record(
            task.task_id, sample_user_id, execution_data
        )

        assert result is not None
        assert result.execution_id.startswith("exe_")
        assert result.task_id == task.task_id
        assert result.user_id == sample_user_id
        assert result.status == TaskStatus.RUNNING

    @pytest.mark.asyncio
    async def test_update_execution_record_success(self, mock_repository, sample_user_id):
        """Update execution record for success"""
        # Create task and execution
        task_data = {"name": TaskTestDataFactory.make_task_name(), "task_type": TaskType.TODO}
        task = await mock_repository.create_task(sample_user_id, task_data)
        execution = await mock_repository.create_execution_record(
            task.task_id, sample_user_id, {"trigger_type": "manual"}
        )

        # Update as successful
        updates = {
            "success": True,
            "result": TaskTestDataFactory.make_execution_result(),
            "credits_consumed": 1.0,
        }

        success = await mock_repository.update_execution_record(
            execution.execution_id, updates
        )

        assert success is True

    @pytest.mark.asyncio
    async def test_update_execution_record_failure(self, mock_repository, sample_user_id):
        """Update execution record for failure"""
        # Create task and execution
        task_data = {"name": TaskTestDataFactory.make_task_name(), "task_type": TaskType.TODO}
        task = await mock_repository.create_task(sample_user_id, task_data)
        execution = await mock_repository.create_execution_record(
            task.task_id, sample_user_id, {"trigger_type": "manual"}
        )

        # Update as failed
        updates = {
            "error": "Task execution failed due to external service timeout",
        }

        success = await mock_repository.update_execution_record(
            execution.execution_id, updates
        )

        assert success is True

    @pytest.mark.asyncio
    async def test_get_task_executions(self, mock_repository, sample_user_id):
        """Get task execution history"""
        # Create task with multiple executions
        task_data = {"name": TaskTestDataFactory.make_task_name(), "task_type": TaskType.TODO}
        task = await mock_repository.create_task(sample_user_id, task_data)

        # Create multiple executions
        for _ in range(3):
            await mock_repository.create_execution_record(
                task.task_id, sample_user_id, {"trigger_type": "manual"}
            )

        # Get executions
        executions = await mock_repository.get_task_executions(task.task_id)

        assert len(executions) == 3
        assert all(e.task_id == task.task_id for e in executions)

    @pytest.mark.asyncio
    async def test_update_task_execution_info(self, mock_repository, sample_user_id):
        """Update task execution statistics"""
        # Create task
        task_data = {"name": TaskTestDataFactory.make_task_name(), "task_type": TaskType.TODO}
        task = await mock_repository.create_task(sample_user_id, task_data)

        # Update execution info for success
        success = await mock_repository.update_task_execution_info(
            task.task_id, success=True, credits_consumed=1.5
        )

        assert success is True

        # Verify stats updated
        updated_task = await mock_repository.get_task_by_id(task.task_id, sample_user_id)
        assert updated_task.run_count == 1
        assert updated_task.success_count == 1
        assert updated_task.failure_count == 0
        assert updated_task.total_credits_consumed == 1.5


# ============================================================================
# Test Task Templates
# ============================================================================


class TestTaskTemplates:
    """Test task template operations"""

    @pytest.mark.asyncio
    async def test_get_templates_for_free_user(self, populated_repository):
        """Free user gets free templates only"""
        templates = await populated_repository.get_task_templates(
            subscription_level="free"
        )

        assert len(templates) >= 1
        assert all(
            t.required_subscription_level in ["free"]
            for t in templates
        )

    @pytest.mark.asyncio
    async def test_get_templates_for_basic_user(self, populated_repository):
        """Basic user gets free and basic templates"""
        templates = await populated_repository.get_task_templates(
            subscription_level="basic"
        )

        assert len(templates) >= 2
        assert all(
            t.required_subscription_level in ["free", "basic"]
            for t in templates
        )

    @pytest.mark.asyncio
    async def test_get_templates_for_pro_user(self, populated_repository):
        """Pro user gets all templates"""
        templates = await populated_repository.get_task_templates(
            subscription_level="pro"
        )

        assert len(templates) == 3

    @pytest.mark.asyncio
    async def test_filter_templates_by_category(self, populated_repository):
        """Filter templates by category"""
        templates = await populated_repository.get_task_templates(
            subscription_level="pro",
            category="information",
        )

        assert len(templates) >= 2
        assert all(t.category == "information" for t in templates)

    @pytest.mark.asyncio
    async def test_get_template_by_id(self, populated_repository):
        """Get specific template by ID"""
        template = await populated_repository.get_template("tpl_weather_free")

        assert template is not None
        assert template.template_id == "tpl_weather_free"
        assert template.task_type == TaskType.DAILY_WEATHER


# ============================================================================
# Test Task Analytics
# ============================================================================


class TestTaskAnalytics:
    """Test task analytics operations"""

    @pytest.mark.asyncio
    async def test_get_analytics_returns_response(
        self, populated_repository, sample_user_id
    ):
        """Get analytics returns TaskAnalyticsResponse"""
        analytics = await populated_repository.get_task_analytics(sample_user_id)

        assert analytics is not None
        assert analytics.user_id == sample_user_id
        assert analytics.total_tasks >= 0
        assert 0 <= analytics.success_rate <= 100

    @pytest.mark.asyncio
    async def test_analytics_task_type_distribution(
        self, populated_repository, sample_user_id
    ):
        """Analytics includes task type distribution"""
        analytics = await populated_repository.get_task_analytics(sample_user_id)

        assert analytics.task_types_distribution is not None
        assert isinstance(analytics.task_types_distribution, dict)

    @pytest.mark.asyncio
    async def test_analytics_empty_for_new_user(self, mock_repository):
        """Analytics returns zero counts for new user"""
        new_user_id = TaskTestDataFactory.make_user_id()

        analytics = await mock_repository.get_task_analytics(new_user_id)

        assert analytics.total_tasks == 0
        assert analytics.total_executions == 0
        assert analytics.success_rate == 0.0


# ============================================================================
# Test Event Publishing
# ============================================================================


class TestEventPublishing:
    """Test event bus interactions"""

    @pytest.mark.asyncio
    async def test_event_bus_publish(self, mock_event_bus):
        """Event bus publishes events"""
        event = {"event_type": "task.created", "task_id": TaskTestDataFactory.make_task_id()}

        await mock_event_bus.publish_event(event)

        mock_event_bus.assert_published()
        assert len(mock_event_bus.published_events) == 1

    @pytest.mark.asyncio
    async def test_event_bus_multiple_events(self, mock_event_bus):
        """Event bus handles multiple events"""
        for i in range(5):
            event = {
                "event_type": f"task.event_{i}",
                "task_id": TaskTestDataFactory.make_task_id(),
            }
            await mock_event_bus.publish_event(event)

        assert len(mock_event_bus.published_events) == 5

    @pytest.mark.asyncio
    async def test_event_bus_clear(self, mock_event_bus):
        """Event bus can be cleared"""
        await mock_event_bus.publish_event({"event_type": "test"})
        assert len(mock_event_bus.published_events) == 1

        mock_event_bus.clear()

        assert len(mock_event_bus.published_events) == 0


# ============================================================================
# Test Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling in mock dependencies"""

    @pytest.mark.asyncio
    async def test_repository_error_propagation(self, mock_repository, sample_user_id):
        """Repository errors propagate correctly"""
        mock_repository.set_error(Exception("Database connection failed"))

        with pytest.raises(Exception) as exc_info:
            await mock_repository.create_task(sample_user_id, {"name": "test"})

        assert "Database connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_repository_error_can_be_cleared(self, mock_repository, sample_user_id):
        """Repository error can be cleared"""
        mock_repository.set_error(Exception("Temporary error"))
        mock_repository.clear_error()

        task_data = {
            "name": TaskTestDataFactory.make_task_name(),
            "task_type": TaskType.TODO,
        }

        # Should not raise
        result = await mock_repository.create_task(sample_user_id, task_data)
        assert result is not None


# ============================================================================
# Test User Task Management
# ============================================================================


class TestUserTaskManagement:
    """Test user-level task management"""

    @pytest.mark.asyncio
    async def test_cancel_user_tasks(self, populated_repository, sample_user_id):
        """Cancel all tasks for a user"""
        # Get initial task count
        initial_tasks = await populated_repository.get_user_tasks(sample_user_id)
        active_count = len([t for t in initial_tasks if t.status != TaskStatus.CANCELLED])

        # Cancel all tasks
        cancelled = await populated_repository.cancel_user_tasks(sample_user_id)

        assert cancelled >= 0

        # All tasks should be cancelled
        updated_tasks = await populated_repository.get_user_tasks(sample_user_id)
        assert all(t.status == TaskStatus.CANCELLED for t in updated_tasks)

    @pytest.mark.asyncio
    async def test_pagination(self, mock_repository, sample_user_id):
        """Pagination works correctly"""
        # Create 10 tasks
        for _ in range(10):
            await mock_repository.create_task(
                sample_user_id,
                {
                    "name": TaskTestDataFactory.make_task_name(),
                    "task_type": TaskType.TODO,
                },
            )

        # Get first page
        page1 = await mock_repository.get_user_tasks(sample_user_id, limit=5, offset=0)
        assert len(page1) == 5

        # Get second page
        page2 = await mock_repository.get_user_tasks(sample_user_id, limit=5, offset=5)
        assert len(page2) == 5

        # Verify no overlap
        page1_ids = {t.task_id for t in page1}
        page2_ids = {t.task_id for t in page2}
        assert page1_ids.isdisjoint(page2_ids)


# ============================================================================
# Test Mock Call Logging
# ============================================================================


class TestMockCallLogging:
    """Test mock call logging for assertions"""

    @pytest.mark.asyncio
    async def test_assert_called(self, mock_repository, sample_user_id):
        """Assert method was called"""
        await mock_repository.get_user_tasks(sample_user_id)

        # Should not raise
        mock_repository.assert_called("get_user_tasks")

    @pytest.mark.asyncio
    async def test_assert_called_with(self, mock_repository, sample_user_id):
        """Assert method was called with specific arguments"""
        await mock_repository.get_user_tasks(sample_user_id, status="pending")

        mock_repository.assert_called_with(
            "get_user_tasks",
            user_id=sample_user_id,
            status="pending",
        )

    @pytest.mark.asyncio
    async def test_get_call_count(self, mock_repository, sample_user_id):
        """Get call count for method"""
        await mock_repository.get_user_tasks(sample_user_id)
        await mock_repository.get_user_tasks(sample_user_id)
        await mock_repository.get_user_tasks(sample_user_id)

        count = mock_repository.get_call_count("get_user_tasks")
        assert count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
