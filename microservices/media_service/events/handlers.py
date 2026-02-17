"""
Media Service Event Handlers

Handles event-driven cleanup and synchronization for media resources
"""

import json
import logging
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from ..media_service import MediaService

logger = logging.getLogger(__name__)


class MediaEventHandler:
    """Event handler for Media Service"""

    def __init__(self, media_service: "MediaService"):
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
            if hasattr(event, "to_dict"):
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
            elif (
                event_type == "file.uploaded.with_ai"
                or event_type == "FILE_UPLOADED_WITH_AI"
            ):
                # Priority: Handle events with AI metadata first
                await self.handle_file_uploaded_with_ai(data)
            elif event_type == "file.uploaded" or event_type == "FILE_UPLOADED":
                await self.handle_file_uploaded(data)
            elif event_type == "user.deleted" or event_type == "USER_DELETED":
                await self.handle_user_deleted(data)
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

            logger.info(
                f"Handling file.deleted event for file_id={file_id}, user_id={user_id}"
            )

            # 1. Delete photo versions associated with this file
            logger.info(f"Cleaning up photo versions for file {file_id}")
            # TODO: Implement repository method to delete photo versions by file_id

            # 2. Delete photo metadata
            try:
                metadata = await self.media_service.repository.get_photo_metadata(
                    file_id
                )
                if metadata and metadata.user_id == user_id:
                    await self.media_service.repository.delete_photo_metadata(
                        file_id, user_id
                    )
                    logger.info(f"Deleted photo metadata for file {file_id}")
            except Exception as e:
                logger.error(f"Error deleting photo metadata for file {file_id}: {e}")

            # 3. Remove photo from all playlists
            # TODO: Implement repository method to remove photo from playlists

            logger.info(
                f"Successfully handled file.deleted event for file_id={file_id}"
            )

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

            logger.info(
                f"Handling device.deleted event for device_id={device_id}, user_id={user_id}"
            )

            # 1. Delete rotation schedules for this device
            try:
                schedules = await self.media_service.repository.list_frame_schedules(
                    device_id, user_id
                )
                for schedule in schedules:
                    await self.media_service.repository.delete_rotation_schedule(
                        schedule.schedule_id, user_id
                    )
                logger.info(
                    f"Deleted {len(schedules)} rotation schedules for device {device_id}"
                )
            except Exception as e:
                logger.error(
                    f"Error deleting rotation schedules for device {device_id}: {e}"
                )

            # 2. Delete photo cache entries for this device
            try:
                logger.info(f"Cleaning up cache entries for device {device_id}")
                # TODO: Implement repository method to delete all cache entries for a device
            except Exception as e:
                logger.error(
                    f"Error deleting cache entries for device {device_id}: {e}"
                )

            logger.info(
                f"Successfully handled device.deleted event for device_id={device_id}"
            )

        except Exception as e:
            logger.error(f"Error handling device.deleted event: {e}", exc_info=True)

    async def handle_user_deleted(self, event_data: Dict[str, Any]):
        """
        Handle user.deleted event - Clean up all user media resources

        When a user is deleted, we need to:
        1. Delete all photo metadata for this user
        2. Delete all rotation schedules for this user
        3. Delete all photo versions for this user

        Args:
            event_data: Event data containing user_id
        """
        try:
            user_id = event_data.get("user_id")

            if not user_id:
                logger.warning("user.deleted event missing user_id")
                return

            logger.info(f"Handling user.deleted event for user_id={user_id}")

            # 1. Delete all photo metadata for this user
            try:
                deleted_count = await self.media_service.repository.delete_all_user_metadata(user_id)
                logger.info(f"Deleted {deleted_count} photo metadata records for user {user_id}")
            except Exception as e:
                logger.error(f"Error deleting photo metadata for user {user_id}: {e}")

            # 2. Delete all rotation schedules for this user
            try:
                schedules_deleted = await self.media_service.repository.delete_all_user_schedules(user_id)
                logger.info(f"Deleted {schedules_deleted} rotation schedules for user {user_id}")
            except Exception as e:
                logger.error(f"Error deleting rotation schedules for user {user_id}: {e}")

            # 3. Delete all photo versions for this user
            try:
                versions_deleted = await self.media_service.repository.delete_all_user_photo_versions(user_id)
                logger.info(f"Deleted {versions_deleted} photo versions for user {user_id}")
            except Exception as e:
                logger.error(f"Error deleting photo versions for user {user_id}: {e}")

            logger.info(f"Successfully handled user.deleted event for user_id={user_id}")

        except Exception as e:
            logger.error(f"Error handling user.deleted event: {e}", exc_info=True)

    async def handle_file_uploaded(self, event_data: Dict[str, Any]):
        """
        Handle file.uploaded event - Process AI analysis via Digital Analytics Service

        Event-driven AI processing workflow:
        1. Storage Service uploads file → publishes file.uploaded event
        2. Media Service receives event → triggers AI processing
        3. Digital Analytics Service performs VLM/OCR analysis
        4. Media Service caches AI metadata to PostgreSQL

        Args:
            event_data: Event data containing:
                - file_id: File ID
                - user_id: User ID
                - file_name: File name
                - content_type: MIME type
                - bucket_name: MinIO bucket name
                - object_name: MinIO object key
                - enable_indexing: Whether to enable AI indexing (default: true)
                - organization_id: Organization ID (optional)
                - tags: User-provided tags (optional)
                - metadata: User-provided metadata (optional)
        """
        try:
            file_id = event_data.get("file_id")
            user_id = event_data.get("user_id")
            content_type = event_data.get("content_type", "")
            enable_indexing = event_data.get("enable_indexing", True)
            bucket_name = event_data.get("bucket_name")
            object_name = event_data.get("object_name")

            if not file_id or not user_id:
                logger.warning("file.uploaded event missing file_id or user_id")
                return

            if not bucket_name or not object_name:
                logger.warning(
                    f"file.uploaded event missing bucket_name or object_name for file {file_id}"
                )
                return

            # Check if AI indexing is disabled
            if not enable_indexing:
                logger.info(f"AI indexing disabled for file {file_id}, skipping")
                return

            # Only process image and PDF files
            is_image = content_type.startswith("image/")
            is_pdf = content_type == "application/pdf"

            if not (is_image or is_pdf):
                logger.debug(f"Skipping non-media file: {content_type}")
                return

            logger.info(
                f"🎬 Processing file.uploaded event: file_id={file_id}, type={content_type}"
            )

            # Check if metadata already exists and is already indexed
            existing_metadata = await self.media_service.repository.get_photo_metadata(
                file_id
            )
            if existing_metadata:
                # Check if already has AI metadata (from previous processing)
                if hasattr(existing_metadata, "ai_processing_status"):
                    if existing_metadata.ai_processing_status == "completed":
                        logger.info(f"File {file_id} already has AI metadata, skipping")
                        return
                else:
                    logger.info(
                        f"Metadata exists for file {file_id}, updating with AI analysis"
                    )

            # Create initial metadata with processing status
            from ..models import PhotoMetadata

            metadata = PhotoMetadata(
                file_id=file_id,
                user_id=user_id,
                organization_id=event_data.get("organization_id"),
                ai_labels=[],
                ai_objects=[],
                ai_scenes=[],
                ai_colors=[],
                face_detection={},
                quality_score=None,
                full_metadata={
                    "ai_processing_status": "processing",
                    "file_name": event_data.get("file_name"),
                    "content_type": content_type,
                },
            )

            await self.media_service.repository.create_or_update_metadata(metadata)
            logger.info(
                f"Created initial metadata for file {file_id}, status=processing"
            )

            # Import Digital Analytics Client
            from ..clients import DigitalAnalyticsClient

            analytics_client = DigitalAnalyticsClient()

            if not analytics_client.is_enabled():
                logger.warning(
                    "Digital Analytics Service not enabled, skipping AI processing"
                )
                return

            # Prepare collection name (user-specific)
            collection_name = f"user_{user_id}_media"

            # Prepare metadata for Digital Analytics
            da_metadata = {
                "file_id": file_id,
                "file_name": event_data.get("file_name"),
                "content_type": content_type,
                "user_tags": event_data.get("tags", []),
                "custom_metadata": event_data.get("metadata", {}),
            }

            # Process based on file type using MinIO bucket+key
            # This avoids presigned URL signature issues in K8s internal network
            ai_result = None
            minio_input = {"bucket": bucket_name, "key": object_name}

            if is_image:
                logger.info(
                    f"📷 Processing image via Digital Analytics: {file_id} (bucket={bucket_name}, key={object_name})"
                )
                ai_result = await analytics_client.process_image(
                    user_id=user_id,
                    image_url=minio_input,  # Pass MinIO bucket+key dict instead of URL
                    collection_name=collection_name,
                    metadata=da_metadata,
                )

            elif is_pdf:
                logger.info(
                    f"📄 Processing PDF via Digital Analytics: {file_id} (bucket={bucket_name}, key={object_name})"
                )
                ai_result = await analytics_client.process_pdf(
                    user_id=user_id,
                    pdf_url=minio_input,  # Pass MinIO bucket+key dict instead of URL
                    collection_name=collection_name,
                    metadata=da_metadata,
                )

            # Save AI analysis results to PostgreSQL cache
            if ai_result and ai_result.get("success"):
                logger.info(f"✅ AI processing completed for file {file_id}")

                # Extract AI metadata from result
                ai_metadata = ai_result.get("ai_metadata", {})
                processing_metadata = ai_result.get("metadata", {})

                logger.info(f"   AI metadata keys: {list(ai_metadata.keys())}")
                logger.info(f"   AI categories: {ai_metadata.get('ai_categories', [])}")
                logger.info(f"   AI tags: {ai_metadata.get('ai_tags', [])[:5]}")

                # Update metadata with AI results
                metadata.ai_labels = ai_metadata.get("ai_tags", [])
                metadata.ai_scenes = ai_metadata.get("ai_categories", [])
                metadata.ai_colors = ai_metadata.get("ai_dominant_colors", [])
                metadata.quality_score = ai_metadata.get("ai_quality_score")

                # Additional AI fields (if available in new schema)
                if hasattr(metadata, "ai_description"):
                    metadata.ai_description = ai_metadata.get("ai_description", "")
                if hasattr(metadata, "ai_tags"):
                    metadata.ai_tags = ai_metadata.get("ai_tags", [])
                if hasattr(metadata, "ai_categories"):
                    metadata.ai_categories = ai_metadata.get("ai_categories", [])
                if hasattr(metadata, "ai_mood"):
                    metadata.ai_mood = ai_metadata.get("ai_mood")
                if hasattr(metadata, "ai_style"):
                    metadata.ai_style = ai_metadata.get("ai_style")
                if hasattr(metadata, "ai_dominant_colors"):
                    metadata.ai_dominant_colors = ai_metadata.get(
                        "ai_dominant_colors", []
                    )
                if hasattr(metadata, "knowledge_id"):
                    metadata.knowledge_id = ai_result.get(
                        "operation_id"
                    ) or ai_result.get("knowledge_id")
                if hasattr(metadata, "collection_name"):
                    metadata.collection_name = collection_name
                if hasattr(metadata, "vector_indexed"):
                    metadata.vector_indexed = True
                if hasattr(metadata, "ai_processing_status"):
                    metadata.ai_processing_status = "completed"
                if hasattr(metadata, "ai_indexed_at"):
                    from datetime import datetime, timezone

                    metadata.ai_indexed_at = datetime.now(timezone.utc)

                # Store processing metadata in full_metadata
                metadata.full_metadata = {
                    **metadata.full_metadata,
                    "ai_processing_status": "completed",
                    "knowledge_id": ai_result.get("operation_id"),
                    "collection_name": collection_name,
                    "processing_metadata": processing_metadata,
                    "ai_metadata": ai_metadata,  # Full AI metadata for reference
                }

                await self.media_service.repository.create_or_update_metadata(metadata)
                logger.info(f"💾 Cached AI metadata to PostgreSQL for file {file_id}")

            else:
                logger.error(f"❌ AI processing failed for file {file_id}")
                # Update status to failed
                metadata.full_metadata = {
                    **metadata.full_metadata,
                    "ai_processing_status": "failed",
                    "ai_processing_error": ai_result.get("error", "Unknown error")
                    if ai_result
                    else "No result returned",
                }
                if hasattr(metadata, "ai_processing_status"):
                    metadata.ai_processing_status = "failed"
                if hasattr(metadata, "ai_processing_error"):
                    metadata.ai_processing_error = (
                        ai_result.get("error", "Unknown error")
                        if ai_result
                        else "No result returned"
                    )

                await self.media_service.repository.create_or_update_metadata(metadata)

            await analytics_client.close()

        except Exception as e:
            logger.error(f"Error handling file.uploaded event: {e}", exc_info=True)

    async def handle_file_uploaded_with_ai(self, event_data: Dict[str, Any]):
        """
        Handle file.uploaded.with_ai event - Process file upload with AI metadata

        When Storage Service completes AI extraction, save complete AI metadata to Media Service.
        This avoids Media Service from calling VLM API again.

        Args:
            event_data: Event data containing:
                - file_id: File ID
                - user_id: User ID
                - chunk_id: Qdrant vector ID (for future search)
                - ai_metadata: AI extracted metadata
                    - ai_categories: Categories
                    - ai_tags: Tags
                    - ai_mood: Mood
                    - ai_dominant_colors: Dominant colors
                    - ai_quality_score: Quality score
                - download_url: MinIO download link
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
                logger.warning(
                    f"file.uploaded.with_ai event for {file_id} has no ai_metadata"
                )
                return

            logger.info(
                f"📥 Handling file.uploaded.with_ai event for file_id={file_id}, chunk_id={chunk_id}"
            )
            logger.info(
                f"AI metadata received: categories={ai_metadata.get('ai_categories')}, tags={ai_metadata.get('ai_tags', [])[:3]}"
            )

            # Check if metadata already exists
            existing_metadata = await self.media_service.repository.get_photo_metadata(
                file_id
            )
            if existing_metadata:
                logger.info(
                    f"Metadata already exists for file {file_id}, updating with AI data"
                )

            # Create/update complete PhotoMetadata (with AI data)
            from ..models import PhotoMetadata

            metadata = PhotoMetadata(
                file_id=file_id,
                user_id=user_id,
                organization_id=event_data.get("organization_id"),
                # AI extracted data (from Storage Service)
                ai_labels=ai_metadata.get("ai_tags", []),  # Use tags as labels
                ai_objects=[],  # TODO: If VLM supports object detection, populate this
                ai_scenes=ai_metadata.get(
                    "ai_categories", []
                ),  # Use categories as scenes
                ai_colors=ai_metadata.get("ai_dominant_colors", []),
                ai_description=f"Mood: {ai_metadata.get('ai_mood', 'unknown')}, Style: {ai_metadata.get('ai_style', 'unknown')}",
                quality_score=ai_metadata.get("ai_quality_score"),
                # Face detection (if needed, can be added later)
                face_detection={"has_people": ai_metadata.get("ai_has_people", False)},
                # Related data - use full_metadata field
                full_metadata={
                    "chunk_id": chunk_id,  # Qdrant vector ID
                    "download_url": event_data.get("download_url"),
                    "bucket_name": event_data.get("bucket_name"),
                    "object_name": event_data.get("object_name"),
                    "ai_extraction_source": "storage_service_mcp",
                },
            )

            await self.media_service.repository.create_or_update_metadata(metadata)
            logger.info(f"✅ Saved AI metadata for file {file_id} to Media Service")
            logger.info(f"   - Categories: {ai_metadata.get('ai_categories')}")
            logger.info(f"   - Tags: {ai_metadata.get('ai_tags', [])[:5]}")
            logger.info(f"   - Quality: {ai_metadata.get('ai_quality_score')}")
            logger.info(f"   - Chunk ID: {chunk_id}")

        except Exception as e:
            logger.error(
                f"Error handling file.uploaded.with_ai event: {e}", exc_info=True
            )
