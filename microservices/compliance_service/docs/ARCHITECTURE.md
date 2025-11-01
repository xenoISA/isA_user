# Compliance Service - 架构设计文档

## 系统概览

Compliance Service是isA_user平台的核心安全组件，为AI Agent平台提供全面的内容合规检查和安全防护。

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         isA_user Platform                           │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │ isa_agent    │  │ Account      │  │ Storage      │            │
│  │ (Frontend)   │  │ Service      │  │ Service      │            │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘            │
│         │                  │                  │                     │
│         └──────────────────┼──────────────────┘                     │
│                           ▼                                         │
│               ┌─────────────────────────┐                          │
│               │  Compliance Service     │◄──────┐                  │
│               │  (Port 8250)            │       │                  │
│               └───────┬─────────────────┘       │                  │
│                       │                         │                  │
│         ┌─────────────┼─────────────────────────┼─────┐           │
│         │             │                         │     │           │
│         ▼             ▼                         ▼     ▼           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Content  │  │   PII    │  │ Prompt   │  │ Toxicity │         │
│  │Moderation│  │Detection │  │Injection │  │ Check    │         │
│  │  Engine  │  │  Engine  │  │ Detector │  │  Engine  │         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
│         │             │                         │                  │
│         └─────────────┼─────────────────────────┘                  │
│                       ▼                                            │
│            ┌─────────────────────┐                                │
│            │  External AI APIs   │                                │
│            ├─────────────────────┤                                │
│            │ • OpenAI Moderation │                                │
│            │ • AWS Comprehend    │                                │
│            │ • Perspective API   │                                │
│            └─────────────────────┘                                │
│                       │                                            │
│                       ▼                                            │
│         ┌────────────────────────────┐                            │
│         │  Data & Event Layer        │                            │
│         ├────────────────────────────┤                            │
│         │ • Supabase (PostgreSQL)    │                            │
│         │ • NATS Event Bus           │                            │
│         │ • Audit Service            │                            │
│         └────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 核心组件

### 1. API层 (`main.py`)

**职责:**
- 提供RESTful API端点
- 请求验证和路由
- 响应格式化
- 错误处理

**主要端点:**
```
POST   /api/compliance/check          - 单次合规检查
POST   /api/compliance/check/batch    - 批量检查
GET    /api/compliance/checks/{id}    - 查询检查记录
GET    /api/compliance/reviews/pending - 待审核队列
PUT    /api/compliance/reviews/{id}   - 更新审核状态
POST   /api/compliance/reports         - 生成报告
GET    /api/compliance/stats          - 统计数据
POST   /api/compliance/policies        - 创建策略
```

### 2. 业务逻辑层 (`compliance_service.py`)

**职责:**
- 合规检查编排
- 策略评估
- 风险评分
- 行动决策

**核心方法:**
```python
class ComplianceService:
    async def perform_compliance_check()  # 主检查流程
    async def _check_content_moderation() # 内容审核
    async def _check_pii_detection()      # PII检测
    async def _check_prompt_injection()   # 注入检测
    async def _evaluate_results()         # 结果评估
    async def _determine_action()         # 行动决策
```

### 3. 检查引擎

#### 3.1 Content Moderation Engine（内容审核引擎）

**文件:** `compliance_service.py` - 第156-289行

**功能:**
- 检测有害内容（仇恨言论、暴力、色情等）
- 支持文本、图片、音频、视频
- 多provider支持（OpenAI, AWS, local rules）

**检测类别:**
```python
ModerationCategory:
- HATE_SPEECH     # 仇恨言论
- VIOLENCE        # 暴力内容
- SEXUAL          # 色情内容
- HARASSMENT      # 骚扰
- SELF_HARM       # 自残
- ILLEGAL         # 违法内容
- SPAM            # 垃圾信息
- MISINFORMATION  # 虚假信息
- CHILD_SAFETY    # 儿童安全
```

**处理流程:**
```
Text/Image/Audio → Provider API → Category Scores → 
Risk Assessment → Action Decision
```

#### 3.2 PII Detection Engine（个人信息检测引擎）

**文件:** `compliance_service.py` - 第291-361行

**功能:**
- 识别个人敏感信息
- 自动脱敏处理
- GDPR/HIPAA合规支持

**检测类型:**
```python
PIIType:
- EMAIL           # 邮箱地址
- PHONE           # 电话号码
- SSN             # 社保号
- CREDIT_CARD     # 信用卡号
- PASSPORT        # 护照号码
- DRIVER_LICENSE  # 驾照号码
- IP_ADDRESS      # IP地址
- ADDRESS         # 家庭住址
- NAME            # 姓名
- DATE_OF_BIRTH   # 出生日期
- MEDICAL_INFO    # 医疗信息
```

**检测方法:**
```python
# 1. 正则表达式匹配
EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

# 2. NLP实体识别（可选）
# 3. AWS Comprehend PII API（可选）
```

#### 3.3 Prompt Injection Detector（提示词注入检测器）

**文件:** `compliance_service.py` - 第368-462行

**功能:**
- 检测恶意提示词注入尝试
- 防止AI系统被操控
- 保护系统提示词

**检测模式:**
```python
INJECTION_PATTERNS = [
    r'ignore\s+(previous|above|prior)\s+(instructions|prompts?)',
    r'forget\s+(everything|all|previous)',
    r'you\s+are\s+now',
    r'system\s*:\s*',
    r'</?\s*system\s*>',
    r'jailbreak',
    r'developer\s+mode',
    r'override\s+(safety|rules|restrictions)',
]
```

**风险分级:**
```
High Risk (>0.8):     直接注入尝试 → 立即阻止
Medium Risk (0.5-0.8): 可疑模式 → 标记审核
Low Risk (<0.5):      安全 → 放行
```

### 4. 数据访问层 (`compliance_repository.py`)

**职责:**
- 数据库操作封装
- 查询优化
- 事务管理

**主要操作:**
```python
class ComplianceRepository:
    # 检查记录
    async def create_check()
    async def get_check_by_id()
    async def get_checks_by_user()
    
    # 审核管理
    async def get_pending_reviews()
    async def update_review_status()
    
    # 统计报告
    async def get_statistics()
    async def get_violations_summary()
    
    # 策略管理
    async def create_policy()
    async def get_active_policies()
```

### 5. 集成层 (`middleware.py`)

**职责:**
- 其他服务集成
- 请求拦截
- 自动化检查

**组件:**
```python
# 1. 中间件（自动拦截）
ComplianceMiddleware
  - 拦截特定路径请求
  - 自动执行合规检查
  - 阻止违规请求

# 2. 客户端（手动调用）
ComplianceClient
  - check_text()
  - check_prompt()
  - check_file()
  
# 3. 依赖注入
require_compliance_check()
  - FastAPI依赖
  - 强制检查通过
```

---

## 数据模型

### 数据库Schema

**文件:** `migrations/001_create_compliance_tables.sql`

#### 主表: `compliance_checks`

```sql
CREATE TABLE compliance_checks (
    id SERIAL PRIMARY KEY,
    check_id VARCHAR(100) UNIQUE NOT NULL,
    
    -- 检查信息
    check_type VARCHAR(50) NOT NULL,
    content_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    
    -- 关联
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),
    
    -- 结果
    confidence_score DECIMAL(3,2),
    violations JSONB,
    warnings JSONB,
    detected_pii JSONB,
    
    -- 审核
    human_review_required BOOLEAN,
    reviewed_by VARCHAR(100),
    review_notes TEXT,
    
    -- 时间戳
    checked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE,
    
    -- 索引
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_checked_at (checked_at DESC)
);
```

#### 策略表: `compliance_policies`

```sql
CREATE TABLE compliance_policies (
    id SERIAL PRIMARY KEY,
    policy_id VARCHAR(100) UNIQUE,
    policy_name VARCHAR(200),
    organization_id VARCHAR(100),
    
    -- 配置
    content_types TEXT[],
    check_types TEXT[],
    rules JSONB,
    thresholds JSONB,
    
    -- 行为
    auto_block BOOLEAN,
    require_human_review BOOLEAN,
    
    -- 状态
    is_active BOOLEAN,
    priority INTEGER
);
```

---

## 数据流

### 1. 实时检查流程

```
User Request
    │
    ▼
┌─────────────────────────────────┐
│ 1. API接收请求                   │
│    - 验证参数                    │
│    - 提取内容                    │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 2. 策略查询                      │
│    - 获取组织策略                │
│    - 确定检查类型                │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 3. 并发执行检查                  │
│    ├─ Content Moderation        │
│    ├─ PII Detection             │
│    └─ Prompt Injection          │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 4. 结果评估                      │
│    - 计算风险级别                │
│    - 识别违规项                  │
│    - 确定行动                    │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 5. 保存记录                      │
│    - 写入数据库                  │
│    - 发送NATS事件                │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 6. 返回响应                      │
│    - 格式化结果                  │
│    - 添加建议                    │
└────────────┬────────────────────┘
             │
             ▼
      Response to User
```

### 2. 人工审核流程

```
Flagged Content
    │
    ▼
┌─────────────────────────────────┐
│ 1. 加入审核队列                  │
│    status: pending               │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 2. 分配审核员                    │
│    assigned_to: reviewer_id      │
│    status: in_review             │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 3. 审核员决策                    │
│    - 查看内容                    │
│    - 做出决定                    │
│    - 添加备注                    │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 4. 更新状态                      │
│    status: pass/fail             │
│    reviewed_by: reviewer_id      │
│    reviewed_at: timestamp        │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 5. 通知相关方                    │
│    - 通知用户                    │
│    - 发送事件                    │
└─────────────────────────────────┘
```

---

## 集成架构

### 与现有服务集成

```
┌────────────────────────────────────────────────────────────┐
│                    Service Integration                      │
└────────────────────────────────────────────────────────────┘

Account Service (8202)
    │
    ├─→ 用户注册时检查个人信息
    └─→ 个人资料更新时检查内容
            │
            ▼
    Compliance Service (8250)
            │
            ▼
    POST /api/compliance/check
    {
        "user_id": "...",
        "content_type": "text",
        "content": "user profile info",
        "check_types": ["pii_detection", "content_moderation"]
    }

───────────────────────────────────────────────────────

Storage Service (8209)
    │
    ├─→ 文件上传前检查
    ├─→ 图片内容审核
    └─→ 音频内容检查
            │
            ▼
    Compliance Service (8250)
            │
            ▼
    POST /api/compliance/check
    {
        "user_id": "...",
        "content_type": "image",
        "content_id": "file_id",
        "check_types": ["content_moderation"]
    }

───────────────────────────────────────────────────────

Audit Service (8203)
    │
    ├─→ 订阅合规事件
    └─→ 记录审计日志
            ▲
            │
    Compliance Service (8250)
            │
            ▼
    NATS Event: compliance.check.completed
    {
        "check_id": "...",
        "user_id": "...",
        "status": "fail",
        "risk_level": "high",
        "violations": [...]
    }
```

---

## 部署架构

### 生产环境部署

```
┌─────────────────────────────────────────────────────┐
│                   Load Balancer                     │
│                   (Nginx/HAProxy)                   │
└──────────────┬──────────────────────────────────────┘
               │
               ├─────────────┬─────────────┬──────────
               │             │             │
               ▼             ▼             ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ Compliance   │ │ Compliance   │ │ Compliance   │
    │ Service 1    │ │ Service 2    │ │ Service 3    │
    │ (Container)  │ │ (Container)  │ │ (Container)  │
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                │                │
           └────────────────┼────────────────┘
                           ▼
              ┌──────────────────────────┐
              │   Shared Resources       │
              ├──────────────────────────┤
              │ • PostgreSQL (Supabase)  │
              │ • Redis Cache            │
              │ • NATS Cluster           │
              └──────────────────────────┘
```

### 扩展策略

**水平扩展:**
- 无状态设计，支持任意数量实例
- 通过负载均衡器分发请求
- 共享数据库和缓存

**垂直扩展:**
- 增加单实例资源（CPU/内存）
- 用于处理复杂的AI检查

**弹性伸缩:**
```yaml
# Kubernetes HPA配置示例
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: compliance-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: compliance-service
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 性能特征

### 响应时间

| 检查类型 | 平均响应时间 | P95 | P99 |
|---------|-------------|-----|-----|
| 文本审核（本地）| 50ms | 100ms | 150ms |
| 文本审核（OpenAI）| 200ms | 400ms | 600ms |
| PII检测 | 30ms | 60ms | 100ms |
| 提示词注入检测 | 20ms | 40ms | 80ms |
| 图片审核 | 500ms | 1000ms | 1500ms |

### 吞吐量

- **单实例:** ~100 req/s
- **3实例集群:** ~300 req/s
- **批量处理:** ~1000 items/s

### 资源使用

```
单实例资源需求:
- CPU: 2 cores
- Memory: 4GB
- Network: 100Mbps
- Storage: 50GB (日志+缓存)
```

---

## 安全考虑

### 1. 认证授权

```python
# API密钥认证
@app.post("/api/compliance/check")
async def check(
    request: ComplianceCheckRequest,
    api_key: str = Header(...)
):
    if not validate_api_key(api_key):
        raise HTTPException(401, "Invalid API key")
    
    # 继续处理...
```

### 2. 数据加密

- **传输加密:** TLS 1.3
- **存储加密:** 敏感字段AES-256加密
- **PII脱敏:** 自动掩码处理

### 3. 访问控制

```python
# 基于角色的访问控制
ROLES = {
    "user": ["check_content"],
    "moderator": ["check_content", "review_content"],
    "admin": ["check_content", "review_content", "manage_policies"]
}
```

---

## 监控和可观测性

### Metrics (Prometheus)

```python
# 关键指标
compliance_checks_total           # 总检查数
compliance_checks_failed          # 失败数
compliance_check_duration_seconds # 检查耗时
compliance_violations_by_type     # 按类型的违规数
```

### Logging (Loki)

```python
# 结构化日志
logger.info(
    "Compliance check completed",
    extra={
        "check_id": check_id,
        "user_id": user_id,
        "status": status,
        "risk_level": risk_level,
        "processing_time_ms": duration
    }
)
```

### Tracing (Jaeger)

```python
# 分布式追踪
@tracer.start_as_current_span("compliance_check")
async def perform_check(request):
    with tracer.start_as_current_span("content_moderation"):
        await moderate_content()
    
    with tracer.start_as_current_span("pii_detection"):
        await detect_pii()
```

---

## 未来扩展

### 短期(3个月)

- [ ] 集成更多AI审核provider
- [ ] 增加图片/视频审核能力
- [ ] 实现实时流式内容检查
- [ ] 优化批量处理性能

### 中期(6个月)

- [ ] 机器学习模型自训练
- [ ] 多语言支持增强
- [ ] WebHook通知支持
- [ ] 合规报告可视化

### 长期(12个月)

- [ ] 联邦学习支持
- [ ] 区块链审计追踪
- [ ] 零知识证明合规
- [ ] 全自动化审核

---

## 参考资源

### 文件说明

| 文件 | 描述 | 行数 |
|------|------|------|
| `models.py` | 数据模型定义 | ~500 |
| `compliance_service.py` | 核心业务逻辑 | ~650 |
| `compliance_repository.py` | 数据访问层 | ~400 |
| `main.py` | API服务入口 | ~600 |
| `middleware.py` | 集成中间件 | ~400 |
| `migrations/*.sql` | 数据库迁移 | ~300 |
| `examples/*.py` | 集成示例 | ~700 |

### 相关文档

- [README.md](../README.md) - 快速开始指南
- [BEST_PRACTICES.md](BEST_PRACTICES.md) - 最佳实践
- [API文档](http://localhost:8250/docs) - Swagger UI

---

**最后更新:** 2025-10-22  
**版本:** 1.0.0  
**作者:** isA_user Platform Team

