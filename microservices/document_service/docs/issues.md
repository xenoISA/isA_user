# Document Service - 当前问题总结

**日期**: 2025-11-23
**状态**: 部分完成 - 需要进一步修复

---

## 完成的工作 ✅

### 1. 真实Client集成
已将所有mock clients替换为真实的微服务调用：

- ✅ **StorageServiceClient** - 直接import `microservices.storage_service.client.StorageServiceClient`
  - 提供: `get_file_info()`, `download_file()`, `delete_file()` 等方法
  - 使用service discovery连接到 storage_service (8209端口)

- ✅ **AuthorizationServiceClient** - 直接import `microservices.authorization_service.client.AuthorizationServiceClient`
  - 提供: `check_access()`, `get_user_groups()` 等方法
  - 使用service discovery连接到 authorization_service (8204端口)

- ✅ **DigitalAnalyticsClient** - 从media_service复制并修改配置
  - 提供: `store_content()`, `search_content()`, `generate_response()` 等方法
  - 连接到 Digital Analytics Service (isA_Data) at `http://data.isa-cloud-staging.svc.cluster.local:8084/api/v1/digital`
  - 配置来源: `deployment/k8s/user-configmap.yaml` 中的 `DIGITAL_ANALYTICS_URL` 和 `DIGITAL_ANALYTICS_ENABLED`

### 2. 数据库表创建
- ✅ 运行了 `migrations/001_create_documents_table.sql`
- ✅ 创建了 `document.knowledge_documents` 和 `document.document_permission_history` 表
- ✅ 移除了外键约束 (微服务架构不应使用外键)

### 3. 服务部署
- ✅ 更新了 `deployment/k8s/build-all-images.sh` 添加 `document_service:8227`
- ✅ 更新了 `deployment/k8s/generate-manifests.sh` (已有 `document_service:8227`)
- ✅ 生成了 Kubernetes manifests
- ✅ 成功部署到 Kind 集群
- ✅ 服务启动正常，健康检查通过
- ✅ 注册到 Consul

---

## 当前问题 ❌

### 问题1: 文档索引失败 - 文件不存在

**症状:**
- 创建文档成功（写入PostgreSQL）
- 文档状态变为 `"status": "failed"`
- 但没有错误日志输出

**根本原因:**
在 `document_service.py:918` 中，`_index_document_async()` 方法会调用：
```python
file_content = await self._download_file_content(document.file_id, user_id)
```

测试使用的 `file_id` 是mock的（例如 `test_file_1763892062_29673`），这个文件在 storage_service 中**不存在**，导致下载失败。

**调用链:**
```
create_document()
  → _index_document_async()
    → _download_file_content()
      → storage_client.download_file(file_id, user_id)  # 失败：文件不存在
        → storage_service API: GET /api/v1/storage/files/{file_id}/download
```

**错误处理:**
```python
# document_service.py:950-954
except Exception as e:
    logger.error(f"Document indexing failed: {e}")
    await self.repository.update_document_status(
        document.doc_id, DocumentStatus.FAILED
    )
```

文档状态被设置为 FAILED，但错误日志可能没有正确输出。

### 问题2: document_service设计与isA_Data API不匹配

**document_service当前尝试做的事情 (不正确):**
```python
# 当前代码中调用的方法（这些方法在DigitalAnalyticsClient中不存在）
await digital_client.delete_points()              # ❌ 不存在
await digital_client.get_document_chunks()        # ❌ 不存在
await digital_client.chunk_document()             # ❌ 不存在
await digital_client.update_point()               # ❌ 不存在
await digital_client.store_chunk()                # ❌ 不存在
await digital_client.batch_update_points_metadata()  # ❌ 不存在
await digital_client.rag_query_with_filter()      # ❌ 不存在
await digital_client.search_with_filter()         # ❌ 不存在
```

**isA_Data实际提供的API (根据 `/Users/xenodennis/Documents/Fun/isA_Data/docs/how_to_digital.md`):**
```
POST /api/v1/digital/store      - 存储内容（自动chunking和向量化）
POST /api/v1/digital/search     - 搜索内容
POST /api/v1/digital/response   - 生成RAG回答
```

**DigitalAnalyticsClient实际有的方法 (从media_service复制):**
```python
✅ store_content()        - 映射到 /store
✅ search_content()       - 映射到 /search
✅ generate_response()    - 映射到 /response
✅ process_pdf()          - 便捷方法，调用store_content
✅ process_image()        - 便捷方法，调用store_content
```

**关键理解:**
- ❌ document_service **不应该**管理chunks (这是digital_analytics的职责)
- ❌ document_service **不应该**直接操作Qdrant (通过digital_analytics间接操作)
- ✅ document_service **应该**只管理文档元数据和权限（PostgreSQL）
- ✅ document_service **应该**通过高层API调用digital_analytics

**正确的设计应该是:**

| 操作 | document_service应该做的 |
|------|-------------------------|
| 创建/更新文档 | 调用 `store_content()` 传入完整的metadata（包括权限信息） |
| 权限更新 | 重新调用 `store_content()` 用新的权限metadata（isA_Data会覆盖） |
| 删除文档 | 不需要显式删除chunks（或通过collection_name管理） |
| RAG查询 | 调用 `generate_response()` |
| 语义搜索 | 调用 `search_content()` |

---

## 需要修复的内容

### 修复1: 解决测试文件不存在的问题

**方案A: 修改测试，上传真实文件**
```bash
# 在测试前：
# 1. 上传一个文件到storage_service
# 2. 获取file_id
# 3. 使用这个file_id创建document
```

**方案B: 让document_service处理文件下载失败的情况**
```python
# 在_download_file_content中添加fallback
async def _download_file_content(self, file_id: str, user_id: str) -> str:
    if not self.storage_client:
        return self._get_mock_content(file_id)  # 用于测试

    try:
        content = await self.storage_client.download_file(file_id, user_id)
        return content
    except Exception as e:
        logger.warning(f"Failed to download file {file_id}: {e}, using mock content")
        return self._get_mock_content(file_id)  # Fallback
```

**方案C: 查询storage_service是否有现有文件**
```bash
# 查询storage_service中的文件列表
curl http://localhost:8209/api/v1/storage/files?user_id=<some_user>
# 使用现有文件的file_id进行测试
```

**推荐**: 先执行方案C，查看是否有可用文件，然后决定采用方案A或B

### 修复2: 简化document_service逻辑

需要重构以下方法，移除低层次的Qdrant操作：

**文件位置**: `document_service.py`

**需要重构的方法:**

1. **`_smart_incremental_update()` (line ~463-526)**
   - 当前: 尝试获取old chunks，比较相似度，更新/删除points
   - 应该: 直接重新调用 `store_content()`，让digital_analytics处理增量更新

2. **`_diff_incremental_update()` (line ~530-590)**
   - 当前: 尝试text diff，然后store individual chunks
   - 应该: 简化为直接重新 `store_content()`

3. **`update_document_permissions()` (line ~673)**
   - 当前: 尝试调用 `batch_update_points_metadata()`
   - 应该: 重新调用 `store_content()` 用新的permissions metadata

4. **`delete_document()` (清理digital_analytics数据)**
   - 当前: 可能尝试删除points
   - 应该: 通过collection管理，或者不需要显式删除（依赖TTL/GC）

**重构原则:**
- 文档内容/权限有任何更新 → 重新调用 `store_content()`
- digital_analytics会自动处理：chunking、embedding、存储到Qdrant
- 使用 `collection_name` 来组织数据（例如 `user_{user_id}`）

---

## 测试状态

### 测试套件: `tests/run_all_tests.sh`

**结果**: 2/5 通过

| 测试 | 状态 | 说明 |
|------|------|------|
| Document CRUD | ❌ 部分失败 | 创建成功但索引失败（文件不存在） |
| Permission Management | ❌ 部分失败 | 同上 |
| RAG Query & Semantic Search | ✅ 通过 | 使用mock响应 |
| Event Publishing | ❌ 失败 | 依赖文档创建成功 |
| Event Subscriptions | ✅ 通过 | 仅验证健康检查 |

**核心问题**: 所有失败都源于"文件不存在"导致的索引失败

---

## 架构确认

### 微服务职责划分

**document_service职责** ✅:
- 文档元数据管理（title, description, tags等）
- 文档权限管理（access_level, allowed_users, allowed_groups）
- 文档版本管理（parent_version_id, is_latest）
- 调用其他服务完成实际工作

**digital_analytics_service (isA_Data)职责** ✅:
- 文档内容的chunking
- Embedding生成
- Qdrant向量存储
- RAG查询和语义搜索
- Chunk级别的metadata管理

**storage_service职责** ✅:
- 文件的实际存储（MinIO）
- 文件的上传/下载
- 文件元数据

**关键原则**:
- ❌ **没有外键约束** (微服务架构)
- ✅ **通过events和clients通信**
- ✅ **每个服务管理自己的数据**

---

## 配置验证

### Environment Variables (from `deployment/k8s/user-configmap.yaml`)

```yaml
# Digital Analytics Service
DIGITAL_ANALYTICS_URL: "http://data.isa-cloud-staging.svc.cluster.local:8084/api/v1/digital"
DIGITAL_ANALYTICS_ENABLED: "true"

# Document Service
DOCUMENT_SERVICE_PORT: 8227
```

### Service Discovery

```python
# StorageServiceClient - 使用ConfigManager和service discovery
base_url = sd.get_service_url("storage_service")
# → http://storage.isa-cloud-staging.svc.cluster.local:8209

# AuthorizationServiceClient - 使用service discovery
base_url = sd.get_service_url("authorization_service")
# → http://authorization.isa-cloud-staging.svc.cluster.local:8204

# DigitalAnalyticsClient - 使用ConfigManager读取配置
base_url = config.get("DIGITAL_ANALYTICS_URL")
# → http://data.isa-cloud-staging.svc.cluster.local:8084/api/v1/digital
```

---

## 下一步行动

### 优先级1: 修复文件下载问题
1. 查询storage_service是否有现有文件（方案C）
2. 如果有，更新测试使用真实file_id
3. 如果没有，先上传测试文件或实现fallback mock

### 优先级2: 简化document_service逻辑
1. 移除所有尝试管理chunks的代码
2. 只保留高层API调用: `store_content()`, `search_content()`, `generate_response()`
3. 权限更新 = 重新store_content with new metadata

### 优先级3: 完整测试
1. 使用真实文件测试完整流程
2. 验证RAG查询能正常工作
3. 验证权限过滤是否生效

---

## 相关文件

### 代码文件
- `microservices/document_service/document_service.py` - 主要业务逻辑
- `microservices/document_service/clients/` - 三个client
- `microservices/document_service/migrations/001_create_documents_table.sql` - 数据库schema

### 配置文件
- `deployment/k8s/user-configmap.yaml` - 环境变量配置
- `deployment/k8s/generate-manifests.sh` - K8s manifest生成
- `deployment/k8s/build-all-images.sh` - Docker镜像构建

### 测试文件
- `microservices/document_service/tests/run_all_tests.sh` - 测试入口
- `microservices/document_service/tests/1_document_crud.sh`
- `microservices/document_service/tests/2_permissions.sh`
- `microservices/document_service/tests/3_rag_query.sh`
- `microservices/document_service/tests/integration/test_event_publishing.sh`
- `microservices/document_service/tests/integration/test_event_subscriptions.sh`

### 文档
- `/Users/xenodennis/Documents/Fun/isA_Data/docs/how_to_digital.md` - Digital Analytics API文档
- `microservices/document_service/README.md` - 服务说明

---

## 结论

document_service的**基础架构已经完成**，所有clients都已替换为真实调用。主要问题是：

1. **测试依赖真实文件** - 需要先上传文件或实现fallback
2. **过度设计** - 尝试管理chunks，应该简化为只调用高层API

这些都是**可修复的设计问题**，不影响核心架构的正确性。
