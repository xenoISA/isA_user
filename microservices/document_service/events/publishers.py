"""
Document Event Publishers

Publishes events to NATS event bus
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from core.nats_client import Event

logger = logging.getLogger(__name__)


class DocumentEventPublisher:
    """Document event publisher"""

    def __init__(self, event_bus):
        """
        Initialize event publisher

        Args:
            event_bus: NATS event bus instance
        """
        self.event_bus = event_bus

    async def publish_document_created(
        self,
        doc_id: str,
        user_id: str,
        title: str,
        doc_type: str,
        file_id: str,
        organization_id: Optional[str] = None,
    ) -> bool:
        """Publish document.created event"""
        try:
            event = Event(
                event_type="document.created",
                source="document_service",
                data={
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "organization_id": organization_id,
                    "title": title,
                    "doc_type": doc_type,
                    "file_id": file_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            await self.event_bus.publish_event(event)
            logger.info(f"✅ Published document.created: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish document.created: {e}")
            return False

    async def publish_document_indexed(
        self,
        doc_id: str,
        user_id: str,
        chunk_count: int,
        collection_name: str,
    ) -> bool:
        """Publish document.indexed event"""
        try:
            event = Event(
                event_type="document.indexed",
                source="document_service",
                data={
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "chunk_count": chunk_count,
                    "collection_name": collection_name,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            await self.event_bus.publish_event(event)
            logger.info(f"✅ Published document.indexed: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish document.indexed: {e}")
            return False

    async def publish_document_updated(
        self,
        doc_id: str,
        old_doc_id: str,
        user_id: str,
        version: int,
        update_strategy: str,
        chunks_added: int = 0,
        chunks_updated: int = 0,
        chunks_deleted: int = 0,
    ) -> bool:
        """Publish document.updated event"""
        try:
            event = Event(
                event_type="document.updated",
                source="document_service",
                data={
                    "doc_id": doc_id,
                    "old_doc_id": old_doc_id,
                    "user_id": user_id,
                    "version": version,
                    "update_strategy": update_strategy,
                    "chunks_added": chunks_added,
                    "chunks_updated": chunks_updated,
                    "chunks_deleted": chunks_deleted,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            await self.event_bus.publish_event(event)
            logger.info(f"✅ Published document.updated: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish document.updated: {e}")
            return False

    async def publish_document_deleted(
        self, doc_id: str, user_id: str, permanent: bool = False
    ) -> bool:
        """Publish document.deleted event"""
        try:
            event = Event(
                event_type="document.deleted",
                source="document_service",
                data={
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "permanent": permanent,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            await self.event_bus.publish_event(event)
            logger.info(f"✅ Published document.deleted: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish document.deleted: {e}")
            return False

    async def publish_document_permission_updated(
        self,
        doc_id: str,
        user_id: str,
        access_level: str,
        points_updated: int = 0,
    ) -> bool:
        """Publish document.permission.updated event"""
        try:
            event = Event(
                event_type="document.permission.updated",
                source="document_service",
                data={
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "access_level": access_level,
                    "points_updated": points_updated,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            await self.event_bus.publish_event(event)
            logger.info(f"✅ Published document.permission.updated: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish document.permission.updated: {e}")
            return False
