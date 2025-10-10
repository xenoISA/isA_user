# 统一日志系统使用指南

## 概述

新的统一日志系统提供了结构化日志、智能分析和自动监控功能，帮助更好地管理和分析微服务日志。

## 1. 基础使用

### 在服务中启用统一日志

```python
# 在服务主文件中添加
from core.logging_config import setup_service_logging

# 初始化日志
logger, log_context = setup_service_logging("your_service_name", level="INFO")

# 基础日志记录
logger.info("Service started successfully")
logger.error("Database connection failed", extra={"db_host": "localhost"})

# 带上下文的日志
log_context.set_context(user_id="user123", request_id="req456")
log_context.info("Processing user request")
log_context.error("Validation failed", validation_error="missing_field")
```

### 日志输出格式

系统会自动生成三种日志文件：
- `logs/service_name/service_name.log` - 人类可读格式
- `logs/service_name/service_name.json` - 结构化JSON格式  
- `logs/service_name/service_name_error.log` - 错误专用日志

## 2. 日志管理命令

### 分析日志

```bash
# 分析最近24小时日志
python scripts/log_manager.py analyze --hours 24

# 分析最近1小时日志
python scripts/log_manager.py analyze --hours 1
```

输出示例：
```
=== Log Analysis Report ===
Total logs: 20202
Error count: 6
Warning count: 0
Error rate: 0.03%

Services: event, auth, storage, notification...

=== Service Log Distribution ===
notification: 2873 logs
auth: 1615 logs
storage: 1396 logs

=== Top Errors ===
1. Database connection timeout (count: 3)
2. Invalid API key (count: 2)
```

### 监控告警

```bash
# 检查系统告警
python scripts/log_manager.py monitor
```

自动检测：
- 高错误率（>5%）
- 服务静默（>10分钟无日志）
- 异常模式

### 搜索日志

```bash
# 搜索所有包含"error"的日志
python scripts/log_manager.py search "error" --hours 24

# 搜索特定服务的错误日志
python scripts/log_manager.py search "database" --service auth --level ERROR

# 限制搜索结果
python scripts/log_manager.py search "timeout" --limit 10
```

### 导出日志

```bash
# 导出为JSON格式
python scripts/log_manager.py export logs_export.json --format json --hours 24

# 导出为CSV格式
python scripts/log_manager.py export logs_export.csv --format csv --hours 12
```

## 3. 日志维护

### 清理旧日志

```bash
# 清理7天前的日志文件
python scripts/log_manager.py cleanup --days 7

# 清理30天前的日志文件  
python scripts/log_manager.py cleanup --days 30
```

### 压缩日志

```bash
# 压缩1天前的日志文件
python scripts/log_manager.py compress --days 1

# 压缩3天前的日志文件
python scripts/log_manager.py compress --days 3
```

## 4. 高级功能

### 编程方式使用日志聚合器

```python
from core.log_aggregator import LogAggregator, get_log_summary

# 获取日志摘要
summary = await get_log_summary("logs", hours=24)
print(f"总日志数: {summary['total_logs']}")
print(f"错误率: {summary['error_rate']:.2f}%")

# 创建聚合器实例
aggregator = LogAggregator("logs")

# 搜索特定日志
results = await aggregator.search_logs("database error", service="auth", hours=1)
for log in results:
    print(f"{log.timestamp}: {log.message}")

# 获取服务健康状态
health = await aggregator.get_service_health("auth_service")
print(f"服务状态: {health.status}")
print(f"1小时错误数: {health.error_count_1h}")
```

### 自定义日志格式

```python
from core.logging_config import UnifiedLoggingConfig, LogLevel

# 自定义配置
config = UnifiedLoggingConfig("my_service", log_dir="custom_logs")
logger = config.setup_logging(
    level=LogLevel.DEBUG,
    enable_console=True,
    enable_file=True,
    enable_json=True,
    enable_rotation=True,
    max_bytes=20*1024*1024,  # 20MB
    backup_count=10
)
```

## 5. 监控和告警

### 设置定时监控

```bash
# 添加到crontab，每5分钟检查一次
*/5 * * * * cd /path/to/project && python scripts/log_manager.py monitor >> logs/monitoring.log 2>&1

# 每天凌晨2点清理旧日志
0 2 * * * cd /path/to/project && python scripts/log_manager.py cleanup --days 7

# 每天凌晨3点压缩日志
0 3 * * * cd /path/to/project && python scripts/log_manager.py compress --days 1
```

### 集成到现有监控系统

```python
from core.log_aggregator import LogMonitor

async def check_system_health():
    aggregator = LogAggregator("logs")
    monitor = LogMonitor(aggregator)
    
    alerts = await monitor.check_alerts()
    if alerts:
        # 发送告警到Slack/邮件/短信
        for alert in alerts:
            send_alert(alert)
```

## 6. 最佳实践

### 日志级别使用

- **DEBUG**: 详细调试信息，仅开发环境
- **INFO**: 正常业务流程记录
- **WARNING**: 警告信息，需要关注但不影响功能
- **ERROR**: 错误信息，影响功能但服务可继续
- **CRITICAL**: 严重错误，服务无法继续

### 结构化日志字段

```python
# 推荐的日志字段
logger.info("User login successful", extra={
    "user_id": "user123",
    "ip_address": "192.168.1.100", 
    "user_agent": "Mozilla/5.0...",
    "session_id": "sess456",
    "duration_ms": 150
})

# API调用日志
logger.info("API call completed", extra={
    "method": "POST",
    "endpoint": "/api/v1/users",
    "status_code": 200,
    "response_time_ms": 50,
    "request_id": "req789"
})
```

### 错误日志记录

```python
try:
    result = risky_operation()
except Exception as e:
    logger.error("Operation failed", extra={
        "operation": "risky_operation",
        "error_type": type(e).__name__,
        "error_message": str(e),
        "traceback": traceback.format_exc(),
        "context": {"param1": "value1"}
    })
```

## 7. 故障排查

### 常见问题

1. **日志文件过大**
   ```bash
   # 检查文件大小
   du -sh logs/
   
   # 启用日志轮转
   python scripts/log_manager.py compress --days 1
   ```

2. **找不到特定错误**
   ```bash
   # 精确搜索
   python scripts/log_manager.py search "exact error message" --hours 24
   
   # 按服务搜索
   python scripts/log_manager.py search "error" --service problem_service
   ```

3. **服务日志缺失**
   ```bash
   # 检查服务状态
   python scripts/log_manager.py monitor
   
   # 检查最近日志
   python scripts/log_manager.py analyze --hours 1
   ```

## 8. 性能考虑

- JSON日志会增加约20%的存储空间，但提供更好的查询能力
- 日志轮转避免单文件过大影响性能
- 异步日志记录不会阻塞业务逻辑
- 缓存机制减少重复分析的开销

## 支持

如有问题，请查看：
- 日志配置: `core/logging_config.py`
- 分析工具: `core/log_aggregator.py`  
- 管理脚本: `scripts/log_manager.py`