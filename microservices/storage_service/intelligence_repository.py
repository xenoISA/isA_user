"""
Storage Service - Intelligence Repository

智能文档索引的数据访问层
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from core.database.supabase_client import get_supabase_client
from .intelligence_models import IndexedDocument, DocumentStatus, ChunkingStrategy

logger = logging.getLogger(__name__)


class IntelligenceRepository:
    """智能索引数据访问层"""

    def __init__(self):
        self.supabase = get_supabase_client()
        self.table = "storage_intelligence_index"

    async def create_index_record(self, doc_data: IndexedDocument) -> IndexedDocument:
        """创建文档索引记录"""
        try:
            data = {
                "doc_id": doc_data.doc_id,
                "file_id": doc_data.file_id,
                "user_id": doc_data.user_id,
                "organization_id": doc_data.organization_id,
                "title": doc_data.title,
                "content_preview": doc_data.content_preview,
                "status": doc_data.status.value,
                "chunking_strategy": doc_data.chunking_strategy.value,
                "chunk_count": doc_data.chunk_count,
                "metadata": doc_data.metadata,
                "tags": doc_data.tags,
                "search_count": 0,
                "indexed_at": datetime.utcnow().isoformat() if doc_data.status == DocumentStatus.INDEXED else None,
                "updated_at": datetime.utcnow().isoformat()
            }

            result = self.supabase.table(self.table).insert(data).execute()

            if result.data:
                return IndexedDocument.model_validate(result.data[0])
            return None

        except Exception as e:
            logger.error(f"Error creating index record: {e}")
            raise

    async def get_by_file_id(self, file_id: str, user_id: str) -> Optional[IndexedDocument]:
        """根据文件ID获取索引记录"""
        try:
            result = self.supabase.table(self.table).select("*")\
                .eq("file_id", file_id)\
                .eq("user_id", user_id)\
                .neq("status", DocumentStatus.DELETED.value)\
                .execute()

            if result.data and len(result.data) > 0:
                return IndexedDocument.model_validate(result.data[0])
            return None

        except Exception as e:
            logger.error(f"Error getting index by file_id: {e}")
            raise

    async def update_status(
        self,
        doc_id: str,
        status: DocumentStatus,
        chunk_count: Optional[int] = None
    ) -> bool:
        """更新索引状态"""
        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat()
            }

            if chunk_count is not None:
                update_data["chunk_count"] = chunk_count

            if status == DocumentStatus.INDEXED:
                update_data["indexed_at"] = datetime.utcnow().isoformat()

            result = self.supabase.table(self.table)\
                .update(update_data)\
                .eq("doc_id", doc_id)\
                .execute()

            return len(result.data) > 0 if result.data else False

        except Exception as e:
            logger.error(f"Error updating index status: {e}")
            return False

    async def increment_search_count(self, doc_id: str) -> bool:
        """增加搜索计数"""
        try:
            result = self.supabase.table(self.table)\
                .select("search_count")\
                .eq("doc_id", doc_id)\
                .single().execute()

            if result.data:
                current_count = result.data.get("search_count", 0)

                update_data = {
                    "search_count": current_count + 1,
                    "last_accessed_at": datetime.utcnow().isoformat()
                }

                result = self.supabase.table(self.table)\
                    .update(update_data)\
                    .eq("doc_id", doc_id)\
                    .execute()

                return len(result.data) > 0 if result.data else False
            return False

        except Exception as e:
            logger.error(f"Error incrementing search count: {e}")
            return False

    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户智能统计"""
        try:
            result = self.supabase.table(self.table).select("*")\
                .eq("user_id", user_id)\
                .neq("status", DocumentStatus.DELETED.value)\
                .execute()

            stats = {
                "indexed_files": 0,
                "total_chunks": 0,
                "total_searches": 0
            }

            if result.data:
                stats["indexed_files"] = len([d for d in result.data if d.get("status") == "indexed"])
                stats["total_chunks"] = sum(d.get("chunk_count", 0) for d in result.data)
                stats["total_searches"] = sum(d.get("search_count", 0) for d in result.data)

            return stats

        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {"indexed_files": 0, "total_chunks": 0, "total_searches": 0}
