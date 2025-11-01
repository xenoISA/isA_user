"""
Storage Service Client

Client library for other microservices to interact with storage service
"""

import httpx
import logging
from typing import Optional, List, Dict, Any, BinaryIO
from datetime import datetime

logger = logging.getLogger(__name__)


class StorageServiceClient:
    """Storage Service HTTP client"""

    def __init__(self, base_url: str = None):
        """
        Initialize Storage Service client

        Args:
            base_url: Storage service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("storage_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8209"

        self.client = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # File Upload & Management
    # =============================================================================

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        user_id: str,
        organization_id: Optional[str] = None,
        access_level: str = "private",
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        auto_delete_after_days: Optional[int] = None,
        enable_indexing: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Upload file to storage

        Args:
            file_content: File binary content
            filename: File name
            user_id: User ID
            organization_id: Organization ID (optional)
            access_level: Access level (public/private/restricted/shared)
            content_type: MIME type (optional)
            metadata: File metadata (optional)
            tags: File tags (optional)
            auto_delete_after_days: Auto delete after N days (optional)
            enable_indexing: Enable semantic indexing (default: True)

        Returns:
            Upload result with file_id and download_url

        Example:
            >>> client = StorageServiceClient()
            >>> result = await client.upload_file(
            ...     file_content=image_bytes,
            ...     filename="photo.jpg",
            ...     user_id="user123",
            ...     organization_id="org456",
            ...     tags=["vacation", "2024"]
            ... )
        """
        try:
            import json
            from io import BytesIO

            files = {"file": (filename, BytesIO(file_content), content_type or "application/octet-stream")}
            data = {
                "user_id": user_id,
                "access_level": access_level,
                "enable_indexing": enable_indexing
            }

            if organization_id:
                data["organization_id"] = organization_id
            if metadata:
                data["metadata"] = json.dumps(metadata)
            if tags:
                data["tags"] = ",".join(tags)
            if auto_delete_after_days:
                data["auto_delete_after_days"] = auto_delete_after_days

            response = await self.client.post(
                f"{self.base_url}/api/v1/files/upload",
                files=files,
                data=data
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to upload file: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None

    async def get_file_info(
        self,
        file_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get file information

        Args:
            file_id: File ID
            user_id: User ID

        Returns:
            File information

        Example:
            >>> file_info = await client.get_file_info("file123", "user456")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/files/{file_id}",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get file info: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None

    async def list_files(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        prefix: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Optional[List[Dict[str, Any]]]:
        """
        List user files

        Args:
            user_id: User ID
            organization_id: Organization ID (optional)
            prefix: File name prefix filter (optional)
            status: File status filter (optional)
            limit: Result limit (default: 100)
            offset: Pagination offset (default: 0)

        Returns:
            List of files

        Example:
            >>> files = await client.list_files("user123", limit=50)
        """
        try:
            params = {"user_id": user_id, "limit": limit, "offset": offset}
            if organization_id:
                params["organization_id"] = organization_id
            if prefix:
                params["prefix"] = prefix
            if status:
                params["status"] = status

            response = await self.client.get(
                f"{self.base_url}/api/v1/files",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list files: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return None

    async def get_download_url(
        self,
        file_id: str,
        user_id: str,
        expires_minutes: int = 60
    ) -> Optional[Dict[str, Any]]:
        """
        Get file download URL

        Args:
            file_id: File ID
            user_id: User ID
            expires_minutes: URL expiration in minutes (default: 60)

        Returns:
            Download URL and metadata

        Example:
            >>> download_info = await client.get_download_url("file123", "user456")
            >>> url = download_info["download_url"]
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/files/{file_id}/download",
                params={"user_id": user_id, "expires_minutes": expires_minutes}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get download URL: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting download URL: {e}")
            return None

    async def delete_file(
        self,
        file_id: str,
        user_id: str,
        permanent: bool = False
    ) -> bool:
        """
        Delete file

        Args:
            file_id: File ID
            user_id: User ID
            permanent: Whether to permanently delete (default: False)

        Returns:
            True if successful

        Example:
            >>> success = await client.delete_file("file123", "user456")
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/files/{file_id}",
                params={"user_id": user_id, "permanent": permanent}
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete file: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False

    # =============================================================================
    # File Sharing
    # =============================================================================

    async def share_file(
        self,
        file_id: str,
        shared_by: str,
        shared_with: Optional[str] = None,
        shared_with_email: Optional[str] = None,
        permissions: Optional[Dict[str, bool]] = None,
        password: Optional[str] = None,
        expires_hours: int = 24,
        max_downloads: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Share file with user or email

        Args:
            file_id: File ID
            shared_by: Sharer user ID
            shared_with: Recipient user ID (optional)
            shared_with_email: Recipient email (optional)
            permissions: Permission settings (view/download/delete)
            password: Access password (optional)
            expires_hours: Expiration in hours (default: 24)
            max_downloads: Max download count (optional)

        Returns:
            Share information with share_id

        Example:
            >>> share = await client.share_file(
            ...     file_id="file123",
            ...     shared_by="user456",
            ...     shared_with="user789",
            ...     permissions={"view": True, "download": True}
            ... )
        """
        try:
            data = {
                "shared_by": shared_by,
                "view": permissions.get("view", True) if permissions else True,
                "download": permissions.get("download", False) if permissions else False,
                "delete": permissions.get("delete", False) if permissions else False,
                "expires_hours": expires_hours
            }

            if shared_with:
                data["shared_with"] = shared_with
            if shared_with_email:
                data["shared_with_email"] = shared_with_email
            if password:
                data["password"] = password
            if max_downloads:
                data["max_downloads"] = max_downloads

            response = await self.client.post(
                f"{self.base_url}/api/v1/files/{file_id}/share",
                data=data
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to share file: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error sharing file: {e}")
            return None

    async def get_shared_file(
        self,
        share_id: str,
        token: Optional[str] = None,
        password: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Access shared file

        Args:
            share_id: Share ID
            token: Access token (optional)
            password: Access password (optional)

        Returns:
            File information

        Example:
            >>> file_info = await client.get_shared_file("share123", password="secret")
        """
        try:
            params = {}
            if token:
                params["token"] = token
            if password:
                params["password"] = password

            response = await self.client.get(
                f"{self.base_url}/api/v1/shares/{share_id}",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get shared file: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting shared file: {e}")
            return None

    # =============================================================================
    # Storage Statistics & Quota
    # =============================================================================

    async def get_storage_stats(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get storage statistics

        Args:
            user_id: User ID (optional)
            organization_id: Organization ID (optional)

        Returns:
            Storage statistics

        Example:
            >>> stats = await client.get_storage_stats(user_id="user123")
        """
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id
            if organization_id:
                params["organization_id"] = organization_id

            response = await self.client.get(
                f"{self.base_url}/api/v1/storage/stats",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get storage stats: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return None

    async def get_storage_quota(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get storage quota

        Args:
            user_id: User ID (optional)
            organization_id: Organization ID (optional)

        Returns:
            Storage quota information

        Example:
            >>> quota = await client.get_storage_quota(user_id="user123")
        """
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id
            if organization_id:
                params["organization_id"] = organization_id

            response = await self.client.get(
                f"{self.base_url}/api/v1/storage/quota",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get storage quota: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting storage quota: {e}")
            return None

    # =============================================================================
    # Album Management
    # =============================================================================

    async def create_album(
        self,
        name: str,
        user_id: str,
        description: Optional[str] = None,
        organization_id: Optional[str] = None,
        cover_photo_id: Optional[str] = None,
        auto_sync: bool = False,
        is_shared: bool = False,
        tags: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create album

        Args:
            name: Album name
            user_id: Creator user ID
            description: Album description (optional)
            organization_id: Organization ID (optional)
            cover_photo_id: Cover photo ID (optional)
            auto_sync: Auto sync to frames (default: False)
            is_shared: Is shared album (default: False)
            tags: Tags (optional)

        Returns:
            Created album

        Example:
            >>> album = await client.create_album(
            ...     name="Vacation 2024",
            ...     user_id="user123",
            ...     organization_id="org456",
            ...     tags=["vacation", "family"]
            ... )
        """
        try:
            payload = {
                "name": name,
                "user_id": user_id,
                "auto_sync": auto_sync,
                "is_shared": is_shared
            }

            if description:
                payload["description"] = description
            if organization_id:
                payload["organization_id"] = organization_id
            if cover_photo_id:
                payload["cover_photo_id"] = cover_photo_id
            if tags:
                payload["tags"] = tags

            response = await self.client.post(
                f"{self.base_url}/api/v1/albums",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create album: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating album: {e}")
            return None

    async def get_album(
        self,
        album_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get album details

        Args:
            album_id: Album ID
            user_id: User ID

        Returns:
            Album details

        Example:
            >>> album = await client.get_album("album123", "user456")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/albums/{album_id}",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get album: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting album: {e}")
            return None

    async def list_user_albums(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        List user albums

        Args:
            user_id: User ID
            limit: Result limit (default: 100)
            offset: Pagination offset (default: 0)

        Returns:
            Album list response

        Example:
            >>> albums = await client.list_user_albums("user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/albums",
                params={"user_id": user_id, "limit": limit, "offset": offset}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list albums: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing albums: {e}")
            return None

    async def update_album(
        self,
        album_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update album

        Args:
            album_id: Album ID
            user_id: User ID
            updates: Update data

        Returns:
            Updated album

        Example:
            >>> updated = await client.update_album(
            ...     album_id="album123",
            ...     user_id="user456",
            ...     updates={"name": "New Album Name"}
            ... )
        """
        try:
            response = await self.client.put(
                f"{self.base_url}/api/v1/albums/{album_id}",
                json=updates,
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update album: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error updating album: {e}")
            return None

    async def delete_album(
        self,
        album_id: str,
        user_id: str
    ) -> bool:
        """
        Delete album

        Args:
            album_id: Album ID
            user_id: User ID

        Returns:
            True if successful

        Example:
            >>> success = await client.delete_album("album123", "user456")
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/albums/{album_id}",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete album: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deleting album: {e}")
            return False

    async def add_photos_to_album(
        self,
        album_id: str,
        photo_ids: List[str],
        added_by: str,
        is_featured: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Add photos to album

        Args:
            album_id: Album ID
            photo_ids: List of photo IDs
            added_by: User ID adding photos
            is_featured: Mark as featured (default: False)

        Returns:
            Result with added photo count

        Example:
            >>> result = await client.add_photos_to_album(
            ...     album_id="album123",
            ...     photo_ids=["photo1", "photo2"],
            ...     added_by="user456"
            ... )
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/albums/{album_id}/photos",
                json={
                    "photo_ids": photo_ids,
                    "added_by": added_by,
                    "is_featured": is_featured
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to add photos to album: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error adding photos to album: {e}")
            return None

    async def get_album_photos(
        self,
        album_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Get album photos

        Args:
            album_id: Album ID
            user_id: User ID
            limit: Result limit (default: 50)
            offset: Pagination offset (default: 0)

        Returns:
            Album photos response

        Example:
            >>> photos = await client.get_album_photos("album123", "user456")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/albums/{album_id}/photos",
                params={"user_id": user_id, "limit": limit, "offset": offset}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get album photos: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting album photos: {e}")
            return None

    # =============================================================================
    # Photo Version Management
    # =============================================================================

    async def save_photo_version(
        self,
        photo_id: str,
        user_id: str,
        version_type: str,
        version_url: str,
        ai_model: Optional[str] = None,
        ai_prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Save AI-processed photo version

        Args:
            photo_id: Original photo ID
            user_id: User ID
            version_type: Version type (ai_enhanced, ai_generated, etc.)
            version_url: AI-generated image URL
            ai_model: AI model used (optional)
            ai_prompt: AI prompt used (optional)
            metadata: Additional metadata (optional)

        Returns:
            Saved version info

        Example:
            >>> version = await client.save_photo_version(
            ...     photo_id="photo123",
            ...     user_id="user456",
            ...     version_type="ai_enhanced",
            ...     version_url="https://..."
            ... )
        """
        try:
            payload = {
                "photo_id": photo_id,
                "user_id": user_id,
                "version_type": version_type,
                "version_url": version_url
            }

            if ai_model:
                payload["ai_model"] = ai_model
            if ai_prompt:
                payload["ai_prompt"] = ai_prompt
            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/photos/versions/save",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to save photo version: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error saving photo version: {e}")
            return None

    async def get_photo_versions(
        self,
        photo_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get all photo versions

        Args:
            photo_id: Photo ID
            user_id: User ID

        Returns:
            Photo with all versions

        Example:
            >>> versions = await client.get_photo_versions("photo123", "user456")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/photos/{photo_id}/versions",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get photo versions: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting photo versions: {e}")
            return None

    # =============================================================================
    # Semantic Search & RAG (Intelligence Features)
    # =============================================================================

    async def semantic_search(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        enable_rerank: bool = False,
        min_score: float = 0.0,
        file_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Semantic search files using natural language

        Args:
            user_id: User ID
            query: Natural language query
            top_k: Number of results (default: 5)
            enable_rerank: Enable reranking (default: False)
            min_score: Minimum relevance score (default: 0.0)
            file_types: File type filter (optional)
            tags: Tag filter (optional)

        Returns:
            Search results with relevance scores

        Example:
            >>> results = await client.semantic_search(
            ...     user_id="user123",
            ...     query="family vacation photos from summer",
            ...     top_k=10
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "query": query,
                "top_k": top_k,
                "enable_rerank": enable_rerank,
                "min_score": min_score
            }

            if file_types:
                payload["file_types"] = file_types
            if tags:
                payload["tags"] = tags

            response = await self.client.post(
                f"{self.base_url}/api/v1/files/search",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed semantic search: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return None

    async def rag_query(
        self,
        user_id: str,
        query: str,
        rag_mode: str = "simple",
        session_id: Optional[str] = None,
        top_k: int = 3,
        enable_citations: bool = True,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> Optional[Dict[str, Any]]:
        """
        RAG query based on user files

        Supported RAG modes: simple, raptor, self_rag, crag, plan_rag, hm_rag

        Args:
            user_id: User ID
            query: User question
            rag_mode: RAG mode (default: simple)
            session_id: Session ID for multi-turn (optional)
            top_k: Number of documents to retrieve (default: 3)
            enable_citations: Enable citations (default: True)
            max_tokens: Max generation length (default: 500)
            temperature: Generation temperature (default: 0.7)

        Returns:
            RAG response with answer and citations

        Example:
            >>> response = await client.rag_query(
            ...     user_id="user123",
            ...     query="What are the key points in my research papers?",
            ...     rag_mode="raptor"
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "query": query,
                "rag_mode": rag_mode,
                "top_k": top_k,
                "enable_citations": enable_citations,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            if session_id:
                payload["session_id"] = session_id

            response = await self.client.post(
                f"{self.base_url}/api/v1/files/ask",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed RAG query: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            return None

    async def get_intelligence_stats(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get intelligence service statistics

        Args:
            user_id: User ID

        Returns:
            Intelligence statistics

        Example:
            >>> stats = await client.get_intelligence_stats("user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/intelligence/stats",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get intelligence stats: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting intelligence stats: {e}")
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


__all__ = ["StorageServiceClient"]
