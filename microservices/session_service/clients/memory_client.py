"""
Memory Service Client

Client for session_service to interact with memory_service.
Used for retrieving and storing session memories.
"""

import os
import sys
from typing import Optional, Dict, Any, List

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from microservices.memory_service.client import MemoryServiceClient


class MemoryClient:
    """
    Wrapper client for Memory Service calls from Session Service.

    This wrapper provides session-specific convenience methods
    while delegating to the actual MemoryServiceClient.
    """

    def __init__(self, base_url: str = None, api_key: str = None):
        """
        Initialize Memory Service client

        Args:
            base_url: Memory service base URL (optional, defaults to localhost:8223)
            api_key: Optional API key for authentication
        """
        self._client = MemoryServiceClient(
            base_url=base_url or "http://localhost:8223",
            api_key=api_key
        )

    async def close(self):
        """Close HTTP client (no-op for MemoryServiceClient as it uses context managers)"""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Session-specific convenience methods
    # =============================================================================

    async def get_session_context(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """
        Get relevant memories for session context.

        Retrieves recent memories to provide context for the session.

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            Dict with session memories and relevant context
        """
        try:
            # Get session-specific memories
            session_memories = await self._client.get_session_memories(
                session_id=session_id,
                user_id=user_id
            )

            # Get active working memories
            working_memories = await self._client.get_active_working_memories(user_id)

            return {
                "session_memories": session_memories.get("memories", []) if session_memories else [],
                "working_memories": working_memories.get("memories", []) if working_memories else [],
                "session_id": session_id
            }
        except Exception:
            return {
                "session_memories": [],
                "working_memories": [],
                "session_id": session_id
            }

    async def save_session_memory(
        self,
        user_id: str,
        session_id: str,
        content: str,
        memory_type: str = "session",
        importance: float = 0.5
    ) -> bool:
        """
        Save a memory from the current session.

        Args:
            user_id: User ID
            session_id: Session ID
            content: Memory content
            memory_type: Type of memory (session, factual, episodic)
            importance: Importance score (0-1)

        Returns:
            True if saved successfully
        """
        try:
            from microservices.memory_service.models import MemoryCreateRequest, MemoryType

            request = MemoryCreateRequest(
                user_id=user_id,
                memory_type=MemoryType(memory_type),
                content=content,
                importance_score=importance,
                metadata={"session_id": session_id}
            )

            result = await self._client.create_memory(request)
            return result is not None and result.success
        except Exception:
            return False

    async def extract_memories_from_dialog(
        self,
        user_id: str,
        dialog_content: str,
        importance: float = 0.5
    ) -> Dict[str, Any]:
        """
        Extract and store memories from dialog using AI.

        Args:
            user_id: User ID
            dialog_content: Dialog text to extract memories from
            importance: Importance score

        Returns:
            Dict with extraction results
        """
        results = {}

        try:
            # Extract factual memories
            factual = await self._client.extract_factual_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                importance_score=importance
            )
            results["factual"] = factual
        except Exception:
            results["factual"] = None

        try:
            # Extract episodic memories
            episodic = await self._client.extract_episodic_memory(
                user_id=user_id,
                dialog_content=dialog_content,
                importance_score=importance
            )
            results["episodic"] = episodic
        except Exception:
            results["episodic"] = None

        return results

    async def end_session_memories(self, user_id: str, session_id: str) -> bool:
        """
        Mark session as ended and deactivate session memories.

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            True if successful
        """
        try:
            result = await self._client.deactivate_session(
                session_id=session_id,
                user_id=user_id
            )
            return result is not None and result.success
        except Exception:
            return False

    async def get_user_memory_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get memory statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Memory statistics or None
        """
        try:
            return await self._client.get_memory_statistics(user_id)
        except Exception:
            return None

    # =============================================================================
    # Direct delegation to MemoryServiceClient
    # =============================================================================

    async def list_memories(
        self,
        user_id: str,
        memory_type: Optional[str] = None,
        limit: int = 50
    ):
        """List user memories"""
        return await self._client.list_memories(
            user_id=user_id,
            memory_type=memory_type,
            limit=limit
        )

    async def health_check(self) -> bool:
        """Check Memory Service health"""
        try:
            result = await self._client.health_check()
            return result is not None
        except Exception:
            return False


__all__ = ["MemoryClient"]
