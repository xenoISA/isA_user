# Compliance Service - Domain Context

## Overview

The Compliance Service is the **regulatory guardian** for the entire isA platform. It provides centralized content moderation, PII detection, prompt injection prevention, and regulatory compliance enforcement (GDPR, PCI-DSS). Every piece of user-generated content, AI prompt, and sensitive data operation flows through the Compliance Service for validation before being processed.

The service acts as a critical safety layer between user input and system processing, ensuring that harmful content is blocked, personal data is protected, and regulatory requirements are met. It operates as a high-throughput, low-latency gatekeeper that must never become a bottleneck.

**Business Context**: Enable secure, compliant AI-powered services by detecting and preventing harmful content, protecting personal data, and ensuring regulatory compliance across all platform interactions.

**Core Value Proposition**: Transform raw user input into verified, compliant content through multi-layer safety checks, intelligent risk assessment, and comprehensive audit trails - protecting both users and the platform from legal and security risks.

---

## Business Taxonomy

### Core Entities

#### 1. Compliance Check
**Definition**: A record of a content compliance evaluation including the check type, result status, risk assessment, and any violations or warnings detected.

**Business Purpose**:
- Evaluate user-generated content for policy violations
- Detect and flag potentially harmful or risky content
- Provide audit trail for regulatory compliance
- Enable human review workflow for borderline cases
- Track compliance patterns and identify repeat offenders

**Key Attributes**:
- Check ID (unique identifier for the compliance check)
- Check Type (content_moderation, pii_detection, prompt_injection, etc.)
- Content Type (text, image, audio, video, prompt, response)
- Status (pass, fail, warning, pending, flagged, blocked)
- Risk Level (none, low, medium, high, critical)
- User ID (account requesting the check)
- Organization ID (optional organizational context)
- Violations (list of detected policy violations)
- Warnings (list of potential issues requiring attention)
- Action Taken (allowed, blocked, flagged_for_review)
- Processing Time (milliseconds to complete check)

**Check States**:
- **Pass**: Content cleared all checks, safe to proceed
- **Warning**: Content allowed but with noted concerns
- **Flagged**: Content requires human review before action
- **Fail**: Content violates policies, action required
- **Blocked**: Content automatically rejected due to critical violations
- **Pending**: Check in progress or awaiting human review

#### 2. Compliance Policy
**Definition**: A configurable rule set that defines what content types to check, which checks to run, and what thresholds trigger violations.

**Business Purpose**:
- Define organization-specific compliance requirements
- Configure check sensitivity and thresholds
- Enable/disable specific check types per organization
- Control automatic blocking vs. human review workflows
- Support multi-tenant compliance configurations

**Key Attributes**:
- Policy ID (unique policy identifier)
- Policy Name (human-readable name)
- Organization ID (null for global policies)
- Content Types (list of applicable content types)
- Check Types (enabled compliance check types)
- Rules (JSONB configuration for thresholds and behaviors)
- Thresholds (score thresholds for each category)
- Auto Block (boolean - automatically block violations)
- Require Human Review (boolean - flag for review)
- Priority (policy precedence order)
- Is Active (boolean - policy enabled status)

**Policy States**:
- **Active**: Policy is enabled and being applied
- **Inactive**: Policy is disabled but preserved
- **Draft**: Policy created but not yet activated

#### 3. Content Moderation Result
**Definition**: Detailed results from content moderation checks including category scores, flagged categories, and recommendations.

**Business Purpose**:
- Classify content across multiple harm categories
- Provide confidence scores for each category
- Enable nuanced decision-making based on severity
- Support appeals and review workflows
- Track moderation patterns over time

**Key Attributes**:
- Check ID (reference to parent compliance check)
- Content Type (type of content being moderated)
- Categories (dictionary of category scores 0.0-1.0)
- Flagged Categories (list of categories exceeding threshold)
- Confidence (overall confidence in the assessment)
- Recommendation (allow, review, block)
- Explanation (human-readable reason for decision)

#### 4. PII Detection Result
**Definition**: Results from personally identifiable information scanning including detected PII types, locations, and redaction recommendations.

**Business Purpose**:
- Identify personal data in content (email, phone, SSN, etc.)
- Protect user privacy by flagging sensitive data exposure
- Support GDPR/CCPA data protection requirements
- Enable automatic PII redaction workflows
- Prevent accidental data leakage

**Key Attributes**:
- Check ID (reference to parent compliance check)
- Detected PII (list with type, masked value, location, confidence)
- PII Count (total instances detected)
- PII Types (distinct types found - email, phone, ssn, credit_card)
- Risk Level (based on sensitivity and volume)
- Needs Redaction (boolean - requires PII removal)

#### 5. Prompt Injection Result
**Definition**: Results from AI prompt security scanning to detect attempts to manipulate AI system behavior.

**Business Purpose**:
- Protect AI systems from manipulation attempts
- Detect jailbreak and override patterns
- Identify suspicious prompt structures
- Prevent unauthorized system instruction changes
- Ensure AI safety and reliability

**Key Attributes**:
- Check ID (reference to parent compliance check)
- Is Injection Detected (boolean - injection attempt found)
- Injection Type (direct, indirect, jailbreak, none)
- Confidence (confidence score 0.0-1.0)
- Detected Patterns (list of matched injection patterns)
- Suspicious Tokens (unusual tokens found)
- Recommendation (allow, review, block)
- Explanation (description of detection)

#### 6. User Consent Record
**Definition**: Record of user consent for data processing activities, required for GDPR compliance.

**Business Purpose**:
- Track user consent for different data processing types
- Enable consent withdrawal (right to revoke)
- Support GDPR Article 7 requirements
- Provide audit trail of consent history
- Enable consent-based feature access control

**Key Attributes**:
- User ID (account giving consent)
- Consent Type (data_processing, marketing, analytics, ai_training)
- Granted (boolean - consent given or revoked)
- Granted At (timestamp of consent action)
- IP Address (for consent verification)
- User Agent (for consent verification)

---

## Domain Scenarios

### Scenario 1: Real-Time Content Moderation Check
**Actor**: AI Service, Chat Application
**Trigger**: User submits a message or prompt for AI processing
**Flow**:
1. AI Service receives user prompt for processing
2. AI Service calls `POST /api/v1/compliance/check` with prompt content
3. Compliance Service generates unique check_id
4. Compliance Service retrieves applicable policy for organization
5. Compliance Service runs concurrent checks:
   - Content moderation (OpenAI Moderation + local rules)
   - PII detection (regex patterns for sensitive data)
   - Prompt injection detection (pattern matching)
6. Compliance Service evaluates results against policy thresholds
7. Determines overall status (pass/fail/warning) and risk level
8. Records check in PostgreSQL database
9. Publishes `compliance.check.performed` event to NATS
10. If violations detected, publishes `compliance.violation.detected` event
11. Returns ComplianceCheckResponse with decision
12. AI Service proceeds or blocks based on response
13. Audit Service records compliance check for reporting

**Outcome**: User content validated in <200ms, violations blocked, audit trail created

### Scenario 2: Batch Content Moderation
**Actor**: Media Service, Bulk Upload System
**Trigger**: User uploads multiple files or messages for processing
**Flow**:
1. Media Service receives batch of user content (e.g., 50 images)
2. Media Service calls `POST /api/v1/compliance/check/batch` with items list
3. Compliance Service iterates through items sequentially
4. For each item, performs full compliance check workflow
5. Aggregates results (passed, failed, flagged counts)
6. Calculates summary statistics (pass rate, avg processing time)
7. Returns BatchComplianceCheckResponse with all results
8. Media Service processes passed items, rejects failed items
9. Flagged items queued for human review

**Outcome**: Efficient batch processing, consistent policy enforcement across all items

### Scenario 3: PII Detection and Redaction
**Actor**: Document Service, Storage Service
**Trigger**: User uploads document or enters text containing potential PII
**Flow**:
1. Document Service receives user content
2. Calls Compliance Service with check_types: ["pii_detection"]
3. Compliance Service scans content using regex patterns:
   - Email addresses (`[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}`)
   - Phone numbers (`\d{3}[-.]?\d{3}[-.]?\d{4}`)
   - Social Security Numbers (`\d{3}-\d{2}-\d{4}`)
   - Credit card numbers (`\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}`)
   - IP addresses (`(?:\d{1,3}\.){3}\d{1,3}`)
4. Masks detected PII values (first 2 + last 2 chars visible)
5. Calculates risk level based on PII count and types
6. Returns PIIDetectionResult with needs_redaction flag
7. Document Service applies redaction if needed
8. If critical PII (SSN, credit card), blocks content

**Outcome**: Personal data protected, GDPR/CCPA requirements met, data leakage prevented

### Scenario 4: Prompt Injection Prevention
**Actor**: AI Gateway, Chatbot Service
**Trigger**: User submits potentially malicious prompt
**Flow**:
1. AI Gateway receives user prompt: "Ignore previous instructions..."
2. Calls Compliance Service with check_types: ["prompt_injection"]
3. Compliance Service analyzes prompt structure:
   - Checks for injection patterns ("ignore previous", "you are now", etc.)
   - Detects suspicious tokens (<|, |>, ###, ```)
   - Evaluates overall manipulation risk
4. Pattern match found: "ignore\s+(previous|above|prior)\s+(instructions)"
5. Confidence score: 0.85 (high confidence injection attempt)
6. Status: FAIL, Risk: HIGH, Recommendation: block
7. Returns result to AI Gateway
8. AI Gateway rejects prompt, returns safe error to user
9. Publishes `compliance.violation.detected` event
10. User flagged for potential abuse monitoring

**Outcome**: AI system protected from manipulation, attack logged for analysis

### Scenario 5: GDPR User Data Export
**Actor**: User, Privacy Portal
**Trigger**: User requests their data under GDPR Article 15/20
**Flow**:
1. User navigates to privacy settings and requests data export
2. Portal calls `GET /api/v1/compliance/user/{user_id}/data-export?format=json`
3. Compliance Service validates user authorization
4. Retrieves all compliance checks for user from database
5. Compiles export package:
   - All compliance check records
   - Consent history
   - Violation history
   - Statistics summary
6. Formats as JSON or CSV based on request
7. Returns downloadable file with all user data
8. Logs data export event for audit trail

**Outcome**: User receives complete data export within regulatory timeframe

### Scenario 6: GDPR Right to Erasure
**Actor**: User, Admin, Privacy Portal
**Trigger**: User requests account deletion under GDPR Article 17
**Flow**:
1. User requests data deletion with confirmation
2. Portal calls `DELETE /api/v1/compliance/user/{user_id}/data?confirmation=CONFIRM_DELETE`
3. Compliance Service validates confirmation parameter
4. Retrieves count of records to be deleted
5. Deletes all compliance checks for user
6. Deletes all consent records for user
7. Logs deletion event with metadata for audit
8. Publishes internal event for other services to clean up
9. Returns success response with deleted record count

**Outcome**: User data erased from compliance records, audit log preserved

### Scenario 7: Compliance Report Generation
**Actor**: Compliance Officer, Admin Dashboard
**Trigger**: Monthly compliance report required for stakeholders
**Flow**:
1. Compliance Officer accesses reporting dashboard
2. Sets date range and filters (organization, check types, risk levels)
3. Dashboard calls `POST /api/v1/compliance/reports` with parameters
4. Compliance Service generates unique report_id
5. Queries database for:
   - Total checks in period
   - Pass/fail/flagged breakdown
   - Violations by type and category
   - High-risk incident count
   - Top violators list
6. Calculates trends and aggregations
7. Returns comprehensive ComplianceReportResponse
8. Dashboard renders charts and tables
9. Report can be exported as PDF

**Outcome**: Stakeholders have visibility into platform compliance health

### Scenario 8: Human Review Workflow
**Actor**: Moderator, Admin
**Trigger**: Content flagged for human review (borderline cases)
**Flow**:
1. Content check results in FLAGGED status (medium risk)
2. Compliance Service stores check with human_review_required=true
3. Moderator accesses `GET /api/v1/compliance/reviews/pending`
4. Retrieves list of items awaiting review (max 50)
5. Moderator reviews flagged content and context
6. Moderator calls `PUT /api/v1/compliance/reviews/{check_id}`:
   - reviewed_by: moderator ID
   - status: pass or fail (final decision)
   - review_notes: explanation
7. Compliance Service updates check record
8. Sets reviewed_at timestamp
9. Publishes event with final decision
10. Original service receives decision and takes action

**Outcome**: Borderline cases handled with human judgment, decisions documented

---

## Domain Events

### Published Events

#### 1. compliance.check.performed
**Trigger**: Any compliance check completes (pass, fail, warning, flagged)
**Payload**:
- check_id: Unique check identifier
- user_id: User who initiated the check
- organization_id: Optional organization context
- check_type: Type of check performed (content_moderation, pii_detection, etc.)
- content_type: Type of content checked (text, image, prompt, etc.)
- status: Result status (pass, fail, warning, flagged, blocked)
- risk_level: Assessed risk level (none, low, medium, high, critical)
- violations_count: Number of violations detected
- warnings_count: Number of warnings issued
- action_taken: Action taken (allowed, blocked, flagged_for_review)
- processing_time_ms: Time to complete check in milliseconds
- timestamp: ISO 8601 event timestamp
- metadata: Additional context data

**Subscribers**:
- **Audit Service**: Records compliance activity for regulatory reporting
- **Analytics Service**: Tracks compliance metrics and trends
- **Billing Service**: Metering for compliance check API usage
- **Notification Service**: Alerts for high-risk checks

#### 2. compliance.violation.detected
**Trigger**: Compliance check detects policy violation (status FAIL or BLOCKED)
**Payload**:
- check_id: Unique check identifier
- user_id: User who violated policy
- organization_id: Optional organization context
- violations: List of violation details (issue, category, severity)
- risk_level: Risk level of violations (high, critical)
- action_taken: Action taken (blocked, flagged_for_review)
- requires_review: Boolean - needs human review
- blocked_content: Boolean - content was blocked
- timestamp: ISO 8601 event timestamp
- metadata: Additional context data

**Subscribers**:
- **Audit Service**: Records violation for compliance reporting
- **Notification Service**: Sends alert to admins/moderators
- **Account Service**: May flag user account for monitoring
- **Authorization Service**: May restrict user permissions
- **Analytics Service**: Tracks violation patterns

#### 3. compliance.warning.issued
**Trigger**: Compliance check issues warnings (content allowed with concerns)
**Payload**:
- check_id: Unique check identifier
- user_id: User who received warning
- organization_id: Optional organization context
- warnings: List of warning details
- warning_types: Categories of warnings issued
- risk_level: Risk level (typically low or medium)
- allowed_with_warning: Boolean - content was allowed
- timestamp: ISO 8601 event timestamp
- metadata: Additional context data

**Subscribers**:
- **Audit Service**: Records warning for trend analysis
- **Analytics Service**: Tracks warning patterns
- **Notification Service**: May notify user of concerning content

### Subscribed Events

#### 1. user.created
**Source**: account_service
**Handler**: Log new user for compliance monitoring baseline
**Side Effects**:
- Initialize user consent record with defaults
- Set up compliance tracking for user

#### 2. order.completed
**Source**: order_service
**Handler**: Validate order for PCI-DSS compliance
**Side Effects**:
- Check for exposed payment data in order metadata
- Flag any compliance issues with transaction

---

## Core Concepts

### Compliance Check Lifecycle
1. **Request**: External service requests compliance check
2. **Policy Resolution**: Applicable policy determined by organization/content type
3. **Parallel Checks**: Multiple check types run concurrently
4. **Result Aggregation**: Individual results combined into overall status
5. **Action Determination**: Based on status and policy, action is determined
6. **Recording**: Check recorded in database with full context
7. **Event Publishing**: Appropriate events published to NATS
8. **Response**: Caller receives decision and can take action

### Risk Level Hierarchy
- **NONE** (0): No risk detected, content is safe
- **LOW** (1): Minor concerns, allowed with logging
- **MEDIUM** (2): Moderate risk, may require review
- **HIGH** (3): Significant risk, likely blocked
- **CRITICAL** (4): Severe risk, always blocked, immediate action

### Content Moderation Categories
- **Hate Speech**: Discrimination, prejudice, slurs
- **Violence**: Threats, graphic violence, harm
- **Sexual**: Adult content, explicit material
- **Harassment**: Bullying, targeted abuse
- **Self-Harm**: Suicide, self-injury promotion
- **Illegal**: Criminal activity, drugs
- **Spam**: Unsolicited, repetitive content
- **Misinformation**: False information, propaganda
- **Child Safety**: Content involving minors

### Separation of Concerns
**Compliance Service owns**:
- Content moderation decisions
- PII detection and risk assessment
- Prompt injection detection
- Compliance check records and history
- Policy configuration and thresholds
- User consent management
- GDPR data export/deletion
- Compliance reporting and analytics

**Compliance Service does NOT own**:
- User authentication (auth_service)
- User account management (account_service)
- Content storage (storage_service, media_service)
- Payment processing (payment_service)
- Organization management (organization_service)
- Audit logging persistence (audit_service)

### Check Type Capabilities
- **CONTENT_MODERATION**: Text/image/audio/video safety classification
- **PII_DETECTION**: Personal data identification (email, phone, SSN, etc.)
- **PROMPT_INJECTION**: AI prompt manipulation detection
- **TOXICITY**: Harmful language detection (via Perspective API)
- **COPYRIGHT**: Copyrighted content detection (placeholder)
- **AGE_RESTRICTION**: Age-appropriate content verification
- **GDPR_COMPLIANCE**: GDPR regulation checks
- **HIPAA_COMPLIANCE**: Healthcare data compliance
- **CONTENT_SAFETY**: General safety assessment

### Event-Driven Architecture
- All compliance decisions publish events for observability
- Violations trigger immediate alerts to monitoring systems
- Asynchronous processing enables high throughput
- Event consumers can react to compliance events independently
- Audit trail created automatically via event persistence

---

## Business Rules (High-Level)

### Content Moderation Rules
- **BR-CMP-001**: All user-generated text content must pass content moderation before processing
- **BR-CMP-002**: Content with moderation score >= 0.9 is automatically BLOCKED
- **BR-CMP-003**: Content with moderation score >= 0.7 is FAILED and requires action
- **BR-CMP-004**: Content with moderation score >= 0.5 is FLAGGED for review
- **BR-CMP-005**: Content with moderation score >= 0.3 receives WARNING but is allowed
- **BR-CMP-006**: Content with moderation score < 0.3 PASSES compliance checks
- **BR-CMP-007**: Multiple flagged categories increase overall risk level

### PII Detection Rules
- **BR-PII-001**: All text content submitted for AI processing must be scanned for PII
- **BR-PII-002**: Detection of 5+ PII instances results in CRITICAL risk level
- **BR-PII-003**: Detection of 3-4 PII instances results in HIGH risk level
- **BR-PII-004**: Detection of 1-2 PII instances results in MEDIUM risk level
- **BR-PII-005**: Credit card numbers always trigger HIGH risk regardless of count
- **BR-PII-006**: SSN detection always triggers CRITICAL risk regardless of count
- **BR-PII-007**: Detected PII must be masked in logs (show only first 2 and last 2 chars)

### Prompt Injection Rules
- **BR-INJ-001**: All AI prompts must be scanned for injection attempts
- **BR-INJ-002**: Detection of direct injection patterns (confidence >= 0.8) results in BLOCK
- **BR-INJ-003**: Suspicious patterns (confidence 0.5-0.8) trigger REVIEW requirement
- **BR-INJ-004**: Special tokens (<|, |>) in user input trigger warning
- **BR-INJ-005**: "System:" or similar prefixes in user content are flagged
- **BR-INJ-006**: Known jailbreak phrases result in immediate block

### Policy Management Rules
- **BR-POL-001**: Organization-specific policies take precedence over global policies
- **BR-POL-002**: Only active policies are applied to compliance checks
- **BR-POL-003**: Policy thresholds can customize default score cutoffs
- **BR-POL-004**: Policy auto_block setting overrides default review workflow
- **BR-POL-005**: Policies are matched by content_type first, then by priority

### GDPR Compliance Rules
- **BR-GDR-001**: Users can request data export at any time (Article 15/20)
- **BR-GDR-002**: Users can request data deletion with confirmation (Article 17)
- **BR-GDR-003**: Deletion requires explicit confirmation string "CONFIRM_DELETE"
- **BR-GDR-004**: Data exports must include all compliance checks for user
- **BR-GDR-005**: Consent records must track granted status, timestamp, IP, and user agent
- **BR-GDR-006**: Consent can be revoked at any time (Article 7)
- **BR-GDR-007**: Data retention default is 7 years (2555 days) for compliance records

### PCI-DSS Compliance Rules
- **BR-PCI-001**: Credit card numbers must never be stored in plain text
- **BR-PCI-002**: Full PAN (Primary Account Number) must be masked in all logs
- **BR-PCI-003**: Card data exposure detection triggers CRITICAL violation
- **BR-PCI-004**: Visa, Mastercard, Amex, Discover patterns must be detected
- **BR-PCI-005**: Card data detection results in content blocking recommendation

### Human Review Rules
- **BR-REV-001**: FLAGGED content requires human review before final decision
- **BR-REV-002**: HIGH and CRITICAL risk items are queued for priority review
- **BR-REV-003**: Reviewers must provide review_notes for all decisions
- **BR-REV-004**: Review decisions are final and update the original check record
- **BR-REV-005**: reviewed_at timestamp is set when review is completed

### Event Publishing Rules
- **BR-EVT-001**: All compliance checks publish `compliance.check.performed` event
- **BR-EVT-002**: Violations (FAIL/BLOCKED) publish `compliance.violation.detected` event
- **BR-EVT-003**: Warnings publish `compliance.warning.issued` event
- **BR-EVT-004**: Event publishing failures are logged but don't block check response
- **BR-EVT-005**: Events include full context for downstream processing

### Data Consistency Rules
- **BR-CON-001**: Compliance check creation is atomic (PostgreSQL transaction)
- **BR-CON-002**: Check ID is generated as UUID before any processing
- **BR-CON-003**: Processing time is measured from request start to response
- **BR-CON-004**: All timestamps use UTC (datetime.utcnow())
- **BR-CON-005**: Content hashes are SHA-256 for deduplication

---

## Compliance Service in the Ecosystem

### Upstream Dependencies
- **Account Service**: User identity and organization context
- **Auth Service**: JWT validation for authenticated endpoints
- **PostgreSQL gRPC Service**: Persistent storage for compliance records
- **NATS Event Bus**: Event publishing infrastructure
- **Consul**: Service discovery and health checks
- **API Gateway**: Request routing and rate limiting
- **OpenAI Moderation API**: External content moderation (optional)

### Downstream Consumers
- **AI Gateway**: Checks prompts before sending to AI models
- **Chat Service**: Validates messages before processing
- **Media Service**: Checks uploaded images/videos/audio
- **Document Service**: Scans documents for PII and violations
- **Storage Service**: Validates file uploads
- **Memory Service**: Checks memory content before storage
- **Audit Service**: Records all compliance activity
- **Analytics Service**: Tracks compliance metrics
- **Notification Service**: Sends violation alerts
- **Billing Service**: Meters compliance API usage

### Integration Patterns
- **Synchronous REST**: Real-time compliance checks via FastAPI
- **Asynchronous Events**: NATS for violation notifications
- **Service Discovery**: Consul for dynamic service location
- **Protocol Buffers**: PostgreSQL gRPC communication
- **Health Checks**: `/health` and `/status` endpoints
- **Batch Processing**: `/check/batch` for bulk operations

### Dependency Injection
- **Repository Pattern**: ComplianceRepository for data access
- **Protocol Interfaces**: ComplianceRepositoryProtocol, EventBusProtocol
- **Factory Pattern**: create_compliance_service() for production instances
- **Mock-Friendly**: Protocols enable test doubles and mocks
- **Configuration Injection**: ConfigManager for environment-specific settings

---

## Success Metrics

### Compliance Quality Metrics
- **True Positive Rate**: % of actual violations correctly detected (target: >95%)
- **False Positive Rate**: % of safe content incorrectly flagged (target: <5%)
- **Violation Detection Coverage**: % of violation types accurately detected
- **PII Detection Accuracy**: % of PII instances correctly identified (target: >99%)

### Performance Metrics
- **Check Latency (P50)**: Median compliance check time (target: <100ms)
- **Check Latency (P95)**: 95th percentile check time (target: <200ms)
- **Check Latency (P99)**: 99th percentile check time (target: <500ms)
- **Batch Throughput**: Checks per second for batch operations (target: >50/sec)
- **Concurrent Capacity**: Simultaneous checks supported (target: >1000)

### Availability Metrics
- **Service Uptime**: Compliance Service availability (target: 99.9%)
- **Database Connectivity**: PostgreSQL connection success rate (target: 99.99%)
- **Event Publishing Success**: % of events successfully published (target: >99.5%)
- **External API Availability**: OpenAI Moderation API connectivity

### Business Metrics
- **Daily Compliance Checks**: Total checks processed per day
- **Violation Rate**: % of checks resulting in violations
- **Block Rate**: % of content automatically blocked
- **Review Queue Size**: Pending human reviews at any time (target: <100)
- **Review Turnaround Time**: Average time to complete human review (target: <4hr)

### Regulatory Metrics
- **GDPR Export SLA**: Data export requests completed within 30 days (target: 100%)
- **GDPR Deletion SLA**: Deletion requests completed within 30 days (target: 100%)
- **Consent Record Accuracy**: % of users with valid consent records
- **Audit Trail Completeness**: % of compliance events with full context

### System Health Metrics
- **PostgreSQL Query Performance**: Average query execution time (target: <20ms)
- **NATS Event Throughput**: Events published per second
- **Consul Registration Health**: Service registration success rate
- **Memory Usage**: Service memory consumption stability
- **Error Rate**: % of requests resulting in 5xx errors (target: <0.1%)

---

## Glossary

**Compliance Check**: Evaluation of content against platform policies and regulations
**Content Moderation**: Process of reviewing content for harmful or inappropriate material
**PII (Personally Identifiable Information)**: Data that can identify an individual (email, phone, SSN)
**Prompt Injection**: Technique to manipulate AI systems by embedding malicious instructions
**Risk Level**: Assessment of threat severity (none, low, medium, high, critical)
**Violation**: Content that fails compliance checks and violates policies
**Warning**: Content that passes but contains concerning elements
**Flagged Content**: Content requiring human review before final decision
**Human Review**: Manual moderation by trained personnel
**Policy**: Configurable rule set defining compliance requirements
**Threshold**: Score cutoff that triggers a specific action (block, review, allow)
**GDPR**: General Data Protection Regulation (EU privacy law)
**PCI-DSS**: Payment Card Industry Data Security Standard
**CCPA**: California Consumer Privacy Act
**Right to Erasure**: GDPR Article 17 - right to have personal data deleted
**Right to Access**: GDPR Article 15 - right to receive copy of personal data
**Data Portability**: GDPR Article 20 - right to receive data in portable format
**Consent**: User permission for specific data processing activities
**Audit Trail**: Chronological record of compliance activities
**Event Bus**: NATS messaging system for asynchronous event publishing
**Repository Pattern**: Data access abstraction layer
**Jailbreak**: Attempt to bypass AI safety restrictions
**Toxicity Score**: Measure of harmful or offensive language
**Content Hash**: SHA-256 hash for content deduplication

---

**Document Version**: 1.0
**Last Updated**: 2025-12-22
**Maintained By**: Compliance Service Team
