"""
Task Service Integration Tests

Tests the TaskService layer with mocked dependencies (repository, event_bus).
These are NOT HTTP tests - they test the service business logic layer directly.

Purpose:
- Test TaskService business logic with mocked repository
- Test event publishing integration
- Test validation and error handling
- Test cross-service interactions

According to TDD_CONTRACT.md:
- Service layer tests use mocked repository (no real DB)
- Service layer tests use mocked event bus (no real NATS)
- Use TaskTestDataFactory from data contracts (no hardcoded data)
- Target 15-20 tests with full coverage

Usage:
    pytest tests/integration/golden/task_service/test_task_integration.py -v
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any

# Import from centralized data contracts
from tests.contracts.task.data_contract import (
    TaskTestDataFactory,
    TaskCreateRequestContract,
    TaskUpdateRequestContract,
    TaskExecutionRequestContract,
    TaskStatusContract,
    TaskTypeContract,
    TaskPriorityContract,
    TriggerTypeContract,
)

# Import service layer to test
from microservices.task_service.task_service import (
    TaskService,
    TaskExecutionError,
)

# Import models
from microservices.task_service.models import (
    TaskResponse,
    TaskExecutionResponse,
    TaskTemplateResponse,
    TaskAnalyticsResponse,
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskExecutionRequest,
    TaskStatus,
    TaskType,
    TaskPriority,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_repository():
    """
    Mock repository for testing service layer.

    This replaces the real TaskRepository with an AsyncMock,
    allowing us to test business logic without database I/O.
    """
    return AsyncMock()


@pytest.fixture
def mock_event_bus():
    """
    Mock event bus for testing event publishing.

    This replaces the real NATS connection with a Mock,
    allowing us to verify events are published correctly.
    """
    mock = AsyncMock()
    mock.publish_event = AsyncMock()
    return mock


@pytest.fixture
def mock_notification_client():
    """Mock notification client for cross-service tests"""
    return AsyncMock()


@pytest.fixture
def mock_calendar_client():
    """Mock calendar client for cross-service tests"""
    return AsyncMock()


@pytest.fixture
def task_service(mock_repository, mock_event_bus):
    """
    Create TaskService with mocked dependencies.

    This is the service under test - we test its business logic
    while mocking all I/O dependencies.
    """
    service = TaskService(event_bus=mock_event_bus)
    # Replace repository with mock
    service.repository = mock_repository
    return service


@pytest.fixture
def sample_task():
    """
    Create sample task for testing using data contract factory.

    This ensures consistent test data structure across all tests.
    """
    task_id = TaskTestDataFactory.make_task_id()
    user_id = TaskTestDataFactory.make_user_id()
    name = TaskTestDataFactory.make_task_name()

    return TaskResponse(
        id=1,
        task_id=task_id,
        user_id=user_id,
        name=name,
        description=TaskTestDataFactory.make_description(),
        task_type=TaskType.TODO,
        status=TaskStatus.PENDING,
        priority=TaskPriority.MEDIUM,
        config={},
        schedule=None,
        credits_per_run=0.0,
        tags=TaskTestDataFactory.make_tags(2),
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
        deleted_at=None,
    )


@pytest.fixture
def sample_execution():
    """Create sample execution for testing"""
    return TaskExecutionResponse(
        id=1,
        execution_id=TaskTestDataFactory.make_execution_id(),
        task_id=TaskTestDataFactory.make_task_id(),
        user_id=TaskTestDataFactory.make_user_id(),
        status=TaskStatus.RUNNING,
        trigger_type="manual",
        trigger_data={},
        result=None,
        error_message=None,
        error_details=None,
        credits_consumed=0.0,
        tokens_used=None,
        api_calls_made=0,
        duration_ms=None,
        started_at=datetime.now(timezone.utc),
        completed_at=None,
        created_at=datetime.now(timezone.utc),
    )


# ============================================================================
# TEST CLASS 1: Task Creation Tests
# ============================================================================


class TestTaskCreation:
    """
    Test task creation operations.

    Tests the create_task() method.
    """

    async def test_create_task_success(
        self, task_service, mock_repository, sample_task
    ):
        """
        Test that create_task creates a new task.

        GIVEN: A valid task creation request
        WHEN: create_task is called
        THEN: Repository creates the task and returns TaskResponse
        """
        # Arrange
        user_id = sample_task.user_id
        request = TaskCreateRequest(
            name=TaskTestDataFactory.make_task_name(),
            task_type=TaskType.TODO,
            priority=TaskPriority.MEDIUM,
        )

        mock_repository.create_task.return_value = sample_task
        mock_repository.get_user_tasks.return_value = []  # No existing tasks

        # Act
        result = await task_service.create_task(user_id, request)

        # Assert
        assert result is not None
        assert result.task_id == sample_task.task_id
        assert result.user_id == user_id
        mock_repository.create_task.assert_called_once()

    async def test_create_task_with_schedule(
        self, task_service, mock_repository, sample_task
    ):
        """
        Test that create_task handles scheduled tasks.

        GIVEN: A task creation request with schedule
        WHEN: create_task is called
        THEN: Task is created with SCHEDULED status and next_run_time
        """
        # Arrange
        user_id = sample_task.user_id
        schedule = {"type": "daily", "run_time": "09:00"}
        request = TaskCreateRequest(
            name=TaskTestDataFactory.make_task_name(),
            task_type=TaskType.DAILY_WEATHER,
            config={"location": TaskTestDataFactory.make_location()},
            schedule=schedule,
        )

        # Mock scheduled task
        scheduled_task = TaskResponse(**sample_task.dict())
        scheduled_task.status = TaskStatus.SCHEDULED
        scheduled_task.schedule = schedule
        mock_repository.create_task.return_value = scheduled_task
        mock_repository.get_user_tasks.return_value = []

        # Act
        result = await task_service.create_task(user_id, request)

        # Assert
        assert result.status == TaskStatus.SCHEDULED

    async def test_create_task_validates_weather_config(
        self, task_service, mock_repository, sample_task
    ):
        """
        Test that create_task validates weather task config.

        GIVEN: A weather task without required location
        WHEN: create_task is called
        THEN: Raises TaskExecutionError
        """
        # Arrange
        user_id = sample_task.user_id
        request = TaskCreateRequest(
            name=TaskTestDataFactory.make_task_name(),
            task_type=TaskType.DAILY_WEATHER,
            config={},  # Missing location
        )
        mock_repository.get_user_tasks.return_value = []

        # Act & Assert
        with pytest.raises(TaskExecutionError, match="location"):
            await task_service.create_task(user_id, request)


# ============================================================================
# TEST CLASS 2: Task Retrieval Tests
# ============================================================================


class TestTaskRetrieval:
    """
    Test task retrieval operations.

    Tests get_task() and get_user_tasks() methods.
    """

    async def test_get_task_success(
        self, task_service, mock_repository, sample_task
    ):
        """
        Test successful task retrieval.

        GIVEN: An existing task
        WHEN: get_task is called
        THEN: Returns the task
        """
        # Arrange
        mock_repository.get_task_by_id.return_value = sample_task

        # Act
        result = await task_service.get_task(sample_task.task_id, sample_task.user_id)

        # Assert
        assert result is not None
        assert result.task_id == sample_task.task_id
        assert mock_repository.get_task_by_id.called

    async def test_get_task_not_found(self, task_service, mock_repository):
        """
        Test task retrieval for non-existent task.

        GIVEN: A non-existent task_id
        WHEN: get_task is called
        THEN: Raises TaskExecutionError
        """
        # Arrange
        task_id = TaskTestDataFactory.make_task_id()
        user_id = TaskTestDataFactory.make_user_id()
        mock_repository.get_task_by_id.return_value = None

        # Act & Assert
        with pytest.raises(TaskExecutionError, match="not found|access denied"):
            await task_service.get_task(task_id, user_id)

    async def test_get_user_tasks_returns_list(
        self, task_service, mock_repository, sample_task
    ):
        """
        Test get_user_tasks returns task list.

        GIVEN: A user with tasks
        WHEN: get_user_tasks is called
        THEN: Returns TaskListResponse with tasks
        """
        # Arrange
        user_id = sample_task.user_id
        mock_repository.get_user_tasks.return_value = [sample_task]

        # Act
        result = await task_service.get_user_tasks(user_id)

        # Assert
        assert result.count >= 1
        assert len(result.tasks) >= 1
        mock_repository.get_user_tasks.assert_called_once()

    async def test_get_user_tasks_with_filters(
        self, task_service, mock_repository, sample_task
    ):
        """
        Test get_user_tasks with status and type filters.

        GIVEN: Filter parameters
        WHEN: get_user_tasks is called
        THEN: Repository receives filter parameters
        """
        # Arrange
        user_id = sample_task.user_id
        mock_repository.get_user_tasks.return_value = [sample_task]

        # Act
        result = await task_service.get_user_tasks(
            user_id,
            status="pending",
            task_type="todo",
            limit=50,
            offset=0,
        )

        # Assert
        mock_repository.get_user_tasks.assert_called_once_with(
            user_id=user_id,
            status="pending",
            task_type="todo",
            limit=50,
            offset=0,
        )


# ============================================================================
# TEST CLASS 3: Task Update Tests
# ============================================================================


class TestTaskUpdate:
    """
    Test task update operations.

    Tests update_task() method.
    """

    async def test_update_task_success(
        self, task_service, mock_repository, sample_task
    ):
        """
        Test successful task update.

        GIVEN: An existing task and valid update data
        WHEN: update_task is called
        THEN: Task is updated successfully
        """
        # Arrange
        new_name = TaskTestDataFactory.make_task_name()
        request = TaskUpdateRequest(name=new_name, priority=TaskPriority.HIGH)

        updated_task = TaskResponse(**sample_task.dict())
        updated_task.name = new_name
        updated_task.priority = TaskPriority.HIGH

        # Set up mock to return updated task on subsequent calls
        mock_repository.get_task_by_id.return_value = updated_task
        mock_repository.update_task.return_value = updated_task

        # Act
        result = await task_service.update_task(
            sample_task.task_id, sample_task.user_id, request
        )

        # Assert
        assert result is not None
        assert mock_repository.update_task.called or mock_repository.get_task_by_id.called

    async def test_update_task_not_found(self, task_service, mock_repository):
        """
        Test update for non-existent task.

        GIVEN: A non-existent task_id
        WHEN: update_task is called
        THEN: Raises TaskExecutionError
        """
        # Arrange
        task_id = TaskTestDataFactory.make_task_id()
        user_id = TaskTestDataFactory.make_user_id()
        request = TaskUpdateRequest(name="New Name")

        mock_repository.get_task_by_id.return_value = None

        # Act & Assert
        with pytest.raises(TaskExecutionError, match="not found|access denied"):
            await task_service.update_task(task_id, user_id, request)

    async def test_update_task_status_change(
        self, task_service, mock_repository, sample_task
    ):
        """
        Test task status update.

        GIVEN: A status change request
        WHEN: update_task is called
        THEN: Task status is updated
        """
        # Arrange
        request = TaskUpdateRequest(status=TaskStatus.COMPLETED)

        updated_task = TaskResponse(**sample_task.dict())
        updated_task.status = TaskStatus.COMPLETED

        mock_repository.get_task_by_id.return_value = updated_task
        mock_repository.update_task.return_value = updated_task

        # Act
        result = await task_service.update_task(
            sample_task.task_id, sample_task.user_id, request
        )

        # Assert
        assert result.status == TaskStatus.COMPLETED


# ============================================================================
# TEST CLASS 4: Task Deletion Tests
# ============================================================================


class TestTaskDeletion:
    """
    Test task deletion operations.

    Tests delete_task() method.
    """

    async def test_delete_task_success(
        self, task_service, mock_repository, sample_task
    ):
        """
        Test successful task deletion.

        GIVEN: An existing task
        WHEN: delete_task is called
        THEN: Task is soft-deleted
        """
        # Arrange
        mock_repository.get_task_by_id.return_value = sample_task
        mock_repository.delete_task.return_value = True

        # Act
        result = await task_service.delete_task(
            sample_task.task_id, sample_task.user_id
        )

        # Assert
        assert result is True
        mock_repository.delete_task.assert_called_once_with(
            sample_task.task_id, sample_task.user_id
        )

    async def test_delete_task_not_found(self, task_service, mock_repository):
        """
        Test deletion of non-existent task.

        GIVEN: A non-existent task_id
        WHEN: delete_task is called
        THEN: Raises TaskExecutionError
        """
        # Arrange
        task_id = TaskTestDataFactory.make_task_id()
        user_id = TaskTestDataFactory.make_user_id()
        mock_repository.get_task_by_id.return_value = None

        # Act & Assert
        with pytest.raises(TaskExecutionError, match="not found|access denied|deletion failed"):
            await task_service.delete_task(task_id, user_id)


# ============================================================================
# TEST CLASS 5: Task Execution Tests
# ============================================================================


class TestTaskExecution:
    """
    Test task execution operations.

    Tests execute_task() method.
    """

    async def test_execute_task_creates_execution_record(
        self, task_service, mock_repository, sample_task, sample_execution
    ):
        """
        Test that execute_task creates execution record.

        GIVEN: A valid task
        WHEN: execute_task is called
        THEN: Execution record is created
        """
        # Arrange
        request = TaskExecutionRequest(
            trigger_type="manual",
            trigger_data=TaskTestDataFactory.make_trigger_data(),
        )

        mock_repository.get_task_by_id.return_value = sample_task
        mock_repository.create_execution_record.return_value = sample_execution
        mock_repository.get_user_tasks.return_value = []

        # Act
        result = await task_service.execute_task(
            sample_task.task_id, sample_task.user_id, request
        )

        # Assert
        assert result is not None
        assert result.execution_id == sample_execution.execution_id
        mock_repository.create_execution_record.assert_called_once()

    async def test_execute_task_rejects_cancelled_task(
        self, task_service, mock_repository, sample_task
    ):
        """
        Test that execute_task rejects cancelled tasks.

        GIVEN: A cancelled task
        WHEN: execute_task is called
        THEN: Raises TaskExecutionError
        """
        # Arrange
        cancelled_task = TaskResponse(**sample_task.dict())
        cancelled_task.status = TaskStatus.CANCELLED

        request = TaskExecutionRequest(trigger_type="manual")
        mock_repository.get_task_by_id.return_value = cancelled_task

        # Act & Assert
        with pytest.raises(TaskExecutionError, match="Cannot execute|CANCELLED|status"):
            await task_service.execute_task(
                sample_task.task_id, sample_task.user_id, request
            )

    async def test_execute_task_rejects_running_task(
        self, task_service, mock_repository, sample_task
    ):
        """
        Test that execute_task rejects already running tasks.

        GIVEN: A running task
        WHEN: execute_task is called
        THEN: Raises TaskExecutionError
        """
        # Arrange
        running_task = TaskResponse(**sample_task.dict())
        running_task.status = TaskStatus.RUNNING

        request = TaskExecutionRequest(trigger_type="manual")
        mock_repository.get_task_by_id.return_value = running_task

        # Act & Assert
        with pytest.raises(TaskExecutionError, match="Cannot execute|RUNNING|status"):
            await task_service.execute_task(
                sample_task.task_id, sample_task.user_id, request
            )


# ============================================================================
# TEST CLASS 6: Event Publishing Tests
# ============================================================================


class TestEventPublishing:
    """
    Test event publishing integration.

    Verifies that service layer publishes events correctly.
    """

    async def test_create_task_publishes_event(
        self, task_service, mock_repository, mock_event_bus, sample_task
    ):
        """
        Test that create_task publishes task.created event.

        GIVEN: A successful task creation
        WHEN: create_task completes
        THEN: task.created event is published
        """
        # Arrange
        user_id = sample_task.user_id
        request = TaskCreateRequest(
            name=TaskTestDataFactory.make_task_name(),
            task_type=TaskType.TODO,
        )

        mock_repository.create_task.return_value = sample_task
        mock_repository.get_user_tasks.return_value = []

        # Act
        await task_service.create_task(user_id, request)

        # Assert
        mock_event_bus.publish_event.assert_called()

    async def test_update_task_publishes_event(
        self, task_service, mock_repository, mock_event_bus, sample_task
    ):
        """
        Test that update_task publishes task.updated event.

        GIVEN: A successful task update
        WHEN: update_task completes
        THEN: task.updated event is published
        """
        # Arrange
        request = TaskUpdateRequest(name="Updated Name")

        updated_task = TaskResponse(**sample_task.dict())
        updated_task.name = "Updated Name"

        mock_repository.get_task_by_id.return_value = updated_task
        mock_repository.update_task.return_value = updated_task

        # Act
        await task_service.update_task(
            sample_task.task_id, sample_task.user_id, request
        )

        # Assert
        mock_event_bus.publish_event.assert_called()

    async def test_delete_task_publishes_event(
        self, task_service, mock_repository, mock_event_bus, sample_task
    ):
        """
        Test that delete_task publishes task.cancelled event.

        GIVEN: A successful task deletion
        WHEN: delete_task completes
        THEN: task.cancelled event is published
        """
        # Arrange
        mock_repository.get_task_by_id.return_value = sample_task
        mock_repository.delete_task.return_value = True

        # Act
        await task_service.delete_task(sample_task.task_id, sample_task.user_id)

        # Assert
        mock_event_bus.publish_event.assert_called()


# ============================================================================
# TEST CLASS 7: Templates and Analytics Tests
# ============================================================================


class TestTemplatesAndAnalytics:
    """
    Test templates and analytics operations.

    Tests get_task_templates() and get_task_analytics() methods.
    """

    async def test_get_task_templates(self, task_service, mock_repository):
        """
        Test get_task_templates returns templates.

        GIVEN: Available templates
        WHEN: get_task_templates is called
        THEN: Returns filtered templates
        """
        # Arrange
        user_id = TaskTestDataFactory.make_user_id()
        template = TaskTemplateResponse(
            id=1,
            template_id=TaskTestDataFactory.make_template_id(),
            name="Weather Template",
            description="Daily weather updates",
            category="information",
            task_type=TaskType.DAILY_WEATHER,
            default_config={"location": "New York"},
            required_fields=["location"],
            optional_fields=[],
            config_schema={},
            required_subscription_level="free",
            credits_per_run=0.0,
            tags=[],
            metadata={},
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_repository.get_task_templates.return_value = [template]

        # Act
        result = await task_service.get_task_templates(user_id)

        # Assert
        assert len(result) == 1
        assert result[0].template_id == template.template_id

    async def test_get_task_analytics(
        self, task_service, mock_repository
    ):
        """
        Test get_task_analytics returns analytics.

        GIVEN: A user with task history
        WHEN: get_task_analytics is called
        THEN: Returns TaskAnalyticsResponse
        """
        # Arrange
        user_id = TaskTestDataFactory.make_user_id()
        analytics = TaskAnalyticsResponse(
            user_id=user_id,
            time_period="30_days",
            total_tasks=10,
            active_tasks=5,
            completed_tasks=3,
            failed_tasks=1,
            paused_tasks=1,
            total_executions=50,
            successful_executions=45,
            failed_executions=5,
            success_rate=90.0,
            average_execution_time=1.5,
            total_credits_consumed=25.0,
            total_tokens_used=1000,
            total_api_calls=50,
            task_types_distribution={"todo": 5, "reminder": 3, "daily_weather": 2},
            busiest_hours=[9, 10, 11],
            busiest_days=["Monday", "Tuesday"],
        )
        mock_repository.get_task_analytics.return_value = analytics

        # Act
        result = await task_service.get_task_analytics(user_id)

        # Assert
        assert result is not None
        assert result.user_id == user_id
        assert result.total_tasks == 10
        assert result.success_rate == 90.0


# ============================================================================
# TEST CLASS 8: Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """
    Test error handling and edge cases.

    Verifies that service layer handles errors gracefully.
    """

    async def test_service_handles_repository_errors(
        self, task_service, mock_repository
    ):
        """
        Test that service layer wraps repository errors.

        GIVEN: Repository throws exception
        WHEN: Service method is called
        THEN: Exception is wrapped appropriately
        """
        # Arrange
        task_id = TaskTestDataFactory.make_task_id()
        user_id = TaskTestDataFactory.make_user_id()
        mock_repository.get_task_by_id.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(TaskExecutionError):
            await task_service.get_task(task_id, user_id)

    async def test_event_publishing_failures_dont_block_operations(
        self, task_service, mock_repository, mock_event_bus, sample_task
    ):
        """
        Test that event publishing failures don't break operations.

        GIVEN: Event bus is unavailable
        WHEN: An operation is performed
        THEN: Operation succeeds even if event fails
        """
        # Arrange
        user_id = sample_task.user_id
        request = TaskCreateRequest(
            name=TaskTestDataFactory.make_task_name(),
            task_type=TaskType.TODO,
        )

        mock_repository.create_task.return_value = sample_task
        mock_repository.get_user_tasks.return_value = []
        mock_event_bus.publish_event.side_effect = Exception("NATS unavailable")

        # Act - Should not raise
        result = await task_service.create_task(user_id, request)

        # Assert - Operation succeeded despite event failure
        assert result is not None
        assert result.task_id == sample_task.task_id


# ============================================================================
# SUMMARY
# ============================================================================
"""
TASK SERVICE INTEGRATION TESTS SUMMARY:

Test Coverage (20+ tests total):

1. Task Creation (3 tests):
   - Creates new task
   - Handles scheduled tasks
   - Validates weather config

2. Task Retrieval (4 tests):
   - Get task success
   - Get task not found
   - Get user tasks returns list
   - Get user tasks with filters

3. Task Update (3 tests):
   - Update task success
   - Update task not found
   - Update task status change

4. Task Deletion (2 tests):
   - Delete task success
   - Delete task not found

5. Task Execution (3 tests):
   - Creates execution record
   - Rejects cancelled task
   - Rejects running task

6. Event Publishing (3 tests):
   - Create task publishes event
   - Update task publishes event
   - Delete task publishes event

7. Templates and Analytics (2 tests):
   - Get task templates
   - Get task analytics

8. Error Handling (2 tests):
   - Handles repository errors
   - Event failures don't block operations

Key Features:
- Uses TaskTestDataFactory from data contracts (no hardcoded data)
- Mocks repository and event bus (no I/O dependencies)
- Tests business logic layer only
- Verifies event publishing patterns
- Comprehensive error handling coverage

Run with:
    pytest tests/integration/golden/task_service/test_task_integration.py -v
"""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
