 📸 三大服务架构解析

  🎯 服务定位

  | 服务              | 核心职责        | 端口   | 数据库 Schema |
  |-----------------|-------------|------|------------|
  | Storage Service | 文件存储与管理（底层） | 8209 | storage    |
  | Album Service   | 相册组织与管理（中层） | 8223 | album      |
  | Media Service   | 智能展示与处理（上层） | 8222 | media      |

  ---
  📤 流程1：用户上传一张照片

  用户 → Storage Service → MinIO → Album Service → Media Service

  详细步骤：

  步骤1：Storage Service 处理上传

  📁 storage_service/storage_service.py:175-334

  操作：
  1. ✅ 验证文件类型、大小、配额
  2. 📦 生成 file_id (例: file_a1b2c3d4)
  3. ☁️ 上传到 MinIO 对象存储（使用 isa_common.MinIOClient）
  4. 💾 保存文件记录到数据库 storage.storage_files 表
    - file_id, user_id, file_path, bucket_name, object_name
    - content_type, file_size, checksum, download_url
  5. 📊 更新用户存储配额使用量
  6. 📢 发布事件: FILE_UPLOADED (NATS)

  事件数据：
  {
    "event_type": "FILE_UPLOADED",
    "file_id": "file_a1b2c3d4",
    "file_name": "vacation.jpg",
    "file_size": 2048576,
    "content_type": "image/jpeg",
    "user_id": "user_123",
    "organization_id": "org_456"
  }

  ---
  步骤2：智能索引（自动触发）

  如果文件是文本/PDF，Storage Service 会自动调用智能索引：

  📁 storage_service/intelligence_service.py:52-124

  操作：
  - 通过 MCP (Model Context Protocol) 调用 isA_MCP 服务
  - 使用 store_knowledge 工具进行语义索引
  - 保存索引记录到 storage.storage_intelligence_index 表
  - 支持后续的 语义搜索 和 RAG问答

  ---
  步骤3：Media Service 监听事件（可选）

  📁 media_service/events.py:156-207

  操作：
  - 监听 FILE_UPLOADED 事件
  - 如果是图片文件 (image/*)，创建初始 PhotoMetadata 记录
  - 等待后续 AI 分析（标签、场景、人脸检测）

  ---
  步骤4：用户添加照片到相册（手动）

  用户调用 Album Service API：
  POST /api/v1/albums/{album_id}/photos
  {
    "photo_ids": ["file_a1b2c3d4", "file_xyz789"]
  }

  📁 album_service/album_service.py:379-447

  操作：
  1. ✅ 验证相册存在且用户有权限
  2. 🔗 在 album.album_photos 表中创建关联记录
  3. 📊 更新相册的 photo_count
  4. 📢 发布事件: ALBUM_PHOTO_ADDED

  ---
  🔍 流程2：用户搜索一张照片

  场景1：基于文件名/标签搜索（Storage Service）

  GET /api/v1/files?search_term=vacation&tags=summer

  📁 storage_service/storage_repository.py

  操作：
  - 在 storage.storage_files 表中进行 SQL 查询
  - 支持文件名模糊匹配、标签过滤、日期范围
  - 返回文件列表（含预签名下载URL）

  ---
  场景2：语义搜索（Storage Service - Intelligence）

  POST /api/v1/intelligence/search
  {
    "query": "beach sunset photos from last summer",
    "top_k": 10
  }

  📁 storage_service/intelligence_service.py:181-235

  操作：
  1. 🔍 通过 MCP 调用 isA_MCP 的 semantic_search 工具
  2. 🧠 使用向量相似度查找最相关的文档
  3. 📋 返回搜索结果（文档ID、相似度分数、摘要）

  适用场景：
  - 文档内容搜索（不仅仅是文件名）
  - 自然语言查询（"去年夏天拍的海滩照片"）

  ---
  场景3：基于AI标签搜索（Media Service）

  如果 Media Service 已经完成了 AI 分析：

  GET /api/v1/metadata?ai_labels=beach,sunset&quality_min=0.8

  📁 media_service/media_repository.py

  操作：
  - 在 media.photo_metadata 表中查询
  - 支持 AI 标签、场景、颜色、人脸检测过滤
  - 返回带有 AI 分析结果的照片元数据

  ---
  场景4：相册内搜索（Album Service）

  GET /api/v1/albums/{album_id}/photos?limit=50&offset=0

  📁 album_service/album_service.py:515-556

  操作：
  - 在 album.album_photos 表中查询
  - 返回相册内的照片列表（按添加时间排序）

  ---
  🔄 服务协作关系图

  ┌─────────────────────────────────────────────────────────────┐
  │                      用户上传照片流程                         │
  └─────────────────────────────────────────────────────────────┘

  用户
   │
   ├─► Storage Service (8209)
   │    ├─► MinIO 对象存储 (文件实际存储)
   │    ├─► PostgreSQL `storage` schema (文件元数据)
   │    └─► 📢 EVENT: FILE_UPLOADED
   │
   ├─► Intelligence Service (自动触发)
   │    ├─► MCP → isA_MCP (语义索引)
   │    └─► PostgreSQL `storage_intelligence_index`
   │
   ├─► Media Service (8222) - 监听事件
   │    └─► PostgreSQL `media` schema
   │         ├─► photo_metadata (AI分析结果)
   │         ├─► photo_versions (增强版本)
   │         ├─► playlists (播放列表)
   │         └─► rotation_schedules (轮播计划)
   │
   └─► Album Service (8223) - 用户手动添加
        └─► PostgreSQL `album` schema
             ├─► albums (相册)
             └─► album_photos (相册-照片关联)

  ┌─────────────────────────────────────────────────────────────┐
  │                      用户搜索照片流程                         │
  └─────────────────────────────────────────────────────────────┘

  用户搜索请求
   │
   ├─► 按文件名/标签 → Storage Service
   │    └─► SQL查询 `storage.storage_files`
   │
   ├─► 语义搜索 → Intelligence Service
   │    └─► MCP → isA_MCP → 向量相似度搜索
   │
   ├─► AI标签搜索 → Media Service
   │    └─► SQL查询 `media.photo_metadata`
   │
   └─► 相册内搜索 → Album Service
        └─► SQL查询 `album.album_photos`

  ---
  🎭 服务职责明确边界

  | 功能         | Storage | Album | Media | 说明                         |
  |------------|---------|-------|-------|----------------------------|
  | 文件上传/下载    | ✅       | ❌     | ❌     | Storage 独占                 |
  | MinIO 对象存储 | ✅       | ❌     | ❌     | Storage 独占                 |
  | 存储配额管理     | ✅       | ❌     | ❌     | Storage 独占                 |
  | 文件分享       | ✅       | ❌     | ❌     | Storage 独占                 |
  | 语义搜索 + RAG | ✅       | ❌     | ❌     | Storage 独占（通过Intelligence） |
  | 相册管理       | ❌       | ✅     | ❌     | Album 独占                   |
  | 家庭共享相册     | ❌       | ✅     | ❌     | Album 独占                   |
  | 相册同步到设备    | ❌       | ✅     | ❌     | Album 独占                   |
  | AI元数据分析    | ❌       | ❌     | ✅     | Media 独占                   |
  | 照片版本管理     | ❌       | ❌     | ✅     | Media 独占                   |
  | 播放列表       | ❌       | ❌     | ✅     | Media 独占                   |
  | 轮播计划       | ❌       | ❌     | ✅     | Media 独占                   |
  | 设备端缓存      | ❌       | ❌     | ✅     | Media 独占                   |

  ---
  🚨 重要注意事项

  1. 功能重叠问题（已发现）

  Storage Service 早期代码中也实现了部分照片版本、播放列表功能，但这些应该迁移到 Media Service。

  建议整改：
  - 移除 storage.photo_versions 表（已在 Media Service 中实现）
  - 保留 Storage Service 的基础存储功能

  2. 事件驱动架构

  三个服务通过 NATS 事件总线解耦：
  - FILE_UPLOADED → Media Service 创建元数据
  - FILE_DELETED → Media Service 清理相关数据
  - ALBUM_PHOTO_ADDED → 可触发相册同步到设备

  3. 跨服务验证

  - Album Service 添加照片时，应验证 photo_id 在 Storage Service 中存在
  - Media Service 创建版本时，应验证 file_id 在 Storage Service 中存在

  ---
  🎯 总结

  | 阶段  | 负责服务            | 核心操作                                                   |
  |-----|-----------------|--------------------------------------------------------|
  | 上传  | Storage Service | MinIO存储 + 文件元数据 + 智能索引                                 |
  | 组织  | Album Service   | 相册管理 + 家庭共享                                            |
  | 展示  | Media Service   | AI分析 + 播放列表 + 轮播计划                                     |
  | 搜索  | 三者协作            | 文件名（Storage）+ 语义（Intelligence）+ AI标签（Media）+ 相册（Album） |

  简单记忆：
  - Storage = 存哪儿？（MinIO）
  - Album = 怎么组织？（相册、共享）
  - Media = 怎么展示？（播放列表、轮播、AI增强）