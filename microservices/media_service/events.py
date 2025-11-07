"""
Media Service Event Handlers

Handles event-driven cleanup and synchronization for media resources
"""

import logging
import json
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .media_service import MediaService

logger = logging.getLogger(__name__)


class MediaEventHandler:
    """Event handler for Media Service"""

    def __init__(self, media_service: 'MediaService'):
        """
        Initialize event handler

        Args:
            media_service: Media service instance
        """
        self.media_service = media_service

    async def handle_event(self, event):
        """
        Generic event handler dispatcher

        Args:
            event: Event object (already parsed from NATS message)
        """
        try:
            # Event is already parsed by NATSEventBus
            # Extract data from Event object
            if hasattr(event, 'to_dict'):
                event_dict = event.to_dict()
                data = event_dict.get("data", {})
                event_type = event_dict.get("type")
            else:
                # Fallback: if it's a raw dict
                data = event.get("data", {}) if isinstance(event, dict) else {}
                event_type = event.get("type") if isinstance(event, dict) else None

            logger.info(f"Received event: {event_type}")

            if event_type == "file.deleted" or event_type == "FILE_DELETED":
                await self.handle_file_deleted(data)
            elif event_type == "device.deleted" or event_type == "DEVICE_DELETED":
                await self.handle_device_deleted(data)
            elif event_type == "file.uploaded.with_ai" or event_type == "FILE_UPLOADED_WITH_AI":
                # 🆕 优先处理带 AI 元数据的事件
                await self.handle_file_uploaded_with_ai(data)
            elif event_type == "file.uploaded" or event_type == "FILE_UPLOADED":
                await self.handle_file_uploaded(data)
            else:
                logger.warning(f"Unknown event type: {event_type}")

        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)

    async def handle_file_deleted(self, event_data: Dict[str, Any]):
        """
        Handle file.deleted event - Clean up photo versions and metadata

        When a file is deleted from storage, we need to:
        1. Delete all photo versions associated with this file
        2. Delete photo metadata
        3. Remove photo from all playlists

        Args:
            event_data: Event data containing file_id and user_id
        """
        try:
            file_id = event_data.get("file_id")
            user_id = event_data.get("user_id")

            if not file_id:
                logger.warning("file.deleted event missing file_id")
                return

            logger.info(f"Handling file.deleted event for file_id={file_id}, user_id={user_id}")

            # 1. Delete photo versions associated with this file
            # Note: In production, you'd want to implement a method to find versions by file_id
            # For now, we'll log the action
            logger.info(f"Cleaning up photo versions for file {file_id}")

            # TODO: Implement repository method to delete photo versions by file_id
            # deleted_versions = await self.media_service.repository.delete_photo_versions_by_file_id(file_id, user_id)
            # logger.info(f"Deleted {deleted_versions} photo versions for file {file_id}")

            # 2. Delete photo metadata
            try:
                metadata = await self.media_service.repository.get_photo_metadata(file_id)
                if metadata and metadata.user_id == user_id:
                    await self.media_service.repository.delete_photo_metadata(file_id, user_id)
                    logger.info(f"Deleted photo metadata for file {file_id}")
            except Exception as e:
                logger.error(f"Error deleting photo metadata for file {file_id}: {e}")

            # 3. Remove photo from all playlists
            # TODO: Implement repository method to remove photo from playlists
            # removed_count = await self.media_service.repository.remove_photo_from_all_playlists(file_id, user_id)
            # logger.info(f"Removed file {file_id} from {removed_count} playlists")

            logger.info(f"Successfully handled file.deleted event for file_id={file_id}")

        except Exception as e:
            logger.error(f"Error handling file.deleted event: {e}", exc_info=True)

    async def handle_device_deleted(self, event_data: Dict[str, Any]):
        """
        Handle device.deleted event - Clean up device-related media resources

        When a device (smart frame) is deleted, we need to:
        1. Delete all playlists associated with this device
        2. Delete all rotation schedules for this device
        3. Delete all photo cache entries for this device

        Args:
            event_data: Event data containing device_id and user_id
        """
        try:
            device_id = event_data.get("device_id")
            user_id = event_data.get("user_id")

            if not device_id:
                logger.warning("device.deleted event missing device_id")
                return

            logger.info(f"Handling device.deleted event for device_id={device_id}, user_id={user_id}")

            # 1. Delete rotation schedules for this device
            try:
                schedules = await self.media_service.repository.list_frame_schedules(device_id, user_id)
                for schedule in schedules:
                    await self.media_service.repository.delete_rotation_schedule(
                        schedule.schedule_id,
                        user_id
                    )
                logger.info(f"Deleted {len(schedules)} rotation schedules for device {device_id}")
            except Exception as e:
                logger.error(f"Error deleting rotation schedules for device {device_id}: {e}")

            # 2. Delete photo cache entries for this device
            try:
                # TODO: Implement repository method to delete all cache entries for a device
                # deleted_cache = await self.media_service.repository.delete_frame_cache(device_id, user_id)
                # logger.info(f"Deleted {deleted_cache} cache entries for device {device_id}")
                logger.info(f"Cleaning up cache entries for device {device_id}")
            except Exception as e:
                logger.error(f"Error deleting cache entries for device {device_id}: {e}")

            # 3. Optionally delete device-specific playlists
            # Note: You might want to keep playlists even if device is deleted
            # so users can re-assign them to new devices

            logger.info(f"Successfully handled device.deleted event for device_id={device_id}")

        except Exception as e:
            logger.error(f"Error handling device.deleted event: {e}", exc_info=True)

    async def handle_file_uploaded(self, event_data: Dict[str, Any]):
        """
        Handle file.uploaded event - Auto-create photo metadata (optional)

        When a photo file is uploaded, optionally create initial metadata entry
        for AI processing queue.

        Args:
            event_data: Event data containing file_id, user_id, file_type, etc.
        """
        try:
            file_id = event_data.get("file_id")
            user_id = event_data.get("user_id")
            file_type = event_data.get("file_type", "")

            if not file_id or not user_id:
                logger.warning("file.uploaded event missing file_id or user_id")
                return

            # Only process image files
            if not file_type.startswith("image/"):
                logger.debug(f"Skipping non-image file: {file_type}")
                return

            logger.info(f"Handling file.uploaded event for file_id={file_id}, user_id={user_id}")

            # Check if metadata already exists
            existing_metadata = await self.media_service.repository.get_photo_metadata(file_id)
            if existing_metadata:
                logger.info(f"Metadata already exists for file {file_id}, skipping")
                return

            # Create initial metadata entry (AI processing can populate it later)
            from .models import PhotoMetadata

            metadata = PhotoMetadata(
                file_id=file_id,
                user_id=user_id,
                organization_id=event_data.get("organization_id"),
                ai_labels=[],
                ai_objects=[],
                ai_scenes=[],
                ai_colors=[],
                face_detection={},
                quality_score=None
            )

            await self.media_service.repository.create_or_update_metadata(metadata)
            logger.info(f"Created initial metadata for file {file_id}")

        except Exception as e:
            logger.error(f"Error handling file.uploaded event: {e}", exc_info=True)

    async def handle_file_uploaded_with_ai(self, event_data: Dict[str, Any]):
        """
        Handle file.uploaded.with_ai event - 处理带 AI 元数据的文件上传事件

        当 Storage Service 完成 AI 提取后，直接保存完整的 AI 元数据到 Media Service。
        这样避免了 Media Service 重复调用 VLM API。

        Args:
            event_data: 事件数据包含:
                - file_id: 文件ID
                - user_id: 用户ID
                - chunk_id: Qdrant 向量 ID (用于后续搜索)
                - ai_metadata: AI 提取的元数据
                    - ai_categories: 分类
                    - ai_tags: 标签
                    - ai_mood: 情绪
                    - ai_dominant_colors: 主色调
                    - ai_quality_score: 质量分数
                - download_url: MinIO 下载链接
                - bucket_name: MinIO bucket
                - object_name: MinIO object key
        """
        try:
            file_id = event_data.get("file_id")
            user_id = event_data.get("user_id")
            ai_metadata = event_data.get("ai_metadata", {})
            chunk_id = event_data.get("chunk_id")

            if not file_id or not user_id:
                logger.warning("file.uploaded.with_ai event missing file_id or user_id")
                return

            if not ai_metadata:
                logger.warning(f"file.uploaded.with_ai event for {file_id} has no ai_metadata")
                return

            logger.info(f"📥 Handling file.uploaded.with_ai event for file_id={file_id}, chunk_id={chunk_id}")
            logger.info(f"AI metadata received: categories={ai_metadata.get('ai_categories')}, tags={ai_metadata.get('ai_tags', [])[:3]}")

            # 检查是否已存在元数据
            existing_metadata = await self.media_service.repository.get_photo_metadata(file_id)
            if existing_metadata:
                logger.info(f"Metadata already exists for file {file_id}, updating with AI data")

            # 创建/更新完整的 PhotoMetadata（带 AI 数据）
            from .models import PhotoMetadata

            metadata = PhotoMetadata(
                file_id=file_id,
                user_id=user_id,
                organization_id=event_data.get("organization_id"),

                # AI 提取的数据（来自 Storage Service）
                ai_labels=ai_metadata.get("ai_tags", []),  # 使用 tags 作为 labels
                ai_objects=[],  # TODO: 如果 VLM 支持对象检测，可以填充
                ai_scenes=ai_metadata.get("ai_categories", []),  # 使用 categories 作为 scenes
                ai_colors=ai_metadata.get("ai_dominant_colors", []),
                ai_description=f"Mood: {ai_metadata.get('ai_mood', 'unknown')}, Style: {ai_metadata.get('ai_style', 'unknown')}",
                quality_score=ai_metadata.get("ai_quality_score"),

                # 面部检测（如果需要，可以后续添加）
                face_detection={
                    "has_people": ai_metadata.get("ai_has_people", False)
                },

                # EXIF 数据（保持为空，如果需要可以从 Storage Service 传递）
                exif_data={},

                # 🔗 关联数据
                metadata={
                    "chunk_id": chunk_id,  # Qdrant 向量 ID
                    "download_url": event_data.get("download_url"),
                    "bucket_name": event_data.get("bucket_name"),
                    "object_name": event_data.get("object_name"),
                    "ai_extraction_source": "storage_service_mcp"
                }
            )

            await self.media_service.repository.create_or_update_metadata(metadata)
            logger.info(f"✅ Saved AI metadata for file {file_id} to Media Service")
            logger.info(f"   - Categories: {ai_metadata.get('ai_categories')}")
            logger.info(f"   - Tags: {ai_metadata.get('ai_tags', [])[:5]}")
            logger.info(f"   - Quality: {ai_metadata.get('ai_quality_score')}")
            logger.info(f"   - Chunk ID: {chunk_id}")

        except Exception as e:
            logger.error(f"Error handling file.uploaded.with_ai event: {e}", exc_info=True)
