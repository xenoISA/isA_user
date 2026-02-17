# PostgreSQL gRPC Client 迁移问题与解决方案

## 核心问题总结

### 1. Proto ListValue 转换
**问题**: JSONB 字段返回 `google.protobuf.struct_pb2.ListValue` 对象，不是 Python list

**解决方案**:
```python
from google.protobuf.json_format import MessageToDict

api_keys_raw = row.get('api_keys', [])
if hasattr(api_keys_raw, 'values'):
    api_keys = [MessageToDict(val.struct_value) if hasattr(val, 'struct_value') else val
               for val in api_keys_raw.values]
```

### 2. JSONB 中的 Datetime
**问题**: JSONB 不能存储 datetime 对象

**解决方案**: 转换为 ISO 字符串
```python
key_data = {
    'created_at': now.isoformat(),
    'expires_at': expires_at.isoformat() if expires_at else None
}
```

### 3. Database DEFAULT 值
**问题**: 手动传递 created_at/updated_at 会冲突

**解决方案**: 让数据库自动设置，INSERT后重新查询
```python
# 不包含 created_at/updated_at
record = {'id': id, 'name': name}
count = db.insert_into(table, [record])
if count is not None and count > 0:
    return await self.get_record(id)  # 重新查询获取完整记录
```

### 4. gRPC 服务端口
**问题**: postgres-grpc在50061端口，不是默认的50051

**解决方案**: 
```python
db = PostgresClient(host='isa-postgres-grpc', port=50061, user_id='service-name')
```

服务端口映射:
- postgres-grpc: 50061
- minio-grpc: 50051  
- redis-grpc: 50055
- nats-grpc: 50056

### 5. insert_into 返回 None
**问题**: 失败时返回None，不抛异常

**解决方案**: 显式检查None
```python
count = db.insert_into(table, [data])
if count is not None and count > 0:  # 检查None
    return data
```

### 6. Schema 名称一致性
**问题**: Migration和代码使用不同schema

**解决方案**: 统一使用 `auth` schema
```python
self.schema = "auth"
```

## 迁移 Checklist

### 数据库准备
- [ ] 创建正确的schema
- [ ] 时间字段用 `TIMESTAMPTZ DEFAULT NOW()`
- [ ] JSONB 字段定义正确

### Repository 修改
- [ ] 导入 `PostgresClient`
- [ ] 配置正确 host/port
- [ ] 设置正确 schema
- [ ] 添加 proto ListValue 转换
- [ ] datetime 转 ISO 字符串
- [ ] 不传递 DEFAULT 字段
- [ ] 检查 insert 返回 None

### 测试
- [ ] 创建测试数据脚本
- [ ] 运行所有测试
- [ ] 验证 JSONB 读写

## 代码模板

```python
from isa_common.postgres_client import PostgresClient
from google.protobuf.json_format import MessageToDict

class Repository:
    def __init__(self):
        self.db = PostgresClient(host='isa-postgres-grpc', port=50061, user_id='service')
        self.schema = "auth"
    
    def _convert_proto_list(self, proto_raw):
        if hasattr(proto_raw, 'values'):
            return [MessageToDict(v.struct_value) if hasattr(v, 'struct_value') else v
                   for v in proto_raw.values]
        return proto_raw or []
    
    async def create(self, data):
        record = {
            'id': data['id'],
            'metadata': data.get('metadata', {}),
            'expires_at': data['expires_at'].isoformat() if data.get('expires_at') else None
        }
        with self.db:
            count = self.db.insert_into(self.table, [record], schema=self.schema)
        if count is not None and count > 0:
            return await self.get_by_id(record['id'])
        return None
```

## 测试结果

auth_service 迁移完成:
- JWT Authentication: 14/14 ✅
- Device Authentication: 11/11 ✅
- API Key Management: 8/8 ✅

**总计: 33/33 通过**

---

*文档日期: 2025-10-23*
*适用版本: auth_service v0.1.0*
