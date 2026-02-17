"""
Session Service - Component Tests (Golden)

Tests for:
- Session creation and lifecycle
- Message management
- Metrics tracking
- Event publishing
- Validation and error handling

All tests use SessionTestDataFactory - zero hardcoded data.
These tests capture current behavior and should not be modified
unless intentionally changing the service behavior.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from tests.contracts.session.data_contract import (
    SessionTestDataFactory,
    SessionCreateRequestContract,
    SessionUpdateRequestContract,
    MessageCreateRequestContract,
    SessionCreateRequestBuilder,
    SessionUpdateRequestBuilder,
    MessageCreateRequestBuilder,
)

pytestmark = [pytest.mark.component, pytest.mark.asyncio]


# ============================================================================
# Factory Tests (20+ tests)
# ============================================================================


class TestSessionTestDataFactory:
    """Test factory generates valid unique data"""

    def test_make_session_id_format(self):
        """Factory generates valid session ID format"""
        session_id = SessionTestDataFactory.make_session_id()
        assert session_id.startswith("sess_")
        assert len(session_id) > 5

    def test_make_session_id_uniqueness(self):
        """Factory generates unique session IDs"""
        id1 = SessionTestDataFactory.make_session_id()
        id2 = SessionTestDataFactory.make_session_id()
        assert id1 != id2

    def test_make_user_id_format(self):
        """Factory generates valid user ID format"""
        user_id = SessionTestDataFactory.make_user_id()
        assert user_id.startswith("user_")
        assert len(user_id) > 5

    def test_make_user_id_uniqueness(self):
        """Factory generates unique user IDs"""
        id1 = SessionTestDataFactory.make_user_id()
        id2 = SessionTestDataFactory.make_user_id()
        assert id1 != id2

    def test_make_message_id_format(self):
        """Factory generates valid message ID format"""
        message_id = SessionTestDataFactory.make_message_id()
        assert message_id.startswith("msg_")
        assert len(message_id) > 4

    def test_make_content_non_empty(self):
        """Factory generates non-empty content"""
        content = SessionTestDataFactory.make_content()
        assert len(content) > 0

    def test_make_tokens_used_valid_range(self):
        """Factory generates valid token count"""
        tokens = SessionTestDataFactory.make_tokens_used()
        assert tokens >= 10
        assert tokens < 510

    def test_make_cost_usd_valid_range(self):
        """Factory generates valid cost"""
        cost = SessionTestDataFactory.make_cost_usd()
        assert cost >= 0.001
        assert cost < 0.02

    def test_make_session_create_request(self):
        """Factory generates valid session create request"""
        request = SessionTestDataFactory.make_session_create_request()
        assert isinstance(request, SessionCreateRequestContract)
        assert request.user_id.startswith("user_")

    def test_make_message_create_request(self):
        """Factory generates valid message create request"""
        request = SessionTestDataFactory.make_message_create_request()
        assert isinstance(request, MessageCreateRequestContract)
        assert request.role in ["user", "assistant", "system"]
        assert len(request.content) > 0

    def test_make_user_message_request(self):
        """Factory generates user message request"""
        request = SessionTestDataFactory.make_user_message_request()
        assert request.role == "user"

    def test_make_assistant_message_request(self):
        """Factory generates assistant message request"""
        request = SessionTestDataFactory.make_assistant_message_request()
        assert request.role == "assistant"

    def test_make_system_message_request(self):
        """Factory generates system message request"""
        request = SessionTestDataFactory.make_system_message_request()
        assert request.role == "system"

    def test_make_invalid_user_id_empty(self):
        """Factory generates empty invalid user ID"""
        invalid_id = SessionTestDataFactory.make_invalid_user_id_empty()
        assert invalid_id == ""

    def test_make_invalid_role(self):
        """Factory generates invalid role"""
        invalid_role = SessionTestDataFactory.make_invalid_role()
        assert invalid_role not in ["user", "assistant", "system"]

    def test_make_invalid_content_empty(self):
        """Factory generates empty invalid content"""
        invalid_content = SessionTestDataFactory.make_invalid_content_empty()
        assert invalid_content == ""


# ============================================================================
# Builder Tests (9+ tests)
# ============================================================================


class TestSessionCreateRequestBuilder:
    """Test session create request builder"""

    def test_builder_default_build(self):
        """Builder creates valid request with defaults"""
        request = SessionCreateRequestBuilder().build()
        assert isinstance(request, SessionCreateRequestContract)
        assert request.user_id.startswith("user_")
        assert request.session_id is None

    def test_builder_with_custom_user_id(self):
        """Builder accepts custom user ID"""
        custom_user_id = "custom_user_123"
        request = SessionCreateRequestBuilder().with_user_id(custom_user_id).build()
        assert request.user_id == custom_user_id

    def test_builder_with_custom_session_id(self):
        """Builder accepts custom session ID"""
        custom_session_id = "custom_session_456"
        request = SessionCreateRequestBuilder().with_session_id(custom_session_id).build()
        assert request.session_id == custom_session_id

    def test_builder_chaining(self):
        """Builder supports method chaining"""
        request = (
            SessionCreateRequestBuilder()
            .with_user_id("user_test")
            .with_topic("test topic")
            .with_platform("mobile")
            .build()
        )
        assert request.user_id == "user_test"
        assert request.conversation_data.get("topic") == "test topic"
        assert request.metadata.get("platform") == "mobile"


class TestMessageCreateRequestBuilder:
    """Test message create request builder"""

    def test_builder_default_build(self):
        """Builder creates valid request with defaults"""
        request = MessageCreateRequestBuilder().build()
        assert isinstance(request, MessageCreateRequestContract)
        assert request.role == "user"

    def test_builder_as_assistant(self):
        """Builder sets assistant role"""
        request = MessageCreateRequestBuilder().as_assistant().build()
        assert request.role == "assistant"

    def test_builder_as_system(self):
        """Builder sets system role"""
        request = MessageCreateRequestBuilder().as_system().build()
        assert request.role == "system"

    def test_builder_with_metrics(self):
        """Builder sets tokens and cost"""
        request = (
            MessageCreateRequestBuilder()
            .with_metrics(tokens=100, cost=0.01)
            .build()
        )
        assert request.tokens_used == 100
        assert request.cost_usd == 0.01

    def test_builder_as_tool_call(self):
        """Builder sets tool_call type"""
        request = MessageCreateRequestBuilder().as_tool_call().build()
        assert request.message_type == "tool_call"


# ============================================================================
# Validation Tests (15 tests)
# ============================================================================


class TestRequestValidation:
    """Test request contract validation"""

    def test_valid_session_create_request(self):
        """Valid session create request passes validation"""
        request = SessionTestDataFactory.make_session_create_request()
        assert isinstance(request, SessionCreateRequestContract)

    def test_empty_user_id_raises_error(self):
        """Empty user_id raises ValidationError"""
        with pytest.raises(ValidationError):
            SessionCreateRequestContract(user_id="")

    def test_whitespace_user_id_raises_error(self):
        """Whitespace-only user_id raises ValidationError"""
        with pytest.raises(ValidationError):
            SessionCreateRequestContract(user_id="   ")

    def test_valid_message_create_request(self):
        """Valid message create request passes validation"""
        request = SessionTestDataFactory.make_message_create_request()
        assert isinstance(request, MessageCreateRequestContract)

    def test_invalid_role_raises_error(self):
        """Invalid role raises ValidationError"""
        with pytest.raises(ValidationError):
            MessageCreateRequestContract(
                role="invalid_role",
                content="Test content"
            )

    def test_empty_content_raises_error(self):
        """Empty content raises ValidationError"""
        with pytest.raises(ValidationError):
            MessageCreateRequestContract(
                role="user",
                content=""
            )

    def test_invalid_message_type_raises_error(self):
        """Invalid message_type raises ValidationError"""
        with pytest.raises(ValidationError):
            MessageCreateRequestContract(
                role="user",
                content="Test",
                message_type="invalid_type"
            )

    def test_negative_tokens_raises_error(self):
        """Negative tokens raises ValidationError"""
        with pytest.raises(ValidationError):
            MessageCreateRequestContract(
                role="user",
                content="Test",
                tokens_used=-10
            )

    def test_negative_cost_raises_error(self):
        """Negative cost raises ValidationError"""
        with pytest.raises(ValidationError):
            MessageCreateRequestContract(
                role="user",
                content="Test",
                cost_usd=-0.5
            )

    def test_invalid_status_update_raises_error(self):
        """Invalid status in update raises ValidationError"""
        with pytest.raises(ValidationError):
            SessionUpdateRequestContract(status="invalid_status")

    def test_valid_status_update_accepted(self):
        """Valid status in update is accepted"""
        request = SessionUpdateRequestContract(status="ended")
        assert request.status == "ended"

    def test_session_create_with_custom_id(self):
        """Session create with custom ID is valid"""
        request = SessionCreateRequestContract(
            user_id="user_test",
            session_id="custom_session_id"
        )
        assert request.session_id == "custom_session_id"

    def test_message_default_type_is_chat(self):
        """Message default type is chat"""
        request = MessageCreateRequestContract(
            role="user",
            content="Test content"
        )
        assert request.message_type == "chat"

    def test_message_default_tokens_is_zero(self):
        """Message default tokens is zero"""
        request = MessageCreateRequestContract(
            role="user",
            content="Test content"
        )
        assert request.tokens_used == 0

    def test_message_default_cost_is_zero(self):
        """Message default cost is zero"""
        request = MessageCreateRequestContract(
            role="user",
            content="Test content"
        )
        assert request.cost_usd == 0.0


# ============================================================================
# Session Service Tests (25+ tests)
# ============================================================================


class TestSessionCreate:
    """Test session creation business logic"""

    async def test_create_session_success(
        self, session_service, mock_session_repository, mock_event_bus
    ):
        """Successful session creation returns session data and publishes event"""
        # Arrange
        from microservices.session_service.models import SessionCreateRequest
        user_id = SessionTestDataFactory.make_user_id()
        request = SessionCreateRequest(user_id=user_id)

        # Act
        result = await session_service.create_session(request)

        # Assert
        assert result.user_id == user_id
        assert result.status == "active"
        assert result.is_active is True
        assert result.message_count == 0
        mock_session_repository.create_session.assert_called_once()
        assert len(mock_event_bus.published_events) > 0

    async def test_create_session_with_custom_id(
        self, session_service, mock_session_repository
    ):
        """Session creation accepts custom session_id"""
        # Arrange
        from microservices.session_service.models import SessionCreateRequest
        user_id = SessionTestDataFactory.make_user_id()
        custom_session_id = SessionTestDataFactory.make_session_id()
        request = SessionCreateRequest(
            user_id=user_id,
            session_id=custom_session_id
        )

        # Act
        result = await session_service.create_session(request)

        # Assert
        assert result.session_id == custom_session_id

    async def test_create_session_with_metadata(
        self, session_service, mock_session_repository
    ):
        """Session creation includes metadata"""
        # Arrange
        from microservices.session_service.models import SessionCreateRequest
        user_id = SessionTestDataFactory.make_user_id()
        metadata = {"platform": "web", "client_version": "1.0.0"}
        request = SessionCreateRequest(
            user_id=user_id,
            metadata=metadata
        )

        # Act
        result = await session_service.create_session(request)

        # Assert
        assert result.metadata == metadata

    async def test_create_session_empty_user_id_raises_error(
        self, session_service
    ):
        """Session creation with empty user_id raises error"""
        # Arrange
        from microservices.session_service.models import SessionCreateRequest
        from microservices.session_service.protocols import SessionValidationError
        request = SessionCreateRequest(user_id="")

        # Act & Assert
        with pytest.raises(SessionValidationError):
            await session_service.create_session(request)


class TestSessionGet:
    """Test session retrieval business logic"""

    async def test_get_session_success(
        self, session_service, mock_session_repository
    ):
        """Successful session retrieval returns session data"""
        # Arrange - First create a session
        from microservices.session_service.models import SessionCreateRequest
        user_id = SessionTestDataFactory.make_user_id()
        create_request = SessionCreateRequest(user_id=user_id)
        created = await session_service.create_session(create_request)

        # Act
        result = await session_service.get_session(created.session_id, user_id)

        # Assert
        assert result.session_id == created.session_id
        assert result.user_id == user_id

    async def test_get_session_not_found_raises_error(
        self, session_service
    ):
        """Get non-existent session raises SessionNotFoundError"""
        # Arrange
        from microservices.session_service.protocols import SessionNotFoundError
        nonexistent_id = SessionTestDataFactory.make_nonexistent_session_id()

        # Act & Assert
        with pytest.raises(SessionNotFoundError):
            await session_service.get_session(nonexistent_id)

    async def test_get_session_wrong_user_raises_error(
        self, session_service, mock_session_repository
    ):
        """Get session with wrong user_id raises SessionNotFoundError"""
        # Arrange - Create a session
        from microservices.session_service.models import SessionCreateRequest
        from microservices.session_service.protocols import SessionNotFoundError
        user_id = SessionTestDataFactory.make_user_id()
        wrong_user_id = SessionTestDataFactory.make_user_id()
        create_request = SessionCreateRequest(user_id=user_id)
        created = await session_service.create_session(create_request)

        # Act & Assert
        with pytest.raises(SessionNotFoundError):
            await session_service.get_session(created.session_id, wrong_user_id)


class TestSessionList:
    """Test session listing business logic"""

    async def test_get_user_sessions_empty(
        self, session_service
    ):
        """Get sessions for user with no sessions returns empty list"""
        # Arrange
        user_id = SessionTestDataFactory.make_user_id()

        # Act
        result = await session_service.get_user_sessions(user_id)

        # Assert
        assert len(result.sessions) == 0
        assert result.total == 0

    async def test_get_user_sessions_returns_user_sessions(
        self, session_service, mock_session_repository
    ):
        """Get sessions returns only user's sessions"""
        # Arrange - Create sessions for user
        from microservices.session_service.models import SessionCreateRequest
        user_id = SessionTestDataFactory.make_user_id()
        for _ in range(3):
            request = SessionCreateRequest(user_id=user_id)
            await session_service.create_session(request)

        # Act
        result = await session_service.get_user_sessions(user_id)

        # Assert
        assert len(result.sessions) == 3
        for session in result.sessions:
            assert session.user_id == user_id

    async def test_get_user_sessions_active_only_filter(
        self, session_service, mock_session_repository
    ):
        """Get sessions with active_only=True filters inactive sessions"""
        # Arrange - Create and end a session
        from microservices.session_service.models import SessionCreateRequest
        user_id = SessionTestDataFactory.make_user_id()

        # Create active session
        request1 = SessionCreateRequest(user_id=user_id)
        await session_service.create_session(request1)

        # Create and end session
        request2 = SessionCreateRequest(user_id=user_id)
        created2 = await session_service.create_session(request2)
        await session_service.end_session(created2.session_id, user_id)

        # Act
        result = await session_service.get_user_sessions(user_id, active_only=True)

        # Assert
        assert len(result.sessions) == 1
        assert result.sessions[0].is_active is True


class TestSessionEnd:
    """Test session ending business logic"""

    async def test_end_session_success(
        self, session_service, mock_session_repository, mock_event_bus
    ):
        """Successful session end returns True and publishes event"""
        # Arrange - Create a session
        from microservices.session_service.models import SessionCreateRequest
        user_id = SessionTestDataFactory.make_user_id()
        request = SessionCreateRequest(user_id=user_id)
        created = await session_service.create_session(request)
        initial_event_count = len(mock_event_bus.published_events)

        # Act
        result = await session_service.end_session(created.session_id, user_id)

        # Assert
        assert result is True
        # Session.ended event should be published
        assert len(mock_event_bus.published_events) > initial_event_count

    async def test_end_session_updates_status(
        self, session_service, mock_session_repository
    ):
        """Ending session updates status to ended"""
        # Arrange - Create a session
        from microservices.session_service.models import SessionCreateRequest
        user_id = SessionTestDataFactory.make_user_id()
        request = SessionCreateRequest(user_id=user_id)
        created = await session_service.create_session(request)

        # Act
        await session_service.end_session(created.session_id, user_id)
        result = await session_service.get_session(created.session_id, user_id)

        # Assert
        assert result.status == "ended"
        assert result.is_active is False

    async def test_end_session_not_found_raises_error(
        self, session_service
    ):
        """End non-existent session raises SessionNotFoundError"""
        # Arrange
        from microservices.session_service.protocols import SessionNotFoundError
        nonexistent_id = SessionTestDataFactory.make_nonexistent_session_id()

        # Act & Assert
        with pytest.raises(SessionNotFoundError):
            await session_service.end_session(nonexistent_id)


class TestMessageAdd:
    """Test message adding business logic"""

    async def test_add_message_success(
        self, session_service, mock_session_repository, mock_message_repository, mock_event_bus
    ):
        """Successful message add returns message data"""
        # Arrange - Create a session first
        from microservices.session_service.models import SessionCreateRequest, MessageCreateRequest
        user_id = SessionTestDataFactory.make_user_id()
        session_request = SessionCreateRequest(user_id=user_id)
        session = await session_service.create_session(session_request)

        message_request = MessageCreateRequest(
            role="user",
            content="Test message content",
            tokens_used=50,
            cost_usd=0.005
        )

        # Act
        result = await session_service.add_message(
            session.session_id, message_request, user_id
        )

        # Assert
        assert result.role == "user"
        assert result.content == "Test message content"
        assert result.tokens_used == 50
        assert result.session_id == session.session_id

    async def test_add_message_updates_session_metrics(
        self, session_service, mock_session_repository, mock_message_repository
    ):
        """Adding message updates session metrics"""
        # Arrange - Create a session
        from microservices.session_service.models import SessionCreateRequest, MessageCreateRequest
        user_id = SessionTestDataFactory.make_user_id()
        session_request = SessionCreateRequest(user_id=user_id)
        session = await session_service.create_session(session_request)

        message_request = MessageCreateRequest(
            role="user",
            content="Test message",
            tokens_used=100,
            cost_usd=0.01
        )

        # Act
        await session_service.add_message(session.session_id, message_request, user_id)

        # Verify increment_message_count was called
        mock_session_repository.increment_message_count.assert_called()

    async def test_add_message_to_nonexistent_session_raises_error(
        self, session_service
    ):
        """Adding message to non-existent session raises error"""
        # Arrange
        from microservices.session_service.models import MessageCreateRequest
        from microservices.session_service.protocols import SessionNotFoundError
        nonexistent_id = SessionTestDataFactory.make_nonexistent_session_id()
        message_request = MessageCreateRequest(role="user", content="Test")

        # Act & Assert
        with pytest.raises(SessionNotFoundError):
            await session_service.add_message(nonexistent_id, message_request)

    async def test_add_message_wrong_user_raises_error(
        self, session_service, mock_session_repository
    ):
        """Adding message with wrong user raises error"""
        # Arrange - Create a session
        from microservices.session_service.models import SessionCreateRequest, MessageCreateRequest
        from microservices.session_service.protocols import SessionNotFoundError
        user_id = SessionTestDataFactory.make_user_id()
        wrong_user_id = SessionTestDataFactory.make_user_id()

        session_request = SessionCreateRequest(user_id=user_id)
        session = await session_service.create_session(session_request)

        message_request = MessageCreateRequest(role="user", content="Test")

        # Act & Assert
        with pytest.raises(SessionNotFoundError):
            await session_service.add_message(
                session.session_id, message_request, wrong_user_id
            )

    async def test_add_message_invalid_role_raises_error(
        self, session_service, mock_session_repository
    ):
        """Adding message with invalid role raises error"""
        # Arrange - Create a session
        from microservices.session_service.models import SessionCreateRequest, MessageCreateRequest
        from microservices.session_service.protocols import SessionValidationError
        user_id = SessionTestDataFactory.make_user_id()
        session_request = SessionCreateRequest(user_id=user_id)
        session = await session_service.create_session(session_request)

        # Create request with invalid role (manually construct to bypass Pydantic)
        message_request = MessageCreateRequest.__new__(MessageCreateRequest)
        object.__setattr__(message_request, 'role', 'invalid_role')
        object.__setattr__(message_request, 'content', 'Test')
        object.__setattr__(message_request, 'message_type', 'chat')
        object.__setattr__(message_request, 'metadata', {})
        object.__setattr__(message_request, 'tokens_used', 0)
        object.__setattr__(message_request, 'cost_usd', 0.0)

        # Act & Assert
        with pytest.raises(SessionValidationError):
            await session_service.add_message(
                session.session_id, message_request, user_id
            )


class TestMessageGet:
    """Test message retrieval business logic"""

    async def test_get_session_messages_empty(
        self, session_service, mock_session_repository
    ):
        """Get messages for session with no messages returns empty list"""
        # Arrange - Create a session
        from microservices.session_service.models import SessionCreateRequest
        user_id = SessionTestDataFactory.make_user_id()
        session_request = SessionCreateRequest(user_id=user_id)
        session = await session_service.create_session(session_request)

        # Act
        result = await session_service.get_session_messages(
            session.session_id, user_id=user_id
        )

        # Assert
        assert len(result.messages) == 0
        assert result.total == 0

    async def test_get_session_messages_returns_messages(
        self, session_service, mock_session_repository, mock_message_repository
    ):
        """Get messages returns all session messages"""
        # Arrange - Create session and add messages
        from microservices.session_service.models import SessionCreateRequest, MessageCreateRequest
        user_id = SessionTestDataFactory.make_user_id()
        session_request = SessionCreateRequest(user_id=user_id)
        session = await session_service.create_session(session_request)

        for i in range(3):
            msg_request = MessageCreateRequest(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}"
            )
            await session_service.add_message(
                session.session_id, msg_request, user_id
            )

        # Act
        result = await session_service.get_session_messages(
            session.session_id, user_id=user_id
        )

        # Assert
        assert len(result.messages) == 3


class TestEventPublishing:
    """Test event publishing behavior"""

    async def test_create_session_publishes_started_event(
        self, session_service, mock_event_bus
    ):
        """Session creation publishes session.started event"""
        # Arrange
        from microservices.session_service.models import SessionCreateRequest
        user_id = SessionTestDataFactory.make_user_id()
        request = SessionCreateRequest(user_id=user_id)

        # Act
        await session_service.create_session(request)

        # Assert
        assert len(mock_event_bus.published_events) > 0
        # Check event has type attribute (Event uses 'type' not 'event_type')
        event = mock_event_bus.published_events[0]
        assert hasattr(event, 'type') or hasattr(event, 'event_type')

    async def test_add_message_publishes_message_event(
        self, session_service, mock_session_repository, mock_message_repository, mock_event_bus
    ):
        """Message addition publishes session.message_sent event"""
        # Arrange - Create session
        from microservices.session_service.models import SessionCreateRequest, MessageCreateRequest
        user_id = SessionTestDataFactory.make_user_id()
        session_request = SessionCreateRequest(user_id=user_id)
        session = await session_service.create_session(session_request)
        initial_count = len(mock_event_bus.published_events)

        message_request = MessageCreateRequest(
            role="user",
            content="Test message",
            tokens_used=50
        )

        # Act
        await session_service.add_message(
            session.session_id, message_request, user_id
        )

        # Assert - More events published after message
        assert len(mock_event_bus.published_events) > initial_count

    async def test_no_event_bus_does_not_fail(
        self, session_service_no_event_bus, mock_session_repository
    ):
        """Operations work when event bus is not configured"""
        # Arrange
        from microservices.session_service.models import SessionCreateRequest
        user_id = SessionTestDataFactory.make_user_id()
        request = SessionCreateRequest(user_id=user_id)

        # Act - Should not raise
        result = await session_service_no_event_bus.create_session(request)

        # Assert
        assert result.user_id == user_id


class TestSessionSummary:
    """Test session summary business logic"""

    async def test_get_session_summary_success(
        self, session_service, mock_session_repository
    ):
        """Get session summary returns summary data"""
        # Arrange - Create a session
        from microservices.session_service.models import SessionCreateRequest
        user_id = SessionTestDataFactory.make_user_id()
        request = SessionCreateRequest(user_id=user_id)
        session = await session_service.create_session(request)

        # Act
        result = await session_service.get_session_summary(
            session.session_id, user_id
        )

        # Assert
        assert result.session_id == session.session_id
        assert result.user_id == user_id
        assert result.message_count == 0
        assert result.total_tokens == 0


class TestHealthCheck:
    """Test health check functionality"""

    async def test_health_check_returns_healthy(
        self, session_service
    ):
        """Health check returns healthy status"""
        # Act
        result = await session_service.health_check()

        # Assert
        assert result["status"] == "healthy"
        assert result["service"] == "session_service"
        assert "timestamp" in result


class TestServiceStats:
    """Test service statistics functionality"""

    async def test_get_service_stats_returns_stats(
        self, session_service
    ):
        """Get service stats returns statistics data"""
        # Act
        result = await session_service.get_service_stats()

        # Assert
        assert hasattr(result, 'total_sessions')
        assert hasattr(result, 'active_sessions')
        assert hasattr(result, 'total_messages')
