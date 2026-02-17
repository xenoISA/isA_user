"""
Memory Service HTTP Client

Provides a Python client for interacting with the Memory Service API.
Supports all memory types: factual, procedural, episodic, semantic, working, session.
"""

import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime

from .models import (
    MemoryType, MemoryOperationResult,
    MemoryCreateRequest, MemoryUpdateRequest, MemoryListParams
)


class MemoryServiceClient:
    """HTTP client for Memory Service"""

    def __init__(
        self,
        base_url: str = "http://localhost:8223",
        timeout: float = 30.0,
        api_key: Optional[str] = None
    ):
        """
        Initialize Memory Service client

        Args:
            base_url: Base URL of the memory service
            timeout: Request timeout in seconds
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    # ==================== AI-Powered Memory Extraction ====================

    async def extract_factual_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """
        Extract and store factual memories from dialog using AI

        Args:
            user_id: User ID
            dialog_content: Dialog text to extract facts from
            importance_score: Importance score (0-1)

        Returns:
            MemoryOperationResult with operation status
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/memories/factual/extract",
                json={
                    "user_id": user_id,
                    "dialog_content": dialog_content,
                    "importance_score": importance_score
                },
                headers=self.headers
            )
            response.raise_for_status()
            return MemoryOperationResult(**response.json())

    async def extract_episodic_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """Extract and store episodic memories from dialog using AI"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/memories/episodic/extract",
                json={
                    "user_id": user_id,
                    "dialog_content": dialog_content,
                    "importance_score": importance_score
                },
                headers=self.headers
            )
            response.raise_for_status()
            return MemoryOperationResult(**response.json())

    async def extract_procedural_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """Extract and store procedural memories from dialog using AI"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/memories/procedural/extract",
                json={
                    "user_id": user_id,
                    "dialog_content": dialog_content,
                    "importance_score": importance_score
                },
                headers=self.headers
            )
            response.raise_for_status()
            return MemoryOperationResult(**response.json())

    async def extract_semantic_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """Extract and store semantic memories from dialog using AI"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/memories/semantic/extract",
                json={
                    "user_id": user_id,
                    "dialog_content": dialog_content,
                    "importance_score": importance_score
                },
                headers=self.headers
            )
            response.raise_for_status()
            return MemoryOperationResult(**response.json())

    # ==================== CRUD Operations ====================

    async def create_memory(
        self,
        request: MemoryCreateRequest
    ) -> MemoryOperationResult:
        """
        Create a new memory

        Args:
            request: Memory creation request

        Returns:
            MemoryOperationResult with created memory ID
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/memories",
                json=request.model_dump(),
                headers=self.headers
            )
            response.raise_for_status()
            return MemoryOperationResult(**response.json())

    async def get_memory(
        self,
        memory_type: MemoryType,
        memory_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get memory by ID and type

        Args:
            memory_type: Type of memory
            memory_id: Memory ID
            user_id: Optional user ID for validation

        Returns:
            Memory data as dictionary
        """
        params = {}
        if user_id:
            params["user_id"] = user_id

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/memories/{memory_type}/{memory_id}",
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def list_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 50,
        offset: int = 0,
        importance_min: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        List memories for a user

        Args:
            user_id: User ID
            memory_type: Optional memory type filter
            limit: Maximum number of results (1-100)
            offset: Offset for pagination
            importance_min: Minimum importance score filter

        Returns:
            Dictionary with memories and count
        """
        params = {
            "user_id": user_id,
            "limit": limit,
            "offset": offset
        }
        if memory_type:
            params["memory_type"] = memory_type
        if importance_min is not None:
            params["importance_min"] = importance_min

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/memories",
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def update_memory(
        self,
        memory_type: MemoryType,
        memory_id: str,
        request: MemoryUpdateRequest,
        user_id: str
    ) -> MemoryOperationResult:
        """
        Update a memory

        Args:
            memory_type: Type of memory
            memory_id: Memory ID
            request: Update request
            user_id: User ID for validation

        Returns:
            MemoryOperationResult with operation status
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(
                f"{self.base_url}/memories/{memory_type}/{memory_id}",
                json=request.model_dump(exclude_unset=True),
                params={"user_id": user_id},
                headers=self.headers
            )
            response.raise_for_status()
            return MemoryOperationResult(**response.json())

    async def delete_memory(
        self,
        memory_type: MemoryType,
        memory_id: str,
        user_id: str
    ) -> MemoryOperationResult:
        """
        Delete a memory

        Args:
            memory_type: Type of memory
            memory_id: Memory ID
            user_id: User ID for validation

        Returns:
            MemoryOperationResult with operation status
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(
                f"{self.base_url}/memories/{memory_type}/{memory_id}",
                params={"user_id": user_id},
                headers=self.headers
            )
            response.raise_for_status()
            return MemoryOperationResult(**response.json())

    # ==================== Search Operations ====================

    async def search_facts_by_subject(
        self,
        user_id: str,
        subject: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search factual memories by subject

        Args:
            user_id: User ID
            subject: Subject to search for
            limit: Maximum number of results

        Returns:
            Dictionary with memories and count
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/memories/factual/search/subject",
                params={"user_id": user_id, "subject": subject, "limit": limit},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def search_episodes_by_event_type(
        self,
        user_id: str,
        event_type: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search episodic memories by event type

        Args:
            user_id: User ID
            event_type: Event type to search for
            limit: Maximum number of results

        Returns:
            Dictionary with memories and count
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/memories/episodic/search/event_type",
                params={"user_id": user_id, "event_type": event_type, "limit": limit},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def get_active_working_memories(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get active working memories

        Args:
            user_id: User ID

        Returns:
            Dictionary with active memories and count
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/memories/working/active",
                params={"user_id": user_id},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def cleanup_expired_memories(
        self,
        user_id: Optional[str] = None
    ) -> MemoryOperationResult:
        """
        Clean up expired working memories

        Args:
            user_id: Optional user ID to cleanup specific user's memories

        Returns:
            MemoryOperationResult with operation status
        """
        params = {}
        if user_id:
            params["user_id"] = user_id

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/memories/working/cleanup",
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            return MemoryOperationResult(**response.json())

    # ==================== Session Operations ====================

    async def get_session_memories(
        self,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get memories for a specific session

        Args:
            session_id: Session ID
            user_id: User ID

        Returns:
            Dictionary with session memories and count
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/memories/session/{session_id}",
                params={"user_id": user_id},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def deactivate_session(
        self,
        session_id: str,
        user_id: str
    ) -> MemoryOperationResult:
        """
        Deactivate a session

        Args:
            session_id: Session ID
            user_id: User ID

        Returns:
            MemoryOperationResult with operation status
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/memories/session/{session_id}/deactivate",
                params={"user_id": user_id},
                headers=self.headers
            )
            response.raise_for_status()
            return MemoryOperationResult(**response.json())

    # ==================== Statistics ====================

    async def get_memory_statistics(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get memory statistics for a user

        Args:
            user_id: User ID

        Returns:
            Dictionary with memory statistics
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/memories/statistics",
                params={"user_id": user_id},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()


# Synchronous wrapper for convenience
class MemoryServiceSyncClient:
    """Synchronous wrapper for MemoryServiceClient"""

    def __init__(
        self,
        base_url: str = "http://localhost:8223",
        timeout: float = 30.0,
        api_key: Optional[str] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    def extract_factual_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> Dict[str, Any]:
        """Extract and store factual memories from dialog using AI"""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/memories/factual/extract",
                json={
                    "user_id": user_id,
                    "dialog_content": dialog_content,
                    "importance_score": importance_score
                },
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def get_memory(
        self,
        memory_type: str,
        memory_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get memory by ID and type"""
        params = {}
        if user_id:
            params["user_id"] = user_id

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/memories/{memory_type}/{memory_id}",
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def list_memories(
        self,
        user_id: str,
        memory_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List memories for a user"""
        params = {"user_id": user_id, "limit": limit, "offset": offset}
        if memory_type:
            params["memory_type"] = memory_type

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/memories",
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def extract_episodic_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> Dict[str, Any]:
        """Extract and store episodic memories from dialog using AI"""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/memories/episodic/extract",
                json={
                    "user_id": user_id,
                    "dialog_content": dialog_content,
                    "importance_score": importance_score
                },
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def extract_procedural_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> Dict[str, Any]:
        """Extract and store procedural memories from dialog using AI"""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/memories/procedural/extract",
                json={
                    "user_id": user_id,
                    "dialog_content": dialog_content,
                    "importance_score": importance_score
                },
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def extract_semantic_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> Dict[str, Any]:
        """Extract and store semantic memories from dialog using AI"""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/memories/semantic/extract",
                json={
                    "user_id": user_id,
                    "dialog_content": dialog_content,
                    "importance_score": importance_score
                },
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def create_memory(
        self,
        memory_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new memory"""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/memories",
                json=memory_data,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def update_memory(
        self,
        memory_type: str,
        memory_id: str,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a memory"""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.put(
                f"{self.base_url}/memories/{memory_type}/{memory_id}",
                json=update_data,
                params={"user_id": user_id},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def delete_memory(
        self,
        memory_type: str,
        memory_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Delete a memory"""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.delete(
                f"{self.base_url}/memories/{memory_type}/{memory_id}",
                params={"user_id": user_id},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def search_facts_by_subject(
        self,
        user_id: str,
        subject: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Search factual memories by subject"""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/memories/factual/search/subject",
                params={"user_id": user_id, "subject": subject, "limit": limit},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def search_episodes_by_event_type(
        self,
        user_id: str,
        event_type: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Search episodic memories by event type"""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/memories/episodic/search/event_type",
                params={"user_id": user_id, "event_type": event_type, "limit": limit},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def get_active_working_memories(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get active working memories"""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/memories/working/active",
                params={"user_id": user_id},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def cleanup_expired_memories(
        self,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clean up expired working memories"""
        params = {}
        if user_id:
            params["user_id"] = user_id

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/memories/working/cleanup",
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def get_session_memories(
        self,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get memories for a specific session"""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/memories/session/{session_id}",
                params={"user_id": user_id},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def deactivate_session(
        self,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Deactivate a session"""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/memories/session/{session_id}/deactivate",
                params={"user_id": user_id},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def get_memory_statistics(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get memory statistics for a user"""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/memories/statistics",
                params={"user_id": user_id},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
