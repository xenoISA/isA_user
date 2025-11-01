-- Storage Service Intelligence Index Migration
-- Version: 002
-- Date: 2025-10-01
-- Description: 添加智能文档索引表 (集成到storage_service)

-- ==================== 智能索引表 ====================

CREATE TABLE IF NOT EXISTS storage.storage_intelligence_index (
    id SERIAL PRIMARY KEY,
    doc_id TEXT UNIQUE NOT NULL,
    file_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    organization_id TEXT,

    -- 文档信息
    title TEXT NOT NULL,
    content_preview TEXT,

    -- 索引状态
    status TEXT NOT NULL DEFAULT 'pending',
    chunking_strategy TEXT NOT NULL DEFAULT 'semantic',
    chunk_count INTEGER DEFAULT 0,

    -- 元数据
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- 统计
    search_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,

    -- 时间戳
    indexed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_index_status CHECK (status IN ('pending', 'processing', 'indexed', 'failed', 'deleted')),
    CONSTRAINT valid_chunking_strategy CHECK (chunking_strategy IN ('fixed', 'semantic', 'sliding_window', 'recursive'))
);

-- 创建索引
CREATE INDEX idx_storage_intel_user_id ON storage.storage_intelligence_index(user_id) WHERE status != 'deleted';
CREATE INDEX idx_storage_intel_file_id ON storage.storage_intelligence_index(file_id);
CREATE INDEX idx_storage_intel_status ON storage.storage_intelligence_index(status);
CREATE INDEX idx_storage_intel_tags ON storage.storage_intelligence_index USING GIN(tags);
CREATE INDEX idx_storage_intel_metadata ON storage.storage_intelligence_index USING GIN(metadata);

-- 触发器 (使用统一的 update_updated_at 函数)
CREATE TRIGGER trigger_update_storage_intel_updated_at
    BEFORE UPDATE ON storage.storage_intelligence_index
    FOR EACH ROW
    EXECUTE FUNCTION storage.update_updated_at();

-- 授权
GRANT ALL ON storage.storage_intelligence_index TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON storage.storage_intelligence_index TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE storage.storage_intelligence_index_id_seq TO authenticated;

-- 注释
COMMENT ON TABLE storage.storage_intelligence_index IS '智能文档索引表 - 存储文件的智能索引元数据';
COMMENT ON COLUMN storage.storage_intelligence_index.doc_id IS '文档唯一标识符';
COMMENT ON COLUMN storage.storage_intelligence_index.file_id IS '关联的存储文件ID (外键到storage_files)';
COMMENT ON COLUMN storage.storage_intelligence_index.chunk_count IS '文档分块数量';
COMMENT ON COLUMN storage.storage_intelligence_index.search_count IS '搜索次数统计';
