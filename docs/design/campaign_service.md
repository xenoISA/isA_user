# Campaign Service - Design Document

## Overview

The Campaign Service is a high-performance marketing automation system designed to orchestrate multi-channel campaign delivery with advanced targeting, A/B testing, and real-time analytics. It integrates with isA_Data for audience segmentation, isA_Creative for content management, and notification_service for delivery.

---

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   Mobile App    │    │  Other Services │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │     API Gateway          │
                    └────────────┬────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │   Campaign Service       │
                    │   (FastAPI + PostgreSQL) │
                    │       Port: 8240         │
                    └────────────┬────────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           │                     │                     │
    ┌──────┴──────┐      ┌──────┴──────┐      ┌──────┴──────┐
    │    NATS     │      │  PostgreSQL │      │    Redis    │
    │ (Event Bus) │      │  (campaign) │      │  (Cache)    │
    └──────┬──────┘      └─────────────┘      └─────────────┘
           │
    ┌──────┴──────────────────────────────────────────┐
    │                                                  │
┌───┴────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────┴───┐
│ event  │  │ task   │  │notif.  │  │isA_Data│  │isA_    │
│service │  │service │  │service │  │        │  │Creative│
└────────┘  └────────┘  └────────┘  └────────┘  └────────┘
```

### Core Components

#### 1. API Layer (FastAPI)
- **Campaign Router**: `/api/v1/campaigns/*`
- **Audience Router**: `/api/v1/campaigns/{id}/audiences/*`
- **Variant Router**: `/api/v1/campaigns/{id}/variants/*`
- **Execution Router**: `/api/v1/campaigns/{id}/executions/*`
- **Metrics Router**: `/api/v1/campaigns/{id}/metrics/*`
- **Health Router**: `/health/*`

#### 2. Service Layer
- **CampaignService**: Campaign CRUD, lifecycle management
- **AudienceService**: Segment resolution, holdout management
- **VariantService**: A/B test variant management
- **ExecutionService**: Campaign execution orchestration
- **TriggerService**: Event trigger evaluation
- **MetricsService**: Metric aggregation and reporting
- **ThrottleService**: Rate limiting and scheduling

#### 3. Repository Layer
- **CampaignRepository**: Campaign CRUD operations
- **AudienceRepository**: Audience configuration storage
- **VariantRepository**: Variant configuration storage
- **ExecutionRepository**: Execution history storage
- **MessageRepository**: Individual message tracking
- **MetricsRepository**: Metric aggregation storage

#### 4. External Integrations
- **IntelligentQueryClient**: isA_Data segment resolution
- **User360Client**: isA_Data user profile enrichment
- **CreativeClient**: isA_Creative template management
- **NotificationClient**: notification_service delivery
- **TaskClient**: task_service scheduling
- **EventClient**: event_service trigger subscription

---

## Database Schema

### Schema: campaign

#### 1. campaigns (Core Campaign Entity)
```sql
CREATE TABLE campaign.campaigns (
    id SERIAL PRIMARY KEY,
    campaign_id VARCHAR(50) NOT NULL UNIQUE,
    organization_id VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    campaign_type VARCHAR(20) NOT NULL, -- scheduled, triggered
    status VARCHAR(20) NOT NULL DEFAULT 'draft', -- draft, scheduled, active, running, paused, completed, cancelled

    -- Scheduling Configuration
    schedule_type VARCHAR(20), -- one_time, recurring
    scheduled_at TIMESTAMPTZ,
    cron_expression VARCHAR(100),
    timezone VARCHAR(50) DEFAULT 'UTC',

    -- Throttling Configuration
    throttle_per_minute INTEGER,
    throttle_per_hour INTEGER,
    send_window_start INTEGER, -- Hour (0-23)
    send_window_end INTEGER,   -- Hour (0-23)
    exclude_weekends BOOLEAN DEFAULT FALSE,

    -- A/B Testing Configuration
    enable_ab_testing BOOLEAN DEFAULT FALSE,
    auto_winner_enabled BOOLEAN DEFAULT FALSE,
    auto_winner_metric VARCHAR(50), -- open_rate, click_rate, conversion_rate
    auto_winner_confidence DECIMAL(5,2) DEFAULT 0.95,
    auto_winner_min_sample INTEGER DEFAULT 1000,
    winner_variant_id VARCHAR(50),

    -- Conversion Tracking
    conversion_event_type VARCHAR(100),
    attribution_window_days INTEGER DEFAULT 7,
    attribution_model VARCHAR(20) DEFAULT 'last_touch', -- first_touch, last_touch, linear

    -- Holdout Configuration
    holdout_percentage DECIMAL(5,2) DEFAULT 0,

    -- Task Service Integration
    task_id VARCHAR(50),

    -- Metadata
    tags JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Audit
    created_by VARCHAR(50) NOT NULL,
    updated_by VARCHAR(50),
    paused_by VARCHAR(50),
    paused_at TIMESTAMPTZ,
    cancelled_by VARCHAR(50),
    cancelled_at TIMESTAMPTZ,
    cancelled_reason TEXT,
    cloned_from_id VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT valid_status CHECK (status IN ('draft', 'scheduled', 'active', 'running', 'paused', 'completed', 'cancelled')),
    CONSTRAINT valid_campaign_type CHECK (campaign_type IN ('scheduled', 'triggered')),
    CONSTRAINT valid_schedule_type CHECK (schedule_type IS NULL OR schedule_type IN ('one_time', 'recurring')),
    CONSTRAINT valid_holdout CHECK (holdout_percentage >= 0 AND holdout_percentage <= 20)
);

CREATE INDEX idx_campaigns_org ON campaign.campaigns(organization_id);
CREATE INDEX idx_campaigns_status ON campaign.campaigns(status);
CREATE INDEX idx_campaigns_type ON campaign.campaigns(campaign_type);
CREATE INDEX idx_campaigns_scheduled_at ON campaign.campaigns(scheduled_at) WHERE scheduled_at IS NOT NULL;
CREATE INDEX idx_campaigns_deleted ON campaign.campaigns(deleted_at) WHERE deleted_at IS NULL;
```

#### 2. campaign_audiences (Audience Segments)
```sql
CREATE TABLE campaign.campaign_audiences (
    id SERIAL PRIMARY KEY,
    audience_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL REFERENCES campaign.campaigns(campaign_id),

    -- Segment Configuration
    segment_type VARCHAR(20) NOT NULL, -- include, exclude
    segment_id VARCHAR(100), -- Reference to isA_Data segment
    segment_query JSONB, -- Inline segment query

    -- Metadata
    name VARCHAR(255),
    estimated_size INTEGER,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_segment_type CHECK (segment_type IN ('include', 'exclude'))
);

CREATE INDEX idx_audiences_campaign ON campaign.campaign_audiences(campaign_id);
```

#### 3. campaign_variants (A/B Test Variants)
```sql
CREATE TABLE campaign.campaign_variants (
    id SERIAL PRIMARY KEY,
    variant_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL REFERENCES campaign.campaigns(campaign_id),

    -- Variant Configuration
    name VARCHAR(100) NOT NULL,
    description TEXT,
    allocation_percentage DECIMAL(5,2) NOT NULL,
    is_control BOOLEAN DEFAULT FALSE, -- Control variant (no message sent)

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_allocation CHECK (allocation_percentage >= 0 AND allocation_percentage <= 100)
);

CREATE INDEX idx_variants_campaign ON campaign.campaign_variants(campaign_id);
```

#### 4. campaign_channels (Channel Content)
```sql
CREATE TABLE campaign.campaign_channels (
    id SERIAL PRIMARY KEY,
    channel_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL REFERENCES campaign.campaigns(campaign_id),
    variant_id VARCHAR(50) REFERENCES campaign.campaign_variants(variant_id),

    -- Channel Configuration
    channel_type VARCHAR(20) NOT NULL, -- email, sms, whatsapp, in_app, webhook
    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0, -- Fallback order

    -- Email Configuration
    email_subject VARCHAR(255),
    email_body_html TEXT,
    email_body_text TEXT,
    email_sender_name VARCHAR(100),
    email_sender_email VARCHAR(255),
    email_reply_to VARCHAR(255),

    -- SMS Configuration
    sms_body VARCHAR(160),

    -- WhatsApp Configuration
    whatsapp_body VARCHAR(1600),
    whatsapp_template_id VARCHAR(100),

    -- In-App Configuration
    in_app_title VARCHAR(255),
    in_app_body TEXT,
    in_app_action_url TEXT,
    in_app_icon VARCHAR(255),

    -- Webhook Configuration
    webhook_url TEXT,
    webhook_method VARCHAR(10) DEFAULT 'POST',
    webhook_headers JSONB DEFAULT '{}'::jsonb,
    webhook_payload_template TEXT,

    -- Template Reference
    template_id VARCHAR(100), -- Reference to isA_Creative template

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_channel_type CHECK (channel_type IN ('email', 'sms', 'whatsapp', 'in_app', 'webhook'))
);

CREATE INDEX idx_channels_campaign ON campaign.campaign_channels(campaign_id);
CREATE INDEX idx_channels_variant ON campaign.campaign_channels(variant_id);
```

#### 5. campaign_triggers (Event Triggers)
```sql
CREATE TABLE campaign.campaign_triggers (
    id SERIAL PRIMARY KEY,
    trigger_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL REFERENCES campaign.campaigns(campaign_id),

    -- Trigger Configuration
    event_type VARCHAR(100) NOT NULL,
    conditions JSONB DEFAULT '[]'::jsonb, -- [{field, operator, value}]
    delay_minutes INTEGER DEFAULT 0,
    delay_days INTEGER DEFAULT 0,

    -- Frequency Limiting
    frequency_limit INTEGER DEFAULT 1,
    frequency_window_hours INTEGER DEFAULT 24,

    -- Quiet Hours
    quiet_hours_start INTEGER, -- Hour (0-23)
    quiet_hours_end INTEGER,   -- Hour (0-23)
    quiet_hours_timezone VARCHAR(50) DEFAULT 'user_local',

    -- State
    enabled BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_triggers_campaign ON campaign.campaign_triggers(campaign_id);
CREATE INDEX idx_triggers_event_type ON campaign.campaign_triggers(event_type);
CREATE INDEX idx_triggers_enabled ON campaign.campaign_triggers(enabled) WHERE enabled = TRUE;
```

#### 6. campaign_executions (Execution History)
```sql
CREATE TABLE campaign.campaign_executions (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL REFERENCES campaign.campaigns(campaign_id),

    -- Execution Configuration
    execution_type VARCHAR(20) NOT NULL, -- scheduled, triggered, manual
    trigger_event_id VARCHAR(50), -- For triggered executions

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, running, paused, completed, failed, cancelled

    -- Audience
    total_audience_size INTEGER DEFAULT 0,
    holdout_size INTEGER DEFAULT 0,

    -- Progress
    messages_queued INTEGER DEFAULT 0,
    messages_sent INTEGER DEFAULT 0,
    messages_delivered INTEGER DEFAULT 0,
    messages_failed INTEGER DEFAULT 0,

    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    paused_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_executions_campaign ON campaign.campaign_executions(campaign_id);
CREATE INDEX idx_executions_status ON campaign.campaign_executions(status);
CREATE INDEX idx_executions_started ON campaign.campaign_executions(started_at);
```

#### 7. campaign_messages (Individual Messages)
```sql
CREATE TABLE campaign.campaign_messages (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL,
    execution_id VARCHAR(50) NOT NULL,
    variant_id VARCHAR(50),

    -- Recipient
    user_id VARCHAR(50) NOT NULL,
    channel_type VARCHAR(20) NOT NULL,
    recipient_address VARCHAR(255), -- email, phone, etc.

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'queued', -- queued, sent, delivered, opened, clicked, bounced, failed, unsubscribed

    -- Tracking
    notification_id VARCHAR(50), -- Reference to notification_service
    provider_message_id VARCHAR(100),

    -- Timestamps
    queued_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    bounced_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    unsubscribed_at TIMESTAMPTZ,

    -- Error Tracking
    error_message TEXT,
    bounce_type VARCHAR(20), -- hard, soft

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb
) PARTITION BY RANGE (queued_at);

-- Create monthly partitions
CREATE TABLE campaign.campaign_messages_2026_01 PARTITION OF campaign.campaign_messages
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE campaign.campaign_messages_2026_02 PARTITION OF campaign.campaign_messages
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE INDEX idx_messages_campaign ON campaign.campaign_messages(campaign_id);
CREATE INDEX idx_messages_execution ON campaign.campaign_messages(execution_id);
CREATE INDEX idx_messages_user ON campaign.campaign_messages(user_id);
CREATE INDEX idx_messages_status ON campaign.campaign_messages(status);
```

#### 8. campaign_metrics (Aggregated Metrics)
```sql
CREATE TABLE campaign.campaign_metrics (
    id SERIAL PRIMARY KEY,
    metric_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL,
    execution_id VARCHAR(50),
    variant_id VARCHAR(50),
    channel_type VARCHAR(20),
    segment_id VARCHAR(50),

    -- Metric Type
    metric_type VARCHAR(50) NOT NULL, -- sent, delivered, opened, clicked, converted, bounced, unsubscribed

    -- Values
    count INTEGER DEFAULT 0,
    rate DECIMAL(10,6), -- Calculated rate (e.g., open_rate = opened/delivered)
    value DECIMAL(15,2), -- For conversion value

    -- Time Bucket (for time-series metrics)
    bucket_start TIMESTAMPTZ,
    bucket_end TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_metrics_campaign ON campaign.campaign_metrics(campaign_id);
CREATE INDEX idx_metrics_execution ON campaign.campaign_metrics(execution_id);
CREATE INDEX idx_metrics_type ON campaign.campaign_metrics(metric_type);
CREATE INDEX idx_metrics_bucket ON campaign.campaign_metrics(bucket_start, bucket_end);
```

#### 9. campaign_conversions (Conversion Attribution)
```sql
CREATE TABLE campaign.campaign_conversions (
    id SERIAL PRIMARY KEY,
    conversion_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL,
    execution_id VARCHAR(50),
    message_id VARCHAR(50),

    -- User
    user_id VARCHAR(50) NOT NULL,

    -- Conversion Details
    conversion_event_type VARCHAR(100) NOT NULL,
    conversion_event_id VARCHAR(50),
    conversion_value DECIMAL(15,2),

    -- Attribution
    attribution_model VARCHAR(20) NOT NULL,
    attribution_weight DECIMAL(5,4) DEFAULT 1.0, -- For linear attribution

    -- Timestamps
    converted_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversions_campaign ON campaign.campaign_conversions(campaign_id);
CREATE INDEX idx_conversions_user ON campaign.campaign_conversions(user_id);
CREATE INDEX idx_conversions_converted ON campaign.campaign_conversions(converted_at);
```

#### 10. campaign_unsubscribes (Unsubscribe Tracking)
```sql
CREATE TABLE campaign.campaign_unsubscribes (
    id SERIAL PRIMARY KEY,
    unsubscribe_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL,
    message_id VARCHAR(50),

    -- User
    user_id VARCHAR(50) NOT NULL,

    -- Channel
    channel_type VARCHAR(20) NOT NULL,

    -- Details
    reason VARCHAR(255),
    source VARCHAR(50) DEFAULT 'link', -- link, reply, complaint

    -- Timestamps
    unsubscribed_at TIMESTAMPTZ DEFAULT NOW(),
    synced_to_account_at TIMESTAMPTZ
);

CREATE INDEX idx_unsubscribes_campaign ON campaign.campaign_unsubscribes(campaign_id);
CREATE INDEX idx_unsubscribes_user ON campaign.campaign_unsubscribes(user_id);
```

#### 11. campaign_trigger_history (Trigger Execution History)
```sql
CREATE TABLE campaign.campaign_trigger_history (
    id SERIAL PRIMARY KEY,
    history_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL,
    trigger_id VARCHAR(50) NOT NULL,

    -- Event Details
    event_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    user_id VARCHAR(50) NOT NULL,

    -- Result
    triggered BOOLEAN NOT NULL,
    skip_reason VARCHAR(100), -- frequency_limit, quiet_hours, not_in_segment, already_triggered

    -- Execution Reference
    execution_id VARCHAR(50),

    -- Timestamps
    evaluated_at TIMESTAMPTZ DEFAULT NOW(),
    scheduled_send_at TIMESTAMPTZ
);

CREATE INDEX idx_trigger_history_campaign ON campaign.campaign_trigger_history(campaign_id);
CREATE INDEX idx_trigger_history_user ON campaign.campaign_trigger_history(user_id);
CREATE INDEX idx_trigger_history_evaluated ON campaign.campaign_trigger_history(evaluated_at);
```

---

## API Design

### Core Endpoints

#### 1. Create Campaign
```http
POST /api/v1/campaigns
Content-Type: application/json
Authorization: Bearer {token}

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
    }
  ],
  "channels": [
    {
      "channel_type": "email",
      "email_subject": "Happy New Year, {{first_name}}!",
      "email_body_html": "<html>...</html>"
    }
  ],
  "holdout_percentage": 5
}
```

**Response**: `201 Created`
```json
{
  "campaign": {
    "campaign_id": "cmp_2026010112345678",
    "name": "New Year Promotion 2026",
    "status": "draft",
    "campaign_type": "scheduled",
    "created_at": "2026-01-15T10:00:00Z"
  },
  "message": "Campaign created successfully"
}
```

#### 2. Get Campaign
```http
GET /api/v1/campaigns/{campaign_id}
Authorization: Bearer {token}
```

**Response**: `200 OK`
```json
{
  "campaign": {
    "campaign_id": "cmp_2026010112345678",
    "name": "New Year Promotion 2026",
    "status": "scheduled",
    "campaign_type": "scheduled",
    "schedule_type": "one_time",
    "scheduled_at": "2026-01-01T09:00:00Z",
    "audiences": [...],
    "channels": [...],
    "variants": [...],
    "metrics": {
      "total_audience": 50000,
      "sent": 0,
      "delivered": 0,
      "opened": 0,
      "clicked": 0
    }
  }
}
```

#### 3. List Campaigns
```http
GET /api/v1/campaigns?status=running&type=scheduled&limit=20&offset=0
Authorization: Bearer {token}
```

**Response**: `200 OK`
```json
{
  "campaigns": [...],
  "total": 150,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

#### 4. Update Campaign
```http
PATCH /api/v1/campaigns/{campaign_id}
Content-Type: application/json
Authorization: Bearer {token}

{
  "name": "New Year Promotion 2026 - Updated",
  "scheduled_at": "2026-01-01T10:00:00Z"
}
```

#### 5. Schedule Campaign
```http
POST /api/v1/campaigns/{campaign_id}/schedule
Content-Type: application/json
Authorization: Bearer {token}

{
  "scheduled_at": "2026-01-01T09:00:00Z"
}
```

#### 6. Activate Triggered Campaign
```http
POST /api/v1/campaigns/{campaign_id}/activate
Authorization: Bearer {token}
```

#### 7. Pause Campaign
```http
POST /api/v1/campaigns/{campaign_id}/pause
Authorization: Bearer {token}
```

#### 8. Resume Campaign
```http
POST /api/v1/campaigns/{campaign_id}/resume
Authorization: Bearer {token}
```

#### 9. Cancel Campaign
```http
POST /api/v1/campaigns/{campaign_id}/cancel
Content-Type: application/json
Authorization: Bearer {token}

{
  "reason": "Strategy changed"
}
```

#### 10. Clone Campaign
```http
POST /api/v1/campaigns/{campaign_id}/clone
Content-Type: application/json
Authorization: Bearer {token}

{
  "name": "New Year Promotion 2026 - Copy"
}
```

#### 11. Get Campaign Metrics
```http
GET /api/v1/campaigns/{campaign_id}/metrics?breakdown_by=variant,channel
Authorization: Bearer {token}
```

**Response**: `200 OK`
```json
{
  "campaign_id": "cmp_2026010112345678",
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
      "conversion_rate": 0.011
    },
    "by_variant": {...},
    "by_channel": {...}
  },
  "updated_at": "2026-01-01T12:00:00Z"
}
```

#### 12. Add Campaign Variant
```http
POST /api/v1/campaigns/{campaign_id}/variants
Content-Type: application/json
Authorization: Bearer {token}

{
  "name": "Variant B - Free Shipping",
  "allocation_percentage": 50,
  "channels": [
    {
      "channel_type": "email",
      "email_subject": "Free Shipping for You, {{first_name}}!"
    }
  ]
}
```

#### 13. Estimate Audience Size
```http
POST /api/v1/campaigns/{campaign_id}/audiences/estimate
Authorization: Bearer {token}
```

**Response**: `200 OK`
```json
{
  "estimated_size": 50000,
  "by_segment": [
    {"segment_id": "seg_premium", "size": 35000},
    {"segment_id": "seg_active", "size": 45000}
  ],
  "after_exclusions": 48000,
  "after_holdout": 45600,
  "estimated_at": "2026-01-15T10:00:00Z"
}
```

#### 14. Preview Content
```http
POST /api/v1/campaigns/{campaign_id}/preview
Content-Type: application/json
Authorization: Bearer {token}

{
  "variant_id": "var_123",
  "channel_type": "email",
  "sample_user_id": "usr_456"
}
```

---

## Service Implementation

### 1. CampaignService

#### Core Methods
```python
class CampaignService:
    async def create_campaign(self, request: CampaignCreateRequest) -> Campaign
    async def get_campaign(self, campaign_id: str) -> Campaign
    async def update_campaign(self, campaign_id: str, request: CampaignUpdateRequest) -> Campaign
    async def delete_campaign(self, campaign_id: str) -> bool
    async def list_campaigns(self, query: CampaignQueryRequest) -> CampaignListResponse
    async def clone_campaign(self, campaign_id: str, new_name: str) -> Campaign

    # Lifecycle
    async def schedule_campaign(self, campaign_id: str, scheduled_at: datetime) -> Campaign
    async def activate_campaign(self, campaign_id: str) -> Campaign
    async def pause_campaign(self, campaign_id: str) -> Campaign
    async def resume_campaign(self, campaign_id: str) -> Campaign
    async def cancel_campaign(self, campaign_id: str, reason: str) -> Campaign
```

### 2. ExecutionService

#### Core Methods
```python
class ExecutionService:
    async def start_execution(self, campaign_id: str, trigger_event: Optional[Event] = None) -> Execution
    async def process_execution(self, execution_id: str) -> None
    async def pause_execution(self, execution_id: str) -> None
    async def resume_execution(self, execution_id: str) -> None
    async def complete_execution(self, execution_id: str) -> None

    # Message Processing
    async def queue_messages(self, execution_id: str, user_ids: List[str]) -> int
    async def send_message(self, message_id: str) -> bool
    async def handle_delivery_status(self, message_id: str, status: str) -> None
```

### 3. TriggerService

#### Core Methods
```python
class TriggerService:
    async def evaluate_trigger(self, trigger: CampaignTrigger, event: Event) -> bool
    async def check_frequency_limit(self, campaign_id: str, user_id: str) -> bool
    async def check_quiet_hours(self, user_id: str, quiet_hours_config: dict) -> bool
    async def schedule_triggered_send(self, campaign_id: str, user_id: str, delay: timedelta) -> None
```

### 4. AudienceService

#### Core Methods
```python
class AudienceService:
    async def resolve_audience(self, campaign_id: str) -> List[str]
    async def estimate_audience_size(self, campaign_id: str) -> AudienceEstimate
    async def apply_holdout(self, user_ids: List[str], holdout_percentage: float, campaign_id: str) -> Tuple[List[str], List[str]]
    async def check_user_eligibility(self, user_id: str, campaign_id: str) -> bool
```

### 5. MetricsService

#### Core Methods
```python
class MetricsService:
    async def record_metric(self, campaign_id: str, metric_type: str, count: int = 1) -> None
    async def get_campaign_metrics(self, campaign_id: str, breakdown_by: List[str] = None) -> CampaignMetrics
    async def calculate_rates(self, campaign_id: str) -> Dict[str, float]
    async def calculate_statistical_significance(self, campaign_id: str) -> VariantSignificance
    async def get_metrics_time_series(self, campaign_id: str, interval: str) -> List[MetricsBucket]
```

---

## Event System

### NATS Events

#### Events Published

| Event | Subject | Trigger | Payload |
|-------|---------|---------|---------|
| `campaign.created` | `campaign.created` | Campaign created | campaign_id, name, type, status, created_by, organization_id |
| `campaign.updated` | `campaign.updated` | Campaign modified | campaign_id, changed_fields, updated_by |
| `campaign.scheduled` | `campaign.scheduled` | Campaign scheduled | campaign_id, scheduled_at, task_id |
| `campaign.activated` | `campaign.activated` | Triggered campaign activated | campaign_id, activated_at |
| `campaign.started` | `campaign.started` | Execution started | campaign_id, execution_id, audience_size |
| `campaign.paused` | `campaign.paused` | Campaign paused | campaign_id, paused_by, messages_sent |
| `campaign.resumed` | `campaign.resumed` | Campaign resumed | campaign_id, resumed_by |
| `campaign.completed` | `campaign.completed` | Campaign completed | campaign_id, execution_id, total_sent, total_delivered |
| `campaign.cancelled` | `campaign.cancelled` | Campaign cancelled | campaign_id, cancelled_by, reason |
| `campaign.message.queued` | `campaign.message.queued` | Message queued | campaign_id, message_id, user_id, channel |
| `campaign.message.sent` | `campaign.message.sent` | Message sent | campaign_id, message_id, notification_id |
| `campaign.message.delivered` | `campaign.message.delivered` | Message delivered | campaign_id, message_id, delivered_at |
| `campaign.message.opened` | `campaign.message.opened` | Message opened | campaign_id, message_id, opened_at |
| `campaign.message.clicked` | `campaign.message.clicked` | Link clicked | campaign_id, message_id, link_url, clicked_at |
| `campaign.message.converted` | `campaign.message.converted` | Conversion recorded | campaign_id, message_id, conversion_event, value |
| `campaign.message.bounced` | `campaign.message.bounced` | Message bounced | campaign_id, message_id, bounce_type, reason |
| `campaign.message.unsubscribed` | `campaign.message.unsubscribed` | User unsubscribed | campaign_id, message_id, user_id |
| `campaign.metric.updated` | `campaign.metric.updated` | Metrics updated | campaign_id, metric_type, count, rate |

#### Events Subscribed

| Subject | Source | Handler |
|---------|--------|---------|
| `user.created` | account_service | `handle_user_created` - Add to welcome audiences |
| `user.deleted` | account_service | `handle_user_deleted` - GDPR cleanup |
| `user.preferences.updated` | account_service | `handle_preferences_updated` - Update eligibility |
| `notification.delivered` | notification_service | `handle_notification_delivered` - Update message status |
| `notification.failed` | notification_service | `handle_notification_failed` - Update message status |
| `notification.opened` | notification_service | `handle_notification_opened` - Update message status |
| `notification.clicked` | notification_service | `handle_notification_clicked` - Update message status |
| `task.executed` | task_service | `handle_task_executed` - Start scheduled campaign |
| `event.stored` | event_service | `handle_event_stored` - Evaluate triggers |

---

## Sequence Diagrams

### 1. Scheduled Campaign Execution

```
┌─────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐  ┌────────────┐  ┌──────────────┐
│task_svc │  │campaign_svc│  │isA_Data    │  │user_360  │  │notif_svc   │  │  NATS        │
└────┬────┘  └─────┬──────┘  └─────┬──────┘  └────┬─────┘  └─────┬──────┘  └──────┬───────┘
     │             │               │              │              │                │
     │ task.executed               │              │              │                │
     │────────────>│               │              │              │                │
     │             │               │              │              │                │
     │             │ resolve_audience             │              │                │
     │             │──────────────>│              │              │                │
     │             │               │              │              │                │
     │             │<──────────────│              │              │                │
     │             │ user_ids[]    │              │              │                │
     │             │               │              │              │                │
     │             │               │ get_user_profile            │                │
     │             │               │ ─────────────>│             │                │
     │             │               │              │              │                │
     │             │               │<─────────────│              │                │
     │             │               │ user_profile │              │                │
     │             │               │              │              │                │
     │             │ render_template              │              │                │
     │             │──────────────────────────────┼──────────────>│               │
     │             │                              │              │                │
     │             │<──────────────────────────────────────────────               │
     │             │ rendered_content             │              │                │
     │             │               │              │              │                │
     │             │                              │ send_notification             │
     │             │──────────────────────────────┼──────────────>│               │
     │             │               │              │              │                │
     │             │<──────────────────────────────────────────────               │
     │             │ notification_id              │              │                │
     │             │               │              │              │                │
     │             │               │              │              │ campaign.message.sent
     │             │──────────────────────────────┼──────────────┼──────────────>│
     │             │               │              │              │                │
```

### 2. Triggered Campaign Execution

```
┌──────────┐  ┌────────────┐  ┌────────────┐  ┌──────────────┐
│event_svc │  │campaign_svc│  │isA_Data    │  │  NATS        │
└────┬─────┘  └─────┬──────┘  └─────┬──────┘  └──────┬───────┘
     │              │               │                │
     │ event.stored │               │                │
     │─────────────>│               │                │
     │              │               │                │
     │              │ evaluate_triggers              │
     │              │ (check conditions)             │
     │              │               │                │
     │              │ check_frequency_limit          │
     │              │ (user not triggered recently)  │
     │              │               │                │
     │              │ check_user_in_segment          │
     │              │──────────────>│                │
     │              │               │                │
     │              │<──────────────│                │
     │              │ is_in_segment │                │
     │              │               │                │
     │              │ schedule_send │                │
     │              │ (apply delay) │                │
     │              │               │                │
     │              │ ... (same as scheduled flow)   │
     │              │               │                │
```

---

## Integration Patterns

### 1. isA_Data Integration

```python
class IntelligentQueryClient:
    async def resolve_segment(self, segment_id: str) -> List[str]:
        """Resolve segment to user IDs"""
        response = await self.http_client.post(
            f"{self.base_url}/api/v1/segments/{segment_id}/resolve"
        )
        return response.json()["user_ids"]

    async def estimate_segment_size(self, segment_id: str) -> int:
        """Estimate segment size without full resolution"""
        response = await self.http_client.get(
            f"{self.base_url}/api/v1/segments/{segment_id}/estimate"
        )
        return response.json()["estimated_size"]

class User360Client:
    async def get_user_profile(self, user_id: str) -> UserProfile:
        """Get user profile for personalization"""
        response = await self.http_client.get(
            f"{self.base_url}/api/v1/users/{user_id}/profile"
        )
        return UserProfile(**response.json())

    async def get_user_profiles_batch(self, user_ids: List[str]) -> Dict[str, UserProfile]:
        """Batch get user profiles"""
        response = await self.http_client.post(
            f"{self.base_url}/api/v1/users/profiles/batch",
            json={"user_ids": user_ids}
        )
        return {p["user_id"]: UserProfile(**p) for p in response.json()["profiles"]}
```

### 2. Task Service Integration

```python
class TaskServiceClient:
    async def schedule_campaign(self, campaign_id: str, scheduled_at: datetime) -> str:
        """Schedule campaign execution"""
        response = await self.http_client.post(
            f"{self.base_url}/api/v1/tasks",
            json={
                "task_type": "campaign_execution",
                "name": f"Campaign Execution: {campaign_id}",
                "scheduled_at": scheduled_at.isoformat(),
                "config": {
                    "campaign_id": campaign_id,
                    "callback_subject": "task.executed.campaign"
                }
            }
        )
        return response.json()["task_id"]

    async def cancel_scheduled_task(self, task_id: str) -> bool:
        """Cancel scheduled campaign execution"""
        response = await self.http_client.delete(
            f"{self.base_url}/api/v1/tasks/{task_id}"
        )
        return response.status_code == 200
```

### 3. Notification Service Integration

```python
class NotificationServiceClient:
    async def send_campaign_message(
        self,
        channel_type: str,
        recipient: str,
        content: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> str:
        """Send campaign message via notification service"""
        response = await self.http_client.post(
            f"{self.base_url}/api/v1/notifications/send",
            json={
                "type": channel_type,
                "recipient_email" if channel_type == "email" else "recipient_phone": recipient,
                "subject": content.get("subject"),
                "content": content.get("body_text"),
                "html_content": content.get("body_html"),
                "metadata": {
                    **metadata,
                    "source": "campaign_service",
                    "campaign_id": metadata.get("campaign_id"),
                    "message_id": metadata.get("message_id")
                }
            }
        )
        return response.json()["notification"]["notification_id"]
```

---

## Performance Optimization

### 1. Audience Resolution Caching

```python
# Cache segment resolution for 5 minutes
SEGMENT_CACHE_TTL = 300

async def resolve_audience_cached(self, campaign_id: str) -> List[str]:
    cache_key = f"campaign:audience:{campaign_id}"

    cached = await self.redis.get(cache_key)
    if cached:
        return json.loads(cached)

    user_ids = await self._resolve_audience_from_isa_data(campaign_id)
    await self.redis.setex(cache_key, SEGMENT_CACHE_TTL, json.dumps(user_ids))

    return user_ids
```

### 2. Batch Message Processing

```python
async def process_messages_batch(self, messages: List[CampaignMessage], batch_size: int = 100):
    """Process messages in batches for efficiency"""
    for batch in chunked(messages, batch_size):
        # Batch fetch user profiles
        user_ids = [m.user_id for m in batch]
        profiles = await self.user_360_client.get_user_profiles_batch(user_ids)

        # Process batch
        tasks = [
            self.send_message(message, profiles.get(message.user_id))
            for message in batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle results
        for message, result in zip(batch, results):
            if isinstance(result, Exception):
                await self.handle_send_failure(message, result)
```

### 3. Metrics Aggregation

```python
async def aggregate_metrics_periodically(self, interval_seconds: int = 60):
    """Aggregate metrics periodically to reduce query load"""
    while True:
        try:
            # Get pending metric updates from Redis
            pending = await self.redis.lrange("campaign:metrics:pending", 0, -1)
            await self.redis.delete("campaign:metrics:pending")

            # Aggregate by campaign_id, metric_type
            aggregated = defaultdict(lambda: defaultdict(int))
            for item in pending:
                data = json.loads(item)
                key = (data["campaign_id"], data["execution_id"], data["metric_type"])
                aggregated[key]["count"] += 1

            # Batch update database
            for (campaign_id, execution_id, metric_type), values in aggregated.items():
                await self.metrics_repository.increment_metric(
                    campaign_id, execution_id, metric_type, values["count"]
                )
        except Exception as e:
            logger.error(f"Error aggregating metrics: {e}")

        await asyncio.sleep(interval_seconds)
```

---

## Security

### 1. Authorization

```python
class CampaignAuthorizationMiddleware:
    async def check_campaign_access(self, user: User, campaign_id: str, action: str) -> bool:
        """Check if user can perform action on campaign"""
        campaign = await self.campaign_repository.get_campaign(campaign_id)
        if not campaign:
            return False

        # Check organization membership
        if campaign.organization_id != user.organization_id:
            return False

        # Check role permissions
        permissions = self.get_permissions_for_role(user.role)
        return action in permissions.get("campaign", [])
```

### 2. Rate Limiting

```python
RATE_LIMITS = {
    "create_campaign": "100/hour",
    "update_campaign": "200/hour",
    "list_campaigns": "1000/hour",
    "get_metrics": "500/hour"
}
```

### 3. Input Validation

```python
class CampaignCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    campaign_type: CampaignType
    schedule_type: Optional[ScheduleType] = None
    scheduled_at: Optional[datetime] = None

    @field_validator("scheduled_at")
    @classmethod
    def validate_scheduled_at(cls, v, info):
        if v and v < datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("Scheduled time must be at least 5 minutes in the future")
        return v

    @field_validator("holdout_percentage")
    @classmethod
    def validate_holdout(cls, v):
        if v < 0 or v > 20:
            raise ValueError("Holdout percentage must be between 0 and 20")
        return v
```

---

## Monitoring

### 1. Prometheus Metrics

```python
# Campaign metrics
campaigns_created_total = Counter("campaigns_created_total", ["type", "organization"])
campaigns_completed_total = Counter("campaigns_completed_total", ["type", "status"])
campaign_execution_duration = Histogram("campaign_execution_duration_seconds", ["type"])
campaign_messages_sent_total = Counter("campaign_messages_sent_total", ["channel", "status"])

# Trigger metrics
trigger_evaluations_total = Counter("trigger_evaluations_total", ["campaign", "result"])
trigger_evaluation_duration = Histogram("trigger_evaluation_duration_seconds")

# API metrics
api_request_duration = Histogram("api_request_duration_seconds", ["endpoint", "method"])
api_request_total = Counter("api_request_total", ["endpoint", "method", "status"])
```

### 2. Health Checks

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "campaign_service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health/ready")
async def readiness_check():
    checks = {
        "database": await check_database_health(),
        "nats": await check_nats_health(),
        "redis": await check_redis_health()
    }

    is_ready = all(c["status"] == "healthy" for c in checks.values())

    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks
    }
```

---

## Deployment

### Environment Variables

```bash
# Service Configuration
CAMPAIGN_SERVICE_PORT=8240
CAMPAIGN_SERVICE_HOST=0.0.0.0

# Database
POSTGRES_HOST=isa-postgres-grpc
POSTGRES_PORT=50061
DATABASE_POOL_SIZE=20

# NATS
NATS_GRPC_HOST=isa-nats-grpc
NATS_GRPC_PORT=50056

# Redis
REDIS_URL=redis://localhost:6379/0

# Consul
CONSUL_ENABLED=true
CONSUL_HOST=localhost
CONSUL_PORT=8500

# External Services
ISA_DATA_URL=http://isa-data:8300
ISA_CREATIVE_URL=http://isa-creative:8310
NOTIFICATION_SERVICE_URL=http://notification-service:8208
TASK_SERVICE_URL=http://task-service:8229
EVENT_SERVICE_URL=http://event-service:8230

# Rate Limiting
MESSAGE_RATE_LIMIT_PER_MINUTE=10000
MESSAGE_RATE_LIMIT_PER_HOUR=100000
```

### Kubernetes Resources

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

---

**Version**: 1.0.0
**Last Updated**: 2026-02-02
**Author**: Marketing Platform Team
