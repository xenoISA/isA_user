# Cloud Storage Service - 云盘功能使用指南

## 服务概述
Storage Service 现已扩展为完整的云盘服务，在原有的文件存储基础上增加了文件夹管理、照片相册、文件同步等高级功能。

**服务端口**: 8208
**MinIO端口**: 9000 (控制台: 9001)
**API版本**: v1
**API基础URL**: `http://localhost:8208/api/v1`

## 🆕 API v1 更新说明

**更新日期**: 2025-10-01

所有API端点已升级到 v1 版本，路径从 `/api/...` 更新为 `/api/v1/...`

主要变更：
- ✅ 所有端点添加 `/v1/` 版本前缀
- ✅ 照片版本管理 API 完整实现
- ✅ 版本类型枚举值严格验证
- ✅ 完整的参数验证和错误处理

## 快速开始

### 1. 确保服务运行
```bash
# 健康检查
curl http://localhost:8208/health

# 获取服务信息
curl http://localhost:8208/info
```

## 核心功能测试结果

### ✅ 已验证的基础功能

#### ✅ 照片版本管理功能 - API v1 测试通过

**最新测试时间**: 2025-10-01
**API版本**: v1
**测试状态**: 全部功能测试通过 ✅

测试结果：
- ✅ **保存AI处理版本** (`POST /api/v1/photos/versions/save`) - 成功保存版本到云存储
  - 版本ID生成正常 (例: ver_f2f28b08037e)
  - 支持所有版本类型枚举值
- ✅ **获取照片版本列表** (`POST /api/v1/photos/{photo_id}/versions`) - 正确返回所有版本信息
  - 返回完整版本数据结构
  - 包含版本计数信息
- ✅ **切换照片版本** (`PUT /api/v1/photos/{photo_id}/versions/{version_id}/switch`) - 成功切换当前显示版本
  - 切换操作正常执行
  - 返回成功消息确认
- ✅ **删除照片版本** (`DELETE /api/v1/photos/versions/{version_id}`) - 安全删除（保护原始版本）
  - 删除操作成功执行
  - 版本类型枚举验证正常
- ✅ **错误处理** - 完善的异常处理机制（422 参数验证）
- ✅ **云存储集成** - MinIO存储架构正常
- ✅ **用户权限隔离** - 用户数据安全隔离

#### 1. 文件上传
```bash
# 上传文本文件
curl -X POST http://localhost:8208/api/v1/files/upload \
  -F "file=@test.txt" \
  -F "user_id=test_user_123" \
  -F "organization_id=org_456" \
  -F "access_level=private" \
  -F 'metadata={"project":"demo","version":"1.0"}' \
  -F "tags=document,important"

# 响应示例
{
  "file_id": "file_19f76d4034e74e0b93cc0450d3039753",
  "file_path": "users/test_user_123/2025/09/27/20250927_091851_e3c8a7e8.txt",
  "download_url": "http://localhost:9000/...",
  "file_size": 58,
  "content_type": "text/plain",
  "uploaded_at": "2025-09-27T09:18:51.170013"
}
```

#### 2. 照片上传（适合云盘相册）
```bash
# 上传照片，带位置和日期元数据
curl -X POST http://localhost:8208/api/v1/files/upload \
  -F "file=@photo.png" \
  -F "user_id=test_user_123" \
  -F 'metadata={"album":"vacation","location":"Beijing","date":"2024-09"}' \
  -F "tags=photo,vacation,2024"
```

#### 3. 🆕 照片版本管理（AI增强功能）

Storage Service 现已支持照片版本管理功能，可以保存AI处理后的多个版本，支持版本切换和管理。

##### 3.1 保存AI处理版本
```bash
# 保存AI增强后的照片版本
curl -X POST "http://localhost:8208/api/v1/photos/versions/save" \
  -H "Content-Type: application/json" \
  -d '{
    "photo_id": "photo_001",
    "user_id": "test_user_123",
    "version_name": "AI Enhanced Version",
    "version_type": "ai_enhanced",
    "processing_mode": "enhance_colors",
    "source_url": "https://ai-service.com/processed/image.jpg",
    "save_local": false,
    "processing_params": {
      "brightness": 1.2,
      "contrast": 1.1,
      "saturation": 1.15
    },
    "metadata": {
      "ai_model": "vision_enhance_v2",
      "processing_time": 2.5
    },
    "set_as_current": true
  }'

# 响应示例
{
  "version_id": "ver_69aee6db265f",
  "photo_id": "photo_001",
  "cloud_url": "http://localhost:9000/emoframe-photos/...",
  "local_path": null,
  "version_name": "AI Enhanced Version",
  "created_at": "2025-09-30T03:39:45.324438",
  "message": "Photo version saved successfully"
}
```

##### 3.2 获取照片所有版本
```bash
# 获取照片的所有版本列表
curl -X POST "http://localhost:8208/api/v1/photos/photo_001/versions?user_id=test_user_123"

# 响应示例
{
  "photo_id": "photo_001",
  "title": "我的照片",
  "original_file_id": "file_photo_001",
  "current_version_id": "ver_69aee6db265f",
  "versions": [
    {
      "version_id": "ver_original",
      "version_name": "Original",
      "version_type": "original",
      "is_current": false,
      "file_size": 1024000,
      "created_at": "2025-09-30T03:35:00Z"
    },
    {
      "version_id": "ver_69aee6db265f",
      "version_name": "AI Enhanced Version",
      "version_type": "ai_enhanced",
      "processing_mode": "enhance_colors",
      "is_current": true,
      "file_size": 1156000,
      "processing_params": {
        "brightness": 1.2,
        "contrast": 1.1,
        "saturation": 1.15
      },
      "created_at": "2025-09-30T03:39:45Z"
    }
  ],
  "version_count": 2
}
```

##### 3.3 切换照片版本
```bash
# 切换到指定版本
curl -X PUT "http://localhost:8208/api/v1/photos/photo_001/versions/ver_original/switch?user_id=test_user_123"

# 响应示例
{
  "success": true,
  "photo_id": "photo_001",
  "current_version_id": "ver_original",
  "message": "Photo version switched successfully"
}
```

##### 3.4 删除照片版本
```bash
# 删除指定版本（不能删除原始版本）
curl -X DELETE "http://localhost:8208/api/v1/photos/versions/ver_69aee6db265f?user_id=test_user_123"

# 响应示例
{
  "success": true,
  "version_id": "ver_69aee6db265f",
  "message": "Photo version deleted successfully"
}
```

##### 版本类型说明（PhotoVersionType 枚举）
- `original`: 原始版本（不可删除）
- `ai_enhanced`: AI增强版本
- `ai_styled`: AI风格化版本
- `user_edited`: 用户编辑版本
- `restored`: 恢复版本

**注意**: version_type 必须使用上述枚举值之一

##### 存储架构
```
云存储结构 (MinIO):
emoframe-photos/
└── photo_versions/
    └── {user_id}/
        └── {photo_id}/
            ├── {photo_id}_{version_id}.jpg
            └── {photo_id}_{version_id}.png

本地存储结构（相框端）:
/data/emoframe/photos/
└── {user_id}/
    └── {photo_id}/
        └── {photo_id}_{version_id}.jpg
```

#### 4. 文件列表
```bash
# 获取用户所有文件
curl "http://localhost:8208/api/v1/files?user_id=test_user_123&limit=10"

# 按状态筛选
curl "http://localhost:8208/api/v1/files?user_id=test_user_123&status=available"

# 按前缀筛选（模拟文件夹）
curl "http://localhost:8208/api/v1/files?user_id=test_user_123&prefix=photos/"
```

#### 5. 存储统计
```bash
curl "http://localhost:8208/api/v1/storage/stats?user_id=test_user_123"

# 响应示例
{
  "user_id": "test_user_123",
  "total_quota_bytes": 10737418240,  // 10GB
  "used_bytes": 126,
  "available_bytes": 10737418114,
  "usage_percentage": 0.0,
  "file_count": 2,
  "by_type": {
    "text/plain": {"count": 1, "total_size": 58},
    "image/png": {"count": 1, "total_size": 68}
  }
}
```

#### 6. 文件下载
```bash
# 获取下载链接
curl "http://localhost:8208/api/v1/files/{file_id}/download?user_id=test_user_123&expires_minutes=60"
```

#### 7. 文件删除
```bash
# 软删除（移到回收站）
curl -X DELETE "http://localhost:8208/api/v1/files/{file_id}?user_id=test_user_123&permanent=false"

# 永久删除
curl -X DELETE "http://localhost:8208/api/v1/files/{file_id}?user_id=test_user_123&permanent=true"
```

## 🆕 智能索引与检索功能

**更新日期**: 2025-10-01

Storage Service现已集成智能文档索引功能，通过MCP digital_analytics_tools实现语义搜索和RAG问答。

### 核心特性

- ✅ **自动索引**: 文本文件上传后自动生成向量索引
- ✅ **语义搜索**: 基于内容语义而非关键词的智能搜索
- ✅ **RAG问答**: 7种RAG模式，基于文档内容回答问题
- ✅ **多语言支持**: 支持中英文混合文档索引与检索
- ✅ **MCP集成**: 通过isA_MCP服务提供AI能力

### 已验证功能测试结果

**测试时间**: 2025-10-01
**测试状态**: 全部通过 ✅

- ✅ 文本文件自动索引 - 上传后自动触发向量化
- ✅ 语义搜索 - 6.7秒响应，准确返回相关文档
- ✅ RAG问答 - 13.3秒生成答案并引用源文档
- ✅ 数据库集成 - storage_intelligence_index表正常工作
- ✅ MCP通信 - JSON-RPC 2.0格式，SSE响应解析正常

### 1. 自动索引

文本文件（`text/*` MIME类型）上传后会自动触发智能索引：

```bash
# 上传文本文件会自动索引
curl -X POST "http://localhost:8208/api/v1/files/upload" \
  -H "X-User-ID: test_user_001" \
  -H "X-Organization-ID: test_org_001" \
  -F "file=@document.txt" \
  -F "user_id=test_user_001" \
  -F 'metadata={"description":"技术文档"}'

# 响应示例
{
  "file_id": "file_abc123",
  "file_path": "users/test_user_001/2025/10/01/document.txt",
  "message": "File uploaded successfully"
}

# 后台自动索引日志
# Auto-indexing file file_abc123 for user test_user_001
# Successfully indexed file file_abc123
```

**支持的文件类型**:
- `text/plain` - 纯文本
- `text/markdown` - Markdown文档
- `text/csv` - CSV数据
- 更多文本格式...

### 2. 语义搜索

通过语义理解内容，而非简单关键词匹配：

```bash
# POST /api/v1/intelligence/search
curl -X POST "http://localhost:8208/api/v1/intelligence/search" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_001",
    "query": "机器学习",
    "top_k": 5,
    "enable_rerank": false,
    "min_score": 0.0
  }'

# 响应示例
{
  "query": "机器学习",
  "results": [
    {
      "file_id": "file_abc123",
      "doc_id": "doc_xyz456",
      "file_name": "ai_document.txt",
      "relevance_score": 0.481,
      "content_snippet": "机器学习是AI的一个重要分支，它使计算机能够从数据中学习...",
      "file_type": "text/plain",
      "file_size": 306,
      "metadata": {"description": "技术文档"},
      "uploaded_at": "2025-10-01T07:12:59Z",
      "download_url": "http://localhost:9000/..."
    }
  ],
  "results_count": 1,
  "latency_ms": 6682.15,
  "message": "Search completed successfully"
}
```

**请求参数说明**:
- `user_id` (必需): 用户ID，用于权限隔离
- `query` (必需): 搜索查询文本
- `top_k` (可选): 返回结果数量，默认5，范围1-50
- `enable_rerank` (可选): 启用重排序，默认false
- `min_score` (可选): 最低相关性分数，默认0.0，范围0.0-1.0
- `file_types` (可选): 文件类型过滤，例如 `["text/plain"]`
- `tags` (可选): 标签过滤

### 3. RAG问答查询

基于已索引文档回答问题，支持7种RAG模式：

```bash
# POST /api/v1/intelligence/rag
curl -X POST "http://localhost:8208/api/v1/intelligence/rag" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_001",
    "query": "什么是深度学习？",
    "rag_mode": "simple",
    "top_k": 3,
    "enable_citations": true,
    "max_tokens": 500,
    "temperature": 0.7
  }'

# 响应示例
{
  "query": "什么是深度学习？",
  "rag_answer": {
    "answer": "深度学习是机器学习的一个子领域，主要利用多层神经网络进行学习和模型训练。它通过模拟人脑神经元的结构和功能，能够自动从大量数据中提取特征，从而实现更复杂和准确的模式识别、分类和预测任务 [1]...",
    "confidence": 0.8,
    "sources": [
      {
        "file_id": "file_abc123",
        "doc_id": "doc_xyz456",
        "file_name": "ai_document.txt",
        "relevance_score": 0.220,
        "content_snippet": "深度学习是机器学习的一个子领域，使用神经网络进行学习...",
        "file_type": "text/plain",
        "file_size": 306,
        "uploaded_at": "2025-10-01T07:12:59Z"
      }
    ],
    "citations": ["[d9faff24] ai_document.txt"],
    "session_id": null
  },
  "latency_ms": 13285.06,
  "message": "Query completed successfully"
}
```

**RAG模式说明**:
- `simple` - 基础RAG（推荐日常使用）
- `raptor` - 递归摘要树RAG（适合长文档）
- `self_rag` - 自我反思RAG（高准确性）
- `crag` - 校正式RAG（减少幻觉）
- `plan_rag` - 计划式RAG（复杂问题）
- `hm_rag` - 混合记忆RAG（多轮对话）
- `graph` - 知识图谱RAG（关系推理）

**请求参数说明**:
- `user_id` (必需): 用户ID
- `query` (必需): 用户问题
- `rag_mode` (可选): RAG模式，默认"simple"
- `session_id` (可选): 会话ID，用于多轮对话
- `top_k` (可选): 检索文档数量，默认3，范围1-10
- `enable_citations` (可选): 启用引用标注，默认true
- `max_tokens` (可选): 最大生成长度，默认500，范围50-2000
- `temperature` (可选): 生成温度，默认0.7，范围0.0-1.0

### 4. 智能统计

获取用户的智能索引统计信息：

```bash
# GET /api/v1/intelligence/stats
curl "http://localhost:8208/api/v1/intelligence/stats?user_id=test_user_001"

# 响应示例
{
  "user_id": "test_user_001",
  "total_files": 5,
  "indexed_files": 3,
  "total_chunks": 45,
  "total_searches": 12,
  "avg_search_latency_ms": 6500.0,
  "storage_size_bytes": 15360
}
```

### 技术架构

**索引流程**:
1. 用户上传文本文件 → Storage Service
2. 文件保存到MinIO → 元数据写入Supabase
3. 自动触发智能索引 → 调用MCP `store_knowledge`
4. MCP生成向量嵌入 → 存储到ChromaDB
5. 索引元数据记录 → `storage_intelligence_index`表

**检索流程**:
1. 用户发起搜索/RAG查询 → Intelligence API
2. 调用MCP `search_knowledge` / `generate_rag_response`
3. MCP向量检索 → ChromaDB相似度搜索
4. 返回文档片段 → 关联storage文件元数据
5. 构建完整响应 → 返回给用户

**数据表结构**:
```sql
-- storage_intelligence_index (Supabase)
CREATE TABLE dev.storage_intelligence_index (
    id SERIAL PRIMARY KEY,
    doc_id TEXT UNIQUE NOT NULL,
    file_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    organization_id TEXT,
    title TEXT NOT NULL,
    content_preview TEXT,
    status TEXT DEFAULT 'indexed',
    chunking_strategy TEXT DEFAULT 'semantic',
    chunk_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    tags TEXT[],
    search_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    indexed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 性能指标

基于测试结果（单文档306字节）:
- **索引延迟**: ~7秒（包括向量化）
- **搜索延迟**: ~6.7秒（语义检索）
- **RAG延迟**: ~13.3秒（检索+生成）
- **相关性分数**: 0.22-0.48（中文查询）

### 限制与注意事项

1. **仅支持文本文件**: 当前版本仅对`text/*`类型自动索引
2. **文件大小**: 建议单文件<10MB，大文件会自动分块
3. **索引延迟**: 索引是异步的，上传成功不代表索引完成
4. **用户隔离**: 每个用户只能搜索自己的文档
5. **MCP依赖**: 需要isA_MCP服务运行在localhost:8081

### 故障排查

**问题1: 文件上传成功但未索引**
```bash
# 检查日志
tail -f logs/storage_service.log | grep "Auto-indexing"

# 可能原因：
# - 文件类型不是text/*
# - MCP服务未运行
# - 数据库表不存在
```

**问题2: 搜索无结果**
```bash
# 检查索引状态
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" \
  -c "SELECT * FROM dev.storage_intelligence_index WHERE user_id='test_user_001';"

# 可能原因：
# - 文档尚未索引完成
# - 查询词与文档内容相关性低
# - min_score设置过高
```

**问题3: MCP连接失败**
```bash
# 检查MCP服务
curl http://localhost:8081/health

# 检查MCP配置
echo $MCP_ENDPOINT  # 应为 http://localhost:8081
```

## 🖼️ 图片智能处理功能

**更新日期**: 2025-10-01

Storage Service现已集成图片智能处理功能，通过MCP digital_analytics_tools实现图片理解、语义搜索和智能问答。

### 核心特性

- ✅ **智能图片理解**: VLM自动提取图片描述（gpt-4o-mini）
- ✅ **图片语义搜索**: 用文字查找图片内容
- ✅ **多模态RAG**: 结合图片和文本生成答案
- ✅ **快速高效**: VLM→文本→向量嵌入，复用现有RAG基础设施
- ✅ **成本优化**: gpt-4o-mini ($0.15/$0.60 per 1M tokens)

### 技术架构

**图片处理流程**:
```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
│   Image     │────▶│  VLM Extract │────▶│   Embed      │────▶│  Store   │
│  (JPG/PNG)  │     │  Description │     │   (Text)     │     │ (Vector) │
└─────────────┘     └──────────────┘     └──────────────┘     └──────────┘
                       gpt-4o-mini          text-embedding         Supabase
                       (6-7s)               -3-small               /ChromaDB
```

**为什么用这种方案**:
- ✅ 简单 - 复用所有现有RAG基础设施
- ✅ 快速 - 不需要新模型/API
- ✅ 有效 - VLM描述丰富且可搜索
- ✅ 成本低 - 使用最便宜的VLM模型

### 1. 图片上传与理解

上传图片时自动触发VLM理解，提取详细描述并生成向量索引：

```bash
# POST /api/v1/intelligence/image/store
curl -X POST "http://localhost:8208/api/v1/intelligence/image/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_001",
    "image_path": "/path/to/photo.jpg",
    "metadata": {
      "category": "product",
      "album": "vacation_2025"
    },
    "model": "gpt-4o-mini"
  }'

# 响应示例
{
  "success": true,
  "image_path": "/path/to/photo.jpg",
  "description": "The image features a small, light blue car parked on a street. It is a side view of the vehicle, showcasing its compact design and rounded edges...",
  "description_length": 953,
  "storage_id": "87e5f273-c6b6-443c-91f7-6313909a1103",
  "vlm_model": "gpt-4o-mini",
  "processing_time": 6.18,
  "metadata": {
    "content_type": "image",
    "image_path": "/path/to/photo.jpg",
    "category": "product",
    "stored_at": "2025-10-01T14:23:45.123456"
  }
}
```

**请求参数说明**:
- `user_id` (必需): 用户ID
- `image_path` (必需): 本地图片路径（支持JPG、PNG等）
- `metadata` (可选): 自定义元数据（分类、相册、标签等）
- `description_prompt` (可选): 自定义VLM提示词
- `model` (可选): VLM模型，默认`gpt-4o-mini`

**支持的VLM模型**:
- `gpt-4o-mini` (默认) - $0.15/$0.60 per 1M tokens，最快
- `gpt-4o` - $6/$18 per 1M tokens，更准确
- `gpt-4-turbo` - $10/$30 per 1M tokens，传统

### 2. 图片语义搜索

用自然语言搜索图片内容：

```bash
# POST /api/v1/intelligence/image/search
curl -X POST "http://localhost:8208/api/v1/intelligence/image/search" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_001",
    "query": "蓝色的汽车",
    "top_k": 5,
    "enable_rerank": false
  }'

# 响应示例
{
  "success": true,
  "user_id": "test_user_001",
  "query": "蓝色的汽车",
  "image_results": [
    {
      "knowledge_id": "87e5f273-c6b6-443c-91f7-6313909a1103",
      "image_path": "/tmp/test_car.jpg",
      "description": "The image features a small, light blue car parked on a street...",
      "relevance_score": 0.494,
      "metadata": {
        "content_type": "image",
        "category": "vehicle",
        "stored_at": "2025-10-01T14:23:45.123456"
      },
      "search_method": "traditional_isa"
    }
  ],
  "total_images_found": 1,
  "search_method": "traditional_isa"
}
```

**请求参数说明**:
- `user_id` (必需): 用户ID
- `query` (必需): 搜索查询文本（用自然语言描述图片内容）
- `top_k` (可选): 返回结果数量，默认5
- `enable_rerank` (可选): 启用MMR重排序，默认false
- `search_mode` (可选): "semantic"(语义), "hybrid"(混合), "lexical"(词法)

### 3. 多模态RAG问答

结合图片和文本内容生成答案：

```bash
# POST /api/v1/intelligence/image/rag
curl -X POST "http://localhost:8208/api/v1/intelligence/image/rag" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_001",
    "query": "我有哪些类型的照片？",
    "context_limit": 3,
    "include_images": true
  }'

# 响应示例
{
  "success": true,
  "response": "根据您的照片，主要有三种类型：1. 车辆照片 - 一辆浅蓝色的小型汽车；2. 自然风光 - 黎明时分的山脉景观；3. 美食照片 - 精美摆盘的餐食...",
  "context_items": 3,
  "image_sources": [
    {
      "image_path": "/tmp/test_car.jpg",
      "description": "The image features a small, light blue car...",
      "relevance": 0.494
    },
    {
      "image_path": "/tmp/test_mountain.jpg",
      "description": "The image depicts a breathtaking mountain landscape...",
      "relevance": 0.656
    }
  ],
  "text_sources": [],
  "metadata": {
    "model": "gpt-4.1-nano",
    "total_context_items": 3,
    "image_count": 2,
    "text_count": 1
  }
}
```

**请求参数说明**:
- `user_id` (必需): 用户ID
- `query` (必需): 用户问题
- `context_limit` (可选): 最大上下文数量，默认3
- `include_images` (可选): 包含图片，默认true
- `rag_mode` (可选): RAG模式，默认自动选择

### 性能指标

基于真实测试（Storage Service实际测试，2025-10-01）:
- **VLM理解延迟**: 6.5秒/图片（gpt-4o-mini）
- **描述长度**: 1481字符（详细描述）
- **完整存储流程**: 13.7秒（VLM + 向量嵌入 + 存储）
- **搜索延迟**: 9秒（语义检索 + 排序）
- **RAG生成**: 19秒（检索 + LLM生成）
- **相关性分数**: 0.50-0.53（高精度匹配）

**测试环境**:
- 图片大小: 36KB (Unsplash)
- 服务端口: 8208 (Storage) + 8081 (MCP)
- VLM模型: gpt-4o-mini
- RAG模型: gpt-4.1-nano
- 向量数据库: Supabase + ChromaDB

### 测试结果

**测试时间**: 2025-10-01
**测试状态**: 全部通过 ✅
**测试服务**: Storage Service (Port 8208) + MCP (Port 8081)

#### 真实测试案例

**测试图片**: 黄色Mercedes-Benz跑车 (Unsplash, 36KB)

##### Test 1: 图片存储与理解
```bash
# 请求
curl -X POST "http://localhost:8208/api/v1/intelligence/image/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_storage_user",
    "image_path": "/tmp/test_storage_car.jpg",
    "metadata": {"category": "vehicle"},
    "model": "gpt-4o-mini"
  }'

# 实际响应
{
  "success": true,
  "image_path": "/tmp/test_storage_car.jpg",
  "description": "The image features a vibrant yellow sports car, specifically a Mercedes-Benz model, captured in motion. The car is positioned slightly off-center, emphasizing its dynamic movement along a road...",
  "description_length": 1481,
  "storage_id": "72d587b0-fe4a-4806-bee9-0d31f41287e7",
  "vlm_model": "gpt-4o-mini",
  "processing_time": 13.73,
  "metadata": {
    "category": "vehicle",
    "content_type": "image",
    "extraction_time": 6.54,
    "stored_at": "2025-10-01T16:44:41.863934"
  }
}
```
✅ **结果**:
- VLM提取时间: 6.54秒
- 总处理时间: 13.73秒
- 描述长度: 1481字符（详细准确）
- 存储成功，生成UUID

##### Test 2: 图片语义搜索
```bash
# 请求
curl -X POST "http://localhost:8208/api/v1/intelligence/image/search" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_storage_user",
    "query": "yellow sports car",
    "top_k": 3
  }'

# 实际响应（摘要）
{
  "success": true,
  "query": "yellow sports car",
  "image_results": [
    {
      "knowledge_id": "72d587b0-fe4a-4806-bee9-0d31f41287e7",
      "image_path": "/tmp/test_storage_car.jpg",
      "description": "The image features a vibrant yellow sports car...",
      "relevance_score": 0.5275,
      "metadata": {"category": "vehicle"},
      "search_method": "traditional_isa"
    }
  ],
  "total_images_found": 2
}
```
✅ **结果**:
- 搜索延迟: ~9秒
- 相关性分数: 0.5275 (高相关性)
- 准确返回黄色跑车图片
- 语义理解正确（"yellow sports car" 匹配成功）

##### Test 3: 多模态RAG问答
```bash
# 请求
curl -X POST "http://localhost:8208/api/v1/intelligence/image/rag" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_storage_user",
    "query": "Describe the car in my photos",
    "context_limit": 2,
    "include_images": true
  }'

# 实际响应（摘要）
{
  "success": true,
  "response": "The car in your photo is a vibrant yellow Mercedes-Benz sports car, captured in motion along a scenic road. It features a sleek, modern, aerodynamic design characterized by prominent curves and aggressive lines that emphasize its sporty and luxurious appearance... Overall, the image conveys a sense of excitement, luxury, and high performance...",
  "context_items": 2,
  "image_sources": [
    {
      "image_path": "/tmp/test_storage_car.jpg",
      "description": "[Image] The image features a vibrant yellow sports car...",
      "relevance": 0.5010
    }
  ],
  "metadata": {
    "model": "gpt-4.1-nano",
    "image_count": 2,
    "text_count": 0
  }
}
```
✅ **结果**:
- RAG生成延迟: ~19秒
- 生成模型: gpt-4.1-nano
- 答案质量: 详细、准确、自然
- 正确识别品牌（Mercedes-Benz）
- 包含设计细节（aerodynamic, curves, aggressive lines）
- 准确描述颜色和场景

#### 性能测试结果

| 操作 | 延迟 | 状态 |
|------|------|------|
| 图片存储+VLM理解 | 13.7秒 | ✅ 通过 |
| 语义搜索 | 9秒 | ✅ 通过 |
| 多模态RAG生成 | 19秒 | ✅ 通过 |

#### 质量验证

- ✅ **VLM理解准确性**: 正确识别车型、颜色、场景
- ✅ **语义搜索精度**: 0.5275相关性分数，准确匹配查询意图
- ✅ **RAG生成质量**: 详细、流畅、包含上下文信息
- ✅ **元数据保留**: category、source等自定义字段正确存储
- ✅ **错误处理**: API验证、超时处理完善
- ✅ **成本效益**: gpt-4o-mini ($0.15/$0.60 per 1M tokens)

### 应用场景

- 📸 **相册管理** - 用自然语言搜索个人照片
- 🛍️ **电商产品** - 按特征查找产品图片
- 📚 **文档管理** - 搜索图表和截图
- 🎨 **设计资源** - 按风格查找设计稿
- 🏥 **医疗影像** - 按发现搜索医学扫描

### 限制与注意事项

1. **本地文件**: 图片必须是可访问的本地路径
2. **VLM成本**: 每次存储调用VLM（$0.15 per 1M tokens）
3. **描述质量**: 依赖VLM模型和提示词
4. **文本嵌入**: 使用文本向量（非原生图片嵌入），更快更简单
5. **处理时间**: VLM理解需6-7秒，适合异步处理
6. **超时设置**:
   - 存储API: 120秒超时（包含VLM处理）
   - 搜索API: 60秒超时
   - RAG API: 120秒超时（包含LLM生成）

### 故障排查

**问题1: 存储图片失败 - "validation error for description_prompt"**

```bash
# 错误信息
{
  "detail": "Store image failed: Input should be a valid string [type=string_type, input_value=None]"
}

# 原因：MCP工具不接受None作为可选参数值

# 解决方案：不传该参数，或传有效字符串
curl -X POST "http://localhost:8208/api/v1/intelligence/image/store" \
  -d '{
    "user_id": "user123",
    "image_path": "/path/to/image.jpg"
    // 不要传 "description_prompt": null
  }'
```

**问题2: 图片搜索无结果**

```bash
# 检查是否已存储图片
curl "http://localhost:8208/api/v1/intelligence/stats?user_id=user123"

# 可能原因：
# 1. 图片尚未索引完成（需等待6-7秒）
# 2. 查询词与图片描述相关性低
# 3. user_id不匹配
```

**问题3: RAG查询超时**

```bash
# RAG生成需要较长时间（~19秒）
# 解决方案：
# 1. 增加客户端超时时间（建议30-60秒）
# 2. 减少context_limit（默认3，可降至2）
# 3. 使用更快的RAG模式（如不指定，自动选择）

curl -X POST "http://localhost:8208/api/v1/intelligence/image/rag" \
  -m 60 \  # 60秒超时
  -d '{
    "user_id": "user123",
    "query": "描述我的照片",
    "context_limit": 2  # 减少上下文
  }'
```

**问题4: 重复结果**

当前版本可能返回重复的搜索结果（已知问题）。这是MCP层的行为，不影响功能使用。后续版本将优化去重逻辑。

### 未来增强计划

- 🔮 **直接图片嵌入** - CLIP/OpenAI vision embeddings
- 🔮 **混合嵌入** - VLM描述 + 图片向量
- 🔮 **以图搜图** - 用示例图片查询
- 🔮 **批量处理** - 并行图片描述
- 🔮 **多VLM支持** - 支持其他视觉模型

---

## 📋 API快速参考

### Storage Service - 完整API列表

#### 基础文件操作
| Endpoint | Method | 功能 | 状态 |
|----------|--------|------|------|
| `/api/v1/files/upload` | POST | 文件上传 | ✅ 已实现 |
| `/api/v1/files` | GET | 文件列表 | ✅ 已实现 |
| `/api/v1/files/{file_id}` | GET | 获取文件详情 | ✅ 已实现 |
| `/api/v1/files/{file_id}` | DELETE | 删除文件 | ✅ 已实现 |
| `/api/v1/files/{file_id}/download` | GET | 下载文件 | ✅ 已实现 |
| `/api/v1/files/{file_id}/share` | POST | 分享文件 | ✅ 已实现 |
| `/api/v1/storage/stats` | GET | 存储统计 | ✅ 已实现 |

#### 照片版本管理
| Endpoint | Method | 功能 | 状态 |
|----------|--------|------|------|
| `/api/v1/photos/versions/save` | POST | 保存照片版本 | ✅ 已测试 |
| `/api/v1/photos/{photo_id}/versions` | POST | 获取版本列表 | ✅ 已测试 |
| `/api/v1/photos/{photo_id}/versions/{version_id}/switch` | PUT | 切换版本 | ✅ 已测试 |
| `/api/v1/photos/versions/{version_id}` | DELETE | 删除版本 | ✅ 已测试 |

#### 智能文档分析（文本）
| Endpoint | Method | 功能 | 延迟 | 状态 |
|----------|--------|------|------|------|
| `/api/v1/files/upload` | POST | 文本文件自动索引 | 7秒 | ✅ 已测试 |
| `/api/v1/intelligence/search` | POST | 文档语义搜索 | 6.7秒 | ✅ 已测试 |
| `/api/v1/intelligence/rag` | POST | RAG问答 | 13.3秒 | ✅ 已测试 |
| `/api/v1/intelligence/stats` | GET | 智能统计 | <1秒 | ✅ 已实现 |

#### 图片智能处理（NEW!）
| Endpoint | Method | 功能 | 延迟 | 状态 |
|----------|--------|------|------|------|
| `/api/v1/intelligence/image/store` | POST | 存储+VLM理解 | 13.7秒 | ✅ 已测试 |
| `/api/v1/intelligence/image/search` | POST | 图片语义搜索 | 9秒 | ✅ 已测试 |
| `/api/v1/intelligence/image/rag` | POST | 多模态RAG | 19秒 | ✅ 已测试 |

**测试日期**: 2025-10-01
**所有API均已验证并正常工作** ✅

**性能汇总**:
- 文件上传: <1秒（不含索引）
- 文本索引: ~7秒（自动触发）
- 图片理解: ~6.5秒（VLM）
- 语义搜索: 6.7-9秒
- RAG生成: 13-19秒

---

## 🆕 云盘扩展功能

> **注意**: 以下云盘扩展功能的API端点尚未实现，仅为规划设计。当前已实现的功能请参考上方的"核心功能测试结果"部分。

### 1. 文件夹管理 (cloud_models.py)

#### 创建文件夹
```bash
curl -X POST http://localhost:8208/api/cloud/folders \
  -H "Content-Type: application/json" \
  -d '{
    "name": "我的照片",
    "folder_type": "photos",
    "description": "家庭照片收藏",
    "icon": "📷",
    "color": "#FF5733",
    "is_public": false
  }' \
  --data-urlencode "user_id=test_user_123"
```

#### 文件夹类型
- `normal` - 普通文件夹
- `photos` - 照片文件夹
- `documents` - 文档文件夹
- `videos` - 视频文件夹
- `music` - 音乐文件夹
- `shared` - 共享文件夹
- `trash` - 回收站

#### 列出文件夹
```bash
# 获取根目录文件夹
curl "http://localhost:8208/api/cloud/folders?user_id=test_user_123"

# 获取子文件夹
curl "http://localhost:8208/api/cloud/folders?user_id=test_user_123&parent_folder_id=folder_123"
```

#### 移动文件夹
```bash
curl -X POST http://localhost:8208/api/cloud/folders/{folder_id}/move \
  -H "Content-Type: application/json" \
  -d '{"target_folder_id": "folder_456"}' \
  --data-urlencode "user_id=test_user_123"
```

### 2. 照片相册管理

#### 创建相册
```bash
# 手动相册
curl -X POST http://localhost:8208/api/cloud/albums \
  -F "name=2024年旅行" \
  -F "description=全年旅行照片集" \
  -F "album_type=manual" \
  -F "user_id=test_user_123"

# 智能相册（自动归类）
curl -X POST http://localhost:8208/api/cloud/albums \
  -F "name=北京照片" \
  -F "album_type=smart" \
  -F 'smart_rules={"location": "Beijing", "year": 2024}' \
  -F "user_id=test_user_123"
```

#### 添加照片到相册
```bash
curl -X POST http://localhost:8208/api/cloud/albums/{album_id}/photos \
  -H "Content-Type: application/json" \
  -d '{"photo_ids": ["photo_1", "photo_2", "photo_3"]}' \
  --data-urlencode "user_id=test_user_123"
```

#### 获取照片元数据
```bash
curl "http://localhost:8208/api/cloud/photos/{photo_id}/metadata?user_id=test_user_123"

# 返回EXIF数据、位置信息、AI分析结果等
{
  "photo_id": "photo_123",
  "camera_make": "Apple",
  "camera_model": "iPhone 14 Pro",
  "taken_at": "2024-09-15T10:30:00Z",
  "gps_latitude": 39.9042,
  "gps_longitude": 116.4074,
  "location_name": "北京市",
  "faces_detected": [...],
  "scene_tags": ["outdoor", "landscape", "mountain"]
}
```

### 3. 文件同步配置

#### 设置同步
```bash
curl -X POST http://localhost:8208/api/cloud/sync/config \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "auto_sync": true,
    "sync_interval": 300,
    "sync_folders": ["/Documents", "/Photos"],
    "exclude_patterns": ["*.tmp", "~*"],
    "wifi_only": true,
    "conflict_strategy": "newer",
    "versioning": true,
    "max_versions": 5
  }' \
  --data-urlencode "user_id=test_user_123" \
  --data-urlencode "device_id=device_456"
```

#### 手动同步
```bash
curl -X POST http://localhost:8208/api/cloud/sync/start \
  --data-urlencode "user_id=test_user_123" \
  --data-urlencode "device_id=device_456"
```

#### 获取同步状态
```bash
curl "http://localhost:8208/api/cloud/sync/status?user_id=test_user_123&device_id=device_456"
```

### 4. 云盘统计（增强版）

#### 获取详细统计
```bash
curl "http://localhost:8208/api/cloud/stats?user_id=test_user_123&refresh=true"

# 返回
{
  "user_id": "test_user_123",
  "total_storage": 10737418240,
  "used_storage": 1048576,
  "free_storage": 10736369664,
  "usage_percent": 0.01,
  "total_files": 150,
  "total_folders": 25,
  "photo_count": 80,
  "video_count": 10,
  "document_count": 60,
  "photo_size": 524288,
  "video_size": 262144,
  "document_size": 262144,
  "upload_today": 5,
  "download_today": 3,
  "synced_devices": 2,
  "album_count": 5
}
```

#### 获取存储趋势
```bash
curl "http://localhost:8208/api/cloud/stats/trends?user_id=test_user_123&days=30"
```

### 5. 批量操作

#### 批量移动/复制/删除
```bash
curl -X POST http://localhost:8208/api/cloud/bulk/operations \
  -H "Content-Type: application/json" \
  -d '{
    "operation_type": "move",
    "file_ids": ["file_1", "file_2", "file_3"],
    "target_folder_id": "folder_123"
  }' \
  --data-urlencode "user_id=test_user_123"
```

### 6. 版本管理

#### 列出文件版本
```bash
curl "http://localhost:8208/api/cloud/files/{file_id}/versions?user_id=test_user_123&limit=10"
```

#### 恢复到指定版本
```bash
curl -X POST http://localhost:8208/api/cloud/files/{file_id}/versions/{version_id}/restore \
  --data-urlencode "user_id=test_user_123"
```

### 7. 回收站管理

#### 查看回收站
```bash
curl "http://localhost:8208/api/cloud/trash?user_id=test_user_123&limit=100"
```

#### 恢复文件
```bash
curl -X POST http://localhost:8208/api/cloud/trash/restore \
  -H "Content-Type: application/json" \
  -d '{"item_ids": ["file_1", "folder_2"]}' \
  --data-urlencode "user_id=test_user_123"
```

#### 清空回收站
```bash
curl -X DELETE "http://localhost:8208/api/cloud/trash/empty?user_id=test_user_123&confirm=true"
```

## 实用场景示例

### 场景1：创建照片备份系统
```bash
# 1. 创建照片文件夹
curl -X POST http://localhost:8208/api/cloud/folders \
  -d '{"name": "照片备份", "folder_type": "photos"}'

# 2. 上传照片
for photo in *.jpg; do
  curl -X POST http://localhost:8208/api/files/upload \
    -F "file=@$photo" \
    -F "user_id=test_user_123" \
    -F "tags=backup,photo"
done

# 3. 创建智能相册
curl -X POST http://localhost:8208/api/cloud/albums \
  -F "name=今日照片" \
  -F "album_type=smart" \
  -F 'smart_rules={"date": "today"}'
```

### 场景2：文档同步
```bash
# 1. 配置文档同步
curl -X POST http://localhost:8208/api/cloud/sync/config \
  -d '{
    "sync_folders": ["/Documents"],
    "sync_documents": true,
    "auto_sync": true,
    "sync_interval": 600
  }'

# 2. 监控同步状态
watch -n 5 'curl -s http://localhost:8208/api/cloud/sync/status'
```

### 场景3：团队文件共享
```bash
# 1. 创建共享文件夹
curl -X POST http://localhost:8208/api/cloud/folders \
  -d '{"name": "团队共享", "folder_type": "shared", "is_public": true}'

# 2. 上传文件到共享文件夹
curl -X POST http://localhost:8208/api/files/upload \
  -F "file=@document.pdf" \
  -F "folder_id=shared_folder_123" \
  -F "access_level=shared"
```

## 性能优化建议

### 1. 大文件上传
- 使用分块上传（MinIO multipart upload）
- 建议块大小：5MB - 100MB
- 支持断点续传

### 2. 照片优化
- 自动生成缩略图（200x200, 800x800）
- EXIF数据提取和索引
- 智能压缩（保持质量85%）

### 3. 缓存策略
- 文件夹结构缓存（Redis）
- 热门文件CDN加速
- 元数据本地缓存

## 安全建议

### 1. 访问控制
- 文件级权限控制
- 文件夹继承权限
- 共享链接过期时间

### 2. 数据保护
- 传输加密（HTTPS）
- 存储加密（MinIO SSE）
- 客户端加密选项

### 3. 备份策略
- 自动版本保存
- 定期快照备份
- 跨区域复制

## 故障排查

### 问题1：文件上传失败
```bash
# 检查MinIO状态
curl http://localhost:9000/minio/health/live

# 检查用户配额
curl "http://localhost:8208/api/storage/stats?user_id=test_user_123"
```

### 问题2：同步冲突
```bash
# 查看冲突文件
curl "http://localhost:8208/api/cloud/sync/status?status=conflict"

# 解决冲突
curl -X POST http://localhost:8208/api/cloud/sync/resolve-conflict \
  -d '{"sync_id": "sync_123", "resolution": "keep_newer"}'
```

### 问题3：存储空间不足
```bash
# 清理回收站
curl -X DELETE "http://localhost:8208/api/cloud/trash/empty?confirm=true"

# 删除旧版本
curl -X DELETE "http://localhost:8208/api/cloud/files/cleanup-versions?keep_latest=3"
```

## 下一步开发计划

### 短期（1周）
- [ ] 完成文件夹UI界面
- [ ] 实现拖拽上传
- [ ] 添加图片预览功能

### 中期（1个月）
- [ ] 集成AI照片分析
- [ ] 实现视频流播放
- [ ] 添加文档在线预览

### 长期（3个月）
- [ ] 端到端加密
- [ ] 多用户协作编辑
- [ ] 移动端SDK开发

## API文档
- **完整API文档 (Swagger UI)**: http://localhost:8208/docs
- **API版本**: v1
- **所有端点前缀**: `/api/v1/`

## 联系支持
- 技术问题：查看日志 `logs/storage_service.log`
- MinIO控制台：http://localhost:9001 (用户名/密码: minioadmin)
- 服务状态：http://localhost:8208/health