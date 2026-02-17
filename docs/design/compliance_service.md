# Compliance Service - Design Document

## Design Overview

**Service Name**: compliance_service
**Port**: 8226
**Version**: 1.0.0
**Protocol**: HTTP REST API
**Last Updated**: 2025-12-22

### Design Principles
1. **Safety First**: Block harmful content before it reaches AI systems or storage
2. **Low Latency**: Real-time compliance decisions in <200ms for interactive applications
3. **Event-Driven Synchronization**: Loose coupling via NATS events
4. **Separation of Concerns**: Compliance checking only - no content storage or processing
5. **ACID Guarantees**: PostgreSQL transactions for data integrity
6. **Graceful Degradation**: Event failures and external API failures don't block operations
7. **Defense in Depth**: Multiple check types for comprehensive protection

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       External Clients                               │
│ (AI Gateway, Media Service, Chat Service, Document Service, Admin)   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTP REST API
                           │ (via API Gateway - JWT validation)
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  Compliance Service (Port 8226)                      │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │               FastAPI HTTP Layer (main.py)                     │ │
│  │  - Request validation (Pydantic models)                        │ │
│  │  - Response formatting                                         │ │
│  │  - Error handling & exception handlers                         │ │
│  │  - Health checks (/health, /status)                           │ │
│  │  - Lifecycle management (startup/shutdown)                     │ │
│  └────────────────────────────┬───────────────────────────────────┘ │
│                               │                                      │
│  ┌────────────────────────────▼───────────────────────────────────┐ │
│  │         Service Layer (compliance_service.py)                  │ │
│  │  - Content moderation (text, image, audio)                     │ │
│  │  - PII detection (email, phone, SSN, credit card)             │ │
│  │  - Prompt injection detection (patterns, tokens)               │ │
│  │  - Toxicity detection                                          │ │
│  │  - Risk level assessment                                       │ │
│  │  - Policy-based decision making                                │ │
│  │  - Event publishing orchestration                              │ │
│  │  - Statistics aggregation                                      │ │
│  └────────────────────────────┬───────────────────────────────────┘ │
│                               │                                      │
│  ┌────────────────────────────▼───────────────────────────────────┐ │
│  │        Repository Layer (compliance_repository.py)             │ │
│  │  - Compliance check CRUD operations                            │ │
│  │  - Policy management                                           │ │
│  │  - User data management (GDPR)                                 │ │
│  │  - Statistics queries                                          │ │
│  │  - PostgreSQL gRPC communication                               │ │
│  │  - Query construction (parameterized)                          │ │
│  └────────────────────────────┬───────────────────────────────────┘ │
│                               │                                      │
│  ┌────────────────────────────▼───────────────────────────────────┐ │
│  │         Event Publishing (events/publishers.py)                │ │
│  │  - NATS event bus integration                                  │ │
│  │  - Event model construction                                    │ │
│  │  - Async non-blocking publishing                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ↓                   ↓                   ↓
    ┌──────────────┐    ┌─────────────┐    ┌────────────┐
    │  PostgreSQL  │    │    NATS     │    │   Consul   │
    │   (gRPC)     │    │  (Events)   │    │ (Discovery)│
    │              │    │             │    │            │
    │  Schema:     │    │  Subjects:  │    │  Service:  │
    │  compliance  │    │  compliance.│    │  compliance│
    │  Tables:     │    │             │    │  _service  │
    │  - checks    │    │  Publishers:│    │            │
    │  - policies  │    │  - check    │    │  Health:   │
    │              │    │    performed│    │  /health   │
    │  Indexes:    │    │  - violation│    │            │
    │  - check_id  │    │    detected │    │            │
    │  - user_id   │    │  - warning  │    │            │
    │  - status    │    │    issued   │    │            │
    │  - risk_level│    │             │    │            │
    └──────────────┘    └─────────────┘    └────────────┘

Optional External:
┌──────────────────┐
│ OpenAI           │ ← Content moderation API (optional)
│ Moderation API   │
└──────────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Compliance Service                             │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐    │
│  │     Models      │─→│     Service     │─→│   Repository     │    │
│  │   (Pydantic)    │  │   (Business)    │  │     (Data)       │    │
│  │                 │  │                 │  │                  │    │
│  │ - ComplianceChk │  │ - Compliance    │  │ - Compliance     │    │
│  │ - CompliancePol │  │   Service       │  │   Repository     │    │
│  │ - ContentModRes │  │                 │  │                  │    │
│  │ - PIIDetectRes  │  │                 │  │                  │    │
│  │ - PromptInjRes  │  │                 │  │                  │    │
│  │ - CheckRequest  │  │                 │  │                  │    │
│  │ - CheckResponse │  │                 │  │                  │    │
│  │ - ReportRequest │  │                 │  │                  │    │
│  └─────────────────┘  └─────────────────┘  └──────────────────┘    │
│          ↑                    ↑                      ↑              │
│          │                    │                      │              │
│  ┌───────┴────────────────────┴──────────────────────┴───────────┐  │
│  │                  FastAPI Main (main.py)                       │  │
│  │  - Dependency Injection (get_compliance_service)              │  │
│  │  - Route Handlers (18 endpoints)                              │  │
│  │  - Exception Handlers (custom errors)                         │  │
│  │  - GDPR/PCI-DSS endpoints                                     │  │
│  └───────────────────────────┬───────────────────────────────────┘  │
│                              │                                      │
│  ┌───────────────────────────▼───────────────────────────────────┐  │
│  │                 Event Publishers                              │  │
│  │           (events/publishers.py, events/models.py)            │  │
│  │  - publish_compliance_check_performed                         │  │
│  │  - publish_compliance_violation_detected                      │  │
│  │  - publish_compliance_warning_issued                          │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Factory Pattern                            │  │
│  │               (factory.py, protocols.py)                      │  │
│  │  - create_compliance_service (production)                     │  │
│  │  - ComplianceRepositoryProtocol (interface)                   │  │
│  │  - Enables dependency injection for tests                     │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Responsibilities**:
- HTTP request/response handling
- Request validation via Pydantic models
- Route definitions (18 endpoints)
- Health checks
- Service initialization (lifespan management)
- Consul registration
- NATS event bus setup
- Exception handling
- GDPR/PCI-DSS endpoint handling

**Key Endpoints**:
```python
# Health Checks
GET /health                                      # Basic health check
GET /status                                      # Detailed service status

# Core Compliance Checking
POST /api/v1/compliance/check                    # Perform compliance check
POST /api/v1/compliance/check/batch              # Batch compliance check

# Check History
GET  /api/v1/compliance/checks/{check_id}        # Get check by ID
GET  /api/v1/compliance/checks/user/{user_id}    # Get user's check history

# Human Review
GET  /api/v1/compliance/reviews/pending          # Get pending reviews
PUT  /api/v1/compliance/reviews/{check_id}       # Update review decision

# Policy Management
POST /api/v1/compliance/policies                 # Create policy
GET  /api/v1/compliance/policies/{policy_id}     # Get policy by ID
GET  /api/v1/compliance/policies                 # List active policies

# Reporting
POST /api/v1/compliance/reports                  # Generate report
GET  /api/v1/compliance/stats                    # Get statistics

# GDPR Endpoints
GET  /api/v1/compliance/user/{user_id}/data-export    # Data export
DELETE /api/v1/compliance/user/{user_id}/data         # Data deletion
GET  /api/v1/compliance/user/{user_id}/data-summary   # Data summary
POST /api/v1/compliance/user/{user_id}/consent        # Consent management
GET  /api/v1/compliance/user/{user_id}/audit-log      # Audit log

# PCI-DSS
POST /api/v1/compliance/pci/card-data-check      # Card data detection
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global compliance_service, compliance_repository, event_bus

    # Startup
    # 1. Initialize NATS event bus
    event_bus = await get_event_bus("compliance_service")

    # 2. Initialize compliance service
    compliance_service = ComplianceService(event_bus=event_bus, config=config_manager)
    compliance_repository = compliance_service.repository
    await compliance_repository.initialize()

    # 3. Register event handlers
    if event_bus:
        handler_map = get_event_handlers(compliance_service, event_bus)
        for event_pattern, handler_func in handler_map.items():
            await event_bus.subscribe_to_events(pattern=event_pattern, handler=handler_func)

    # 4. Consul registration
    if config.consul_enabled:
        route_meta = get_routes_for_consul()
        consul_registry = ConsulRegistry(
            service_name=SERVICE_METADATA['service_name'],
            service_port=SERVICE_PORT,
            tags=SERVICE_METADATA['tags'],
            meta=consul_meta,
            health_check_type='http'
        )
        consul_registry.register()

    yield  # Service runs

    # Shutdown
    if consul_registry:
        consul_registry.deregister()
    if event_bus:
        await event_bus.close()
```

### 2. Service Layer (compliance_service.py)

**Class**: `ComplianceService`

**Responsibilities**:
- Content moderation (text, image, audio)
- PII detection using regex patterns
- Prompt injection detection using pattern matching
- Toxicity detection (placeholder for Perspective API)
- Risk level calculation and assessment
- Policy retrieval and application
- Action determination (allow, block, review)
- Event publishing coordination
- Statistics caching

**Key Methods**:
```python
class ComplianceService:
    def __init__(self, event_bus=None, config=None):
        self.repository = ComplianceRepository(config=config)
        self.event_bus = event_bus

        # Configuration
        self.enable_openai_moderation = True
        self.enable_local_checks = True

        # Cache
        self._policy_cache: Dict[str, CompliancePolicy] = {}

        # Statistics
        self._stats = {
            "total_checks": 0,
            "blocked_content": 0,
            "flagged_content": 0
        }

    async def perform_compliance_check(
        self,
        request: ComplianceCheckRequest
    ) -> ComplianceCheckResponse:
        """
        Main entry point for compliance checking.

        1. Generate unique check_id
        2. Get applicable policy
        3. Run checks concurrently (moderation, PII, injection, toxicity)
        4. Evaluate results against policy
        5. Determine action (allow, block, review)
        6. Record check in database
        7. Publish events
        8. Return response
        """
        start_time = time.time()
        check_id = str(uuid.uuid4())

        # Get policy
        policy = await self._get_applicable_policy(request)

        # Run checks concurrently
        check_results = await self._run_checks(request, check_id)

        # Evaluate overall status
        overall_status, risk_level, violations, warnings = \
            self._evaluate_results(check_results, policy)

        # Determine action
        action_required, action_taken = \
            await self._determine_action(overall_status, risk_level, policy)

        # Create and save check record
        compliance_check = ComplianceCheck(
            check_id=check_id,
            check_type=request.check_types[0],
            content_type=request.content_type,
            status=overall_status,
            risk_level=risk_level,
            user_id=request.user_id,
            organization_id=request.organization_id,
            violations=violations,
            warnings=warnings,
            action_taken=action_taken,
            metadata=request.metadata,
            checked_at=datetime.utcnow()
        )
        await self.repository.create_check(compliance_check)

        # Publish events
        await publish_compliance_check_performed(...)
        if violations:
            await publish_compliance_violation_detected(...)
        if warnings:
            await publish_compliance_warning_issued(...)

        return ComplianceCheckResponse(...)

    async def _run_checks(
        self,
        request: ComplianceCheckRequest,
        check_id: str
    ) -> Dict[str, Any]:
        """Run all required checks concurrently"""
        tasks = []

        if ComplianceCheckType.CONTENT_MODERATION in request.check_types:
            tasks.append(self._check_content_moderation(request, check_id))

        if ComplianceCheckType.PII_DETECTION in request.check_types:
            tasks.append(self._check_pii_detection(request, check_id))

        if ComplianceCheckType.PROMPT_INJECTION in request.check_types:
            tasks.append(self._check_prompt_injection(request, check_id))

        if ComplianceCheckType.TOXICITY in request.check_types:
            tasks.append(self._check_toxicity(request, check_id))

        # Execute concurrently
        if tasks:
            check_results = await asyncio.gather(*tasks, return_exceptions=True)
            # Process results...

        return results

    async def _check_content_moderation(
        self,
        request: ComplianceCheckRequest,
        check_id: str
    ) -> ContentModerationResult:
        """Text/image/audio content moderation"""
        if request.content_type in [ContentType.TEXT, ContentType.PROMPT]:
            return await self._moderate_text(request.content, check_id)
        elif request.content_type == ContentType.IMAGE:
            return await self._moderate_image(request.content_id, check_id)
        elif request.content_type == ContentType.AUDIO:
            return await self._moderate_audio(request.content_id, check_id)
        return ContentModerationResult(status=ComplianceStatus.PASS, ...)

    async def _check_pii_detection(
        self,
        request: ComplianceCheckRequest,
        check_id: str
    ) -> PIIDetectionResult:
        """
        Detect PII using regex patterns:
        - Email: [A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}
        - Phone: \d{3}[-.]?\d{3}[-.]?\d{4}
        - SSN: \d{3}-\d{2}-\d{4}
        - Credit Card: \d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}
        - IP Address: (?:\d{1,3}\.){3}\d{1,3}
        """
        detected_pii = []
        pii_patterns = {
            PIIType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            PIIType.PHONE: r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            PIIType.SSN: r'\b\d{3}-\d{2}-\d{4}\b',
            PIIType.CREDIT_CARD: r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            PIIType.IP_ADDRESS: r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        }

        for pii_type, pattern in pii_patterns.items():
            matches = re.finditer(pattern, request.content)
            for match in matches:
                detected_pii.append({
                    "type": pii_type.value,
                    "value": self._mask_pii(match.group()),
                    "location": match.span(),
                    "confidence": 0.95
                })

        # Assess risk level based on PII count
        pii_count = len(detected_pii)
        if pii_count >= 5:
            risk_level = RiskLevel.CRITICAL
            status = ComplianceStatus.FAIL
        elif pii_count >= 3:
            risk_level = RiskLevel.HIGH
            status = ComplianceStatus.FLAGGED
        elif pii_count >= 1:
            risk_level = RiskLevel.MEDIUM
            status = ComplianceStatus.WARNING
        else:
            risk_level = RiskLevel.NONE
            status = ComplianceStatus.PASS

        return PIIDetectionResult(...)

    async def _check_prompt_injection(
        self,
        request: ComplianceCheckRequest,
        check_id: str
    ) -> PromptInjectionResult:
        """
        Detect prompt injection patterns:
        - ignore\s+(previous|above|prior)\s+(instructions|prompts?|commands?)
        - forget\s+(everything|all|previous)
        - you\s+are\s+now
        - system\s*:\s*
        - </?\s*system\s*>
        - jailbreak
        - developer\s+mode
        - override\s+(safety|rules|restrictions)
        """
        text = request.content.lower()
        injection_patterns = [
            r'ignore\s+(previous|above|prior)\s+(instructions|prompts?|commands?)',
            r'forget\s+(everything|all|previous)',
            r'you\s+are\s+now',
            r'system\s*:\s*',
            r'</?\s*system\s*>',
            r'jailbreak',
            r'developer\s+mode',
            r'override\s+(safety|rules|restrictions)',
        ]

        detected_patterns = []
        max_confidence = 0.0

        for pattern in injection_patterns:
            if re.search(pattern, text):
                detected_patterns.append(pattern)
                max_confidence = max(max_confidence, 0.8)

        # Check suspicious tokens
        suspicious_tokens = []
        if '<|' in text or '|>' in text:
            suspicious_tokens.append('special_tokens')
            max_confidence = max(max_confidence, 0.6)

        if '###' in text or '```' in text:
            suspicious_tokens.append('code_blocks')
            max_confidence = max(max_confidence, 0.4)

        # Determine result
        if max_confidence >= 0.8:
            status = ComplianceStatus.FAIL
            risk_level = RiskLevel.HIGH
            injection_type = "direct"
            recommendation = "block"
        elif max_confidence >= 0.5:
            status = ComplianceStatus.FLAGGED
            risk_level = RiskLevel.MEDIUM
            injection_type = "suspicious"
            recommendation = "review"
        else:
            status = ComplianceStatus.PASS
            risk_level = RiskLevel.NONE
            injection_type = None
            recommendation = "allow"

        return PromptInjectionResult(...)

    def _evaluate_results(
        self,
        check_results: Dict[str, Any],
        policy: Optional[CompliancePolicy]
    ) -> Tuple[ComplianceStatus, RiskLevel, List[Dict], List[Dict]]:
        """
        Evaluate all check results to determine overall status.

        Status priority: BLOCKED > FAIL > FLAGGED > WARNING > PASS
        Risk priority: CRITICAL > HIGH > MEDIUM > LOW > NONE
        """
        violations = []
        warnings = []
        max_risk = RiskLevel.NONE
        worst_status = ComplianceStatus.PASS

        status_priority = {
            ComplianceStatus.PASS: 0,
            ComplianceStatus.WARNING: 1,
            ComplianceStatus.FLAGGED: 2,
            ComplianceStatus.FAIL: 3,
            ComplianceStatus.BLOCKED: 4
        }

        for check_type, result in check_results.items():
            if hasattr(result, 'status'):
                if status_priority[result.status] > status_priority[worst_status]:
                    worst_status = result.status

                if result.risk_level > max_risk:
                    max_risk = result.risk_level

                # Collect violations and warnings
                if result.status in [ComplianceStatus.FAIL, ComplianceStatus.BLOCKED]:
                    violations.append({...})
                elif result.status in [ComplianceStatus.WARNING, ComplianceStatus.FLAGGED]:
                    warnings.append({...})

        return worst_status, max_risk, violations, warnings

    async def _determine_action(
        self,
        status: ComplianceStatus,
        risk_level: RiskLevel,
        policy: Optional[CompliancePolicy]
    ) -> Tuple[str, Optional[str]]:
        """Determine what action to take based on status and risk"""
        if status == ComplianceStatus.BLOCKED or risk_level == RiskLevel.CRITICAL:
            return "block", "blocked"
        elif status == ComplianceStatus.FAIL or risk_level == RiskLevel.HIGH:
            return "block", "blocked"
        elif status == ComplianceStatus.FLAGGED or risk_level == RiskLevel.MEDIUM:
            return "review", "flagged_for_review"
        elif status == ComplianceStatus.WARNING:
            return "allow", "allowed_with_warning"
        else:
            return "none", "allowed"
```

**Custom Exceptions**:
```python
class ComplianceServiceError(Exception):
    """Base exception for compliance service"""
    pass

class ComplianceCheckNotFoundError(ComplianceServiceError):
    """Check not found"""
    pass

class PolicyNotFoundError(ComplianceServiceError):
    """Policy not found"""
    pass

class ValidationError(ComplianceServiceError):
    """Validation error"""
    pass
```

### 3. Repository Layer (compliance_repository.py)

**Class**: `ComplianceRepository`

**Responsibilities**:
- PostgreSQL CRUD operations for compliance checks
- Policy management (create, get, list)
- User data operations (GDPR support)
- Statistics and reporting queries
- gRPC communication with postgres_grpc_service
- Query construction (parameterized)
- Result parsing

**Key Methods**:
```python
class ComplianceRepository:
    def __init__(self, config: Optional[ConfigManager] = None):
        # Discover PostgreSQL gRPC service
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061
        )
        self.db = AsyncPostgresClient(host=host, port=port, user_id="compliance_service")
        self.schema = "compliance"
        self.checks_table = "compliance_checks"
        self.policies_table = "compliance_policies"

    async def create_check(self, check: ComplianceCheck) -> Optional[ComplianceCheck]:
        """Create compliance check record"""
        query = f'''
            INSERT INTO {self.schema}.{self.checks_table} (
                check_id, check_type, content_type, status, risk_level,
                user_id, organization_id, session_id, request_id, content_id,
                content_hash, content_size, confidence_score,
                violations, warnings, detected_issues, moderation_categories,
                detected_pii, action_taken, blocked_reason, human_review_required,
                reviewed_by, review_notes, metadata, provider,
                checked_at, reviewed_at, created_at, updated_at
            ) VALUES ($1, $2, $3, ... $29)
            RETURNING *
        '''
        # Execute and return result
        ...

    async def get_check_by_id(self, check_id: str) -> Optional[ComplianceCheck]:
        """Get check by ID"""
        query = f'''
            SELECT * FROM {self.schema}.{self.checks_table}
            WHERE check_id = $1
        '''
        ...

    async def get_checks_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        status: Optional[ComplianceStatus] = None,
        risk_level: Optional[RiskLevel] = None
    ) -> List[ComplianceCheck]:
        """Get user's compliance check history"""
        # Build dynamic query with filters
        ...

    async def get_pending_reviews(self, limit: int = 50) -> List[ComplianceCheck]:
        """Get checks awaiting human review"""
        query = f'''
            SELECT * FROM {self.schema}.{self.checks_table}
            WHERE human_review_required = TRUE
              AND status = 'pending'
              AND reviewed_by IS NULL
            ORDER BY checked_at ASC
            LIMIT $1
        '''
        ...

    async def update_review_status(
        self,
        check_id: str,
        reviewed_by: str,
        status: ComplianceStatus,
        review_notes: Optional[str] = None
    ) -> bool:
        """Update human review decision"""
        query = f'''
            UPDATE {self.schema}.{self.checks_table}
            SET status = $1, reviewed_by = $2, reviewed_at = $3,
                review_notes = $4, updated_at = $5
            WHERE check_id = $6
        '''
        ...

    async def get_statistics(
        self,
        organization_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get aggregate statistics"""
        query = f'''
            SELECT
                COUNT(*) as total_checks,
                COUNT(CASE WHEN status = 'pass' THEN 1 END) as passed_checks,
                COUNT(CASE WHEN status = 'fail' THEN 1 END) as failed_checks,
                COUNT(CASE WHEN status = 'flagged' THEN 1 END) as flagged_checks
            FROM {self.schema}.{self.checks_table}
            WHERE ...
        '''
        ...

    # Policy Methods
    async def create_policy(self, policy: CompliancePolicy) -> Optional[CompliancePolicy]:
        """Create compliance policy"""
        ...

    async def get_policy_by_id(self, policy_id: str) -> Optional[CompliancePolicy]:
        """Get policy by ID"""
        ...

    async def get_active_policies(self, organization_id: str) -> List[CompliancePolicy]:
        """Get active policies for organization"""
        ...

    # GDPR Methods
    async def delete_user_data(self, user_id: str) -> int:
        """Delete all user data (GDPR Article 17)"""
        query = f'''
            DELETE FROM {self.schema}.{self.checks_table}
            WHERE user_id = $1
        '''
        ...

    async def update_user_consent(
        self,
        user_id: str,
        consent_type: str,
        granted: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Update user consent (GDPR Article 7)"""
        ...
```

---

## Database Schema Design

### PostgreSQL Schema: `compliance`

#### Table: compliance.compliance_checks

```sql
-- Create compliance schema
CREATE SCHEMA IF NOT EXISTS compliance;

-- Create compliance checks table
CREATE TABLE IF NOT EXISTS compliance.compliance_checks (
    -- Primary Key
    id SERIAL,
    check_id VARCHAR(255) PRIMARY KEY,

    -- Check Type and Content
    check_type VARCHAR(50) NOT NULL,        -- content_moderation, pii_detection, prompt_injection, etc.
    content_type VARCHAR(50) NOT NULL,       -- text, image, audio, video, prompt, response

    -- Status and Risk
    status VARCHAR(50) NOT NULL,             -- pass, fail, warning, pending, flagged, blocked
    risk_level VARCHAR(50) DEFAULT 'none',   -- none, low, medium, high, critical

    -- User Context
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    session_id VARCHAR(255),
    request_id VARCHAR(255),

    -- Content Reference
    content_id VARCHAR(255),                 -- Reference to file/message
    content_hash VARCHAR(64),                -- SHA-256 hash for deduplication
    content_size INTEGER,

    -- Check Results
    confidence_score FLOAT DEFAULT 0.0,
    violations JSONB DEFAULT '[]'::jsonb,
    warnings JSONB DEFAULT '[]'::jsonb,
    detected_issues JSONB DEFAULT '{}'::jsonb,
    moderation_categories JSONB DEFAULT '[]'::jsonb,
    detected_pii JSONB DEFAULT '[]'::jsonb,

    -- Actions
    action_taken VARCHAR(100),               -- allowed, blocked, flagged_for_review
    blocked_reason TEXT,

    -- Human Review
    human_review_required BOOLEAN DEFAULT FALSE,
    reviewed_by VARCHAR(255),
    review_notes TEXT,
    reviewed_at TIMESTAMPTZ,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    provider VARCHAR(100),                   -- openai, aws, local

    -- Timestamps
    checked_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for compliance_checks
CREATE INDEX IF NOT EXISTS idx_checks_check_id ON compliance.compliance_checks(check_id);
CREATE INDEX IF NOT EXISTS idx_checks_user_id ON compliance.compliance_checks(user_id);
CREATE INDEX IF NOT EXISTS idx_checks_organization_id ON compliance.compliance_checks(organization_id);
CREATE INDEX IF NOT EXISTS idx_checks_status ON compliance.compliance_checks(status);
CREATE INDEX IF NOT EXISTS idx_checks_risk_level ON compliance.compliance_checks(risk_level);
CREATE INDEX IF NOT EXISTS idx_checks_check_type ON compliance.compliance_checks(check_type);
CREATE INDEX IF NOT EXISTS idx_checks_checked_at ON compliance.compliance_checks(checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_checks_human_review ON compliance.compliance_checks(human_review_required)
    WHERE human_review_required = TRUE;
CREATE INDEX IF NOT EXISTS idx_checks_violations ON compliance.compliance_checks USING GIN(violations);

-- Comments
COMMENT ON TABLE compliance.compliance_checks IS 'Compliance check records for content moderation, PII detection, prompt injection, etc.';
COMMENT ON COLUMN compliance.compliance_checks.check_id IS 'Unique identifier for the compliance check (UUID)';
COMMENT ON COLUMN compliance.compliance_checks.check_type IS 'Type of check: content_moderation, pii_detection, prompt_injection, toxicity';
COMMENT ON COLUMN compliance.compliance_checks.status IS 'Check result: pass, fail, warning, pending, flagged, blocked';
COMMENT ON COLUMN compliance.compliance_checks.risk_level IS 'Risk assessment: none, low, medium, high, critical';
COMMENT ON COLUMN compliance.compliance_checks.violations IS 'JSONB array of detected violations';
COMMENT ON COLUMN compliance.compliance_checks.detected_pii IS 'JSONB array of detected PII (masked values)';
```

#### Table: compliance.compliance_policies

```sql
-- Create compliance policies table
CREATE TABLE IF NOT EXISTS compliance.compliance_policies (
    -- Primary Key
    id SERIAL,
    policy_id VARCHAR(255) PRIMARY KEY,

    -- Policy Identity
    policy_name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Scope
    organization_id VARCHAR(255),            -- NULL for global policies

    -- Configuration
    enabled BOOLEAN DEFAULT TRUE,
    check_types TEXT[],                      -- Array of check types to enable
    content_types TEXT[],                    -- Array of content types this applies to
    rules JSONB NOT NULL,                    -- Policy rules configuration
    thresholds JSONB DEFAULT '{}'::jsonb,    -- Score thresholds per category

    -- Behavior
    auto_block BOOLEAN DEFAULT TRUE,
    require_review BOOLEAN DEFAULT FALSE,
    notify_admin BOOLEAN DEFAULT TRUE,

    -- Metadata
    priority INTEGER DEFAULT 100,
    created_by VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for policies
CREATE INDEX IF NOT EXISTS idx_policies_policy_id ON compliance.compliance_policies(policy_id);
CREATE INDEX IF NOT EXISTS idx_policies_organization_id ON compliance.compliance_policies(organization_id);
CREATE INDEX IF NOT EXISTS idx_policies_enabled ON compliance.compliance_policies(enabled)
    WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_policies_priority ON compliance.compliance_policies(priority DESC);

-- Comments
COMMENT ON TABLE compliance.compliance_policies IS 'Configurable compliance policies per organization';
COMMENT ON COLUMN compliance.compliance_policies.policy_id IS 'Unique policy identifier (UUID)';
COMMENT ON COLUMN compliance.compliance_policies.rules IS 'JSONB policy rules configuration';
COMMENT ON COLUMN compliance.compliance_policies.thresholds IS 'JSONB score thresholds (e.g., {"hate_speech": 0.3, "violence": 0.5})';
```

#### Table: compliance.user_consents (Future)

```sql
-- Create user consents table (for GDPR Article 7)
CREATE TABLE IF NOT EXISTS compliance.user_consents (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    consent_type VARCHAR(100) NOT NULL,      -- data_processing, marketing, analytics, ai_training
    granted BOOLEAN NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, consent_type)
);

CREATE INDEX IF NOT EXISTS idx_consents_user_id ON compliance.user_consents(user_id);
CREATE INDEX IF NOT EXISTS idx_consents_type ON compliance.user_consents(consent_type);
```

### Index Strategy

1. **Primary Key** (`check_id`, `policy_id`): Clustered index for fast lookups
2. **User ID Index** (`idx_checks_user_id`): B-tree for user history queries
3. **Organization ID Index** (`idx_checks_organization_id`): B-tree for org reports
4. **Status Index** (`idx_checks_status`): Filter by check status
5. **Risk Level Index** (`idx_checks_risk_level`): Filter high-risk items
6. **Timestamp Index** (`idx_checks_checked_at`): Time-range queries, sorted DESC
7. **Human Review Partial Index** (`idx_checks_human_review`): Only pending reviews
8. **Violations GIN Index** (`idx_checks_violations`): JSONB queries

### JSONB Query Examples

```sql
-- Find checks with specific violation type
SELECT * FROM compliance.compliance_checks
WHERE violations @> '[{"check_type": "content_moderation"}]';

-- Find checks with hate_speech violations
SELECT * FROM compliance.compliance_checks
WHERE violations @> '[{"category": "hate_speech"}]';

-- Find all high-risk PII detections
SELECT * FROM compliance.compliance_checks
WHERE risk_level = 'high'
  AND detected_pii != '[]'::jsonb;

-- Get checks with specific threshold exceeded
SELECT * FROM compliance.compliance_checks
WHERE (violations->0->>'confidence')::float > 0.8;
```

---

## Event-Driven Architecture

### Event Publishing (events/publishers.py)

**NATS Subjects**:
```
compliance.check.performed        # Compliance check completed
compliance.violation.detected     # Violation detected (FAIL/BLOCKED)
compliance.warning.issued         # Warning issued (content allowed with concerns)
```

### Event Models (events/models.py)

```python
class ComplianceEventType(str, Enum):
    """Events published by compliance_service"""
    CHECK_PERFORMED = "compliance.check.performed"
    VIOLATION_DETECTED = "compliance.violation.detected"
    WARNING_ISSUED = "compliance.warning.issued"

class ComplianceCheckPerformedEvent(BaseModel):
    """Event: compliance.check.performed"""
    check_id: str
    user_id: str
    organization_id: Optional[str]
    check_type: str              # content_moderation, pii_detection, etc.
    content_type: str            # text, image, prompt, etc.
    status: str                  # pass, fail, warning, flagged, blocked
    risk_level: str              # none, low, medium, high, critical
    violations_count: int
    warnings_count: int
    action_taken: Optional[str]  # allowed, blocked, flagged_for_review
    processing_time_ms: Optional[float]
    timestamp: str               # ISO 8601
    metadata: Optional[Dict[str, Any]]

class ComplianceViolationDetectedEvent(BaseModel):
    """Event: compliance.violation.detected"""
    check_id: str
    user_id: str
    organization_id: Optional[str]
    violations: List[Dict[str, Any]]  # Violation details
    risk_level: str
    action_taken: Optional[str]
    requires_review: bool
    blocked_content: bool
    timestamp: str
    metadata: Optional[Dict[str, Any]]

class ComplianceWarningIssuedEvent(BaseModel):
    """Event: compliance.warning.issued"""
    check_id: str
    user_id: str
    organization_id: Optional[str]
    warnings: List[Dict[str, Any]]   # Warning details
    warning_types: List[str]
    risk_level: str
    allowed_with_warning: bool
    timestamp: str
    metadata: Optional[Dict[str, Any]]
```

### Subscribed Events (events/handlers.py)

```python
class ComplianceSubscribedEventType(str, Enum):
    """Events that compliance_service subscribes to"""
    USER_CREATED = "user.created"       # Initialize user compliance tracking
    ORDER_COMPLETED = "order.completed" # PCI-DSS validation
```

### Event Flow Diagram

```
┌─────────────┐
│   Client    │ (AI Gateway, Media Service)
└──────┬──────┘
       │ POST /api/v1/compliance/check
       ↓
┌───────────────────────────────┐
│     Compliance Service        │
│                               │
│  1. Generate check_id         │
│  2. Get policy                │
│  3. Run checks (concurrent)   │
│     - Content moderation      │
│     - PII detection           │
│     - Prompt injection        │
│  4. Evaluate results          │
│  5. Determine action          │
│  6. Save to PostgreSQL ───────┼──→ compliance.compliance_checks
│  7. Publish events            │
└───────────────────────────────┘
       │
       │ Events based on result:
       ↓
┌─────────────────────────┐
│       NATS Bus          │
│                         │
│ If any check completes: │
│ → compliance.check.     │
│   performed             │
│                         │
│ If violations found:    │
│ → compliance.violation. │
│   detected              │
│                         │
│ If warnings issued:     │
│ → compliance.warning.   │
│   issued                │
└────────────┬────────────┘
             │
             ├──→ Audit Service (log all checks)
             ├──→ Analytics Service (track metrics)
             ├──→ Notification Service (alert on violations)
             └──→ Account Service (flag repeat violators)
```

---

## Data Flow Diagrams

### 1. Real-Time Compliance Check Flow

```
AI Gateway calls POST /api/v1/compliance/check
    │
    ↓
┌────────────────────────────────────────────────────────────────────┐
│  ComplianceService.perform_compliance_check                        │
│                                                                    │
│  Step 1: Generate check_id                                         │
│    check_id = uuid4()                                              │
│                                                                    │
│  Step 2: Get applicable policy                                     │
│    _get_applicable_policy(request) ────────────────────────────────┼──→ PostgreSQL
│                                     ←──────────────────────────────┤    compliance.policies
│    Result: CompliancePolicy | None                                 │
│                                                                    │
│  Step 3: Run checks concurrently                                   │
│    asyncio.gather(                                                 │
│      _check_content_moderation()  ─────→ Local rules + OpenAI      │
│      _check_pii_detection()       ─────→ Regex patterns            │
│      _check_prompt_injection()    ─────→ Pattern matching          │
│    )                                                               │
│    Result: Dict[check_type, result]                                │
│                                                                    │
│  Step 4: Evaluate results                                          │
│    _evaluate_results(check_results, policy)                        │
│    Result: (status, risk_level, violations, warnings)              │
│                                                                    │
│  Step 5: Determine action                                          │
│    _determine_action(status, risk_level, policy)                   │
│    Result: (action_required, action_taken)                         │
│                                                                    │
│  Step 6: Save check record                                         │
│    repository.create_check(compliance_check) ──────────────────────┼──→ PostgreSQL
│                                              ←─────────────────────┤    compliance.checks
│    Success                                                         │
│                                                                    │
│  Step 7: Publish events                                            │
│    publish_compliance_check_performed() ───────────────────────────┼──→ NATS
│    if violations: publish_violation_detected() ────────────────────┼──→ NATS
│    if warnings: publish_warning_issued() ──────────────────────────┼──→ NATS
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
    │
    │ Return ComplianceCheckResponse (< 200ms)
    ↓
AI Gateway receives decision
    │
    │ If passed → Send to AI model
    │ If blocked → Return error to user
    │ If flagged → Queue for review
    ↓
┌────────────────────────────────────────────────────────────────────┐
│                      Event Subscribers                             │
│  - Audit Service: Log check for compliance reporting               │
│  - Analytics: Track violation patterns                             │
│  - Notification: Alert moderators on high-risk content             │
│  - Account: Flag users with repeated violations                    │
└────────────────────────────────────────────────────────────────────┘
```

### 2. PII Detection Flow

```
Content with potential PII: "Contact john@email.com at 555-123-4567"
    │
    ↓
┌────────────────────────────────────────────────────────────────────┐
│  ComplianceService._check_pii_detection                            │
│                                                                    │
│  Step 1: Initialize patterns                                       │
│    pii_patterns = {                                                │
│      EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'│
│      PHONE: r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'                      │
│      SSN: r'\b\d{3}-\d{2}-\d{4}\b'                                │
│      CREDIT_CARD: r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'  │
│      IP_ADDRESS: r'\b(?:\d{1,3}\.){3}\d{1,3}\b'                   │
│    }                                                               │
│                                                                    │
│  Step 2: Scan content                                              │
│    for pii_type, pattern in pii_patterns.items():                 │
│      matches = re.finditer(pattern, content)                       │
│      for match in matches:                                         │
│        detected_pii.append({                                       │
│          "type": pii_type.value,                                   │
│          "value": mask_pii(match.group()),  # "jo***om"           │
│          "location": match.span(),                                 │
│          "confidence": 0.95                                        │
│        })                                                          │
│                                                                    │
│  Step 3: Calculate risk level                                      │
│    pii_count = 2  # email + phone                                  │
│    risk_level = MEDIUM  # 1-2 PII instances                        │
│    status = WARNING                                                │
│    needs_redaction = True                                          │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
    │
    ↓
Return PIIDetectionResult:
{
  "check_id": "chk_abc123",
  "status": "warning",
  "detected_pii": [
    {"type": "email", "value": "jo***om", "location": [8, 22], "confidence": 0.95},
    {"type": "phone", "value": "55***67", "location": [26, 38], "confidence": 0.95}
  ],
  "pii_count": 2,
  "pii_types": ["email", "phone"],
  "risk_level": "medium",
  "needs_redaction": true
}
```

### 3. Human Review Workflow

```
Moderator requests pending reviews
    │
    ↓
GET /api/v1/compliance/reviews/pending?limit=50
    │
    ↓
┌────────────────────────────────────────────────────────────────────┐
│  repository.get_pending_reviews()                                  │
│                                                                    │
│  Query: SELECT * FROM compliance.compliance_checks                 │
│         WHERE human_review_required = TRUE                         │
│           AND status = 'pending'                                   │
│           AND reviewed_by IS NULL                                  │
│         ORDER BY risk_level DESC, checked_at ASC                   │
│         LIMIT 50                                                   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
    │
    │ Return pending_reviews list
    ↓
Moderator reviews content and submits decision
    │
    ↓
PUT /api/v1/compliance/reviews/{check_id}
{
  "reviewed_by": "moderator_123",
  "status": "pass",
  "review_notes": "False positive - content is safe"
}
    │
    ↓
┌────────────────────────────────────────────────────────────────────┐
│  repository.update_review_status()                                 │
│                                                                    │
│  UPDATE compliance.compliance_checks                               │
│  SET status = 'pass',                                              │
│      reviewed_by = 'moderator_123',                                │
│      reviewed_at = NOW(),                                          │
│      review_notes = 'False positive - content is safe',            │
│      updated_at = NOW()                                            │
│  WHERE check_id = $1                                               │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
    │
    │ Notify original service of decision
    ↓
Return {message: "Review updated successfully", status: "pass"}
```

### 4. GDPR Data Export Flow

```
User requests data export
    │
    ↓
GET /api/v1/compliance/user/{user_id}/data-export?format=json
    │
    ↓
┌────────────────────────────────────────────────────────────────────┐
│  Export User Data (GDPR Article 15/20)                             │
│                                                                    │
│  Step 1: Validate authorization                                    │
│    (Handled by API Gateway JWT)                                    │
│                                                                    │
│  Step 2: Retrieve all user data                                    │
│    checks = repository.get_checks_by_user(                         │
│      user_id=user_id,                                              │
│      limit=10000  # All records                                    │
│    )                                                               │
│                                                                    │
│  Step 3: Get statistics                                            │
│    stats = repository.get_statistics(user_id=user_id)              │
│                                                                    │
│  Step 4: Compile export package                                    │
│    export_data = {                                                 │
│      "user_id": user_id,                                           │
│      "export_date": datetime.utcnow().isoformat(),                 │
│      "export_type": "gdpr_data_export",                            │
│      "total_checks": len(checks),                                  │
│      "checks": [format_check(c) for c in checks],                  │
│      "statistics": stats                                           │
│    }                                                               │
│                                                                    │
│  Step 5: Format response (JSON or CSV)                             │
│    if format == "json":                                            │
│      return JSONResponse(export_data)                              │
│    else:                                                           │
│      return StreamingResponse(csv_data, media_type="text/csv")     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
    │
    ↓
Return downloadable data file
```

---

## Technology Stack

### Core Technologies
- **Python 3.11+**: Programming language
- **FastAPI 0.104+**: Web framework
- **Pydantic 2.0+**: Data validation
- **asyncio**: Async/await concurrency
- **uvicorn**: ASGI server
- **re** (regex): Pattern matching for PII and injection detection

### Data Storage
- **PostgreSQL 15+**: Primary database
- **AsyncPostgresClient** (gRPC): Database communication
- **Schema**: `compliance`
- **Tables**: `compliance_checks`, `compliance_policies`, `user_consents`

### Event-Driven
- **NATS 2.9+**: Event bus
- **Subjects**: `compliance.*`
- **Publishers**: Compliance Service
- **Subscribers**: Audit, Analytics, Notification, Account services

### Service Discovery
- **Consul 1.15+**: Service registry
- **Health Checks**: HTTP `/health`
- **Metadata**: Route registration, capabilities

### External Integrations (Optional)
- **OpenAI Moderation API**: Enhanced content moderation
- **AWS Comprehend**: Future - NLP-based detection
- **Perspective API**: Future - toxicity scoring

### Dependency Injection
- **Protocols (typing.Protocol)**: Interface definitions
- **Factory Pattern**: Production vs test instances
- **ConfigManager**: Environment-based configuration

### Observability
- **Structured Logging**: JSON format via core.logger
- **Health Endpoints**: `/health`, `/status`
- **Processing Time Tracking**: Millisecond resolution

---

## Security Considerations

### Input Validation
- **Pydantic Models**: All requests validated
- **Content Sanitization**: Prevent XSS in stored data
- **SQL Injection**: Parameterized queries via gRPC
- **Size Limits**: Content size restrictions

### PII Protection
- **Masking**: Detected PII masked in logs and responses (show first 2 + last 2 chars)
- **No Content Storage**: Raw content not persisted, only hashes
- **Secure Logging**: PII never logged in plain text
- **GDPR Compliance**: Full deletion support

### Access Control
- **JWT Authentication**: Handled by API Gateway
- **User Isolation**: All queries filtered by user_id
- **Admin Endpoints**: Role-based access for policy management
- **Rate Limiting**: Future enhancement

### Data Privacy
- **Content Hashing**: SHA-256 for deduplication without storing content
- **Soft Delete**: Audit trail preserved
- **GDPR Support**: Data export, deletion, consent management
- **PCI-DSS**: Credit card detection and blocking

### External API Security
- **API Key Management**: Secure storage for OpenAI keys
- **Fallback Strategy**: Local rules if external API unavailable
- **Timeout Handling**: Prevent hanging on external calls

---

## Performance Optimization

### Latency Optimization
- **Concurrent Checks**: `asyncio.gather` for parallel check execution
- **Early Exit**: Stop on first BLOCKED result
- **Policy Caching**: Cache frequently-used policies
- **Connection Pooling**: gRPC client pools connections

### Database Optimization
- **Strategic Indexes**: check_id, user_id, status, risk_level, checked_at
- **Partial Indexes**: Only human_review_required=TRUE for review queue
- **GIN Indexes**: JSONB violations field for complex queries
- **Query Optimization**: Parameterized queries, LIMIT/OFFSET

### API Optimization
- **Async Operations**: All I/O is async
- **Streaming Responses**: CSV exports streamed
- **Pagination**: Max 100 items per page
- **Batch Processing**: Up to 100 items per batch

### Event Publishing
- **Non-Blocking**: Event failures don't block operations
- **Async Publishing**: Fire-and-forget pattern
- **Error Logging**: Failed publishes logged for investigation

### Target Performance
- **Single Check**: <200ms (p95)
- **Batch Check (100 items)**: <5000ms (p95)
- **Policy Lookup**: <50ms
- **Statistics Query**: <200ms
- **Health Check**: <20ms

---

## Error Handling

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: New policy created
- `400 Bad Request`: Validation error, missing confirmation
- `404 Not Found`: Check or policy not found
- `500 Internal Server Error`: Database error, unexpected error
- `503 Service Unavailable`: Database unavailable

### Error Response Format
```json
{
  "detail": "Compliance check not found with check_id: chk_xyz"
}
```

### Exception Handling
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": str(request.url)
        }
    )
```

### Graceful Degradation
- **OpenAI Unavailable**: Fall back to local moderation rules
- **Event Bus Down**: Log warning, continue processing
- **Database Error**: Return 503, log detailed error
- **External Timeout**: Use default safe response

---

## Testing Strategy

### Contract Testing (Layer 4 & 5)
- **Data Contract**: Pydantic schema validation for all models
- **Logic Contract**: Business rule documentation (40-50 rules)
- **Component Tests**: Factory, builder, validation tests

### Unit Testing
- **Service Layer**: Mock repository, test business logic
- **PII Detection**: Test all regex patterns with edge cases
- **Prompt Injection**: Test pattern detection accuracy
- **Risk Calculation**: Test threshold logic

### Integration Testing
- **HTTP + Database**: Full request/response cycle
- **Event Publishing**: Verify events published correctly
- **GDPR Endpoints**: Test export and deletion

### API Testing
- **Endpoint Contracts**: All 18 endpoints tested
- **Error Handling**: Validation, not found, server errors
- **Response Times**: Verify <200ms for single checks

### Smoke Testing
- **E2E Scripts**: Bash scripts for critical paths
- **Health Checks**: Service startup validation
- **Database Connectivity**: PostgreSQL availability

---

## Deployment Configuration

### Environment Variables
```bash
# Service Configuration
COMPLIANCE_SERVICE_PORT=8226
COMPLIANCE_SERVICE_HOST=0.0.0.0

# PostgreSQL
POSTGRES_HOST=isa-postgres-grpc
POSTGRES_PORT=50061

# NATS
NATS_HOST=isa-nats
NATS_PORT=4222

# Consul
CONSUL_ENABLED=true
CONSUL_HOST=localhost
CONSUL_PORT=8500

# OpenAI (Optional)
OPENAI_API_KEY=sk-xxx
ENABLE_OPENAI_MODERATION=true
```

### Docker Configuration
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY microservices/compliance_service /app/microservices/compliance_service
COPY core /app/core
COPY isa_common /app/isa_common

EXPOSE 8226
CMD ["uvicorn", "microservices.compliance_service.main:app", "--host", "0.0.0.0", "--port", "8226"]
```

### Kubernetes Resources
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliance-service
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: compliance-service
        image: isa/compliance-service:latest
        ports:
        - containerPort: 8226
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
            port: 8226
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8226
          initialDelaySeconds: 5
          periodSeconds: 10
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-22
**Maintained By**: Compliance Service Engineering Team
**Related Documents**:
- Domain Context: docs/domain/compliance_service.md
- PRD: docs/prd/compliance_service.md
- Data Contract: tests/contracts/compliance/data_contract.py
- Logic Contract: tests/contracts/compliance/logic_contract.md
- System Contract: tests/contracts/compliance/system_contract.md
