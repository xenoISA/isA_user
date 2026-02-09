"""
Session Service - Mock Dependencies

Mock implementations for component testing.
These mocks simulate repository and external service behavior.
"""
from unittest.mock import AsyncMock, MagicMock
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid


class MockSessionRepository:
    """Mock session repository for component testing"""

    def __init__(self):
        self._sessions: Dict[str, Dict] = {}
        self.create_session = AsyncMock(side_effect=self._create_session)
        self.get_by_session_id = AsyncMock(side_effect=self._get_by_session_id)
        self.get_user_sessions = AsyncMock(side_effect=self._get_user_sessions)
        self.update_session_status = AsyncMock(side_effect=self._update_session_status)
        self.update_session_activity = AsyncMock(side_effect=self._update_session_activity)
        self.increment_message_count = AsyncMock(side_effect=self._increment_message_count)
        self.expire_old_sessions = AsyncMock(return_value=0)

    async def _create_session(self, session_data: Dict[str, Any]) -> Any:
        """Mock session creation"""
        session_id = session_data.get("session_id", f"sess_{uuid.uuid4().hex[:24]}")
        now = datetime.now(timezone.utc)

        session = MagicMock()
        session.session_id = session_id
        session.user_id = session_data.get("user_id")
        session.status = session_data.get("status", "active")
        session.conversation_data = session_data.get("conversation_data", {})
        session.metadata = session_data.get("metadata", {})
        session.is_active = session_data.get("is_active", True)
        session.message_count = 0
        session.total_tokens = 0
        session.total_cost = 0.0
        session.session_summary = ""
        session.created_at = now
        session.updated_at = now
        session.last_activity = now

        self._sessions[session_id] = {
            "session_id": session_id,
            "user_id": session.user_id,
            "status": session.status,
            "conversation_data": session.conversation_data,
            "metadata": session.metadata,
            "is_active": session.is_active,
            "message_count": session.message_count,
            "total_tokens": session.total_tokens,
            "total_cost": session.total_cost,
            "session_summary": session.session_summary,
            "created_at": now,
            "updated_at": now,
            "last_activity": now,
        }

        return session

    async def _get_by_session_id(self, session_id: str) -> Optional[Any]:
        """Mock session retrieval"""
        data = self._sessions.get(session_id)
        if data is None:
            return None

        session = MagicMock()
        for key, value in data.items():
            setattr(session, key, value)
        return session

    async def _get_user_sessions(
        self,
        user_id: str,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Any]:
        """Mock user sessions retrieval"""
        sessions = []
        for session_id, data in self._sessions.items():
            if data["user_id"] == user_id:
                if active_only and not data["is_active"]:
                    continue
                session = MagicMock()
                for key, value in data.items():
                    setattr(session, key, value)
                sessions.append(session)

        # Sort by created_at DESC
        sessions.sort(key=lambda s: s.created_at, reverse=True)

        # Apply pagination
        return sessions[offset:offset + limit]

    async def _update_session_status(self, session_id: str, status: str) -> bool:
        """Mock session status update"""
        if session_id not in self._sessions:
            return False

        self._sessions[session_id]["status"] = status
        self._sessions[session_id]["updated_at"] = datetime.now(timezone.utc)

        if status == "ended":
            self._sessions[session_id]["is_active"] = False

        return True

    async def _update_session_activity(self, session_id: str) -> bool:
        """Mock session activity update"""
        if session_id not in self._sessions:
            return False

        now = datetime.now(timezone.utc)
        self._sessions[session_id]["last_activity"] = now
        self._sessions[session_id]["updated_at"] = now
        return True

    async def _increment_message_count(
        self,
        session_id: str,
        tokens_used: int = 0,
        cost_usd: float = 0.0
    ) -> bool:
        """Mock message count increment"""
        if session_id not in self._sessions:
            return False

        now = datetime.now(timezone.utc)
        self._sessions[session_id]["message_count"] += 1
        self._sessions[session_id]["total_tokens"] += tokens_used
        self._sessions[session_id]["total_cost"] += cost_usd
        self._sessions[session_id]["last_activity"] = now
        self._sessions[session_id]["updated_at"] = now
        return True

    def reset(self):
        """Reset mock state"""
        self._sessions.clear()


class MockSessionMessageRepository:
    """Mock session message repository for component testing"""

    def __init__(self):
        self._messages: Dict[str, Dict] = {}
        self._message_by_session: Dict[str, List[str]] = {}
        self.create_message = AsyncMock(side_effect=self._create_message)
        self.get_session_messages = AsyncMock(side_effect=self._get_session_messages)

    async def _create_message(self, message_data: Dict[str, Any]) -> Any:
        """Mock message creation"""
        message_id = f"msg_{uuid.uuid4().hex[:24]}"
        now = datetime.now(timezone.utc)

        message = MagicMock()
        message.message_id = message_id
        message.session_id = message_data.get("session_id")
        message.user_id = message_data.get("user_id")
        message.role = message_data.get("role")
        message.content = message_data.get("content")
        message.message_type = message_data.get("message_type", "chat")
        message.metadata = message_data.get("metadata", {})
        message.tokens_used = message_data.get("tokens_used", 0)
        message.cost_usd = message_data.get("cost_usd", 0.0)
        message.created_at = now

        self._messages[message_id] = {
            "message_id": message_id,
            "session_id": message.session_id,
            "user_id": message.user_id,
            "role": message.role,
            "content": message.content,
            "message_type": message.message_type,
            "metadata": message.metadata,
            "tokens_used": message.tokens_used,
            "cost_usd": message.cost_usd,
            "created_at": now,
        }

        # Track by session
        if message.session_id not in self._message_by_session:
            self._message_by_session[message.session_id] = []
        self._message_by_session[message.session_id].append(message_id)

        return message

    async def _get_session_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Any]:
        """Mock message retrieval for session"""
        message_ids = self._message_by_session.get(session_id, [])
        messages = []

        for msg_id in message_ids:
            data = self._messages.get(msg_id)
            if data:
                message = MagicMock()
                for key, value in data.items():
                    setattr(message, key, value)
                messages.append(message)

        # Sort by created_at ASC
        messages.sort(key=lambda m: m.created_at)

        # Apply pagination
        return messages[offset:offset + limit]

    def reset(self):
        """Reset mock state"""
        self._messages.clear()
        self._message_by_session.clear()


class MockEventBus:
    """Mock NATS event bus for component testing"""

    def __init__(self):
        self.published_events: List[Any] = []
        self.publish_event = AsyncMock(side_effect=self._publish_event)

    async def _publish_event(self, event: Any) -> None:
        """Mock event publishing"""
        self.published_events.append(event)

    def get_published_events(self) -> List[Any]:
        """Get all published events"""
        return self.published_events

    def get_events_by_type(self, event_type: str) -> List[Any]:
        """Get published events by type"""
        result = []
        for e in self.published_events:
            # Event objects from nats_client use 'type' attribute, not 'event_type'
            if hasattr(e, 'type'):
                if str(e.type) == event_type or str(e.type.value) == event_type:
                    result.append(e)
            elif hasattr(e, 'event_type'):
                if str(e.event_type) == event_type:
                    result.append(e)
        return result

    def reset(self):
        """Reset mock state"""
        self.published_events.clear()


class MockAccountClient:
    """Mock account service client for component testing"""

    def __init__(self):
        self._accounts: Dict[str, Dict] = {}
        self.get_account_profile = AsyncMock(side_effect=self._get_account_profile)

    async def _get_account_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Mock account profile retrieval"""
        return self._accounts.get(user_id)

    def add_account(self, user_id: str, profile: Optional[Dict[str, Any]] = None):
        """Add account to mock"""
        self._accounts[user_id] = profile or {
            "user_id": user_id,
            "email": f"{user_id}@example.com",
            "name": f"User {user_id}",
            "is_active": True,
        }

    def reset(self):
        """Reset mock state"""
        self._accounts.clear()
