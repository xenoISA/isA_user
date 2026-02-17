# Event Service 测试指南

## 基于真实测试的完整验证流程

这个文档基于我们刚刚完成的真实测试，提供完整的测试验证步骤。

## 测试环境设置

### 1. 服务启动验证

```bash
# 启动服务
python -m microservices.event_service.main

# 验证输出应包含：
# [event-service] Service started successfully on port 8230
# [event-service] Connected to NATS successfully
```

### 2. 依赖服务检查

```bash
# 检查NATS服务器
nats --version

# 检查数据库连接
psql $DATABASE_URL -c "SELECT 1;"
```

## 功能测试用例

### 测试1：基础健康检查

```python
import requests

def test_health_check():
    """测试服务健康状态"""
    response = requests.get('http://localhost:8230/health')
    assert response.status_code == 200
    
    data = response.json()
    assert data['status'] == 'healthy'
    assert data['service'] == 'event-service'
    assert 'timestamp' in data
    
    print("✅ 基础健康检查通过")

# 运行测试
test_health_check()
```

**预期输出：**
```json
{
  "status": "healthy",
  "service": "event-service", 
  "version": "1.0.0",
  "timestamp": "2025-09-28T04:11:59.929021"
}
```

### 测试2：前端事件采集健康检查

```python
def test_frontend_health():
    """测试前端事件采集健康状态"""
    response = requests.get('http://localhost:8230/api/frontend/health')
    assert response.status_code == 200
    
    data = response.json()
    assert data['status'] == 'healthy'
    assert data['service'] == 'frontend-event-collection'
    assert data['nats_connected'] == True
    
    print("✅ 前端采集健康检查通过")

test_frontend_health()
```

### 测试3：单个事件创建

```python
def test_create_single_event():
    """测试创建单个后端事件"""
    event_data = {
        'event_type': 'test_event',
        'event_source': 'backend',
        'event_category': 'user_action',
        'user_id': 'test_user_123',
        'data': {'test': 'data', 'value': 42}
    }
    
    response = requests.post(
        'http://localhost:8230/api/events/create',
        json=event_data,
        headers={'Content-Type': 'application/json'}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert 'event_id' in data
    assert data['event_type'] == 'test_event'
    assert data['user_id'] == 'test_user_123'
    assert data['status'] == 'pending'
    
    print(f"✅ 事件创建成功，ID: {data['event_id']}")
    return data['event_id']

event_id = test_create_single_event()
```

### 测试4：前端单个事件采集

```python
def test_frontend_single_event():
    """测试前端单个事件采集"""
    frontend_event = {
        'event_type': 'page_view',
        'category': 'user_interaction',
        'page_url': 'https://example.com/dashboard',
        'user_id': 'user123',
        'session_id': 'session456',
        'data': {
            'page_title': 'Dashboard',
            'load_time': 1.5,
            'referrer': 'https://google.com'
        },
        'metadata': {
            'browser': 'Chrome',
            'version': '120.0'
        }
    }
    
    response = requests.post(
        'http://localhost:8230/api/frontend/events',
        json=frontend_event,
        headers={'Content-Type': 'application/json'}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data['status'] == 'accepted'
    assert 'event_id' in data
    assert data['message'] == 'Event published to stream'
    
    print(f"✅ 前端事件采集成功，ID: {data['event_id']}")
    return data['event_id']

frontend_event_id = test_frontend_single_event()
```

### 测试5：前端批量事件采集

```python
def test_frontend_batch_events():
    """测试前端批量事件采集"""
    batch_events = {
        'events': [
            {
                'event_type': 'button_click',
                'category': 'user_interaction',
                'page_url': 'https://example.com/dashboard',
                'user_id': 'user123',
                'session_id': 'session456',
                'data': {'button_id': 'save_btn', 'action': 'save_profile'},
                'metadata': {'element_text': 'Save Changes'}
            },
            {
                'event_type': 'form_submit',
                'category': 'business_action',
                'page_url': 'https://example.com/profile',
                'user_id': 'user123',
                'session_id': 'session456',
                'data': {'form_name': 'user_profile', 'fields_count': 5},
                'metadata': {'validation_passed': 'true'}
            },
            {
                'event_type': 'api_error',
                'category': 'system_event',
                'page_url': 'https://example.com/profile',
                'user_id': 'user123',
                'session_id': 'session456',
                'data': {'error_code': 500, 'endpoint': '/api/user/update'},
                'metadata': {'retry_count': '1'}
            }
        ],
        'client_info': {
            'browser': 'Chrome',
            'version': '120.0',
            'device': 'desktop',
            'screen_resolution': '1920x1080'
        }
    }
    
    response = requests.post(
        'http://localhost:8230/api/frontend/events/batch',
        json=batch_events,
        headers={'Content-Type': 'application/json'}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data['status'] == 'accepted'
    assert data['processed_count'] == 3
    assert len(data['event_ids']) == 3
    assert 'Batch of 3 events published' in data['message']
    
    print(f"✅ 批量事件采集成功，处理了 {data['processed_count']} 个事件")
    print(f"   事件IDs: {data['event_ids']}")
    
    return data['event_ids']

batch_event_ids = test_frontend_batch_events()
```

## 完整测试脚本

将以上所有测试合并成一个完整的测试脚本：

```python
#!/usr/bin/env python3
"""
Event Service 完整测试套件
基于真实测试验证的功能测试
"""

import requests
import json
import time
from datetime import datetime

def main():
    """运行完整测试套件"""
    print("🚀 开始 Event Service 测试")
    print("=" * 50)
    
    try:
        # 基础测试
        test_health_check()
        test_frontend_health()
        
        # 功能测试
        event_id = test_create_single_event()
        frontend_event_id = test_frontend_single_event()
        batch_event_ids = test_frontend_batch_events()
        
        # 性能测试
        test_performance()
        
        print("\n" + "=" * 50)
        print("🎉 所有测试通过！")
        print(f"📊 测试总结:")
        print(f"   - 后端事件: 1 个")
        print(f"   - 前端单个事件: 1 个") 
        print(f"   - 前端批量事件: 3 个")
        print(f"   - 总计: 5 个事件成功处理")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False
        
    return True

def test_performance():
    """性能测试"""
    print("\n🔥 运行性能测试...")
    
    start_time = time.time()
    
    # 连续发送10个事件
    for i in range(10):
        event_data = {
            'event_type': f'perf_test_{i}',
            'category': 'user_interaction',
            'user_id': f'perf_user_{i}',
            'data': {'iteration': i, 'timestamp': datetime.now().isoformat()}
        }
        
        response = requests.post(
            'http://localhost:8230/api/frontend/events',
            json=event_data
        )
        assert response.status_code == 200
    
    end_time = time.time()
    duration = end_time - start_time
    throughput = 10 / duration
    
    print(f"✅ 性能测试通过")
    print(f"   - 10个事件处理时间: {duration:.2f}秒")
    print(f"   - 吞吐量: {throughput:.1f} 事件/秒")

if __name__ == "__main__":
    main()
```

## 保存并运行测试

1. **保存测试脚本**：
```bash
# 保存为 test_event_service.py
python test_event_service.py
```

2. **使用 curl 快速测试**：
```bash
# 快速健康检查
curl -s http://localhost:8230/health | jq

# 快速事件测试
curl -X POST http://localhost:8230/api/frontend/events \
  -H "Content-Type: application/json" \
  -d '{"event_type":"quick_test","category":"user_interaction","data":{"test":true}}' | jq
```

## 验证事件流

### NATS 事件流验证

```bash
# 如果安装了 nats CLI 工具
nats stream ls
nats stream info EVENTS
nats consumer ls EVENTS
```

### 数据库验证

```sql
-- 查看存储的事件
SELECT event_id, event_type, event_source, created_at 
FROM events 
ORDER BY created_at DESC 
LIMIT 10;
```

## 故障排查指南

### 常见问题及解决方案

1. **连接超时错误**
   ```
   HTTPConnectionPool(host='localhost', port=8230): Max retries exceeded
   ```
   - 检查服务是否启动：`ps aux | grep event_service`
   - 检查端口占用：`lsof -i :8230`

2. **NATS认证错误**
   ```
   nats: 'Authorization Violation'
   ```
   - 验证NATS_USERNAME和NATS_PASSWORD环境变量
   - 检查NATS服务器配置

3. **数据库连接错误**
   ```
   Error getting event statistics
   ```
   - 验证DATABASE_URL正确性
   - 检查数据库权限和Schema

## 持续测试

### 自动化测试脚本

```bash
#!/bin/bash
# 定期健康检查脚本

while true; do
    if curl -f -s http://localhost:8230/health > /dev/null; then
        echo "$(date): ✅ Event Service healthy"
    else
        echo "$(date): ❌ Event Service unhealthy"
        # 可以添加告警逻辑
    fi
    sleep 60
done
```

### 监控指标

建议监控的关键指标：

- 服务响应时间 (<100ms)
- 事件处理成功率 (>99%)
- NATS连接状态 (始终连接)
- 内存使用量 (<512MB)
- 错误日志频率 (<1/分钟)

这个测试指南基于我们刚才的真实测试，确保了所有功能都经过验证并可以正常工作。