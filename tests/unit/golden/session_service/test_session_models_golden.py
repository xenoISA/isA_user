"""
Unit Golden Tests: Session Service Models

Tests model validation and serialization without external dependencies.
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.session_service.models import (
    SessionStatus,
    MessageType,
    Session,
    SessionMessage,
    SessionMemory,
    SessionCreateRequest,
    SessionUpdateRequest,
    MessageCreateRequest,
    MemoryCreateRequest,
    MemoryUpdateRequest,
    SessionResponse,
    SessionListResponse,
    MessageResponse,
    MessageListResponse,
    MemoryResponse,
    SessionSummaryResponse,
    SessionStatsResponse,
    SessionServiceStatus,
    ErrorResponse,
)


class TestSessionStatus:
    """Test SessionStatus enum"""

    def test_session_status_values(self):
        """Test all session status values are defined"""
        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.COMPLETED.value == "completed"
        assert SessionStatus.ARCHIVED.value == "archived"
        assert SessionStatus.ENDED.value == "ended"

    def test_session_status_comparison(self):
        """Test session status comparison"""
        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.ACTIVE != SessionStatus.COMPLETED
        assert SessionStatus.ENDED != SessionStatus.ARCHIVED


class TestMessageType:
    """Test MessageType enum"""

    def test_message_type_values(self):
        """Test all message type values are defined"""
        assert MessageType.CHAT.value == "chat"
        assert MessageType.SYSTEM.value == "system"
        assert MessageType.TOOL_CALL.value == "tool_call"
        assert MessageType.TOOL_RESULT.value == "tool_result"
        assert MessageType.NOTIFICATION.value == "notification"

    def test_message_type_comparison(self):
        """Test message type comparison"""
        assert MessageType.CHAT.value == "chat"
        assert MessageType.CHAT != MessageType.SYSTEM
        assert MessageType.TOOL_CALL != MessageType.TOOL_RESULT


class TestSessionModel:
    """Test Session model validation"""

    def test_session_creation_with_all_fields(self):
        """Test creating session with all fields"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=24)

        session = Session(
            session_id="sess_123",
            user_id="user_456",
            conversation_data={"context": "test", "history": []},
            status="active",
            metadata={"source": "web", "device": "desktop"},
            is_active=True,
            message_count=5,
            total_tokens=1500,
            total_cost=0.05,
            session_summary="Test session summary",
            created_at=now,
            updated_at=now,
            last_activity=now,
            expires_at=future,
        )

        assert session.session_id == "sess_123"
        assert session.user_id == "user_456"
        assert session.conversation_data == {"context": "test", "history": []}
        assert session.status == "active"
        assert session.metadata == {"source": "web", "device": "desktop"}
        assert session.is_active is True
        assert session.message_count == 5
        assert session.total_tokens == 1500
        assert session.total_cost == 0.05
        assert session.session_summary == "Test session summary"
        assert session.created_at == now
        assert session.updated_at == now
        assert session.last_activity == now
        assert session.expires_at == future

    def test_session_with_minimal_fields(self):
        """Test creating session with only required fields"""
        session = Session(
            session_id="sess_minimal",
            user_id="user_123",
        )

        assert session.session_id == "sess_minimal"
        assert session.user_id == "user_123"
        assert session.conversation_data == {}
        assert session.status == "active"
        assert session.metadata == {}
        assert session.is_active is True
        assert session.message_count == 0
        assert session.total_tokens == 0
        assert session.total_cost == 0.0
        assert session.session_summary == ""

    def test_session_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            Session()

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "session_id" in missing_fields
        assert "user_id" in missing_fields

    def test_session_default_conversation_data(self):
        """Test session default conversation_data is empty dict"""
        session = Session(session_id="sess_test", user_id="user_123")
        assert session.conversation_data == {}
        assert isinstance(session.conversation_data, dict)

    def test_session_default_metadata(self):
        """Test session default metadata is empty dict"""
        session = Session(session_id="sess_test", user_id="user_123")
        assert session.metadata == {}
        assert isinstance(session.metadata, dict)


class TestSessionMessageModel:
    """Test SessionMessage model validation"""

    def test_session_message_creation_with_all_fields(self):
        """Test creating session message with all fields"""
        now = datetime.now(timezone.utc)

        message = SessionMessage(
            message_id="msg_123",
            session_id="sess_456",
            user_id="user_789",
            role="user",
            content="Hello, how can I help you?",
            message_type="chat",
            metadata={"sentiment": "positive", "language": "en"},
            tokens_used=15,
            cost_usd=0.001,
            created_at=now,
        )

        assert message.message_id == "msg_123"
        assert message.session_id == "sess_456"
        assert message.user_id == "user_789"
        assert message.role == "user"
        assert message.content == "Hello, how can I help you?"
        assert message.message_type == "chat"
        assert message.metadata == {"sentiment": "positive", "language": "en"}
        assert message.tokens_used == 15
        assert message.cost_usd == 0.001
        assert message.created_at == now

    def test_session_message_with_minimal_fields(self):
        """Test creating session message with only required fields"""
        message = SessionMessage(
            session_id="sess_123",
            user_id="user_456",
            role="assistant",
            content="I can help with that.",
        )

        assert message.message_id is None
        assert message.session_id == "sess_123"
        assert message.user_id == "user_456"
        assert message.role == "assistant"
        assert message.content == "I can help with that."
        assert message.message_type == "chat"
        assert message.metadata == {}
        assert message.tokens_used == 0
        assert message.cost_usd == 0.0

    def test_session_message_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            SessionMessage(role="user", content="Test")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "session_id" in missing_fields
        assert "user_id" in missing_fields

    def test_session_message_system_type(self):
        """Test session message with system type"""
        message = SessionMessage(
            session_id="sess_123",
            user_id="user_456",
            role="system",
            content="Session started",
            message_type="system",
        )

        assert message.role == "system"
        assert message.message_type == "system"

    def test_session_message_tool_call_type(self):
        """Test session message with tool_call type"""
        message = SessionMessage(
            session_id="sess_123",
            user_id="user_456",
            role="assistant",
            content="Calling weather API",
            message_type="tool_call",
            metadata={"tool": "weather_api", "params": {"city": "SF"}},
        )

        assert message.message_type == "tool_call"
        assert message.metadata["tool"] == "weather_api"


class TestSessionMemoryModel:
    """Test SessionMemory model validation"""

    def test_session_memory_creation_with_all_fields(self):
        """Test creating session memory with all fields"""
        now = datetime.now(timezone.utc)

        memory = SessionMemory(
            memory_id="mem_123",
            session_id="sess_456",
            user_id="user_789",
            memory_type="context",
            content="User prefers concise responses",
            metadata={"priority": "high", "category": "preference"},
            created_at=now,
        )

        assert memory.memory_id == "mem_123"
        assert memory.session_id == "sess_456"
        assert memory.user_id == "user_789"
        assert memory.memory_type == "context"
        assert memory.content == "User prefers concise responses"
        assert memory.metadata == {"priority": "high", "category": "preference"}
        assert memory.created_at == now

    def test_session_memory_with_minimal_fields(self):
        """Test creating session memory with only required fields"""
        memory = SessionMemory(
            session_id="sess_123",
            user_id="user_456",
            memory_type="fact",
            content="User is from California",
        )

        assert memory.memory_id is None
        assert memory.session_id == "sess_123"
        assert memory.user_id == "user_456"
        assert memory.memory_type == "fact"
        assert memory.content == "User is from California"
        assert memory.metadata == {}

    def test_session_memory_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            SessionMemory(user_id="user_123", content="Test content")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "session_id" in missing_fields
        assert "memory_type" in missing_fields

    def test_session_memory_different_types(self):
        """Test session memory with different memory types"""
        memory_types = ["context", "fact", "preference", "history", "summary"]

        for mem_type in memory_types:
            memory = SessionMemory(
                session_id="sess_123",
                user_id="user_456",
                memory_type=mem_type,
                content=f"Test {mem_type} content",
            )
            assert memory.memory_type == mem_type


class TestSessionCreateRequest:
    """Test SessionCreateRequest model validation"""

    def test_session_create_request_valid(self):
        """Test valid session creation request"""
        request = SessionCreateRequest(
            user_id="user_123",
            session_id="sess_custom_123",
            conversation_data={"initial_context": "test"},
            metadata={"source": "mobile_app"},
        )

        assert request.user_id == "user_123"
        assert request.session_id == "sess_custom_123"
        assert request.conversation_data == {"initial_context": "test"}
        assert request.metadata == {"source": "mobile_app"}

    def test_session_create_request_minimal(self):
        """Test minimal session creation request"""
        request = SessionCreateRequest(user_id="user_123")

        assert request.user_id == "user_123"
        assert request.session_id is None
        assert request.conversation_data == {}
        assert request.metadata == {}

    def test_session_create_request_missing_user_id(self):
        """Test that missing user_id raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            SessionCreateRequest()

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "user_id" in missing_fields


class TestSessionUpdateRequest:
    """Test SessionUpdateRequest model validation"""

    def test_session_update_request_partial(self):
        """Test partial update request"""
        request = SessionUpdateRequest(
            status="completed",
            conversation_data={"updated": True},
        )

        assert request.status == "completed"
        assert request.conversation_data == {"updated": True}
        assert request.metadata is None

    def test_session_update_request_all_fields(self):
        """Test update request with all fields"""
        request = SessionUpdateRequest(
            status="archived",
            conversation_data={"final_state": "archived"},
            metadata={"archived_reason": "user_request"},
        )

        assert request.status == "archived"
        assert request.conversation_data == {"final_state": "archived"}
        assert request.metadata == {"archived_reason": "user_request"}

    def test_session_update_request_empty(self):
        """Test empty update request is valid"""
        request = SessionUpdateRequest()

        assert request.status is None
        assert request.conversation_data is None
        assert request.metadata is None


class TestMessageCreateRequest:
    """Test MessageCreateRequest model validation"""

    def test_message_create_request_valid(self):
        """Test valid message creation request"""
        request = MessageCreateRequest(
            role="user",
            content="What is the weather?",
            message_type="chat",
            metadata={"source": "web"},
            tokens_used=10,
            cost_usd=0.0005,
        )

        assert request.role == "user"
        assert request.content == "What is the weather?"
        assert request.message_type == "chat"
        assert request.metadata == {"source": "web"}
        assert request.tokens_used == 10
        assert request.cost_usd == 0.0005

    def test_message_create_request_minimal(self):
        """Test minimal message creation request"""
        request = MessageCreateRequest(
            role="assistant",
            content="The weather is sunny.",
        )

        assert request.role == "assistant"
        assert request.content == "The weather is sunny."
        assert request.message_type == "chat"
        assert request.metadata == {}
        assert request.tokens_used == 0
        assert request.cost_usd == 0.0

    def test_message_create_request_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            MessageCreateRequest(content="Test")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "role" in missing_fields

    def test_message_create_request_tool_call(self):
        """Test message creation request for tool call"""
        request = MessageCreateRequest(
            role="assistant",
            content="Searching database",
            message_type="tool_call",
            metadata={"tool_name": "database_search", "query": "user_123"},
        )

        assert request.message_type == "tool_call"
        assert request.metadata["tool_name"] == "database_search"


class TestMemoryCreateRequest:
    """Test MemoryCreateRequest model validation"""

    def test_memory_create_request_valid(self):
        """Test valid memory creation request"""
        request = MemoryCreateRequest(
            memory_type="preference",
            content="User prefers dark mode",
            metadata={"importance": "high"},
        )

        assert request.memory_type == "preference"
        assert request.content == "User prefers dark mode"
        assert request.metadata == {"importance": "high"}

    def test_memory_create_request_minimal(self):
        """Test minimal memory creation request"""
        request = MemoryCreateRequest(
            memory_type="fact",
            content="User birthday is January 1",
        )

        assert request.memory_type == "fact"
        assert request.content == "User birthday is January 1"
        assert request.metadata == {}

    def test_memory_create_request_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            MemoryCreateRequest(content="Test content")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "memory_type" in missing_fields


class TestMemoryUpdateRequest:
    """Test MemoryUpdateRequest model validation"""

    def test_memory_update_request_partial(self):
        """Test partial memory update request"""
        request = MemoryUpdateRequest(
            content="Updated memory content",
        )

        assert request.content == "Updated memory content"
        assert request.metadata is None

    def test_memory_update_request_all_fields(self):
        """Test memory update request with all fields"""
        request = MemoryUpdateRequest(
            content="Fully updated content",
            metadata={"updated": True, "version": 2},
        )

        assert request.content == "Fully updated content"
        assert request.metadata == {"updated": True, "version": 2}

    def test_memory_update_request_empty(self):
        """Test empty memory update request is valid"""
        request = MemoryUpdateRequest()

        assert request.content is None
        assert request.metadata is None


class TestSessionResponse:
    """Test SessionResponse model"""

    def test_session_response_creation(self):
        """Test creating session response"""
        now = datetime.now(timezone.utc)

        response = SessionResponse(
            session_id="sess_123",
            user_id="user_456",
            status="active",
            conversation_data={"data": "test"},
            metadata={"source": "web"},
            is_active=True,
            message_count=10,
            total_tokens=2000,
            total_cost=0.10,
            session_summary="Active conversation",
            created_at=now,
            updated_at=now,
            last_activity=now,
        )

        assert response.session_id == "sess_123"
        assert response.user_id == "user_456"
        assert response.status == "active"
        assert response.conversation_data == {"data": "test"}
        assert response.metadata == {"source": "web"}
        assert response.is_active is True
        assert response.message_count == 10
        assert response.total_tokens == 2000
        assert response.total_cost == 0.10
        assert response.session_summary == "Active conversation"

    def test_session_response_minimal(self):
        """Test creating minimal session response"""
        response = SessionResponse(
            session_id="sess_minimal",
            user_id="user_123",
            status="active",
            is_active=True,
            message_count=0,
            total_tokens=0,
            total_cost=0.0,
            created_at=None,
            updated_at=None,
            last_activity=None,
        )

        assert response.session_id == "sess_minimal"
        assert response.user_id == "user_123"
        assert response.conversation_data == {}
        assert response.metadata == {}
        assert response.session_summary == ""


class TestSessionListResponse:
    """Test SessionListResponse model"""

    def test_session_list_response(self):
        """Test session list response"""
        now = datetime.now(timezone.utc)

        sessions = [
            SessionResponse(
                session_id=f"sess_{i}",
                user_id="user_123",
                status="active",
                is_active=True,
                message_count=i * 5,
                total_tokens=i * 100,
                total_cost=i * 0.01,
                created_at=now,
                updated_at=now,
                last_activity=now,
            )
            for i in range(3)
        ]

        response = SessionListResponse(
            sessions=sessions,
            total=3,
            page=1,
            page_size=10,
        )

        assert len(response.sessions) == 3
        assert response.total == 3
        assert response.page == 1
        assert response.page_size == 10

    def test_session_list_response_empty(self):
        """Test empty session list response"""
        response = SessionListResponse(
            sessions=[],
            total=0,
            page=1,
            page_size=10,
        )

        assert len(response.sessions) == 0
        assert response.total == 0


class TestMessageResponse:
    """Test MessageResponse model"""

    def test_message_response_creation(self):
        """Test creating message response"""
        now = datetime.now(timezone.utc)

        response = MessageResponse(
            message_id="msg_123",
            session_id="sess_456",
            user_id="user_789",
            role="user",
            content="Test message",
            message_type="chat",
            metadata={"source": "mobile"},
            tokens_used=20,
            cost_usd=0.002,
            created_at=now,
        )

        assert response.message_id == "msg_123"
        assert response.session_id == "sess_456"
        assert response.user_id == "user_789"
        assert response.role == "user"
        assert response.content == "Test message"
        assert response.message_type == "chat"
        assert response.tokens_used == 20
        assert response.cost_usd == 0.002

    def test_message_response_minimal(self):
        """Test creating minimal message response"""
        response = MessageResponse(
            message_id="msg_minimal",
            session_id="sess_123",
            user_id="user_456",
            role="assistant",
            content="Response",
            message_type="chat",
            tokens_used=0,
            cost_usd=0.0,
            created_at=None,
        )

        assert response.message_id == "msg_minimal"
        assert response.metadata == {}


class TestMessageListResponse:
    """Test MessageListResponse model"""

    def test_message_list_response(self):
        """Test message list response"""
        now = datetime.now(timezone.utc)

        messages = [
            MessageResponse(
                message_id=f"msg_{i}",
                session_id="sess_123",
                user_id="user_456",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                message_type="chat",
                tokens_used=10,
                cost_usd=0.001,
                created_at=now,
            )
            for i in range(5)
        ]

        response = MessageListResponse(
            messages=messages,
            total=5,
            page=1,
            page_size=20,
        )

        assert len(response.messages) == 5
        assert response.total == 5
        assert response.page == 1
        assert response.page_size == 20

    def test_message_list_response_empty(self):
        """Test empty message list response"""
        response = MessageListResponse(
            messages=[],
            total=0,
            page=1,
            page_size=20,
        )

        assert len(response.messages) == 0
        assert response.total == 0


class TestMemoryResponse:
    """Test MemoryResponse model"""

    def test_memory_response_creation(self):
        """Test creating memory response"""
        now = datetime.now(timezone.utc)

        response = MemoryResponse(
            memory_id="mem_123",
            session_id="sess_456",
            user_id="user_789",
            memory_type="preference",
            content="User prefers technical explanations",
            metadata={"category": "communication_style"},
            created_at=now,
        )

        assert response.memory_id == "mem_123"
        assert response.session_id == "sess_456"
        assert response.user_id == "user_789"
        assert response.memory_type == "preference"
        assert response.content == "User prefers technical explanations"
        assert response.metadata == {"category": "communication_style"}
        assert response.created_at == now

    def test_memory_response_minimal(self):
        """Test creating minimal memory response"""
        response = MemoryResponse(
            memory_id="mem_minimal",
            session_id="sess_123",
            user_id="user_456",
            memory_type="fact",
            content="Test fact",
            created_at=None,
        )

        assert response.memory_id == "mem_minimal"
        assert response.metadata == {}


class TestSessionSummaryResponse:
    """Test SessionSummaryResponse model"""

    def test_session_summary_response_creation(self):
        """Test creating session summary response"""
        now = datetime.now(timezone.utc)

        response = SessionSummaryResponse(
            session_id="sess_123",
            user_id="user_456",
            status="active",
            message_count=25,
            total_tokens=5000,
            total_cost=0.25,
            has_memory=True,
            is_active=True,
            created_at=now,
            last_activity=now,
        )

        assert response.session_id == "sess_123"
        assert response.user_id == "user_456"
        assert response.status == "active"
        assert response.message_count == 25
        assert response.total_tokens == 5000
        assert response.total_cost == 0.25
        assert response.has_memory is True
        assert response.is_active is True

    def test_session_summary_response_minimal(self):
        """Test creating minimal session summary response"""
        response = SessionSummaryResponse(
            session_id="sess_minimal",
            user_id="user_123",
            status="completed",
            message_count=0,
            total_tokens=0,
            total_cost=0.0,
            has_memory=False,
            is_active=False,
            created_at=None,
            last_activity=None,
        )

        assert response.session_id == "sess_minimal"
        assert response.has_memory is False
        assert response.is_active is False


class TestSessionStatsResponse:
    """Test SessionStatsResponse model"""

    def test_session_stats_response_creation(self):
        """Test creating session stats response"""
        response = SessionStatsResponse(
            total_sessions=100,
            active_sessions=25,
            total_messages=5000,
            total_tokens=250000,
            total_cost=12.50,
            average_messages_per_session=50.0,
        )

        assert response.total_sessions == 100
        assert response.active_sessions == 25
        assert response.total_messages == 5000
        assert response.total_tokens == 250000
        assert response.total_cost == 12.50
        assert response.average_messages_per_session == 50.0

    def test_session_stats_response_defaults(self):
        """Test session stats response with default values"""
        response = SessionStatsResponse()

        assert response.total_sessions == 0
        assert response.active_sessions == 0
        assert response.total_messages == 0
        assert response.total_tokens == 0
        assert response.total_cost == 0.0
        assert response.average_messages_per_session == 0.0

    def test_session_stats_response_partial(self):
        """Test session stats response with partial values"""
        response = SessionStatsResponse(
            total_sessions=50,
            active_sessions=10,
        )

        assert response.total_sessions == 50
        assert response.active_sessions == 10
        assert response.total_messages == 0
        assert response.total_tokens == 0


class TestSessionServiceStatus:
    """Test SessionServiceStatus model"""

    def test_session_service_status_creation(self):
        """Test creating session service status"""
        now = datetime.now(timezone.utc)

        status = SessionServiceStatus(
            service="session_service",
            status="operational",
            port=8205,
            version="1.0.0",
            database_connected=True,
            timestamp=now,
        )

        assert status.service == "session_service"
        assert status.status == "operational"
        assert status.port == 8205
        assert status.version == "1.0.0"
        assert status.database_connected is True
        assert status.timestamp == now

    def test_session_service_status_defaults(self):
        """Test session service status with default values"""
        now = datetime.now(timezone.utc)

        status = SessionServiceStatus(
            database_connected=True,
            timestamp=now,
        )

        assert status.service == "session_service"
        assert status.status == "operational"
        assert status.port == 8205
        assert status.version == "1.0.0"

    def test_session_service_status_degraded(self):
        """Test session service status when degraded"""
        now = datetime.now(timezone.utc)

        status = SessionServiceStatus(
            status="degraded",
            database_connected=False,
            timestamp=now,
        )

        assert status.status == "degraded"
        assert status.database_connected is False


class TestErrorResponse:
    """Test ErrorResponse model"""

    def test_error_response_creation(self):
        """Test creating error response"""
        now = datetime.now(timezone.utc)

        error = ErrorResponse(
            error="Session not found",
            detail="Session with ID sess_123 does not exist",
            timestamp=now,
        )

        assert error.error == "Session not found"
        assert error.detail == "Session with ID sess_123 does not exist"
        assert error.timestamp == now

    def test_error_response_minimal(self):
        """Test creating minimal error response"""
        error = ErrorResponse(error="Invalid request")

        assert error.error == "Invalid request"
        assert error.detail is None
        assert isinstance(error.timestamp, datetime)

    def test_error_response_auto_timestamp(self):
        """Test error response auto-generates timestamp"""
        before = datetime.utcnow()
        error = ErrorResponse(error="Test error")
        after = datetime.utcnow()

        assert before <= error.timestamp <= after

    def test_error_response_with_detail(self):
        """Test error response with detailed information"""
        error = ErrorResponse(
            error="Validation failed",
            detail="Required field 'user_id' is missing",
        )

        assert error.error == "Validation failed"
        assert "user_id" in error.detail


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
