# isA_Model 计费事件发布迁移指南

## 📋 概述

本文档说明如何修改 isA_Model，使其不再依赖 `isa_common` 的业务事件模型，而是直接使用基础的 NATS 客户端发布简单的使用记录数据。

## 🔄 修改内容

### 修改文件
- `isA_Model/isa_model/inference/services/base_service.py`

### 修改前（当前代码）

```python
# ❌ 依赖 isa_common 的业务事件模型
from isa_common.events import publish_usage_event

async def _publish_billing_event(...):
    """发布计费事件"""
    try:
        from isa_common.events import publish_usage_event
        
        success = await publish_usage_event(
            user_id=user_id,
            product_id=self.model_name,
            usage_amount=usage_amount,
            unit_type=unit_type,
            usage_details=usage_details,
            nats_host=nats_host,
            nats_port=nats_port
        )
        ...
```

### 修改后（新代码）

```python
# ✅ 只使用基础的 NATS 客户端
from isa_common.nats_client import NATSClient
import json

async def _publish_usage_event(
    self,
    user_id: str,
    service_type: Union[str, ServiceType],
    operation: str,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    input_units: Optional[float] = None,
    output_units: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    发布使用事件到 NATS
    
    isA_Model 只负责发布原始使用数据，不关心计费逻辑
    billing_service 会监听并处理这些事件
    
    NATS Subject: billing.usage.recorded.{product_id}
    Event Data: 简单的 JSON 数据，按约定格式发布
    """
    try:
        import logging
        from decimal import Decimal
        logger = logging.getLogger(__name__)
        
        logger.info(f"Publishing usage event for user={user_id}, model={self.model_name}")
        
        # 计算使用量
        if input_tokens is not None and output_tokens is not None:
            usage_amount = input_tokens + output_tokens
            unit_type = "token"
        elif input_units is not None:
            usage_amount = input_units
            unit_type = "request"
        else:
            logger.warning(f"No usage metrics provided for {user_id}")
            return False
        
        # 准备使用详情
        usage_details = {
            "provider": self.provider_name,
            "model": self.model_name,
            "operation": operation,
            "service_type": service_type if isinstance(service_type, str) else service_type.value,
        }
        
        # 添加 token 分解
        if input_tokens is not None:
            usage_details["input_tokens"] = input_tokens
        if output_tokens is not None:
            usage_details["output_tokens"] = output_tokens
        if input_units is not None:
            usage_details["input_units"] = float(input_units)
        if output_units is not None:
            usage_details["output_units"] = float(output_units)
        if metadata:
            usage_details.update(metadata)
        
        # 构造事件数据（按约定格式）
        event_data = {
            "user_id": user_id,
            "product_id": self.model_name,  # 产品ID = 模型名称
            "usage_amount": float(usage_amount),
            "unit_type": unit_type,
            "usage_details": usage_details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 获取 NATS 连接信息
        import os
        from isa_common.consul_client import ConsulRegistry
        
        nats_host = None
        nats_port = None
        
        try:
            # 尝试通过 Consul 发现 NATS
            consul_host = os.getenv('CONSUL_HOST', 'localhost')
            consul_port = int(os.getenv('CONSUL_PORT', '8500'))
            consul = ConsulRegistry(consul_host=consul_host, consul_port=consul_port)
            
            nats_url = consul.get_nats_url()
            if '://' in nats_url:
                nats_url = nats_url.split('://', 1)[1]
            nats_host, port_str = nats_url.rsplit(':', 1)
            nats_port = int(port_str)
            logger.info(f"Discovered NATS via Consul: {nats_host}:{nats_port}")
        except Exception as consul_err:
            logger.debug(f"Consul discovery failed: {consul_err}, using environment variables")
            # 使用环境变量或默认值
            nats_host = os.getenv('NATS_HOST', 'localhost')
            nats_port = int(os.getenv('NATS_PORT', '50056'))
        
        # 创建 NATS 客户端
        nats_client = NATSClient(
            host=nats_host,
            port=nats_port,
            user_id=user_id
        )
        
        # 发布事件
        # NATS Subject 格式: billing.usage.recorded.{product_id}
        subject = f"billing.usage.recorded.{self.model_name}"
        data = json.dumps(event_data).encode('utf-8')
        
        result = nats_client.publish(
            subject=subject,
            data=data,
            headers={"event_type": "billing.usage.recorded"}
        )
        
        if result and result.get('success'):
            logger.info(
                f"Published usage event: {self.model_name} for user {user_id}, "
                f"usage {usage_amount} {unit_type}"
            )
            return True
        else:
            logger.error(f"Failed to publish usage event: {result}")
            return False
            
    except Exception as e:
        # 不让计费事件发布失败影响主业务
        import logging
        logging.getLogger(__name__).warning(
            f"Failed to publish usage event: {e}",
            exc_info=True
        )
        return False
```

## 📝 完整修改步骤

### 1. 备份原文件

```bash
cd /Users/xenodennis/Documents/Fun/isA_Model
cp isa_model/inference/services/base_service.py isa_model/inference/services/base_service.py.backup
```

### 2. 修改 base_service.py

找到 `_publish_billing_event` 方法（大约在第 49 行），替换为上面的 `_publish_usage_event` 新实现。

### 3. 修改方法调用

在所有调用 `_publish_billing_event` 的地方，保持方法签名不变，内部实现已更新。

### 4. 移除不需要的导入

```python
# 移除
# from isa_common.events import publish_usage_event  ❌

# 添加
from isa_common.nats_client import NATSClient  # ✅
import json  # ✅
from datetime import datetime  # ✅
```

## 🧪 测试验证

### 测试 1: 验证事件发布

```python
# 在 isA_Model 项目中运行
python -m pytest tests/test_billing_event_publish.py -v
```

### 测试 2: 手动验证

```python
import asyncio
from isa_model.inference.services.llm import OpenAILLMService

async def test_usage_event():
    service = OpenAILLMService(
        provider_name="openai",
        model_name="gpt-4"
    )
    
    # 模拟发布使用事件
    await service._publish_usage_event(
        user_id="test_user_123",
        service_type="text",
        operation="chat",
        input_tokens=100,
        output_tokens=200
    )
    
    print("Usage event published successfully!")

asyncio.run(test_usage_event())
```

### 测试 3: 监听 NATS 事件

```bash
# 使用 NATS CLI 监听事件
nats sub "billing.usage.recorded.>"
```

预期输出：
```json
{
  "user_id": "test_user_123",
  "product_id": "gpt-4",
  "usage_amount": 300,
  "unit_type": "token",
  "usage_details": {
    "provider": "openai",
    "model": "gpt-4",
    "operation": "chat",
    "service_type": "text",
    "input_tokens": 100,
    "output_tokens": 200
  },
  "timestamp": "2025-01-09T12:00:00.000000"
}
```

## 📊 对比

| 方面 | 修改前 | 修改后 |
|------|--------|--------|
| **依赖** | isa_common.events (业务逻辑) | isa_common.nats_client (基础设施) |
| **事件模型** | UsageEvent (Pydantic) | 简单 dict/JSON |
| **职责** | 知道业务事件格式 | 只知道数据格式约定 |
| **耦合度** | 高（依赖 isA_user 业务） | 低（只依赖协议） |
| **测试** | 需要 mock 复杂事件模型 | 只需验证 JSON 数据 |

## ✅ 验证清单

- [ ] 修改 `base_service.py` 的 `_publish_billing_event` 方法
- [ ] 移除 `from isa_common.events import publish_usage_event`
- [ ] 添加 `from isa_common.nats_client import NATSClient`
- [ ] 运行单元测试确保没有破坏现有功能
- [ ] 启动 isA_Model 服务
- [ ] 启动 billing_service（监听 billing.usage.recorded.*）
- [ ] 发送测试请求，验证计费流程
- [ ] 检查 billing_records 表是否有新记录
- [ ] 检查 wallet transactions 表是否有扣费记录

## 🔗 相关文档

- [计费流程架构](./billing_flow_architecture.md)
- [事件契约文档](./event_contracts.md)
- [NATS 客户端使用指南](./nats_client_usage.md)

---

最后更新: 2025-01-09
