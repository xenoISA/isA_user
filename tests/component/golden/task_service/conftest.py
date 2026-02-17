"""
Task Service - Component Test Fixtures

Pytest fixtures for component testing using mock dependencies.
"""
import pytest
from datetime import datetime, timezone

from .mocks import (
    MockTaskRepository,
    MockEventBus,
    MockNotificationClient,
    MockCalendarClient,
    MockAccountClient,
)
from microservices.task_service.models import TaskType, TaskStatus, TaskPriority
from tests.contracts.task.data_contract import TaskTestDataFactory


@pytest.fixture
def mock_repository():
    """Create a mock task repository"""
    return MockTaskRepository()


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus"""
    return MockEventBus()


@pytest.fixture
def mock_notification_client():
    """Create a mock notification client"""
    return MockNotificationClient()


@pytest.fixture
def mock_calendar_client():
    """Create a mock calendar client"""
    return MockCalendarClient()


@pytest.fixture
def mock_account_client():
    """Create a mock account client"""
    return MockAccountClient()


@pytest.fixture
def sample_user_id():
    """Generate a sample user ID"""
    return TaskTestDataFactory.make_user_id()


@pytest.fixture
def sample_task_id():
    """Generate a sample task ID"""
    return TaskTestDataFactory.make_task_id()


@pytest.fixture
def sample_execution_id():
    """Generate a sample execution ID"""
    return TaskTestDataFactory.make_execution_id()


@pytest.fixture
def sample_template_id():
    """Generate a sample template ID"""
    return TaskTestDataFactory.make_template_id()


@pytest.fixture
def populated_repository(mock_repository, sample_user_id):
    """Create a repository with sample data"""
    # Add multiple tasks for the user
    for i in range(5):
        task_id = TaskTestDataFactory.make_task_id()
        mock_repository.set_task(
            task_id=task_id,
            user_id=sample_user_id,
            name=TaskTestDataFactory.make_task_name(),
            task_type=TaskType.TODO if i % 2 == 0 else TaskType.REMINDER,
            status=TaskStatus.PENDING if i < 3 else TaskStatus.SCHEDULED,
            priority=TaskPriority.MEDIUM,
        )

    # Add a completed task
    mock_repository.set_task(
        task_id=TaskTestDataFactory.make_task_id(),
        user_id=sample_user_id,
        name="Completed Task",
        task_type=TaskType.TODO,
        status=TaskStatus.COMPLETED,
        priority=TaskPriority.HIGH,
    )

    # Add a task for another user
    other_user_id = TaskTestDataFactory.make_user_id()
    mock_repository.set_task(
        task_id=TaskTestDataFactory.make_task_id(),
        user_id=other_user_id,
        name="Other User Task",
        task_type=TaskType.DAILY_WEATHER,
        config={"location": "New York, NY"},
    )

    # Add templates
    mock_repository.set_template(
        template_id="tpl_weather_free",
        name="Daily Weather",
        task_type=TaskType.DAILY_WEATHER,
        category="information",
        required_subscription_level="free",
    )

    mock_repository.set_template(
        template_id="tpl_news_basic",
        name="Daily News",
        task_type=TaskType.DAILY_NEWS,
        category="information",
        required_subscription_level="basic",
    )

    mock_repository.set_template(
        template_id="tpl_custom_pro",
        name="Custom Automation",
        task_type=TaskType.CUSTOM,
        category="automation",
        required_subscription_level="pro",
    )

    return mock_repository


@pytest.fixture
def basic_user_client(mock_account_client, sample_user_id):
    """Create an account client with basic subscription user"""
    mock_account_client.set_subscription_level(sample_user_id, "basic")
    mock_account_client.set_profile(sample_user_id, {
        "user_id": sample_user_id,
        "name": "Test User",
        "email": "test@example.com",
        "subscription_level": "basic",
    })
    return mock_account_client


@pytest.fixture
def pro_user_client(mock_account_client, sample_user_id):
    """Create an account client with pro subscription user"""
    mock_account_client.set_subscription_level(sample_user_id, "pro")
    mock_account_client.set_profile(sample_user_id, {
        "user_id": sample_user_id,
        "name": "Pro User",
        "email": "pro@example.com",
        "subscription_level": "pro",
    })
    return mock_account_client


@pytest.fixture
def free_user_client(mock_account_client, sample_user_id):
    """Create an account client with free subscription user"""
    mock_account_client.set_subscription_level(sample_user_id, "free")
    mock_account_client.set_profile(sample_user_id, {
        "user_id": sample_user_id,
        "name": "Free User",
        "email": "free@example.com",
        "subscription_level": "free",
    })
    return mock_account_client
