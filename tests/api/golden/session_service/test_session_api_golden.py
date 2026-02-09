"""
Session Service API Golden Tests

Layer 4: API Contract Tests with real HTTP calls.
Tests validate HTTP contracts, status codes, and response schemas.

Purpose:
- Test actual HTTP endpoints against running session_service
- Validate request/response schemas
- Test status code contracts (200, 201, 400, 404, 422)
- Test pagination and query parameters

Usage:
    pytest tests/api/golden/session_service -v
    pytest tests/api/golden/session_service -v -k "health"
"""
import pytest
import uuid
from datetime import datetime

from tests.api.conftest import APIClient, APIAssertions
from tests.contracts.session.data_contract import SessionTestDataFactory

pytestmark = [pytest.mark.api, pytest.mark.golden, pytest.mark.asyncio]


# =============================================================================
# Test Data Generators
# =============================================================================

def unique_user_id() -> str:
    """Generate unique user ID for tests"""
    return f"api_test_{uuid.uuid4().hex[:12]}"


def unique_session_id() -> str:
    """Generate unique session ID for tests"""
    return f"sess_api_{uuid.uuid4().hex[:16]}"


# =============================================================================
# Health Endpoint Tests
# =============================================================================

class TestSessionHealthAPIGolden:
    """GOLDEN: Session service health endpoint contracts"""

    async def test_health_endpoint_returns_200(self, session_api: APIClient):
        """GOLDEN: GET /health returns 200 OK"""
        response = await session_api.get_raw("/health")
        assert response.status_code == 200

    async def test_health_detailed_returns_200(self, session_api: APIClient):
        """GOLDEN: GET /health/detailed returns 200 with component status"""
        response = await session_api.get_raw("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "service" in data


# =============================================================================
# Session Creation Tests
# =============================================================================

class TestSessionCreateAPIGolden:
    """GOLDEN: POST /api/v1/sessions endpoint contracts"""

    async def test_create_session_returns_200_or_201(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST / creates session and returns session response"""
        user_id = unique_user_id()

        response = await session_api.post(
            "",
            json={
                "user_id": user_id,
                "conversation_data": {"topic": "test"},
                "metadata": {"platform": "api_test"}
            }
        )

        api_assert.assert_created(response)
        data = response.json()
        api_assert.assert_has_fields(data, ["session_id", "user_id", "status"])
        assert data["user_id"] == user_id
        assert data["status"] == "active"
        assert data["is_active"] is True

    async def test_create_session_with_custom_id(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST / with custom session_id uses that ID"""
        user_id = unique_user_id()
        session_id = unique_session_id()

        response = await session_api.post(
            "",
            json={
                "user_id": user_id,
                "session_id": session_id,
            }
        )

        api_assert.assert_created(response)
        data = response.json()
        assert data["session_id"] == session_id

    async def test_create_session_rejects_empty_user_id(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST / with empty user_id returns 400 or 422"""
        response = await session_api.post(
            "",
            json={"user_id": ""}
        )

        # Accept either 400 or 422 for validation error
        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_create_session_rejects_whitespace_user_id(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST / with whitespace user_id returns 400 or 422"""
        response = await session_api.post(
            "",
            json={"user_id": "   "}
        )

        # Accept either 400 or 422 for validation error
        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"


# =============================================================================
# Session Retrieval Tests
# =============================================================================

class TestSessionGetAPIGolden:
    """GOLDEN: GET /api/v1/sessions/{session_id} endpoint contracts"""

    async def test_get_session_returns_session(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /{session_id} returns session details"""
        user_id = unique_user_id()

        # Create session first
        create_response = await session_api.post(
            "",
            json={"user_id": user_id}
        )
        api_assert.assert_created(create_response)
        session_id = create_response.json()["session_id"]

        # Get session
        response = await session_api.get(f"/{session_id}?user_id={user_id}")
        api_assert.assert_success(response)

        data = response.json()
        api_assert.assert_has_fields(data, [
            "session_id", "user_id", "status", "is_active",
            "message_count", "total_tokens", "total_cost"
        ])
        assert data["session_id"] == session_id

    async def test_get_session_nonexistent_returns_404(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /{nonexistent_id} returns 404"""
        session_id = f"sess_nonexistent_{uuid.uuid4().hex[:8]}"
        response = await session_api.get(f"/{session_id}")
        api_assert.assert_not_found(response)

    async def test_get_session_unauthorized_returns_404(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /{session_id} with wrong user_id returns 404 (not 403)"""
        user_id = unique_user_id()
        wrong_user_id = unique_user_id()

        # Create session
        create_response = await session_api.post(
            "",
            json={"user_id": user_id}
        )
        session_id = create_response.json()["session_id"]

        # Try to get with wrong user_id
        response = await session_api.get(f"/{session_id}?user_id={wrong_user_id}")

        # Should return 404 to not leak session existence
        api_assert.assert_not_found(response)


# =============================================================================
# Session List Tests
# =============================================================================

class TestSessionListAPIGolden:
    """GOLDEN: GET /api/v1/sessions endpoint contracts"""

    async def test_list_sessions_requires_user_id(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET / without user_id returns 422"""
        response = await session_api.get("")
        api_assert.assert_validation_error(response)

    async def test_list_sessions_returns_user_sessions(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /?user_id=xxx returns user's sessions"""
        user_id = unique_user_id()

        # Create a session
        await session_api.post("", json={"user_id": user_id})

        # List sessions
        response = await session_api.get(f"?user_id={user_id}")
        api_assert.assert_success(response)

        data = response.json()
        api_assert.assert_has_fields(data, ["sessions", "total", "page", "page_size"])
        assert isinstance(data["sessions"], list)

    async def test_list_sessions_pagination(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /?user_id=xxx&page=1&page_size=5 respects pagination"""
        user_id = unique_user_id()

        # Create multiple sessions
        for _ in range(3):
            await session_api.post("", json={"user_id": user_id})

        # List with pagination
        response = await session_api.get(f"?user_id={user_id}&page=1&page_size=2")
        api_assert.assert_success(response)

        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["sessions"]) <= 2

    async def test_list_sessions_active_only_filter(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /?user_id=xxx&active_only=true filters active sessions"""
        user_id = unique_user_id()

        # Create session
        await session_api.post("", json={"user_id": user_id})

        # List with active_only filter
        response = await session_api.get(f"?user_id={user_id}&active_only=true")
        api_assert.assert_success(response)

        data = response.json()
        # All returned sessions should be active
        for session in data["sessions"]:
            assert session["is_active"] is True

    async def test_list_sessions_empty_for_new_user(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /?user_id=xxx returns empty list for user with no sessions"""
        user_id = unique_user_id()

        response = await session_api.get(f"?user_id={user_id}")
        api_assert.assert_success(response)

        data = response.json()
        assert data["sessions"] == []
        assert data["total"] == 0


# =============================================================================
# Session Update Tests
# =============================================================================

class TestSessionUpdateAPIGolden:
    """GOLDEN: PUT /api/v1/sessions/{session_id} endpoint contracts"""

    async def test_update_session_status(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: PUT /{session_id} updates session status"""
        user_id = unique_user_id()

        # Create session
        create_response = await session_api.post(
            "",
            json={"user_id": user_id}
        )
        session_id = create_response.json()["session_id"]

        # Update status
        response = await session_api.put(
            f"/{session_id}?user_id={user_id}",
            json={"status": "completed"}
        )
        api_assert.assert_success(response)

        data = response.json()
        assert data["status"] == "completed"

    async def test_update_session_nonexistent_returns_404(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: PUT /{nonexistent_id} returns 404"""
        session_id = f"sess_nonexistent_{uuid.uuid4().hex[:8]}"

        response = await session_api.put(
            f"/{session_id}",
            json={"status": "completed"}
        )
        api_assert.assert_not_found(response)


# =============================================================================
# Session End (Delete) Tests
# =============================================================================

class TestSessionEndAPIGolden:
    """GOLDEN: DELETE /api/v1/sessions/{session_id} endpoint contracts"""

    async def test_end_session_returns_success(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: DELETE /{session_id} ends session and returns success"""
        user_id = unique_user_id()

        # Create session
        create_response = await session_api.post(
            "",
            json={"user_id": user_id}
        )
        session_id = create_response.json()["session_id"]

        # End session
        response = await session_api.delete(f"/{session_id}?user_id={user_id}")
        api_assert.assert_success(response)

    async def test_end_session_nonexistent_returns_404(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: DELETE /{nonexistent_id} returns 404"""
        session_id = f"sess_nonexistent_{uuid.uuid4().hex[:8]}"

        response = await session_api.delete(f"/{session_id}")
        api_assert.assert_not_found(response)


# =============================================================================
# Message Tests
# =============================================================================

class TestSessionMessageAPIGolden:
    """GOLDEN: Message endpoint contracts"""

    async def test_add_message_returns_message(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /{session_id}/messages creates message"""
        user_id = unique_user_id()

        # Create session
        create_response = await session_api.post(
            "",
            json={"user_id": user_id}
        )
        session_id = create_response.json()["session_id"]

        # Add message
        response = await session_api.post(
            f"/{session_id}/messages?user_id={user_id}",
            json={
                "role": "user",
                "content": "Hello, this is a test message",
                "message_type": "chat",
                "tokens_used": 50,
                "cost_usd": 0.005
            }
        )

        api_assert.assert_created(response)
        data = response.json()
        api_assert.assert_has_fields(data, [
            "message_id", "session_id", "role", "content"
        ])
        assert data["role"] == "user"
        assert data["content"] == "Hello, this is a test message"

    async def test_add_message_rejects_invalid_role(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /{session_id}/messages with invalid role returns 400"""
        user_id = unique_user_id()

        # Create session
        create_response = await session_api.post(
            "",
            json={"user_id": user_id}
        )
        session_id = create_response.json()["session_id"]

        # Try to add message with invalid role
        response = await session_api.post(
            f"/{session_id}/messages?user_id={user_id}",
            json={
                "role": "invalid_role",
                "content": "Test content",
                "message_type": "chat"
            }
        )

        # Should return 400 for validation error
        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_add_message_rejects_empty_content(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /{session_id}/messages with empty content returns 400"""
        user_id = unique_user_id()

        # Create session
        create_response = await session_api.post(
            "",
            json={"user_id": user_id}
        )
        session_id = create_response.json()["session_id"]

        # Try to add message with empty content
        response = await session_api.post(
            f"/{session_id}/messages?user_id={user_id}",
            json={
                "role": "user",
                "content": "",
                "message_type": "chat"
            }
        )

        # Should return 400 for validation error
        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_get_session_messages_returns_list(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /{session_id}/messages returns message list"""
        user_id = unique_user_id()

        # Create session
        create_response = await session_api.post(
            "",
            json={"user_id": user_id}
        )
        session_id = create_response.json()["session_id"]

        # Add a message
        await session_api.post(
            f"/{session_id}/messages?user_id={user_id}",
            json={
                "role": "user",
                "content": "Test message",
                "message_type": "chat"
            }
        )

        # Get messages
        response = await session_api.get(f"/{session_id}/messages?user_id={user_id}")
        api_assert.assert_success(response)

        data = response.json()
        api_assert.assert_has_fields(data, ["messages", "total", "page", "page_size"])
        assert isinstance(data["messages"], list)
        assert len(data["messages"]) >= 1

    async def test_get_session_messages_empty_session(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /{session_id}/messages for empty session returns empty list"""
        user_id = unique_user_id()

        # Create session
        create_response = await session_api.post(
            "",
            json={"user_id": user_id}
        )
        session_id = create_response.json()["session_id"]

        # Get messages (should be empty)
        response = await session_api.get(f"/{session_id}/messages?user_id={user_id}")
        api_assert.assert_success(response)

        data = response.json()
        assert data["messages"] == []
        assert data["total"] == 0


# =============================================================================
# Session Summary Tests
# =============================================================================

class TestSessionSummaryAPIGolden:
    """GOLDEN: GET /api/v1/sessions/{session_id}/summary endpoint contracts"""

    async def test_get_summary_returns_metrics(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /{session_id}/summary returns session metrics"""
        user_id = unique_user_id()

        # Create session
        create_response = await session_api.post(
            "",
            json={"user_id": user_id}
        )
        session_id = create_response.json()["session_id"]

        # Get summary
        response = await session_api.get(f"/{session_id}/summary?user_id={user_id}")
        api_assert.assert_success(response)

        data = response.json()
        api_assert.assert_has_fields(data, [
            "session_id", "user_id", "status",
            "message_count", "total_tokens", "total_cost"
        ])

    async def test_get_summary_nonexistent_returns_404(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /{nonexistent_id}/summary returns 404"""
        session_id = f"sess_nonexistent_{uuid.uuid4().hex[:8]}"

        response = await session_api.get(f"/{session_id}/summary")
        api_assert.assert_not_found(response)


# =============================================================================
# Stats Tests
# =============================================================================

class TestSessionStatsAPIGolden:
    """GOLDEN: GET /api/v1/sessions/stats endpoint contracts"""

    async def test_stats_returns_service_stats(
        self, session_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /stats returns session service statistics"""
        response = await session_api.get("/stats")
        api_assert.assert_success(response)

        data = response.json()
        api_assert.assert_has_fields(data, [
            "total_sessions", "active_sessions", "total_messages",
            "total_tokens", "total_cost"
        ])


# =============================================================================
# SUMMARY
# =============================================================================
"""
SESSION SERVICE API GOLDEN TESTS SUMMARY:

Test Coverage (25 tests total):

1. Health Endpoints (2 tests):
   - /health returns 200
   - /health/detailed returns 200 with status

2. Session Creation (4 tests):
   - Creates session returns 200/201
   - Creates with custom session_id
   - Rejects empty user_id
   - Rejects whitespace user_id

3. Session Retrieval (3 tests):
   - Get session returns details
   - Get nonexistent returns 404
   - Get unauthorized returns 404 (not 403)

4. Session List (5 tests):
   - Requires user_id parameter
   - Returns user's sessions
   - Respects pagination
   - Supports active_only filter
   - Returns empty for new user

5. Session Update (2 tests):
   - Updates session status
   - Update nonexistent returns 404

6. Session End (2 tests):
   - Ends session returns success
   - End nonexistent returns 404

7. Messages (5 tests):
   - Add message returns message
   - Rejects invalid role
   - Rejects empty content
   - Get messages returns list
   - Get empty session returns empty list

8. Session Summary (2 tests):
   - Get summary returns metrics
   - Get nonexistent summary returns 404

9. Stats (1 test):
   - Get stats returns service statistics

Key Features:
- Real HTTP calls against running service
- Tests HTTP status code contracts
- Tests response schema contracts
- No mocking - validates actual behavior
- Uses unique IDs for test isolation

Run with:
    pytest tests/api/golden/session_service -v
"""
