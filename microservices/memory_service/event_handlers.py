"""
Memory Service Event Handlers

Subscribes to session events to automatically extract and store memories from AI conversations
"""
import logging
from typing import Set
from datetime import datetime

from core.nats_client import Event

logger = logging.getLogger(__name__)


class MemoryEventHandlers:
    """Handles events for memory extraction and storage"""

    def __init__(self, memory_service):
        self.memory_service = memory_service
        self.processed_event_ids: Set[str] = set()
        self.session_message_buffer = {}  # Buffer messages per session for batch processing

    def is_event_processed(self, event_id: str) -> bool:
        """Check if event has been processed (idempotency)"""
        return event_id in self.processed_event_ids

    def mark_event_processed(self, event_id: str):
        """Mark event as processed"""
        self.processed_event_ids.add(event_id)
        # Keep only last 10000 event IDs to prevent memory growth
        if len(self.processed_event_ids) > 10000:
            # Remove oldest 1000 entries
            self.processed_event_ids = set(list(self.processed_event_ids)[-9000:])

    async def handle_session_message_sent(self, event: Event):
        """
        Handle session.message_sent event

        Automatically extract memories from AI conversation messages
        """
        try:
            # Check idempotency
            if self.is_event_processed(event.id):
                logger.debug(f"Event {event.id} already processed, skipping")
                return

            user_id = event.data.get("user_id")
            session_id = event.data.get("session_id")
            message_id = event.data.get("message_id")
            role = event.data.get("role")  # 'user' or 'assistant'
            content = event.data.get("content")

            if not user_id or not content:
                logger.warning(f"Missing required fields in session.message_sent event: {event.id}")
                return

            # Buffer messages for this session
            if session_id not in self.session_message_buffer:
                self.session_message_buffer[session_id] = []

            self.session_message_buffer[session_id].append({
                "role": role,
                "content": content,
                "message_id": message_id,
                "timestamp": event.data.get("timestamp", datetime.now().isoformat())
            })

            logger.info(f"Buffered message {message_id} for session {session_id} (total: {len(self.session_message_buffer[session_id])})")

            # If we have at least 4 messages (2 exchanges), try to extract memories
            if len(self.session_message_buffer[session_id]) >= 4:
                await self._extract_memories_from_buffer(user_id, session_id)

            self.mark_event_processed(event.id)

        except Exception as e:
            logger.error(f"Failed to handle session.message_sent event: {e}", exc_info=True)

    async def handle_session_ended(self, event: Event):
        """
        Handle session.ended event

        Extract and store memories from completed session
        """
        try:
            # Check idempotency
            if self.is_event_processed(event.id):
                logger.debug(f"Event {event.id} already processed, skipping")
                return

            user_id = event.data.get("user_id")
            session_id = event.data.get("session_id")
            total_messages = event.data.get("total_messages", 0)

            if not user_id or not session_id:
                logger.warning(f"Missing required fields in session.ended event: {event.id}")
                return

            logger.info(f"Processing session end for session {session_id}: {total_messages} messages")

            # Extract memories from any remaining buffered messages
            if session_id in self.session_message_buffer and len(self.session_message_buffer[session_id]) > 0:
                await self._extract_memories_from_buffer(user_id, session_id, final=True)

                # Clear buffer for this session
                del self.session_message_buffer[session_id]

            # Deactivate session in memory system
            try:
                result = await self.memory_service.deactivate_session(user_id, session_id)
                logger.info(f"Deactivated session {session_id}: {result.message}")
            except Exception as e:
                logger.warning(f"Failed to deactivate session {session_id}: {e}")

            self.mark_event_processed(event.id)

        except Exception as e:
            logger.error(f"Failed to handle session.ended event: {e}", exc_info=True)

    async def _extract_memories_from_buffer(self, user_id: str, session_id: str, final: bool = False):
        """Extract memories from buffered messages"""
        try:
            messages = self.session_message_buffer.get(session_id, [])
            if not messages:
                return

            # Build dialog content from messages
            dialog_lines = []
            for msg in messages:
                role_label = "User" if msg["role"] == "user" else "Assistant"
                dialog_lines.append(f"{role_label}: {msg['content']}")

            dialog_content = "\n".join(dialog_lines)

            logger.info(f"Extracting memories from {len(messages)} messages for session {session_id}")

            # Extract different types of memories in parallel
            # We use importance_score based on whether this is the final extraction
            importance_score = 0.7 if final else 0.5

            try:
                # Extract factual memories (facts about the user, preferences, etc.)
                factual_result = await self.memory_service.store_factual_memory(
                    user_id=user_id,
                    dialog_content=dialog_content,
                    importance_score=importance_score
                )
                logger.info(f"Extracted {factual_result.count} factual memories for session {session_id}")
            except Exception as e:
                logger.warning(f"Failed to extract factual memories: {e}")

            try:
                # Extract episodic memories (specific events and experiences)
                episodic_result = await self.memory_service.store_episodic_memory(
                    user_id=user_id,
                    dialog_content=dialog_content,
                    importance_score=importance_score
                )
                logger.info(f"Extracted {episodic_result.count} episodic memories for session {session_id}")
            except Exception as e:
                logger.warning(f"Failed to extract episodic memories: {e}")

            # Clear buffer after extraction (unless this is the final extraction)
            if not final:
                self.session_message_buffer[session_id] = []

        except Exception as e:
            logger.error(f"Failed to extract memories from buffer: {e}", exc_info=True)

    def get_event_handler_map(self):
        """Return mapping of event patterns to handler functions"""
        return {
            "*.session.message_sent": self.handle_session_message_sent,
            "*.session.ended": self.handle_session_ended,
        }
