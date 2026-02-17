"""
Document Repository - Data access layer for document service
Handles database operations for knowledge documents, permissions, and version history

Uses PostgresClient with gRPC for PostgreSQL access
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from google.protobuf.json_format import MessageToDict
from google.protobuf.struct_pb2 import ListValue, Struct
from isa_common import AsyncPostgresClient

from core.config_manager import ConfigManager

from .models import (
    AccessLevel,
    ChunkingStrategy,
    DocumentStatus,
    DocumentType,
    KnowledgeDocument,
    DocumentPermissionHistory,
)

logger = logging.getLogger(__name__)


class DocumentRepository:
    """Document repository - data access layer for document operations"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize document repository with PostgresClient"""
        # Use config_manager for service discovery
        if config is None:
            config = ConfigManager("document_service")

        # Discover PostgreSQL service
        # Priority: Environment variables → Consul → localhost fallback
        host, port = config.discover_service(
            service_name="postgres_grpc_service",
            default_host="isa-postgres-grpc",
            default_port=5432,
            env_host_key="POSTGRES_HOST",
            env_port_key="POSTGRES_PORT",
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(host=host, port=port, user_id="document_service")

        # Table names (document schema)
        self.schema = "document"
        self.documents_table = "knowledge_documents"
        self.permission_history_table = "document_permission_history"

    def _convert_protobuf_to_native(self, value: Any) -> Any:
        """Convert Protobuf types (Struct, ListValue) to native Python types

        This handles JSONB fields returned from PostgreSQL gRPC service.
        """
        if isinstance(value, (ListValue, Struct)):
            return MessageToDict(value, preserving_proto_field_name=True)
        return value

    # ==================== Knowledge Document Operations ====================

    async def create_document(
        self, document_data: KnowledgeDocument
    ) -> Optional[KnowledgeDocument]:
        """Create a new knowledge document"""
        try:
            data = {
                "doc_id": document_data.doc_id,
                "user_id": document_data.user_id,
                "organization_id": document_data.organization_id or "",
                "title": document_data.title,
                "description": document_data.description or "",
                "doc_type": document_data.doc_type.value
                if hasattr(document_data.doc_type, "value")
                else str(document_data.doc_type),
                "file_id": document_data.file_id,
                "file_size": document_data.file_size or 0,
                "file_url": document_data.file_url or "",
                "version": document_data.version or 1,
                "parent_version_id": document_data.parent_version_id or "",
                "is_latest": document_data.is_latest,
                "status": document_data.status.value
                if hasattr(document_data.status, "value")
                else str(document_data.status),
                "chunk_count": document_data.chunk_count or 0,
                "chunking_strategy": document_data.chunking_strategy.value
                if hasattr(document_data.chunking_strategy, "value")
                else str(document_data.chunking_strategy),
                "indexed_at": document_data.indexed_at.isoformat()
                if document_data.indexed_at
                else None,
                "last_updated_at": document_data.last_updated_at.isoformat()
                if document_data.last_updated_at
                else None,
                "access_level": document_data.access_level.value
                if hasattr(document_data.access_level, "value")
                else str(document_data.access_level),
                "allowed_users": document_data.allowed_users or [],
                "allowed_groups": document_data.allowed_groups or [],
                "denied_users": document_data.denied_users or [],
                "collection_name": document_data.collection_name or "default",
                "point_ids": document_data.point_ids or [],
                "metadata": document_data.metadata or {},
                "tags": document_data.tags or [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            async with self.db:
                count = await self.db.insert_into(
                    self.documents_table, [data], schema=self.schema
                )

            if count is not None and count > 0:
                return await self.get_document_by_id(document_data.doc_id)
            return await self.get_document_by_id(document_data.doc_id)

        except Exception as e:
            logger.error(f"Error creating document: {e}")
            raise

    async def get_document_by_id(self, doc_id: str) -> Optional[KnowledgeDocument]:
        """Get document by ID"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.documents_table}
                WHERE doc_id = $1
            """
            params = [doc_id]

            async with self.db:
                result = await self.db.query_row(query, params, schema=self.schema)

            if result:
                # Convert protobuf JSONB fields
                for field in ["metadata", "allowed_users", "allowed_groups", "denied_users", "point_ids", "tags"]:
                    if field in result:
                        result[field] = self._convert_protobuf_to_native(result[field])

                return KnowledgeDocument.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting document: {e}")
            return None

    async def get_document_by_file_id(
        self, file_id: str, user_id: str
    ) -> Optional[KnowledgeDocument]:
        """Get document by file ID and user ID"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.documents_table}
                WHERE file_id = $1 AND user_id = $2 AND is_latest = true
            """
            params = [file_id, user_id]

            async with self.db:
                result = await self.db.query_row(query, params, schema=self.schema)

            if result:
                for field in ["metadata", "allowed_users", "allowed_groups", "denied_users", "point_ids", "tags"]:
                    if field in result:
                        result[field] = self._convert_protobuf_to_native(result[field])

                return KnowledgeDocument.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting document by file_id: {e}")
            return None

    async def list_user_documents(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        status: Optional[DocumentStatus] = None,
        doc_type: Optional[DocumentType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[KnowledgeDocument]:
        """List user's documents"""
        try:
            # Build query with filters
            conditions = ["user_id = $1", "is_latest = true"]
            params = [user_id]
            param_count = 1

            if organization_id:
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(organization_id)

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status.value if hasattr(status, "value") else str(status))

            if doc_type:
                param_count += 1
                conditions.append(f"doc_type = ${param_count}")
                params.append(doc_type.value if hasattr(doc_type, "value") else str(doc_type))

            where_clause = " AND ".join(conditions)
            param_count += 1
            limit_param = f"${param_count}"
            param_count += 1
            offset_param = f"${param_count}"
            params.extend([limit, offset])

            query = f"""
                SELECT * FROM {self.schema}.{self.documents_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit_param} OFFSET {offset_param}
            """

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            # Convert protobuf JSONB fields
            for row in results:
                for field in ["metadata", "allowed_users", "allowed_groups", "denied_users", "point_ids", "tags"]:
                    if field in row:
                        row[field] = self._convert_protobuf_to_native(row[field])

            return [KnowledgeDocument.model_validate(row) for row in results]

        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return []

    async def update_document(
        self, doc_id: str, update_data: Dict[str, Any]
    ) -> Optional[KnowledgeDocument]:
        """Update document fields"""
        try:
            # Build SET clause dynamically
            set_clauses = []
            params = []
            param_count = 0

            for key, value in update_data.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")

                # Handle enum values
                if hasattr(value, "value"):
                    params.append(value.value)
                elif isinstance(value, datetime):
                    params.append(value.isoformat())
                else:
                    params.append(value)

            # Add updated_at
            param_count += 1
            set_clauses.append(f"updated_at = ${param_count}")
            params.append(datetime.now(timezone.utc).isoformat())

            # Add doc_id for WHERE clause
            param_count += 1
            params.append(doc_id)

            query = f"""
                UPDATE {self.schema}.{self.documents_table}
                SET {', '.join(set_clauses)}
                WHERE doc_id = ${param_count}
            """

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            if count is not None and count > 0:
                return await self.get_document_by_id(doc_id)
            return await self.get_document_by_id(doc_id)

        except Exception as e:
            logger.error(f"Error updating document: {e}")
            raise

    async def update_document_status(
        self, doc_id: str, status: DocumentStatus, chunk_count: Optional[int] = None
    ) -> bool:
        """Update document status and optionally chunk count"""
        try:
            update_data = {"status": status}

            if chunk_count is not None:
                update_data["chunk_count"] = chunk_count

            if status == DocumentStatus.INDEXED:
                update_data["indexed_at"] = datetime.now(timezone.utc)

            if status in [DocumentStatus.UPDATING, DocumentStatus.UPDATE_PENDING]:
                update_data["last_updated_at"] = datetime.now(timezone.utc)

            result = await self.update_document(doc_id, update_data)
            return result is not None

        except Exception as e:
            logger.error(f"Error updating document status: {e}")
            return False

    async def mark_version_as_old(self, doc_id: str) -> bool:
        """Mark a document version as not latest"""
        try:
            query = f"""
                UPDATE {self.schema}.{self.documents_table}
                SET is_latest = false, updated_at = $1
                WHERE doc_id = $2
            """
            params = [datetime.now(timezone.utc).isoformat(), doc_id]

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error marking version as old: {e}")
            return False

    async def delete_document(self, doc_id: str, user_id: str, soft: bool = True) -> bool:
        """Delete document (soft or hard)"""
        try:
            if soft:
                # Soft delete - mark as deleted
                query = f"""
                    UPDATE {self.schema}.{self.documents_table}
                    SET status = $1, updated_at = $2
                    WHERE doc_id = $3 AND user_id = $4
                """
                params = [
                    DocumentStatus.DELETED.value,
                    datetime.now(timezone.utc).isoformat(),
                    doc_id,
                    user_id,
                ]
            else:
                # Hard delete
                query = f"""
                    DELETE FROM {self.schema}.{self.documents_table}
                    WHERE doc_id = $1 AND user_id = $2
                """
                params = [doc_id, user_id]

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise

    # ==================== Version Operations ====================

    async def list_document_versions(
        self, file_id: str, user_id: str
    ) -> List[KnowledgeDocument]:
        """List all versions of a document"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.documents_table}
                WHERE file_id = $1 AND user_id = $2
                ORDER BY version DESC
            """
            params = [file_id, user_id]

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            # Convert protobuf JSONB fields
            for row in results:
                for field in ["metadata", "allowed_users", "allowed_groups", "denied_users", "point_ids", "tags"]:
                    if field in row:
                        row[field] = self._convert_protobuf_to_native(row[field])

            return [KnowledgeDocument.model_validate(row) for row in results]

        except Exception as e:
            logger.error(f"Error listing document versions: {e}")
            return []

    async def create_document_version(
        self,
        base_doc_id: str,
        new_file_id: str,
        new_version: int,
        chunk_count: int,
        point_ids: List[str],
        user_id: str,
    ) -> Optional[KnowledgeDocument]:
        """Create a new version of an existing document"""
        try:
            # Get base document
            base_doc = await self.get_document_by_id(base_doc_id)
            if not base_doc:
                raise ValueError(f"Base document {base_doc_id} not found")

            # Generate new doc_id for version
            import uuid
            new_doc_id = f"doc_{uuid.uuid4().hex[:12]}"

            # Create new version
            new_doc = KnowledgeDocument(
                doc_id=new_doc_id,
                user_id=user_id,
                organization_id=base_doc.organization_id,
                title=base_doc.title,
                description=base_doc.description,
                doc_type=base_doc.doc_type,
                file_id=new_file_id,
                file_size=base_doc.file_size,
                version=new_version,
                parent_version_id=base_doc_id,
                is_latest=True,
                status=DocumentStatus.INDEXED,
                chunk_count=chunk_count,
                chunking_strategy=base_doc.chunking_strategy,
                indexed_at=datetime.now(timezone.utc),
                access_level=base_doc.access_level,
                allowed_users=base_doc.allowed_users,
                allowed_groups=base_doc.allowed_groups,
                denied_users=base_doc.denied_users,
                collection_name=base_doc.collection_name,
                point_ids=point_ids,
                metadata=base_doc.metadata,
                tags=base_doc.tags,
            )

            return await self.create_document(new_doc)

        except Exception as e:
            logger.error(f"Error creating document version: {e}")
            raise

    # ==================== Permission Operations ====================

    async def update_document_permissions(
        self,
        doc_id: str,
        access_level: Optional[AccessLevel] = None,
        allowed_users: Optional[List[str]] = None,
        allowed_groups: Optional[List[str]] = None,
        denied_users: Optional[List[str]] = None,
    ) -> bool:
        """Update document permissions"""
        try:
            update_data = {}

            if access_level is not None:
                update_data["access_level"] = access_level

            if allowed_users is not None:
                update_data["allowed_users"] = allowed_users

            if allowed_groups is not None:
                update_data["allowed_groups"] = allowed_groups

            if denied_users is not None:
                update_data["denied_users"] = denied_users

            if not update_data:
                return False

            result = await self.update_document(doc_id, update_data)
            return result is not None

        except Exception as e:
            logger.error(f"Error updating document permissions: {e}")
            return False

    async def record_permission_change(
        self, history_data: DocumentPermissionHistory
    ) -> bool:
        """Record permission change history"""
        try:
            data = {
                "doc_id": history_data.doc_id,
                "changed_by": history_data.changed_by,
                "old_access_level": history_data.old_access_level.value
                if history_data.old_access_level
                else None,
                "new_access_level": history_data.new_access_level.value
                if history_data.new_access_level
                else None,
                "users_added": history_data.users_added or [],
                "users_removed": history_data.users_removed or [],
                "groups_added": history_data.groups_added or [],
                "groups_removed": history_data.groups_removed or [],
                "changed_at": datetime.now(timezone.utc).isoformat(),
            }

            async with self.db:
                count = await self.db.insert_into(
                    self.permission_history_table, [data], schema=self.schema
                )

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error recording permission change: {e}")
            return False

    async def get_permission_history(
        self, doc_id: str, limit: int = 50
    ) -> List[DocumentPermissionHistory]:
        """Get permission change history for a document"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.permission_history_table}
                WHERE doc_id = $1
                ORDER BY changed_at DESC
                LIMIT $2
            """
            params = [doc_id, limit]

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            # Convert protobuf JSONB fields
            for row in results:
                for field in ["users_added", "users_removed", "groups_added", "groups_removed"]:
                    if field in row:
                        row[field] = self._convert_protobuf_to_native(row[field])

            return [DocumentPermissionHistory.model_validate(row) for row in results]

        except Exception as e:
            logger.error(f"Error getting permission history: {e}")
            return []

    # ==================== Statistics ====================

    async def get_user_stats(
        self, user_id: str, organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user's document statistics"""
        try:
            conditions = ["user_id = $1", "is_latest = true"]
            params = [user_id]

            if organization_id:
                conditions.append("organization_id = $2")
                params.append(organization_id)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    COUNT(*) as total_documents,
                    SUM(CASE WHEN status = 'indexed' THEN 1 ELSE 0 END) as indexed_documents,
                    SUM(chunk_count) as total_chunks,
                    SUM(file_size) as total_size_bytes,
                    doc_type,
                    status
                FROM {self.schema}.{self.documents_table}
                WHERE {where_clause}
                GROUP BY doc_type, status
            """

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            # Aggregate results
            stats = {
                "total_documents": 0,
                "indexed_documents": 0,
                "total_chunks": 0,
                "total_size_bytes": 0,
                "by_type": {},
                "by_status": {},
            }

            for row in results:
                stats["total_documents"] += row.get("total_documents", 0)
                stats["indexed_documents"] += row.get("indexed_documents", 0)
                stats["total_chunks"] += row.get("total_chunks", 0)
                stats["total_size_bytes"] += row.get("total_size_bytes", 0)

                doc_type = row.get("doc_type", "unknown")
                status = row.get("status", "unknown")

                stats["by_type"][doc_type] = stats["by_type"].get(doc_type, 0) + row.get(
                    "total_documents", 0
                )
                stats["by_status"][status] = stats["by_status"].get(status, 0) + row.get(
                    "total_documents", 0
                )

            return stats

        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {
                "total_documents": 0,
                "indexed_documents": 0,
                "total_chunks": 0,
                "total_size_bytes": 0,
                "by_type": {},
                "by_status": {},
            }

    # ==================== Health Check ====================

    async def check_connection(self) -> bool:
        """Check database connection"""
        try:
            query = "SELECT 1"
            async with self.db:
                result = await self.db.query_row(query, [])
            return result is not None
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
