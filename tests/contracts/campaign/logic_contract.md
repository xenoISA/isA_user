# Campaign Service Logic Contract

**Business Rules and Specifications for Campaign Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for campaign service behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [State Machines](#state-machines)
3. [Authorization Matrix](#authorization-matrix)
4. [API Contracts](#api-contracts)
5. [Event Contracts](#event-contracts)
6. [Performance SLAs](#performance-slas)
7. [Edge Cases](#edge-cases)
8. [Test Coverage Requirements](#test-coverage-requirements)

---

## Business Rules

### BR-CAM-001: Campaign Lifecycle Management

**Capability**: Create, configure, activate, pause, and complete campaigns

---

#### BR-CAM-001.1: Create Campaign

**Given**: Valid campaign creation request with required fields
**When**: System processes campaign creation request
**Then**:
- Campaign ID generated (format: `cmp_{uuid16}`)
- Campaign record created in `campaign.campaigns` table
- Status set to `draft`
- Default variant created if no A/B testing enabled
- Audiences validated for existence (isA_Data segment references)
- Channels validated for required content per type
- Event `campaign.created` published after successful creation
- Response includes campaign object with generated ID

**Validation Rules**:
- `name`: Required, 1-255 characters
- `description`: Optional, max 2000 characters
- `campaign_type`: Required, must be `scheduled` or `triggered`
- `organization_id`: Required, extracted from auth context
- `created_by`: Required, extracted from auth context
- `audiences`: Optional, max 10 segments per campaign (BR-CAM-002.6)
- `channels`: Required if no variants specified (at least one channel)
- `holdout_percentage`: Optional, 0-20% (BR-CAM-001 constraint)

**Edge Cases**:
- Missing name -> **400 Bad Request** `{"detail": "Campaign name is required"}`
- Empty name -> **422 Validation Error** `{"detail": "Name must be at least 1 character"}`
- Name exceeds 255 chars -> **422 Validation Error** `{"detail": "Name must not exceed 255 characters"}`
- Invalid campaign_type -> **422 Validation Error** `{"detail": "Invalid campaign type"}`
- Holdout > 20% -> **422 Validation Error** `{"detail": "Holdout percentage must be between 0 and 20"}`
- More than 10 segments -> **400 Bad Request** `{"detail": "Maximum 10 segments per campaign"}`

---

#### BR-CAM-001.2: Schedule Campaign (Scheduled Type)

**Given**: Draft campaign of type `scheduled` with valid configuration
**When**: System processes schedule request
**Then**:
- Campaign validated for completeness (audiences, channels, content)
- Schedule type validated (`one_time` or `recurring`)
- Scheduled time validated (minimum 5 minutes in future)
- Task created in task_service for execution
- Campaign status updated to `scheduled`
- `task_id` stored in campaign record
- Event `campaign.scheduled` published with task_id
- Response includes updated campaign with scheduled status

**Validation Rules**:
- `schedule_type`: Required, must be `one_time` or `recurring`
- `scheduled_at`: Required for one_time, must be >= now + 5 minutes
- `cron_expression`: Required for recurring, valid cron format
- `timezone`: Optional, default UTC, valid IANA timezone

**Edge Cases**:
- Missing audiences -> **400 Bad Request** `{"detail": "Campaign must have at least one audience segment"}`
- Missing channels/content -> **400 Bad Request** `{"detail": "Campaign must have valid content for configured channels"}`
- Scheduled time < 5 min future -> **400 Bad Request** `{"detail": "Scheduled time must be at least 5 minutes in the future"}`
- Invalid cron expression -> **422 Validation Error** `{"detail": "Invalid cron expression"}`
- Campaign not in draft status -> **409 Conflict** `{"detail": "Only draft campaigns can be scheduled"}`
- Campaign type is triggered -> **400 Bad Request** `{"detail": "Cannot schedule a triggered campaign"}`

---

#### BR-CAM-001.3: Activate Campaign (Triggered Type)

**Given**: Draft campaign of type `triggered` with valid triggers
**When**: System processes activate request
**Then**:
- Campaign validated for completeness (audiences, triggers, channels)
- At least one trigger condition required
- Campaign status updated to `active`
- Trigger subscriptions registered with event_service
- Event `campaign.activated` published
- Response includes updated campaign with active status

**Validation Rules**:
- At least one trigger with valid `event_type`
- Each trigger has valid conditions (field, operator, value)
- Trigger delay within bounds (0 to 30 days)
- Frequency limit configured (default: 1 per 24 hours)

**Edge Cases**:
- No triggers defined -> **400 Bad Request** `{"detail": "Triggered campaigns require at least one trigger"}`
- Campaign not in draft status -> **409 Conflict** `{"detail": "Only draft campaigns can be activated"}`
- Campaign type is scheduled -> **400 Bad Request** `{"detail": "Cannot activate a scheduled campaign"}`
- Invalid trigger event_type -> **400 Bad Request** `{"detail": "Invalid trigger event type"}`

---

#### BR-CAM-001.4: Pause Running Campaign

**Given**: Campaign in `running` status
**When**: System processes pause request
**Then**:
- In-flight messages complete delivery (not aborted)
- New message queueing stops immediately
- Campaign status updated to `paused`
- `paused_at` and `paused_by` recorded
- Execution status updated to `paused`
- Event `campaign.paused` published with messages_sent count
- Response includes updated campaign with paused status

**Validation Rules**:
- Campaign must be in `running` status
- Only authorized users can pause (Admin, System)

**Edge Cases**:
- Campaign not running -> **409 Conflict** `{"detail": "Only running campaigns can be paused"}`
- Campaign already paused -> **409 Conflict** `{"detail": "Campaign is already paused"}`

---

#### BR-CAM-001.5: Resume Paused Campaign

**Given**: Campaign in `paused` status
**When**: System processes resume request
**Then**:
- Campaign status updated to `running`
- Execution continues from where it stopped
- Remaining unprocessed messages queued
- Event `campaign.resumed` published
- Response includes updated campaign with running status

**Validation Rules**:
- Campaign must be in `paused` status
- Scheduled time not expired (for scheduled campaigns)

**Edge Cases**:
- Campaign not paused -> **409 Conflict** `{"detail": "Only paused campaigns can be resumed"}`
- Scheduled time expired -> **400 Bad Request** `{"detail": "Cannot resume expired campaign"}`

---

#### BR-CAM-001.6: Cancel Campaign

**Given**: Campaign in any non-terminal status
**When**: System processes cancel request with reason
**Then**:
- Campaign status updated to `cancelled`
- `cancelled_at`, `cancelled_by`, `cancelled_reason` recorded
- Scheduled task cancelled in task_service (if exists)
- In-flight messages allowed to complete
- No new messages queued
- Event `campaign.cancelled` published with reason
- Response includes updated campaign with cancelled status

**Validation Rules**:
- `reason`: Optional but recommended, max 500 characters
- Campaign not already completed or cancelled

**Edge Cases**:
- Campaign already completed -> **409 Conflict** `{"detail": "Cannot cancel a completed campaign"}`
- Campaign already cancelled -> **409 Conflict** `{"detail": "Campaign is already cancelled"}`

---

#### BR-CAM-001.7: Clone Campaign

**Given**: Any existing campaign regardless of status
**When**: System processes clone request
**Then**:
- New campaign created with copied configuration
- New campaign_id generated
- Status set to `draft`
- Name prefixed with "Copy of " (or custom name if provided)
- `cloned_from_id` references original campaign
- All audiences, channels, variants, triggers copied
- Schedule cleared (user must set new schedule)
- Metrics NOT copied (fresh start)
- Event `campaign.created` published for new campaign
- Response includes new campaign object

**Validation Rules**:
- Source campaign must exist
- Custom name (if provided) must follow name rules

**Edge Cases**:
- Source campaign not found -> **404 Not Found** `{"detail": "Campaign not found"}`
- Name collision -> Campaign created with unique suffix

---

#### BR-CAM-001.8: Update Campaign

**Given**: Campaign in `draft` or `paused` status
**When**: System processes update request
**Then**:
- Only modifiable fields updated
- `updated_at` and `updated_by` recorded
- Validation rules re-applied
- Event `campaign.updated` published with changed_fields
- Response includes updated campaign object

**Validation Rules**:
- Campaign must be in `draft` or `paused` status (BR-CAM-001.5)
- Running campaigns can only be paused, not edited (BR-CAM-001.6)
- Completed campaigns cannot be modified, only cloned (BR-CAM-001.7)
- Cancelled campaigns cannot be modified (BR-CAM-001.8)

**Edge Cases**:
- Campaign running -> **409 Conflict** `{"detail": "Running campaigns cannot be edited, pause first"}`
- Campaign completed -> **409 Conflict** `{"detail": "Completed campaigns cannot be edited, use clone"}`
- Campaign cancelled -> **409 Conflict** `{"detail": "Cancelled campaigns cannot be modified"}`

---

### BR-CAM-002: Audience Segmentation

**Capability**: Define and resolve audience segments for targeting

---

#### BR-CAM-002.1: Resolve Audience at Execution Time

**Given**: Campaign with audience segments ready for execution
**When**: System starts campaign execution
**Then**:
- Segment queries delegated to isA_Data intelligent_query service
- User IDs resolved in real-time for accuracy
- Multiple include segments intersected (AND logic)
- Multiple exclude segments combined (OR logic)
- Suppression lists applied (unsubscribed, bounced, complained)
- Final audience set calculated
- Audience size recorded in execution record

**Processing Rules**:
- Cache segment resolution for 5 minutes (performance optimization)
- Handle isA_Data timeouts with cached fallback
- Log warning if using cached data

**Edge Cases**:
- isA_Data unavailable -> Use cached segment if available, alert and continue
- Empty audience after resolution -> Complete execution with 0 messages, log warning
- Segment query error -> Mark execution as failed, publish `campaign.completed` with error

---

#### BR-CAM-002.2: Apply Holdout Groups

**Given**: Resolved audience and holdout_percentage configured
**When**: System applies holdout selection
**Then**:
- Holdout group selected using deterministic hash (user_id + campaign_id)
- Holdout percentage applied (e.g., 5% = 5% of users excluded)
- Same users always in holdout for same campaign (reproducible)
- Holdout users tracked separately for measurement
- Non-holdout users proceed to variant assignment

**Calculation**:
```python
hash_value = md5(f"{user_id}:{campaign_id}").hexdigest()
bucket = int(hash_value, 16) % 100
is_holdout = bucket < holdout_percentage
```

**Edge Cases**:
- Holdout percentage 0 -> No holdout applied
- Holdout percentage 20 (max) -> 20% excluded

---

#### BR-CAM-002.3: Estimate Audience Size

**Given**: Campaign with configured audiences
**When**: System processes estimate request
**Then**:
- Each segment size estimated via isA_Data
- Include segment sizes reported individually
- Exclusion impact calculated
- Holdout impact calculated
- Final estimated size returned
- Estimation timestamp recorded

**Response Structure**:
```json
{
  "estimated_size": 50000,
  "by_segment": [
    {"segment_id": "seg_premium", "type": "include", "size": 35000},
    {"segment_id": "seg_inactive", "type": "exclude", "size": 5000}
  ],
  "after_exclusions": 30000,
  "after_holdout": 28500,
  "estimated_at": "2026-01-15T10:00:00Z"
}
```

---

### BR-CAM-003: Multi-Channel Delivery

**Capability**: Deliver messages across multiple channels with channel-specific formatting

---

#### BR-CAM-003.1: Channel Content Requirements

**Given**: Campaign with multiple channels configured
**When**: System validates channel content
**Then**:
- Each channel has required content fields:

| Channel | Required Fields |
|---------|-----------------|
| **email** | subject, body_html or body_text, sender_email |
| **sms** | body (max 160 chars) |
| **whatsapp** | body (max 1600 chars) or template_id |
| **in_app** | title, body |
| **webhook** | url, method |

**Validation Rules**:
- Email body_html or body_text required (at least one)
- SMS body strictly <= 160 characters
- WhatsApp body <= 1600 characters
- Webhook URL must be valid HTTPS URL
- Template variables validated against user_360 schema

**Edge Cases**:
- SMS body > 160 chars -> **422 Validation Error** `{"detail": "SMS body must not exceed 160 characters"}`
- WhatsApp body > 1600 chars -> **422 Validation Error** `{"detail": "WhatsApp body must not exceed 1600 characters"}`
- Invalid webhook URL -> **422 Validation Error** `{"detail": "Webhook URL must be a valid HTTPS URL"}`
- Missing email subject -> **422 Validation Error** `{"detail": "Email subject is required"}`

---

#### BR-CAM-003.2: Channel Eligibility Check

**Given**: User in audience and channel configured
**When**: System checks channel eligibility
**Then**:
- User preferences checked from account_service
- Contact data availability verified:

| Channel | Eligibility Requirements |
|---------|--------------------------|
| **email** | Valid email + email_opted_in=true |
| **sms** | Valid phone + sms_opted_in=true |
| **whatsapp** | Verified WhatsApp number |
| **in_app** | Active user account (delivered on next login if offline) |
| **webhook** | Always eligible |

**Processing Rules**:
- Users without channel eligibility skipped for that channel
- Multiple channels: try in priority order (fallback)
- At least one channel must succeed for message to be counted

**Edge Cases**:
- No eligible channels -> User skipped, logged as "no_eligible_channel"
- Email bounced previously -> Channel marked ineligible
- User unsubscribed -> All marketing channels ineligible

---

#### BR-CAM-003.3: Channel Fallback Order

**Given**: Campaign with multiple channels and priority configured
**When**: System attempts message delivery
**Then**:
- Channels attempted in priority order (lower number = higher priority)
- If primary channel fails, next channel attempted
- Success on any channel counts as delivered
- All attempted channels logged in message record

**Example Configuration**:
```json
{
  "channels": [
    {"channel_type": "email", "priority": 1},
    {"channel_type": "in_app", "priority": 2},
    {"channel_type": "sms", "priority": 3}
  ]
}
```

---

### BR-CAM-004: A/B Testing

**Capability**: Test multiple content variants to optimize campaign performance

---

#### BR-CAM-004.1: Create Campaign Variants

**Given**: Campaign with A/B testing enabled
**When**: System validates variant configuration
**Then**:
- Maximum 5 variants allowed per campaign
- Variant allocation percentages must sum to 100%
- Each variant has independent channel content
- Control variant (no message) supported

**Validation Rules**:
- `variants`: 2-5 items required when A/B testing enabled
- `allocation_percentage`: Each >= 0, total = 100
- `name`: Required, unique within campaign
- `is_control`: Boolean, only one control variant allowed

**Edge Cases**:
- Allocations sum != 100 -> **422 Validation Error** `{"detail": "Variant allocations must sum to 100%"}`
- More than 5 variants -> **400 Bad Request** `{"detail": "Maximum 5 variants per campaign"}`
- Multiple control variants -> **400 Bad Request** `{"detail": "Only one control variant allowed"}`

---

#### BR-CAM-004.2: Deterministic Variant Assignment

**Given**: User in audience and variants configured
**When**: System assigns user to variant
**Then**:
- Assignment is deterministic using hash of user_id + campaign_id
- Same user always gets same variant for same campaign
- Hash maps to percentage bucket
- Bucket determines variant based on cumulative allocation

**Algorithm**:
```python
def assign_variant(user_id: str, campaign_id: str, variants: List[Variant]) -> Variant:
    hash_value = md5(f"{user_id}:{campaign_id}").hexdigest()
    bucket = int(hash_value, 16) % 100

    cumulative = 0
    for variant in variants:
        cumulative += variant.allocation_percentage
        if bucket < cumulative:
            return variant
    return variants[-1]  # Fallback
```

---

#### BR-CAM-004.3: Statistical Significance Calculation

**Given**: A/B test with sufficient sample size
**When**: System calculates variant performance
**Then**:
- Chi-square test performed on conversion/click rates
- P-value calculated for each variant pair
- Statistical significance determined at configured threshold (90%, 95%, 99%)
- Confidence intervals calculated
- Winner highlighted when significance reached

**Requirements**:
- Minimum 1000 recipients per variant for auto-winner (BR-CAM-004.6)
- Results include: chi_square_statistic, p_value, is_significant, confidence_interval

---

#### BR-CAM-004.4: Auto-Winner Selection

**Given**: A/B test with auto_winner_enabled
**When**: Statistical significance reached
**Then**:
- Target metric evaluated (open_rate, click_rate, conversion_rate)
- Confidence threshold checked (default 95%)
- Minimum sample size verified (default 1000 per variant)
- Winner variant_id recorded
- Remaining messages sent using winner variant only
- Notification published when winner selected

**Configuration**:
```json
{
  "ab_test": {
    "enabled": true,
    "auto_winner_enabled": true,
    "auto_winner_metric": "click_rate",
    "auto_winner_confidence": 0.95,
    "auto_winner_min_sample": 1000
  }
}
```

---

### BR-CAM-005: Performance Tracking

**Capability**: Track and report campaign delivery and engagement metrics

---

#### BR-CAM-005.1: Message Lifecycle Tracking

**Given**: Campaign message queued for delivery
**When**: System processes message through lifecycle
**Then**:
- Status transitions tracked with timestamps:

| Status | Trigger | Timestamp Field |
|--------|---------|-----------------|
| `queued` | Message created | `queued_at` |
| `sent` | Sent to provider | `sent_at` |
| `delivered` | Provider confirms | `delivered_at` |
| `opened` | Pixel/event tracked | `opened_at` |
| `clicked` | Link redirect | `clicked_at` |
| `bounced` | Delivery failed | `bounced_at` |
| `failed` | Processing error | `failed_at` |
| `unsubscribed` | User opted out | `unsubscribed_at` |

- Each status change published as event
- Metrics aggregated in real-time

---

#### BR-CAM-005.2: Real-Time Metric Updates

**Given**: Message status change event received
**When**: System updates metrics
**Then**:
- Metrics updated within 5 seconds of event (BR-CAM-005.4)
- Aggregation at campaign, variant, channel, segment levels
- Rates recalculated:

| Metric | Calculation |
|--------|-------------|
| `delivery_rate` | delivered / sent |
| `open_rate` | opened / delivered |
| `click_rate` | clicked / delivered |
| `conversion_rate` | converted / sent |
| `bounce_rate` | bounced / sent |
| `unsubscribe_rate` | unsubscribed / delivered |

---

#### BR-CAM-005.3: Conversion Attribution

**Given**: Conversion event within attribution window
**When**: System processes conversion
**Then**:
- Message identified by campaign tracking token
- Attribution window checked (default 7 days, max 30 days)
- Attribution model applied:

| Model | Logic |
|-------|-------|
| `first_touch` | Credit to first campaign interaction |
| `last_touch` | Credit to most recent campaign interaction |
| `linear` | Equal credit to all campaign touches |

- Conversion value recorded (if provided in event)
- Total conversion value aggregated

---

#### BR-CAM-005.4: Click Tracking

**Given**: Campaign message with tracked links
**When**: Recipient clicks link
**Then**:
- Click captured via redirect URL
- Unique tracking token identifies message
- Original destination URL extracted and redirected
- Click timestamp and link_id recorded
- Event `campaign.message.clicked` published
- Metrics updated

**Tracking URL Format**:
```
https://track.example.com/c/{message_id}/{link_id}?url={encoded_destination}
```

---

#### BR-CAM-005.5: Open Tracking (Email)

**Given**: Email message with tracking pixel
**When**: Recipient opens email (pixel loads)
**Then**:
- Open captured via 1x1 transparent pixel request
- Unique tracking token identifies message
- Open timestamp recorded
- Event `campaign.message.opened` published
- Metrics updated

**Tracking Pixel Format**:
```
https://track.example.com/o/{message_id}.gif
```

---

### BR-CAM-006: Rate Limiting and Throttling

**Capability**: Control message delivery rate to prevent system overload and provider limits

---

#### BR-CAM-006.1: Campaign-Level Throttling

**Given**: Campaign with throttle configuration
**When**: System queues messages for delivery
**Then**:
- Messages queued at configured rate:

| Setting | Default | Description |
|---------|---------|-------------|
| `per_minute` | 10,000 | Messages per minute |
| `per_hour` | 100,000 | Messages per hour |
| `send_window_start` | 8 | Start hour (local time) |
| `send_window_end` | 21 | End hour (local time) |
| `exclude_weekends` | false | Skip Saturday/Sunday |

- Rate limit exhaustion triggers queueing, not failure (BR-CAM-006.5)
- Delivery distributed evenly over window (BR-CAM-006.4)

---

#### BR-CAM-006.2: Channel-Level Rate Limits

**Given**: Messages ready for channel delivery
**When**: System sends to notification_service
**Then**:
- Per-channel rate limits enforced:

| Channel | Default Rate Limit |
|---------|-------------------|
| **email** | 10,000/hour |
| **sms** | 1,000/hour |
| **whatsapp** | 5,000/hour |
| **in_app** | 50,000/hour |
| **webhook** | 10,000/hour |

- Channel limits are global per organization
- Campaign throttle may be lower but not higher than channel limit

---

#### BR-CAM-006.3: Quiet Hours Enforcement

**Given**: Campaign with quiet hours configured
**When**: System evaluates send timing
**Then**:
- User's local timezone determined
- Quiet hours checked (default: 21:00-08:00 user local time)
- Messages during quiet hours queued for next available window
- Triggered campaigns respect quiet hours delay

**Configuration**:
```json
{
  "throttle": {
    "send_window_start": 8,
    "send_window_end": 21,
    "exclude_weekends": true
  }
}
```

---

### BR-CAM-007: Trigger Evaluation

**Capability**: Evaluate event-based triggers and fire campaigns accordingly

---

#### BR-CAM-007.1: Evaluate Trigger Conditions

**Given**: Event received from event_service matching trigger event_type
**When**: System evaluates trigger conditions
**Then**:
- All conditions evaluated using AND logic (BR-CAM-007.3)
- Supported operators:

| Operator | Description | Example |
|----------|-------------|---------|
| `equals` | Exact match | `plan == "premium"` |
| `not_equals` | Not equal | `status != "cancelled"` |
| `contains` | String contains | `email contains "@company.com"` |
| `greater_than` | Numeric > | `amount > 100` |
| `less_than` | Numeric < | `days_since_signup < 7` |
| `in` | Value in list | `country in ["US", "CA"]` |
| `exists` | Field exists | `referral_code exists` |

**Processing**:
- If all conditions pass, trigger fires
- If any condition fails, trigger skipped (logged)

---

#### BR-CAM-007.2: Apply Trigger Delay

**Given**: Trigger evaluation passed
**When**: System applies delay configuration
**Then**:
- Delay calculated: `delay_minutes + (delay_days * 24 * 60)`
- Maximum delay: 30 days (BR-CAM-007.4)
- Scheduled send recorded in `trigger_history`
- Task scheduled for delayed execution
- Quiet hours applied to final send time

---

#### BR-CAM-007.3: Enforce Frequency Limits

**Given**: Trigger ready to fire for user
**When**: System checks frequency limit
**Then**:
- Recent trigger history checked for user + campaign
- Frequency window evaluated (default: 24 hours)
- If limit exceeded, trigger skipped with reason `frequency_limit`
- If within limit, trigger proceeds

**Configuration**:
```json
{
  "trigger": {
    "frequency_limit": 1,
    "frequency_window_hours": 24
  }
}
```

**Example**: `frequency_limit=1, frequency_window_hours=24` means max 1 trigger per user per 24 hours

---

#### BR-CAM-007.4: Verify User in Segment

**Given**: Trigger about to fire
**When**: System verifies audience membership
**Then**:
- User must be in audience segment at trigger time (BR-CAM-007.7)
- Real-time segment check via isA_Data
- If user not in segment, trigger skipped with reason `not_in_segment`
- If user in segment, message queued

---

### BR-CAM-008: Creative Content Integration

**Capability**: Integrate with isA_Creative for template management

---

#### BR-CAM-008.1: Template Variable Resolution

**Given**: Template with variables and user_360 data available
**When**: System renders message content
**Then**:
- Variables extracted using `{{variable_name}}` pattern
- Variables resolved against user_360 schema
- Missing variables replaced with empty string
- Template preview available with sample data

**Variable Examples**:
```
{{first_name}} -> "John"
{{last_name}} -> "Doe"
{{email}} -> "john@example.com"
{{subscription_plan}} -> "Premium"
{{custom_field.value}} -> "Custom Value"
```

---

#### BR-CAM-008.2: Content Preview

**Given**: Campaign with content configured and sample user
**When**: System generates preview
**Then**:
- Template variables resolved with sample user data
- Each channel content rendered independently
- HTML content rendered as HTML
- Preview includes: rendered content, sample user data, variable values

**Response**:
```json
{
  "campaign_id": "cmp_123",
  "variant_id": "var_a",
  "channel_type": "email",
  "rendered_content": {
    "subject": "Hello John!",
    "body_html": "<html>...</html>",
    "body_text": "Hello John!..."
  },
  "sample_user": {
    "first_name": "John",
    "email": "john@example.com"
  }
}
```

---

## State Machines

### Campaign Status State Machine

```
┌─────────┐
│  DRAFT  │ Initial state, configurable
└────┬────┘
     │
     ├─────────────────────────────────────────────┐
     │                                             │
     ▼                                             ▼
┌───────────┐                              ┌───────────┐
│ SCHEDULED │ (scheduled campaigns)        │  ACTIVE   │ (triggered campaigns)
└─────┬─────┘                              └─────┬─────┘
      │                                          │
      │ (task_service triggers)                  │ (event matches trigger)
      │                                          │
      ▼                                          ▼
┌───────────┐◄───────────────────────────────────┘
│  RUNNING  │ Executing, sending messages
└─────┬─────┘
      │
      ├────────────────┬────────────────┐
      │                │                │
      ▼                ▼                ▼
┌──────────┐    ┌───────────┐    ┌───────────┐
│  PAUSED  │    │ COMPLETED │    │ CANCELLED │
└────┬─────┘    └───────────┘    └───────────┘
     │                                  ▲
     │ (resume)                         │
     └─────────────────────────────────►│
                                        │
     (from any non-terminal state) ─────┘
```

**Valid Transitions**:
- `DRAFT` -> `SCHEDULED` (schedule scheduled campaign)
- `DRAFT` -> `ACTIVE` (activate triggered campaign)
- `SCHEDULED` -> `RUNNING` (task executes at scheduled time)
- `SCHEDULED` -> `CANCELLED` (cancel before execution)
- `SCHEDULED` -> `DRAFT` (unschedule to edit)
- `ACTIVE` -> `RUNNING` (trigger fires)
- `ACTIVE` -> `CANCELLED` (deactivate triggered campaign)
- `ACTIVE` -> `DRAFT` (deactivate to edit)
- `RUNNING` -> `PAUSED` (pause execution)
- `RUNNING` -> `COMPLETED` (all messages processed)
- `RUNNING` -> `CANCELLED` (cancel during execution)
- `PAUSED` -> `RUNNING` (resume execution)
- `PAUSED` -> `CANCELLED` (cancel paused campaign)

**Invalid Transitions**:
- `COMPLETED` -> any (terminal state)
- `CANCELLED` -> any (terminal state)
- `RUNNING` -> `DRAFT` (must pause first)
- `SCHEDULED` -> `ACTIVE` (different campaign types)
- `ACTIVE` -> `SCHEDULED` (different campaign types)

---

### Execution Status State Machine

```
┌─────────┐
│ PENDING │ Execution created, not started
└────┬────┘
     │
     ▼
┌─────────┐
│ RUNNING │ Messages being processed
└────┬────┘
     │
     ├─────────────┬─────────────┬─────────────┐
     │             │             │             │
     ▼             ▼             ▼             ▼
┌────────┐  ┌───────────┐  ┌────────┐  ┌───────────┐
│ PAUSED │  │ COMPLETED │  │ FAILED │  │ CANCELLED │
└────┬───┘  └───────────┘  └────────┘  └───────────┘
     │
     │ (resume)
     ▼
┌─────────┐
│ RUNNING │
└─────────┘
```

**Valid Transitions**:
- `PENDING` -> `RUNNING` (execution starts)
- `RUNNING` -> `PAUSED` (user pauses)
- `RUNNING` -> `COMPLETED` (all messages processed)
- `RUNNING` -> `FAILED` (critical error)
- `RUNNING` -> `CANCELLED` (user cancels)
- `PAUSED` -> `RUNNING` (user resumes)
- `PAUSED` -> `CANCELLED` (user cancels while paused)

---

### Message Status State Machine

```
┌────────┐
│ QUEUED │ Message created, waiting to send
└────┬───┘
     │
     ▼
┌────────┐
│  SENT  │ Sent to notification_service
└────┬───┘
     │
     ├─────────────┬─────────────┬─────────────┐
     │             │             │             │
     ▼             ▼             ▼             ▼
┌───────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐
│ DELIVERED │  │ BOUNCED │  │ FAILED  │  │        │
└─────┬─────┘  └─────────┘  └─────────┘  │        │
      │                                   │        │
      ├─────────────┬─────────────┐      │        │
      │             │             │      │        │
      ▼             ▼             ▼      ▼        │
┌────────┐   ┌─────────┐   ┌──────────────┐      │
│ OPENED │   │ CLICKED │   │ UNSUBSCRIBED │◄─────┘
└────┬───┘   └─────────┘   └──────────────┘
     │             ▲
     └─────────────┘
```

**Valid Transitions**:
- `QUEUED` -> `SENT` (sent to provider)
- `SENT` -> `DELIVERED` (provider confirms)
- `SENT` -> `BOUNCED` (delivery failed)
- `SENT` -> `FAILED` (provider error)
- `DELIVERED` -> `OPENED` (email opened)
- `DELIVERED` -> `CLICKED` (link clicked)
- `DELIVERED` -> `UNSUBSCRIBED` (user unsubscribed)
- `OPENED` -> `CLICKED` (user clicked after opening)

---

## Authorization Matrix

### Campaign Operations

| Operation | User | Admin | System | Service Account |
|-----------|------|-------|--------|-----------------|
| **Create Campaign** | ❌ | ✅ | ✅ | ✅ |
| **Read Campaign** | ✅ (org) | ✅ (any) | ✅ | ✅ |
| **Update Campaign** | ❌ | ✅ | ✅ | ✅ |
| **Delete Campaign** | ❌ | ✅ | ✅ | ✅ |
| **Schedule Campaign** | ❌ | ✅ | ✅ | ✅ |
| **Activate Campaign** | ❌ | ✅ | ✅ | ✅ |
| **Pause Campaign** | ❌ | ✅ | ✅ | ✅ |
| **Resume Campaign** | ❌ | ✅ | ✅ | ✅ |
| **Cancel Campaign** | ❌ | ✅ | ✅ | ✅ |
| **Clone Campaign** | ❌ | ✅ | ✅ | ✅ |
| **View Metrics** | ✅ (org) | ✅ (any) | ✅ | ✅ |
| **Estimate Audience** | ❌ | ✅ | ✅ | ✅ |
| **Preview Content** | ❌ | ✅ | ✅ | ✅ |

### Variant Operations

| Operation | User | Admin | System | Service Account |
|-----------|------|-------|--------|-----------------|
| **Add Variant** | ❌ | ✅ | ✅ | ✅ |
| **Update Variant** | ❌ | ✅ | ✅ | ✅ |
| **Delete Variant** | ❌ | ✅ | ✅ | ✅ |
| **View Variant Stats** | ✅ (org) | ✅ (any) | ✅ | ✅ |

### Execution Operations

| Operation | User | Admin | System | Service Account |
|-----------|------|-------|--------|-----------------|
| **View Executions** | ✅ (org) | ✅ (any) | ✅ | ✅ |
| **Start Execution** | ❌ | ❌ | ✅ | ✅ |
| **View Messages** | ✅ (org) | ✅ (any) | ✅ | ✅ |

---

## API Contracts

### POST /api/v1/campaigns

**Request**: `application/json`
```json
{
  "name": "New Year Promotion 2026",
  "description": "Promotional campaign for new year",
  "campaign_type": "scheduled",
  "schedule_type": "one_time",
  "scheduled_at": "2026-01-01T09:00:00Z",
  "timezone": "America/New_York",
  "audiences": [
    {
      "segment_type": "include",
      "segment_id": "seg_premium_users"
    },
    {
      "segment_type": "exclude",
      "segment_id": "seg_unsubscribed"
    }
  ],
  "channels": [
    {
      "channel_type": "email",
      "email_content": {
        "subject": "Happy New Year, {{first_name}}!",
        "body_html": "<html><body>Special offer for you...</body></html>",
        "body_text": "Special offer for you...",
        "sender_name": "Marketing Team",
        "sender_email": "marketing@example.com"
      }
    }
  ],
  "holdout_percentage": 5,
  "conversion_event_type": "purchase.completed",
  "attribution_window_days": 7,
  "tags": ["new-year", "promotion"]
}
```

**Success Response**: `201 Created`
```json
{
  "campaign": {
    "campaign_id": "cmp_2026010112345678",
    "organization_id": "org_abc123",
    "name": "New Year Promotion 2026",
    "description": "Promotional campaign for new year",
    "campaign_type": "scheduled",
    "status": "draft",
    "schedule_type": "one_time",
    "scheduled_at": "2026-01-01T09:00:00Z",
    "timezone": "America/New_York",
    "holdout_percentage": 5,
    "created_by": "usr_admin123",
    "created_at": "2026-01-15T10:00:00Z",
    "updated_at": "2026-01-15T10:00:00Z"
  },
  "message": "Campaign created successfully"
}
```

**Error Responses**:
- `400 Bad Request`: Missing required fields, invalid configuration
- `422 Validation Error`: Field validation failed
- `401 Unauthorized`: Invalid or missing authentication
- `403 Forbidden`: Insufficient permissions

---

### GET /api/v1/campaigns/{campaign_id}

**Success Response**: `200 OK`
```json
{
  "campaign": {
    "campaign_id": "cmp_2026010112345678",
    "organization_id": "org_abc123",
    "name": "New Year Promotion 2026",
    "status": "scheduled",
    "campaign_type": "scheduled",
    "schedule_type": "one_time",
    "scheduled_at": "2026-01-01T09:00:00Z",
    "timezone": "America/New_York",
    "audiences": [
      {
        "audience_id": "aud_123",
        "segment_type": "include",
        "segment_id": "seg_premium_users",
        "estimated_size": 45000
      }
    ],
    "variants": [
      {
        "variant_id": "var_default",
        "name": "Default",
        "allocation_percentage": 100,
        "channels": [...]
      }
    ],
    "metrics": {
      "sent": 0,
      "delivered": 0,
      "opened": 0,
      "clicked": 0,
      "converted": 0,
      "bounced": 0,
      "unsubscribed": 0
    },
    "created_at": "2026-01-15T10:00:00Z",
    "updated_at": "2026-01-15T10:00:00Z"
  }
}
```

**Error Responses**:
- `404 Not Found`: Campaign not found
- `401 Unauthorized`: Invalid authentication
- `403 Forbidden`: Not in same organization

---

### GET /api/v1/campaigns

**Query Parameters**:
- `status`: Filter by status (comma-separated: draft,scheduled,running)
- `type`: Filter by type (scheduled, triggered)
- `channel`: Filter by channel (email, sms, etc.)
- `search`: Search by name (prefix match)
- `created_after`: Filter by creation date
- `created_before`: Filter by creation date
- `scheduled_after`: Filter by scheduled date
- `scheduled_before`: Filter by scheduled date
- `tags`: Filter by tags (comma-separated)
- `sort_by`: Sort field (created_at, scheduled_at, name)
- `sort_order`: Sort order (asc, desc)
- `limit`: Page size (1-100, default 20)
- `offset`: Page offset (default 0)

**Success Response**: `200 OK`
```json
{
  "campaigns": [
    {
      "campaign_id": "cmp_123",
      "name": "New Year Promotion",
      "status": "scheduled",
      "campaign_type": "scheduled",
      "scheduled_at": "2026-01-01T09:00:00Z",
      "created_at": "2026-01-15T10:00:00Z"
    }
  ],
  "total": 150,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

---

### POST /api/v1/campaigns/{campaign_id}/schedule

**Request**: `application/json`
```json
{
  "scheduled_at": "2026-01-01T09:00:00Z",
  "timezone": "America/New_York"
}
```

**Success Response**: `200 OK`
```json
{
  "campaign": {
    "campaign_id": "cmp_123",
    "status": "scheduled",
    "scheduled_at": "2026-01-01T09:00:00Z",
    "task_id": "tsk_456"
  },
  "message": "Campaign scheduled successfully"
}
```

---

### POST /api/v1/campaigns/{campaign_id}/activate

**Success Response**: `200 OK`
```json
{
  "campaign": {
    "campaign_id": "cmp_123",
    "status": "active"
  },
  "message": "Campaign activated successfully"
}
```

---

### POST /api/v1/campaigns/{campaign_id}/pause

**Success Response**: `200 OK`
```json
{
  "campaign": {
    "campaign_id": "cmp_123",
    "status": "paused",
    "paused_at": "2026-01-01T12:00:00Z",
    "paused_by": "usr_admin"
  },
  "message": "Campaign paused successfully"
}
```

---

### POST /api/v1/campaigns/{campaign_id}/resume

**Success Response**: `200 OK`
```json
{
  "campaign": {
    "campaign_id": "cmp_123",
    "status": "running"
  },
  "message": "Campaign resumed successfully"
}
```

---

### POST /api/v1/campaigns/{campaign_id}/cancel

**Request**: `application/json`
```json
{
  "reason": "Strategy changed, launching new campaign instead"
}
```

**Success Response**: `200 OK`
```json
{
  "campaign": {
    "campaign_id": "cmp_123",
    "status": "cancelled",
    "cancelled_at": "2026-01-01T12:00:00Z",
    "cancelled_by": "usr_admin",
    "cancelled_reason": "Strategy changed, launching new campaign instead"
  },
  "message": "Campaign cancelled successfully"
}
```

---

### POST /api/v1/campaigns/{campaign_id}/clone

**Request**: `application/json`
```json
{
  "name": "New Year Promotion 2026 - Copy"
}
```

**Success Response**: `201 Created`
```json
{
  "campaign": {
    "campaign_id": "cmp_newid123",
    "name": "New Year Promotion 2026 - Copy",
    "status": "draft",
    "cloned_from_id": "cmp_123"
  },
  "message": "Campaign cloned successfully"
}
```

---

### GET /api/v1/campaigns/{campaign_id}/metrics

**Query Parameters**:
- `breakdown_by`: Dimensions to break down (variant, channel, segment)
- `execution_id`: Filter to specific execution

**Success Response**: `200 OK`
```json
{
  "campaign_id": "cmp_123",
  "metrics": {
    "total": {
      "sent": 45000,
      "delivered": 44100,
      "opened": 15000,
      "clicked": 3000,
      "converted": 500,
      "bounced": 900,
      "unsubscribed": 50,
      "delivery_rate": 0.98,
      "open_rate": 0.34,
      "click_rate": 0.068,
      "conversion_rate": 0.011,
      "bounce_rate": 0.02,
      "unsubscribe_rate": 0.001
    },
    "by_variant": {
      "var_a": {
        "sent": 22500,
        "opened": 8000,
        "open_rate": 0.36
      },
      "var_b": {
        "sent": 22500,
        "opened": 7000,
        "open_rate": 0.32
      }
    },
    "by_channel": {
      "email": {
        "sent": 40000,
        "delivered": 39200
      },
      "sms": {
        "sent": 5000,
        "delivered": 4900
      }
    }
  },
  "updated_at": "2026-01-01T12:00:00Z"
}
```

---

### POST /api/v1/campaigns/{campaign_id}/variants

**Request**: `application/json`
```json
{
  "name": "Variant B - Free Shipping",
  "allocation_percentage": 50,
  "channels": [
    {
      "channel_type": "email",
      "email_content": {
        "subject": "Free Shipping for You, {{first_name}}!",
        "body_html": "..."
      }
    }
  ]
}
```

**Success Response**: `201 Created`
```json
{
  "variant": {
    "variant_id": "var_newid",
    "name": "Variant B - Free Shipping",
    "allocation_percentage": 50,
    "created_at": "2026-01-15T10:00:00Z"
  },
  "message": "Variant created successfully"
}
```

---

### POST /api/v1/campaigns/{campaign_id}/audiences/estimate

**Success Response**: `200 OK`
```json
{
  "campaign_id": "cmp_123",
  "estimated_size": 50000,
  "by_segment": [
    {"segment_id": "seg_premium", "type": "include", "size": 35000},
    {"segment_id": "seg_active", "type": "include", "size": 45000}
  ],
  "after_exclusions": 48000,
  "after_holdout": 45600,
  "estimated_at": "2026-01-15T10:00:00Z"
}
```

---

### POST /api/v1/campaigns/{campaign_id}/preview

**Request**: `application/json`
```json
{
  "variant_id": "var_123",
  "channel_type": "email",
  "sample_user_id": "usr_456"
}
```

**Success Response**: `200 OK`
```json
{
  "campaign_id": "cmp_123",
  "variant_id": "var_123",
  "channel_type": "email",
  "rendered_content": {
    "subject": "Happy New Year, John!",
    "body_html": "<html><body>Dear John, special offer...</body></html>",
    "body_text": "Dear John, special offer..."
  },
  "sample_user": {
    "user_id": "usr_456",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com"
  }
}
```

---

## Event Contracts

### Events Published

#### campaign.created

**Published**: After campaign creation
**Subject**: `campaign.created`
**Payload**:
```json
{
  "event_type": "campaign.created",
  "source": "campaign_service",
  "timestamp": "2026-01-15T10:00:00Z",
  "data": {
    "campaign_id": "cmp_123",
    "organization_id": "org_abc",
    "name": "New Year Promotion",
    "campaign_type": "scheduled",
    "status": "draft",
    "created_by": "usr_admin"
  }
}
```

---

#### campaign.updated

**Published**: After campaign update
**Subject**: `campaign.updated`
**Payload**:
```json
{
  "event_type": "campaign.updated",
  "source": "campaign_service",
  "timestamp": "2026-01-15T10:00:00Z",
  "data": {
    "campaign_id": "cmp_123",
    "changed_fields": ["name", "scheduled_at"],
    "updated_by": "usr_admin"
  }
}
```

---

#### campaign.scheduled

**Published**: After campaign scheduled
**Subject**: `campaign.scheduled`
**Payload**:
```json
{
  "event_type": "campaign.scheduled",
  "source": "campaign_service",
  "timestamp": "2026-01-15T10:00:00Z",
  "data": {
    "campaign_id": "cmp_123",
    "scheduled_at": "2026-01-01T09:00:00Z",
    "task_id": "tsk_456"
  }
}
```

---

#### campaign.activated

**Published**: After triggered campaign activated
**Subject**: `campaign.activated`
**Payload**:
```json
{
  "event_type": "campaign.activated",
  "source": "campaign_service",
  "timestamp": "2026-01-15T10:00:00Z",
  "data": {
    "campaign_id": "cmp_123",
    "activated_at": "2026-01-15T10:00:00Z",
    "trigger_count": 2
  }
}
```

---

#### campaign.started

**Published**: When campaign execution begins
**Subject**: `campaign.started`
**Payload**:
```json
{
  "event_type": "campaign.started",
  "source": "campaign_service",
  "timestamp": "2026-01-01T09:00:00Z",
  "data": {
    "campaign_id": "cmp_123",
    "execution_id": "exe_789",
    "audience_size": 45000,
    "holdout_size": 2250
  }
}
```

---

#### campaign.paused

**Published**: When campaign paused
**Subject**: `campaign.paused`
**Payload**:
```json
{
  "event_type": "campaign.paused",
  "source": "campaign_service",
  "timestamp": "2026-01-01T12:00:00Z",
  "data": {
    "campaign_id": "cmp_123",
    "execution_id": "exe_789",
    "paused_by": "usr_admin",
    "messages_sent": 30000,
    "messages_remaining": 15000
  }
}
```

---

#### campaign.resumed

**Published**: When campaign resumed
**Subject**: `campaign.resumed`
**Payload**:
```json
{
  "event_type": "campaign.resumed",
  "source": "campaign_service",
  "timestamp": "2026-01-01T14:00:00Z",
  "data": {
    "campaign_id": "cmp_123",
    "execution_id": "exe_789",
    "resumed_by": "usr_admin",
    "messages_remaining": 15000
  }
}
```

---

#### campaign.completed

**Published**: When campaign execution finishes
**Subject**: `campaign.completed`
**Payload**:
```json
{
  "event_type": "campaign.completed",
  "source": "campaign_service",
  "timestamp": "2026-01-01T15:00:00Z",
  "data": {
    "campaign_id": "cmp_123",
    "execution_id": "exe_789",
    "total_sent": 45000,
    "total_delivered": 44100,
    "total_failed": 900,
    "duration_minutes": 360
  }
}
```

---

#### campaign.cancelled

**Published**: When campaign cancelled
**Subject**: `campaign.cancelled`
**Payload**:
```json
{
  "event_type": "campaign.cancelled",
  "source": "campaign_service",
  "timestamp": "2026-01-01T12:00:00Z",
  "data": {
    "campaign_id": "cmp_123",
    "cancelled_by": "usr_admin",
    "reason": "Strategy changed",
    "messages_sent_before_cancel": 15000
  }
}
```

---

#### campaign.message.queued

**Published**: When message queued for delivery
**Subject**: `campaign.message.queued`
**Payload**:
```json
{
  "event_type": "campaign.message.queued",
  "source": "campaign_service",
  "timestamp": "2026-01-01T09:00:01Z",
  "data": {
    "campaign_id": "cmp_123",
    "execution_id": "exe_789",
    "message_id": "msg_abc",
    "user_id": "usr_recipient",
    "channel_type": "email",
    "variant_id": "var_a"
  }
}
```

---

#### campaign.message.sent

**Published**: When message sent to provider
**Subject**: `campaign.message.sent`
**Payload**:
```json
{
  "event_type": "campaign.message.sent",
  "source": "campaign_service",
  "timestamp": "2026-01-01T09:00:02Z",
  "data": {
    "campaign_id": "cmp_123",
    "message_id": "msg_abc",
    "notification_id": "ntf_xyz",
    "provider_id": "prov_123"
  }
}
```

---

#### campaign.message.delivered

**Published**: When delivery confirmed
**Subject**: `campaign.message.delivered`
**Payload**:
```json
{
  "event_type": "campaign.message.delivered",
  "source": "campaign_service",
  "timestamp": "2026-01-01T09:00:05Z",
  "data": {
    "campaign_id": "cmp_123",
    "message_id": "msg_abc",
    "delivered_at": "2026-01-01T09:00:05Z"
  }
}
```

---

#### campaign.message.opened

**Published**: When message opened
**Subject**: `campaign.message.opened`
**Payload**:
```json
{
  "event_type": "campaign.message.opened",
  "source": "campaign_service",
  "timestamp": "2026-01-01T10:30:00Z",
  "data": {
    "campaign_id": "cmp_123",
    "message_id": "msg_abc",
    "opened_at": "2026-01-01T10:30:00Z",
    "user_agent": "Mozilla/5.0..."
  }
}
```

---

#### campaign.message.clicked

**Published**: When link clicked
**Subject**: `campaign.message.clicked`
**Payload**:
```json
{
  "event_type": "campaign.message.clicked",
  "source": "campaign_service",
  "timestamp": "2026-01-01T10:35:00Z",
  "data": {
    "campaign_id": "cmp_123",
    "message_id": "msg_abc",
    "link_id": "lnk_456",
    "link_url": "https://example.com/offer",
    "clicked_at": "2026-01-01T10:35:00Z"
  }
}
```

---

#### campaign.message.converted

**Published**: When conversion attributed
**Subject**: `campaign.message.converted`
**Payload**:
```json
{
  "event_type": "campaign.message.converted",
  "source": "campaign_service",
  "timestamp": "2026-01-02T14:00:00Z",
  "data": {
    "campaign_id": "cmp_123",
    "message_id": "msg_abc",
    "conversion_event": "purchase.completed",
    "conversion_value": 99.99,
    "attribution_model": "last_touch"
  }
}
```

---

#### campaign.message.bounced

**Published**: When message bounces
**Subject**: `campaign.message.bounced`
**Payload**:
```json
{
  "event_type": "campaign.message.bounced",
  "source": "campaign_service",
  "timestamp": "2026-01-01T09:00:10Z",
  "data": {
    "campaign_id": "cmp_123",
    "message_id": "msg_abc",
    "bounce_type": "hard",
    "reason": "Invalid email address"
  }
}
```

---

#### campaign.message.unsubscribed

**Published**: When user unsubscribes
**Subject**: `campaign.message.unsubscribed`
**Payload**:
```json
{
  "event_type": "campaign.message.unsubscribed",
  "source": "campaign_service",
  "timestamp": "2026-01-01T11:00:00Z",
  "data": {
    "campaign_id": "cmp_123",
    "message_id": "msg_abc",
    "user_id": "usr_recipient",
    "channel_type": "email",
    "reason": "No longer interested"
  }
}
```

---

#### campaign.metric.updated

**Published**: When metrics aggregated
**Subject**: `campaign.metric.updated`
**Payload**:
```json
{
  "event_type": "campaign.metric.updated",
  "source": "campaign_service",
  "timestamp": "2026-01-01T12:00:00Z",
  "data": {
    "campaign_id": "cmp_123",
    "metric_type": "delivered",
    "count": 44100,
    "rate": 0.98
  }
}
```

---

### Events Subscribed

| Subject | Source | Handler | Action |
|---------|--------|---------|--------|
| `user.created` | account_service | `handle_user_created` | Add to welcome campaign audiences |
| `user.deleted` | account_service | `handle_user_deleted` | Remove from all campaigns, GDPR cleanup |
| `user.preferences.updated` | account_service | `handle_preferences_updated` | Update channel availability |
| `subscription.created` | subscription_service | `handle_subscription_created` | Trigger onboarding campaigns |
| `subscription.upgraded` | subscription_service | `handle_subscription_upgraded` | Trigger upsell thank-you campaigns |
| `subscription.cancelled` | subscription_service | `handle_subscription_cancelled` | Trigger win-back campaigns |
| `order.completed` | order_service | `handle_order_completed` | Trigger post-purchase campaigns |
| `notification.delivered` | notification_service | `handle_notification_delivered` | Update message delivery status |
| `notification.failed` | notification_service | `handle_notification_failed` | Update message failure status |
| `notification.opened` | notification_service | `handle_notification_opened` | Update message open status |
| `notification.clicked` | notification_service | `handle_notification_clicked` | Update message click status |
| `task.executed` | task_service | `handle_task_executed` | Handle scheduled campaign execution |
| `event.stored` | event_service | `handle_event_stored` | Evaluate triggered campaign conditions |

---

## Performance SLAs

### Response Time Targets (p95)

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| Create Campaign | < 300ms | < 1s |
| Get Campaign | < 100ms | < 500ms |
| List Campaigns | < 200ms | < 1s |
| Update Campaign | < 300ms | < 1s |
| Schedule Campaign | < 500ms | < 2s |
| Activate Campaign | < 500ms | < 2s |
| Pause Campaign | < 200ms | < 1s |
| Resume Campaign | < 500ms | < 2s |
| Cancel Campaign | < 200ms | < 1s |
| Clone Campaign | < 500ms | < 2s |
| Get Metrics | < 300ms | < 1s |
| Estimate Audience | < 2s | < 5s |
| Preview Content | < 500ms | < 2s |

### Throughput Targets

| Metric | Target |
|--------|--------|
| Message throughput | 100,000 messages/minute/org |
| Campaign creation | 100 campaigns/minute |
| Metric updates | 10,000 updates/second |
| Trigger evaluations | 5,000 evaluations/second |

### Latency Targets

| Metric | Target |
|--------|--------|
| Campaign start latency | < 60 seconds from scheduled time |
| Trigger response latency | < 5 seconds from event |
| Metric update delay | < 5 seconds from event |
| Unsubscribe processing | < 10 seconds |

### Reliability Targets

| Metric | Target |
|--------|--------|
| Service availability | 99.9% |
| Message delivery guarantee | At-least-once |
| Data durability | Zero message loss |
| Metric accuracy | < 1% variance |

---

## Edge Cases

### EC-CAM-001: Concurrent Campaign Updates

**Scenario**: Multiple admins update same campaign simultaneously
**Expected**: Last update wins, version tracked
**Solution**: Optimistic concurrency with `updated_at` check

---

### EC-CAM-002: Audience Resolution Timeout

**Scenario**: isA_Data takes too long to resolve segment
**Expected**: Use cached segment if available, continue with warning
**Solution**: 5-minute cache TTL, timeout at 30 seconds, fallback to cache

---

### EC-CAM-003: Task Service Unavailable During Scheduling

**Scenario**: task_service unreachable when scheduling campaign
**Expected**: Retry with exponential backoff, fail after 3 attempts
**Solution**: Async task creation with retry queue

---

### EC-CAM-004: Trigger Evaluation Race Condition

**Scenario**: Same event triggers multiple campaigns simultaneously
**Expected**: All applicable campaigns fire independently
**Solution**: Stateless trigger evaluation, no cross-campaign locking

---

### EC-CAM-005: Message Delivery Partial Failure

**Scenario**: Some messages in batch fail, others succeed
**Expected**: Batch continues processing, statistics track both
**Solution**: Error isolation per message, continue batch

---

### EC-CAM-006: Variant Allocation Rounding

**Scenario**: 3 variants with 33.33% allocation each
**Expected**: Rounding handled gracefully, no user skipped
**Solution**: Use cumulative percentage, last variant catches remainder

---

### EC-CAM-007: Duplicate Conversion Events

**Scenario**: Same conversion event received multiple times
**Expected**: Single conversion attributed, duplicates ignored
**Solution**: Idempotency key on (user_id, campaign_id, conversion_event_id)

---

### EC-CAM-008: Quiet Hours Timezone Edge Case

**Scenario**: User timezone changes during campaign execution
**Expected**: Use timezone at message queue time
**Solution**: Store timezone with queued message, don't re-evaluate

---

### EC-CAM-009: Large Audience Memory Pressure

**Scenario**: Campaign with 10M+ audience members
**Expected**: Streaming processing, not full audience in memory
**Solution**: Batch audience resolution (10,000 at a time), cursor-based pagination

---

### EC-CAM-010: Rate Limit Exhaustion

**Scenario**: Campaign rate limit reached during execution
**Expected**: Messages queued, not failed
**Solution**: Rate limiter with queue, exponential retry

---

### EC-CAM-011: Provider Webhook Out of Order

**Scenario**: Delivered webhook arrives before sent webhook
**Expected**: Status updated correctly based on timestamp
**Solution**: Store all status updates, use latest timestamp per status

---

### EC-CAM-012: Template Variable Missing

**Scenario**: Template uses variable not in user profile
**Expected**: Variable replaced with empty string, message sent
**Solution**: Graceful degradation, log warning

---

### EC-CAM-013: Auto-Winner Tie

**Scenario**: Two variants have identical performance metrics
**Expected**: No winner selected automatically, manual decision required
**Solution**: Tie-breaker: require clear winner (5% difference minimum)

---

### EC-CAM-014: Holdout User Receives Message

**Scenario**: Bug allows holdout user to receive message
**Expected**: Message marked as error, excluded from metrics
**Solution**: Double-check holdout at queue time, validation in send path

---

### EC-CAM-015: Campaign Deleted During Execution

**Scenario**: Admin deletes campaign while running
**Expected**: Cannot delete running campaign
**Solution**: Soft delete only, require cancel/pause first

---

## Test Coverage Requirements

All tests MUST cover:

- ✅ Happy path (BR-CAM-XXX success scenarios)
- ✅ Validation errors (400, 422)
- ✅ Authorization failures (401, 403)
- ✅ Not found errors (404)
- ✅ Conflict errors (409) - invalid state transitions
- ✅ State transitions (valid and invalid)
- ✅ Event publishing (verify all events published correctly)
- ✅ Event subscription (verify handlers process correctly)
- ✅ Edge cases (EC-CAM-XXX scenarios)
- ✅ Performance within SLAs
- ✅ A/B testing scenarios (variant assignment, statistics)
- ✅ Throttling behavior (rate limits, quiet hours)
- ✅ Trigger evaluation (conditions, frequency limits)
- ✅ Conversion attribution (all models)
- ✅ Multi-channel delivery (eligibility, fallback)
- ✅ Audience resolution (caching, errors)

---

**Version**: 1.0.0
**Last Updated**: 2026-02-02
**Owner**: Marketing Platform Team
