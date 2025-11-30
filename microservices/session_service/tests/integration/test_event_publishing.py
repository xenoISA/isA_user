#!/usr/bin/env python3
"""
Test Session Service Event Publishing

Tests that session service correctly publishes events to NATS
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from decimal import Decimal

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from microservices.session_service.session_service import SessionService
from microservices.session_service.models import (
    SessionCreateRequest, MessageCreateRequest,
    Session, SessionMessage
)
from core.nats_client import EventType, ServiceSource, get_event_bus


class MockEventBus:
    """Mock event bus for testing"""

    def __init__(self):
        self.published_events = []
        self._is_connected = False

    async def publish_event(self, event):
        """Mock publish event"""
        self.published_events.append({
            "id": event.id,
            "type": event.type,
            "source": event.source,
            "data": event.data,
            "timestamp": event.timestamp
        })
        print(f"✅ Mock event published: {event.type}")

    async def close(self):
        """Mock close"""
        pass


class MockSessionRepository:
    """Mock session repository for testing"""

    def __init__(self):
        self.sessions = {}

    async def create_session(self, session_data):
        """Mock create session"""
        now = datetime.now(timezone.utc)
        session = Session(
            session_id=session_data['session_id'],
            user_id=session_data['user_id'],
            conversation_data=session_data.get('conversation_data', {}),
            metadata=session_data.get('metadata', {}),
            status=session_data.get('status', 'active'),
            is_active=True,
            message_count=0,
            total_tokens=0,
            total_cost=0.0,
            created_at=now,
            updated_at=now
        )
        self.sessions[session.session_id] = session
        return session

    async def get_by_session_id(self, session_id):
        """Mock get session"""
        return self.sessions.get(session_id)

    async def update_session_status(self, session_id, status):
        """Mock update session status"""
        if session_id in self.sessions:
            self.sessions[session_id].status = status
            return True
        return False

    async def increment_message_count(self, session_id, tokens_used, cost_usd):
        """Mock increment message count"""
        if session_id in self.sessions:
            self.sessions[session_id].message_count += 1
            self.sessions[session_id].total_tokens += (tokens_used or 0)
            self.sessions[session_id].total_cost += (float(cost_usd) if cost_usd else 0.0)
            return True
        return False


class MockSessionMessageRepository:
    """Mock session message repository for testing"""

    def __init__(self):
        self.messages = {}
        self.message_counter = 0

    async def create_message(self, message_data):
        """Mock create message"""
        self.message_counter += 1
        message_id = f"msg_{self.message_counter}"
        now = datetime.now(timezone.utc)
        message = SessionMessage(
            message_id=message_id,
            session_id=message_data['session_id'],
            user_id=message_data['user_id'],
            role=message_data['role'],
            content=message_data['content'],
            message_type=message_data.get('message_type', 'text'),
            metadata=message_data.get('metadata', {}),
            tokens_used=message_data.get('tokens_used', 0),
            cost_usd=float(message_data.get('cost_usd', 0.0)),
            created_at=now
        )
        self.messages[message_id] = message
        return message


class MockAccountClient:
    """Mock account client for testing"""

    def check_user_exists(self, user_id):
        """Mock check user exists"""
        return True


async def test_session_started_event():
    """Test session.started event is published when new session is created"""
    print("\n" + "="*60)
    print("TEST 1: Session Started Event")
    print("="*60)

    # Create mock event bus and repositories
    mock_event_bus = MockEventBus()

    # Create service with mock event bus
    service = SessionService.__new__(SessionService)
    service.event_bus = mock_event_bus
    service.session_repo = MockSessionRepository()
    service.message_repo = MockSessionMessageRepository()
    service.account_client = MockAccountClient()
    service.consul_registry = None

    # Create session
    request = SessionCreateRequest(
        user_id="user_123",
        session_id="session_456",
        conversation_data={"context": "test conversation"},
        metadata={"client": "test"}
    )

    response = await service.create_session(request)

    # Verify session was created
    assert response is not None, "Session creation should succeed"
    assert response.session_id == "session_456", "Session ID should match"

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"
    event = mock_event_bus.published_events[0]

    assert event["type"] == EventType.SESSION_STARTED.value
    assert event["source"] == ServiceSource.SESSION_SERVICE.value
    assert event["data"]["session_id"] == "session_456"
    assert event["data"]["user_id"] == "user_123"
    assert "timestamp" in event["data"]

    print(f"✅ session.started event published successfully")
    print(f"   Session ID: {event['data']['session_id']}")
    print(f"   User ID: {event['data']['user_id']}")

    return True


async def test_session_ended_event():
    """Test session.ended event is published when session is ended"""
    print("\n" + "="*60)
    print("TEST 2: Session Ended Event")
    print("="*60)

    # Create mock event bus and repositories
    mock_event_bus = MockEventBus()

    # Create service with mock event bus
    service = SessionService.__new__(SessionService)
    service.event_bus = mock_event_bus
    service.session_repo = MockSessionRepository()
    service.message_repo = MockSessionMessageRepository()
    service.account_client = MockAccountClient()
    service.consul_registry = None

    # Create session first
    create_request = SessionCreateRequest(
        user_id="user_789",
        session_id="session_end_test",
        conversation_data={},
        metadata={}
    )

    await service.create_session(create_request)

    # Clear events from creation
    mock_event_bus.published_events.clear()

    # End the session
    success = await service.end_session("session_end_test")

    # Verify session was ended
    assert success == True, "Session end should succeed"

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"
    event = mock_event_bus.published_events[0]

    assert event["type"] == EventType.SESSION_ENDED.value
    assert event["source"] == ServiceSource.SESSION_SERVICE.value
    assert event["data"]["session_id"] == "session_end_test"
    assert event["data"]["user_id"] == "user_789"
    assert "total_messages" in event["data"]
    assert "total_tokens" in event["data"]
    assert "total_cost" in event["data"]

    print(f"✅ session.ended event published successfully")
    print(f"   Session ID: {event['data']['session_id']}")
    print(f"   Total Messages: {event['data']['total_messages']}")
    print(f"   Total Tokens: {event['data']['total_tokens']}")

    return True


async def test_session_message_sent_event():
    """Test session.message_sent event is published when message is added"""
    print("\n" + "="*60)
    print("TEST 3: Session Message Sent Event")
    print("="*60)

    # Create mock event bus and repositories
    mock_event_bus = MockEventBus()

    # Create service with mock event bus
    service = SessionService.__new__(SessionService)
    service.event_bus = mock_event_bus
    service.session_repo = MockSessionRepository()
    service.message_repo = MockSessionMessageRepository()
    service.account_client = MockAccountClient()
    service.consul_registry = None

    # Create session first
    create_request = SessionCreateRequest(
        user_id="user_msg",
        session_id="session_msg_test",
        conversation_data={},
        metadata={}
    )

    await service.create_session(create_request)

    # Clear events from creation
    mock_event_bus.published_events.clear()

    # Add message to session
    message_request = MessageCreateRequest(
        role="user",
        content="Hello, how are you?",
        message_type="text",
        tokens_used=10,
        cost_usd=Decimal("0.001"),
        metadata={}
    )

    response = await service.add_message("session_msg_test", message_request)

    # Verify message was added
    assert response is not None, "Message creation should succeed"
    assert response.message_id is not None, "Message should have an ID"

    # Verify events were published (message_sent + tokens_used)
    assert len(mock_event_bus.published_events) == 2, "Expected 2 events to be published"

    # Check SESSION_MESSAGE_SENT event
    message_event = mock_event_bus.published_events[0]
    assert message_event["type"] == EventType.SESSION_MESSAGE_SENT.value
    assert message_event["source"] == ServiceSource.SESSION_SERVICE.value
    assert message_event["data"]["session_id"] == "session_msg_test"
    assert message_event["data"]["user_id"] == "user_msg"
    assert message_event["data"]["role"] == "user"
    assert message_event["data"]["tokens_used"] == 10

    print(f"✅ session.message_sent event published successfully")
    print(f"   Session ID: {message_event['data']['session_id']}")
    print(f"   Role: {message_event['data']['role']}")
    print(f"   Tokens Used: {message_event['data']['tokens_used']}")

    return True


async def test_session_tokens_used_event():
    """Test session.tokens_used event is published when tokens are consumed"""
    print("\n" + "="*60)
    print("TEST 4: Session Tokens Used Event")
    print("="*60)

    # Create mock event bus and repositories
    mock_event_bus = MockEventBus()

    # Create service with mock event bus
    service = SessionService.__new__(SessionService)
    service.event_bus = mock_event_bus
    service.session_repo = MockSessionRepository()
    service.message_repo = MockSessionMessageRepository()
    service.account_client = MockAccountClient()
    service.consul_registry = None

    # Create session first
    create_request = SessionCreateRequest(
        user_id="user_tokens",
        session_id="session_tokens_test",
        conversation_data={},
        metadata={}
    )

    await service.create_session(create_request)

    # Clear events from creation
    mock_event_bus.published_events.clear()

    # Add message with token usage
    message_request = MessageCreateRequest(
        role="assistant",
        content="I'm doing well, thank you!",
        message_type="text",
        tokens_used=150,
        cost_usd=Decimal("0.015"),
        metadata={}
    )

    await service.add_message("session_tokens_test", message_request)

    # Verify events were published
    assert len(mock_event_bus.published_events) == 2, "Expected 2 events to be published"

    # Check SESSION_TOKENS_USED event (second event)
    tokens_event = mock_event_bus.published_events[1]
    assert tokens_event["type"] == EventType.SESSION_TOKENS_USED.value
    assert tokens_event["source"] == ServiceSource.SESSION_SERVICE.value
    assert tokens_event["data"]["session_id"] == "session_tokens_test"
    assert tokens_event["data"]["user_id"] == "user_tokens"
    assert tokens_event["data"]["tokens_used"] == 150
    assert tokens_event["data"]["cost_usd"] == 0.015

    print(f"✅ session.tokens_used event published successfully")
    print(f"   Session ID: {tokens_event['data']['session_id']}")
    print(f"   Tokens Used: {tokens_event['data']['tokens_used']}")
    print(f"   Cost USD: ${tokens_event['data']['cost_usd']}")

    return True


async def test_graceful_degradation_without_event_bus():
    """Test service works without event bus (graceful degradation)"""
    print("\n" + "="*60)
    print("TEST 5: Graceful Degradation Without Event Bus")
    print("="*60)

    # Create service WITHOUT event bus
    service = SessionService.__new__(SessionService)
    service.event_bus = None  # No event bus
    service.session_repo = MockSessionRepository()
    service.message_repo = MockSessionMessageRepository()
    service.account_client = MockAccountClient()
    service.consul_registry = None

    # Create session
    request = SessionCreateRequest(
        user_id="user_no_events",
        session_id="session_no_events",
        conversation_data={},
        metadata={}
    )

    response = await service.create_session(request)

    # Verify session was created successfully
    assert response is not None, "Session creation should succeed without event bus"
    assert response.session_id == "session_no_events", "Session should be returned"

    print(f"✅ Service works without event bus (graceful degradation)")
    print(f"   Session created: {response.session_id}")
    print(f"   No events published (expected)")

    return True


async def test_nats_connection():
    """Test actual NATS connection (if available)"""
    print("\n" + "="*60)
    print("TEST 6: NATS Connection Test")
    print("="*60)

    try:
        # Try to connect to NATS
        event_bus = await get_event_bus("session_service_test")

        if event_bus and event_bus._is_connected:
            print("✅ Successfully connected to NATS")
            print(f"   URL: {event_bus.nats_url}")
            await event_bus.close()
            return True
        else:
            print("⚠️  NATS not available or not configured")
            return False

    except Exception as e:
        print(f"⚠️  NATS connection test failed: {e}")
        print("   This is OK for testing without NATS running")
        return False


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("SESSION SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Run tests
    try:
        results["session_started_event"] = await test_session_started_event()
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["session_started_event"] = False

    try:
        results["session_ended_event"] = await test_session_ended_event()
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["session_ended_event"] = False

    try:
        results["session_message_sent_event"] = await test_session_message_sent_event()
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["session_message_sent_event"] = False

    try:
        results["session_tokens_used_event"] = await test_session_tokens_used_event()
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["session_tokens_used_event"] = False

    try:
        results["graceful_degradation"] = await test_graceful_degradation_without_event_bus()
    except Exception as e:
        print(f"❌ TEST 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["graceful_degradation"] = False

    try:
        results["nats_connection"] = await test_nats_connection()
    except Exception as e:
        print(f"❌ TEST 6 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["nats_connection"] = False

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    elif passed >= 5:  # Core tests (NATS is optional)
        print("\n✅ Core tests passed (NATS optional)")
    else:
        print("\n⚠️  Some tests failed")

    return passed, total


if __name__ == "__main__":
    passed, total = asyncio.run(run_all_tests())

    # Exit with appropriate code
    if passed >= 5:  # Core tests must pass (NATS is optional)
        sys.exit(0)
    else:
        sys.exit(1)
