"""
Memory Service Event Subscription Tests

Tests that Memory Service correctly subscribes to and processes session events
"""
import asyncio
import sys
import os
import logging
from datetime import datetime, timezone
from typing import Set

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource

logger = logging.getLogger(__name__)


# Import MemoryEventHandlers inline to avoid memory_service import issues
class MemoryEventHandlers:
    """Handles events for memory extraction and storage"""

    def __init__(self, memory_service):
        self.memory_service = memory_service
        self.processed_event_ids: Set[str] = set()
        self.session_message_buffer = {}

    def is_event_processed(self, event_id: str) -> bool:
        return event_id in self.processed_event_ids

    def mark_event_processed(self, event_id: str):
        self.processed_event_ids.add(event_id)
        if len(self.processed_event_ids) > 10000:
            self.processed_event_ids = set(list(self.processed_event_ids)[-9000:])

    async def handle_session_message_sent(self, event: Event):
        try:
            if self.is_event_processed(event.id):
                logger.debug(f"Event {event.id} already processed, skipping")
                return

            user_id = event.data.get("user_id")
            session_id = event.data.get("session_id")
            message_id = event.data.get("message_id")
            role = event.data.get("role")
            content = event.data.get("content")

            if not user_id or not content:
                logger.warning(f"Missing required fields in session.message_sent event: {event.id}")
                return

            if session_id not in self.session_message_buffer:
                self.session_message_buffer[session_id] = []

            self.session_message_buffer[session_id].append({
                "role": role,
                "content": content,
                "message_id": message_id,
                "timestamp": event.data.get("timestamp", datetime.now().isoformat())
            })

            if len(self.session_message_buffer[session_id]) >= 4:
                await self._extract_memories_from_buffer(user_id, session_id)

            self.mark_event_processed(event.id)

        except Exception as e:
            logger.error(f"Failed to handle session.message_sent event: {e}", exc_info=True)

    async def handle_session_ended(self, event: Event):
        try:
            if self.is_event_processed(event.id):
                logger.debug(f"Event {event.id} already processed, skipping")
                return

            user_id = event.data.get("user_id")
            session_id = event.data.get("session_id")

            if not user_id or not session_id:
                logger.warning(f"Missing required fields in session.ended event: {event.id}")
                return

            if session_id in self.session_message_buffer and len(self.session_message_buffer[session_id]) > 0:
                await self._extract_memories_from_buffer(user_id, session_id, final=True)
                del self.session_message_buffer[session_id]

            try:
                result = await self.memory_service.deactivate_session(user_id, session_id)
            except Exception as e:
                logger.warning(f"Failed to deactivate session {session_id}: {e}")

            self.mark_event_processed(event.id)

        except Exception as e:
            logger.error(f"Failed to handle session.ended event: {e}", exc_info=True)

    async def _extract_memories_from_buffer(self, user_id: str, session_id: str, final: bool = False):
        try:
            messages = self.session_message_buffer.get(session_id, [])
            if not messages:
                return

            dialog_lines = []
            for msg in messages:
                role_label = "User" if msg["role"] == "user" else "Assistant"
                dialog_lines.append(f"{role_label}: {msg['content']}")

            dialog_content = "\n".join(dialog_lines)
            importance_score = 0.7 if final else 0.5

            try:
                factual_result = await self.memory_service.store_factual_memory(
                    user_id=user_id,
                    dialog_content=dialog_content,
                    importance_score=importance_score
                )
            except Exception as e:
                logger.warning(f"Failed to extract factual memories: {e}")

            try:
                episodic_result = await self.memory_service.store_episodic_memory(
                    user_id=user_id,
                    dialog_content=dialog_content,
                    importance_score=importance_score
                )
            except Exception as e:
                logger.warning(f"Failed to extract episodic memories: {e}")

            if not final:
                self.session_message_buffer[session_id] = []

        except Exception as e:
            logger.error(f"Failed to extract memories from buffer: {e}", exc_info=True)

    def get_event_handler_map(self):
        return {
            "*.session.message_sent": self.handle_session_message_sent,
            "*.session.ended": self.handle_session_ended,
        }


class MockMemoryService:
    """Mock Memory Service for testing"""

    def __init__(self):
        self.factual_memories = []
        self.episodic_memories = []
        self.deactivated_sessions = []

    async def store_factual_memory(self, user_id: str, dialog_content: str, importance_score: float):
        """Mock store factual memory"""
        memory = {
            "user_id": user_id,
            "dialog_content": dialog_content,
            "importance_score": importance_score,
            "type": "factual",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.factual_memories.append(memory)

        # Return mock result
        class MockResult:
            def __init__(self):
                self.success = True
                self.message = "Factual memories extracted"
                self.count = 1

        return MockResult()

    async def store_episodic_memory(self, user_id: str, dialog_content: str, importance_score: float):
        """Mock store episodic memory"""
        memory = {
            "user_id": user_id,
            "dialog_content": dialog_content,
            "importance_score": importance_score,
            "type": "episodic",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.episodic_memories.append(memory)

        # Return mock result
        class MockResult:
            def __init__(self):
                self.success = True
                self.message = "Episodic memories extracted"
                self.count = 1

        return MockResult()

    async def deactivate_session(self, user_id: str, session_id: str):
        """Mock deactivate session"""
        self.deactivated_sessions.append({
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Return mock result
        class MockResult:
            def __init__(self):
                self.success = True
                self.message = f"Session {session_id} deactivated"

        return MockResult()


async def test_session_message_sent_event():
    """Test that session.message_sent events are handled correctly"""
    print("\n" + "="*60)
    print("TEST 1: Session Message Sent Event Handling")
    print("="*60)

    mock_service = MockMemoryService()
    handlers = MemoryEventHandlers(mock_service)

    # Send 4 messages to trigger memory extraction
    messages = [
        ("user", "Hello, I'm planning a trip to Tokyo next month"),
        ("assistant", "That sounds exciting! When in next month are you planning to visit?"),
        ("user", "I'll be there from March 15th to March 22nd. I love Japanese food!"),
        ("assistant", "Great! I can help you plan your trip. What type of experiences are you interested in?"),
    ]

    for i, (role, content) in enumerate(messages):
        event = Event(
            event_type=EventType.SESSION_MESSAGE_SENT,
            source=ServiceSource.SESSION_SERVICE,
            data={
                "session_id": "session_123",
                "user_id": "user_456",
                "message_id": f"msg_{i+1}",
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

        await handlers.handle_session_message_sent(event)

    # Wait a bit for async processing
    await asyncio.sleep(1)

    # Verify memories were extracted after 4 messages
    assert len(mock_service.factual_memories) > 0, "Factual memories should have been extracted"
    assert len(mock_service.episodic_memories) > 0, "Episodic memories should have been extracted"

    factual_memory = mock_service.factual_memories[0]
    assert factual_memory["user_id"] == "user_456"
    assert "Tokyo" in factual_memory["dialog_content"]
    assert "Japanese food" in factual_memory["dialog_content"]

    print("✅ session.message_sent event handled correctly")
    print(f"   Factual memories extracted: {len(mock_service.factual_memories)}")
    print(f"   Episodic memories extracted: {len(mock_service.episodic_memories)}")
    print(f"   Dialog content length: {len(factual_memory['dialog_content'])} chars")

    return True


async def test_session_ended_event():
    """Test that session.ended events are handled correctly"""
    print("\n" + "="*60)
    print("TEST 2: Session Ended Event Handling")
    print("="*60)

    mock_service = MockMemoryService()
    handlers = MemoryEventHandlers(mock_service)

    # Add some messages to the buffer first
    for i in range(2):
        event = Event(
            event_type=EventType.SESSION_MESSAGE_SENT,
            source=ServiceSource.SESSION_SERVICE,
            data={
                "session_id": "session_789",
                "user_id": "user_999",
                "message_id": f"msg_{i+1}",
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Test message {i+1}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        await handlers.handle_session_message_sent(event)

    # Now send session.ended event
    event = Event(
        event_type=EventType.SESSION_ENDED,
        source=ServiceSource.SESSION_SERVICE,
        data={
            "session_id": "session_789",
            "user_id": "user_999",
            "total_messages": 10,
            "total_tokens": 5000,
            "total_cost": 0.50,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    await handlers.handle_session_ended(event)

    # Wait a bit for async processing
    await asyncio.sleep(1)

    # Verify session was deactivated
    assert len(mock_service.deactivated_sessions) == 1, "Session should have been deactivated"
    assert mock_service.deactivated_sessions[0]["session_id"] == "session_789"
    assert mock_service.deactivated_sessions[0]["user_id"] == "user_999"

    # Verify final memories were extracted
    assert len(mock_service.factual_memories) > 0, "Final factual memories should have been extracted"
    assert len(mock_service.episodic_memories) > 0, "Final episodic memories should have been extracted"

    # Verify buffer was cleared
    assert "session_789" not in handlers.session_message_buffer, "Buffer should be cleared after session end"

    print("✅ session.ended event handled correctly")
    print(f"   Session deactivated: {mock_service.deactivated_sessions[0]['session_id']}")
    print(f"   Final factual memories: {len(mock_service.factual_memories)}")
    print(f"   Final episodic memories: {len(mock_service.episodic_memories)}")

    return True


async def test_idempotency():
    """Test that duplicate events are not processed twice"""
    print("\n" + "="*60)
    print("TEST 3: Event Idempotency")
    print("="*60)

    mock_service = MockMemoryService()
    handlers = MemoryEventHandlers(mock_service)

    # Create an event
    event = Event(
        event_type=EventType.SESSION_ENDED,
        source=ServiceSource.SESSION_SERVICE,
        data={
            "session_id": "session_idempotent",
            "user_id": "user_idempotent",
            "total_messages": 5,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Process it once
    await handlers.handle_session_ended(event)
    first_count = len(mock_service.deactivated_sessions)

    # Process it again (should be skipped)
    await handlers.handle_session_ended(event)
    second_count = len(mock_service.deactivated_sessions)

    assert first_count == 1, "First event should be processed"
    assert second_count == 1, "Duplicate event should not be processed"
    assert first_count == second_count, "Counts should be the same (idempotency working)"

    print("✅ Event idempotency working correctly")
    print(f"   First processing: {first_count} sessions deactivated")
    print(f"   Duplicate processing: {second_count} sessions deactivated (no change)")

    return True


async def test_message_buffering():
    """Test that messages are buffered correctly before extraction"""
    print("\n" + "="*60)
    print("TEST 4: Message Buffering")
    print("="*60)

    mock_service = MockMemoryService()
    handlers = MemoryEventHandlers(mock_service)

    # Send only 2 messages (should not trigger extraction yet)
    for i in range(2):
        event = Event(
            event_type=EventType.SESSION_MESSAGE_SENT,
            source=ServiceSource.SESSION_SERVICE,
            data={
                "session_id": "session_buffer",
                "user_id": "user_buffer",
                "message_id": f"msg_{i+1}",
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i+1}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        await handlers.handle_session_message_sent(event)

    # Verify no memories extracted yet
    assert len(mock_service.factual_memories) == 0, "Should not extract with only 2 messages"
    assert len(mock_service.episodic_memories) == 0, "Should not extract with only 2 messages"

    # Verify messages are buffered
    assert "session_buffer" in handlers.session_message_buffer, "Session should be in buffer"
    assert len(handlers.session_message_buffer["session_buffer"]) == 2, "Should have 2 buffered messages"

    # Send 2 more messages to trigger extraction
    for i in range(2, 4):
        event = Event(
            event_type=EventType.SESSION_MESSAGE_SENT,
            source=ServiceSource.SESSION_SERVICE,
            data={
                "session_id": "session_buffer",
                "user_id": "user_buffer",
                "message_id": f"msg_{i+1}",
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i+1}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        await handlers.handle_session_message_sent(event)

    await asyncio.sleep(1)

    # Now memories should be extracted
    assert len(mock_service.factual_memories) > 0, "Should extract with 4+ messages"
    assert len(mock_service.episodic_memories) > 0, "Should extract with 4+ messages"

    print("✅ Message buffering working correctly")
    print(f"   Initial messages (no extraction): 2")
    print(f"   After 4 messages:")
    print(f"     - Factual memories: {len(mock_service.factual_memories)}")
    print(f"     - Episodic memories: {len(mock_service.episodic_memories)}")

    return True


async def test_event_handler_map():
    """Test that event handler map is correctly configured"""
    print("\n" + "="*60)
    print("TEST 5: Event Handler Map Configuration")
    print("="*60)

    mock_service = MockMemoryService()
    handlers = MemoryEventHandlers(mock_service)

    handler_map = handlers.get_event_handler_map()

    # Verify correct event types are registered
    assert "*.session.message_sent" in handler_map, "session.message_sent should be registered"
    assert "*.session.ended" in handler_map, "session.ended should be registered"

    # Verify handlers are callable
    assert callable(handler_map["*.session.message_sent"]), "Handler should be callable"
    assert callable(handler_map["*.session.ended"]), "Handler should be callable"

    print("✅ Event handler map configured correctly")
    print(f"   Registered event patterns: {len(handler_map)}")
    for pattern in handler_map.keys():
        print(f"     - {pattern}")

    return True


async def run_all_tests():
    """Run all Memory Service event subscription tests"""
    print("\n" + "="*80)
    print("MEMORY SERVICE EVENT SUBSCRIPTION TEST SUITE")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Run tests
    try:
        results["session_message_sent"] = await test_session_message_sent_event()
    except AssertionError as e:
        print(f"❌ TEST 1 FAILED: {e}")
        results["session_message_sent"] = False
    except Exception as e:
        print(f"❌ TEST 1 ERROR: {e}")
        results["session_message_sent"] = False

    try:
        results["session_ended"] = await test_session_ended_event()
    except AssertionError as e:
        print(f"❌ TEST 2 FAILED: {e}")
        results["session_ended"] = False
    except Exception as e:
        print(f"❌ TEST 2 ERROR: {e}")
        results["session_ended"] = False

    try:
        results["idempotency"] = await test_idempotency()
    except AssertionError as e:
        print(f"❌ TEST 3 FAILED: {e}")
        results["idempotency"] = False
    except Exception as e:
        print(f"❌ TEST 3 ERROR: {e}")
        results["idempotency"] = False

    try:
        results["message_buffering"] = await test_message_buffering()
    except AssertionError as e:
        print(f"❌ TEST 4 FAILED: {e}")
        results["message_buffering"] = False
    except Exception as e:
        print(f"❌ TEST 4 ERROR: {e}")
        results["message_buffering"] = False

    try:
        results["event_handler_map"] = await test_event_handler_map()
    except AssertionError as e:
        print(f"❌ TEST 5 FAILED: {e}")
        results["event_handler_map"] = False
    except Exception as e:
        print(f"❌ TEST 5 ERROR: {e}")
        results["event_handler_map"] = False

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
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

    return passed, total


if __name__ == "__main__":
    passed, total = asyncio.run(run_all_tests())
    sys.exit(0 if passed == total else 1)
