# Migration Files Mapping (旧迁移文件到新微服务的映射)

## 概述

原 `storage_service/migrations_old/` 目录下的文件已被重构并拆分到三个微服务中：
- **storage_service** - 文件存储、分享、配额、智能索引
- **album_service** - 相册管理、相册同步
- **media_service** - 照片处理、版本管理、播放列表、缓存

## 详细映射

### 旧文件 → 新文件映射表

| 旧文件 (migrations_old/) | 新文件 | 新服务 | 表名变化 | 备注 |
|---------------------|--------|--------|---------|------|
| 001_create_storage_files_table.sql | migrations/001_create_storage_files_table.sql | storage_service | storage_files (无变化) | ✅ 已优化 |
| 002_create_file_shares_table.sql | migrations/002_create_file_shares_table.sql | storage_service | file_shares (无变化) | ✅ 已优化 |
| 003_create_storage_quotas_table.sql | migrations/003_create_storage_quotas_table.sql | storage_service | storage_quotas (无变化) | ✅ 重新设计 (quota_type + entity_id) |
| 004_add_intelligence_index.sql | migrations/004_add_intelligence_index.sql | storage_service | storage_intelligence_index (无变化) | ✅ RAG/AI功能保留在storage |
| 005_create_album_tables.sql | ../album_service/migrations/001_create_album_tables.sql | album_service | albums, album_photos, album_sync_status | ✅ 拆分到新服务 |
| 006_create_photo_versions_table.sql | ../media_service/migrations/001_create_media_tables.sql | media_service | photo_versions → media.photo_versions | ✅ 添加 organization_id |
| 007_create_gallery_tables.sql | ../media_service/migrations/001_create_media_tables.sql | media_service | 见下方详细表名映射 | ✅ 表名简化 + 字段补全 |

### 007_create_gallery_tables.sql 的表映射

| 旧表名 (public schema) | 新表名 (media schema) | 主要变化 |
|----------------------|---------------------|---------|
| slideshow_playlists | media.playlists | ✅ 添加 organization_id |
| photo_rotation_schedules | media.rotation_schedules | ✅ 添加 user_id |
| photo_metadata | media.photo_metadata | ✅ 添加 user_id, organization_id |
| photo_cache | media.photo_cache | ✅ 添加 user_id |

## 新增初始化文件

为了记录所有数据库操作，新增了 `000_init_schema.sql` 文件：

```
storage_service/migrations/000_init_schema.sql  - 创建 storage schema 和辅助函数
album_service/migrations/000_init_schema.sql    - 创建 album schema 和辅助函数
media_service/migrations/000_init_schema.sql    - 创建 media schema 和辅助函数
```

## 主要改进

### 1. Schema 隔离
- ✅ 每个微服务使用独立的 schema (storage, album, media)
- ❌ 旧文件：使用 public schema 或无 schema 前缀

### 2. 移除 Foreign Keys
- ✅ 所有 FK 约束已移除
- ✅ 添加应用层验证注释
- ❌ 旧文件：部分表有 FK 约束

### 3. 多租户支持
- ✅ 所有表都有 user_id
- ✅ 需要的表添加了 organization_id
- ❌ 旧文件：部分表缺少 user_id/organization_id

### 4. 字段优化
- ✅ storage_quotas: 从 user_id/organization_id (nullable) 改为 quota_type + entity_id
- ✅ 统一 timestamp 类型为 TIMESTAMPTZ
- ✅ 添加详细的 COMMENT

### 5. 索引优化
- ✅ 为 user_id, organization_id 添加索引
- ✅ 为 JSONB 字段添加 GIN 索引
- ✅ 为常用查询添加复合索引

## 执行顺序

### Storage Service
```bash
cd /Users/xenodennis/Documents/Fun/isA_user
docker exec -i staging-postgres psql -U postgres -d isa_platform < microservices/storage_service/migrations/000_init_schema.sql
docker exec -i staging-postgres psql -U postgres -d isa_platform < microservices/storage_service/migrations/001_create_storage_files_table.sql
docker exec -i staging-postgres psql -U postgres -d isa_platform < microservices/storage_service/migrations/002_create_file_shares_table.sql
docker exec -i staging-postgres psql -U postgres -d isa_platform < microservices/storage_service/migrations/003_create_storage_quotas_table.sql
docker exec -i staging-postgres psql -U postgres -d isa_platform < microservices/storage_service/migrations/004_add_intelligence_index.sql
```

### Album Service
```bash
docker exec -i staging-postgres psql -U postgres -d isa_platform < microservices/album_service/migrations/000_init_schema.sql
docker exec -i staging-postgres psql -U postgres -d isa_platform < microservices/album_service/migrations/001_create_album_tables.sql
```

### Media Service
```bash
docker exec -i staging-postgres psql -U postgres -d isa_platform < microservices/media_service/migrations/000_init_schema.sql
docker exec -i staging-postgres psql -U postgres -d isa_platform < microservices/media_service/migrations/001_create_media_tables.sql
```

## 验证

查看创建的表：

```bash
# Storage Service 表 (4个)
docker exec staging-postgres psql -U postgres -d isa_platform -c "\dt storage.*"

# Album Service 表 (3个)
docker exec staging-postgres psql -U postgres -d isa_platform -c "\dt album.*"

# Media Service 表 (5个)
docker exec staging-postgres psql -U postgres -d isa_platform -c "\dt media.*"
```

## 迁移状态

✅ 所有 migration 文件已创建
✅ 所有表已在数据库中创建
✅ Schema 和 Role 已初始化
⏳ 待办：更新 Python 代码使用 PostgresClient
⏳ 待办：创建 album_service 和 media_service 的 Python 代码

---

**生成日期**: 2025-10-24
**版本**: v1.0
