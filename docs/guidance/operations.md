# Operations

Platform operations, monitoring, and compliance services.

## Overview

Operational capabilities are handled by five services:

| Service | Port | Purpose |
|---------|------|---------|
| audit_service | 8205 | Event logging, security tracking |
| notification_service | 8206 | Multi-channel notifications |
| task_service | 8211 | Background jobs, scheduling |
| compliance_service | 8226 | Content moderation, PII detection |
| event_service | 8230 | Event sourcing, analytics |

## Audit Service (8205)

### Log Audit Event

```bash
curl -X POST "http://localhost:8205/api/v1/audit/events" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "user.login",
    "category": "authentication",
    "severity": "info",
    "actor_id": "user_123",
    "resource_type": "session",
    "resource_id": "sess_abc",
    "action": "create",
    "metadata": {
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0..."
    }
  }'
```

### Query Audit Events

```bash
curl -X POST "http://localhost:8205/api/v1/audit/events/query" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "user.login",
    "actor_id": "user_123",
    "from_date": "2024-01-01T00:00:00Z",
    "to_date": "2024-01-31T23:59:59Z",
    "limit": 100
  }'
```

### Get User Activity Summary

```bash
curl "http://localhost:8205/api/v1/audit/users/user_123/summary" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "user_id": "user_123",
  "total_events": 1250,
  "last_activity": "2024-01-28T10:30:00Z",
  "activity_by_type": {
    "user.login": 45,
    "file.upload": 320,
    "payment.created": 15
  }
}
```

### Create Security Alert

```bash
curl -X POST "http://localhost:8205/api/v1/audit/security/alerts" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_type": "suspicious_login",
    "severity": "high",
    "user_id": "user_123",
    "description": "Login from unusual location",
    "metadata": {
      "location": "Unknown Country",
      "ip_address": "203.0.113.1"
    }
  }'
```

### Generate Compliance Report

```bash
curl -X POST "http://localhost:8205/api/v1/audit/compliance/reports" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "standard": "GDPR",
    "period_start": "2024-01-01",
    "period_end": "2024-01-31",
    "include_details": true
  }'
```

### Batch Event Logging

```bash
curl -X POST "http://localhost:8205/api/v1/audit/events/batch" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {"event_type": "file.view", "resource_id": "file_1"},
      {"event_type": "file.view", "resource_id": "file_2"}
    ]
  }'
```

## Notification Service (8206)

### Create Notification Template

```bash
curl -X POST "http://localhost:8206/api/v1/notifications/templates" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "welcome_email",
    "type": "email",
    "subject": "Welcome to isA!",
    "body": "Hello {{name}}, welcome to our platform!",
    "variables": ["name"]
  }'
```

### Send Notification

```bash
curl -X POST "http://localhost:8206/api/v1/notifications/send" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "template_id": "welcome_email",
    "channels": ["email", "in_app"],
    "variables": {
      "name": "John"
    },
    "priority": "high"
  }'
```

### Send Batch Notifications

```bash
curl -X POST "http://localhost:8206/api/v1/notifications/batch" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "promotion_notice",
    "user_ids": ["user_1", "user_2", "user_3"],
    "variables": {
      "discount": "20%"
    }
  }'
```

### Get In-App Notifications

```bash
curl "http://localhost:8206/api/v1/notifications/in-app/user_123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Mark Notification as Read

```bash
curl -X POST "http://localhost:8206/api/v1/notifications/in-app/notif_123/read" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get Unread Count

```bash
curl "http://localhost:8206/api/v1/notifications/in-app/user_123/unread-count" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Register Push Subscription

```bash
curl -X POST "http://localhost:8206/api/v1/notifications/push/subscribe" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_token": "fcm_token_xyz",
    "platform": "ios",
    "device_id": "device_123"
  }'
```

### Notification Channels

| Channel | Description |
|---------|-------------|
| `email` | Email via SMTP/SendGrid |
| `sms` | SMS via Twilio |
| `in_app` | In-app notification center |
| `push` | Push notifications (iOS/Android) |
| `webhook` | HTTP webhook delivery |

## Task Service (8211)

### Create Task

```bash
curl -X POST "http://localhost:8211/api/v1/tasks" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "process_video",
    "type": "transcoding",
    "priority": "high",
    "payload": {
      "file_id": "file_123",
      "output_format": "mp4",
      "quality": "720p"
    },
    "scheduled_at": "2024-01-28T12:00:00Z"
  }'
```

Response:
```json
{
  "task_id": "task_abc123",
  "name": "process_video",
  "status": "pending",
  "priority": "high",
  "created_at": "2024-01-28T10:30:00Z",
  "scheduled_at": "2024-01-28T12:00:00Z"
}
```

### Execute Task

```bash
curl -X POST "http://localhost:8211/api/v1/tasks/task_abc123/execute" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get Task Status

```bash
curl "http://localhost:8211/api/v1/tasks/task_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "task_id": "task_abc123",
  "status": "running",
  "progress": 45,
  "started_at": "2024-01-28T12:00:00Z",
  "estimated_completion": "2024-01-28T12:05:00Z"
}
```

### Get Execution History

```bash
curl "http://localhost:8211/api/v1/tasks/task_abc123/executions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### List Tasks

```bash
curl "http://localhost:8211/api/v1/tasks?status=pending&type=transcoding&limit=20" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Task Analytics

```bash
curl "http://localhost:8211/api/v1/tasks/analytics" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Task Status

| Status | Description |
|--------|-------------|
| `pending` | Task queued |
| `scheduled` | Scheduled for later |
| `running` | Currently executing |
| `completed` | Successfully finished |
| `failed` | Execution failed |
| `cancelled` | Manually cancelled |

## Compliance Service (8226)

### Check Content

```bash
curl -X POST "http://localhost:8226/api/v1/compliance/check" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User submitted text to check",
    "content_type": "text",
    "check_types": ["toxicity", "pii", "prompt_injection"]
  }'
```

Response:
```json
{
  "check_id": "chk_abc123",
  "status": "flagged",
  "risk_level": "medium",
  "results": {
    "toxicity": {
      "score": 0.15,
      "flagged": false
    },
    "pii": {
      "detected": ["email", "phone"],
      "flagged": true,
      "redacted": "User email is [EMAIL] and phone is [PHONE]"
    },
    "prompt_injection": {
      "score": 0.02,
      "flagged": false
    }
  }
}
```

### Batch Compliance Check

```bash
curl -X POST "http://localhost:8226/api/v1/compliance/batch-check" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"id": "msg_1", "content": "First message"},
      {"id": "msg_2", "content": "Second message"}
    ],
    "check_types": ["toxicity", "pii"]
  }'
```

### Get Compliance Policies

```bash
curl "http://localhost:8226/api/v1/compliance/policies" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Generate Compliance Report

```bash
curl -X POST "http://localhost:8226/api/v1/compliance/reports" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "pii_summary",
    "period": "monthly",
    "include_details": true
  }'
```

### Check Types

| Type | Description |
|------|-------------|
| `toxicity` | Hate speech, harassment detection |
| `pii` | Personal identifiable information |
| `prompt_injection` | AI prompt injection attacks |
| `nsfw` | Adult content detection |
| `spam` | Spam content detection |

### PII Types Detected

| PII Type | Example |
|----------|---------|
| `email` | user@example.com |
| `phone` | +1-555-123-4567 |
| `ssn` | Social Security Number |
| `credit_card` | Card numbers |
| `address` | Physical addresses |

## Event Service (8230)

### Publish Event

```bash
curl -X POST "http://localhost:8230/api/v1/events" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "user.signup",
    "source": "web_app",
    "category": "user",
    "payload": {
      "user_id": "user_123",
      "plan": "free"
    },
    "correlation_id": "corr_abc123"
  }'
```

### Batch Publish Events

```bash
curl -X POST "http://localhost:8230/api/v1/events/batch" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {"event_type": "page.view", "payload": {"page": "/home"}},
      {"event_type": "button.click", "payload": {"button": "signup"}}
    ]
  }'
```

### Query Events

```bash
curl "http://localhost:8230/api/v1/events?event_type=user.signup&from=2024-01-01&limit=100" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Replay Events

```bash
curl -X POST "http://localhost:8230/api/v1/events/replay" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from_timestamp": "2024-01-01T00:00:00Z",
    "to_timestamp": "2024-01-02T00:00:00Z",
    "event_types": ["user.signup", "user.login"],
    "target_stream": "analytics_replay"
  }'
```

### Subscribe to Events

```bash
curl -X POST "http://localhost:8230/api/v1/subscriptions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_types": ["user.*", "payment.succeeded"],
    "delivery_type": "webhook",
    "webhook_url": "https://example.com/events"
  }'
```

### Get Event Statistics

```bash
curl "http://localhost:8230/api/v1/events/statistics" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "total_events": 1250000,
  "events_today": 15000,
  "by_category": {
    "user": 450000,
    "payment": 120000,
    "storage": 680000
  },
  "processing_lag_ms": 50
}
```

### Event Categories

| Category | Event Types |
|----------|-------------|
| `user` | signup, login, logout, profile_update |
| `payment` | created, succeeded, failed, refunded |
| `storage` | upload, download, delete, share |
| `system` | error, warning, maintenance |

## Python SDK

```python
from isa_user import (
    AuditClient, NotificationClient,
    TaskClient, ComplianceClient, EventClient
)

# Audit logging
audit = AuditClient("http://localhost:8205")
await audit.log_event(
    token=access_token,
    event_type="user.action",
    resource_id="resource_123"
)

# Send notification
notifications = NotificationClient("http://localhost:8206")
await notifications.send(
    token=access_token,
    user_id="user_123",
    template_id="welcome",
    channels=["email", "push"]
)

# Create background task
tasks = TaskClient("http://localhost:8211")
task = await tasks.create(
    token=access_token,
    name="process_file",
    payload={"file_id": "file_123"}
)

# Check content compliance
compliance = ComplianceClient("http://localhost:8226")
result = await compliance.check(
    token=access_token,
    content="Text to check",
    check_types=["toxicity", "pii"]
)

# Publish event
events = EventClient("http://localhost:8230")
await events.publish(
    token=access_token,
    event_type="user.action",
    payload={"action": "click"}
)
```

## Next Steps

- [Commerce](./commerce) - Orders & products
- [Security](./security) - Vault & secrets
- [Architecture](./architecture) - System design
