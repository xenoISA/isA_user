"""
Storage Service - Event Publishers

封装所有事件发布逻辑（本服务发出事件）
业务逻辑层通过这些方法发布事件
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.nats_client import Event, EventType, ServiceSource

from .models import (
    FileDeletedEventData,
    FileIndexedEventData,
    FileIndexingFailedEventData,
    FileIndexingRequestedEventData,
    FileSharedEventData,
    FileUploadedEventData,
    FileUploadedWithAIEventData,
)

logger = logging.getLogger(__name__)


class StorageEventPublisher:
    """Storage Service 事件发布器"""

    def __init__(self, event_bus):
        self.event_bus = event_bus

    async def publish_file_uploaded(
        self,
        file_id: str,
        file_name: str,
        file_size: int,
        content_type: str,
        user_id: str,
        organization_id: Optional[str],
        access_level: str,
        download_url: str,
        bucket_name: str,
        object_name: str,
    ) -> bool:
        """发布文件上传事件"""
        try:
            event_data = FileUploadedEventData(
                file_id=file_id,
                file_name=file_name,
                file_size=file_size,
                content_type=content_type,
                user_id=user_id,
                organization_id=organization_id,
                access_level=access_level,
                download_url=download_url,
                bucket_name=bucket_name,
                object_name=object_name,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            event = Event(
                event_type=EventType.FILE_UPLOADED,
                source=ServiceSource.STORAGE_SERVICE,
                data=event_data.dict(),
            )

            result = await self.event_bus.publish_event(event)
            if result:
                logger.info(f"✅ Published FILE_UPLOADED event for file {file_id}")
            else:
                logger.error(f"❌ Failed to publish FILE_UPLOADED event")
            return result

        except Exception as e:
            logger.error(f"Error publishing file_uploaded event: {e}")
            return False

    async def publish_file_uploaded_with_ai(
        self,
        file_id: str,
        file_name: str,
        file_size: int,
        content_type: str,
        user_id: str,
        organization_id: Optional[str],
        access_level: str,
        download_url: str,
        bucket_name: str,
        object_name: str,
        chunk_id: str,
        ai_metadata: Dict[str, Any],
    ) -> bool:
        """发布带AI元数据的文件上传事件"""
        try:
            event_data = FileUploadedWithAIEventData(
                file_id=file_id,
                file_name=file_name,
                file_size=file_size,
                content_type=content_type,
                user_id=user_id,
                organization_id=organization_id,
                access_level=access_level,
                download_url=download_url,
                bucket_name=bucket_name,
                object_name=object_name,
                chunk_id=chunk_id,
                ai_metadata=ai_metadata,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            event = Event(
                event_type=EventType.FILE_UPLOADED_WITH_AI,
                source=ServiceSource.STORAGE_SERVICE,
                data=event_data.dict(),
            )

            result = await self.event_bus.publish_event(event)
            if result:
                logger.info(
                    f"✅ Published FILE_UPLOADED_WITH_AI event for file {file_id}"
                )
            else:
                logger.error(f"❌ Failed to publish FILE_UPLOADED_WITH_AI event")
            return result

        except Exception as e:
            logger.error(f"Error publishing file_uploaded_with_ai event: {e}")
            return False

    async def publish_file_indexing_requested(
        self,
        file_id: str,
        user_id: str,
        organization_id: Optional[str],
        file_name: str,
        file_type: str,
        file_size: int,
        bucket_name: str,
        object_name: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """发布文件索引请求事件（异步后台处理）"""
        try:
            event_data = FileIndexingRequestedEventData(
                file_id=file_id,
                user_id=user_id,
                organization_id=organization_id,
                file_name=file_name,
                file_type=file_type,
                file_size=file_size,
                metadata=metadata,
                tags=tags,
                bucket_name=bucket_name,
                object_name=object_name,
            )

            event = Event(
                event_type=EventType.FILE_INDEXING_REQUESTED,
                source=ServiceSource.STORAGE_SERVICE,
                data=event_data.dict(),
            )

            result = await self.event_bus.publish_event(event)
            if result:
                logger.info(
                    f"📤 Published async indexing request for {file_type} file {file_id}"
                )
            return result

        except Exception as e:
            logger.error(f"Error publishing file_indexing_requested event: {e}")
            return False

    async def publish_file_indexed(
        self, file_id: str, user_id: str, file_name: str, file_size: int
    ) -> bool:
        """发布文件索引完成事件"""
        try:
            event_data = FileIndexedEventData(
                file_id=file_id,
                user_id=user_id,
                file_name=file_name,
                file_size=file_size,
                indexed_at=datetime.now(timezone.utc).isoformat(),
            )

            event = Event(
                event_type=EventType.FILE_INDEXED,
                source=ServiceSource.STORAGE_SERVICE,
                data=event_data.dict(),
            )

            result = await self.event_bus.publish_event(event)
            if result:
                logger.info(f"✅ Published FILE_INDEXED event for file {file_id}")
            return result

        except Exception as e:
            logger.error(f"Error publishing file_indexed event: {e}")
            return False

    async def publish_file_indexing_failed(
        self, file_id: str, user_id: str, error: str
    ) -> bool:
        """发布文件索引失败事件"""
        try:
            event_data = FileIndexingFailedEventData(
                file_id=file_id, user_id=user_id, error=error
            )

            event = Event(
                event_type=EventType.FILE_INDEXING_FAILED,
                source=ServiceSource.STORAGE_SERVICE,
                data=event_data.dict(),
            )

            result = await self.event_bus.publish_event(event)
            if result:
                logger.warning(
                    f"⚠️ Published FILE_INDEXING_FAILED event for file {file_id}"
                )
            return result

        except Exception as e:
            logger.error(f"Error publishing file_indexing_failed event: {e}")
            return False

    async def publish_file_deleted(
        self,
        file_id: str,
        file_name: str,
        file_size: int,
        user_id: str,
        permanent: bool,
    ) -> bool:
        """发布文件删除事件"""
        try:
            event_data = FileDeletedEventData(
                file_id=file_id,
                file_name=file_name,
                file_size=file_size,
                user_id=user_id,
                permanent=permanent,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            event = Event(
                event_type=EventType.FILE_DELETED,
                source=ServiceSource.STORAGE_SERVICE,
                data=event_data.dict(),
            )

            result = await self.event_bus.publish_event(event)
            if result:
                logger.info(f"✅ Published FILE_DELETED event for file {file_id}")
            return result

        except Exception as e:
            logger.error(f"Error publishing FILE_DELETED event: {e}")
            return False

    async def publish_file_shared(
        self,
        share_id: str,
        file_id: str,
        file_name: str,
        shared_by: str,
        shared_with: Optional[str],
        shared_with_email: Optional[str],
        expires_at: str,
    ) -> bool:
        """发布文件分享事件"""
        try:
            event_data = FileSharedEventData(
                share_id=share_id,
                file_id=file_id,
                file_name=file_name,
                shared_by=shared_by,
                shared_with=shared_with,
                shared_with_email=shared_with_email,
                expires_at=expires_at,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            event = Event(
                event_type=EventType.FILE_SHARED,
                source=ServiceSource.STORAGE_SERVICE,
                data=event_data.dict(),
            )

            result = await self.event_bus.publish_event(event)
            if result:
                logger.info(f"✅ Published FILE_SHARED event for file {file_id}")
            return result

        except Exception as e:
            logger.error(f"Error publishing FILE_SHARED event: {e}")
            return False
