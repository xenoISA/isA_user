"""
Storage Service - Event Handlers

处理接收到的事件（订阅其他服务事件，包括自己的异步事件）
"""

import logging
from datetime import datetime

from core.nats_client import Event, EventType, ServiceSource

logger = logging.getLogger(__name__)


async def handle_file_indexing_request(
    event: Event, intelligence_service, storage_service, event_bus
):
    """
    处理文件索引请求事件（异步后台任务）

    当文件上传时，会发布 FILE_INDEXING_REQUESTED 事件
    此 handler 在后台异步处理索引工作
    """
    try:
        logger.info(f"Received file indexing request: {event.id}")

        # 提取事件数据
        data = event.data
        file_id = data.get("file_id")
        user_id = data.get("user_id")
        organization_id = data.get("organization_id")
        file_name = data.get("file_name")
        file_type = data.get("file_type")
        file_size = data.get("file_size")
        metadata = data.get("metadata", {})
        tags = data.get("tags", [])
        bucket_name = data.get("bucket_name")
        object_name = data.get("object_name")

        if not all([file_id, user_id, file_name, bucket_name, object_name]):
            logger.error(f"Missing required fields in indexing request: {data}")
            return

        # 准备文件内容/URL
        try:
            # 对于图片和PDF，传递预签名URL
            if file_type.startswith("image/") or file_type == "application/pdf":
                file_content = storage_service.minio_client.get_presigned_url(
                    bucket_name=bucket_name,
                    object_key=object_name,
                    expiry_seconds=3600,  # 1小时
                )
                if not file_content:
                    raise Exception("Failed to generate presigned URL")
                logger.info(
                    f"Generated presigned URL for {file_type}: {file_content[:100]}..."
                )
            else:
                # 对于文本文件，下载内容
                file_bytes = storage_service.minio_client.get_object(
                    bucket_name, object_name
                )
                if file_bytes is None:
                    raise Exception("File not found in MinIO")
                file_content = file_bytes.decode("utf-8", errors="ignore")

        except Exception as e:
            logger.error(f"Failed to download file {file_id} from MinIO: {e}")
            # 发布索引失败事件
            if event_bus:
                from .publishers import StorageEventPublisher

                publisher = StorageEventPublisher(event_bus)
                await publisher.publish_file_indexing_failed(
                    file_id=file_id,
                    user_id=user_id,
                    error=f"Failed to download file: {str(e)}",
                )
            return

        # 通过 intelligence service 索引文件
        try:
            logger.info(f"Starting async indexing for file {file_id}")
            await intelligence_service.index_file(
                file_id=file_id,
                user_id=user_id,
                organization_id=organization_id,
                file_name=file_name,
                file_content=file_content,
                file_type=file_type,
                file_size=file_size,
                metadata=metadata,
                tags=tags,
            )

            logger.info(f"Successfully indexed file {file_id}")

            # 发布索引成功事件
            if event_bus:
                from .publishers import StorageEventPublisher

                publisher = StorageEventPublisher(event_bus)
                await publisher.publish_file_indexed(
                    file_id=file_id,
                    user_id=user_id,
                    file_name=file_name,
                    file_size=file_size,
                )

        except Exception as e:
            logger.error(f"Failed to index file {file_id}: {e}")
            # 发布索引失败事件
            if event_bus:
                from .publishers import StorageEventPublisher

                publisher = StorageEventPublisher(event_bus)
                await publisher.publish_file_indexing_failed(
                    file_id=file_id, user_id=user_id, error=str(e)
                )

    except Exception as e:
        logger.error(f"Error handling file indexing request: {e}")


# 添加其他 event handlers（如果需要订阅其他服务的事件）
# 例如：
# async def handle_album_created(event: Event, storage_service):
#     """处理相册创建事件"""
#     pass
