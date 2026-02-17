-- Media Service Migration: Add Digital Analytics AI metadata caching
-- Version: 002
-- Date: 2025-01-22
--
-- Purpose: 扩展 photo_metadata 表以缓存 Digital Analytics Service 返回的 AI 分析结果
--
-- Architecture:
-- - Digital Analytics Service (isA_Data) 存储向量索引和语义信息 (Qdrant)
-- - Media Service 缓存 AI 分析结果到 PostgreSQL，用于:
--   1. 快速查询 (不需要每次调用 Digital Analytics)
--   2. 离线可用性 (Digital Analytics Service 挂了也能查询基本信息)
--   3. 复合查询 (AI tags + 用户标签 + 相册 + 日期范围)

-- 添加 Digital Analytics 缓存字段到 photo_metadata 表
ALTER TABLE media.photo_metadata
ADD COLUMN IF NOT EXISTS ai_description TEXT,                    -- VLM 生成的图像描述
ADD COLUMN IF NOT EXISTS ai_tags TEXT[],                         -- AI 生成的语义标签
ADD COLUMN IF NOT EXISTS ai_categories TEXT[],                   -- AI 分类 (nature, urban, portrait, etc.)
ADD COLUMN IF NOT EXISTS ai_mood VARCHAR(100),                   -- 情绪分析 (happy, peaceful, energetic, etc.)
ADD COLUMN IF NOT EXISTS ai_style VARCHAR(100),                  -- 风格分析 (modern, vintage, minimalist, etc.)
ADD COLUMN IF NOT EXISTS ai_dominant_colors JSONB,               -- 主要颜色 [{color: "#FF5733", percentage: 0.45}, ...]
ADD COLUMN IF NOT EXISTS ai_objects_detected JSONB,              -- 检测到的物体 [{object: "person", confidence: 0.95, bbox: [...]}]
ADD COLUMN IF NOT EXISTS ai_faces_detected JSONB,                -- 人脸检测 [{bbox: [...], age: "25-35", gender: "female"}]
ADD COLUMN IF NOT EXISTS ai_text_detected JSONB,                 -- OCR 文本检测 [{text: "...", bbox: [...]}]

-- Digital Analytics Service 引用
ADD COLUMN IF NOT EXISTS knowledge_id VARCHAR(255),              -- Qdrant 中的向量 ID
ADD COLUMN IF NOT EXISTS collection_name VARCHAR(255),           -- Qdrant 集合名称 (通常为 "user_{user_id}_media")
ADD COLUMN IF NOT EXISTS vector_indexed BOOLEAN DEFAULT false,   -- 是否已建立向量索引

-- 处理状态
ADD COLUMN IF NOT EXISTS ai_processing_status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, failed
ADD COLUMN IF NOT EXISTS ai_processing_error TEXT,              -- 处理失败时的错误信息

-- 时间戳
ADD COLUMN IF NOT EXISTS ai_indexed_at TIMESTAMPTZ,             -- AI 索引完成时间
ADD COLUMN IF NOT EXISTS ai_last_synced_at TIMESTAMPTZ;         -- 最后同步时间

-- 创建索引以支持快速查询
CREATE INDEX IF NOT EXISTS idx_photo_metadata_ai_tags ON media.photo_metadata USING GIN(ai_tags);
CREATE INDEX IF NOT EXISTS idx_photo_metadata_ai_categories ON media.photo_metadata USING GIN(ai_categories);
CREATE INDEX IF NOT EXISTS idx_photo_metadata_knowledge_id ON media.photo_metadata(knowledge_id) WHERE knowledge_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_photo_metadata_collection_name ON media.photo_metadata(collection_name) WHERE collection_name IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_photo_metadata_vector_indexed ON media.photo_metadata(vector_indexed) WHERE vector_indexed = true;
CREATE INDEX IF NOT EXISTS idx_photo_metadata_ai_processing_status ON media.photo_metadata(ai_processing_status);
CREATE INDEX IF NOT EXISTS idx_photo_metadata_ai_indexed_at ON media.photo_metadata(ai_indexed_at DESC) WHERE ai_indexed_at IS NOT NULL;

-- 复合索引：用于复杂查询
-- 示例查询: SELECT * FROM media.photo_metadata WHERE user_id = 'alice' AND 'sunset' = ANY(ai_tags) AND ai_processing_status = 'completed'
CREATE INDEX IF NOT EXISTS idx_photo_metadata_user_ai_status ON media.photo_metadata(user_id, ai_processing_status);

-- 注释
COMMENT ON COLUMN media.photo_metadata.ai_description IS 'VLM 生成的图像描述 (来自 Digital Analytics Service)';
COMMENT ON COLUMN media.photo_metadata.ai_tags IS 'AI 生成的语义标签数组';
COMMENT ON COLUMN media.photo_metadata.ai_categories IS 'AI 分类标签 (nature, urban, portrait, etc.)';
COMMENT ON COLUMN media.photo_metadata.knowledge_id IS 'Qdrant 向量数据库中的 knowledge ID';
COMMENT ON COLUMN media.photo_metadata.collection_name IS 'Qdrant 集合名称';
COMMENT ON COLUMN media.photo_metadata.vector_indexed IS '是否已建立向量索引 (用于语义搜索)';
COMMENT ON COLUMN media.photo_metadata.ai_processing_status IS 'AI 处理状态: pending, processing, completed, failed';
COMMENT ON COLUMN media.photo_metadata.ai_indexed_at IS 'AI 索引完成时间';

-- 示例查询：

-- 1. 查找所有包含"日落"标签的照片
-- SELECT file_id, ai_description, ai_tags
-- FROM media.photo_metadata
-- WHERE user_id = 'alice' AND 'sunset' = ANY(ai_tags);

-- 2. 查找特定类别的照片
-- SELECT file_id, ai_description, ai_categories
-- FROM media.photo_metadata
-- WHERE user_id = 'alice' AND 'nature' = ANY(ai_categories);

-- 3. 复合查询：风景类照片 + 特定日期范围
-- SELECT pm.file_id, pm.ai_description, pm.photo_taken_at
-- FROM media.photo_metadata pm
-- WHERE pm.user_id = 'alice'
--   AND 'landscape' = ANY(pm.ai_categories)
--   AND pm.photo_taken_at BETWEEN '2024-01-01' AND '2024-12-31'
--   AND pm.ai_processing_status = 'completed'
-- ORDER BY pm.photo_taken_at DESC;

-- 4. 查找未索引的照片（需要处理）
-- SELECT file_id, ai_processing_status, created_at
-- FROM media.photo_metadata
-- WHERE user_id = 'alice'
--   AND (vector_indexed = false OR ai_processing_status = 'pending')
-- ORDER BY created_at DESC;
