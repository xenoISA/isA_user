# Notification Service Logic Contract

**Business Rules and Specifications for Notification Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for notification service behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [State Machines](#state-machines)
3. [Authorization Matrix](#authorization-matrix)
4. [API Contracts](#api-contracts)
5. [Event Contracts](#event-contracts)
6. [Performance SLAs](#performance-slas)
7. [Edge Cases](#edge-cases)

---

## Business Rules

### BR-001: Send Single Notification
**Given**: Valid notification send request
**When**: System processes notification send request
**Then**:
- Notification ID generated (format: `ntf_{type}_{timestamp}`)
- Notification record created in `notification.notifications` table
- Status set to `pending` if scheduled, `sending` if immediate
- Template variables replaced if template_id provided
- Recipient validation performed (email format, phone format, user existence)
- Event `notification.sent` published after successful send
- Response includes notification object with generated ID

**Validation Rules**:
- `type`: Required, must be valid NotificationType enum
- Recipient: Either `recipient_id`, `recipient_email`, or `recipient_phone` required
- `content`: Required if no `template_id` provided
- `template_id`: Must exist if provided
- `priority`: Default `normal`, valid enum values only
- `scheduled_at`: Must be future time if provided

**Edge Cases**:
- Missing recipient → **400 Bad Request** `{"detail": "At least one recipient is required"}`
- Missing content and template → **400 Bad Request** `{"detail": "Content is required when not using a template"}`
- Invalid template_id → **404 Not Found** `{"detail": "Template not found"}`
- Invalid email format → **422 Validation Error** `{"detail": "Invalid email format"}`
- Scheduled time in past → **400 Bad Request** `{"detail": "Scheduled time must be in the future"}`

---

### BR-002: Send Batch Notifications
**Given**: Valid batch notification request
**When**: System processes batch notification request
**Then**:
- Batch ID generated (format: `batch_{timestamp}`)
- Batch record created in `notification.notification_batches` table
- Individual notification records created for each recipient
- Batch status set to `pending` or `processing`
- Async task spawned for batch processing
- Response includes batch object with total recipients

**Validation Rules**:
- `template_id`: Required, must exist
- `recipients`: Required, 1-10,000 items
- Each recipient must have `user_id` or `email`
- `scheduled_at`: Must be future time if provided
- `name`: Optional, defaults to "Batch Campaign {timestamp}"

**Processing Rules**:
- Batch processed in background with rate limiting
- Individual notifications processed with error isolation
- Batch statistics updated in real-time
- Failed notifications don't stop batch processing
- Maximum 100 notifications per second per batch

---

### BR-003: Create Notification Template
**Given**: Valid template creation request
**When**: System creates notification template
**Then**:
- Template ID generated (format: `tpl_{type}_{timestamp}`)
- Template record created in `notification.notification_templates` table
- Status set to `active` by default
- Variables extracted from content using `{{variable}}` pattern
- Response includes template object with all fields

**Validation Rules**:
- `name`: Required, unique within type, 1-255 characters
- `type`: Required, valid NotificationType enum
- `content`: Required, non-empty
- `subject`: Required for email templates, optional otherwise
- `html_content`: Optional, required only for email with HTML
- `variables`: Auto-extracted if not provided

**Variable Extraction**:
- Pattern: `{{variable_name}}`
- Case-sensitive, alphanumeric + underscore only
- Duplicates removed, order preserved
- Missing variables cause validation warning but not error

---

### BR-004: Update Notification Template
**Given**: Valid template update request
**When**: System updates notification template
**Then**:
- Template fields updated as specified
- Version incremented automatically
- Variables re-extracted if content changed
- Update timestamp set
- Response includes updated template object

**Validation Rules**:
- `template_id`: Required, must exist
- `name`: Must be unique within type if changed
- `content`: Must not be empty if provided
- `status`: Must be valid enum if provided
- Partial updates allowed (only provided fields changed)

**Version Control**:
- `version` increments by 1 for any content change
- Status changes don't increment version
- Old versions archived automatically
- Active notifications continue using their template version

---

### BR-005: Template Variable Replacement
**Given**: Template with variables and notification with variable values
**When**: System processes template-based notification
**Then**:
- All `{{variable}}` placeholders replaced with provided values
- Missing variables replaced with empty string
- Extra variables ignored (no error)
- Both subject and content processed
- HTML content processed separately from plain content

**Replacement Rules**:
- Exact match only (case-sensitive)
- Recursive replacement not supported
- Nested variables like `{{user.{{field}}}}` not processed
- HTML escaping applied only for HTML content
- Variable values can contain any string content

---

### BR-006: Send Email Notification
**Given**: Valid email notification request
**When**: System sends email notification
**Then**:
- Recipient email validated for format
- Template variables replaced if template used
- Email sent via Resend API or configured provider
- Provider message ID stored
- Status updated to `sent` on success, `failed` on error
- Event `notification.email_sent` published on success

**Email Processing**:
- `from`: Uses configured default from email
- `to`: Single recipient from recipient_email
- `subject`: From subject field or template
- `content`: Plain text body
- `html_content`: HTML body if provided
- `reply_to`: Optional from metadata

**Error Handling**:
- Invalid email → **422 Validation Error**
- Provider API error → Status `failed`, error logged
- Rate limit exceeded → Retry with exponential backoff
- Bounce detected → Status `bounced`

---

### BR-007: Send In-App Notification
**Given**: Valid in-app notification request
**When**: System creates in-app notification
**Then**:
- In-app record created in `notification.in_app_notifications` table
- User ID validated (must exist)
- Title and content required
- Default category `system` if not specified
- Response includes in-app notification object
- Event `notification.in_app_created` published

**In-App Rules**:
- `title`: Required, max 255 characters
- `message`: Required, max 2000 characters
- `category`: Optional, default `system`
- `priority`: Default `normal`, affects display order
- `action_url`: Optional, deep link for user action
- `expires_at`: Optional, auto-cleanup after expiry

---

### BR-008: Send Push Notification
**Given**: Valid push notification request
**When**: System sends push notification
**Then**:
- All active push subscriptions retrieved for user
- Push sent to each platform-specific endpoint
- Success/failure tracked per device
- Status `delivered` if any device succeeds
- Event `notification.push_sent` published

**Platform Handling**:
- **iOS**: APNs service, device token format
- **Android**: FCM service, registration token
- **Web**: Web Push Protocol, VAPID keys

**Push Processing**:
- Multiple devices supported per user
- Failed devices marked inactive after 3 failures
- Rate limiting: 10 pushes/minute/user
- Payload size limits enforced (iOS: 4KB, Android: 4KB)

---

### BR-009: Register Push Subscription
**Given**: Valid push subscription request
**When**: System registers device for push notifications
**Then**:
- Subscription record created in `notification.push_subscriptions` table
- Device token validated for platform
- Existing subscription for same user/device replaced
- Response includes subscription object
- Event `notification.subscription_registered` published

**Validation Rules**:
- `user_id`: Required, must exist
- `device_token`: Required, platform-specific format
- `platform`: Required, valid PushPlatform enum
- `endpoint`, `auth`, `p256dh`: Required for Web Push
- `device_name`, `device_model`: Optional for identification

**Uniqueness**:
- One active subscription per (user_id, device_token, platform)
- New registration replaces existing one
- Old subscriptions marked inactive automatically

---

### BR-010: List User Notifications
**Given**: Valid list notifications request
**When**: System retrieves user's in-app notifications
**Then**:
- Notifications filtered by user_id
- Pagination applied (limit 1-100, offset 0+)
- Filters applied: is_read, is_archived, category
- Results sorted by created_at DESC
- Unread count calculated and returned
- Response includes notifications and metadata

**Filtering Rules**:
- `is_read`: `true/false` or null (all)
- `is_archived`: `true/false` or null (all)
- `category`: Exact match or null (all)
- `limit`: Default 50, max 100
- `offset`: Default 0, must be >= 0

**Performance**:
- Database indexes used for efficient filtering
- Pagination prevents large result sets
- Count queries optimized with partial indexes
- Response time <200ms for 100 items

---

### BR-011: Mark Notification Read/Archived
**Given**: Valid mark read/archive request
**When**: System updates notification status
**Then**:
- In-app notification found by notification_id and user_id
- `is_read` set to true and `read_at` timestamp set
- `is_archived` set to true and `archived_at` timestamp set
- Notification moved from active to read/archived lists
- Response includes updated notification object

**Validation Rules**:
- `notification_id`: Required, must exist
- `user_id`: Required, must match notification owner
- Operation idempotent (no error if already read/archived)
- `read_at`: Optional, defaults to now

---

### BR-012: Get Notification Statistics
**Given**: Valid statistics request
**When**: System calculates notification statistics
**Then**:
- Statistics calculated from notification table
- Time period filtering applied (today, week, month, year, all)
- Counts by status: sent, delivered, failed, pending
- Counts by type: email, push, in_app, sms, webhook
- Response includes all counts and period

**Period Rules**:
- `today`: From 00:00:00 today to now
- `week`: Last 7 days from now
- `month`: Last 30 days from now
- `year`: Last 365 days from now
- `all_time`: All records

**Accuracy**:
- Real-time calculation (no caching)
- Database aggregates for performance
- Counts include all notifications, not just successful
- Period boundaries inclusive of start, exclusive of end

---

## State Machines

### Notification Status State Machine

```
┌─────────┐
│ PENDING │ Initial state, queued for sending
└────┬────┘
     │
     ▼
┌─────────┐
│ SENDING │ Currently being processed
└────┬────┘
     │
     ├────► SENT     (Email/Webhook sent successfully)
     │
     ├────► DELIVERED (In-App/Push delivered to user)
     │
     └────► FAILED    (Error during sending)
└────┬────┘
     │
     ├────► BOUNCED  (Email bounced, invalid address)
     │
     └────► CANCELLED (Expired or manually cancelled)
```

**Valid Transitions**:
- `PENDING` → `SENDING` (processing starts)
- `SENDING` → `SENT` (email/webhook sent to provider)
- `SENDING` → `DELIVERED` (in-app created, push sent)
- `SENDING` → `FAILED` (provider error, validation error)
- `SENT` → `DELIVERED` (provider confirms delivery)
- `SENT` → `BOUNCED` (email provider reports bounce)
- `FAILED` → `SENDING` (retry attempt)
- `PENDING` → `CANCELLED` (expired, manual cancellation)

**Invalid Transitions**:
- `DELIVERED` → `FAILED`
- `BOUNCED` → `SENT`
- `CANCELLED` → `SENDING`

---

### Template Status State Machine

```
┌─────────┐
│  DRAFT  │ Initial state, not ready for use
└────┬────┘
     │
     ▼
┌─────────┐
│ ACTIVE  │ Ready for use in notifications
└────┬────┘
     │
     ├────► INACTIVE (Disabled temporarily)
     │
     └────► ARCHIVED (Obsolete, replaced)
```

**Valid Transitions**:
- `DRAFT` → `ACTIVE` (template activated)
- `ACTIVE` → `INACTIVE` (temporarily disabled)
- `ACTIVE` → `ARCHIVED` (replaced or deprecated)
- `INACTIVE` → `ACTIVE` (reactivated)
- `INACTIVE` → `ARCHIVED` (deprecated while inactive)

---

### Batch Status State Machine

```
┌─────────┐
│ PENDING │ Scheduled, waiting to start
└────┬────┘
     │
     ▼
┌───────────┐
│PROCESSING │ Currently sending notifications
└─────┬─────┘
      │
      ├────► COMPLETED (All processed)
      │
      └────► FAILED     (Critical error)
```

---

## Authorization Matrix

### Notification Operations

| Action | User | Admin | System | Service Account |
|---------|-------|--------|---------|-----------------|
| **Send Notification** | ✅ (own user_id) | ✅ (any user_id) | ✅ | ✅ |
| **Send Batch** | ❌ | ✅ | ✅ | ✅ |
| **Create Template** | ❌ | ✅ | ✅ | ✅ |
| **Update Template** | ❌ | ✅ | ✅ | ✅ |
| **List Notifications** | ✅ (own user_id) | ✅ (any user_id) | ✅ | ✅ |
| **Mark Read/Archive** | ✅ (own notifications) | ✅ (any) | ✅ | ✅ |
| **Register Push Sub** | ✅ (own user_id) | ✅ (any) | ✅ | ✅ |
| **Get Statistics** | ✅ (own data) | ✅ (all data) | ✅ | ✅ |

### Template Access Control

| Template Type | Who Can Use |
|---------------|--------------|
| `email` | Admin, Service Account |
| `sms` | Admin, Service Account |
| `push` | Admin, Service Account |
| `in_app` | User (own), Admin, Service Account |
| `webhook` | Admin, Service Account |

### Notification Content Rules

| Content Type | User Can Create | Admin Can Create |
|--------------|------------------|-------------------|
| **Direct Content** | ✅ (own) | ✅ (any) |
| **Template-based** | ❌ | ✅ |
| **HTML Content** | ❌ | ✅ |
| **Scheduled Send** | ❌ | ✅ |

---

## API Contracts

### POST /api/v1/notifications/send

**Request**: `application/json`
```json
{
  "type": "email",
  "recipient_email": "user@example.com",
  "template_id": "tpl_welcome_123",
  "variables": {"name": "John", "activation_code": "ABC123"},
  "priority": "normal",
  "metadata": {"source": "user_registration"}
}
```

**Success Response**: `200 OK`
```json
{
  "notification": {
    "notification_id": "ntf_email_1234567890",
    "type": "email",
    "status": "pending",
    "recipient_email": "user@example.com",
    "template_id": "tpl_welcome_123",
    "subject": "Welcome to Our Platform!",
    "created_at": "2025-12-15T14:30:00Z"
  },
  "message": "Notification created and queued for sending",
  "success": true
}
```

**Error Responses**:
- `400 Bad Request`: Missing recipient, invalid schedule
- `422 Validation Error`: Invalid email, invalid enum values
- `404 Not Found`: Template not found
- `500 Internal Server Error`: Database error, provider error

---

### POST /api/v1/notifications/batch

**Request**: `application/json`
```json
{
  "name": "Welcome Campaign",
  "template_id": "tpl_welcome_123",
  "type": "email",
  "recipients": [
    {"user_id": "user_123", "variables": {"name": "John"}},
    {"email": "jane@example.com", "variables": {"name": "Jane"}}
  ],
  "priority": "normal",
  "scheduled_at": "2025-12-20T10:00:00Z"
}
```

**Success Response**: `200 OK`
```json
{
  "batch": {
    "batch_id": "batch_1234567890",
    "name": "Welcome Campaign",
    "template_id": "tpl_welcome_123",
    "total_count": 2,
    "status": "pending",
    "created_at": "2025-12-15T14:30:00Z"
  },
  "message": "Batch created with 2 recipients"
}
```

---

### POST /api/v1/notifications/templates

**Request**: `application/json`
```json
{
  "name": "Welcome Email Template",
  "description": "Template for user welcome emails",
  "type": "email",
  "subject": "Welcome to {{company_name}}!",
  "content": "Hello {{name}},\n\nWelcome to our platform! Your activation code is {{activation_code}}.",
  "variables": ["name", "company_name", "activation_code"],
  "metadata": {"category": "onboarding"}
}
```

**Success Response**: `200 OK`
```json
{
  "template": {
    "template_id": "tpl_email_welcome_123",
    "name": "Welcome Email Template",
    "type": "email",
    "status": "active",
    "created_at": "2025-12-15T14:30:00Z"
  },
  "message": "Template created successfully"
}
```

---

### GET /api/v1/notifications/in-app/{user_id}

**Request Parameters**:
- `user_id`: String (path)
- `is_read`: Boolean (query, optional)
- `is_archived`: Boolean (query, optional)
- `category`: String (query, optional)
- `limit`: Integer (query, optional, default: 50, max: 100)
- `offset`: Integer (query, optional, default: 0)

**Success Response**: `200 OK`
```json
{
  "notifications": [
    {
      "notification_id": "ntf_inapp_123",
      "user_id": "user_123",
      "title": "New Message",
      "message": "You have a new message from John",
      "category": "messages",
      "is_read": false,
      "created_at": "2025-12-15T14:30:00Z"
    }
  ],
  "total_count": 15,
  "unread_count": 3
}
```

---

### POST /api/v1/notifications/push/subscribe

**Request**: `application/json`
```json
{
  "user_id": "user_123",
  "device_token": "fmK2LxTzR9Q7mP8vX3nY6wJ5bG4fE1dC",
  "platform": "ios",
  "device_name": "iPhone 14 Pro",
  "device_model": "iPhone15,3",
  "app_version": "1.2.0"
}
```

**Success Response**: `200 OK`
```json
{
  "subscription": {
    "subscription_id": "sub_1234567890",
    "user_id": "user_123",
    "platform": "ios",
    "device_token": "fmK2LxTzR9Q7mP8vX3nY6wJ5bG4fE1dC",
    "is_active": true,
    "created_at": "2025-12-15T14:30:00Z"
  },
  "message": "Push subscription registered successfully"
}
```

---

### GET /api/v1/notifications/stats

**Request Parameters**:
- `user_id`: String (query, optional)
- `period`: String (query, optional, default: "all_time")

**Success Response**: `200 OK`
```json
{
  "total_sent": 1500,
  "total_delivered": 1350,
  "total_failed": 100,
  "total_pending": 50,
  "by_type": {
    "email": 800,
    "push": 500,
    "in_app": 200
  },
  "by_status": {
    "sent": 1400,
    "delivered": 1350,
    "failed": 100,
    "pending": 50
  },
  "period": "week"
}
```

---

## Event Contracts

### Event: notification.sent

**Published**: After successful notification processing
**Subject**: `notification.sent`
**Payload**:
```json
{
  "event_type": "NOTIFICATION_SENT",
  "source": "notification_service",
  "timestamp": "2025-12-15T14:30:00Z",
  "data": {
    "notification_id": "ntf_email_1234567890",
    "type": "email",
    "recipient_id": "user_123",
    "recipient_email": "user@example.com",
    "status": "sent",
    "subject": "Welcome to Our Platform!",
    "priority": "normal",
    "template_id": "tpl_welcome_123",
    "metadata": {"source": "user_registration"}
  }
}
```

**Subscribers**:
- `audit_service`: Records notification audit log
- `analytics_service`: Tracks notification metrics
- `user_service`: Updates user notification preferences

---

### Event: notification.template_created

**Published**: After template creation
**Subject**: `notification.template_created`
**Payload**:
```json
{
  "event_type": "NOTIFICATION_TEMPLATE_CREATED",
  "source": "notification_service",
  "timestamp": "2025-12-15T14:30:00Z",
  "data": {
    "template_id": "tpl_email_welcome_123",
    "name": "Welcome Email Template",
    "type": "email",
    "status": "active",
    "variables": ["name", "company_name", "activation_code"],
    "created_by": "admin_456"
  }
}
```

**Subscribers**:
- `audit_service`: Records template creation
- `admin_service`: Updates template management UI

---

### Event: notification.push_sent

**Published**: After push notification delivery attempt
**Subject**: `notification.push_sent`
**Payload**:
```json
{
  "event_type": "NOTIFICATION_PUSH_SENT",
  "source": "notification_service",
  "timestamp": "2025-12-15T14:30:00Z",
  "data": {
    "notification_id": "ntf_push_1234567890",
    "user_id": "user_123",
    "platform": "ios",
    "device_count": 2,
    "success_count": 2,
    "failed_count": 0,
    "title": "New Message",
    "message": "You have a new message"
  }
}
```

**Subscribers**:
- `analytics_service`: Tracks push delivery rates
- `device_service`: Updates device activity status

---

### Event: notification.subscription_registered

**Published**: After push subscription registration
**Subject**: `notification.subscription_registered`
**Payload**:
```json
{
  "event_type": "NOTIFICATION_SUBSCRIPTION_REGISTERED",
  "source": "notification_service",
  "timestamp": "2025-12-15T14:30:00Z",
  "data": {
    "subscription_id": "sub_1234567890",
    "user_id": "user_123",
    "platform": "ios",
    "device_token": "fmK2LxTzR9Q7mP8vX3nY6wJ5bG4fE1dC",
    "device_name": "iPhone 14 Pro",
    "app_version": "1.2.0"
  }
}
```

**Subscribers**:
- `analytics_service`: Tracks push subscription metrics
- `device_service`: Updates device registry

---

## Performance SLAs

### Response Time Targets (p95)

| Operation | Target | Max Acceptable |
|------------|---------|-----------------|
| Send Notification | < 500ms | < 2s |
| Send Batch | < 1s | < 5s |
| Create Template | < 300ms | < 1s |
| Update Template | < 300ms | < 1s |
| List Notifications | < 200ms | < 1s |
| Mark Read/Archive | < 100ms | < 500ms |
| Register Push Sub | < 200ms | < 1s |
| Get Statistics | < 500ms | < 2s |

### Throughput Targets

- **Email Sending**: 100 emails/second
- **Push Notifications**: 1000 pushes/second
- **In-App Notifications**: 5000 notifications/second
- **Batch Processing**: 10,000 notifications/batch
- **Template Lookups**: 10,000 lookups/second

### Resource Limits

- **Max Batch Size**: 10,000 recipients
- **Max Recipients/User**: 100 push subscriptions
- **Max Notification Content**: 10MB (including attachments)
- **Max Template Content**: 1MB
- **Rate Limiting**: 100 requests/minute/user

---

## Edge Cases

### EC-001: Concurrent Template Updates
**Scenario**: Multiple admins update same template simultaneously
**Expected**: Last update wins, version increments correctly
**Solution**: Database row-level locking with optimistic concurrency

### EC-002: Push Subscription Conflicts
**Scenario**: User registers same device token multiple times
**Expected**: New registration replaces old one
**Solution**: UNIQUE constraint on (user_id, device_token, platform)

### EC-003: Batch Processing Partial Failure
**Scenario**: Some notifications in batch fail, others succeed
**Expected**: Batch continues processing, statistics track both
**Solution**: Error isolation per notification, continue batch

### EC-004: Template Variable Mismatch
**Scenario**: Template expects variables not provided in request
**Expected**: Variables replaced with empty strings, notification sent
**Solution**: Graceful degradation, log warning but continue

### EC-005: Email Provider Rate Limit
**Scenario**: Email provider returns 429 Too Many Requests
**Expected**: Automatic retry with exponential backoff
**Solution**: Retry queue with jitter, max 3 attempts

### EC-006: Large Notification Content
**Scenario**: User sends notification with very large content
**Expected**: Validation error with size limit information
**Solution**: Content size validation before processing

### EC-007: Invalid Push Device Token
**Scenario**: Push sent to device with expired/invalid token
**Expected**: Mark subscription as inactive after 3 failures
**Solution**: Failure counter with automatic cleanup

### EC-008: Scheduled Notification in Past
**Scenario**: User schedules notification for past time
**Expected**: Validation error with specific message
**Solution**: Time validation before creating notification

### EC-009: Template Version Conflicts
**Scenario**: Notification references outdated template version
**Expected**: Use latest active version of template
**Solution**: Template lookup ignores version, uses active

### EC-010: Notification Delivery Race Conditions
**Scenario**: Same notification delivered multiple times
**Expected**: Idempotent delivery, deduplication by ID
**Solution**: Unique notification_id prevents duplicates

---

## Test Coverage Requirements

All tests MUST cover:

- ✅ Happy path (BR-XXX success scenarios)
- ✅ Validation errors (400, 422)
- ✅ Authorization failures (401, 403)
- ✅ Not found errors (404)
- ✅ State transitions (valid and invalid)
- ✅ Event publishing (verify published)
- ✅ Edge cases (EC-XXX scenarios)
- ✅ Performance within SLAs
- ✅ Batch processing scenarios
- ✅ Template variable replacement
- ✅ Push subscription management
- ✅ Rate limiting behavior

---

**Version**: 1.0.0
**Last Updated**: 2025-12-15
**Owner**: Notification Service Team
