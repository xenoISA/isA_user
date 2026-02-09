# Compliance Service Logic Contract

**Business Rules and Specifications for Compliance Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for compliance service behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [State Machines](#state-machines)
3. [Edge Cases](#edge-cases)
4. [Data Consistency Rules](#data-consistency-rules)
5. [Integration Contracts](#integration-contracts)
6. [Error Handling Contracts](#error-handling-contracts)
7. [Performance SLAs](#performance-slas)

---

## Business Rules

### Compliance Check Entity Rules

### BR-ENT-001: Check ID Generation
**Given**: Valid compliance check request
**When**: Compliance check is performed
**Then**:
- System generates unique check_id with format `chk_<uuid>`
- ID is immutable after creation
- ID must be globally unique across all checks

**Validation Rules**:
- Format: `chk_[a-f0-9]{32}`
- Cannot be user-provided
- Generated using UUID4

---

### BR-ENT-002: User ID Required
**Given**: Compliance check request
**When**: Request is validated
**Then**:
- `user_id` must be provided and non-empty
- Empty user_id → **ValidationError**
- Whitespace-only user_id → **ValidationError**

**Validation Rules**:
- Required field on all check requests
- Used for audit trail and data ownership
- Links to account_service user

---

### BR-ENT-003: Content Type Classification
**Given**: Compliance check request with content
**When**: Content type is validated
**Then**:
- Must be one of: `text`, `image`, `audio`, `video`, `file`, `prompt`, `response`
- Content type determines applicable check algorithms
- Text content requires `content` field
- Non-text content requires `content_id` or `content_url`

**Content Type Rules**:
- `text`, `prompt`, `response` → Use text-based checks
- `image` → Use image moderation API
- `audio`, `video` → Use media analysis
- `file` → Content-sniff to determine subtype

---

### BR-ENT-004: Check Type Selection
**Given**: Compliance check request
**When**: Check types are specified
**Then**:
- At least one check type required
- Valid types: `content_moderation`, `pii_detection`, `prompt_injection`, `toxicity`, `copyright`, `age_restriction`, `gdpr_compliance`, `hipaa_compliance`, `content_safety`
- Default: `[content_moderation]` if not specified
- Multiple check types execute in parallel

**Implementation**:
```python
check_types: List[ComplianceCheckType] = Field(
    default_factory=lambda: [ComplianceCheckType.CONTENT_MODERATION]
)
```

---

### BR-ENT-005: Content Hash Generation
**Given**: Content provided for compliance check
**When**: Check is processed
**Then**:
- SHA-256 hash computed for content
- Hash stored with check record
- Used for duplicate detection and caching
- Hash enables idempotent re-checks

**Hash Rules**:
- Computed before any processing
- Stored in `content_hash` field
- Text content: UTF-8 encoded before hashing

---

### Content Moderation Rules

### BR-MOD-001: Category Score Calculation
**Given**: Text content for moderation
**When**: Content moderation check executes
**Then**:
- Returns scores for each category (0.0 to 1.0)
- Categories: `hate_speech`, `violence`, `sexual`, `harassment`, `self_harm`, `illegal`, `spam`, `misinformation`, `child_safety`
- Scores represent probability/confidence of category presence
- Score > threshold → Category flagged

**Default Thresholds**:
```python
DEFAULT_THRESHOLDS = {
    "hate_speech": 0.7,
    "violence": 0.7,
    "sexual": 0.8,
    "harassment": 0.7,
    "self_harm": 0.6,
    "illegal": 0.7,
    "spam": 0.8,
    "misinformation": 0.75,
    "child_safety": 0.5  # Most sensitive
}
```

---

### BR-MOD-002: Risk Level Determination
**Given**: Content moderation scores computed
**When**: Risk level is calculated
**Then**:
- `none`: No categories flagged, max score < 0.3
- `low`: Max score 0.3-0.5, no critical categories
- `medium`: Max score 0.5-0.7, or one non-critical flag
- `high`: Max score 0.7-0.9, or multiple flags
- `critical`: Any score > 0.9 OR child_safety flag

**Priority Categories** (elevate risk level):
- `child_safety` → Always CRITICAL if flagged
- `self_harm` → Minimum HIGH if flagged
- `illegal` → Minimum HIGH if flagged

---

### BR-MOD-003: Recommendation Generation
**Given**: Risk level determined
**When**: Action recommendation generated
**Then**:
- `allow`: Risk level `none` or `low`
- `review`: Risk level `medium`
- `block`: Risk level `high` or `critical`

**Override Rules**:
- Policy `auto_block=false` → `review` instead of `block`
- Policy `require_human_review=true` → Always `review` (never auto-allow)

---

### BR-MOD-004: Confidence Score Aggregation
**Given**: Multiple category scores available
**When**: Overall confidence computed
**Then**:
- Confidence = weighted average of detection models
- Higher confidence = more certain of assessment
- Low confidence triggers human review
- Threshold: confidence < 0.7 → `require_human_review`

**Formula**:
```python
confidence = sum(category_confidence * category_weight) / sum(weights)
```

---

### PII Detection Rules

### BR-PII-001: Pattern-Based Detection
**Given**: Text content for PII detection
**When**: PII detection check executes
**Then**:
- Regex patterns match common PII formats
- Detected PII types: `email`, `phone`, `ssn`, `credit_card`, `passport`, `driver_license`, `ip_address`, `address`, `name`, `date_of_birth`, `medical_info`
- Each detection includes: type, masked value, location, confidence

**Regex Patterns**:
```python
PII_PATTERNS = {
    "email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    "phone": r'(\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
    "ssn": r'\b\d{3}[-]?\d{2}[-]?\d{4}\b',
    "credit_card": r'\b(?:4[0-9]{3}|5[1-5][0-9]{2}|3[47][0-9]{2}|6(?:011|5[0-9]{2}))[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b',
    "ip_address": r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
}
```

---

### BR-PII-002: PII Risk Assessment
**Given**: PII detected in content
**When**: Risk level calculated
**Then**:
- `none`: No PII detected
- `low`: Only email or name detected
- `medium`: Phone or IP address detected
- `high`: SSN, credit card, or passport detected
- `critical`: Multiple high-risk PII OR medical info

**PII Severity Mapping**:
```python
PII_SEVERITY = {
    "email": "low",
    "name": "low",
    "phone": "medium",
    "ip_address": "medium",
    "address": "medium",
    "date_of_birth": "medium",
    "ssn": "high",
    "credit_card": "high",
    "passport": "high",
    "driver_license": "high",
    "medical_info": "critical"
}
```

---

### BR-PII-003: Value Masking
**Given**: PII value detected
**When**: Detection result returned
**Then**:
- Original value never stored in plain text
- Masked format preserves structure recognition
- Email: `t***@example.com`
- Phone: `555-***-****`
- SSN: `***-**-1234`
- Credit Card: `4532-****-****-0000`

**Masking Rules**:
- Keep first and last portions for verification
- Middle portions replaced with asterisks
- Never expose full PII in logs or responses

---

### BR-PII-004: Redaction Recommendation
**Given**: PII detected with severity ≥ medium
**When**: Detection result generated
**Then**:
- `needs_redaction=true` if any high+ severity PII
- Redaction locations provided for automated removal
- Client responsible for implementing redaction
- Redacted content can be re-submitted for verification

---

### Prompt Injection Detection Rules

### BR-INJ-001: Pattern-Based Injection Detection
**Given**: Prompt or text content for injection check
**When**: Prompt injection detection executes
**Then**:
- Checks for known injection patterns
- Patterns: `ignore previous`, `system prompt`, `reveal`, `bypass`, `jailbreak`
- Detection confidence based on pattern match strength
- Multiple patterns increase confidence

**Injection Patterns**:
```python
INJECTION_PATTERNS = [
    r'ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|context|prompts?)',
    r'(reveal|show|display|print)\s+(system\s+)?prompt',
    r'forget\s+(everything|all|your)\s+(instructions|rules)',
    r'you\s+are\s+(now|actually)\s+(a|an)',
    r'(bypass|ignore|disable)\s+(safety|content)\s+(filter|block)',
    r'```(system|admin|root)',
    r'\[INST\]|\[/INST\]|<\|im_start\|>|<\|im_end\|>'
]
```

---

### BR-INJ-002: Injection Type Classification
**Given**: Injection pattern detected
**When**: Injection type determined
**Then**:
- `direct`: Explicit instruction override attempt
- `indirect`: Embedded malicious content in data
- `jailbreak`: Attempt to bypass safety guidelines
- Type affects risk level and response

**Classification Rules**:
- "ignore previous" → `direct`
- "you are now" → `jailbreak`
- Hidden instructions in code blocks → `indirect`

---

### BR-INJ-003: Injection Risk Escalation
**Given**: Any injection detected
**When**: Risk level calculated
**Then**:
- Minimum risk level: HIGH
- Jailbreak attempts: CRITICAL
- Always requires human review OR auto-block
- Never auto-allow detected injections

**Risk Mapping**:
```python
INJECTION_RISK = {
    "direct": RiskLevel.HIGH,
    "indirect": RiskLevel.HIGH,
    "jailbreak": RiskLevel.CRITICAL
}
```

---

### BR-INJ-004: Suspicious Token Extraction
**Given**: Injection patterns found
**When**: Detection result generated
**Then**:
- Extract tokens that triggered detection
- Include in `suspicious_tokens` list
- Limit to 10 tokens max
- Used for audit and pattern improvement

---

### Policy Management Rules

### BR-POL-001: Policy Creation
**Given**: Valid policy creation request
**When**: Policy is created
**Then**:
- Generate unique `policy_id` with format `pol_<uuid>`
- Policy name must be unique within organization
- Global policies (organization_id=null) have system priority
- `is_active=true` by default

**Required Fields**:
- `policy_name`: Non-empty, max 100 chars
- `content_types`: At least one type
- `check_types`: At least one type
- `rules`: Valid JSON object

---

### BR-POL-002: Policy Scope Resolution
**Given**: Compliance check for user in organization
**When**: Policy lookup performed
**Then**:
- Check organization-specific policies first
- Fall back to global policies
- Higher priority policies take precedence
- First matching policy applied

**Resolution Order**:
1. Organization policy with highest priority
2. Global policy with highest priority
3. System defaults if no policy matches

---

### BR-POL-003: Policy Rule Validation
**Given**: Policy rules configuration
**When**: Rules are validated
**Then**:
- Thresholds must be 0.0-1.0
- Check types must be valid enum values
- Content types must be valid enum values
- Invalid rules → **ValidationError**

**Example Valid Rules**:
```json
{
    "max_toxicity_score": 0.7,
    "block_pii_types": ["ssn", "credit_card"],
    "require_review_categories": ["child_safety"]
}
```

---

### BR-POL-004: Policy Priority Ordering
**Given**: Multiple policies match content
**When**: Policy selected for application
**Then**:
- Higher priority number = higher precedence
- Same priority → Organization policy wins
- Same priority + scope → Most recently created
- Default priority: 100

---

### Human Review Rules

### BR-REV-001: Review Queue Flagging
**Given**: Compliance check with `require_human_review=true`
**When**: Check completes
**Then**:
- Check marked `human_review_required=true`
- Status set to `flagged` (not pass/fail)
- Added to pending review queue
- Notification sent if configured

**Flagging Triggers**:
- Policy requires human review
- Confidence score < 0.7
- Medium risk level content
- Specific categories flagged (configurable)

---

### BR-REV-002: Review Status Update
**Given**: Human reviewer updates check
**When**: Review submitted
**Then**:
- `status` updated to reviewer decision (pass/fail/blocked)
- `reviewed_by` set to reviewer ID
- `reviewed_at` set to current timestamp
- `review_notes` optionally captured
- Event published: `compliance.review_completed`

**Allowed Status Updates**:
- `flagged` → `pass` (content approved)
- `flagged` → `fail` (content rejected)
- `flagged` → `blocked` (content blocked + action taken)

---

### BR-REV-003: Review Cannot Change Final Status
**Given**: Check with final status (pass/fail/blocked)
**When**: Review update attempted
**Then**:
- Return **ValidationError**: "Cannot update finalized check"
- Only `flagged` status can be reviewed
- Appeals require new check submission

---

### BR-REV-004: Review Timeout
**Given**: Check in `flagged` status
**When**: No review after 24 hours
**Then**:
- Auto-escalate to supervisor queue
- Notification sent to compliance team
- Risk level preserved
- No auto-decision (requires human action)

---

### GDPR Compliance Rules

### BR-GDPR-001: Data Export (Article 15 & 20)
**Given**: User requests data export
**When**: Export endpoint called
**Then**:
- Return all compliance check records for user
- Include all stored metadata
- Support JSON and CSV formats
- Include summary statistics

**Export Data**:
```json
{
    "user_id": "user_123",
    "export_date": "2025-10-22T10:00:00Z",
    "export_type": "gdpr_data_export",
    "total_checks": 50,
    "checks": [...],
    "statistics": {...}
}
```

---

### BR-GDPR-002: Data Deletion (Article 17)
**Given**: User requests data deletion
**When**: Delete endpoint called with confirmation
**Then**:
- Delete all compliance check records for user
- Confirmation string "CONFIRM_DELETE" required
- Log deletion to audit trail
- Return count of deleted records
- Event published: `compliance.user_data_deleted`

**Deletion Rules**:
- Hard delete (not soft delete)
- Irreversible operation
- Audit log entry preserved (anonymized)

---

### BR-GDPR-003: Consent Management (Article 7)
**Given**: User updates consent preference
**When**: Consent endpoint called
**Then**:
- Store consent type and granted status
- Record timestamp and IP (if available)
- Valid consent types: `data_processing`, `marketing`, `analytics`, `ai_training`
- Event published: `compliance.consent_updated`

**Consent Record**:
```python
{
    "user_id": "user_123",
    "consent_type": "analytics",
    "granted": True,
    "timestamp": "2025-10-22T10:00:00Z"
}
```

---

### BR-GDPR-004: Data Summary (Article 15)
**Given**: User requests data summary
**When**: Summary endpoint called
**Then**:
- Return categories of data stored
- Include record counts per category
- Show date range of data
- Provide export/delete URLs
- Include retention policy information

---

### PCI-DSS Compliance Rules

### BR-PCI-001: Credit Card Detection
**Given**: Content submitted for PCI check
**When**: Card data check executes
**Then**:
- Detect Visa, Mastercard, Amex, Discover patterns
- Return `pci_compliant=false` if card data found
- Mask detected card numbers
- Severity: CRITICAL

**Card Patterns**:
```python
CARD_PATTERNS = {
    "visa": r'\b4[0-9]{3}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b',
    "mastercard": r'\b5[1-5][0-9]{2}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b',
    "amex": r'\b3[47][0-9]{2}[-\s]?[0-9]{6}[-\s]?[0-9]{5}\b',
    "discover": r'\b6(?:011|5[0-9]{2})[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b'
}
```

---

### BR-PCI-002: Card Violation Response
**Given**: Credit card data detected
**When**: Violation response generated
**Then**:
- Return PCI requirement reference
- Include masked card details
- Recommend tokenization/encryption
- Action required: `block_content`

**Response Structure**:
```json
{
    "pci_compliant": false,
    "violation": "credit_card_data_exposed",
    "severity": "critical",
    "detected_cards": [{"type": "visa", "masked_number": "4532-****-****-0000"}],
    "pci_requirement": "PCI-DSS Requirement 3.4 - Render PAN unreadable",
    "action_required": "block_content"
}
```

---

### Batch Processing Rules

### BR-BAT-001: Batch Size Limits
**Given**: Batch compliance check request
**When**: Batch is validated
**Then**:
- Minimum items: 1
- Maximum items: 100
- Empty batch → **ValidationError**
- Oversized batch → **ValidationError**

---

### BR-BAT-002: Batch Result Aggregation
**Given**: Batch check completes
**When**: Results aggregated
**Then**:
- Return individual results for each item
- Calculate `passed_items`, `failed_items`, `flagged_items`
- Calculate `passed_rate` and `avg_processing_time`
- Single failure doesn't fail entire batch

**Aggregation**:
```python
summary = {
    "passed_rate": passed_items / total_items,
    "avg_processing_time": sum(times) / len(times)
}
```

---

### BR-BAT-003: Batch Item Isolation
**Given**: Batch with multiple items
**When**: One item fails validation
**Then**:
- Failed item recorded with error
- Other items continue processing
- Partial results returned
- No transaction rollback

---

### Report Generation Rules

### BR-RPT-001: Date Range Validation
**Given**: Report request with date range
**When**: Dates validated
**Then**:
- `end_date` must be after `start_date`
- Maximum range: 365 days
- Future dates → **ValidationError**
- Invalid range → **ValidationError**

---

### BR-RPT-002: Report Statistics Calculation
**Given**: Report request executes
**When**: Statistics generated
**Then**:
- Calculate total, passed, failed, flagged counts
- Group violations by type and category
- Identify high-risk incidents
- Count unique users

---

### BR-RPT-003: Top Violators Calculation
**Given**: Report includes violation analysis
**When**: Top violators calculated
**Then**:
- List users with most violations
- Maximum 10 users in list
- Include violation count and severity
- Anonymous IDs if privacy required

---

### Event Publishing Rules

### BR-EVT-001: Check Completed Event
**Given**: Compliance check completes
**When**: Result finalized
**Then**:
- Publish `compliance.check_completed` event
- Include check_id, status, risk_level
- Include user_id for routing
- Event failure doesn't block response

**Event Data**:
```json
{
    "event_type": "COMPLIANCE_CHECK_COMPLETED",
    "source": "compliance_service",
    "data": {
        "check_id": "chk_123",
        "user_id": "user_456",
        "status": "pass",
        "risk_level": "none"
    }
}
```

---

### BR-EVT-002: Violation Detected Event
**Given**: Compliance check finds violations
**When**: Violation(s) detected
**Then**:
- Publish `compliance.violation_detected` event
- Include violation details
- Risk level HIGH or CRITICAL triggers alert
- Used for real-time monitoring

---

### BR-EVT-003: Policy Applied Event
**Given**: Policy used for compliance check
**When**: Check completes with policy
**Then**:
- Publish `compliance.policy_applied` event
- Include policy_id and check_id
- Used for policy effectiveness tracking

---

### BR-EVT-004: Human Review Required Event
**Given**: Check flagged for human review
**When**: Review required
**Then**:
- Publish `compliance.review_required` event
- Include check_id and flagging reason
- Triggers notification workflow
- Used for review queue management

---

### BR-EVT-005: Event Failure Handling
**Given**: Event publishing fails
**When**: NATS unavailable or error
**Then**:
- Log error with full context
- Don't fail the main operation
- Return success to client
- Events are best-effort delivery

---

## State Machines

### Compliance Check Status State Machine

```
┌───────────┐
│  PENDING  │ Check initiated, processing started
└─────┬─────┘
      │
      ▼
┌───────────────────────────────────────────────────────┐
│                    PROCESSING                         │
│  Content analysis in progress                         │
└───────────────┬───────────────┬──────────────┬───────┘
                │               │              │
                ▼               ▼              ▼
         ┌──────────┐    ┌──────────┐   ┌──────────┐
         │   PASS   │    │ FLAGGED  │   │   FAIL   │
         │          │    │          │   │          │
         │ Content  │    │ Requires │   │ Content  │
         │ approved │    │  review  │   │ rejected │
         └──────────┘    └────┬─────┘   └────┬─────┘
                              │              │
                              ▼              │
                       ┌──────────┐          │
                       │ REVIEWED │          │
                       │          │          │
                       │  Human   │          │
                       │ decision │          │
                       └────┬─────┘          │
                            │                │
                ┌───────────┴───────────┐    │
                ▼                       ▼    ▼
         ┌──────────┐            ┌──────────────┐
         │   PASS   │            │   BLOCKED    │
         │          │            │              │
         │ Approved │            │ Content      │
         │ by human │            │ blocked +    │
         └──────────┘            │ action taken │
                                 └──────────────┘
```

**States**:
- **PENDING**: Check request received, queued for processing
- **PROCESSING**: Analysis algorithms running (internal state)
- **PASS**: Content passed all checks, no action required
- **FLAGGED**: Content requires human review
- **FAIL**: Content failed checks, policy violation
- **BLOCKED**: Content blocked, action taken (most severe)

**Valid Transitions**:
- `PENDING` → `PASS` (immediate approval)
- `PENDING` → `FLAGGED` (needs review)
- `PENDING` → `FAIL` (automatic rejection)
- `PENDING` → `BLOCKED` (auto-block enabled)
- `FLAGGED` → `PASS` (human approved)
- `FLAGGED` → `FAIL` (human rejected)
- `FLAGGED` → `BLOCKED` (human blocked + action)
- `FAIL` → `BLOCKED` (escalation)

**Invalid Transitions**:
- `PASS` → any (terminal state)
- `BLOCKED` → any (terminal state)
- Any → `PENDING` (no reprocessing)

---

### Risk Level Escalation State Machine

```
┌──────────┐
│   NONE   │ No issues detected
└────┬─────┘
     │ Issue detected
     ▼
┌──────────┐
│   LOW    │ Minor concerns
└────┬─────┘
     │ Multiple issues OR severity increase
     ▼
┌──────────┐
│  MEDIUM  │ Moderate concerns, review recommended
└────┬─────┘
     │ Serious issues OR sensitive category
     ▼
┌──────────┐
│   HIGH   │ Serious concerns, action required
└────┬─────┘
     │ Critical category OR multiple high-severity
     ▼
┌──────────┐
│ CRITICAL │ Maximum severity, immediate action
└──────────┘
```

**Escalation Triggers**:
- `NONE` → `LOW`: Any detection with confidence > 0.3
- `LOW` → `MEDIUM`: Multiple low detections OR confidence > 0.5
- `MEDIUM` → `HIGH`: Serious category flagged OR confidence > 0.7
- `HIGH` → `CRITICAL`: Child safety OR multiple high-severity

**De-escalation**: Not allowed - risk levels only escalate
- If later check passes, new record created
- Original risk level preserved for audit

---

### Policy Lifecycle State Machine

```
┌──────────┐
│  DRAFT   │ Policy being configured (optional)
└────┬─────┘
     │ Activation
     ▼
┌──────────┐
│  ACTIVE  │ Policy in effect, being applied
└────┬─────┘
     │
     ├────► SUSPENDED (temporarily disabled)
     │           │
     │           └────► ACTIVE (reactivated)
     │
     └────► ARCHIVED (permanently disabled)
```

**States**:
- **DRAFT**: Policy configuration in progress
- **ACTIVE**: Policy actively applied to checks
- **SUSPENDED**: Temporarily disabled, can reactivate
- **ARCHIVED**: Permanently disabled, for audit only

**Default State**: `ACTIVE` (policies active on creation)

---

### Human Review Workflow State Machine

```
┌─────────────┐
│  SUBMITTED  │ Content flagged for review
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   QUEUED    │ In review queue, awaiting assignment
└──────┬──────┘
       │ Reviewer claims
       ▼
┌─────────────┐
│ IN_PROGRESS │ Reviewer actively examining
└──────┬──────┘
       │
       ├────► APPROVED (content passes)
       │
       ├────► REJECTED (content fails)
       │
       ├────► ESCALATED (needs senior review)
       │           │
       │           └────► APPROVED/REJECTED
       │
       └────► TIMEOUT (auto-escalate after 24h)
                   │
                   └────► ESCALATED
```

**SLA Requirements**:
- Queue time: < 1 hour (p95)
- Review time: < 4 hours (p95)
- Total time: < 24 hours (hard limit)
- Timeout triggers escalation

---

## Edge Cases

### Content Processing Edge Cases

### EC-001: Empty Content String
**Scenario**: Check request with content=""
**Expected**:
- **ValidationError**: "Content cannot be empty or whitespace only"
- Check not created
- No events published

---

### EC-002: Very Large Content
**Scenario**: Content exceeds 100KB
**Expected**:
- Content truncated to 100KB for processing
- Warning included in result
- Full content hash computed before truncation
- Processing continues with truncated content

---

### EC-003: Binary Content in Text Field
**Scenario**: Binary data submitted as text content
**Expected**:
- Detected as non-text
- Return error: "Invalid content encoding"
- Suggest using content_id for binary

---

### EC-004: Unicode Edge Cases
**Scenario**: Content with RTL text, emoji, zero-width chars
**Expected**:
- Properly encoded as UTF-8
- Zero-width characters stripped before analysis
- Emoji analyzed as part of content
- RTL text normalized

---

### EC-005: Content with Only Whitespace
**Scenario**: Content contains only spaces, tabs, newlines
**Expected**:
- **ValidationError**: "Content cannot be empty or whitespace only"
- Same behavior as empty string

---

### PII Detection Edge Cases

### EC-006: False Positive Phone Numbers
**Scenario**: Text contains numbers that look like phones (ISBN, zip codes)
**Expected**:
- Context analysis reduces false positives
- Lower confidence for ambiguous matches
- ISBN: Not flagged as phone
- 10-digit number in sentence: May flag with lower confidence

---

### EC-007: Partial Credit Card Numbers
**Scenario**: Text contains partial card number (first 8 digits)
**Expected**:
- Not flagged as credit card (incomplete)
- Pattern requires 13-19 digit match
- Educational content discussing formats: Not flagged

---

### EC-008: Masked PII in Input
**Scenario**: Input already contains masked PII (e.g., "call ***-***-1234")
**Expected**:
- Recognize as already masked
- Lower risk level
- Note: "PII appears pre-masked"
- No double-masking in output

---

### Injection Detection Edge Cases

### EC-009: Code Block with Injection-like Content
**Scenario**: Legitimate code example showing injection patterns
**Expected**:
- Analyze context (code block markers)
- Lower confidence for educational content
- Flag but recommend: "review" not "block"
- Include explanation: "May be educational content"

---

### EC-010: Multilingual Injection Attempts
**Scenario**: Injection in non-English language
**Expected**:
- English patterns may not match
- Lower detection rate acknowledged
- Recommend human review for non-English prompts
- Log for pattern database improvement

---

### Batch Processing Edge Cases

### EC-011: Batch with Mix of Valid/Invalid Items
**Scenario**: 5 items, 2 have validation errors
**Expected**:
- Process 3 valid items
- Return errors for 2 invalid items
- `total_items=5`, `passed_items≤3`, errors included
- No partial transaction issues

---

### EC-012: Batch Timeout
**Scenario**: Batch processing exceeds 30 seconds
**Expected**:
- Return partial results
- Include timeout indicator
- Remaining items marked as "not_processed"
- Client can retry failed items

---

### Concurrent Operation Edge Cases

### EC-013: Simultaneous Checks for Same Content
**Scenario**: Same content submitted twice simultaneously
**Expected**:
- Both checks processed
- Content hash enables deduplication (optional)
- Both get unique check_ids
- Results may differ slightly (timing)

---

### EC-014: Policy Update During Check
**Scenario**: Policy updated while check in progress
**Expected**:
- Check uses policy snapshot from start
- New checks use updated policy
- No mid-check policy changes
- Audit log shows which policy version used

---

### EC-015: Review Update Race Condition
**Scenario**: Two reviewers update same flagged check
**Expected**:
- First update wins
- Second update fails: "Check already reviewed"
- Atomic status transition
- Audit trail shows both attempts

---

## Data Consistency Rules

### Timestamp Management

**Rule**: All timestamps in UTC with microsecond precision
- `checked_at`: Set when check completes
- `created_at`: Set at record creation
- `updated_at`: Updated on any modification
- `reviewed_at`: Set when human review completes

**Format**: ISO 8601 with timezone: `2025-10-22T10:00:00.123456Z`

---

### Check Record Immutability

**Rule**: Core check data is immutable after creation
- `check_id`: Never changes
- `user_id`: Never changes
- `content_hash`: Never changes
- `check_types`: Never changes
- `checked_at`: Never changes

**Mutable Fields**:
- `status`: Updated by review process
- `reviewed_by`: Set on review
- `review_notes`: Added on review
- `updated_at`: Always updated on change

---

### Status Transition Validation

**Rule**: Status transitions must follow state machine
- Invalid transitions rejected with error
- Each transition logged for audit
- No skipping intermediate states
- Terminal states cannot transition

**Implementation**:
```python
VALID_TRANSITIONS = {
    ComplianceStatus.PENDING: [PASS, FAIL, FLAGGED, BLOCKED],
    ComplianceStatus.FLAGGED: [PASS, FAIL, BLOCKED],
    ComplianceStatus.WARNING: [PASS, FAIL, FLAGGED],
}
```

---

### Content Hash Integrity

**Rule**: Content hash must match content
- SHA-256 algorithm
- Computed before any processing
- Stored with check record
- Enables duplicate detection and verification

---

## Integration Contracts

### PostgreSQL gRPC Service

**Expectations**:
- Service name: `postgres_grpc_service`
- Default host: `isa-postgres-grpc`
- Default port: `50061`
- Protocol: gRPC with AsyncPostgresClient
- Schema: `compliance`
- Tables: `compliance_checks`, `compliance_policies`, `user_consents`

**Query Format**:
- Parameterized queries with `$1`, `$2`, etc.
- JSONB support for violations, metadata fields
- Async context manager for connection pooling

---

### NATS Event Publishing

**Expectations**:
- Event bus provided via dependency injection
- Events published asynchronously
- Event failures logged but don't block operations
- Subject format: `compliance_service.{event_type}`

**Event Types**:
- `COMPLIANCE_CHECK_COMPLETED` → `compliance_service.check.completed`
- `COMPLIANCE_VIOLATION_DETECTED` → `compliance_service.violation.detected`
- `COMPLIANCE_REVIEW_REQUIRED` → `compliance_service.review.required`
- `COMPLIANCE_POLICY_APPLIED` → `compliance_service.policy.applied`

---

### Consul Service Discovery

**Expectations**:
- Service registered at startup
- Service name: `compliance_service`
- Health check endpoint: `/health`
- Discovers dependencies via Consul

---

### External Moderation APIs (Optional)

**OpenAI Moderation API**:
- Endpoint: `https://api.openai.com/v1/moderations`
- Used for enhanced content moderation
- Fallback to local patterns if unavailable
- Rate limited: 1000 req/min

**AWS Comprehend** (Optional):
- Used for advanced PII detection
- Language detection support
- Fallback to regex patterns if unavailable

---

## Error Handling Contracts

### ComplianceCheckError

**When Raised**:
- Content analysis fails
- External API errors
- Processing timeout

**HTTP Status**: 500 Internal Server Error

**Response**:
```json
{
    "detail": "Compliance check failed: {error_message}",
    "check_id": "chk_123",
    "error_code": "CHECK_FAILED"
}
```

---

### ValidationError

**When Raised**:
- Invalid request body
- Missing required fields
- Invalid enum values
- Content validation failure

**HTTP Status**: 422 Unprocessable Entity

**Response**:
```json
{
    "detail": [
        {"loc": ["body", "content"], "msg": "field required", "type": "value_error.missing"}
    ]
}
```

---

### NotFoundError

**When Raised**:
- Check ID not found
- Policy ID not found
- User data not found

**HTTP Status**: 404 Not Found

**Response**:
```json
{
    "detail": "Compliance check not found: chk_123"
}
```

---

### PolicyError

**When Raised**:
- Policy validation fails
- Policy not found
- Policy not active

**HTTP Status**: 400 Bad Request

**Response**:
```json
{
    "detail": "Policy validation failed: {reason}"
}
```

---

### HTTP Status Code Mappings

| Error Type | HTTP Status | Example Scenario |
|------------|-------------|------------------|
| ValidationError | 422 | Invalid content_type value |
| NotFoundError | 404 | Check ID not found |
| PolicyError | 400 | Invalid policy rules |
| ComplianceCheckError | 500 | Analysis engine failure |
| AuthenticationError | 401 | Missing API key |
| AuthorizationError | 403 | No permission for operation |

---

## Performance SLAs

### Response Time Targets (p95)

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| Single check (text) | < 200ms | < 1000ms |
| Single check (image) | < 500ms | < 2000ms |
| Batch check (10 items) | < 1000ms | < 3000ms |
| Get check by ID | < 50ms | < 200ms |
| Get user checks | < 100ms | < 500ms |
| Create policy | < 100ms | < 300ms |
| Generate report | < 500ms | < 2000ms |
| Data export | < 1000ms | < 5000ms |

### Throughput Targets

- Single checks: 500 req/s
- Batch checks: 100 req/s
- Query operations: 1000 req/s
- Report generation: 10 req/s

### Resource Limits

- Max content size: 100KB
- Max batch size: 100 items
- Max concurrent checks: 1000
- Max report date range: 365 days
- Review queue timeout: 24 hours

---

## Test Coverage Requirements

All tests MUST cover:

- ✅ Happy path (BR-XXX success scenarios)
- ✅ Content moderation categories (all 9)
- ✅ PII detection (all 11 types)
- ✅ Prompt injection patterns
- ✅ Risk level calculations
- ✅ Status transitions (all valid paths)
- ✅ Policy application logic
- ✅ Human review workflow
- ✅ GDPR operations (export, delete, consent)
- ✅ PCI-DSS card detection
- ✅ Batch processing
- ✅ Edge cases (EC-XXX scenarios)
- ✅ Event publishing verification
- ✅ Error handling (all error types)
- ✅ Performance within SLAs

---

**Version**: 1.0.0
**Last Updated**: 2025-12-22
**Owner**: Compliance Service Team
