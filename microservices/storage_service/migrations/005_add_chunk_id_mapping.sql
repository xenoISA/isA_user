-- Storage Service - Add Chunk ID Mapping
-- Version: 005
-- Date: 2025-11-05
-- Description: 添加 chunk_id 字段用于关联 Qdrant 向量数据库

-- 添加 chunk_id 字段（Qdrant 中的向量 ID）
ALTER TABLE storage.storage_intelligence_index
ADD COLUMN IF NOT EXISTS chunk_id TEXT;

-- 创建索引用于快速查找
CREATE INDEX IF NOT EXISTS idx_storage_intel_chunk_id
ON storage.storage_intelligence_index(chunk_id);

-- 注释
COMMENT ON COLUMN storage.storage_intelligence_index.chunk_id IS 'Qdrant 向量数据库中的 chunk ID，用于关联向量搜索结果';

-- 说明关联关系：
-- chunk_id (Qdrant) ←→ file_id (PostgreSQL storage_files) ←→ object_name (MinIO)
-- 这样就可以：
-- 1. 通过向量搜索找到 chunk_id
-- 2. 通过 chunk_id 找到 file_id
-- 3. 通过 file_id 找到 MinIO 的存储位置和下载 URL
