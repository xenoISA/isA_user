# Notification Service Design

## Overview

Notification Service is a high-performance, multi-channel notification delivery system designed to handle email, SMS, push, and in-app notifications at scale. The service provides template management, batch processing, real-time delivery, and comprehensive analytics.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   Mobile App    │    │  Other Services │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │     API Gateway (8208)     │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │   Notification Service      │
                    │   (FastAPI + PostgreSQL)  │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │         NATS              │
                    │    (Event Bus)           │
                    └─────────────┬─────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                      │                      │
┌───────┴───────┐    ┌───────┴───────┐    ┌───────┴───────┐
│  Email Provider│    │  Push Services│    │   PostgreSQL   │
│   (Resend)    │    │ (APNs/FCM)   │    │  (Primary DB)  │
└───────────────┘    └───────────────┘    └───────────────┘
```

### Core Components

#### 1. API Layer (FastAPI)
- **Notification Router**: `/api/v1/notifications/*`
- **Template Router**: `/api/v1/notifications/templates/*`
- **Push Router**: `/api/v1/notifications/push/*`
- **Stats Router**: `/api/v1/notifications/stats/*`
- **Health Router**: `/health/*`

#### 2. Service Layer
- **NotificationService**: Core notification processing logic
- **TemplateService**: Template management and rendering
- **BatchService**: Batch notification processing
- **PushService**: Push notification handling
- **InAppService**: In-app notification management
- **SubscriptionService**: Push subscription management
- **StatsService**: Analytics and statistics

#### 3. Repository Layer
- **NotificationRepository**: Database operations for notifications
- **TemplateRepository**: Template CRUD operations
- **BatchRepository**: Batch processing operations
- **PushSubscriptionRepository**: Push subscription management
- **InAppNotificationRepository**: In-app notification operations

#### 4. External Integrations
- **EmailProvider**: Resend API integration
- **PushProviders**: APNs (iOS) and FCM (Android) integrations
- **WebhookProvider**: Generic webhook delivery

## Database Schema

### Schema: notification

#### 1. notification_templates
```sql
CREATE TABLE notification.notification_templates (
    id SERIAL PRIMARY KEY,
    template_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL, -- email, sms, push, in_app, webhook
    subject VARCHAR(255),
    content TEXT NOT NULL,
    html_content TEXT,
    variables JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(50) DEFAULT 'draft', -- draft, active, archived
    version INTEGER DEFAULT 1,
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 2. notifications
```sql
CREATE TABLE notification.notifications (
    id SERIAL PRIMARY KEY,
    notification_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255),
    template_id VARCHAR(255),
    type VARCHAR(50) NOT NULL, -- email, sms, push, in_app, webhook
    channel VARCHAR(50), -- primary, secondary, all
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(255),
    content TEXT NOT NULL,
    html_content TEXT,
    priority VARCHAR(20) DEFAULT 'normal', -- low, normal, high, urgent
    status VARCHAR(50) DEFAULT 'pending', -- pending, sending, sent, delivered, failed, bounced
    variables JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    scheduled_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    batch_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 3. in_app_notifications
```sql
CREATE TABLE notification.in_app_notifications (
    id SERIAL PRIMARY KEY,
    notification_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) DEFAULT 'info', -- info, success, warning, error, system
    category VARCHAR(100),
    priority VARCHAR(20) DEFAULT 'normal', -- low, normal, high, urgent
    action_type VARCHAR(50), -- link, button, dismiss
    action_url TEXT,
    action_data JSONB DEFAULT '{}'::jsonb,
    icon VARCHAR(255),
    avatar_url TEXT,
    is_read BOOLEAN DEFAULT false,
    is_archived BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 4. notification_batches
```sql
CREATE TABLE notification.notification_batches (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    description TEXT,
    template_id VARCHAR(255),
    type VARCHAR(50) NOT NULL, -- email, sms, push, in_app
    total_count INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    delivered_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed, cancelled
    scheduled_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 5. push_subscriptions
```sql
CREATE TABLE notification.push_subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL, -- ios, android, web
    device_token TEXT NOT NULL,
    device_id VARCHAR(255),
    device_name VARCHAR(255),
    app_version VARCHAR(50),
    os_version VARCHAR(50),
    endpoint TEXT, -- For web push
    p256dh TEXT, -- For web push encryption
    auth TEXT, -- For web push auth
    topics TEXT[], -- Subscription topics/categories
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, device_token, platform)
);
```

## API Design

### Core Endpoints

#### 1. Send Notification
```http
POST /api/v1/notifications/send
Content-Type: application/json

{
  "type": "email",
  "recipient_email": "user@example.com",
  "template_id": "tpl_welcome_123",
  "variables": {"name": "John"},
  "priority": "normal"
}
```

#### 2. Send Batch
```http
POST /api/v1/notifications/batch
Content-Type: application/json

{
  "name": "Welcome Campaign",
  "template_id": "tpl_welcome_123",
  "type": "email",
  "recipients": [
    {"user_id": "user_123", "variables": {"name": "John"}},
    {"email": "jane@example.com", "variables": {"name": "Jane"}}
  ]
}
```

#### 3. Create Template
```http
POST /api/v1/notifications/templates
Content-Type: application/json

{
  "name": "Welcome Email Template",
  "type": "email",
  "subject": "Welcome {{name}}!",
  "content": "Hello {{name}}, welcome aboard!",
  "variables": ["name"]
}
```

#### 4. List In-App Notifications
```http
GET /api/v1/notifications/in-app/{user_id}?is_read=false&limit=20
```

#### 5. Register Push Subscription
```http
POST /api/v1/notifications/push/subscribe
Content-Type: application/json

{
  "user_id": "user_123",
  "device_token": "token_here",
  "platform": "ios",
  "device_name": "iPhone 14"
}
```

### Response Format

All API responses follow consistent format:

```json
{
  "success": true,
  "data": { /* Response data */ },
  "message": "Operation completed successfully",
  "timestamp": "2025-12-15T14:30:00Z"
}
```

Error responses:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "details": {...}
  },
  "timestamp": "2025-12-15T14:30:00Z"
}
```

## Service Implementation

### 1. NotificationService

#### Core Methods
```python
class NotificationService:
    async def send_notification(self, request: SendNotificationRequest) -> NotificationResponse
    async def send_batch(self, request: SendBatchRequest) -> BatchResponse
    async def process_notification(self, notification_id: str) -> bool
    async def retry_failed_notification(self, notification_id: str) -> bool
    async def schedule_notification(self, notification_id: str, scheduled_at: datetime) -> bool
```

#### Processing Pipeline
1. **Validation**: Request validation and template existence
2. **Variable Replacement**: Template variable substitution
3. **Recipient Resolution**: Email/phone/user ID validation
4. **Channel Selection**: Email/SMS/Push/In-app routing
5. **Provider Integration**: External provider API calls
6. **Status Tracking**: Real-time status updates
7. **Event Publishing**: NATS event emission

### 2. TemplateService

#### Core Methods
```python
class TemplateService:
    async def create_template(self, request: CreateTemplateRequest) -> TemplateResponse
    async def update_template(self, template_id: str, request: UpdateTemplateRequest) -> TemplateResponse
    async def render_template(self, template_id: str, variables: dict) -> RenderedContent
    async def extract_variables(self, content: str) -> List[str]
    async def validate_template(self, template: Template) -> ValidationResult
```

#### Variable Replacement Engine
- **Pattern Matching**: `{{variable_name}}` regex extraction
- **Validation**: Variable name format validation
- **Replacement**: Case-sensitive string replacement
- **Fallback**: Empty string for missing variables
- **HTML Handling**: Separate processing for HTML content

### 3. PushService

#### Platform-Specific Handling
```python
class PushService:
    async def send_push(self, notification: PushNotification) -> PushResult
    async def register_subscription(self, subscription: PushSubscription) -> SubscriptionResponse
    async def handle_apns(self, devices: List[iOSDevice], payload: dict) -> List[PushResult]
    async def handle_fcm(self, devices: List[AndroidDevice], payload: dict) -> List[PushResult]
    async def handle_web_push(self, subscriptions: List[WebSubscription], payload: dict) -> List[PushResult]
```

#### Push Payload Structure
```json
{
  "title": "Notification Title",
  "body": "Notification message",
  "data": {"key": "value"},
  "sound": "default",
  "badge": 1,
  "priority": "high",
  "ttl": 3600
}
```

## External Integrations

### 1. Email Provider (Resend)

#### Configuration
```python
EMAIL_CONFIG = {
    "api_key": os.getenv("RESEND_API_KEY"),
    "from_email": "notifications@example.com",
    "from_name": "Example Platform",
    "reply_to": "support@example.com",
    "rate_limit": 100,  # emails per second
    "retry_attempts": 3,
    "timeout": 30
}
```

#### API Integration
```python
class ResendEmailProvider:
    async def send_email(self, email_request: EmailRequest) -> EmailResponse
    async def get_delivery_status(self, message_id: str) -> DeliveryStatus
    async def handle_webhook(self, webhook_data: dict) -> WebhookEvent
```

### 2. Push Services

#### APNs (Apple Push Notification Service)
```python
class APNsProvider:
    def __init__(self, key_id: str, team_id: str, private_key: str):
        self.client = APNsClient(key_id, team_id, private_key)
    
    async def send_notification(self, device_token: str, payload: dict) -> APNsResponse
    async def validate_device_token(self, device_token: str) -> bool
```

#### FCM (Firebase Cloud Messaging)
```python
class FCMProvider:
    def __init__(self, server_key: str):
        self.client = FCMClient(server_key)
    
    async def send_notification(self, registration_token: str, payload: dict) -> FCMResponse
    async def batch_send(self, tokens: List[str], payload: dict) -> List[FCMResponse]
```

## Event System

### NATS Events

#### 1. Notification Events
```python
# notification.sent
{
  "event_type": "NOTIFICATION_SENT",
  "source": "notification_service",
  "timestamp": "2025-12-15T14:30:00Z",
  "data": {
    "notification_id": "ntf_email_123",
    "type": "email",
    "recipient": "user@example.com",
    "status": "sent"
  }
}

# notification.delivered
{
  "event_type": "NOTIFICATION_DELIVERED",
  "source": "notification_service",
  "timestamp": "2025-12-15T14:30:00Z",
  "data": {
    "notification_id": "ntf_push_123",
    "type": "push",
    "platform": "ios",
    "device_count": 2
  }
}

# notification.failed
{
  "event_type": "NOTIFICATION_FAILED",
  "source": "notification_service",
  "timestamp": "2025-12-15T14:30:00Z",
  "data": {
    "notification_id": "ntf_email_123",
    "type": "email",
    "error": "Invalid email address",
    "retry_count": 1
  }
}
```

#### 2. Template Events
```python
# notification.template_created
{
  "event_type": "NOTIFICATION_TEMPLATE_CREATED",
  "source": "notification_service",
  "timestamp": "2025-12-15T14:30:00Z",
  "data": {
    "template_id": "tpl_email_welcome",
    "name": "Welcome Email Template",
    "type": "email",
    "created_by": "admin_123"
  }
}

# notification.template_updated
{
  "event_type": "NOTIFICATION_TEMPLATE_UPDATED",
  "source": "notification_service",
  "timestamp": "2025-12-15T14:30:00Z",
  "data": {
    "template_id": "tpl_email_welcome",
    "version": 2,
    "changed_fields": ["content", "variables"]
  }
}
```

## Performance Optimization

### 1. Database Optimization

#### Indexes
```sql
-- Notifications
CREATE INDEX idx_notifications_user_id ON notification.notifications(user_id);
CREATE INDEX idx_notifications_status ON notification.notifications(status);
CREATE INDEX idx_notifications_type ON notification.notifications(type);
CREATE INDEX idx_notifications_created_at ON notification.notifications(created_at DESC);
CREATE INDEX idx_notifications_scheduled ON notification.notifications(scheduled_at) WHERE scheduled_at IS NOT NULL;

-- In-app notifications
CREATE INDEX idx_in_app_user_id ON notification.in_app_notifications(user_id);
CREATE INDEX idx_in_app_read ON notification.in_app_notifications(user_id, is_read) WHERE is_read = false;
CREATE INDEX idx_in_app_created_at ON notification.in_app_notifications(created_at DESC);

-- Push subscriptions
CREATE INDEX idx_push_user_id ON notification.push_subscriptions(user_id);
CREATE INDEX idx_push_active ON notification.push_subscriptions(is_active) WHERE is_active = true;
CREATE INDEX idx_push_platform ON notification.push_subscriptions(platform);
```

#### Connection Pooling
```python
DATABASE_CONFIG = {
    "pool_size": 20,
    "max_overflow": 30,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "pool_pre_ping": True
}
```

### 2. Caching Strategy

#### Redis Caching
```python
# Template caching
CACHE_KEYS = {
    "template": "notification:template:{template_id}",
    "template_variables": "notification:template:variables:{template_id}",
    "user_subscriptions": "notification:subscriptions:user:{user_id}",
    "notification_stats": "notification:stats:{period}:{user_id}"
}

CACHE_TTL = {
    "template": 3600,  # 1 hour
    "template_variables": 3600,
    "user_subscriptions": 1800,  # 30 minutes
    "notification_stats": 300  # 5 minutes
}
```

### 3. Queue Management

#### Background Tasks
```python
# Using Celery for async processing
@celery.task(bind=True, max_retries=3)
def process_notification_task(self, notification_id: str):
    try:
        notification_service.process_notification(notification_id)
    except Exception as exc:
        self.retry(countdown=60 * (2 ** self.request.retries))

@celery.task
def process_batch_task(batch_id: str):
    batch_service.process_batch_notifications(batch_id)
```

## Security

### 1. Authentication & Authorization

#### JWT Validation
```python
class NotificationAuthMiddleware:
    async def verify_token(self, token: str) -> TokenPayload
    async def check_permissions(self, user_id: str, resource: str, action: str) -> bool
```

#### Rate Limiting
```python
RATE_LIMITS = {
    "send_notification": "100/minute",
    "send_batch": "10/minute",
    "create_template": "20/minute",
    "list_notifications": "1000/minute"
}
```

### 2. Data Protection

#### PII Handling
- Email addresses encrypted at rest
- Phone numbers masked in logs
- User ID validation against auth service
- Data retention policies enforced

#### Input Validation
```python
class SecurityValidator:
    @staticmethod
    def validate_email(email: str) -> bool
    @staticmethod
    def validate_phone(phone: str) -> bool
    @staticmethod
    def sanitize_content(content: str) -> str
    @staticmethod
    def validate_template_variables(variables: dict) -> bool
```

## Monitoring & Observability

### 1. Metrics

#### Prometheus Metrics
```python
# Notification metrics
notifications_sent_total = Counter("notifications_sent_total", ["type", "status"])
notifications_duration = Histogram("notifications_duration_seconds", ["type"])
template_render_duration = Histogram("template_render_duration_seconds")

# Provider metrics
provider_requests_total = Counter("provider_requests_total", ["provider", "status"])
provider_response_time = Histogram("provider_response_time_seconds", ["provider"])
```

#### Health Checks
```python
class HealthChecker:
    async def check_database_health(self) -> HealthStatus
    async def check_email_provider_health(self) -> HealthStatus
    async def check_push_provider_health(self) -> HealthStatus
    async def check_nats_health(self) -> HealthStatus
```

### 2. Logging

#### Structured Logging
```python
LOGGER_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json"
        }
    },
    "loggers": {
        "notification_service": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False
        }
    }
}
```

## Deployment

### 1. Container Configuration

#### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8208

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8208"]
```

#### Health Check
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8208/health || exit 1
```

### 2. Kubernetes Configuration

#### Deployment Manifest
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: notification-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: notification-service
  template:
    metadata:
      labels:
        app: notification-service
    spec:
      containers:
      - name: notification-service
        image: notification-service:latest
        ports:
        - containerPort: 8208
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: notification-secrets
              key: database-url
        - name: RESEND_API_KEY
          valueFrom:
            secretKeyRef:
              name: notification-secrets
              key: resend-api-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8208
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8208
          initialDelaySeconds: 5
          periodSeconds: 5
```

### 3. Configuration Management

#### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/notification
DATABASE_POOL_SIZE=20

# Email Provider
RESEND_API_KEY=re_api_key_here
EMAIL_FROM_EMAIL=notifications@example.com
EMAIL_FROM_NAME=Example Platform

# Push Services
APNS_KEY_ID=apns_key_id
APNS_TEAM_ID=apns_team_id
APNS_PRIVATE_KEY_FILE=/path/to/private/key.p8
FCM_SERVER_KEY=fcm_server_key

# NATS
NATS_URL=nats://localhost:4222
NATS_SUBJECT_PREFIX=notification

# Redis
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# Security
JWT_SECRET_KEY=jwt_secret_key_here
RATE_LIMIT_ENABLED=true
```

## Testing Strategy

### 1. Unit Tests

#### Service Layer Tests
```python
class TestNotificationService:
    async def test_send_notification_success(self)
    async def test_send_notification_invalid_email(self)
    async def test_send_notification_template_not_found(self)
    async def test_send_batch_notification_success(self)
    async def test_send_batch_partial_failure(self)

class TestTemplateService:
    async def test_create_template_success(self)
    async def test_create_template_duplicate_name(self)
    async def test_render_template_with_variables(self)
    async def test_extract_template_variables(self)
```

### 2. Integration Tests

#### API Tests
```python
class TestNotificationAPI:
    async def test_send_notification_endpoint(self)
    async def test_send_batch_endpoint(self)
    async def test_create_template_endpoint(self)
    async def test_list_notifications_endpoint(self)
    async def test_register_push_subscription_endpoint(self)
```

#### Provider Tests
```python
class TestEmailProvider:
    async def test_send_email_success(self)
    async def test_send_email_invalid_recipient(self)
    async def test_handle_webhook_event(self)

class TestPushProviders:
    async def test_apns_send_notification(self)
    async def test_fcm_send_notification(self)
    async def test_web_push_notification(self)
```

### 3. Performance Tests

#### Load Testing
```python
# Using Locust for load testing
class NotificationLoadTest:
    def test_send_notification_load(self, users=100, spawn_rate=10)
    def test_batch_notification_load(self, batches=50, recipients_per_batch=1000)
    def test_template_rendering_load(self, requests=1000)
```

## Scaling Considerations

### 1. Horizontal Scaling

#### Stateless Design
- API layer is stateless
- Database connections managed via pool
- External provider clients are lightweight
- Session state stored in Redis

#### Load Balancing
```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: notification-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: notification-service
  minReplicas: 3
  maxReplicas: 20
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

### 2. Database Scaling

#### Read Replicas
```python
DATABASE_CONFIG = {
    "master": "postgresql://master/db",
    "replicas": [
        "postgresql://replica1/db",
        "postgresql://replica2/db"
    ],
    "read_write_split": True
}
```

#### Partitioning Strategy
```sql
-- Partition notifications by created_at
CREATE TABLE notification.notifications_2025_12 PARTITION OF notification.notifications
FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
```

## Disaster Recovery

### 1. Backup Strategy

#### Database Backups
```bash
# Daily full backups
pg_dump notification | gzip > backup_$(date +%Y%m%d).sql.gz

# Point-in-time recovery
pg_basebackup -h localhost -D /backup/base -U postgres -v -P
```

#### Configuration Backups
```bash
# Backup templates and configurations
kubectl get configmaps notification-config -o yaml > config_backup.yaml
kubectl get secrets notification-secrets -o yaml > secrets_backup.yaml
```

### 2. High Availability

#### Multi-Region Deployment
```yaml
# Service mesh configuration
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: notification-service
spec:
  http:
  - match:
    - uri:
        prefix: /api/v1/notifications
    route:
    - destination:
        host: notification-service-primary
      weight: 90
    - destination:
        host: notification-service-secondary
      weight: 10
```

---

**Version**: 1.0.0  
**Last Updated**: 2025-12-15  
**Author**: Notification Service Team
