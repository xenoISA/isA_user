# Campaign Service - Domain Context

## Service Overview

The Campaign Service manages marketing automation campaigns that deliver targeted messages to segmented audiences through multiple channels. It serves as the orchestration layer between audience segmentation (isA_Data), creative content (isA_Creative), and delivery infrastructure (notification_service).

---

## Business Domain Context

### Domain Definition

**Campaign Management** is the practice of planning, executing, tracking, and optimizing outbound communications to user segments. This includes:

- **Scheduled Campaigns**: Time-based execution where messages are sent at predetermined times
- **Triggered Campaigns**: Event-based execution where user actions or system events initiate message delivery
- **Multi-channel Delivery**: Coordinated delivery across email, SMS/WhatsApp, in-app notifications, and webhooks
- **Performance Tracking**: Measurement of campaign effectiveness through delivery and engagement metrics

### Bounded Context

The Campaign Service operates within the **Marketing Automation** bounded context, bounded by:

| Boundary | Description |
|----------|-------------|
| **Upstream** | isA_Data (audience segments via intelligent_query, user_360), isA_Creative (templates/assets), event_service (triggers) |
| **Downstream** | notification_service (delivery), storage_service/media_service (assets) |
| **Lateral** | account_service (user data), organization_service (permissions), billing_service (usage tracking), task_service (scheduling) |

### Domain Entities

| Entity | Description | Lifecycle |
|--------|-------------|-----------|
| **Campaign** | Core entity representing a marketing initiative | draft -> scheduled/active -> running -> paused/completed/cancelled |
| **CampaignAudience** | Segment definition referencing isA_Data queries | immutable once campaign starts |
| **CampaignVariant** | A/B test variant with content and allocation | created with campaign, locked during execution |
| **CampaignChannel** | Channel-specific content configuration | created with campaign |
| **CampaignSchedule** | Time-based execution configuration | created with campaign, modifiable in draft |
| **CampaignTrigger** | Event-based trigger configuration | created with campaign, modifiable in draft |
| **CampaignExecution** | Single execution instance of a campaign | created at runtime, immutable |
| **CampaignMessage** | Individual message sent to a recipient | tracks full delivery lifecycle |
| **CampaignMetric** | Aggregated performance metric | append-only |

---

## Terminology (Ubiquitous Language)

### Core Terms

| Term | Definition | Example |
|------|------------|---------|
| **Campaign** | A coordinated series of messages with defined audience, content, and delivery schedule | "New Year Promotion 2026" |
| **Audience Segment** | A dynamically calculated set of users matching specific criteria | "Premium users in California who opened email in last 30 days" |
| **Trigger** | An event condition that initiates campaign execution | "user.subscription.upgraded" event |
| **Variant** | Alternative content or delivery parameters for A/B testing | Variant A: 10% discount, Variant B: Free shipping |
| **Channel** | Delivery medium for campaign messages | email, sms, whatsapp, in_app, webhook |
| **Throttle** | Rate limiting configuration to control delivery speed | 1000 messages per minute |
| **Holdout** | Control group excluded from receiving messages | 5% holdout for measurement |
| **Attribution Window** | Time period to attribute conversions to campaign | 7-day click attribution |

### Campaign Type Terms

| Type | Trigger | Execution Pattern |
|------|---------|-------------------|
| **One-time Scheduled** | Schedule datetime | Execute once at specified time |
| **Recurring Scheduled** | Cron schedule | Execute on schedule (daily, weekly, etc.) |
| **Event-triggered** | System event | Execute when event matches conditions |
| **Transactional** | API call | Execute immediately on demand |

### Metric Terms

| Term | Definition | Calculation |
|------|------------|-------------|
| **Sent** | Messages successfully queued for delivery | Count of messages with status >= sent |
| **Delivered** | Messages confirmed delivered by channel provider | Channel-specific delivery confirmation |
| **Opened** | Messages viewed by recipient | Pixel tracking (email), event tracking (in-app) |
| **Clicked** | Recipient clicked a tracked link | URL redirect tracking |
| **Converted** | Recipient completed goal action | Conversion event within attribution window |
| **Bounce** | Message delivery failed | Hard bounce (permanent) or soft bounce (temporary) |
| **Unsubscribed** | Recipient opted out via campaign | Unsubscribe link click |

### Channel Terms

| Channel | Protocol | Content Format | Tracking |
|---------|----------|----------------|----------|
| **Email** | SMTP via provider | HTML + plain text | Open pixel, click redirect |
| **SMS** | SMS gateway | Plain text (160 chars) | Delivery receipt |
| **WhatsApp** | WhatsApp Business API | Rich text (1600 chars) | Read receipts |
| **In-App** | MQTT/WebSocket | JSON payload | Event tracking |
| **Webhook** | HTTP POST | JSON payload | Response code |

---

## Business Capabilities

### BR-CAM-001: Campaign Lifecycle Management

**Capability**: Create, configure, activate, pause, and complete campaigns

**Business Rules**:
- BR-CAM-001.1: Campaigns must have at least one audience segment before scheduling
- BR-CAM-001.2: Campaigns must have valid content for all configured channels
- BR-CAM-001.3: Scheduled campaigns require a future execution time (minimum 5 minutes)
- BR-CAM-001.4: Triggered campaigns require at least one valid trigger condition
- BR-CAM-001.5: Only draft or paused campaigns can be edited
- BR-CAM-001.6: Running campaigns can only be paused, not edited
- BR-CAM-001.7: Completed campaigns cannot be modified, only cloned
- BR-CAM-001.8: Cancelled campaigns cannot be resumed

### BR-CAM-002: Audience Segmentation

**Capability**: Define and resolve audience segments for targeting

**Business Rules**:
- BR-CAM-002.1: Audience segments are resolved at execution time for real-time accuracy
- BR-CAM-002.2: Segment queries are delegated to isA_Data intelligent_query service
- BR-CAM-002.3: Users can be excluded via suppression lists (unsubscribed, complained, bounced)
- BR-CAM-002.4: Holdout groups are randomly selected using deterministic hash for consistency
- BR-CAM-002.5: Audience size estimation available before campaign launch
- BR-CAM-002.6: Maximum 10 segments per campaign (include + exclude)
- BR-CAM-002.7: Segment intersection logic: AND for includes, OR for excludes

### BR-CAM-003: Multi-Channel Delivery

**Capability**: Deliver messages across multiple channels with channel-specific formatting

**Business Rules**:
- BR-CAM-003.1: Each channel has independent content templates
- BR-CAM-003.2: Channel availability determined by user preferences and contact data
- BR-CAM-003.3: Channel fallback order configurable per campaign
- BR-CAM-003.4: Delivery via notification_service for all channels
- BR-CAM-003.5: Channel-specific rate limits respected
- BR-CAM-003.6: Email requires valid email address and email_opted_in=true
- BR-CAM-003.7: SMS requires valid phone number and sms_opted_in=true
- BR-CAM-003.8: WhatsApp requires verified WhatsApp number
- BR-CAM-003.9: In-app requires active user session (delivered on next login if offline)

### BR-CAM-004: A/B Testing

**Capability**: Test multiple content variants to optimize campaign performance

**Business Rules**:
- BR-CAM-004.1: Maximum 5 variants per campaign
- BR-CAM-004.2: Variant allocation must sum to 100%
- BR-CAM-004.3: Variant assignment is deterministic per recipient (hash of user_id + campaign_id)
- BR-CAM-004.4: Statistical significance calculated using chi-square test
- BR-CAM-004.5: Winner selection can be manual or automatic based on metric thresholds
- BR-CAM-004.6: Auto-winner requires minimum sample size of 1000 per variant
- BR-CAM-004.7: Control variant (no message) supported for holdout measurement

### BR-CAM-005: Performance Tracking

**Capability**: Track and report campaign delivery and engagement metrics

**Business Rules**:
- BR-CAM-005.1: All messages tracked through full delivery lifecycle
- BR-CAM-005.2: Metrics aggregated at campaign, variant, channel, and segment level
- BR-CAM-005.3: Conversion attribution window configurable (default 7 days, max 30 days)
- BR-CAM-005.4: Real-time metric updates via event streaming (< 5 second delay)
- BR-CAM-005.5: Historical metrics retained per data retention policy (default 2 years)
- BR-CAM-005.6: Click tracking uses redirect URLs with unique tracking tokens
- BR-CAM-005.7: Open tracking uses 1x1 pixel images with unique tokens

### BR-CAM-006: Rate Limiting and Throttling

**Capability**: Control message delivery rate to prevent system overload and provider limits

**Business Rules**:
- BR-CAM-006.1: Global throughput limit per organization configurable (default 10,000/hour)
- BR-CAM-006.2: Per-channel rate limits enforced (email: 10,000/hour, SMS: 1,000/hour)
- BR-CAM-006.3: Campaign-specific throttle settings override defaults
- BR-CAM-006.4: Throttling distributes delivery evenly over configured window
- BR-CAM-006.5: Rate limit exhaustion triggers queueing, not failure
- BR-CAM-006.6: Quiet hours enforcement (default: 21:00-08:00 user local time)
- BR-CAM-006.7: Weekend exclusion option for business campaigns

### BR-CAM-007: Trigger Evaluation

**Capability**: Evaluate event-based triggers and fire campaigns accordingly

**Business Rules**:
- BR-CAM-007.1: Triggers evaluated against event_service events
- BR-CAM-007.2: Trigger conditions support property matching (equals, contains, greater_than, less_than)
- BR-CAM-007.3: Multiple conditions use AND logic
- BR-CAM-007.4: Trigger delay configurable (0 to 30 days)
- BR-CAM-007.5: Trigger frequency limit per user per campaign (default: 1 per 24 hours)
- BR-CAM-007.6: Triggered campaigns must be in "active" status to fire
- BR-CAM-007.7: User must be in audience segment at trigger time

### BR-CAM-008: Creative Content Integration

**Capability**: Integrate with isA_Creative for template management

**Business Rules**:
- BR-CAM-008.1: Templates retrieved from isA_Creative at campaign creation
- BR-CAM-008.2: Template variables validated against user_360 schema
- BR-CAM-008.3: Dynamic content personalization using user_360 data
- BR-CAM-008.4: Asset URLs resolved via storage_service/media_service
- BR-CAM-008.5: Template preview with sample user data before launch

---

## Domain Events

### Events Published

| Event | Subject | Trigger | Payload |
|-------|---------|---------|---------|
| `campaign.created` | `campaign.created` | Campaign created | campaign_id, name, type, status, created_by |
| `campaign.updated` | `campaign.updated` | Campaign modified | campaign_id, changed_fields, updated_by |
| `campaign.scheduled` | `campaign.scheduled` | Campaign scheduled for execution | campaign_id, scheduled_at, task_id |
| `campaign.activated` | `campaign.activated` | Triggered campaign activated | campaign_id, activated_at |
| `campaign.started` | `campaign.started` | Campaign execution begins | campaign_id, execution_id, audience_size |
| `campaign.paused` | `campaign.paused` | Campaign execution paused | campaign_id, paused_by, messages_sent |
| `campaign.resumed` | `campaign.resumed` | Campaign execution resumed | campaign_id, resumed_by |
| `campaign.completed` | `campaign.completed` | Campaign execution finished | campaign_id, execution_id, total_sent, total_delivered |
| `campaign.cancelled` | `campaign.cancelled` | Campaign cancelled | campaign_id, cancelled_by, reason |
| `campaign.message.queued` | `campaign.message.queued` | Message queued for delivery | campaign_id, message_id, user_id, channel |
| `campaign.message.sent` | `campaign.message.sent` | Message sent to provider | campaign_id, message_id, provider_id |
| `campaign.message.delivered` | `campaign.message.delivered` | Message delivery confirmed | campaign_id, message_id, delivered_at |
| `campaign.message.opened` | `campaign.message.opened` | Message opened by recipient | campaign_id, message_id, opened_at |
| `campaign.message.clicked` | `campaign.message.clicked` | Recipient clicked link | campaign_id, message_id, link_id, clicked_at |
| `campaign.message.converted` | `campaign.message.converted` | Recipient converted | campaign_id, message_id, conversion_event, value |
| `campaign.message.bounced` | `campaign.message.bounced` | Message delivery failed | campaign_id, message_id, bounce_type, reason |
| `campaign.message.unsubscribed` | `campaign.message.unsubscribed` | Recipient unsubscribed | campaign_id, message_id, user_id |
| `campaign.metric.updated` | `campaign.metric.updated` | Metrics aggregated | campaign_id, metric_type, value, timestamp |

### Events Subscribed

| Event | Source | Handler |
|-------|--------|---------|
| `user.created` | account_service | Add to welcome campaign audiences |
| `user.deleted` | account_service | Remove from all campaigns, GDPR cleanup |
| `user.preferences.updated` | account_service | Update channel availability |
| `subscription.created` | subscription_service | Trigger onboarding campaigns |
| `subscription.upgraded` | subscription_service | Trigger upsell thank-you campaigns |
| `subscription.cancelled` | subscription_service | Trigger win-back campaigns |
| `order.completed` | order_service | Trigger post-purchase campaigns |
| `notification.delivered` | notification_service | Update message delivery status |
| `notification.failed` | notification_service | Update message failure status |
| `notification.opened` | notification_service | Update message open status |
| `notification.clicked` | notification_service | Update message click status |
| `task.executed` | task_service | Handle scheduled campaign execution |
| `event.stored` | event_service | Evaluate triggered campaign conditions |

---

## Integration Points

### Upstream Dependencies

| Service | Purpose | Integration Pattern | Fallback |
|---------|---------|---------------------|----------|
| **isA_Data (intelligent_query)** | Audience segment resolution | Sync HTTP call at execution time | Cache last segment, alert |
| **isA_Data (user_360)** | User profile enrichment for personalization | Sync HTTP call for template rendering | Use cached profile, skip personalization |
| **isA_Creative** | Template management, creative orchestration | Sync HTTP call for content retrieval | Use cached template |
| **event_service** | Trigger event subscription | NATS subscription | Queue events, retry |

### Downstream Dependencies

| Service | Purpose | Integration Pattern | Fallback |
|---------|---------|---------------------|----------|
| **notification_service** | Message delivery to all channels | Async event publishing | Queue for retry |
| **storage_service** | Campaign asset storage | Sync HTTP call for asset URLs | Use cached URLs |
| **media_service** | Image processing, optimization | Sync HTTP call for optimized images | Use original assets |

### Cross-Cutting Dependencies

| Service | Purpose | Integration Pattern |
|---------|---------|---------------------|
| **task_service** | Schedule management for scheduled campaigns | Sync HTTP call to create/cancel scheduled tasks |
| **account_service** | User existence validation, preference lookup | Sync HTTP call |
| **organization_service** | Permission validation, org-level settings | Sync HTTP call |
| **billing_service** | Usage tracking for message delivery | Async event publishing |
| **audit_service** | Campaign operation audit trail | Async event publishing |

---

## Organizational Context

### Stakeholders

| Role | Interest | Concerns |
|------|----------|----------|
| **Marketing Team** | Campaign creation and optimization | Ease of use, targeting accuracy, performance insights |
| **Product Team** | User engagement and retention | Delivery reliability, personalization quality |
| **Engineering** | System performance and reliability | Throughput, scalability, monitoring |
| **Compliance** | Regulatory adherence | Consent tracking, unsubscribe handling, data retention |
| **Finance** | Cost management | Message volume tracking, channel costs |

### Compliance Requirements

| Requirement | Implementation |
|-------------|----------------|
| **CAN-SPAM** | Unsubscribe link required in all commercial emails, physical address included |
| **GDPR** | User consent tracking, right to erasure support, data minimization |
| **TCPA** | SMS opt-in verification, quiet hours enforcement (before 8am, after 9pm) |
| **CCPA** | Privacy notice inclusion, opt-out support, do-not-sell flag |
| **CASL** | Express consent required for Canadian recipients |

---

## Quality Attributes

| Attribute | Target | Rationale |
|-----------|--------|-----------|
| **Availability** | 99.9% | Campaigns are time-sensitive |
| **Latency (API)** | p99 < 500ms | Interactive campaign management |
| **Latency (Execution Start)** | Within 60s of scheduled time | Time-sensitive delivery |
| **Latency (Trigger Response)** | < 5 seconds from event | Real-time engagement |
| **Throughput** | 100,000 messages/minute per organization | Large-scale campaigns |
| **Data Durability** | Zero message loss | Every message must be tracked |
| **Metric Accuracy** | < 1% variance | Reliable analytics |

---

## Future Considerations

### Planned Capabilities

1. **Journey Orchestration**: Multi-step campaigns with branching logic based on user actions
2. **Predictive Send Time**: ML-based optimal send time per recipient
3. **Dynamic Content**: Real-time content personalization at delivery time
4. **Cross-Campaign Frequency Capping**: Limit total messages per user across all campaigns
5. **Lookalike Audiences**: ML-based audience expansion from seed segments
6. **Campaign Templates**: Pre-built campaign blueprints for common use cases
7. **Multi-Language Support**: Automatic content localization based on user locale

### Technical Debt Considerations

1. Segment resolution caching for performance
2. Message deduplication across concurrent campaigns
3. Retry strategy standardization across channels
4. Metric calculation optimization for large campaigns

---

**Document Version**: 1.0.0
**Last Updated**: 2026-02-02
**Domain Owner**: Marketing Platform Team
