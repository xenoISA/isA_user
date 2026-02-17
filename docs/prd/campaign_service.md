# Campaign Service - Product Requirements Document

## Executive Summary

The Campaign Service enables marketing teams to create, execute, and measure multi-channel marketing campaigns with advanced targeting, A/B testing, and performance analytics. It integrates with isA_Data for audience segmentation, isA_Creative for content management, and notification_service for delivery.

---

## Product Vision

**For** marketing teams and product managers
**Who** need to engage users through targeted, personalized communications
**The** Campaign Service is a marketing automation platform
**That** enables multi-channel campaign orchestration with real-time analytics
**Unlike** basic notification systems
**Our product** provides advanced segmentation, A/B testing, triggered campaigns, and attribution tracking

---

## Goals and Success Metrics

### Primary Goals

| Goal | Metric | Target |
|------|--------|--------|
| Enable effective user engagement | Campaign delivery rate | > 98% |
| Provide actionable insights | Time to first insight | < 5 minutes post-campaign |
| Support marketing scale | Messages per minute | 100,000+ |
| Ensure compliance | Compliance violations | 0 |
| Optimize campaign performance | A/B test adoption | > 50% of campaigns |

### Key Performance Indicators (KPIs)

| KPI | Definition | Target |
|-----|------------|--------|
| **Delivery Rate** | Delivered / Sent | > 98% |
| **Open Rate** | Opened / Delivered | Baseline + tracking |
| **Click Rate** | Clicked / Delivered | Baseline + tracking |
| **Conversion Rate** | Converted / Sent | Campaign-specific |
| **Time to Launch** | Draft to Running | < 15 minutes |
| **Trigger Latency** | Event to Message Sent | < 60 seconds |

---

## User Stories

### Epic 1: Campaign Creation

#### US-CAM-001: Create Basic Campaign

**As a** marketing manager
**I want to** create a campaign with target audience, content, and schedule
**So that** I can reach users with relevant messages at the right time

**Acceptance Criteria**:
- AC-001.1: Can specify campaign name, description, and type (scheduled/triggered)
- AC-001.2: Can select audience segment from available segments
- AC-001.3: Can configure content for one or more channels
- AC-001.4: Can set schedule (one-time, recurring) or trigger conditions
- AC-001.5: Campaign saved as draft until explicitly scheduled/activated
- AC-001.6: Validation errors displayed inline before submission

**Priority**: P0 - Must Have
**Story Points**: 8

---

#### US-CAM-002: Configure Multi-Channel Content

**As a** marketing manager
**I want to** configure different content for each delivery channel
**So that** messages are optimized for each medium

**Acceptance Criteria**:
- AC-002.1: Can configure email with subject, body (HTML/text), sender, and reply-to
- AC-002.2: Can configure SMS with message body (160 char limit displayed)
- AC-002.3: Can configure WhatsApp with message body (1600 char limit displayed)
- AC-002.4: Can configure in-app notification with title, body, and action URL
- AC-002.5: Can configure webhook with URL, method, headers, and payload template
- AC-002.6: Can preview content with sample user data
- AC-002.7: Template variables resolved against user_360 data

**Priority**: P0 - Must Have
**Story Points**: 13

---

#### US-CAM-003: Define Audience Segment

**As a** marketing manager
**I want to** define the target audience using segmentation criteria
**So that** only relevant users receive the campaign

**Acceptance Criteria**:
- AC-003.1: Can select pre-built segment from isA_Data
- AC-003.2: Can create inline segment with attribute filters
- AC-003.3: Can combine multiple segments (AND/OR logic)
- AC-003.4: Can exclude specific segments (suppression)
- AC-003.5: Can see estimated audience size before launch
- AC-003.6: Can set holdout percentage for control group (0-20%)
- AC-003.7: Audience resolved at execution time for accuracy

**Priority**: P0 - Must Have
**Story Points**: 8

---

#### US-CAM-004: Set Up Triggered Campaign

**As a** marketing manager
**I want to** create campaigns that trigger on specific events
**So that** messages are sent at the most relevant moment

**Acceptance Criteria**:
- AC-004.1: Can select trigger event type from available events
- AC-004.2: Can add conditions on event properties (equals, contains, greater_than, less_than)
- AC-004.3: Can set delay between trigger and send (0 to 30 days)
- AC-004.4: Can set quiet hours to avoid sending during sleep times
- AC-004.5: Can set trigger frequency limits per user (once per 1h/24h/7d/30d)
- AC-004.6: Triggered campaign activates immediately when set to active
- AC-004.7: User must be in audience segment at trigger time

**Priority**: P0 - Must Have
**Story Points**: 13

---

### Epic 2: A/B Testing

#### US-CAM-005: Create Campaign Variants

**As a** marketing manager
**I want to** create multiple content variants for testing
**So that** I can optimize campaign performance

**Acceptance Criteria**:
- AC-005.1: Can create 2-5 variants per campaign
- AC-005.2: Each variant has independent content configuration
- AC-005.3: Can set allocation percentage per variant (must sum to 100%)
- AC-005.4: Can designate control variant (no message sent)
- AC-005.5: Variant assignment is deterministic per user (same user always gets same variant)
- AC-005.6: Can clone variant for quick iteration

**Priority**: P1 - Should Have
**Story Points**: 8

---

#### US-CAM-006: View Variant Performance

**As a** marketing manager
**I want to** compare performance across variants
**So that** I can identify the winning variant

**Acceptance Criteria**:
- AC-006.1: Can see all metrics broken down by variant
- AC-006.2: Can see statistical significance indicator (chi-square test)
- AC-006.3: Can see confidence interval for each metric
- AC-006.4: Winner highlighted when 95% significance reached
- AC-006.5: Can export variant comparison report as CSV/PDF

**Priority**: P1 - Should Have
**Story Points**: 5

---

#### US-CAM-007: Auto-Select Winner

**As a** marketing manager
**I want to** automatically select and scale the winning variant
**So that** I can maximize campaign effectiveness without manual intervention

**Acceptance Criteria**:
- AC-007.1: Can enable auto-winner selection per campaign
- AC-007.2: Can set target metric for winner determination (open rate, click rate, conversion rate)
- AC-007.3: Can set minimum statistical significance threshold (90%, 95%, 99%)
- AC-007.4: Can set minimum sample size before evaluation (default 1000 per variant)
- AC-007.5: Winner automatically scales to 100% when selected
- AC-007.6: Notification sent when winner selected

**Priority**: P2 - Nice to Have
**Story Points**: 8

---

### Epic 3: Campaign Execution

#### US-CAM-008: Schedule Campaign

**As a** marketing manager
**I want to** schedule a campaign for future execution
**So that** it runs at the optimal time

**Acceptance Criteria**:
- AC-008.1: Can set one-time execution datetime
- AC-008.2: Can set recurring schedule (daily, weekly, monthly, custom cron)
- AC-008.3: Can set timezone for schedule
- AC-008.4: Scheduled time must be at least 5 minutes in future
- AC-008.5: Can modify schedule while campaign is scheduled (not running)
- AC-008.6: Task created in task_service for scheduled execution
- AC-008.7: Can cancel scheduled campaign

**Priority**: P0 - Must Have
**Story Points**: 5

---

#### US-CAM-009: Pause Running Campaign

**As a** marketing manager
**I want to** pause a running campaign
**So that** I can stop delivery while investigating issues

**Acceptance Criteria**:
- AC-009.1: Can pause any running campaign
- AC-009.2: In-flight messages complete delivery
- AC-009.3: New messages stop being queued immediately
- AC-009.4: Can see pause timestamp and user who paused
- AC-009.5: Can resume paused campaign
- AC-009.6: Resumed campaign continues from where it stopped

**Priority**: P0 - Must Have
**Story Points**: 5

---

#### US-CAM-010: Configure Throttling

**As a** marketing manager
**I want to** control the rate of message delivery
**So that** I don't overwhelm recipients or exceed provider limits

**Acceptance Criteria**:
- AC-010.1: Can set messages per minute limit (default from org settings)
- AC-010.2: Can set messages per hour limit
- AC-010.3: Can set daily send window (start/end hours in user timezone)
- AC-010.4: Can set weekend exclusion
- AC-010.5: Throttle distributes sends evenly over window
- AC-010.6: Default throttle inherited from organization settings
- AC-010.7: Can see estimated delivery completion time

**Priority**: P1 - Should Have
**Story Points**: 5

---

### Epic 4: Performance Tracking

#### US-CAM-011: View Real-Time Metrics

**As a** marketing manager
**I want to** see campaign performance in real-time
**So that** I can monitor campaign health during execution

**Acceptance Criteria**:
- AC-011.1: Can see sent, delivered, bounced counts updating live
- AC-011.2: Can see open, click, conversion counts updating live
- AC-011.3: Can see delivery rate, open rate, click rate percentages
- AC-011.4: Metrics update within 5 seconds of event
- AC-011.5: Last updated timestamp displayed
- AC-011.6: Alert displayed if delivery rate drops below 95%

**Priority**: P0 - Must Have
**Story Points**: 8

---

#### US-CAM-012: View Campaign Report

**As a** marketing manager
**I want to** see a comprehensive campaign report
**So that** I can analyze performance and derive insights

**Acceptance Criteria**:
- AC-012.1: Report includes all metrics with totals and rates
- AC-012.2: Report includes metrics over time chart
- AC-012.3: Report includes breakdown by channel
- AC-012.4: Report includes breakdown by variant (if applicable)
- AC-012.5: Report includes breakdown by segment
- AC-012.6: Can export report as PDF or CSV
- AC-012.7: Report available within 1 minute of campaign completion

**Priority**: P0 - Must Have
**Story Points**: 8

---

#### US-CAM-013: Track Conversions

**As a** marketing manager
**I want to** track conversions attributed to campaigns
**So that** I can measure business impact

**Acceptance Criteria**:
- AC-013.1: Can define conversion event type per campaign
- AC-013.2: Can set attribution window (1-30 days, default 7)
- AC-013.3: Conversions attributed to campaign if within window
- AC-013.4: Multiple attribution models available (first-touch, last-touch, linear)
- AC-013.5: Can see conversion value if provided in event
- AC-013.6: Conversion rate calculated and displayed
- AC-013.7: Can see revenue attributed to campaign

**Priority**: P1 - Should Have
**Story Points**: 8

---

### Epic 5: Campaign Management

#### US-CAM-014: List and Search Campaigns

**As a** marketing manager
**I want to** find campaigns quickly
**So that** I can manage my campaign portfolio efficiently

**Acceptance Criteria**:
- AC-014.1: Can list all campaigns with pagination (default 20, max 100)
- AC-014.2: Can filter by status (draft, scheduled, active, running, paused, completed, cancelled)
- AC-014.3: Can filter by type (scheduled, triggered)
- AC-014.4: Can filter by channel (email, sms, whatsapp, in_app, webhook)
- AC-014.5: Can search by name (prefix match)
- AC-014.6: Can sort by created date, scheduled date, or name
- AC-014.7: Can filter by date range

**Priority**: P0 - Must Have
**Story Points**: 5

---

#### US-CAM-015: Clone Campaign

**As a** marketing manager
**I want to** clone an existing campaign
**So that** I can quickly create similar campaigns

**Acceptance Criteria**:
- AC-015.1: Can clone any campaign regardless of status
- AC-015.2: Clone creates new draft with copied configuration
- AC-015.3: Clone name includes "Copy of" prefix
- AC-015.4: Can modify clone before scheduling
- AC-015.5: Clone has no association to original (independent)
- AC-015.6: Clone audit trail shows origin campaign

**Priority**: P1 - Should Have
**Story Points**: 3

---

#### US-CAM-016: Delete Campaign

**As a** marketing manager
**I want to** delete campaigns I no longer need
**So that** I can keep my workspace organized

**Acceptance Criteria**:
- AC-016.1: Can delete draft campaigns immediately
- AC-016.2: Can delete completed campaigns
- AC-016.3: Cannot delete running campaigns (must pause first)
- AC-016.4: Delete is soft delete (recoverable for 30 days)
- AC-016.5: Deleted campaigns excluded from list by default
- AC-016.6: Can view and restore deleted campaigns
- AC-016.7: Hard delete after 30 days (GDPR compliance)

**Priority**: P2 - Nice to Have
**Story Points**: 3

---

### Epic 6: Compliance and Preferences

#### US-CAM-017: Handle Unsubscribes

**As a** compliance officer
**I want to** ensure unsubscribes are processed immediately
**So that** we comply with regulations

**Acceptance Criteria**:
- AC-017.1: Unsubscribe link included in all marketing emails (auto-injected)
- AC-017.2: Unsubscribe processed within 10 seconds
- AC-017.3: User excluded from future campaigns immediately
- AC-017.4: Unsubscribe tracked in campaign metrics
- AC-017.5: Can view list of users who unsubscribed per campaign
- AC-017.6: Unsubscribe preference synced to account_service
- AC-017.7: Unsubscribe reason captured if provided

**Priority**: P0 - Must Have
**Story Points**: 5

---

#### US-CAM-018: Respect User Preferences

**As a** compliance officer
**I want to** respect user communication preferences
**So that** we only contact users who have opted in

**Acceptance Criteria**:
- AC-018.1: User channel preferences checked before sending
- AC-018.2: Users with channel disabled excluded from that channel
- AC-018.3: Quiet hours respected for all channels
- AC-018.4: Marketing vs. transactional preference respected
- AC-018.5: Global opt-out stops all campaign messages
- AC-018.6: Preference changes reflected within 1 minute
- AC-018.7: Compliance audit log maintained

**Priority**: P0 - Must Have
**Story Points**: 5

---

## Functional Requirements

### FR-CAM-001: Campaign CRUD Operations

| Requirement | Description |
|-------------|-------------|
| FR-001.1 | System shall support creating campaigns with name, description, type, and status |
| FR-001.2 | System shall support reading campaign details including configuration and metrics |
| FR-001.3 | System shall support updating campaigns in draft or paused status |
| FR-001.4 | System shall support soft-deleting campaigns not in running status |
| FR-001.5 | System shall support listing campaigns with filtering, sorting, and pagination |
| FR-001.6 | System shall support cloning campaigns |

### FR-CAM-002: Audience Management

| Requirement | Description |
|-------------|-------------|
| FR-002.1 | System shall integrate with isA_Data intelligent_query for segment resolution |
| FR-002.2 | System shall support multiple segment inclusion with boolean logic |
| FR-002.3 | System shall support segment exclusion (suppression lists) |
| FR-002.4 | System shall support holdout group configuration (0-20%) |
| FR-002.5 | System shall provide audience size estimation before launch |
| FR-002.6 | System shall resolve audience at execution time |

### FR-CAM-003: Content Management

| Requirement | Description |
|-------------|-------------|
| FR-003.1 | System shall support email content with subject, HTML body, text body, sender, reply-to |
| FR-003.2 | System shall support SMS content with message body (160 char limit) |
| FR-003.3 | System shall support WhatsApp content with message body (1600 char limit) |
| FR-003.4 | System shall support in-app notification with title, body, action URL, icon |
| FR-003.5 | System shall support webhook with URL, method, headers, and payload template |
| FR-003.6 | System shall support template variable resolution from user_360 data |
| FR-003.7 | System shall support content preview with sample data |

### FR-CAM-004: Scheduling and Triggers

| Requirement | Description |
|-------------|-------------|
| FR-004.1 | System shall support one-time scheduled execution |
| FR-004.2 | System shall support recurring scheduled execution (cron-based) |
| FR-004.3 | System shall support event-triggered execution |
| FR-004.4 | System shall support trigger delay configuration (0-30 days) |
| FR-004.5 | System shall support trigger frequency limiting per user |
| FR-004.6 | System shall integrate with task_service for schedule management |
| FR-004.7 | System shall support quiet hours configuration |

### FR-CAM-005: A/B Testing

| Requirement | Description |
|-------------|-------------|
| FR-005.1 | System shall support 2-5 variants per campaign |
| FR-005.2 | System shall support allocation percentage per variant |
| FR-005.3 | System shall deterministically assign variants to users |
| FR-005.4 | System shall calculate statistical significance for comparisons |
| FR-005.5 | System shall support automatic winner selection |
| FR-005.6 | System shall support control variant (holdout) |

### FR-CAM-006: Metrics Tracking

| Requirement | Description |
|-------------|-------------|
| FR-006.1 | System shall track sent, queued, delivered, bounced metrics |
| FR-006.2 | System shall track opened, clicked metrics |
| FR-006.3 | System shall track conversion metrics with attribution |
| FR-006.4 | System shall track unsubscribe metrics |
| FR-006.5 | System shall aggregate metrics at campaign, variant, channel, segment levels |
| FR-006.6 | System shall provide real-time metric updates (< 5 second delay) |
| FR-006.7 | System shall support metric export |

### FR-CAM-007: Rate Limiting

| Requirement | Description |
|-------------|-------------|
| FR-007.1 | System shall support campaign-level messages per minute limit |
| FR-007.2 | System shall support campaign-level messages per hour limit |
| FR-007.3 | System shall support channel-level rate limits |
| FR-007.4 | System shall queue messages when rate limit reached |
| FR-007.5 | System shall support send window configuration |
| FR-007.6 | System shall distribute sends evenly over throttle window |

---

## Non-Functional Requirements

### NFR-CAM-001: Performance

| Requirement | Metric | Target |
|-------------|--------|--------|
| NFR-001.1 | API response time (p50) | < 100ms |
| NFR-001.2 | API response time (p99) | < 500ms |
| NFR-001.3 | Campaign start latency | < 60 seconds from scheduled time |
| NFR-001.4 | Trigger response latency | < 5 seconds from event |
| NFR-001.5 | Message throughput | 100,000 messages/minute/org |
| NFR-001.6 | Metric update latency | < 5 seconds |

### NFR-CAM-002: Reliability

| Requirement | Metric | Target |
|-------------|--------|--------|
| NFR-002.1 | Service availability | 99.9% |
| NFR-002.2 | Message delivery guarantee | At-least-once |
| NFR-002.3 | Data durability | No message loss |
| NFR-002.4 | Recovery time objective | < 15 minutes |
| NFR-002.5 | Recovery point objective | < 1 minute |

### NFR-CAM-003: Scalability

| Requirement | Metric | Target |
|-------------|--------|--------|
| NFR-003.1 | Concurrent campaigns per org | 1000+ |
| NFR-003.2 | Audience size per campaign | 10M+ users |
| NFR-003.3 | Historical campaigns retained | 2 years |
| NFR-003.4 | Horizontal scaling | Stateless service design |
| NFR-003.5 | Message queue depth | 10M+ messages |

### NFR-CAM-004: Security

| Requirement | Description |
|-------------|-------------|
| NFR-004.1 | All API endpoints require authentication |
| NFR-004.2 | Campaign access restricted to owning organization |
| NFR-004.3 | PII data encrypted at rest and in transit |
| NFR-004.4 | Audit trail for all campaign operations |
| NFR-004.5 | Rate limiting on API endpoints |
| NFR-004.6 | Input validation on all user inputs |

---

## Acceptance Criteria Matrix

| User Story | P0 Criteria | P1 Criteria | P2 Criteria |
|------------|-------------|-------------|-------------|
| US-CAM-001 | AC-001.1-5 | AC-001.6 | - |
| US-CAM-002 | AC-002.1-5 | AC-002.6-7 | - |
| US-CAM-003 | AC-003.1-5 | AC-003.6-7 | - |
| US-CAM-004 | AC-004.1-6 | AC-004.7 | - |
| US-CAM-005 | - | AC-005.1-5 | AC-005.6 |
| US-CAM-006 | - | AC-006.1-4 | AC-006.5 |
| US-CAM-007 | - | - | AC-007.1-6 |
| US-CAM-008 | AC-008.1-4 | AC-008.5-7 | - |
| US-CAM-009 | AC-009.1-4 | AC-009.5-6 | - |
| US-CAM-010 | - | AC-010.1-6 | AC-010.7 |
| US-CAM-011 | AC-011.1-5 | AC-011.6 | - |
| US-CAM-012 | AC-012.1-5 | AC-012.6-7 | - |
| US-CAM-013 | - | AC-013.1-6 | AC-013.7 |
| US-CAM-014 | AC-014.1-5 | AC-014.6-7 | - |
| US-CAM-015 | - | AC-015.1-5 | AC-015.6 |
| US-CAM-016 | - | - | AC-016.1-7 |
| US-CAM-017 | AC-017.1-4 | AC-017.5-7 | - |
| US-CAM-018 | AC-018.1-5 | AC-018.6-7 | - |

---

## Release Plan

### MVP (v1.0.0)

**Scope**: Core campaign creation, execution, and tracking

| Feature | User Stories |
|---------|--------------|
| Campaign CRUD | US-CAM-001, US-CAM-014 |
| Multi-channel Content | US-CAM-002 (email, sms, in_app) |
| Basic Audience | US-CAM-003 (segments only) |
| Scheduled Execution | US-CAM-008 |
| Pause/Resume | US-CAM-009 |
| Basic Metrics | US-CAM-011, US-CAM-012 |
| Compliance | US-CAM-017, US-CAM-018 |

**Target**: Q1 2026

### v1.1.0

**Scope**: Triggered campaigns and A/B testing

| Feature | User Stories |
|---------|--------------|
| Triggered Campaigns | US-CAM-004 |
| A/B Testing | US-CAM-005, US-CAM-006 |
| Throttling | US-CAM-010 |
| Clone | US-CAM-015 |
| WhatsApp/Webhook | US-CAM-002 (full) |

**Target**: Q2 2026

### v1.2.0

**Scope**: Advanced analytics and automation

| Feature | User Stories |
|---------|--------------|
| Conversion Tracking | US-CAM-013 |
| Auto-Winner Selection | US-CAM-007 |
| Advanced Audience (holdouts, estimation) | US-CAM-003 (full) |
| Delete/Archive | US-CAM-016 |

**Target**: Q3 2026

---

## Dependencies

### Technical Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| isA_Data intelligent_query API | External Service | Available |
| isA_Data user_360 API | External Service | Available |
| isA_Creative template API | External Service | Planned |
| notification_service | Internal Service | Available |
| task_service | Internal Service | Available |
| event_service | Internal Service | Available |
| storage_service | Internal Service | Available |
| media_service | Internal Service | Available |

### Organizational Dependencies

| Dependency | Team | Timeline |
|------------|------|----------|
| Audience segment definitions | Data Team | Aligned with MVP |
| Email template library | Creative Team | Before MVP |
| Compliance review | Legal | 2 weeks before MVP |
| Provider rate limit agreements | Operations | Before MVP |

---

## Open Questions

| ID | Question | Owner | Due Date | Status |
|----|----------|-------|----------|--------|
| Q1 | What is the retention policy for campaign messages? | Compliance | 2026-02-15 | Open |
| Q2 | Should we support campaign templates (pre-built)? | Product | 2026-02-20 | Open |
| Q3 | What attribution models are required for conversion? | Analytics | 2026-02-15 | Open |
| Q4 | Maximum variants for A/B testing? | Product | 2026-02-10 | Closed (5) |
| Q5 | Default quiet hours per region? | Compliance | 2026-02-15 | Open |

---

## Glossary

| Term | Definition |
|------|------------|
| **Campaign** | A marketing initiative that delivers messages to targeted users |
| **Segment** | A group of users matching specific criteria |
| **Variant** | An alternative version of campaign content for A/B testing |
| **Trigger** | An event that initiates campaign execution |
| **Throttle** | Rate limiting configuration for message delivery |
| **Holdout** | Control group excluded from receiving messages |
| **Attribution** | Assigning credit for conversions to campaigns |

---

**Document Version**: 1.0.0
**Last Updated**: 2026-02-02
**Product Owner**: Marketing Platform Team
**Status**: Draft
