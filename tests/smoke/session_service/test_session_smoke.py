"""
Session Service Smoke Tests

Quick sanity checks to verify session_service is deployed and functioning correctly.
These tests are designed to:
1. Run quickly (< 30 seconds total)
2. Validate critical paths only
3. Catch obvious deployment failures

Purpose:
- Verify service is up and responding
- Test basic CRUD operations work
- Test critical user flows (create session, add message, end session)
- Validate data contracts are honored

Usage:
    pytest tests/smoke/session_service -v
    pytest tests/smoke/session_service -v -k "health"

Environment Variables:
    SESSION_BASE_URL: Base URL for session service (default: http://localhost:8205)
"""

import os
import pytest
import uuid
import httpx
from datetime import datetime

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]

# Configuration
BASE_URL = os.getenv("SESSION_BASE_URL", "http://localhost:8203")
API_V1 = f"{BASE_URL}/api/v1/sessions"
TIMEOUT = 10.0


# =============================================================================
# Test Data Generators
# =============================================================================

def unique_user_id() -> str:
    """Generate unique user ID for smoke tests"""
    return f"smoke_test_{uuid.uuid4().hex[:8]}"


def unique_session_id() -> str:
    """Generate unique session ID for smoke tests"""
    return f"sess_smoke_{uuid.uuid4().hex[:12]}"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def http_client():
    """Async HTTP client for smoke tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


@pytest.fixture
async def test_session(http_client):
    """
    Create a test session for smoke tests.

    This fixture creates a session, yields it for testing,
    and cleans it up afterward.
    """
    user_id = unique_user_id()

    # Create session
    response = await http_client.post(
        API_V1,
        json={
            "user_id": user_id,
            "conversation_data": {"type": "smoke_test"},
            "metadata": {"created_by": "smoke_test"}
        }
    )

    if response.status_code in [200, 201]:
        session_data = response.json()
        session_data["_test_user_id"] = user_id
        yield session_data

        # Cleanup - try to end the session
        try:
            session_id = session_data["session_id"]
            await http_client.delete(f"{API_V1}/{session_id}?user_id={user_id}")
        except Exception:
            pass  # Ignore cleanup errors
    else:
        pytest.skip(f"Could not create test session: {response.status_code}")


# =============================================================================
# SMOKE TEST 1: Health Checks
# =============================================================================

class TestHealthSmoke:
    """Smoke: Health endpoint sanity checks"""

    async def test_health_endpoint_responds(self, http_client):
        """SMOKE: GET /health returns 200"""
        response = await http_client.get(f"{BASE_URL}/health")
        assert response.status_code == 200, \
            f"Health check failed: {response.status_code}"

    async def test_health_detailed_responds(self, http_client):
        """SMOKE: GET /health/detailed returns 200"""
        response = await http_client.get(f"{BASE_URL}/health/detailed")
        assert response.status_code == 200, \
            f"Detailed health check failed: {response.status_code}"


# =============================================================================
# SMOKE TEST 2: Session CRUD
# =============================================================================

class TestSessionCRUDSmoke:
    """Smoke: Session CRUD operation sanity checks"""

    async def test_create_session_works(self, http_client):
        """SMOKE: POST /sessions creates a session"""
        user_id = unique_user_id()

        response = await http_client.post(
            API_V1,
            json={"user_id": user_id}
        )

        assert response.status_code in [200, 201], \
            f"Create session failed: {response.status_code} - {response.text}"

        data = response.json()
        assert "session_id" in data, "Response missing session_id"
        assert data["user_id"] == user_id, "User ID mismatch"
        assert data["status"] == "active", "Session should be active"

        # Cleanup
        await http_client.delete(f"{API_V1}/{data['session_id']}?user_id={user_id}")

    async def test_get_session_works(self, http_client, test_session):
        """SMOKE: GET /sessions/{id} retrieves session"""
        session_id = test_session["session_id"]
        user_id = test_session["_test_user_id"]

        response = await http_client.get(
            f"{API_V1}/{session_id}?user_id={user_id}"
        )

        assert response.status_code == 200, \
            f"Get session failed: {response.status_code}"

        data = response.json()
        assert data["session_id"] == session_id

    async def test_list_sessions_works(self, http_client, test_session):
        """SMOKE: GET /sessions?user_id=xxx returns session list"""
        user_id = test_session["_test_user_id"]

        response = await http_client.get(f"{API_V1}?user_id={user_id}")

        assert response.status_code == 200, \
            f"List sessions failed: {response.status_code}"

        data = response.json()
        assert "sessions" in data, "Response missing sessions field"
        assert isinstance(data["sessions"], list)

    async def test_update_session_works(self, http_client, test_session):
        """SMOKE: PUT /sessions/{id} updates session"""
        session_id = test_session["session_id"]
        user_id = test_session["_test_user_id"]

        response = await http_client.put(
            f"{API_V1}/{session_id}?user_id={user_id}",
            json={"status": "completed"}
        )

        assert response.status_code == 200, \
            f"Update session failed: {response.status_code}"

        data = response.json()
        assert data["status"] == "completed"

    async def test_end_session_works(self, http_client):
        """SMOKE: DELETE /sessions/{id} ends session"""
        user_id = unique_user_id()

        # Create session to end
        create_response = await http_client.post(
            API_V1,
            json={"user_id": user_id}
        )
        session_id = create_response.json()["session_id"]

        # End session
        response = await http_client.delete(
            f"{API_V1}/{session_id}?user_id={user_id}"
        )

        assert response.status_code == 200, \
            f"End session failed: {response.status_code}"


# =============================================================================
# SMOKE TEST 3: Message Operations
# =============================================================================

class TestMessageSmoke:
    """Smoke: Message operation sanity checks"""

    async def test_add_message_works(self, http_client, test_session):
        """SMOKE: POST /sessions/{id}/messages adds message"""
        session_id = test_session["session_id"]
        user_id = test_session["_test_user_id"]

        response = await http_client.post(
            f"{API_V1}/{session_id}/messages?user_id={user_id}",
            json={
                "role": "user",
                "content": "Smoke test message",
                "message_type": "chat",
                "tokens_used": 10,
                "cost_usd": 0.001
            }
        )

        assert response.status_code in [200, 201], \
            f"Add message failed: {response.status_code} - {response.text}"

        data = response.json()
        assert "message_id" in data, "Response missing message_id"
        assert data["role"] == "user"

    async def test_get_messages_works(self, http_client, test_session):
        """SMOKE: GET /sessions/{id}/messages retrieves messages"""
        session_id = test_session["session_id"]
        user_id = test_session["_test_user_id"]

        # Add a message first
        await http_client.post(
            f"{API_V1}/{session_id}/messages?user_id={user_id}",
            json={
                "role": "user",
                "content": "Test message for retrieval",
                "message_type": "chat"
            }
        )

        # Get messages
        response = await http_client.get(
            f"{API_V1}/{session_id}/messages?user_id={user_id}"
        )

        assert response.status_code == 200, \
            f"Get messages failed: {response.status_code}"

        data = response.json()
        assert "messages" in data, "Response missing messages field"
        assert len(data["messages"]) >= 1, "Should have at least 1 message"


# =============================================================================
# SMOKE TEST 4: Session Summary
# =============================================================================

class TestSummarySmoke:
    """Smoke: Session summary sanity checks"""

    async def test_get_summary_works(self, http_client, test_session):
        """SMOKE: GET /sessions/{id}/summary returns metrics"""
        session_id = test_session["session_id"]
        user_id = test_session["_test_user_id"]

        response = await http_client.get(
            f"{API_V1}/{session_id}/summary?user_id={user_id}"
        )

        assert response.status_code == 200, \
            f"Get summary failed: {response.status_code}"

        data = response.json()
        assert "session_id" in data
        assert "message_count" in data
        assert "total_tokens" in data


# =============================================================================
# SMOKE TEST 5: Stats
# =============================================================================

class TestStatsSmoke:
    """Smoke: Service stats sanity checks"""

    async def test_stats_endpoint_works(self, http_client):
        """SMOKE: GET /stats returns service statistics"""
        response = await http_client.get(f"{API_V1}/stats")

        assert response.status_code == 200, \
            f"Get stats failed: {response.status_code}"

        data = response.json()
        assert "total_sessions" in data
        assert "active_sessions" in data


# =============================================================================
# SMOKE TEST 6: Critical User Flow
# =============================================================================

class TestCriticalFlowSmoke:
    """Smoke: Critical user flow end-to-end"""

    async def test_complete_session_lifecycle(self, http_client):
        """
        SMOKE: Complete session lifecycle works end-to-end

        Tests: Create -> Add Messages -> Get Summary -> End Session
        """
        user_id = unique_user_id()
        session_id = None

        try:
            # Step 1: Create session
            create_response = await http_client.post(
                API_V1,
                json={
                    "user_id": user_id,
                    "metadata": {"flow_test": True}
                }
            )
            assert create_response.status_code in [200, 201], "Failed to create session"
            session_id = create_response.json()["session_id"]

            # Step 2: Add user message
            msg1_response = await http_client.post(
                f"{API_V1}/{session_id}/messages?user_id={user_id}",
                json={
                    "role": "user",
                    "content": "Hello, I need help",
                    "message_type": "chat",
                    "tokens_used": 10
                }
            )
            assert msg1_response.status_code in [200, 201], "Failed to add user message"

            # Step 3: Add assistant message
            msg2_response = await http_client.post(
                f"{API_V1}/{session_id}/messages?user_id={user_id}",
                json={
                    "role": "assistant",
                    "content": "Hello! How can I assist you today?",
                    "message_type": "chat",
                    "tokens_used": 15
                }
            )
            assert msg2_response.status_code in [200, 201], "Failed to add assistant message"

            # Step 4: Get session summary
            summary_response = await http_client.get(
                f"{API_V1}/{session_id}/summary?user_id={user_id}"
            )
            assert summary_response.status_code == 200, "Failed to get summary"
            summary = summary_response.json()
            assert summary["message_count"] >= 2, "Message count should be at least 2"
            assert summary["total_tokens"] >= 25, "Total tokens should be at least 25"

            # Step 5: End session
            end_response = await http_client.delete(
                f"{API_V1}/{session_id}?user_id={user_id}"
            )
            assert end_response.status_code == 200, "Failed to end session"

            # Step 6: Verify session is ended
            get_response = await http_client.get(
                f"{API_V1}/{session_id}?user_id={user_id}"
            )
            assert get_response.status_code == 200
            session = get_response.json()
            assert session["status"] == "ended", "Session should be ended"
            assert session["is_active"] is False, "Session should be inactive"

        finally:
            # Cleanup if session was created but test failed mid-way
            if session_id:
                try:
                    await http_client.delete(f"{API_V1}/{session_id}?user_id={user_id}")
                except Exception:
                    pass


# =============================================================================
# SMOKE TEST 7: Error Handling
# =============================================================================

class TestErrorHandlingSmoke:
    """Smoke: Error handling sanity checks"""

    async def test_not_found_returns_404(self, http_client):
        """SMOKE: Non-existent session returns 404"""
        fake_session_id = f"sess_nonexistent_{uuid.uuid4().hex[:8]}"

        response = await http_client.get(f"{API_V1}/{fake_session_id}")

        assert response.status_code == 404, \
            f"Expected 404, got {response.status_code}"

    async def test_invalid_request_returns_error(self, http_client):
        """SMOKE: Invalid request returns 400 or 422"""
        response = await http_client.post(
            API_V1,
            json={"user_id": ""}  # Empty user_id
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"


# =============================================================================
# SUMMARY
# =============================================================================
"""
SESSION SERVICE SMOKE TESTS SUMMARY:

Test Coverage (15 tests total):

1. Health (2 tests):
   - /health responds with 200
   - /health/detailed responds with 200

2. Session CRUD (5 tests):
   - Create session works
   - Get session works
   - List sessions works
   - Update session works
   - End session works

3. Messages (2 tests):
   - Add message works
   - Get messages works

4. Summary (1 test):
   - Get summary works

5. Stats (1 test):
   - Stats endpoint works

6. Critical Flow (1 test):
   - Complete lifecycle: Create -> Messages -> Summary -> End

7. Error Handling (2 tests):
   - Not found returns 404
   - Invalid request returns error

Characteristics:
- Fast execution (< 30 seconds)
- No external dependencies (other than running session_service)
- Tests critical paths only
- Validates deployment health

Run with:
    pytest tests/smoke/session_service -v
    pytest tests/smoke/session_service -v --timeout=60
"""
