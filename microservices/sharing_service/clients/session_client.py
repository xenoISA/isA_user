"""
Session Service Client

HTTP client for communicating with session_service.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

SESSION_SERVICE_URL = os.getenv("SESSION_SERVICE_URL", "http://localhost:8203")


class SessionServiceClient:
    """Client for session_service API"""

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session details from session_service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{SESSION_SERVICE_URL}/api/v1/sessions/{session_id}",
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return response.json()
                if response.status_code == 404:
                    return None
                logger.error(
                    f"Session service returned {response.status_code}: {response.text}"
                )
                return None
        except httpx.ConnectError:
            logger.error("Session service unavailable")
            return None
        except Exception as e:
            logger.error(f"Error fetching session {session_id}: {e}")
            return None

    async def get_session_messages(
        self, session_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get session messages from session_service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{SESSION_SERVICE_URL}/api/v1/sessions/{session_id}/messages",
                    params={"page_size": limit},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("messages", [])
                return []
        except Exception as e:
            logger.error(f"Error fetching messages for session {session_id}: {e}")
            return []

    async def check_user_exists(self, user_id: str) -> bool:
        """Check if user exists (not used currently, placeholder)"""
        return True
