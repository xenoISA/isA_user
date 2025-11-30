# Document Service

Knowledge base document management microservice with **RAG incremental updates** and **fine-grained authorization**.

**Port**: 8227

## 🎯 Core Features

### 1️⃣ RAG 增量更新 (RAG Incremental Updates)

支持三种更新策略：

- **FULL**: 删除旧索引，全量重建
- **SMART**: 智能增量更新（基于相似度的 chunk 比对）
- **DIFF**: 基于 diff 的精准更新

```python
# Smart incremental update - only updates changed chunks
PUT /api/v1/documents/{doc_id}/update
{
    "new_file_id": "file_xyz",
    "update_strategy": "smart",
    "title": "Updated Title"
}
```

**工作原理**:
1. 获取旧文档的所有 chunks（从 Qdrant）
2. 对新内容进行 chunking
3. 计算 chunks 相似度矩阵
4. 根据相似度决定操作：
   - `similarity > 0.95`: 保留旧 point
   - `0.7 < similarity < 0.95`: 更新现有 point
   - `similarity < 0.7`: 创建新 point
5. 删除不再存在的 chunks

### 2️⃣ 细粒度权限管理 (Fine-Grained Authorization)

#### 文档级权限
- **PRIVATE**: 仅创建者
- **TEAM**: 团队成员
- **ORGANIZATION**: 组织内成员
- **PUBLIC**: 公开访问

#### Chunk 级权限
每个 Qdrant point 携带权限 metadata：

```python
{
    "doc_id": "doc_123",
    "user_id": "user_456",
    "organization_id": "org_789",
    "access_level": "organization",
    "allowed_users": ["user_1", "user_2"],
    "allowed_groups": ["group_1"],
    "denied_users": ["user_3"]
}
```

#### RAG 查询时自动权限过滤

```python
POST /api/v1/rag/query
{
    "query": "什么是 RAG？",
    "top_k": 5
}
```

**自动构建 Qdrant filter**:
```python
{
    "should": [
        {"key": "user_id", "match": {"value": current_user}},
        {"key": "access_level", "match": {"value": "public"}},
        {"key": "allowed_users", "match": {"any": [current_user]}},
        {"key": "allowed_groups", "match": {"any": user_groups}}
    ],
    "must_not": [
        {"key": "denied_users", "match": {"any": [current_user]}}
    ]
}
```

### 3️⃣ 文档版本管理

- 每次更新创建新版本
- 保留历史版本
- 支持版本回滚
- 版本权限继承

### 4️⃣ 权限变更时自动更新 Qdrant

```python
PUT /api/v1/documents/{doc_id}/permissions
{
    "access_level": "team",
    "add_users": ["user_1", "user_2"],
    "remove_users": ["user_3"]
}
```

**自动执行**:
1. 更新数据库中的文档权限
2. 批量更新 Qdrant 中所有相关 points 的 metadata
3. 记录权限变更历史

## 📁 Project Structure

```
microservices/document_service/
├── __init__.py                          # Service config (port 8227)
├── models.py                            # Data models (450+ lines)
├── document_repository.py               # Data access layer (700+ lines)
├── document_service.py                  # Business logic (1000+ lines)
├── main.py                              # FastAPI routes (400+ lines)
├── routes_registry.py                   # Consul route metadata
│
├── clients/                             # Service clients
│   ├── __init__.py
│   ├── storage_client.py                # Storage Service client
│   ├── authorization_client.py          # Authorization Service client
│   └── digital_analytics_client.py      # Digital Analytics (isA_Data) client
│
├── events/                              # Event-driven
│   ├── __init__.py
│   ├── handlers.py                      # Event handlers (file.deleted, user.deleted)
│   └── publishers.py                    # Event publishers
│
└── migrations/
    └── 001_create_documents_table.sql   # Database schema
```

## 🔌 API Endpoints

### Document CRUD
- `POST /api/v1/documents` - Create document and index
- `GET /api/v1/documents/{doc_id}` - Get document (with permission check)
- `GET /api/v1/documents` - List user documents
- `DELETE /api/v1/documents/{doc_id}` - Delete document (soft/hard)

### RAG Incremental Update
- `PUT /api/v1/documents/{doc_id}/update` - Incremental RAG update

### Permission Management
- `PUT /api/v1/documents/{doc_id}/permissions` - Update permissions (+ Qdrant)
- `GET /api/v1/documents/{doc_id}/permissions` - Get permissions

### RAG Query (Permission-Filtered)
- `POST /api/v1/rag/query` - RAG query with auto permission filtering
- `POST /api/v1/search` - Semantic search with permission filtering

### Statistics
- `GET /api/v1/stats` - User document statistics

### Health
- `GET /` - Service status
- `GET /health` - Health check

## 🗄️ Database Schema

### knowledge_documents

| Column | Type | Description |
|--------|------|-------------|
| doc_id | VARCHAR(64) | Primary key |
| user_id | VARCHAR(64) | Document owner |
| organization_id | VARCHAR(64) | Organization ID |
| title | VARCHAR(500) | Document title |
| doc_type | VARCHAR(32) | pdf, docx, txt, etc. |
| file_id | VARCHAR(64) | Storage Service file ID |
| version | INTEGER | Version number |
| parent_version_id | VARCHAR(64) | Parent version (for history) |
| is_latest | BOOLEAN | Is this the latest version? |
| status | VARCHAR(32) | draft, indexing, indexed, updating, failed |
| chunk_count | INTEGER | Number of chunks in Qdrant |
| access_level | VARCHAR(32) | private, team, organization, public |
| allowed_users | TEXT[] | User IDs with access |
| allowed_groups | TEXT[] | Group IDs with access |
| denied_users | TEXT[] | Explicitly denied users |
| point_ids | TEXT[] | Qdrant point IDs |
| metadata | JSONB | Additional metadata |
| tags | TEXT[] | Document tags |

### document_permission_history

Audit trail for permission changes.

## 🚀 Deployment

### Environment Variables

```bash
DOCUMENT_SERVICE_PORT=8227

# Service Discovery (Consul)
CONSUL_HOST=host.docker.internal
CONSUL_PORT=8500

# Database (PostgreSQL via gRPC)
POSTGRES_GRPC_HOST=isa-postgres-grpc
POSTGRES_GRPC_PORT=50061

# NATS Event Bus
NATS_URL=nats://host.docker.internal:4222
```

### Run Service

```bash
cd microservices/document_service
python main.py
```

### Run Database Migration

```bash
psql -U postgres -d postgres -f migrations/001_create_documents_table.sql
```

## 🔗 Service Dependencies

| Service | Purpose | Communication |
|---------|---------|---------------|
| **Storage Service** (8209) | File storage/download | HTTP/gRPC |
| **Authorization Service** (8204) | User permissions | HTTP/gRPC |
| **Digital Analytics Service** (isA_Data:8081) | RAG indexing, Qdrant | HTTP |
| **PostgreSQL** (via gRPC) | Database | gRPC |
| **NATS** | Event bus | NATS |
| **Consul** | Service discovery | HTTP |

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Document Service (8227)                      │
│  职责:                                                          │
│  1. 知识库文档管理                                               │
│  2. RAG 增量更新 (FULL/SMART/DIFF)                              │
│  3. 文档/Chunk 级别权限管理                                      │
│  4. 与 Authorization Service 集成                               │
│  5. Qdrant 权限 metadata 管理                                   │
└─────────────────────────────────────────────────────────────────┘
         ↓ 调用                    ↓ 调用                ↓ 调用
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ Storage Service  │    │ Authorization    │    │ Digital Analytics│
│ (8209)           │    │ Service (8204)   │    │ (isA_Data:8081)  │
│ - 文件上传/下载  │    │ - RBAC/ABAC      │    │ - RAG indexing   │
│ - MinIO 管理     │    │ - 用户/组织权限  │    │ - Qdrant 向量库  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

## 🧪 Testing

### Create Document

```bash
curl -X POST "http://localhost:8227/api/v1/documents?user_id=test_user" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "RAG Knowledge Base",
    "description": "Document about RAG",
    "doc_type": "pdf",
    "file_id": "file_123",
    "access_level": "private",
    "tags": ["rag", "ai"]
  }'
```

### RAG Incremental Update

```bash
curl -X PUT "http://localhost:8227/api/v1/documents/doc_123/update?user_id=test_user" \
  -H "Content-Type: application/json" \
  -d '{
    "new_file_id": "file_456",
    "update_strategy": "smart"
  }'
```

### Update Permissions

```bash
curl -X PUT "http://localhost:8227/api/v1/documents/doc_123/permissions?user_id=test_user" \
  -H "Content-Type: application/json" \
  -d '{
    "access_level": "team",
    "add_users": ["user_1", "user_2"]
  }'
```

### RAG Query

```bash
curl -X POST "http://localhost:8227/api/v1/rag/query?user_id=test_user" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是 RAG 增量更新？",
    "top_k": 5
  }'
```

## 📝 Development Notes

### TODO List

- [ ] 实现实际的 Storage Service HTTP 调用（当前为 mock）
- [ ] 实现实际的 Authorization Service 集成
- [ ] 实现实际的 Digital Analytics Service HTTP/gRPC 调用
- [ ] 添加文档协作编辑功能（如需要）
- [ ] 添加文档模板功能（如需要）
- [ ] 添加更多 chunking 策略（当前仅 semantic）
- [ ] 优化 diff-based update 算法
- [ ] 添加文档全文搜索（非向量搜索）
- [ ] 添加文档导出功能

### Known Limitations

1. **Clients 为 Mock 实现**: 当前 `storage_client.py`, `authorization_client.py`, `digital_analytics_client.py` 返回 mock 数据，需要实现实际的 HTTP/gRPC 调用
2. **文本相似度算法简化**: `_calculate_text_similarity()` 使用简单的 Jaccard 相似度，生产环境应使用 embedding cosine similarity
3. **Diff-based update**: 当前回退到 smart update，需要实现实际的 diff 算法

## 🔐 Security Considerations

1. **权限验证**: 所有 API 都进行权限检查
2. **SQL 注入防护**: 使用参数化查询
3. **XSS 防护**: 文本内容需要 sanitize
4. **Rate Limiting**: 建议添加 API rate limiting
5. **审计日志**: 权限变更已记录到 `document_permission_history`

## 📚 References

- [RAG 增量更新设计文档](../docs/rag_incremental_update.md)
- [权限管理设计文档](../docs/document_authorization.md)
- [API 文档](http://localhost:8227/docs) (FastAPI auto-generated)

---

**Version**: 1.0.0
**Last Updated**: 2025-11-23
**Author**: Claude Code
