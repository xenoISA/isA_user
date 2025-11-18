#!/usr/bin/env python3
"""
Test Session Service Event Subscriptions

Tests that session service correctly handles events from other services
"""

import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.session_service.events.handlers import SessionEventHandlers
from core.nats_client import Event, EventType, ServiceSource


class MockSession:
    """Mock session object"""

    def __init__(self, session_id, user_id, status="active"):
        self.session_id = session_id
        self.user_id = user_id
        self.status = status
        self.message_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.created_at = datetime.utcnow()
        self.ended_at = None


class MockSessionRepository:
    """Mock repository for testing"""

    def __init__(self):
        self.sessions = {}
        self.ended_sessions = []

    async def get_user_sessions(self, user_id, active_only=False):
        """Mock get user sessions"""
        if user_id not in self.sessions:
            return []

        sessions = self.sessions[user_id]
        if active_only:
            return [s for s in sessions if s.status == "active"]
        return sessions

    async def end_session(self, session_id):
        """Mock end session"""
        self.ended_sessions.append(session_id)

        # Update session status
        for user_id, sessions in self.sessions.items():
            for session in sessions:
                if session.session_id == session_id:
                    session.status = "ended"
                    session.ended_at = datetime.utcnow()
                    return True
        return False


class MockSessionService:
    """Mock session service for testing"""

    def __init__(self):
        self.session_repo = MockSessionRepository()


async def test_user_deleted_event():
    """Test handling of user.deleted event - should end all active sessions"""
    print("\n" + "="*60)
    print("TEST 1: User Deleted Event Handler")
    print("="*60)

    # Create mock service and handlers
    mock_service = MockSessionService()
    handlers = SessionEventHandlers(mock_service)

    # Setup: Create multiple sessions for the user (some active, some ended)
    user_id = "user_123"
    mock_service.session_repo.sessions[user_id] = [
        MockSession("session_1", user_id, status="active"),
        MockSession("session_2", user_id, status="active"),
        MockSession("session_3", user_id, status="ended"),
        MockSession("session_4", user_id, status="active"),
    ]

    initial_sessions = len(mock_service.session_repo.sessions[user_id])
    active_sessions = len([s for s in mock_service.session_repo.sessions[user_id] if s.status == "active"])

    print(f"📋 User has {initial_sessions} sessions ({active_sessions} active, {initial_sessions - active_sessions} ended)")

    # Create user.deleted event
    event_data = {
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Handle event
    print(f"🔥 Triggering user.deleted event for user: {user_id}")
    await handlers.handle_user_deleted(event_data)

    # Verify active sessions were ended
    ended_count = len(mock_service.session_repo.ended_sessions)
    remaining_active = len([s for s in mock_service.session_repo.sessions[user_id] if s.status == "active"])

    print(f"✅ Ended {ended_count} active sessions")
    print(f"✅ Remaining active sessions: {remaining_active}")

    assert ended_count == 3, f"Expected 3 sessions ended, got {ended_count}"
    assert remaining_active == 0, f"Expected 0 active sessions, got {remaining_active}"

    # Verify ended sessions
    for session_id in mock_service.session_repo.ended_sessions:
        print(f"   - Ended session: {session_id}")

    print("✅ TEST PASSED: All active sessions ended successfully")
    return True


async def test_user_deleted_no_sessions():
    """Test handling of user.deleted event when user has no sessions"""
    print("\n" + "="*60)
    print("TEST 2: User Deleted Event with No Sessions")
    print("="*60)

    # Create mock service and handlers
    mock_service = MockSessionService()
    handlers = SessionEventHandlers(mock_service)

    # User has no sessions
    user_id = "user_456"

    # Create user.deleted event
    event_data = {
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    print(f"🔥 Triggering user.deleted event for user with no sessions: {user_id}")

    # Handle event
    await handlers.handle_user_deleted(event_data)

    # Verify no errors occurred
    ended_count = len(mock_service.session_repo.ended_sessions)

    print(f"✅ No sessions to end (as expected)")
    assert ended_count == 0, f"Expected 0 sessions ended, got {ended_count}"

    print("✅ TEST PASSED: Handled user with no sessions gracefully")
    return True


async def test_user_deleted_already_ended_sessions():
    """Test handling of user.deleted event when all sessions are already ended"""
    print("\n" + "="*60)
    print("TEST 3: User Deleted Event with Already Ended Sessions")
    print("="*60)

    # Create mock service and handlers
    mock_service = MockSessionService()
    handlers = SessionEventHandlers(mock_service)

    # Setup: Create only ended sessions for the user
    user_id = "user_789"
    mock_service.session_repo.sessions[user_id] = [
        MockSession("session_1", user_id, status="ended"),
        MockSession("session_2", user_id, status="ended"),
    ]

    print(f"📋 User has 2 sessions (all already ended)")

    # Create user.deleted event
    event_data = {
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Handle event
    print(f"🔥 Triggering user.deleted event for user: {user_id}")
    await handlers.handle_user_deleted(event_data)

    # Verify no additional sessions were ended
    ended_count = len(mock_service.session_repo.ended_sessions)

    print(f"✅ No active sessions to end (sessions were already ended)")
    assert ended_count == 0, f"Expected 0 sessions ended, got {ended_count}"

    print("✅ TEST PASSED: Handled already-ended sessions correctly")
    return True


async def test_missing_event_data():
    """Test that handlers gracefully handle missing event data"""
    print("\n" + "="*60)
    print("TEST 4: Missing Event Data Handling")
    print("="*60)

    # Create mock service and handlers
    mock_service = MockSessionService()
    handlers = SessionEventHandlers(mock_service)

    # Test user.deleted with missing user_id
    print("🧪 Testing user.deleted with missing user_id")
    await handlers.handle_user_deleted({})

    assert len(mock_service.session_repo.ended_sessions) == 0, \
        "Should not end any sessions when user_id is missing"

    print("✅ Handled missing user_id gracefully")

    # Test user.deleted with None user_id
    print("🧪 Testing user.deleted with None user_id")
    await handlers.handle_user_deleted({"user_id": None})

    assert len(mock_service.session_repo.ended_sessions) == 0, \
        "Should not end any sessions when user_id is None"

    print("✅ Handled None user_id gracefully")

    print("✅ TEST PASSED: All edge cases handled gracefully")
    return True


async def test_concurrent_user_deletions():
    """Test handling of multiple user.deleted events concurrently"""
    print("\n" + "="*60)
    print("TEST 5: Concurrent User Deletions")
    print("="*60)

    # Create mock service and handlers
    mock_service = MockSessionService()
    handlers = SessionEventHandlers(mock_service)

    # Setup: Create sessions for multiple users
    users = ["user_001", "user_002", "user_003"]
    for user_id in users:
        mock_service.session_repo.sessions[user_id] = [
            MockSession(f"{user_id}_session_1", user_id, status="active"),
            MockSession(f"{user_id}_session_2", user_id, status="active"),
        ]

    total_initial_sessions = sum(len(sessions) for sessions in mock_service.session_repo.sessions.values())
    print(f"📋 Created sessions for {len(users)} users ({total_initial_sessions} total sessions)")

    # Create multiple user.deleted events
    events = [
        {"user_id": user_id, "timestamp": datetime.utcnow().isoformat()}
        for user_id in users
    ]

    # Handle events concurrently
    print(f"🔥 Triggering {len(events)} user.deleted events concurrently")
    await asyncio.gather(*[
        handlers.handle_user_deleted(event_data)
        for event_data in events
    ])

    # Verify all sessions were ended
    ended_count = len(mock_service.session_repo.ended_sessions)

    print(f"✅ Ended {ended_count} sessions across {len(users)} users")
    assert ended_count == 6, f"Expected 6 sessions ended, got {ended_count}"

    print("✅ TEST PASSED: Concurrent deletions handled successfully")
    return True


async def run_all_tests():
    """Run all session service event subscription tests"""
    print("\n" + "🔐" * 30)
    print("SESSION SERVICE EVENT SUBSCRIPTION TESTS")
    print("🔐" * 30)

    tests = [
        ("User Deleted Event", test_user_deleted_event),
        ("User Deleted with No Sessions", test_user_deleted_no_sessions),
        ("User Deleted with Already Ended Sessions", test_user_deleted_already_ended_sessions),
        ("Missing Event Data Handling", test_missing_event_data),
        ("Concurrent User Deletions", test_concurrent_user_deletions),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, "PASSED" if result else "FAILED"))
        except Exception as e:
            print(f"❌ TEST FAILED: {test_name}")
            print(f"   Error: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((test_name, "FAILED"))

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for _, status in results if status == "PASSED")
    total = len(results)

    for test_name, status in results:
        emoji = "✅" if status == "PASSED" else "❌"
        print(f"{emoji} {test_name}: {status}")

    print(f"\n📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("⚠️  SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
