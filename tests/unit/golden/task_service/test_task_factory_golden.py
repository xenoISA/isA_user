"""
Task Service - Unit Tests for TestDataFactory (Golden)

Tests for:
- TaskTestDataFactory methods
- Request builders
- Contract validation with factory-generated data

All tests use TaskTestDataFactory - zero hardcoded data.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from tests.contracts.task.data_contract import (
    # Enums
    TaskStatusContract,
    TaskTypeContract,
    TaskPriorityContract,
    TriggerTypeContract,
    # Contracts
    TaskCreateRequestContract,
    TaskUpdateRequestContract,
    TaskExecutionRequestContract,
    TaskFromTemplateRequestContract,
    TaskListQueryContract,
    TaskResponseContract,
    TaskExecutionResponseContract,
    TaskTemplateResponseContract,
    TaskAnalyticsResponseContract,
    # Factory
    TaskTestDataFactory,
    # Builders
    TaskCreateRequestBuilder,
    TaskUpdateRequestBuilder,
    TaskExecutionRequestBuilder,
    TaskFromTemplateRequestBuilder,
)

pytestmark = [pytest.mark.unit]


# ============================================================================
# Test TaskTestDataFactory ID Generators
# ============================================================================


class TestFactoryIdGenerators:
    """Test factory ID generation"""

    def test_task_id_format(self):
        """Task ID has correct format"""
        task_id = TaskTestDataFactory.make_task_id()
        assert task_id.startswith("tsk_")
        assert len(task_id) > 10

    def test_task_id_uniqueness(self):
        """Task IDs are unique"""
        ids = {TaskTestDataFactory.make_task_id() for _ in range(100)}
        assert len(ids) == 100

    def test_execution_id_format(self):
        """Execution ID has correct format"""
        exe_id = TaskTestDataFactory.make_execution_id()
        assert exe_id.startswith("exe_")

    def test_execution_id_uniqueness(self):
        """Execution IDs are unique"""
        ids = {TaskTestDataFactory.make_execution_id() for _ in range(100)}
        assert len(ids) == 100

    def test_template_id_format(self):
        """Template ID has correct format"""
        tpl_id = TaskTestDataFactory.make_template_id()
        assert tpl_id.startswith("tpl_")

    def test_user_id_format(self):
        """User ID has correct format"""
        user_id = TaskTestDataFactory.make_user_id()
        assert user_id.startswith("usr_")


# ============================================================================
# Test TaskTestDataFactory String Generators
# ============================================================================


class TestFactoryStringGenerators:
    """Test factory string generation"""

    def test_task_name_valid_length(self):
        """Task name is within valid length"""
        name = TaskTestDataFactory.make_task_name()
        assert 1 <= len(name) <= 255

    def test_task_name_uniqueness(self):
        """Task names are unique"""
        names = {TaskTestDataFactory.make_task_name() for _ in range(50)}
        assert len(names) == 50

    def test_description_not_empty(self):
        """Description is not empty"""
        desc = TaskTestDataFactory.make_description()
        assert len(desc) > 0

    def test_tag_format(self):
        """Tag has correct format"""
        tag = TaskTestDataFactory.make_tag()
        assert tag.startswith("tag_")

    def test_tags_count(self):
        """make_tags generates correct count"""
        for count in [1, 3, 5, 10]:
            tags = TaskTestDataFactory.make_tags(count)
            assert len(tags) == count

    def test_location_contains_comma(self):
        """Location has city, state format"""
        location = TaskTestDataFactory.make_location()
        assert "," in location


# ============================================================================
# Test TaskTestDataFactory Timestamp Generators
# ============================================================================


class TestFactoryTimestampGenerators:
    """Test factory timestamp generation"""

    def test_timestamp_is_utc(self):
        """Timestamp is in UTC"""
        ts = TaskTestDataFactory.make_timestamp()
        assert ts.tzinfo == timezone.utc

    def test_future_timestamp_is_future(self):
        """Future timestamp is after now"""
        now = datetime.now(timezone.utc)
        future = TaskTestDataFactory.make_future_timestamp(hours=1)
        assert future > now

    def test_past_timestamp_is_past(self):
        """Past timestamp is before now"""
        now = datetime.now(timezone.utc)
        past = TaskTestDataFactory.make_past_timestamp(hours=1)
        assert past < now

    def test_due_date_is_future(self):
        """Due date is in the future"""
        now = datetime.now(timezone.utc)
        due = TaskTestDataFactory.make_due_date()
        assert due > now


# ============================================================================
# Test TaskTestDataFactory Numeric Generators
# ============================================================================


class TestFactoryNumericGenerators:
    """Test factory numeric generation"""

    def test_credits_non_negative(self):
        """Credits are non-negative"""
        for _ in range(50):
            credits = TaskTestDataFactory.make_credits_per_run()
            assert credits >= 0

    def test_duration_positive(self):
        """Duration is positive"""
        for _ in range(50):
            duration = TaskTestDataFactory.make_duration_ms()
            assert duration > 0

    def test_run_count_non_negative(self):
        """Run count is non-negative"""
        for _ in range(50):
            count = TaskTestDataFactory.make_run_count()
            assert count >= 0

    def test_success_count_bounded(self):
        """Success count is bounded by run count"""
        for _ in range(50):
            run_count = TaskTestDataFactory.make_run_count()
            success_count = TaskTestDataFactory.make_success_count(run_count)
            assert 0 <= success_count <= run_count


# ============================================================================
# Test TaskTestDataFactory Config Generators
# ============================================================================


class TestFactoryConfigGenerators:
    """Test factory config generation"""

    def test_weather_config(self):
        """Weather config has required fields"""
        config = TaskTestDataFactory.make_task_config(TaskTypeContract.DAILY_WEATHER)
        assert "location" in config
        assert "units" in config

    def test_news_config(self):
        """News config has categories"""
        config = TaskTestDataFactory.make_task_config(TaskTypeContract.DAILY_NEWS)
        assert "categories" in config

    def test_todo_config(self):
        """Todo config has priority"""
        config = TaskTestDataFactory.make_task_config(TaskTypeContract.TODO)
        assert "priority" in config

    def test_schedule_config_type(self):
        """Schedule config has valid type"""
        config = TaskTestDataFactory.make_schedule_config()
        assert config["type"] in ["cron", "interval"]

    def test_trigger_data_has_fields(self):
        """Trigger data has required fields"""
        data = TaskTestDataFactory.make_trigger_data()
        assert "initiated_by" in data
        assert "timestamp" in data

    def test_execution_result_success(self):
        """Execution result shows success"""
        result = TaskTestDataFactory.make_execution_result()
        assert result["status"] == "success"


# ============================================================================
# Test TaskTestDataFactory Request Generators
# ============================================================================


class TestFactoryRequestGenerators:
    """Test factory request generation"""

    def test_create_request_valid(self):
        """Create request is valid"""
        request = TaskTestDataFactory.make_create_request()
        assert isinstance(request, TaskCreateRequestContract)
        assert len(request.name) > 0
        assert request.task_type in TaskTypeContract

    def test_create_request_with_type(self):
        """Create request respects task type parameter"""
        request = TaskTestDataFactory.make_create_request(
            task_type=TaskTypeContract.REMINDER
        )
        assert request.task_type == TaskTypeContract.REMINDER

    def test_create_request_with_overrides(self):
        """Create request applies overrides"""
        request = TaskTestDataFactory.make_create_request(
            name="Override Name",
            priority=TaskPriorityContract.URGENT
        )
        assert request.name == "Override Name"
        assert request.priority == TaskPriorityContract.URGENT

    def test_update_request_valid(self):
        """Update request is valid"""
        request = TaskTestDataFactory.make_update_request()
        assert isinstance(request, TaskUpdateRequestContract)

    def test_execution_request_valid(self):
        """Execution request is valid"""
        request = TaskTestDataFactory.make_execution_request()
        assert isinstance(request, TaskExecutionRequestContract)

    def test_from_template_request_valid(self):
        """From-template request is valid"""
        request = TaskTestDataFactory.make_from_template_request()
        assert isinstance(request, TaskFromTemplateRequestContract)


# ============================================================================
# Test TaskTestDataFactory Response Generators
# ============================================================================


class TestFactoryResponseGenerators:
    """Test factory response generation"""

    def test_task_response_valid(self):
        """Task response is valid"""
        response = TaskTestDataFactory.make_task_response()
        assert isinstance(response, TaskResponseContract)
        assert response.task_id.startswith("tsk_")

    def test_execution_response_valid(self):
        """Execution response is valid"""
        response = TaskTestDataFactory.make_execution_response()
        assert isinstance(response, TaskExecutionResponseContract)
        assert response.execution_id.startswith("exe_")

    def test_template_response_valid(self):
        """Template response is valid"""
        response = TaskTestDataFactory.make_template_response()
        assert isinstance(response, TaskTemplateResponseContract)

    def test_analytics_response_valid(self):
        """Analytics response is valid"""
        response = TaskTestDataFactory.make_analytics_response()
        assert isinstance(response, TaskAnalyticsResponseContract)
        assert 0 <= response.success_rate <= 100


# ============================================================================
# Test TaskTestDataFactory Invalid Generators
# ============================================================================


class TestFactoryInvalidGenerators:
    """Test factory invalid data generation"""

    def test_invalid_task_id(self):
        """Invalid task ID lacks prefix"""
        invalid = TaskTestDataFactory.make_invalid_task_id()
        assert not invalid.startswith("tsk_")

    def test_invalid_name_empty(self):
        """Invalid empty name"""
        assert TaskTestDataFactory.make_invalid_name_empty() == ""

    def test_invalid_name_whitespace(self):
        """Invalid whitespace name"""
        name = TaskTestDataFactory.make_invalid_name_whitespace()
        assert name.strip() == ""

    def test_invalid_name_too_long(self):
        """Invalid too-long name"""
        name = TaskTestDataFactory.make_invalid_name_too_long()
        assert len(name) > 255

    def test_invalid_credits_negative(self):
        """Invalid negative credits"""
        credits = TaskTestDataFactory.make_invalid_credits_per_run()
        assert credits < 0


# ============================================================================
# Test Request Builders
# ============================================================================


class TestRequestBuilders:
    """Test request builder classes"""

    def test_create_builder_default(self):
        """Create builder has defaults"""
        request = TaskCreateRequestBuilder().build()
        assert isinstance(request, TaskCreateRequestContract)
        assert request.priority == TaskPriorityContract.MEDIUM

    def test_create_builder_chaining(self):
        """Create builder supports chaining"""
        request = (
            TaskCreateRequestBuilder()
            .with_name("Chained Task")
            .with_task_type(TaskTypeContract.TODO)
            .with_priority(TaskPriorityContract.HIGH)
            .with_credits_per_run(2.0)
            .build()
        )
        assert request.name == "Chained Task"
        assert request.task_type == TaskTypeContract.TODO
        assert request.priority == TaskPriorityContract.HIGH
        assert request.credits_per_run == 2.0

    def test_update_builder_default(self):
        """Update builder has defaults"""
        request = TaskUpdateRequestBuilder().build()
        assert isinstance(request, TaskUpdateRequestContract)

    def test_update_builder_with_status(self):
        """Update builder accepts status"""
        request = (
            TaskUpdateRequestBuilder()
            .with_status(TaskStatusContract.COMPLETED)
            .build()
        )
        assert request.status == TaskStatusContract.COMPLETED

    def test_execution_builder_default(self):
        """Execution builder has defaults"""
        request = TaskExecutionRequestBuilder().build()
        assert request.trigger_type == TriggerTypeContract.MANUAL

    def test_execution_builder_with_trigger(self):
        """Execution builder accepts trigger type"""
        request = (
            TaskExecutionRequestBuilder()
            .with_trigger_type(TriggerTypeContract.SCHEDULED)
            .build()
        )
        assert request.trigger_type == TriggerTypeContract.SCHEDULED

    def test_from_template_builder_default(self):
        """From-template builder has defaults"""
        request = TaskFromTemplateRequestBuilder().build()
        assert isinstance(request, TaskFromTemplateRequestContract)

    def test_from_template_builder_chaining(self):
        """From-template builder supports chaining"""
        request = (
            TaskFromTemplateRequestBuilder()
            .with_template_id("tpl_test")
            .with_name("Template Task")
            .with_tags(["test", "template"])
            .build()
        )
        assert request.template_id == "tpl_test"
        assert request.name == "Template Task"
        assert "test" in request.tags


# ============================================================================
# Test Contract Validation with Factory Data
# ============================================================================


class TestContractValidation:
    """Test contract validation using factory data"""

    def test_create_contract_accepts_factory_data(self):
        """Create contract accepts factory-generated data"""
        request = TaskTestDataFactory.make_create_request()
        # Should not raise
        assert request.name is not None
        assert request.task_type is not None

    def test_create_contract_rejects_empty_name(self):
        """Create contract rejects empty name"""
        with pytest.raises(ValidationError):
            TaskCreateRequestContract(
                name=TaskTestDataFactory.make_invalid_name_empty(),
                task_type=TaskTypeContract.TODO
            )

    def test_create_contract_rejects_negative_credits(self):
        """Create contract rejects negative credits"""
        with pytest.raises(ValidationError):
            TaskCreateRequestContract(
                name=TaskTestDataFactory.make_task_name(),
                task_type=TaskTypeContract.TODO,
                credits_per_run=TaskTestDataFactory.make_invalid_credits_per_run()
            )

    def test_list_query_defaults(self):
        """List query has sensible defaults"""
        query = TaskListQueryContract()
        assert query.limit == 100
        assert query.offset == 0

    def test_list_query_rejects_negative_limit(self):
        """List query rejects negative limit"""
        with pytest.raises(ValidationError):
            TaskListQueryContract(limit=TaskTestDataFactory.make_invalid_limit())

    def test_list_query_rejects_negative_offset(self):
        """List query rejects negative offset"""
        with pytest.raises(ValidationError):
            TaskListQueryContract(offset=TaskTestDataFactory.make_invalid_offset())


# ============================================================================
# Test Data Consistency
# ============================================================================


class TestDataConsistency:
    """Test data consistency in generated objects"""

    def test_response_statistics_non_negative(self):
        """Response statistics are non-negative"""
        response = TaskTestDataFactory.make_task_response()
        assert response.run_count >= 0
        assert response.success_count >= 0
        assert response.failure_count >= 0
        assert response.total_credits_consumed >= 0

    def test_analytics_percentages_valid(self):
        """Analytics percentages are in valid range"""
        analytics = TaskTestDataFactory.make_analytics_response()
        assert 0 <= analytics.success_rate <= 100

    def test_analytics_counts_non_negative(self):
        """Analytics counts are non-negative"""
        analytics = TaskTestDataFactory.make_analytics_response()
        assert analytics.total_tasks >= 0
        assert analytics.total_executions >= 0
        assert analytics.successful_executions >= 0
        assert analytics.failed_executions >= 0

    def test_execution_response_timestamps(self):
        """Execution response has valid timestamps"""
        response = TaskTestDataFactory.make_execution_response()
        assert response.started_at is not None
        assert response.created_at is not None
        # completed_at should exist for completed execution
        if response.status == TaskStatusContract.COMPLETED:
            assert response.completed_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
