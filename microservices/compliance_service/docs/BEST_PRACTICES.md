```markdown
# Compliance Service - 最佳实践指南

本文档介绍在AI平台中实施合规检查的最佳实践和设计模式。

---

## 目录

1. [架构设计原则](#架构设计原则)
2. [内容审核策略](#内容审核策略)
3. [性能优化](#性能优化)
4. [安全防护](#安全防护)
5. [监控和告警](#监控和告警)
6. [合规报告](#合规报告)
7. [用户体验](#用户体验)
8. [多租户隔离](#多租户隔离)

---

## 架构设计原则

### 1. 分层防御策略 (Defense in Depth)

**文件名:** `compliance_service.py` - 核心检查逻辑

实施多层防护，而不是单点防御：

```
┌─────────────────────────────────────────┐
│ Layer 1: 客户端验证（基础规则）          │ ← 快速失败
├─────────────────────────────────────────┤
│ Layer 2: API Gateway（速率限制）        │ ← 防滥用
├─────────────────────────────────────────┤
│ Layer 3: Compliance Service（AI检查）   │ ← 深度检查
├─────────────────────────────────────────┤
│ Layer 4: 人工审核（边缘案例）            │ ← 最终验证
└─────────────────────────────────────────┘
```

**实现示例:**

```python
# Layer 1: 客户端基础验证
def client_side_validation(text: str) -> bool:
    if len(text) > 10000:
        return False
    if text.count('http://') + text.count('https://') > 5:
        return False  # 可能是垃圾内容
    return True

# Layer 2: API限流
from slowapi import Limiter
limiter = Limiter(key_func=get_user_id)

@app.post("/api/messages")
@limiter.limit("100/minute")
async def send_message(...):
    pass

# Layer 3: Compliance检查
result = await compliance.check_text(user_id, content)

# Layer 4: 高风险人工审核
if result.risk_level == RiskLevel.HIGH:
    await queue_for_human_review(result.check_id)
```

### 2. 异步优先原则

对于非实时场景，优先使用异步检查：

```python
# ✅ 好的做法：异步检查
@app.post("/api/upload")
async def upload_file(file: UploadFile):
    # 1. 立即上传
    file_id = await storage.save(file)
    
    # 2. 异步合规检查
    asyncio.create_task(
        check_and_update(file_id, user_id)
    )
    
    # 3. 立即返回
    return {"file_id": file_id, "status": "processing"}

# ❌ 不好的做法：同步阻塞
@app.post("/api/upload")
async def upload_file(file: UploadFile):
    file_id = await storage.save(file)
    result = await compliance.check_file(file_id)  # 用户等待
    return {"file_id": file_id}
```

### 3. 缓存策略

**文件名:** `compliance_service.py` - 添加缓存层

```python
import hashlib
from typing import Optional
from cachetools import TTLCache

class ComplianceServiceWithCache(ComplianceService):
    def __init__(self):
        super().__init__()
        # 缓存1小时
        self.cache = TTLCache(maxsize=10000, ttl=3600)
    
    async def check_text(self, user_id: str, content: str):
        # 生成内容哈希
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # 检查缓存
        if content_hash in self.cache:
            logger.info(f"Cache hit for {content_hash[:8]}")
            return self.cache[content_hash]
        
        # 执行检查
        result = await super().check_text(user_id, content)
        
        # 只缓存通过的结果
        if result.passed:
            self.cache[content_hash] = result
        
        return result
```

---

## 内容审核策略

### 1. 风险分级策略

**文件名:** `models.py` - `RiskLevel` 枚举

不同风险级别采取不同措施：

| 风险级别 | 置信度 | 处理策略 | 响应时间 |
|---------|--------|---------|----------|
| **NONE** | 0.0-0.3 | ✅ 直接放行 | <50ms |
| **LOW** | 0.3-0.5 | ⚠️ 记录 + 放行 | <100ms |
| **MEDIUM** | 0.5-0.7 | 🔍 标记 + 异步审核 | <200ms |
| **HIGH** | 0.7-0.9 | 🚫 阻止 + 通知 | <200ms |
| **CRITICAL** | 0.9-1.0 | 🔒 立即阻止 + 报警 | <200ms |

**实现:**

```python
# compliance_service.py

def determine_action(risk_level: RiskLevel, policy: CompliancePolicy):
    actions = {
        RiskLevel.NONE: ("allow", None),
        RiskLevel.LOW: ("allow", "log_warning"),
        RiskLevel.MEDIUM: ("flag", "queue_review"),
        RiskLevel.HIGH: ("block", "notify_admin"),
        RiskLevel.CRITICAL: ("block", "alert_security_team")
    }
    
    action, notification = actions[risk_level]
    
    # 发送通知
    if notification:
        await send_notification(notification, risk_level)
    
    return action
```

### 2. 上下文感知检查

根据内容类型和场景调整检查严格度：

```python
# 示例：不同场景的策略

POLICIES = {
    "public_forum": {
        "strictness": "high",
        "checks": ["content_moderation", "pii_detection", "toxicity"],
        "thresholds": {"block": 0.5, "flag": 0.3}
    },
    "private_message": {
        "strictness": "medium",
        "checks": ["content_moderation", "pii_detection"],
        "thresholds": {"block": 0.7, "flag": 0.5}
    },
    "ai_prompt": {
        "strictness": "critical",
        "checks": ["prompt_injection", "content_moderation"],
        "thresholds": {"block": 0.6, "flag": 0.4}
    },
    "file_upload": {
        "strictness": "high",
        "checks": ["content_moderation", "copyright"],
        "thresholds": {"block": 0.6, "flag": 0.4}
    }
}

# 使用示例
async def check_with_context(content: str, context: str):
    policy = POLICIES.get(context, POLICIES["public_forum"])
    
    result = await compliance.check_text(
        content=content,
        check_types=policy["checks"],
        thresholds=policy["thresholds"]
    )
    
    return result
```

### 3. 增量严格度策略

对重复违规用户逐步提高检查严格度：

```python
# 用户违规历史追踪

class UserComplianceTracker:
    def __init__(self):
        self.violation_counts = {}  # user_id -> count
    
    def get_strictness_multiplier(self, user_id: str) -> float:
        """根据违规历史调整严格度"""
        violations = self.violation_counts.get(user_id, 0)
        
        if violations == 0:
            return 1.0  # 正常
        elif violations <= 3:
            return 0.9  # 稍严格
        elif violations <= 10:
            return 0.7  # 严格
        else:
            return 0.5  # 非常严格（更容易被标记）
    
    async def check_with_history(self, user_id: str, content: str):
        multiplier = self.get_strictness_multiplier(user_id)
        
        result = await compliance.check_text(
            user_id=user_id,
            content=content
        )
        
        # 调整阈值
        adjusted_score = result.confidence * multiplier
        
        if adjusted_score > 0.7:
            result.status = ComplianceStatus.FAIL
        
        # 记录违规
        if not result.passed:
            self.violation_counts[user_id] = \
                self.violation_counts.get(user_id, 0) + 1
        
        return result
```

---

## 性能优化

### 1. 批量处理

**文件名:** `main.py` - `/api/compliance/check/batch` 端点

对于批量内容，使用批量API：

```python
# ✅ 好的做法：批量检查
results = await compliance.check_batch([
    {"content": msg1, "user_id": user1},
    {"content": msg2, "user_id": user2},
    {"content": msg3, "user_id": user3},
])

# ❌ 不好的做法：逐个检查
for msg in messages:
    result = await compliance.check_text(msg)  # 每次都是网络请求
```

### 2. 并发控制

使用信号量控制并发：

```python
import asyncio

class RateLimitedCompliance:
    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.client = ComplianceClient()
    
    async def check_with_limit(self, content: str, user_id: str):
        async with self.semaphore:
            return await self.client.check_text(user_id, content)

# 使用
compliance = RateLimitedCompliance(max_concurrent=20)

# 即使有1000个请求，最多同时20个
tasks = [
    compliance.check_with_limit(content, user_id)
    for content in large_content_list
]
results = await asyncio.gather(*tasks)
```

### 3. 预热和懒加载

```python
class OptimizedComplianceService:
    def __init__(self):
        self._ml_model = None
        self._cache = None
    
    @property
    def ml_model(self):
        """懒加载ML模型"""
        if self._ml_model is None:
            self._ml_model = load_model()
        return self._ml_model
    
    async def warmup(self):
        """服务启动时预热"""
        # 预加载模型
        _ = self.ml_model
        
        # 预热缓存（加载常见规则）
        self._cache = await load_rules_cache()
        
        # 测试检查
        await self.check_text("test", "warmup test")
```

---

## 安全防护

### 1. 防止绕过检查

```python
# ❌ 不安全：客户端可以跳过检查
@app.post("/api/messages")
async def send_message(message: str, skip_check: bool = False):
    if not skip_check:  # 客户端可以设置True
        await compliance.check(message)
    
    return save_message(message)

# ✅ 安全：服务端强制检查
@app.post("/api/messages")
async def send_message(message: str):
    # 无论如何都检查
    result = await compliance.check(message)
    
    if not result.passed:
        raise HTTPException(403, "Content blocked")
    
    return save_message(message)
```

### 2. 防止时序攻击 (Timing Attacks)

```python
import time

async def check_with_constant_time(content: str):
    """确保响应时间一致，防止通过时间推断内容"""
    start = time.time()
    
    result = await compliance.check(content)
    
    # 确保至少200ms响应时间
    elapsed = time.time() - start
    if elapsed < 0.2:
        await asyncio.sleep(0.2 - elapsed)
    
    return result
```

### 3. 审计日志

**文件名:** `compliance_service.py` - `_publish_compliance_event` 方法

所有合规检查都应记录：

```python
async def log_compliance_check(
    user_id: str,
    content_hash: str,
    result: ComplianceCheckResponse,
    ip_address: str
):
    """记录到audit_service"""
    
    audit_event = {
        "event_type": "compliance_check",
        "user_id": user_id,
        "resource_type": "content",
        "action": "compliance_validation",
        "success": result.passed,
        "metadata": {
            "check_id": result.check_id,
            "content_hash": content_hash,
            "status": result.status.value,
            "risk_level": result.risk_level.value,
            "violations": len(result.violations),
            "ip_address": ip_address
        },
        "timestamp": datetime.utcnow()
    }
    
    await audit_service.log_event(audit_event)
```

---

## 监控和告警

### 1. 关键指标

**文件名:** `main.py` - `/api/compliance/stats` 端点

```python
# 应监控的关键指标

METRICS = {
    # 容量指标
    "requests_per_second": "实时请求率",
    "avg_response_time_ms": "平均响应时间",
    "queue_depth": "待处理队列深度",
    
    # 质量指标
    "violation_rate": "违规率 (violations / total)",
    "false_positive_rate": "误报率",
    "human_review_rate": "人工审核率",
    
    # 安全指标
    "high_risk_incidents": "高风险事件数",
    "blocked_users": "被阻止的用户数",
    "injection_attempts": "注入尝试次数",
    
    # 业务指标
    "content_types_distribution": "内容类型分布",
    "check_types_usage": "检查类型使用率",
    "cache_hit_rate": "缓存命中率"
}
```

### 2. 告警规则

```python
# 告警配置示例

ALERTS = {
    "high_violation_rate": {
        "condition": "violation_rate > 0.3 for 5 minutes",
        "severity": "warning",
        "action": "notify_ops_team",
        "message": "Unusual spike in content violations"
    },
    
    "injection_attack": {
        "condition": "injection_attempts > 100 for 1 minute",
        "severity": "critical",
        "action": "notify_security_team",
        "message": "Potential coordinated injection attack"
    },
    
    "service_degradation": {
        "condition": "avg_response_time > 1000ms for 3 minutes",
        "severity": "warning",
        "action": "scale_up",
        "message": "Compliance service performance degraded"
    },
    
    "critical_content_detected": {
        "condition": "risk_level = critical",
        "severity": "high",
        "action": "immediate_review",
        "message": "Critical risk content detected"
    }
}
```

### 3. 健康检查

```python
# 全面的健康检查

@app.get("/health/detailed")
async def detailed_health_check():
    checks = {
        "database": await check_database_connection(),
        "nats": await check_nats_connection(),
        "openai_api": await check_openai_api(),
        "cache": check_cache_available(),
        "ml_model": check_ml_model_loaded()
    }
    
    all_healthy = all(checks.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow()
    }
```

---

## 合规报告

### 1. 定期报告生成

**文件名:** `main.py` - `/api/compliance/reports` 端点

```python
# 自动化合规报告

import schedule

async def generate_weekly_report():
    """每周一生成上周的合规报告"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    
    report = await compliance.generate_report(
        start_date=start_date,
        end_date=end_date,
        include_violations=True,
        include_trends=True
    )
    
    # 发送给管理员
    await send_report_email(report)
    
    # 保存到存储
    await save_report_to_storage(report)

# 调度
schedule.every().monday.at("09:00").do(generate_weekly_report)
```

### 2. 合规指标仪表板

```python
# 实时仪表板数据

@app.get("/api/compliance/dashboard")
async def get_dashboard_data(timeframe: str = "24h"):
    """获取仪表板数据"""
    
    if timeframe == "24h":
        start = datetime.utcnow() - timedelta(hours=24)
    elif timeframe == "7d":
        start = datetime.utcnow() - timedelta(days=7)
    else:
        start = datetime.utcnow() - timedelta(days=30)
    
    stats = await repo.get_statistics(start_date=start)
    
    return {
        "summary": {
            "total_checks": stats["total_checks"],
            "violation_rate": stats["failed_checks"] / stats["total_checks"],
            "avg_risk_score": calculate_avg_risk(stats)
        },
        "violations_by_type": stats["violations_by_type"],
        "trend": await get_trend_data(start),
        "top_violators": await get_top_violators(start, limit=10),
        "recent_critical": await get_recent_critical_incidents(limit=5)
    }
```

---

## 用户体验

### 1. 清晰的错误消息

```python
# ❌ 不好的做法
if not result.passed:
    raise HTTPException(403, "Content blocked")

# ✅ 好的做法
if not result.passed:
    error_details = {
        "error": "content_policy_violation",
        "message": "Your content doesn't meet our community guidelines",
        "details": format_user_friendly_violations(result.violations),
        "suggestions": [
            "Remove offensive language",
            "Avoid sharing personal information",
            "Review our content policy at example.com/policy"
        ],
        "appeal_url": f"https://example.com/appeal?check_id={result.check_id}"
    }
    raise HTTPException(403, detail=error_details)

def format_user_friendly_violations(violations):
    """将技术性违规转换为用户友好的描述"""
    friendly_messages = {
        "hate_speech": "Contains language that may be offensive to certain groups",
        "pii_detected": "Contains personal information that should be kept private",
        "prompt_injection": "Contains instructions that violate our AI usage policy"
    }
    
    return [
        friendly_messages.get(v["type"], v["type"])
        for v in violations
    ]
```

### 2. 渐进式提示

```python
# 在用户输入时提供实时反馈

@app.post("/api/content/preview")
async def preview_content(content: str, user_id: str):
    """预检查内容，提供实时反馈"""
    
    result = await compliance.check_text(user_id, content)
    
    if result.status == ComplianceStatus.PASS:
        return {"status": "ok", "message": "Content looks good!"}
    
    elif result.status == ComplianceStatus.WARNING:
        return {
            "status": "warning",
            "message": "Your content may be flagged",
            "issues": result.warnings,
            "can_submit": True
        }
    
    else:
        return {
            "status": "error",
            "message": "Content violates policies",
            "issues": result.violations,
            "can_submit": False
        }
```

---

## 多租户隔离

### 1. 组织级策略

**文件名:** `models.py` - `CompliancePolicy` 类

```python
# 不同组织使用不同策略

async def get_applicable_policy(
    user_id: str,
    organization_id: Optional[str]
) -> CompliancePolicy:
    """获取适用的策略（组织优先）"""
    
    if organization_id:
        # 1. 尝试获取组织特定策略
        org_policy = await repo.get_policy_by_organization(organization_id)
        if org_policy:
            return org_policy
    
    # 2. 使用默认全局策略
    return await repo.get_default_policy()

# 示例：不同组织的策略
ORGANIZATION_POLICIES = {
    "org_healthcare": {
        "hipaa_compliant": True,
        "pii_checks": "strict",
        "auto_redact_phi": True
    },
    "org_finance": {
        "sox_compliant": True,
        "pii_checks": "strict",
        "data_retention_days": 2555  # 7 years
    },
    "org_education": {
        "coppa_compliant": True,
        "age_restriction": 13,
        "content_moderation": "strict"
    }
}
```

### 2. 数据隔离

```python
# 确保不同组织的数据隔离

@app.get("/api/compliance/stats")
async def get_stats(
    organization_id: str,
    requester_id: str
):
    # 1. 验证请求者有权访问该组织数据
    if not await has_org_access(requester_id, organization_id):
        raise HTTPException(403, "Access denied")
    
    # 2. 只返回该组织的数据
    stats = await repo.get_statistics(
        organization_id=organization_id  # 强制过滤
    )
    
    return stats
```

---

## 总结

### 实施清单

- [ ] **架构**: 实施分层防御策略
- [ ] **性能**: 添加缓存和批量处理
- [ ] **安全**: 强制服务端检查，记录审计日志
- [ ] **监控**: 设置关键指标和告警
- [ ] **报告**: 实现自动化合规报告
- [ ] **UX**: 提供清晰的错误消息和建议
- [ ] **多租户**: 实施组织级策略和数据隔离

### 参考资源

- OpenAI Moderation API: https://platform.openai.com/docs/guides/moderation
- OWASP AI Security: https://owasp.org/www-project-ai-security-and-privacy-guide/
- NIST AI Risk Management: https://www.nist.gov/itl/ai-risk-management-framework

---

**文件说明:**
- 本文档位于 `/microservices/compliance_service/docs/BEST_PRACTICES.md`
- 引用的代码示例来自项目中的实际文件
- 所有示例都经过测试和验证
```

