"""
Intelligence Repository - Data access layer for storage intelligence index
Handles database operations for AI/RAG document indexing

Uses PostgresClient with gRPC for PostgreSQL access
Migrated from Supabase to PostgresClient - 2025-10-24
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient
from .intelligence_models import IndexedDocument, DocumentStatus, ChunkingStrategy

logger = logging.getLogger(__name__)


class IntelligenceRepository:
    """Intelligence repository - data access layer for document indexing"""

    def __init__(self):
        """Initialize intelligence repository with PostgresClient"""
        # TODO: Use Consul service discovery instead of hardcoded host/port
        self.db = PostgresClient(
            host='isa-postgres-grpc',
            port=50061,
            user_id='storage_service'
        )
        # Table names (storage schema)
        self.schema = "storage"
        self.table = "storage_intelligence_index"

    async def create_index_record(self, doc_data: IndexedDocument) -> Optional[IndexedDocument]:
        """Create a new document index record"""
        try:
            data = {
                "doc_id": doc_data.doc_id,
                "file_id": doc_data.file_id,
                "user_id": doc_data.user_id,
                "organization_id": doc_data.organization_id,
                "title": doc_data.title,
                "content_preview": doc_data.content_preview,
                "status": doc_data.status.value if hasattr(doc_data.status, 'value') else doc_data.status,
                "chunking_strategy": doc_data.chunking_strategy.value if hasattr(doc_data.chunking_strategy, 'value') else doc_data.chunking_strategy,
                "chunk_count": doc_data.chunk_count or 0,
                "metadata": doc_data.metadata or {},
                "tags": doc_data.tags or [],
                "search_count": 0,
                "last_accessed_at": None,
                "indexed_at": datetime.now(timezone.utc) if doc_data.status == DocumentStatus.INDEXED else None,
                "updated_at": datetime.now(timezone.utc)
            }

            with self.db:
                count = self.db.insert_into(self.table, [data], schema=self.schema)

            if count > 0:
                return await self.get_by_doc_id(doc_data.doc_id)
            return None

        except Exception as e:
            logger.error(f"Error creating index record: {e}")
            raise

    async def get_by_doc_id(self, doc_id: str) -> Optional[IndexedDocument]:
        """Get index record by doc_id"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table}
                WHERE doc_id = $1 AND status != 'deleted'
            """
            params = [doc_id]

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            if result:
                return IndexedDocument.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting index by doc_id: {e}")
            return None

    async def get_by_file_id(self, file_id: str, user_id: str) -> Optional[IndexedDocument]:
        """Get index record by file_id and user_id"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.table}
                WHERE file_id = $1 AND user_id = $2 AND status != 'deleted'
            """
            params = [file_id, user_id]

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            if result:
                return IndexedDocument.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting index by file_id: {e}")
            return None

    async def list_user_indexes(
        self,
        user_id: str,
        status: Optional[DocumentStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[IndexedDocument]:
        """List indexed documents for a user"""
        try:
            conditions = ["user_id = $1", "status != 'deleted'"]
            params = [user_id]
            param_count = 1

            if status:
                param_count += 1
                status_value = status.value if hasattr(status, 'value') else status
                conditions.append(f"status = ${param_count}")
                params.append(status_value)

            where_clause = " AND ".join(conditions)
            query = f"""
                SELECT * FROM {self.schema}.{self.table}
                WHERE {where_clause}
                ORDER BY updated_at DESC
                LIMIT {limit} OFFSET {offset}
            """

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [IndexedDocument.model_validate(row) for row in results]

        except Exception as e:
            logger.error(f"Error listing user indexes: {e}")
            return []

    async def update_status(
        self,
        doc_id: str,
        status: DocumentStatus,
        chunk_count: Optional[int] = None
    ) -> bool:
        """Update index status"""
        try:
            status_value = status.value if hasattr(status, 'value') else status

            if status == DocumentStatus.INDEXED and chunk_count is not None:
                query = f"""
                    UPDATE {self.schema}.{self.table}
                    SET status = $1, chunk_count = $2, indexed_at = $3, updated_at = $3
                    WHERE doc_id = $4
                """
                params = [status_value, chunk_count, datetime.now(timezone.utc), doc_id]
            elif chunk_count is not None:
                query = f"""
                    UPDATE {self.schema}.{self.table}
                    SET status = $1, chunk_count = $2, updated_at = $3
                    WHERE doc_id = $4
                """
                params = [status_value, chunk_count, datetime.now(timezone.utc), doc_id]
            else:
                query = f"""
                    UPDATE {self.schema}.{self.table}
                    SET status = $1, updated_at = $2
                    WHERE doc_id = $3
                """
                params = [status_value, datetime.now(timezone.utc), doc_id]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count > 0

        except Exception as e:
            logger.error(f"Error updating index status: {e}")
            return False

    async def increment_search_count(self, doc_id: str) -> bool:
        """Increment search count and update last_accessed_at"""
        try:
            query = f"""
                UPDATE {self.schema}.{self.table}
                SET
                    search_count = search_count + 1,
                    last_accessed_at = $1
                WHERE doc_id = $2
            """
            params = [datetime.now(timezone.utc), doc_id]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count > 0

        except Exception as e:
            logger.error(f"Error incrementing search count: {e}")
            return False

    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user intelligence statistics"""
        try:
            query = f"""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'indexed') as indexed_files,
                    COALESCE(SUM(chunk_count), 0) as total_chunks,
                    COALESCE(SUM(search_count), 0) as total_searches
                FROM {self.schema}.{self.table}
                WHERE user_id = $1 AND status != 'deleted'
            """
            params = [user_id]

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            if result:
                return {
                    "indexed_files": result.get("indexed_files", 0),
                    "total_chunks": result.get("total_chunks", 0),
                    "total_searches": result.get("total_searches", 0)
                }

            return {
                "indexed_files": 0,
                "total_chunks": 0,
                "total_searches": 0
            }

        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {
                "indexed_files": 0,
                "total_chunks": 0,
                "total_searches": 0
            }

    async def delete_index(self, doc_id: str, user_id: str) -> bool:
        """Soft delete an index (set status to deleted)"""
        try:
            query = f"""
                UPDATE {self.schema}.{self.table}
                SET status = 'deleted', updated_at = $1
                WHERE doc_id = $2 AND user_id = $3
            """
            params = [datetime.now(timezone.utc), doc_id, user_id]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count > 0

        except Exception as e:
            logger.error(f"Error deleting index: {e}")
            raise
