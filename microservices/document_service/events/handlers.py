"""
Document Event Handlers

Handles incoming events from other services
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DocumentEventHandler:
    """Document event handler for subscribing to events"""

    def __init__(self, document_service):
        """
        Initialize event handler

        Args:
            document_service: DocumentService instance
        """
        self.document_service = document_service

    async def handle_event(self, msg) -> None:
        """
        Main event handler - routes events to specific handlers

        Args:
            msg: NATS message
        """
        try:
            # Extract event type from subject
            # Subject format: events.service_name.event_type
            subject = getattr(msg, 'subject', None)
            if not subject:
                logger.warning("Received message without subject, skipping")
                return

            event_type = subject.split(".")[-1] if "." in subject else subject

            # Parse message data
            import json
            data = json.loads(msg.data.decode())

            logger.info(f"Received event: {event_type} from {subject}")

            # Route to specific handlers
            if event_type == "file.deleted":
                await self._handle_file_deleted(data)
            elif event_type == "user.deleted":
                await self._handle_user_deleted(data)
            elif event_type == "organization.deleted":
                await self._handle_organization_deleted(data)
            else:
                logger.debug(f"Unhandled event type: {event_type}")

        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)

    async def _handle_file_deleted(self, data: Dict[str, Any]) -> None:
        """
        Handle file.deleted event from storage service

        When a file is deleted, also delete associated documents
        """
        try:
            file_id = data.get("file_id")
            user_id = data.get("user_id")
            permanent = data.get("permanent", False)

            if not file_id or not user_id:
                logger.warning("file.deleted event missing file_id or user_id")
                return

            logger.info(
                f"Handling file.deleted: file_id={file_id}, permanent={permanent}"
            )

            # Find document by file_id
            document = await self.document_service.repository.get_document_by_file_id(
                file_id, user_id
            )

            if not document:
                logger.debug(f"No document found for file {file_id}")
                return

            # Delete document (cascade delete to Qdrant if permanent)
            await self.document_service.delete_document(
                document.doc_id, user_id, permanent=permanent
            )

            logger.info(f"✅ Deleted document {document.doc_id} for file {file_id}")

        except Exception as e:
            logger.error(f"Error handling file.deleted: {e}", exc_info=True)

    async def _handle_user_deleted(self, data: Dict[str, Any]) -> None:
        """
        Handle user.deleted event

        Cleanup or anonymize user's documents
        """
        try:
            user_id = data.get("user_id")

            if not user_id:
                logger.warning("user.deleted event missing user_id")
                return

            logger.info(f"Handling user.deleted: user_id={user_id}")

            # Get all user documents
            documents = await self.document_service.repository.list_user_documents(
                user_id=user_id, limit=1000
            )

            # Delete all documents (soft delete by default)
            for doc in documents:
                try:
                    await self.document_service.delete_document(
                        doc.doc_id, user_id, permanent=False
                    )
                except Exception as e:
                    logger.error(f"Failed to delete document {doc.doc_id}: {e}")

            logger.info(f"✅ Deleted {len(documents)} documents for user {user_id}")

        except Exception as e:
            logger.error(f"Error handling user.deleted: {e}", exc_info=True)

    async def _handle_organization_deleted(self, data: Dict[str, Any]) -> None:
        """
        Handle organization.deleted event

        Update or delete organization documents
        """
        try:
            organization_id = data.get("organization_id")

            if not organization_id:
                logger.warning("organization.deleted event missing organization_id")
                return

            logger.info(f"Handling organization.deleted: org_id={organization_id}")

            # TODO: Implement organization document cleanup
            # Options:
            # 1. Delete all organization documents
            # 2. Transfer ownership to admin
            # 3. Archive documents

            logger.info(
                f"Organization {organization_id} deleted - document cleanup needed"
            )

        except Exception as e:
            logger.error(f"Error handling organization.deleted: {e}", exc_info=True)
