"""
Session Service Client

Client library for other microservices to interact with session service
"""

import httpx
from core.service_discovery import get_service_discovery
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class SessionServiceClient:
    """Session Service HTTP client"""

    def __init__(self, base_url: str = None):
        """
        Initialize Session Service client

        Args:
            base_url: Session service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("session_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8207"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Session Management
    # =============================================================================

    async def create_session(
        self,
        user_id: str,
        session_type: str = "conversation",
        metadata: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create new session

        Args:
            user_id: User ID
            session_type: Session type (conversation, task, etc.)
            metadata: Session metadata (optional)
            context: Session context (optional)

        Returns:
            Created session

        Example:
            >>> client = SessionServiceClient()
            >>> session = await client.create_session(
            ...     user_id="user123",
            ...     session_type="conversation",
            ...     metadata={"platform": "web"}
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "session_type": session_type
            }

            if metadata:
                payload["metadata"] = metadata
            if context:
                payload["context"] = context

            response = await self.client.post(
                f"{self.base_url}/api/v1/sessions",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create session: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None

    async def get_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get session by ID

        Args:
            session_id: Session ID
            user_id: User ID for authorization (optional)

        Returns:
            Session details

        Example:
            >>> session = await client.get_session("sess123", "user456")
        """
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id

            response = await self.client.get(
                f"{self.base_url}/api/v1/sessions/{session_id}",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get session: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None

    async def update_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update session

        Args:
            session_id: Session ID
            user_id: User ID for authorization (optional)
            status: New status (optional)
            metadata: Updated metadata (optional)
            context: Updated context (optional)

        Returns:
            Updated session

        Example:
            >>> updated = await client.update_session(
            ...     session_id="sess123",
            ...     status="completed",
            ...     metadata={"result": "success"}
            ... )
        """
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id

            payload = {}
            if status:
                payload["status"] = status
            if metadata:
                payload["metadata"] = metadata
            if context:
                payload["context"] = context

            response = await self.client.put(
                f"{self.base_url}/api/v1/sessions/{session_id}",
                json=payload,
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update session: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error updating session: {e}")
            return None

    async def delete_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        End/delete session

        Args:
            session_id: Session ID
            user_id: User ID for authorization (optional)

        Returns:
            True if successful

        Example:
            >>> success = await client.delete_session("sess123", "user456")
        """
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id

            response = await self.client.delete(
                f"{self.base_url}/api/v1/sessions/{session_id}",
                params=params
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete session: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False

    async def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = False,
        page: int = 1,
        page_size: int = 50
    ) -> Optional[Dict[str, Any]]:
        """
        Get user sessions

        Args:
            user_id: User ID
            active_only: Only return active sessions (default: False)
            page: Page number (default: 1)
            page_size: Items per page (default: 50)

        Returns:
            List of sessions with pagination

        Example:
            >>> sessions = await client.get_user_sessions("user123", active_only=True)
        """
        try:
            params = {
                "active_only": active_only,
                "page": page,
                "page_size": page_size
            }

            response = await self.client.get(
                f"{self.base_url}/api/v1/users/{user_id}/sessions",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get user sessions: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return None

    async def get_session_summary(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get session summary

        Args:
            session_id: Session ID
            user_id: User ID for authorization (optional)

        Returns:
            Session summary

        Example:
            >>> summary = await client.get_session_summary("sess123", "user456")
        """
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id

            response = await self.client.get(
                f"{self.base_url}/api/v1/sessions/{session_id}/summary",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get session summary: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting session summary: {e}")
            return None

    # =============================================================================
    # Message Management
    # =============================================================================

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Add message to session

        Args:
            session_id: Session ID
            role: Message role (user, assistant, system)
            content: Message content
            user_id: User ID for authorization (optional)
            metadata: Message metadata (optional)

        Returns:
            Created message

        Example:
            >>> message = await client.add_message(
            ...     session_id="sess123",
            ...     role="user",
            ...     content="Hello!",
            ...     user_id="user456"
            ... )
        """
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id

            payload = {
                "role": role,
                "content": content
            }

            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/sessions/{session_id}/messages",
                json=payload,
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to add message: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return None

    async def get_messages(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        Get session messages

        Args:
            session_id: Session ID
            user_id: User ID for authorization (optional)
            page: Page number (default: 1)
            page_size: Items per page (default: 100)

        Returns:
            List of messages with pagination

        Example:
            >>> messages = await client.get_messages("sess123", "user456")
        """
        try:
            params = {
                "page": page,
                "page_size": page_size
            }
            if user_id:
                params["user_id"] = user_id

            response = await self.client.get(
                f"{self.base_url}/api/v1/sessions/{session_id}/messages",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get messages: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return None

    # =============================================================================
    # Memory Management
    # =============================================================================

    async def save_memory(
        self,
        session_id: str,
        memory_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Save session memory

        Args:
            session_id: Session ID
            memory_data: Memory data to save
            user_id: User ID for authorization (optional)

        Returns:
            Saved memory

        Example:
            >>> memory = await client.save_memory(
            ...     session_id="sess123",
            ...     memory_data={"key": "value"},
            ...     user_id="user456"
            ... )
        """
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id

            response = await self.client.post(
                f"{self.base_url}/api/v1/sessions/{session_id}/memory",
                json=memory_data,
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to save memory: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
            return None

    async def get_memory(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get session memory

        Args:
            session_id: Session ID
            user_id: User ID for authorization (optional)

        Returns:
            Session memory

        Example:
            >>> memory = await client.get_memory("sess123", "user456")
        """
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id

            response = await self.client.get(
                f"{self.base_url}/api/v1/sessions/{session_id}/memory",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get memory: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting memory: {e}")
            return None

    # =============================================================================
    # Statistics
    # =============================================================================

    async def get_session_stats(
        self
    ) -> Optional[Dict[str, Any]]:
        """
        Get session service statistics

        Returns:
            Session statistics

        Example:
            >>> stats = await client.get_session_stats()
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/sessions/stats"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get session stats: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return None

    # =============================================================================
    # Health Check
    # =============================================================================

    async def health_check(self) -> bool:
        """
        Check service health status

        Returns:
            True if service is healthy
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False


__all__ = ["SessionServiceClient"]
