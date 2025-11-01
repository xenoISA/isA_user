# Event Service 部署指南

## 概述

本指南基于真实测试的Event Service，提供生产环境部署的完整流程和最佳实践。

## 环境要求

### 系统要求

```bash
# 最小配置
CPU: 2 cores
Memory: 4GB RAM
Storage: 50GB SSD
Network: 1Gbps

# 推荐配置（生产环境）
CPU: 4 cores
Memory: 8GB RAM  
Storage: 200GB SSD
Network: 10Gbps
```

### 软件依赖

```bash
# 运行时
Python 3.11+
PostgreSQL 15+
NATS Server 2.10+

# 工具
Docker 24+
Kubernetes 1.28+ (可选)
Redis 7+ (缓存)
```

## 本地开发环境

### 1. 使用Docker Compose

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # NATS Server with JetStream
  nats:
    image: nats:2.10-alpine
    ports:
      - "4222:4222"
      - "8222:8222"  # HTTP monitoring
    command: [
      "-js",                    # Enable JetStream
      "-m", "8222",            # Monitoring port
      "--user", "isa_user_service",
      "--pass", "service123"
    ]
    volumes:
      - nats_data:/data
    healthcheck:
      test: ["CMD", "nats", "server", "check", "jetstream"]
      interval: 10s
      timeout: 5s
      retries: 3

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: postgres
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_INITDB_ARGS: "--auth-host=scram-sha-256"
    ports:
      - "54322:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Redis (缓存)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Event Service
  event-service:
    build: .
    ports:
      - "8230:8230"
    environment:
      # NATS配置
      NATS_URL: nats://nats:4222
      NATS_USERNAME: isa_user_service
      NATS_PASSWORD: service123
      
      # 数据库配置
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/postgres
      DB_SCHEMA: dev
      
      # 服务配置
      EVENT_SERVICE_HOST: 0.0.0.0
      EVENT_SERVICE_PORT: 8230
      
      # 日志配置
      LOG_LEVEL: INFO
      
    depends_on:
      nats:
        condition: service_healthy
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8230/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

volumes:
  nats_data:
  postgres_data:
  redis_data:

networks:
  default:
    name: isa_cloud_network
```

### 2. Dockerfile

```dockerfile
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8230/health || exit 1

# 启动命令
CMD ["python", "-m", "microservices.event_service.main"]
```

### 3. 启动开发环境

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f event-service

# 测试服务
curl http://localhost:8230/health
```

## 生产环境部署

### 1. Kubernetes部署

#### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: event-service-config
  namespace: isa-cloud
data:
  NATS_URL: "nats://nats-cluster:4222"
  DATABASE_URL: "postgresql://postgres:password@postgres-cluster:5432/isa_cloud"
  DB_SCHEMA: "production"
  EVENT_SERVICE_HOST: "0.0.0.0"
  EVENT_SERVICE_PORT: "8230"
  LOG_LEVEL: "INFO"
  EVENT_BATCH_SIZE: "100"
  EVENT_PROCESSING_INTERVAL: "5"
```

#### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: event-service-secrets
  namespace: isa-cloud
type: Opaque
stringData:
  NATS_USERNAME: "isa_user_service"
  NATS_PASSWORD: "production_password_123"
  DATABASE_PASSWORD: "production_db_password"
```

#### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: event-service
  namespace: isa-cloud
  labels:
    app: event-service
    version: v1.0.0
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: event-service
  template:
    metadata:
      labels:
        app: event-service
        version: v1.0.0
    spec:
      serviceAccountName: event-service
      containers:
      - name: event-service
        image: isa-cloud/event-service:v1.0.0
        ports:
        - containerPort: 8230
          protocol: TCP
        envFrom:
        - configMapRef:
            name: event-service-config
        - secretRef:
            name: event-service-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8230
          initialDelaySeconds: 30
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8230
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: tmp
        emptyDir: {}
      - name: logs
        emptyDir: {}
      restartPolicy: Always
```

#### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: event-service
  namespace: isa-cloud
  labels:
    app: event-service
spec:
  selector:
    app: event-service
  ports:
  - name: http
    port: 8230
    targetPort: 8230
    protocol: TCP
  type: ClusterIP
```

#### HorizontalPodAutoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: event-service-hpa
  namespace: isa-cloud
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: event-service
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

### 2. 使用Helm Chart

#### Chart.yaml

```yaml
apiVersion: v2
name: event-service
description: Event Service Helm Chart for isA Cloud
type: application
version: 1.0.0
appVersion: "1.0.0"
keywords:
  - event-sourcing
  - microservices
  - nats
home: https://github.com/your-org/isa-cloud
sources:
  - https://github.com/your-org/isa-cloud
maintainers:
  - name: isA Cloud Team
    email: team@isa-cloud.com
```

#### values.yaml

```yaml
replicaCount: 3

image:
  repository: isa-cloud/event-service
  tag: "v1.0.0"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 8230

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
  hosts:
    - host: events.isa-cloud.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: event-service-tls
      hosts:
        - events.isa-cloud.com

resources:
  limits:
    cpu: 500m
    memory: 1Gi
  requests:
    cpu: 250m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

config:
  natsUrl: "nats://nats-cluster:4222"
  databaseUrl: "postgresql://postgres:password@postgres-cluster:5432/isa_cloud"
  logLevel: "INFO"
  batchSize: 100
  processingInterval: 5

secrets:
  natsUsername: "isa_user_service"
  natsPassword: "production_password_123"
  databasePassword: "production_db_password"

nodeSelector: {}
tolerations: []
affinity: {}

serviceMonitor:
  enabled: true
  namespace: monitoring
  interval: 30s
  path: /metrics
```

#### 部署命令

```bash
# 添加Helm仓库
helm repo add isa-cloud https://charts.isa-cloud.com
helm repo update

# 安装Event Service
helm install event-service isa-cloud/event-service \
  --namespace isa-cloud \
  --create-namespace \
  --values production-values.yaml

# 升级
helm upgrade event-service isa-cloud/event-service \
  --namespace isa-cloud \
  --values production-values.yaml

# 查看状态
helm status event-service -n isa-cloud
```

## 监控和日志

### 1. Prometheus监控

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response

# 指标定义
events_total = Counter('events_total', 'Total events processed', ['event_type', 'source'])
event_processing_time = Histogram('event_processing_seconds', 'Event processing time')
active_connections = Gauge('active_connections', 'Active connections count')

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        generate_latest(),
        media_type="text/plain"
    )

# 在事件处理中使用
@event_processing_time.time()
async def process_event(event):
    events_total.labels(
        event_type=event.event_type,
        source=event.event_source
    ).inc()
    # 处理逻辑...
```

### 2. 日志配置

```python
# logging_config.py
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    """配置结构化日志"""
    
    # JSON格式化器
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # 文件处理器
    file_handler = logging.FileHandler('/app/logs/event-service.log')
    file_handler.setFormatter(formatter)
    
    # 根日志器配置
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # 禁用第三方库的详细日志
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('nats').setLevel(logging.WARNING)
```

### 3. 告警规则

```yaml
# prometheus-rules.yaml
groups:
- name: event-service
  rules:
  - alert: EventServiceDown
    expr: up{job="event-service"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Event Service is down"
      description: "Event Service has been down for more than 5 minutes"

  - alert: HighEventProcessingLatency
    expr: histogram_quantile(0.95, event_processing_seconds_bucket) > 1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High event processing latency"
      description: "95th percentile latency is {{ $value }}s"

  - alert: HighErrorRate
    expr: rate(events_total{status="error"}[5m]) / rate(events_total[5m]) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate in event processing"
      description: "Error rate is {{ $value | humanizePercentage }}"
```

## 备份和恢复

### 1. 数据备份策略

```bash
#!/bin/bash
# backup.sh - 自动备份脚本

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/event-service"
mkdir -p $BACKUP_DIR

# PostgreSQL备份
pg_dump $DATABASE_URL | gzip > $BACKUP_DIR/events_${DATE}.sql.gz

# NATS JetStream备份
nats stream backup EVENTS $BACKUP_DIR/nats_${DATE}.tar

# 清理旧备份（保留30天）
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar" -mtime +30 -delete

echo "Backup completed: $DATE"
```

### 2. 恢复流程

```bash
#!/bin/bash
# restore.sh - 数据恢复脚本

BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# 停止Event Service
kubectl scale deployment event-service --replicas=0 -n isa-cloud

# 恢复数据库
gunzip -c $BACKUP_FILE | psql $DATABASE_URL

# 恢复NATS（如果有备份）
# nats stream restore EVENTS /path/to/nats_backup.tar

# 重启服务
kubectl scale deployment event-service --replicas=3 -n isa-cloud

echo "Restore completed"
```

## 性能调优

### 1. 数据库优化

```sql
-- 索引优化
CREATE INDEX CONCURRENTLY idx_events_user_time 
ON events(user_id, created_at) 
WHERE created_at > NOW() - INTERVAL '30 days';

CREATE INDEX CONCURRENTLY idx_events_type_status 
ON events(event_type, status) 
WHERE status IN ('pending', 'processing');

-- 分区表设置
CREATE TABLE events_y2025m01 PARTITION OF events
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- 自动清理旧数据
DELETE FROM events 
WHERE created_at < NOW() - INTERVAL '1 year'
AND event_type NOT IN ('purchase_completed', 'user_registered');
```

### 2. 应用配置优化

```python
# 生产环境配置
class ProductionConfig:
    # 数据库连接池
    DB_POOL_SIZE = 20
    DB_MAX_OVERFLOW = 30
    DB_POOL_RECYCLE = 3600
    
    # NATS配置
    NATS_MAX_RECONNECT_ATTEMPTS = 10
    NATS_RECONNECT_TIME_WAIT = 2
    
    # 事件处理
    EVENT_BATCH_SIZE = 100
    EVENT_PROCESSING_INTERVAL = 5
    MAX_CONCURRENT_PROCESSORS = 10
    
    # 缓存配置
    REDIS_URL = "redis://redis-cluster:6379/0"
    CACHE_TTL = 3600
```

### 3. 资源限制

```yaml
# 生产环境资源配置
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"

# JVM设置（如果使用Java客户端）
env:
- name: JAVA_OPTS
  value: "-Xmx1g -Xms1g -XX:+UseG1GC"
```

## 安全配置

### 1. 网络安全

```yaml
# NetworkPolicy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: event-service-netpol
  namespace: isa-cloud
spec:
  podSelector:
    matchLabels:
      app: event-service
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: isa-cloud
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8230
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: isa-cloud
  - to: []
    ports:
    - protocol: TCP
      port: 5432  # PostgreSQL
    - protocol: TCP
      port: 4222  # NATS
```

### 2. RBAC配置

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: event-service
  namespace: isa-cloud
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: isa-cloud
  name: event-service-role
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: event-service-rolebinding
  namespace: isa-cloud
subjects:
- kind: ServiceAccount
  name: event-service
  namespace: isa-cloud
roleRef:
  kind: Role
  name: event-service-role
  apiGroup: rbac.authorization.k8s.io
```

## 故障排查

### 1. 常见问题

#### NATS连接问题
```bash
# 检查NATS服务状态
kubectl logs -l app=nats -n isa-cloud

# 测试NATS连接
nats pub test.subject "hello world" --server=nats://nats-cluster:4222

# 检查JetStream状态
nats stream ls --server=nats://nats-cluster:4222
```

#### 数据库连接问题
```bash
# 检查PostgreSQL状态
kubectl logs -l app=postgres -n isa-cloud

# 测试数据库连接
psql $DATABASE_URL -c "SELECT 1;"

# 检查连接数
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"
```

#### 内存泄漏调试
```bash
# 检查内存使用
kubectl top pods -l app=event-service -n isa-cloud

# 获取详细指标
kubectl exec -it deployment/event-service -n isa-cloud -- \
  curl localhost:8230/metrics | grep memory
```

### 2. 调试工具

```bash
# 进入Pod调试
kubectl exec -it deployment/event-service -n isa-cloud -- /bin/bash

# 查看实时日志
kubectl logs -f deployment/event-service -n isa-cloud

# 端口转发用于本地调试
kubectl port-forward deployment/event-service 8230:8230 -n isa-cloud
```

这个部署指南基于我们成功测试的Event Service，涵盖了从开发环境到生产环境的完整部署流程。