"""
Session Service Client Example

Professional client for session management operations with caching and performance optimizations.
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SessionData:
    """Session data"""
    session_id: str
    user_id: str
    status: str
    conversation_data: Dict[str, Any]
    metadata: Dict[str, Any]
    is_active: bool
    message_count: int
    total_tokens: int
    total_cost: float
    created_at: str
    last_activity: str


@dataclass
class MessageData:
    """Message data"""
    message_id: str
    session_id: str
    user_id: str
    role: str
    content: str
    message_type: str
    tokens_used: int
    cost_usd: float
    created_at: str


class SessionClient:
    """Professional Session Service Client"""

    def __init__(
        self,
        base_url: str = "http://localhost:8203",
        timeout: float = 10.0,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.client: Optional[httpx.AsyncClient] = None
        self.request_count = 0
        self.error_count = 0

    async def __aenter__(self):
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=60.0
        )
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            limits=limits,
            headers={
                "User-Agent": "session-client/1.0",
                "Accept": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                self.request_count += 1
                response = await self.client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                last_exception = e
                if 400 <= e.response.status_code < 500:
                    self.error_count += 1
                    try:
                        error_detail = e.response.json()
                        raise Exception(error_detail.get("detail", str(e)))
                    except:
                        raise Exception(str(e))
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.2 * (2 ** attempt))
            except Exception as e:
                last_exception = e
                self.error_count += 1
                raise
        self.error_count += 1
        raise Exception(f"Request failed after {self.max_retries} attempts: {last_exception}")

    async def create_session(
        self,
        user_id: str,
        conversation_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionData:
        """Create new session"""
        result = await self._make_request(
            "POST",
            "/api/v1/sessions",
            json={
                "user_id": user_id,
                "conversation_data": conversation_data or {},
                "metadata": metadata or {}
            }
        )
        return SessionData(**result)

    async def get_session(self, session_id: str, user_id: Optional[str] = None) -> SessionData:
        """Get session by ID"""
        params = {"user_id": user_id} if user_id else {}
        result = await self._make_request(
            "GET",
            f"/api/v1/sessions/{session_id}",
            params=params
        )
        return SessionData(**result)

    async def update_session(
        self,
        session_id: str,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> SessionData:
        """Update session"""
        payload = {}
        if status:
            payload["status"] = status
        if metadata:
            payload["metadata"] = metadata

        params = {"user_id": user_id} if user_id else {}
        result = await self._make_request(
            "PUT",
            f"/api/v1/sessions/{session_id}",
            json=payload,
            params=params
        )
        return SessionData(**result)

    async def end_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        """End session"""
        params = {"user_id": user_id} if user_id else {}
        result = await self._make_request(
            "DELETE",
            f"/api/v1/sessions/{session_id}",
            params=params
        )
        return "successfully" in result.get("message", "")

    async def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = False,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """Get user sessions"""
        result = await self._make_request(
            "GET",
            f"/api/v1/users/{user_id}/sessions",
            params={
                "active_only": active_only,
                "page": page,
                "page_size": page_size
            }
        )
        return result

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        message_type: str = "chat",
        metadata: Optional[Dict[str, Any]] = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        user_id: Optional[str] = None
    ) -> MessageData:
        """Add message to session"""
        params = {"user_id": user_id} if user_id else {}
        result = await self._make_request(
            "POST",
            f"/api/v1/sessions/{session_id}/messages",
            json={
                "role": role,
                "content": content,
                "message_type": message_type,
                "metadata": metadata or {},
                "tokens_used": tokens_used,
                "cost_usd": cost_usd
            },
            params=params
        )
        return MessageData(**result)

    async def get_session_messages(
        self,
        session_id: str,
        page: int = 1,
        page_size: int = 100,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get session messages"""
        params = {
            "page": page,
            "page_size": page_size
        }
        if user_id:
            params["user_id"] = user_id

        result = await self._make_request(
            "GET",
            f"/api/v1/sessions/{session_id}/messages",
            params=params
        )
        return result

    async def create_session_memory(
        self,
        session_id: str,
        content: str,
        memory_type: str = "conversation",
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create session memory"""
        params = {"user_id": user_id} if user_id else {}
        result = await self._make_request(
            "POST",
            f"/api/v1/sessions/{session_id}/memory",
            json={
                "memory_type": memory_type,
                "content": content,
                "metadata": metadata or {}
            },
            params=params
        )
        return result

    async def get_session_memory(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get session memory"""
        params = {"user_id": user_id} if user_id else {}
        try:
            result = await self._make_request(
                "GET",
                f"/api/v1/sessions/{session_id}/memory",
                params=params
            )
            return result
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            raise

    async def get_session_summary(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get session summary with metrics"""
        params = {"user_id": user_id} if user_id else {}
        result = await self._make_request(
            "GET",
            f"/api/v1/sessions/{session_id}/summary",
            params=params
        )
        return result

    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return await self._make_request("GET", "/api/v1/sessions/stats")

    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        return await self._make_request("GET", "/health")

    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics"""
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0
        }


# Example Usage
async def main():
    print("=" * 70)
    print("Session Service Client Examples")
    print("=" * 70)

    async with SessionClient() as client:
        # Example 1: Health Check
        print("\n1. Health Check")
        print("-" * 70)
        health = await client.health_check()
        print(f"✓ Service: {health['service']}")
        print(f"  Status: {health['status']}")
        print(f"  Port: {health['port']}")

        # Example 2: Create Session
        print("\n2. Create Session")
        print("-" * 70)
        session = await client.create_session(
            user_id=f"example_user_{int(datetime.now().timestamp())}",
            conversation_data={"topic": "client_example"},
            metadata={"source": "python_client"}
        )
        print(f"✓ Session created: {session.session_id}")
        print(f"  User: {session.user_id}")
        print(f"  Status: {session.status}")

        # Example 3: Add User Message
        print("\n3. Add User Message")
        print("-" * 70)
        user_msg = await client.add_message(
            session_id=session.session_id,
            role="user",
            content="Hello! Can you help me with session management?",
            tokens_used=10,
            cost_usd=0.0001
        )
        print(f"✓ User message added: {user_msg.message_id}")
        print(f"  Content: {user_msg.content[:50]}...")

        # Example 4: Add Assistant Message
        print("\n4. Add Assistant Message")
        print("-" * 70)
        assistant_msg = await client.add_message(
            session_id=session.session_id,
            role="assistant",
            content="Of course! I'd be happy to help you with session management.",
            tokens_used=15,
            cost_usd=0.00015
        )
        print(f"✓ Assistant message added: {assistant_msg.message_id}")
        print(f"  Content: {assistant_msg.content[:50]}...")

        # Example 5: Get Session Messages
        print("\n5. Get Session Messages")
        print("-" * 70)
        messages_result = await client.get_session_messages(session.session_id)
        print(f"✓ Retrieved {messages_result['total']} messages")
        for msg in messages_result['messages']:
            print(f"  [{msg['role']}]: {msg['content'][:40]}...")

        # Example 6: Create Session Memory
        print("\n6. Create Session Memory")
        print("-" * 70)
        memory = await client.create_session_memory(
            session_id=session.session_id,
            content="User is learning about session management in microservices",
            memory_type="conversation",
            metadata={"key_topics": ["sessions", "microservices"]}
        )
        print(f"✓ Memory created: {memory['memory_id']}")
        print(f"  Content: {memory['content'][:50]}...")

        # Example 7: Get Session Summary
        print("\n7. Get Session Summary")
        print("-" * 70)
        summary = await client.get_session_summary(session.session_id)
        print(f"✓ Session Summary:")
        print(f"  Messages: {summary['message_count']}")
        print(f"  Total tokens: {summary['total_tokens']}")
        print(f"  Total cost: ${summary['total_cost']:.6f}")
        print(f"  Has memory: {summary['has_memory']}")

        # Example 8: Update Session Status
        print("\n8. Update Session Status")
        print("-" * 70)
        updated = await client.update_session(
            session_id=session.session_id,
            status="completed",
            metadata={"completion_reason": "example_finished"}
        )
        print(f"✓ Session updated to: {updated.status}")

        # Example 9: Get User Sessions
        print("\n9. Get User Sessions")
        print("-" * 70)
        user_sessions = await client.get_user_sessions(session.user_id, page_size=5)
        print(f"✓ Total sessions: {user_sessions['total']}")
        print(f"  Showing {len(user_sessions['sessions'])} sessions")

        # Example 10: Get Service Statistics
        print("\n10. Service Statistics")
        print("-" * 70)
        stats = await client.get_service_stats()
        print(f"✓ Total sessions: {stats['total_sessions']}")
        print(f"  Active: {stats['active_sessions']}")
        print(f"  Total messages: {stats['total_messages']}")

        # Example 11: End Session
        print("\n11. End Session")
        print("-" * 70)
        ended = await client.end_session(session.session_id)
        print(f"✓ Session ended: {ended}")

        # Show Client Metrics
        print("\n12. Client Performance Metrics")
        print("-" * 70)
        metrics = client.get_metrics()
        print(f"Total requests: {metrics['total_requests']}")
        print(f"Total errors: {metrics['total_errors']}")
        print(f"Error rate: {metrics['error_rate']:.2%}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
