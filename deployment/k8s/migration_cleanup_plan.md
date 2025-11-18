# Migration Files Cleanup Plan

## 删除策略

**原则**：
- ✅ 保留：使用独立 schema 的新标准文件
- ❌ 删除：使用 `dev` schema 的旧标准文件

---

## 需要删除的文件清单

### 1. audit_service
```bash
rm microservices/audit_service/migrations/001_create_audit_events_table.sql
```
**保留**: `001_migrate_to_audit_schema.sql` (使用 audit schema)

### 2. billing_service
```bash
rm microservices/billing_service/migrations/001_create_billing_tables.sql
```
**保留**: `001_migrate_to_billing_schema.sql` (使用 billing schema)

### 3. compliance_service
```bash
rm microservices/compliance_service/migrations/001_create_compliance_tables.sql
```
**保留**: `001_migrate_to_compliance_schema.sql` (使用 compliance schema)

### 4. event_service
```bash
rm microservices/event_service/migrations/001_create_tables.sql
```
**保留**: `001_create_event_schema.sql` (使用 event schema)

### 5. location_service
```bash
rm microservices/location_service/migrations/001_initial_schema.sql
```
**保留**: `001_initial_schema_simple.sql` (简化版本，不需要 PostGIS)

### 6. notification_service
```bash
rm microservices/notification_service/migrations/001_create_notification_tables.sql
```
**保留**: `001_create_notification_schema.sql` (使用 notification schema)

### 7. order_service
```bash
rm microservices/order_service/migrations/001_create_orders_table.sql
```
**保留**: `001_create_order_schema.sql` (使用 orders schema)

### 8. payment_service
```bash
rm microservices/payment_service/migrations/001_create_payment_tables.sql
```
**保留**: `001_create_payment_schema.sql` (使用 payment schema)

### 9. product_service
```bash
rm microservices/product_service/migrations/001_create_product_tables.sql
```
**保留**: `001_migrate_to_product_schema.sql` (使用 product schema)

### 10. wallet_service
```bash
rm microservices/wallet_service/migrations/001_create_wallet_tables.sql
```
**保留**: `001_create_wallet_schema.sql` (使用 wallet schema)

### 11. weather_service
```bash
rm microservices/weather_service/migrations/001_create_weather_tables.sql
```
**保留**: `001_migrate_to_weather_schema.sql` (使用 weather schema)

---

## 其他有多个文件的服务

### album_service
```
✅ 000_init_schema.sql (创建 album schema)
✅ 001_create_album_tables.sql (在 album schema 中创建表)
```
**状态**: 正确，两个文件都需要，按顺序执行

### calendar_service
```
✅ 001_create_calendar_tables.sql
✅ 002_migrate_to_calendar_schema.sql
```
**状态**: 正确，按顺序执行

### media_service
```
✅ 000_init_schema.sql
✅ 001_create_media_tables.sql
```
**状态**: 正确，按顺序执行

### memory_service
```
✅ 000_init_schema.sql
✅ 001-009 各种 memory 表
```
**状态**: 正确，按顺序执行所有文件

### ota_service
```
✅ 001_create_ota_tables.sql
✅ 002_remove_cross_service_foreign_keys.sql
✅ 003_migrate_to_ota_schema.sql
```
**状态**: 正确，按顺序执行

### session_service
```
✅ 001-006 多个 migration 文件
```
**状态**: 正确，按顺序执行所有

### storage_service
```
✅ 001-004 多个 migration 文件
```
**状态**: 正确，按顺序执行所有

### task_service
```
✅ 001-004 多个 migration 文件
```
**状态**: 正确，按顺序执行所有

### telemetry_service
```
✅ 001_create_telemetry_tables.sql
✅ 002_migrate_to_telemetry_schema.sql
```
**状态**: 正确，按顺序执行

### vault_service
```
✅ 001_create_vault_tables.sql
✅ 002_add_encryption_fields.sql
✅ 003_remove_user_foreign_key.sql
```
**状态**: 正确，按顺序执行

---

## 执行删除的脚本

```bash
#!/bin/bash
# 删除旧的 migration 文件

echo "Deleting old migration files..."

rm microservices/audit_service/migrations/001_create_audit_events_table.sql
rm microservices/billing_service/migrations/001_create_billing_tables.sql
rm microservices/compliance_service/migrations/001_create_compliance_tables.sql
rm microservices/event_service/migrations/001_create_tables.sql
rm microservices/location_service/migrations/001_initial_schema.sql
rm microservices/notification_service/migrations/001_create_notification_tables.sql
rm microservices/order_service/migrations/001_create_orders_table.sql
rm microservices/payment_service/migrations/001_create_payment_tables.sql
rm microservices/product_service/migrations/001_create_product_tables.sql
rm microservices/wallet_service/migrations/001_create_wallet_tables.sql
rm microservices/weather_service/migrations/001_create_weather_tables.sql

echo "✅ Cleanup complete!"
echo ""
echo "Deleted files:"
echo "  - 11 old *_tables.sql files"
echo ""
echo "Remaining migrations use independent schemas (account, auth, wallet, etc.)"
```

---

## 验证

删除后，每个服务应该只有：
- 一个或多个按顺序编号的 migration 文件
- 所有文件使用独立的 schema（不是 `dev` schema）
- 文件按数字顺序执行（000, 001, 002...）
