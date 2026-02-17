"""
Unit Golden Tests: Event Repository Data Access Layer

Tests EventRepository methods with mocked database client.
Focus: Input validation, row conversion, error handling.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from microservices.event_service.event_repository import EventRepository
from microservices.event_service.models import (
    Event,
    EventSource,
    EventCategory,
    EventStatus,
    ProcessingStatus,
    EventStatistics,
    EventProcessingResult,
)


# ==================== Fixtures ====================

@pytest.fixture
def mock_config_manager():
    """Create a mock config manager"""
    config = MagicMock()
    config.discover_service.return_value = ("localhost", 50061)
    return config


@pytest.fixture
def mock_db_client():
    """Create a mock PostgresClient"""
    client = AsyncMock()
    client.insert_into = AsyncMock(return_value=1)
    client.query = AsyncMock(return_value=[])
    client.query_row = AsyncMock(return_value=None)
    client.execute = AsyncMock(return_value=1)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.fixture
def event_repository(mock_config_manager, mock_db_client):
    """Create EventRepository with mocked dependencies"""
    with patch('microservices.event_service.event_repository.AsyncPostgresClient') as MockClient:
        MockClient.return_value = mock_db_client
        repo = EventRepository(config=mock_config_manager)
        repo.db = mock_db_client
    return repo


@pytest.fixture
def sample_db_row():
    """Create a sample database row"""
    now = datetime.utcnow().isoformat()
    return {
        "event_id": "evt_db_123",
        "event_type": "user.login",
        "event_source": "frontend",
        "event_category": "user_action",
        "user_id": "user_456",
        "session_id": None,
        "organization_id": None,
        "device_id": None,
        "correlation_id": None,
        "data": {"method": "oauth"},
        "metadata": {"ip": "10.0.0.1"},
        "context": {},
        "properties": {},
        "status": "pending",
        "processed_at": None,
        "processors": [],
        "error_message": None,
        "retry_count": 0,
        "timestamp": now,
        "created_at": now,
        "updated_at": now,
        "version": "1.0.0",
        "schema_version": "1.0.0",
    }


# ==================== Row Conversion Tests ====================

class TestRowConversion:
    """Test database row to model conversion"""

    def test_row_to_event_converts_enum_values(self, event_repository, sample_db_row):
        """Test row conversion correctly converts enum string values"""
        event = event_repository._row_to_event(sample_db_row)

        assert event.event_source == EventSource.FRONTEND
        assert event.event_category == EventCategory.USER_ACTION
        assert event.status == EventStatus.PENDING

    def test_row_to_event_handles_json_string_data(self, event_repository):
        """Test row conversion parses JSON string data fields"""
        row = {
            **{k: None for k in ["user_id", "session_id", "organization_id", "device_id",
                                 "correlation_id", "processed_at", "error_message"]},
            "event_id": "evt_json",
            "event_type": "test",
            "event_source": "backend",
            "event_category": "system",
            "data": '{"key": "value"}',  # JSON string
            "metadata": '{"meta": "data"}',
            "context": '{}',
            "properties": '{}',
            "status": "pending",
            "processors": [],
            "retry_count": 0,
            "timestamp": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "schema_version": "1.0.0",
        }

        event = event_repository._row_to_event(row)

        assert event.data["key"] == "value"
        assert event.metadata["meta"] == "data"

    def test_row_to_event_handles_none_json_fields(self, event_repository):
        """Test row conversion handles None JSON fields as empty dict"""
        row = {
            **{k: None for k in ["user_id", "session_id", "organization_id", "device_id",
                                 "correlation_id", "processed_at", "error_message",
                                 "data", "metadata", "context", "properties", "processors"]},
            "event_id": "evt_null",
            "event_type": "test",
            "event_source": "backend",
            "event_category": "system",
            "status": "pending",
            "retry_count": 0,
            "timestamp": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "schema_version": "1.0.0",
        }

        event = event_repository._row_to_event(row)

        assert event.data == {}
        assert event.metadata == {}
        assert event.context == {}
        assert event.processors == []

    def test_row_to_event_parses_processed_at_timestamp(self, event_repository, sample_db_row):
        """Test row conversion correctly parses processed_at timestamp"""
        sample_db_row["processed_at"] = datetime.utcnow().isoformat()
        sample_db_row["status"] = "processed"

        event = event_repository._row_to_event(sample_db_row)

        assert event.processed_at is not None
        assert event.status == EventStatus.PROCESSED


# ==================== Statistics Calculation Tests ====================

class TestStatisticsRetrieval:
    """Test statistics retrieval and handling"""

    @pytest.mark.asyncio
    async def test_get_statistics_returns_default_on_no_result(self, event_repository, mock_db_client):
        """Test get_statistics returns default values when no data"""
        mock_db_client.query_row.return_value = None

        stats = await event_repository.get_statistics()

        assert stats.total_events == 0
        assert stats.pending_events == 0
        assert stats.processed_events == 0

    @pytest.mark.asyncio
    async def test_get_statistics_returns_default_on_exception(self, event_repository, mock_db_client):
        """Test get_statistics returns default values on database error"""
        mock_db_client.query_row.side_effect = Exception("Database error")

        stats = await event_repository.get_statistics()

        assert stats.total_events == 0


# ==================== Query Error Handling Tests ====================

class TestQueryErrorHandling:
    """Test query error handling"""

    @pytest.mark.asyncio
    async def test_get_event_returns_none_on_exception(self, event_repository, mock_db_client):
        """Test get_event returns None on database error"""
        mock_db_client.query_row.side_effect = Exception("Database error")

        result = await event_repository.get_event("evt_error")

        assert result is None

    @pytest.mark.asyncio
    async def test_query_events_returns_empty_on_exception(self, event_repository, mock_db_client):
        """Test query_events returns empty list on database error"""
        mock_db_client.query_row.side_effect = Exception("Database error")

        events, total = await event_repository.query_events()

        assert events == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_unprocessed_events_returns_empty_on_exception(self, event_repository, mock_db_client):
        """Test get_unprocessed_events returns empty list on database error"""
        mock_db_client.query.side_effect = Exception("Database error")

        events = await event_repository.get_unprocessed_events()

        assert events == []


# ==================== Update Error Handling Tests ====================

class TestUpdateErrorHandling:
    """Test update error handling"""

    @pytest.mark.asyncio
    async def test_update_event_status_returns_false_on_exception(self, event_repository, mock_db_client):
        """Test update_event_status returns False on database error"""
        mock_db_client.execute.side_effect = Exception("Database error")

        result = await event_repository.update_event_status(
            event_id="evt_123",
            status=EventStatus.PROCESSED,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_update_event_status_returns_false_when_not_found(self, event_repository, mock_db_client):
        """Test update_event_status returns False when event not found"""
        mock_db_client.execute.return_value = 0

        result = await event_repository.update_event_status(
            event_id="evt_nonexistent",
            status=EventStatus.PROCESSED,
        )

        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])
