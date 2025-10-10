# Task Service - Complete API Guide

## Service Overview

Task Service is a comprehensive task management microservice providing todo management, task scheduling, calendar events, reminders, analytics, and templates.

**Service Information:**
- **Port:** 8211
- **Base URL:** `http://localhost:8211`
- **Authentication:** JWT tokens or API keys (required for all endpoints except health checks)
- **Version:** 1.0.0
- **Auth Service Port:** 8202

## Quick Start

### 1. Generate Authentication Token

```bash
curl -s -X POST "http://localhost:8202/api/v1/auth/dev-token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_task_user",
    "email": "test@task.com",
    "expires_in": 86400
  }' | jq .
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzU5MzgwMTQ0LCJzdWIiOiJ0ZXN0X3Rhc2tfdXNlciIsImVtYWlsIjoidGVzdEB0YXNrLmNvbSIsInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiaXNzIjoic3VwYWJhc2UiLCJpYXQiOjE3NTkyOTM3NDR9.ieGV68_tEE31nkFGtFvqqz5dhxhQBrwMJCe_MAk8fGw",
  "expires_in": 86400,
  "token_type": "Bearer",
  "user_id": "test_task_user",
  "email": "test@task.com"
}
```

### 2. Test Service Health

```bash
curl http://localhost:8211/health | jq .
```

**Response:**
```json
{
  "status": "healthy",
  "service": "task_service",
  "port": 8211,
  "version": "1.0.0"
}
```

## API Endpoints

### Health Checks

#### Basic Health Check
**Endpoint:** `GET /health`

```bash
curl http://localhost:8211/health | jq .
```

**Response:**
```json
{
  "status": "healthy",
  "service": "task_service",
  "port": 8211,
  "version": "1.0.0"
}
```

#### Detailed Health Check
**Endpoint:** `GET /health/detailed`

```bash
curl http://localhost:8211/health/detailed | jq .
```

**Response:**
```json
{
  "status": "healthy",
  "service": "task_service",
  "port": 8211,
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "service": "healthy"
  }
}
```

### Task CRUD Operations

#### Create Task
**Endpoint:** `POST /api/v1/tasks`

**Example 1: Simple Todo Task**
```bash
curl -s -X POST "http://localhost:8211/api/v1/tasks" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Task Creation",
    "description": "Testing after all fixes",
    "task_type": "todo",
    "priority": "high"
  }' | jq .
```

**Response:**
```json
{
  "id": 15,
  "task_id": "e888b5b2-4ebf-4b45-82b9-2eeb1b0d85a3",
  "user_id": "test_task_user",
  "name": "Test Task Creation",
  "description": "Testing after all fixes",
  "task_type": "todo",
  "status": "pending",
  "priority": "high",
  "config": {},
  "schedule": null,
  "credits_per_run": "0.0",
  "tags": [],
  "metadata": {},
  "next_run_time": null,
  "last_run_time": null,
  "last_success_time": null,
  "last_error": null,
  "last_result": null,
  "run_count": 0,
  "success_count": 0,
  "failure_count": 0,
  "total_credits_consumed": "0.0",
  "due_date": null,
  "reminder_time": null,
  "created_at": "2025-10-01T04:42:36.088263Z",
  "updated_at": "2025-10-01T04:42:36.088270Z",
  "deleted_at": null
}
```

**Example 2: Calendar Event Task**
```bash
curl -s -X POST "http://localhost:8211/api/v1/tasks" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Team Meeting",
    "description": "Weekly team sync",
    "task_type": "calendar_event",
    "priority": "high",
    "config": {
      "event_title": "Team Meeting",
      "event_time": "2025-10-05T10:00:00Z"
    }
  }' | jq .
```

**Response:**
```json
{
  "id": 16,
  "task_id": "5c0aa3ef-cb07-44d6-adc3-cc0357c0f807",
  "user_id": "test_task_user",
  "name": "Team Meeting",
  "description": "Weekly team sync",
  "task_type": "calendar_event",
  "status": "pending",
  "priority": "high",
  "config": {
    "event_time": "2025-10-05T10:00:00Z",
    "event_title": "Team Meeting"
  },
  "schedule": null,
  "credits_per_run": "0.0",
  "tags": [],
  "metadata": {},
  "next_run_time": null,
  "last_run_time": null,
  "last_success_time": null,
  "last_error": null,
  "last_result": null,
  "run_count": 0,
  "success_count": 0,
  "failure_count": 0,
  "total_credits_consumed": "0.0",
  "due_date": null,
  "reminder_time": null,
  "created_at": "2025-10-01T05:08:52.914870Z",
  "updated_at": "2025-10-01T05:08:52.914879Z",
  "deleted_at": null
}
```

#### Get All Tasks
**Endpoint:** `GET /api/v1/tasks`

**Query Parameters:**
- `status` - Filter by status (pending, running, completed, failed, cancelled, paused)
- `task_type` - Filter by task type (todo, calendar_event, reminder, etc.)
- `priority` - Filter by priority (low, medium, high, urgent)
- `limit` - Max items to return (1-500, default: 100)
- `offset` - Number of items to skip (default: 0)

```bash
curl -s -X GET "http://localhost:8211/api/v1/tasks" \
  -H "Authorization: Bearer <token>" | jq .
```

**Response:**
```json
{
  "tasks": [
    {
      "id": 15,
      "task_id": "e888b5b2-4ebf-4b45-82b9-2eeb1b0d85a3",
      "user_id": "test_task_user",
      "name": "Test Task Creation",
      "description": "Testing after all fixes",
      "task_type": "todo",
      "status": "pending",
      "priority": "high",
      "config": {},
      "schedule": null,
      "credits_per_run": "0.0",
      "tags": [],
      "metadata": {},
      "next_run_time": null,
      "last_run_time": null,
      "last_success_time": null,
      "last_error": null,
      "last_result": null,
      "run_count": 0,
      "success_count": 0,
      "failure_count": 0,
      "total_credits_consumed": "0.0",
      "due_date": null,
      "reminder_time": null,
      "created_at": "2025-10-01T04:42:36.088263Z",
      "updated_at": "2025-10-01T04:42:36.088270Z",
      "deleted_at": null
    }
  ],
  "count": 1,
  "limit": 100,
  "offset": 0,
  "filters": {
    "status": null,
    "task_type": null
  }
}
```

#### Get Single Task
**Endpoint:** `GET /api/v1/tasks/{task_id}`

```bash
curl -s -X GET "http://localhost:8211/api/v1/tasks/e888b5b2-4ebf-4b45-82b9-2eeb1b0d85a3" \
  -H "Authorization: Bearer <token>" | jq .
```

**Response:**
```json
{
  "id": 15,
  "task_id": "e888b5b2-4ebf-4b45-82b9-2eeb1b0d85a3",
  "user_id": "test_task_user",
  "name": "Test Task Creation",
  "description": "Testing after all fixes",
  "task_type": "todo",
  "status": "pending",
  "priority": "high",
  "config": {},
  "schedule": null,
  "credits_per_run": "0.0",
  "tags": [],
  "metadata": {},
  "next_run_time": null,
  "last_run_time": null,
  "last_success_time": null,
  "last_error": null,
  "last_result": null,
  "run_count": 0,
  "success_count": 0,
  "failure_count": 0,
  "total_credits_consumed": "0.0",
  "due_date": null,
  "reminder_time": null,
  "created_at": "2025-10-01T04:42:36.088263Z",
  "updated_at": "2025-10-01T04:42:36.088270Z",
  "deleted_at": null
}
```

#### Update Task
**Endpoint:** `PUT /api/v1/tasks/{task_id}`

```bash
curl -s -X PUT "http://localhost:8211/api/v1/tasks/e888b5b2-4ebf-4b45-82b9-2eeb1b0d85a3" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Task Name",
    "priority": "medium"
  }' | jq .
```

**Response:**
```json
{
  "id": 15,
  "task_id": "e888b5b2-4ebf-4b45-82b9-2eeb1b0d85a3",
  "user_id": "test_task_user",
  "name": "Updated Task Name",
  "description": "Testing after all fixes",
  "task_type": "todo",
  "status": "pending",
  "priority": "medium",
  "config": {},
  "schedule": null,
  "credits_per_run": "0.0",
  "tags": [],
  "metadata": {},
  "next_run_time": null,
  "last_run_time": null,
  "last_success_time": null,
  "last_error": null,
  "last_result": null,
  "run_count": 0,
  "success_count": 0,
  "failure_count": 0,
  "total_credits_consumed": "0.0",
  "due_date": null,
  "reminder_time": null,
  "created_at": "2025-10-01T04:42:36.088263Z",
  "updated_at": "2025-10-01T04:49:26.205690Z",
  "deleted_at": null
}
```

#### Delete Task
**Endpoint:** `DELETE /api/v1/tasks/{task_id}`

```bash
curl -s -X DELETE "http://localhost:8211/api/v1/tasks/e888b5b2-4ebf-4b45-82b9-2eeb1b0d85a3" \
  -H "Authorization: Bearer <token>" | jq .
```

**Response:**
```json
{
  "message": "Task deleted successfully"
}
```

### Task Execution

#### Execute Task Manually
**Endpoint:** `POST /api/v1/tasks/{task_id}/execute`

```bash
curl -s -X POST "http://localhost:8211/api/v1/tasks/e888b5b2-4ebf-4b45-82b9-2eeb1b0d85a3/execute" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" | jq .
```

**Response:**
```json
{
  "id": 1,
  "execution_id": "exec_b90b04355182",
  "task_id": "e888b5b2-4ebf-4b45-82b9-2eeb1b0d85a3",
  "user_id": "test_task_user",
  "status": "running",
  "trigger_type": "manual",
  "trigger_data": {},
  "result": null,
  "error_message": null,
  "error_details": null,
  "credits_consumed": "0.0",
  "tokens_used": null,
  "api_calls_made": 0,
  "duration_ms": null,
  "started_at": "2025-10-01T04:54:17.844878Z",
  "completed_at": null,
  "created_at": "2025-10-01T04:54:17.844883Z"
}
```

#### Get Task Execution History
**Endpoint:** `GET /api/v1/tasks/{task_id}/executions`

**Query Parameters:**
- `limit` - Max items to return (default: 50)

```bash
curl -s -H "Authorization: Bearer <token>" \
  "http://localhost:8211/api/v1/tasks/{task_id}/executions?limit=50" | jq .
```

### Analytics

#### Get Task Analytics
**Endpoint:** `GET /api/v1/analytics`

**Query Parameters:**
- `days` - Number of days to analyze (default: 30)

```bash
curl -s -H "Authorization: Bearer <token>" \
  "http://localhost:8211/api/v1/analytics?days=30" | jq .
```

**Response:**
```json
{
  "user_id": "test_task_user",
  "time_period": "30d",
  "total_tasks": 0,
  "active_tasks": 0,
  "completed_tasks": 0,
  "failed_tasks": 0,
  "paused_tasks": 0,
  "total_executions": 0,
  "successful_executions": 0,
  "failed_executions": 0,
  "success_rate": 0.0,
  "average_execution_time": 0.0,
  "total_credits_consumed": "0.0",
  "total_tokens_used": 0
}
```

### Task Templates

#### Get Available Templates
**Endpoint:** `GET /api/v1/templates`

```bash
curl -s -H "Authorization: Bearer <token>" \
  http://localhost:8211/api/v1/templates | jq .
```

#### Create Task from Template
**Endpoint:** `POST /api/v1/tasks/from-template`

```bash
curl -s -X POST http://localhost:8211/api/v1/tasks/from-template \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "template_123",
    "customization": {
      "name": "My Custom Task",
      "config": {
        "custom_param": "value"
      }
    }
  }' | jq .
```

### Service Information

#### Get Service Statistics
**Endpoint:** `GET /api/v1/service/stats`

```bash
curl http://localhost:8211/api/v1/service/stats | jq .
```

**Response:**
```json
{
  "service": "task_service",
  "version": "1.0.0",
  "port": 8211,
  "endpoints": {
    "health": 2,
    "crud": 5,
    "execution": 2,
    "templates": 2,
    "analytics": 1,
    "scheduler": 2
  },
  "features": [
    "todo_management",
    "task_scheduling",
    "calendar_events",
    "reminders",
    "analytics",
    "templates"
  ]
}
```

## Task Types

### Supported Task Types

1. **todo** - Simple todo/task management
2. **reminder** - One-time or recurring reminders
3. **calendar_event** - Calendar events with specific times
4. **daily_weather** - Daily weather forecast
5. **daily_news** - Daily news summary
6. **news_monitor** - Monitor keywords in news
7. **weather_alert** - Severe weather alerts
8. **price_tracker** - Track product prices
9. **custom** - Custom webhook tasks

### Task Type Configuration Requirements

#### Todo Task
```json
{
  "name": "Buy groceries",
  "task_type": "todo",
  "priority": "medium",
  "due_date": "2025-10-03T18:00:00Z"
}
```

#### Calendar Event Task
**Required config fields:** `event_title`, `event_time`

```json
{
  "name": "Team Meeting",
  "task_type": "calendar_event",
  "priority": "high",
  "config": {
    "event_title": "Team Meeting",
    "event_time": "2025-10-05T10:00:00Z"
  }
}
```

#### Daily Weather Task
```json
{
  "name": "Daily Weather",
  "task_type": "daily_weather",
  "config": {
    "location": "Shanghai",
    "units": "celsius",
    "time": "08:00"
  },
  "schedule": {
    "type": "daily",
    "time": "08:00"
  }
}
```

#### Reminder Task
```json
{
  "name": "Meeting Reminder",
  "task_type": "reminder",
  "priority": "high",
  "reminder_time": "2025-10-05T09:45:00Z",
  "config": {
    "notification_channels": ["in_app", "email"],
    "reminder_before": 15
  }
}
```

### Common Task Fields

- `name` (string, required) - Task name
- `description` (string, optional) - Task description
- `task_type` (string, required) - Task type (see list above)
- `priority` (string, optional) - Priority: low, medium, high, urgent (default: medium)
- `status` (string, auto-managed) - Status: pending, running, completed, failed, cancelled, paused
- `config` (object, optional) - Task-specific configuration
- `schedule` (object, optional) - Schedule for recurring tasks
- `tags` (array, optional) - Array of tags
- `metadata` (object, optional) - Additional metadata
- `due_date` (string, optional) - Due date in ISO 8601 format
- `reminder_time` (string, optional) - Reminder time in ISO 8601 format
- `is_completed` (boolean, auto-managed) - Completion status
- `completed_at` (string, auto-managed) - Completion timestamp

## Error Handling

### HTTP Status Codes

- `200` - Success
- `400` - Bad request / Validation error
- `401` - Unauthorized / Invalid token
- `403` - Forbidden / Permission denied
- `404` - Resource not found
- `500` - Internal server error
- `503` - Service unavailable

### Error Response Format

```json
{
  "detail": "Error message"
}
```

### Common Errors

```json
// Authentication errors
{"detail": "Authentication required"}
{"detail": "Authentication error"}

// Task errors
{"detail": "Task not found"}
{"detail": "Failed to create task"}
{"detail": "Task update failed: ..."}

// Validation errors
{"detail": "Missing required field for calendar event task: event_title"}
{"detail": [{"type": "enum", "msg": "Input should be 'todo', 'reminder', ..."}]}
```

## Database Schema

### Migration Files

1. **001_create_task_tables.sql** - Creates base tables
2. **002_add_todo_calendar_fields.sql** - Adds todo/calendar fields

Run migrations:
```bash
psql -U postgres -d postgres -f microservices/task_service/migrations/001_create_task_tables.sql
psql -U postgres -d postgres -f microservices/task_service/migrations/002_add_todo_calendar_fields.sql
```

### Key Database Fields

```sql
-- user_tasks table
id                      serial primary key
task_id                 uuid unique
user_id                 text (foreign key)
name                    text
description             text
task_type               text
status                  text
priority                text
config                  jsonb
schedule                jsonb
tags                    text[]
metadata                jsonb
due_date                timestamptz
reminder_time           timestamptz
is_completed            boolean
completed_at            timestamptz
created_at              timestamptz
updated_at              timestamptz
deleted_at              timestamptz
```

## Service Management

### Start Service

```bash
# Development mode (auto-reload)
./scripts/start_all_services.sh dev task_service

# Restart service
./scripts/start_all_services.sh restart task_service

# View logs
./scripts/start_all_services.sh logs task_service

# Check status
./scripts/start_all_services.sh status
```

### Manual Start
```bash
python -m microservices.task_service.main
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
DB_SCHEMA=dev

# Service
TASK_SERVICE_HOST=0.0.0.0
TASK_SERVICE_PORT=8211

# Auth Service
AUTH_SERVICE_URL=http://localhost:8202

# Consul (optional)
CONSUL_HOST=localhost
CONSUL_PORT=8500
```

## Complete Test Script

```bash
#!/bin/bash

# 1. Get authentication token
echo "=== Getting Auth Token ==="
TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8202/api/v1/auth/dev-token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_task_user",
    "email": "test@task.com",
    "expires_in": 86400
  }')

TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.token')
echo "Token obtained: ${TOKEN:0:50}..."

# 2. Health check
echo -e "\n=== Health Check ==="
curl -s http://localhost:8211/health | jq .

# 3. Create todo task
echo -e "\n=== Creating Todo Task ==="
TODO_RESPONSE=$(curl -s -X POST "http://localhost:8211/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Todo Task",
    "description": "Testing todo functionality",
    "task_type": "todo",
    "priority": "high"
  }')

echo $TODO_RESPONSE | jq .
TODO_TASK_ID=$(echo $TODO_RESPONSE | jq -r '.task_id')

# 4. Create calendar event
echo -e "\n=== Creating Calendar Event ==="
CALENDAR_RESPONSE=$(curl -s -X POST "http://localhost:8211/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Team Meeting",
    "description": "Weekly sync",
    "task_type": "calendar_event",
    "priority": "high",
    "config": {
      "event_title": "Team Meeting",
      "event_time": "2025-10-05T10:00:00Z"
    }
  }')

echo $CALENDAR_RESPONSE | jq .
CALENDAR_TASK_ID=$(echo $CALENDAR_RESPONSE | jq -r '.task_id')

# 5. Get all tasks
echo -e "\n=== Getting All Tasks ==="
curl -s -X GET "http://localhost:8211/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" | jq .

# 6. Get single task
echo -e "\n=== Getting Single Task ==="
curl -s -X GET "http://localhost:8211/api/v1/tasks/$TODO_TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .

# 7. Update task
echo -e "\n=== Updating Task ==="
curl -s -X PUT "http://localhost:8211/api/v1/tasks/$TODO_TASK_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Task Name",
    "priority": "medium"
  }' | jq .

# 8. Execute task
echo -e "\n=== Executing Task ==="
curl -s -X POST "http://localhost:8211/api/v1/tasks/$TODO_TASK_ID/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq .

# 9. Get analytics
echo -e "\n=== Getting Analytics ==="
curl -s "http://localhost:8211/api/v1/analytics?days=30" \
  -H "Authorization: Bearer $TOKEN" | jq .

# 10. Get templates
echo -e "\n=== Getting Templates ==="
curl -s http://localhost:8211/api/v1/templates \
  -H "Authorization: Bearer $TOKEN" | jq .

# 11. Delete tasks
echo -e "\n=== Deleting Todo Task ==="
curl -s -X DELETE "http://localhost:8211/api/v1/tasks/$TODO_TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .

echo -e "\n=== Deleting Calendar Task ==="
curl -s -X DELETE "http://localhost:8211/api/v1/tasks/$CALENDAR_TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .

echo -e "\n=== Test Complete ==="
```

## Test Results (2025-10-01)

### ✅ Successfully Tested Endpoints

- `GET /health` - Service health check
- `GET /health/detailed` - Detailed health check
- `POST /api/v1/tasks` - Task creation (todo and calendar_event)
- `GET /api/v1/tasks` - List all tasks with filters
- `GET /api/v1/tasks/{task_id}` - Get single task
- `PUT /api/v1/tasks/{task_id}` - Update task
- `POST /api/v1/tasks/{task_id}/execute` - Execute task
- `DELETE /api/v1/tasks/{task_id}` - Delete task

### 🐛 Bugs Fixed During Testing

1. **Task Creation Bug** (main.py:225)
   - Issue: `request.model_dump()` passed dict instead of object
   - Fix: Pass `request` object directly

2. **Task Update Bug** (main.py:263)
   - Issue: Same model_dump() issue
   - Fix: Pass `request` object directly

3. **Task Execute Bug** (main.py:329)
   - Issue: Same model_dump() issue
   - Fix: Pass `request` object directly

4. **Database Schema** (missing columns)
   - Issue: Missing `due_date`, `reminder_time`, `is_completed`, `completed_at`
   - Fix: Created and applied migration `002_add_todo_calendar_fields.sql`

5. **UUID Type Mismatch** (task_repository.py:38)
   - Issue: String task_id format didn't match database UUID type
   - Fix: Changed to `str(uuid.uuid4())`

6. **Auth Response Parsing** (main.py:166-177)
   - Issue: Incorrect user_id extraction from auth response
   - Fix: Read `user_id` from top level of response

## Integration Notes

### Dependencies

- **Auth Service** (port 8202) - Token verification
- **Supabase** - PostgreSQL database
- **Consul** (optional) - Service discovery

### Database Setup

```sql
-- Ensure test user exists
INSERT INTO dev.users (user_id, email, name, subscription_status, is_active)
VALUES ('test_task_user', 'test@task.com', 'Task Test User', 'free', true)
ON CONFLICT (user_id) DO NOTHING;
```

## Troubleshooting

### Common Issues

**"Authentication error"**
- Check auth_service is running on port 8202
- Generate new token if expired
- Verify token format is correct

**"Task creation failed"**
- Check database connection
- Verify user exists in dev.users
- Ensure migrations are applied

**"Missing required field for calendar event task"**
- Calendar events require `event_title` and `event_time` in config
- Check config object structure

**"Task not found"**
- Verify task_id is valid UUID
- Check task belongs to authenticated user
- Task may have been soft-deleted

### Check Service Logs

```bash
./scripts/start_all_services.sh logs task_service
```

### Verify Service Health

```bash
curl http://localhost:8211/health/detailed | jq .
```

## Support

For questions or issues:
- Service logs: `./scripts/start_all_services.sh logs task_service`
- Health check: `curl http://localhost:8211/health/detailed`
- Code location: `/microservices/task_service/`
