"""
Session Service Integration Tests

Tests the SessionService layer with mocked dependencies (repository, event_bus).
These are NOT HTTP tests - they test the service business logic layer directly.

Purpose:
- Test SessionService business logic with mocked repository
- Test event publishing integration
- Test validation and error handling
- Test cross-service interactions (account service)

According to TDD_CONTRACT.md:
- Service layer tests use mocked repository (no real DB)
- Service layer tests use mocked event bus (no real NATS)
- Use SessionTestDataFactory from data contracts (no hardcoded data)
- Target 20-25 tests with full coverage

Usage:
    pytest tests/integration/golden/session_service/test_session_integration.py -v
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, MagicMock
from typing import Dict, Any, List

# Import from centralized data contracts
from tests.contracts.session.data_contract import (
    SessionTestDataFactory,
    SessionCreateRequestContract,
    SessionUpdateRequestContract,
    MessageCreateRequestContract,
    SessionStatusEnum,
    MessageRoleEnum,
    MessageTypeEnum,
)

# Import service layer to test
from microservices.session_service.session_service import SessionService

# Import protocols for type safety and error types
from microservices.session_service.protocols import (
    SessionNotFoundError,
    SessionValidationError,
    SessionServiceError,
)

# Import models
from microservices.session_service.models import (
    Session,
    SessionMessage,
    SessionCreateRequest,
    SessionUpdateRequest,
    MessageCreateRequest,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_session_repository():
    """
    Mock session repository for testing service layer.

    This replaces the real SessionRepository with an AsyncMock,
    allowing us to test business logic without database I/O.
    """
    repo = AsyncMock()
    repo._sessions = {}  # In-memory store for test data
    return repo


@pytest.fixture
def mock_message_repository():
    """
    Mock message repository for testing service layer.

    This replaces the real SessionMessageRepository with an AsyncMock,
    allowing us to test business logic without database I/O.
    """
    repo = AsyncMock()
    repo._messages = {}  # In-memory store for test data
    return repo


@pytest.fixture
def mock_event_bus():
    """
    Mock event bus for testing event publishing.

    This replaces the real NATS connection with an AsyncMock,
    allowing us to verify events are published correctly.
    """
    bus = AsyncMock()
    bus.published_events = []

    async def capture_event(event):
        bus.published_events.append(event)

    bus.publish_event = AsyncMock(side_effect=capture_event)
    return bus


@pytest.fixture
def mock_account_client():
    """Mock account client for cross-service tests"""
    client = AsyncMock()
    client._accounts = {}
    return client


@pytest.fixture
def session_service(mock_session_repository, mock_message_repository, mock_event_bus, mock_account_client):
    """
    Create SessionService with mocked dependencies.

    This is the service under test - we test its business logic
    while mocking all I/O dependencies.
    """
    return SessionService(
        session_repo=mock_session_repository,
        message_repo=mock_message_repository,
        event_bus=mock_event_bus,
        account_client=mock_account_client,
    )


@pytest.fixture
def sample_session():
    """
    Create sample session for testing using data contract factory.

    This ensures consistent test data structure across all tests.
    """
    now = datetime.now(timezone.utc)
    session = MagicMock()
    session.session_id = SessionTestDataFactory.make_session_id()
    session.user_id = SessionTestDataFactory.make_user_id()
    session.status = "active"
    session.conversation_data = {}
    session.metadata = {}
    session.is_active = True
    session.message_count = 0
    session.total_tokens = 0
    session.total_cost = 0.0
    session.session_summary = ""
    session.created_at = now
    session.updated_at = now
    session.last_activity = now
    return session


@pytest.fixture
def sample_message(sample_session):
    """Create sample message for testing."""
    now = datetime.now(timezone.utc)
    message = MagicMock()
    message.message_id = SessionTestDataFactory.make_message_id()
    message.session_id = sample_session.session_id
    message.user_id = sample_session.user_id
    message.role = "user"
    message.content = SessionTestDataFactory.make_content()
    message.message_type = "chat"
    message.metadata = {}
    message.tokens_used = 100
    message.cost_usd = 0.01
    message.created_at = now
    return message


# ============================================================================
# TEST CLASS 1: Session Creation Tests
# ============================================================================

class TestSessionCreation:
    """
    Test session creation operations.

    Tests the create_session() method which handles new session creation.
    """

    async def test_create_session_success(
        self, session_service, mock_session_repository, mock_account_client, sample_session
    ):
        """
        Test successful session creation.

        GIVEN: A valid session creation request
        WHEN: create_session is called
        THEN: Repository creates the session and returns the response
        """
        # Arrange - Use data contract factory
        request_contract = SessionTestDataFactory.make_session_create_request()
        request = SessionCreateRequest(**request_contract.model_dump())

        # Mock account client to return user exists
        mock_account_client.get_account_profile.return_value = {
            "user_id": request.user_id,
            "is_active": True,
        }

        # Mock repository to return created session
        sample_session.user_id = request.user_id
        mock_session_repository.create_session.return_value = sample_session

        # Act
        result = await session_service.create_session(request)

        # Assert
        assert result.user_id == request.user_id
        assert result.status == "active"
        assert result.is_active is True
        assert result.message_count == 0

        # Verify repository was called
        mock_session_repository.create_session.assert_called_once()

    async def test_create_session_with_custom_session_id(
        self, session_service, mock_session_repository, mock_account_client, sample_session
    ):
        """
        Test session creation with custom session ID.

        GIVEN: A request with custom session_id
        WHEN: create_session is called
        THEN: Session is created with the provided ID
        """
        # Arrange
        custom_session_id = SessionTestDataFactory.make_session_id()
        request_contract = SessionTestDataFactory.make_session_create_request(
            session_id=custom_session_id
        )
        request = SessionCreateRequest(**request_contract.model_dump())

        # Mock
        sample_session.session_id = custom_session_id
        sample_session.user_id = request.user_id
        mock_account_client.get_account_profile.return_value = {"user_id": request.user_id}
        mock_session_repository.create_session.return_value = sample_session

        # Act
        result = await session_service.create_session(request)

        # Assert
        assert result.session_id == custom_session_id

    async def test_create_session_validates_empty_user_id(self, session_service):
        """
        Test that create_session rejects empty user_id.

        GIVEN: A request with empty user_id
        WHEN: create_session is called
        THEN: Raises SessionValidationError
        """
        # Arrange - Can't use contract factory since it validates
        request = SessionCreateRequest(
            user_id="   ",  # Whitespace only
            conversation_data={},
            metadata={},
        )

        # Act & Assert
        with pytest.raises(SessionValidationError, match="user_id is required"):
            await session_service.create_session(request)

    async def test_create_session_account_service_unavailable(
        self, session_service, mock_session_repository, mock_account_client, sample_session
    ):
        """
        Test that session creation proceeds when account service is unavailable (fail-open).

        GIVEN: Account service is unavailable
        WHEN: create_session is called
        THEN: Session is created anyway (fail-open behavior)
        """
        # Arrange
        request_contract = SessionTestDataFactory.make_session_create_request()
        request = SessionCreateRequest(**request_contract.model_dump())

        # Mock account service to fail
        mock_account_client.get_account_profile.side_effect = Exception("Service unavailable")
        mock_session_repository.create_session.return_value = sample_session

        # Act - Should not raise exception
        result = await session_service.create_session(request)

        # Assert - Session created despite account service failure
        assert result is not None
        assert result.status == "active"

    async def test_create_session_publishes_event(
        self, session_service, mock_session_repository, mock_account_client, mock_event_bus, sample_session
    ):
        """
        Test that create_session publishes SESSION_STARTED event.

        GIVEN: A valid session creation request
        WHEN: create_session is called
        THEN: SESSION_STARTED event is published
        """
        # Arrange
        request_contract = SessionTestDataFactory.make_session_create_request()
        request = SessionCreateRequest(**request_contract.model_dump())

        mock_account_client.get_account_profile.return_value = {"user_id": request.user_id}
        mock_session_repository.create_session.return_value = sample_session

        # Act
        await session_service.create_session(request)

        # Assert - Event was published
        mock_event_bus.publish_event.assert_called_once()
        published_event = mock_event_bus.published_events[0]
        assert "session_id" in published_event.data
        assert published_event.data["user_id"] == request.user_id


# ============================================================================
# TEST CLASS 2: Session Retrieval Tests
# ============================================================================

class TestSessionRetrieval:
    """
    Test session retrieval operations.

    Tests get_session() and get_user_sessions() methods.
    """

    async def test_get_session_success(
        self, session_service, mock_session_repository, sample_session
    ):
        """
        Test successful session retrieval.

        GIVEN: An existing session
        WHEN: get_session is called
        THEN: Returns the session response
        """
        # Arrange
        mock_session_repository.get_by_session_id.return_value = sample_session

        # Act
        result = await session_service.get_session(sample_session.session_id)

        # Assert
        assert result.session_id == sample_session.session_id
        assert result.user_id == sample_session.user_id
        assert result.status == sample_session.status

        mock_session_repository.get_by_session_id.assert_called_once_with(sample_session.session_id)

    async def test_get_session_not_found(
        self, session_service, mock_session_repository
    ):
        """
        Test session retrieval for non-existent session.

        GIVEN: A non-existent session_id
        WHEN: get_session is called
        THEN: Raises SessionNotFoundError
        """
        # Arrange
        session_id = SessionTestDataFactory.make_nonexistent_session_id()
        mock_session_repository.get_by_session_id.return_value = None

        # Act & Assert
        with pytest.raises(SessionNotFoundError, match=f"Session not found: {session_id}"):
            await session_service.get_session(session_id)

    async def test_get_session_authorization_check(
        self, session_service, mock_session_repository, sample_session
    ):
        """
        Test that get_session validates user_id authorization.

        GIVEN: A session belonging to user A
        WHEN: get_session is called with user B's user_id
        THEN: Raises SessionNotFoundError (not 403 to avoid info leak)
        """
        # Arrange
        different_user_id = SessionTestDataFactory.make_user_id()
        mock_session_repository.get_by_session_id.return_value = sample_session

        # Act & Assert
        with pytest.raises(SessionNotFoundError):
            await session_service.get_session(
                sample_session.session_id,
                user_id=different_user_id
            )

    async def test_get_user_sessions_success(
        self, session_service, mock_session_repository, sample_session
    ):
        """
        Test get_user_sessions returns user's sessions.

        GIVEN: A user with multiple sessions
        WHEN: get_user_sessions is called
        THEN: Returns list of sessions for that user
        """
        # Arrange
        mock_session_repository.get_user_sessions.return_value = [sample_session]

        # Act
        result = await session_service.get_user_sessions(
            user_id=sample_session.user_id,
            active_only=False,
            page=1,
            page_size=50
        )

        # Assert
        assert len(result.sessions) == 1
        assert result.sessions[0].session_id == sample_session.session_id
        assert result.page == 1
        assert result.page_size == 50

    async def test_get_user_sessions_empty(
        self, session_service, mock_session_repository
    ):
        """
        Test get_user_sessions returns empty list for user with no sessions.

        GIVEN: A user with no sessions
        WHEN: get_user_sessions is called
        THEN: Returns empty sessions list (not error)
        """
        # Arrange
        user_id = SessionTestDataFactory.make_user_id()
        mock_session_repository.get_user_sessions.return_value = []

        # Act
        result = await session_service.get_user_sessions(user_id)

        # Assert
        assert result.sessions == []
        assert result.total == 0

    async def test_get_user_sessions_active_only_filter(
        self, session_service, mock_session_repository, sample_session
    ):
        """
        Test get_user_sessions respects active_only filter.

        GIVEN: active_only=true parameter
        WHEN: get_user_sessions is called
        THEN: Repository is called with active_only=true
        """
        # Arrange
        mock_session_repository.get_user_sessions.return_value = [sample_session]

        # Act
        await session_service.get_user_sessions(
            user_id=sample_session.user_id,
            active_only=True
        )

        # Assert - Verify repository received the filter
        call_args = mock_session_repository.get_user_sessions.call_args
        assert call_args.kwargs["active_only"] is True


# ============================================================================
# TEST CLASS 3: Session Update Tests
# ============================================================================

class TestSessionUpdate:
    """
    Test session update operations.

    Tests update_session() and end_session() methods.
    """

    async def test_update_session_status(
        self, session_service, mock_session_repository, sample_session
    ):
        """
        Test successful session status update.

        GIVEN: An existing session
        WHEN: update_session is called with new status
        THEN: Session status is updated
        """
        # Arrange
        request = SessionUpdateRequest(status="completed")
        mock_session_repository.get_by_session_id.return_value = sample_session
        mock_session_repository.update_session_status.return_value = True
        mock_session_repository.update_session_activity.return_value = True

        updated_session = MagicMock()
        updated_session.session_id = sample_session.session_id
        updated_session.user_id = sample_session.user_id
        updated_session.status = "completed"
        updated_session.is_active = True
        updated_session.message_count = 0
        updated_session.total_tokens = 0
        updated_session.total_cost = 0.0
        updated_session.session_summary = ""
        updated_session.conversation_data = {}
        updated_session.metadata = {}
        updated_session.created_at = sample_session.created_at
        updated_session.updated_at = datetime.now(timezone.utc)
        updated_session.last_activity = datetime.now(timezone.utc)

        # Return different session on second call (after update)
        mock_session_repository.get_by_session_id.side_effect = [sample_session, updated_session]

        # Act
        result = await session_service.update_session(
            sample_session.session_id,
            request,
            user_id=sample_session.user_id
        )

        # Assert
        assert result.status == "completed"
        mock_session_repository.update_session_status.assert_called_once_with(
            sample_session.session_id, "completed"
        )

    async def test_update_session_not_found(
        self, session_service, mock_session_repository
    ):
        """
        Test update_session for non-existent session.

        GIVEN: A non-existent session_id
        WHEN: update_session is called
        THEN: Raises SessionNotFoundError
        """
        # Arrange
        session_id = SessionTestDataFactory.make_nonexistent_session_id()
        request = SessionUpdateRequest(status="completed")
        mock_session_repository.get_by_session_id.return_value = None

        # Act & Assert
        with pytest.raises(SessionNotFoundError):
            await session_service.update_session(session_id, request)

    async def test_update_session_authorization(
        self, session_service, mock_session_repository, sample_session
    ):
        """
        Test update_session validates user authorization.

        GIVEN: A session belonging to user A
        WHEN: update_session is called with user B's user_id
        THEN: Raises SessionNotFoundError
        """
        # Arrange
        different_user_id = SessionTestDataFactory.make_user_id()
        request = SessionUpdateRequest(status="completed")
        mock_session_repository.get_by_session_id.return_value = sample_session

        # Act & Assert
        with pytest.raises(SessionNotFoundError):
            await session_service.update_session(
                sample_session.session_id,
                request,
                user_id=different_user_id
            )

    async def test_end_session_success(
        self, session_service, mock_session_repository, mock_event_bus, sample_session
    ):
        """
        Test successful session ending.

        GIVEN: An active session
        WHEN: end_session is called
        THEN: Session status is set to "ended" and event is published
        """
        # Arrange
        mock_session_repository.get_by_session_id.return_value = sample_session
        mock_session_repository.update_session_status.return_value = True

        # Create ended session for event data
        ended_session = MagicMock()
        ended_session.message_count = 5
        ended_session.total_tokens = 1000
        ended_session.total_cost = 0.05

        # Return original then ended session
        mock_session_repository.get_by_session_id.side_effect = [sample_session, ended_session]

        # Act
        result = await session_service.end_session(
            sample_session.session_id,
            user_id=sample_session.user_id
        )

        # Assert
        assert result is True
        mock_session_repository.update_session_status.assert_called_once_with(
            sample_session.session_id, "ended"
        )

        # Verify SESSION_ENDED event was published
        mock_event_bus.publish_event.assert_called()
        published_event = mock_event_bus.published_events[-1]
        assert "session_id" in published_event.data

    async def test_end_session_not_found(
        self, session_service, mock_session_repository
    ):
        """
        Test end_session for non-existent session.

        GIVEN: A non-existent session_id
        WHEN: end_session is called
        THEN: Raises SessionNotFoundError
        """
        # Arrange
        session_id = SessionTestDataFactory.make_nonexistent_session_id()
        mock_session_repository.get_by_session_id.return_value = None

        # Act & Assert
        with pytest.raises(SessionNotFoundError):
            await session_service.end_session(session_id)


# ============================================================================
# TEST CLASS 4: Message Operations Tests
# ============================================================================

class TestMessageOperations:
    """
    Test message operations.

    Tests add_message() and get_session_messages() methods.
    """

    async def test_add_message_success(
        self, session_service, mock_session_repository, mock_message_repository,
        mock_event_bus, sample_session, sample_message
    ):
        """
        Test successful message addition.

        GIVEN: An active session
        WHEN: add_message is called
        THEN: Message is created and metrics are updated
        """
        # Arrange
        request_contract = SessionTestDataFactory.make_message_create_request()
        request = MessageCreateRequest(**request_contract.model_dump())

        mock_session_repository.get_by_session_id.return_value = sample_session
        mock_message_repository.create_message.return_value = sample_message
        mock_session_repository.increment_message_count.return_value = True

        # Act
        result = await session_service.add_message(
            sample_session.session_id,
            request,
            user_id=sample_session.user_id
        )

        # Assert
        assert result.message_id == sample_message.message_id
        assert result.session_id == sample_session.session_id
        mock_message_repository.create_message.assert_called_once()
        mock_session_repository.increment_message_count.assert_called_once()

    async def test_add_message_validates_role(
        self, session_service, mock_session_repository, sample_session
    ):
        """
        Test that add_message validates message role.

        GIVEN: A message with invalid role
        WHEN: add_message is called
        THEN: Raises SessionValidationError
        """
        # Arrange
        request = MessageCreateRequest(
            role="invalid_role",
            content="Test content",
            message_type="chat",
            tokens_used=100,
            cost_usd=0.01,
        )
        mock_session_repository.get_by_session_id.return_value = sample_session

        # Act & Assert
        with pytest.raises(SessionValidationError, match="role must be one of"):
            await session_service.add_message(sample_session.session_id, request)

    async def test_add_message_validates_empty_content(
        self, session_service, mock_session_repository, sample_session
    ):
        """
        Test that add_message validates message content.

        GIVEN: A message with empty content
        WHEN: add_message is called
        THEN: Raises SessionValidationError
        """
        # Arrange
        request = MessageCreateRequest(
            role="user",
            content="   ",  # Whitespace only
            message_type="chat",
            tokens_used=100,
            cost_usd=0.01,
        )
        mock_session_repository.get_by_session_id.return_value = sample_session

        # Act & Assert
        with pytest.raises(SessionValidationError, match="content is required"):
            await session_service.add_message(sample_session.session_id, request)

    async def test_add_message_publishes_events(
        self, session_service, mock_session_repository, mock_message_repository,
        mock_event_bus, sample_session, sample_message
    ):
        """
        Test that add_message publishes MESSAGE_SENT and TOKENS_USED events.

        GIVEN: A message with tokens_used > 0
        WHEN: add_message is called
        THEN: Both events are published
        """
        # Arrange
        request_contract = SessionTestDataFactory.make_message_create_request(
            tokens_used=100,
            cost_usd=0.01
        )
        request = MessageCreateRequest(**request_contract.model_dump())

        mock_session_repository.get_by_session_id.return_value = sample_session
        mock_message_repository.create_message.return_value = sample_message
        mock_session_repository.increment_message_count.return_value = True

        # Act
        await session_service.add_message(sample_session.session_id, request)

        # Assert - Both events published
        assert mock_event_bus.publish_event.call_count == 2  # MESSAGE_SENT + TOKENS_USED

    async def test_add_message_no_tokens_event_when_zero(
        self, session_service, mock_session_repository, mock_message_repository,
        mock_event_bus, sample_session, sample_message
    ):
        """
        Test that add_message skips TOKENS_USED event when tokens = 0.

        GIVEN: A message with tokens_used = 0
        WHEN: add_message is called
        THEN: Only MESSAGE_SENT event is published
        """
        # Arrange
        request_contract = SessionTestDataFactory.make_message_create_request(
            tokens_used=0,
            cost_usd=0.0
        )
        request = MessageCreateRequest(**request_contract.model_dump())

        sample_message.tokens_used = 0
        sample_message.cost_usd = 0.0
        mock_session_repository.get_by_session_id.return_value = sample_session
        mock_message_repository.create_message.return_value = sample_message
        mock_session_repository.increment_message_count.return_value = True

        # Act
        await session_service.add_message(sample_session.session_id, request)

        # Assert - Only MESSAGE_SENT event (no TOKENS_USED)
        assert mock_event_bus.publish_event.call_count == 1

    async def test_add_message_session_not_found(
        self, session_service, mock_session_repository
    ):
        """
        Test add_message for non-existent session.

        GIVEN: A non-existent session_id
        WHEN: add_message is called
        THEN: Raises SessionNotFoundError
        """
        # Arrange
        session_id = SessionTestDataFactory.make_nonexistent_session_id()
        request_contract = SessionTestDataFactory.make_message_create_request()
        request = MessageCreateRequest(**request_contract.model_dump())
        mock_session_repository.get_by_session_id.return_value = None

        # Act & Assert
        with pytest.raises(SessionNotFoundError):
            await session_service.add_message(session_id, request)

    async def test_get_session_messages_success(
        self, session_service, mock_session_repository, mock_message_repository,
        sample_session, sample_message
    ):
        """
        Test successful message retrieval.

        GIVEN: A session with messages
        WHEN: get_session_messages is called
        THEN: Returns list of messages
        """
        # Arrange
        mock_session_repository.get_by_session_id.return_value = sample_session
        mock_message_repository.get_session_messages.return_value = [sample_message]

        # Act
        result = await session_service.get_session_messages(
            sample_session.session_id,
            page=1,
            page_size=100,
            user_id=sample_session.user_id
        )

        # Assert
        assert len(result.messages) == 1
        assert result.messages[0].message_id == sample_message.message_id
        assert result.page == 1
        assert result.page_size == 100

    async def test_get_session_messages_empty(
        self, session_service, mock_session_repository, mock_message_repository,
        sample_session
    ):
        """
        Test get_session_messages for session with no messages.

        GIVEN: A session with no messages
        WHEN: get_session_messages is called
        THEN: Returns empty list (not error)
        """
        # Arrange
        mock_session_repository.get_by_session_id.return_value = sample_session
        mock_message_repository.get_session_messages.return_value = []

        # Act
        result = await session_service.get_session_messages(sample_session.session_id)

        # Assert
        assert result.messages == []
        assert result.total == 0


# ============================================================================
# TEST CLASS 5: Session Summary Tests
# ============================================================================

class TestSessionSummary:
    """
    Test session summary operations.

    Tests get_session_summary() method.
    """

    async def test_get_session_summary_success(
        self, session_service, mock_session_repository, sample_session
    ):
        """
        Test successful session summary retrieval.

        GIVEN: An existing session
        WHEN: get_session_summary is called
        THEN: Returns summary with metrics
        """
        # Arrange
        sample_session.message_count = 10
        sample_session.total_tokens = 1500
        sample_session.total_cost = 0.075
        mock_session_repository.get_by_session_id.return_value = sample_session

        # Act
        result = await session_service.get_session_summary(
            sample_session.session_id,
            user_id=sample_session.user_id
        )

        # Assert
        assert result.session_id == sample_session.session_id
        assert result.message_count == 10
        assert result.total_tokens == 1500
        assert result.total_cost == 0.075
        assert result.has_memory is False  # Memory handled by memory_service

    async def test_get_session_summary_not_found(
        self, session_service, mock_session_repository
    ):
        """
        Test get_session_summary for non-existent session.

        GIVEN: A non-existent session_id
        WHEN: get_session_summary is called
        THEN: Raises SessionNotFoundError
        """
        # Arrange
        session_id = SessionTestDataFactory.make_nonexistent_session_id()
        mock_session_repository.get_by_session_id.return_value = None

        # Act & Assert
        with pytest.raises(SessionNotFoundError):
            await session_service.get_session_summary(session_id)


# ============================================================================
# TEST CLASS 6: Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """
    Test error handling and edge cases.

    Verifies that service layer handles errors gracefully.
    """

    async def test_service_handles_repository_errors(
        self, session_service, mock_session_repository
    ):
        """
        Test that service layer converts repository errors to service errors.

        GIVEN: Repository throws unexpected exception
        WHEN: Service method is called
        THEN: Exception is wrapped in SessionServiceError
        """
        # Arrange
        session_id = SessionTestDataFactory.make_session_id()
        mock_session_repository.get_by_session_id.side_effect = Exception("Database connection failed")

        # Act & Assert
        with pytest.raises(SessionServiceError, match="Failed to get session"):
            await session_service.get_session(session_id)

    async def test_event_publishing_failures_dont_block_operations(
        self, session_service, mock_session_repository, mock_account_client,
        mock_event_bus, sample_session
    ):
        """
        Test that event publishing failures don't break core operations.

        GIVEN: Event bus is unavailable
        WHEN: An operation is performed
        THEN: Operation succeeds even if event fails to publish
        """
        # Arrange
        request_contract = SessionTestDataFactory.make_session_create_request()
        request = SessionCreateRequest(**request_contract.model_dump())

        mock_account_client.get_account_profile.return_value = {"user_id": request.user_id}
        mock_session_repository.create_session.return_value = sample_session

        # Mock event bus failure
        mock_event_bus.publish_event.side_effect = Exception("NATS unavailable")

        # Act - Should not raise exception
        result = await session_service.create_session(request)

        # Assert - Operation succeeded despite event failure
        assert result is not None
        assert result.status == "active"

    async def test_service_without_event_bus(
        self, mock_session_repository, mock_message_repository, mock_account_client, sample_session
    ):
        """
        Test that service works without event bus.

        GIVEN: Service initialized without event_bus
        WHEN: Operations are performed
        THEN: Operations succeed, no event publishing
        """
        # Arrange - Service without event bus
        service = SessionService(
            session_repo=mock_session_repository,
            message_repo=mock_message_repository,
            event_bus=None,  # No event bus
            account_client=mock_account_client,
        )

        request_contract = SessionTestDataFactory.make_session_create_request()
        request = SessionCreateRequest(**request_contract.model_dump())

        mock_account_client.get_account_profile.return_value = {"user_id": request.user_id}
        mock_session_repository.create_session.return_value = sample_session

        # Act - Should not raise exception
        result = await service.create_session(request)

        # Assert
        assert result is not None
        assert result.status == "active"


# ============================================================================
# TEST CLASS 7: Health Check Tests
# ============================================================================

class TestHealthCheck:
    """
    Test service health check.

    Tests health_check() method.
    """

    async def test_health_check_success(self, session_service):
        """
        Test successful health check.

        GIVEN: Service is running
        WHEN: health_check is called
        THEN: Returns healthy status
        """
        # Act
        result = await session_service.health_check()

        # Assert
        assert result["status"] == "healthy"
        assert result["service"] == "session_service"
        assert "timestamp" in result


# ============================================================================
# SUMMARY
# ============================================================================
"""
SESSION SERVICE INTEGRATION TESTS SUMMARY:

Test Coverage (25 tests total):

1. Session Creation (5 tests):
   - Creates new session
   - Creates with custom session_id
   - Validates empty user_id
   - Handles account service unavailable (fail-open)
   - Publishes SESSION_STARTED event

2. Session Retrieval (6 tests):
   - Get session success
   - Get session not found
   - Get session authorization check
   - Get user sessions success
   - Get user sessions empty
   - Get user sessions active_only filter

3. Session Update (4 tests):
   - Update session status
   - Update session not found
   - Update session authorization
   - End session success

4. Message Operations (7 tests):
   - Add message success
   - Add message validates role
   - Add message validates empty content
   - Add message publishes events
   - Add message skips tokens event when zero
   - Add message session not found
   - Get session messages success/empty

5. Session Summary (2 tests):
   - Get summary success
   - Get summary not found

6. Error Handling (3 tests):
   - Handles repository errors
   - Event failures don't block operations
   - Works without event bus

7. Health Check (1 test):
   - Health check success

Key Features:
- Uses SessionTestDataFactory from data contracts (no hardcoded data)
- Mocks repository and event bus (no I/O dependencies)
- Tests business logic layer only
- Verifies event publishing patterns
- Comprehensive error handling coverage
- 100% service method coverage

Run with:
    pytest tests/integration/golden/session_service/test_session_integration.py -v
"""
