# Audit Service - Design Document

## Design Overview

**Service Name**: audit_service
**Port**: 8204
**Version**: 1.0.0
**Protocol**: HTTP REST API + NATS Event Subscription
**Last Updated**: 2025-12-22

### Design Principles
1. **Compliance-First**: Every design decision supports regulatory requirements (GDPR, SOX, HIPAA)
2. **Immutable Audit Trail**: Events cannot be modified after creation
3. **Universal Event Capture**: Wildcard NATS subscription captures all platform events
4. **Idempotent Processing**: Duplicate events handled gracefully
5. **Real-Time Analysis**: High-severity events trigger immediate analysis
6. **Graceful Degradation**: Processing errors don't crash the service

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        External Clients                                  │
│   (Admin Dashboard, Security Tools, Compliance Systems, Other Services) │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTP REST API
                                    │ (via API Gateway - JWT validation)
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                     Audit Service (Port 8204)                            │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                 FastAPI HTTP Layer (main.py)                        │ │
│  │  - Request validation (Pydantic models)                            │ │
│  │  - Response formatting                                              │ │
│  │  - Error handling & exception handlers                              │ │
│  │  - Health checks (/health, /health/detailed)                        │ │
│  │  - Lifecycle management (startup/shutdown)                          │ │
│  │  - Consul registration with route metadata                          │ │
│  └──────────────────────────────┬─────────────────────────────────────┘ │
│                                 │                                        │
│  ┌──────────────────────────────▼─────────────────────────────────────┐ │
│  │              Service Layer (audit_service.py)                       │ │
│  │  - Audit event logging with compliance tagging                      │ │
│  │  - Event querying with complex filters                              │ │
│  │  - User activity tracking and summarization                         │ │
│  │  - Security alert creation and management                           │ │
│  │  - Compliance report generation                                     │ │
│  │  - Real-time event analysis                                         │ │
│  │  - Statistics aggregation                                           │ │
│  └──────────────────────────────┬─────────────────────────────────────┘ │
│                                 │                                        │
│  ┌──────────────────────────────▼─────────────────────────────────────┐ │
│  │            Repository Layer (audit_repository.py)                   │ │
│  │  - PostgreSQL gRPC communication                                   │ │
│  │  - Query construction (parameterized)                              │ │
│  │  - Result parsing (proto JSONB to Python)                          │ │
│  │  - CRUD operations for audit events                                │ │
│  │  - Statistics queries                                               │ │
│  │  - Data cleanup operations                                          │ │
│  └──────────────────────────────┬─────────────────────────────────────┘ │
│                                 │                                        │
│  ┌──────────────────────────────▼─────────────────────────────────────┐ │
│  │            Event Handlers (events/handlers.py)                      │ │
│  │  - NATS wildcard subscription (*.*) processing                     │ │
│  │  - Event type mapping (NATS → Audit EventType)                     │ │
│  │  - Category and severity determination                             │ │
│  │  - Idempotent event processing                                     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                 │                                        │
│  ┌──────────────────────────────▼─────────────────────────────────────┐ │
│  │          Dependency Injection Layer (protocols.py, factory.py)      │ │
│  │  - AuditRepositoryProtocol (interface)                             │ │
│  │  - EventBusProtocol (interface)                                    │ │
│  │  - create_audit_service (factory for production)                   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────┼─────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
            ↓                       ↓                       ↓
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│    PostgreSQL     │   │       NATS        │   │      Consul       │
│     (gRPC)        │   │    Event Bus      │   │   (Discovery)     │
│                   │   │                   │   │                   │
│  Schema:          │   │  Subscribes:      │   │  Service:         │
│    audit          │   │    *.*            │   │    audit_service  │
│                   │   │    (all events)   │   │                   │
│  Table:           │   │                   │   │  Health:          │
│    audit_events   │   │  Publishes:       │   │    /health        │
│                   │   │    audit.event_   │   │                   │
│  Indexes:         │   │      recorded     │   │  Tags:            │
│    - event_id     │   │                   │   │    - governance   │
│    - user_id      │   │                   │   │    - audit        │
│    - event_type   │   │                   │   │    - compliance   │
│    - timestamp    │   │                   │   │                   │
└───────────────────┘   └───────────────────┘   └───────────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Audit Service                                   │
│                                                                          │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐  │
│  │     Models      │───→│     Service     │───→│     Repository      │  │
│  │   (Pydantic)    │    │   (Business)    │    │      (Data)         │  │
│  │                 │    │                 │    │                     │  │
│  │ - AuditEvent    │    │ - AuditService  │    │ - AuditRepository   │  │
│  │ - SecurityEvent │    │                 │    │                     │  │
│  │ - UserActivity  │    │ Methods:        │    │ Methods:            │  │
│  │ - Compliance    │    │ - log_event()   │    │ - create_audit_     │  │
│  │   Report        │    │ - query_events()│    │     event()         │  │
│  │ - UserActivity  │    │ - get_user_     │    │ - query_audit_      │  │
│  │   Summary       │    │     activities()│    │     events()        │  │
│  │ - Event Enums   │    │ - create_       │    │ - get_user_         │  │
│  │   (EventType,   │    │     security_   │    │     activities()    │  │
│  │    Severity,    │    │     alert()     │    │ - get_security_     │  │
│  │    Category)    │    │ - generate_     │    │     events()        │  │
│  │                 │    │     compliance_ │    │ - get_statistics()  │  │
│  │                 │    │     report()    │    │ - cleanup_old_      │  │
│  │                 │    │                 │    │     events()        │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────────┘  │
│          ↑                       ↑                       ↑               │
│          │                       │                       │               │
│  ┌───────┴───────────────────────┴───────────────────────┴────────────┐ │
│  │                   FastAPI Main (main.py)                            │ │
│  │  - Dependency Injection (get_audit_service)                        │ │
│  │  - Route Handlers (15 endpoints)                                    │ │
│  │  - Exception Handlers                                               │ │
│  │  - Lifespan Management                                              │ │
│  └─────────────────────────────┬──────────────────────────────────────┘ │
│                                │                                        │
│  ┌─────────────────────────────▼──────────────────────────────────────┐ │
│  │                    Event Handlers                                   │ │
│  │               (events/handlers.py)                                  │ │
│  │                                                                     │ │
│  │  - AuditEventHandlers class                                        │ │
│  │  - handle_nats_event() - Universal event processor                 │ │
│  │  - _map_nats_event_to_audit_type() - Event mapping                 │ │
│  │  - _determine_audit_category() - Category classification           │ │
│  │  - _determine_event_severity() - Severity classification           │ │
│  │  - _extract_resource_info() - Resource extraction                  │ │
│  │  - Idempotency via processed_event_ids cache                       │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                   Factory & Protocols                               │ │
│  │            (factory.py, protocols.py)                               │ │
│  │                                                                     │ │
│  │  - create_audit_service() - Production factory                     │ │
│  │  - AuditRepositoryProtocol - Repository interface                  │ │
│  │  - EventBusProtocol - Event bus interface                          │ │
│  │  - Custom exceptions (AuditNotFoundError, AuditValidationError)    │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Responsibilities**:
- HTTP request/response handling
- Request validation via Pydantic models
- Route definitions (15 endpoints)
- Health checks
- Service initialization (lifespan management)
- Consul registration with route metadata
- NATS event bus subscription setup
- Exception handling

**Key Endpoints**:
```python
# Health Checks
GET /health                                    # Basic health check
GET /health/detailed                           # Database connectivity check

# Service Information
GET /api/v1/audit/info                         # Service capabilities
GET /api/v1/audit/stats                        # Service statistics

# Audit Event Management
POST /api/v1/audit/events                      # Log single event
GET  /api/v1/audit/events                      # List events (GET params)
POST /api/v1/audit/events/query                # Query with complex filters
POST /api/v1/audit/events/batch                # Batch log events

# User Activity Tracking
GET /api/v1/audit/users/{user_id}/activities   # User activity history
GET /api/v1/audit/users/{user_id}/summary      # User activity summary

# Security Event Management
POST /api/v1/audit/security/alerts             # Create security alert
GET  /api/v1/audit/security/events             # List security events

# Compliance Reporting
POST /api/v1/audit/compliance/reports          # Generate compliance report
GET  /api/v1/audit/compliance/standards        # List compliance standards

# System Maintenance
POST /api/v1/audit/maintenance/cleanup         # Cleanup old data
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global audit_service, event_bus, consul_registry

    logger.info("Audit Service starting up...")

    # Initialize service via factory
    audit_service = create_audit_service(config=config_manager)

    # Check database connection
    if await audit_service.repository.check_connection():
        logger.info("Database connection successful")

    # Initialize event bus
    event_bus = await get_event_bus("audit_service")

    # Initialize event handlers
    event_handlers = AuditEventHandlers(audit_service)

    # Subscribe to ALL events using wildcard pattern
    await event_bus.subscribe_to_events(
        pattern="*.*",  # Subscribe to all events
        handler=event_handlers.handle_nats_event
    )
    logger.info("Subscribed to all NATS events (*.*)")

    # Consul registration
    if config.consul_enabled:
        consul_registry = ConsulRegistry(
            service_name="audit_service",
            service_port=8204,
            tags=["governance-microservice", "audit", "compliance"],
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

### 2. Service Layer (audit_service.py)

**Class**: `AuditService`

**Responsibilities**:
- Business logic execution
- Audit event logging with compliance tagging
- Event querying with validation
- User activity tracking
- Security alert management
- Compliance report generation
- Real-time event analysis
- Statistics aggregation

**Key Methods**:
```python
class AuditService:
    def __init__(self, repository: Optional[AuditRepositoryProtocol] = None):
        self.repository = repository

        # Risk thresholds for scoring
        self.risk_thresholds = {
            "low": 30, "medium": 60, "high": 80, "critical": 95
        }

        # Compliance standards configuration
        self.compliance_standards = {
            "GDPR": {
                "retention_days": 2555,  # 7 years
                "required_fields": ["user_id", "action", "timestamp", "ip_address"],
                "sensitive_events": [EventType.USER_DELETE, EventType.PERMISSION_GRANT]
            },
            "SOX": {
                "retention_days": 2555,
                "required_fields": ["user_id", "action", "timestamp"],
                "sensitive_events": [EventType.RESOURCE_UPDATE, EventType.PERMISSION_UPDATE]
            },
            "HIPAA": {
                "retention_days": 2190,  # 6 years
                "required_fields": ["user_id", "action", "timestamp", "resource_type"],
                "sensitive_events": [EventType.RESOURCE_ACCESS, EventType.USER_UPDATE]
            }
        }

    # Core Audit Event Operations
    async def log_event(
        self,
        request: AuditEventCreateRequest
    ) -> Optional[AuditEventResponse]:
        """
        Log audit event with automatic compliance tagging.

        1. Create AuditEvent from request
        2. Apply compliance policies (retention, flags)
        3. Persist to database
        4. Trigger real-time analysis
        5. Return response
        """
        audit_event = AuditEvent(
            id=str(uuid.uuid4()),
            event_type=request.event_type,
            category=request.category,
            severity=request.severity,
            status=EventStatus.SUCCESS if request.success else EventStatus.FAILURE,
            action=request.action,
            user_id=request.user_id,
            # ... other fields
            timestamp=datetime.utcnow()
        )

        # Auto-apply compliance policies
        await self._apply_compliance_policies(audit_event)

        # Persist
        created_event = await self.repository.create_audit_event(audit_event)

        # Real-time analysis for high-severity events
        await self._trigger_real_time_analysis(created_event)

        return AuditEventResponse.from_event(created_event)

    async def query_events(
        self,
        query: AuditQueryRequest
    ) -> AuditQueryResponse:
        """
        Query audit events with complex filters.

        Validates:
        - Limit <= 1000
        - Time range <= 365 days
        - Start time < end time
        """
        await self._validate_query_parameters(query)
        events = await self.repository.query_audit_events(query)
        return AuditQueryResponse(
            events=[AuditEventResponse.from_event(e) for e in events],
            total_count=len(events),
            page_info={"limit": query.limit, "offset": query.offset},
            filters_applied={...}
        )

    # User Activity Operations
    async def get_user_activities(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100
    ) -> List[UserActivity]:
        """Get user activity history"""
        return await self.repository.get_user_activities(user_id, days, limit)

    async def get_user_activity_summary(
        self,
        user_id: str,
        days: int = 30
    ) -> UserActivitySummary:
        """Generate user activity summary with risk score"""
        summary_data = await self.repository.get_user_activity_summary(user_id, days)
        return UserActivitySummary(
            user_id=user_id,
            total_activities=summary_data.get("total_activities", 0),
            success_count=summary_data.get("success_count", 0),
            failure_count=summary_data.get("failure_count", 0),
            last_activity=summary_data.get("last_activity"),
            most_common_activities=summary_data.get("most_common_activities", []),
            risk_score=summary_data.get("risk_score", 0.0)
        )

    # Security Event Operations
    async def create_security_alert(
        self,
        alert: SecurityAlertRequest
    ) -> Optional[SecurityEvent]:
        """
        Create security alert with threat level calculation.
        """
        security_event = SecurityEvent(
            id=str(uuid.uuid4()),
            event_type=EventType.SECURITY_ALERT,
            severity=alert.severity,
            threat_level=self._calculate_threat_level(alert.severity),
            source_ip=alert.source_ip,
            target_resource=alert.target_resource,
            detection_method="manual_report",
            confidence_score=0.8,
            response_action="investigation_required",
            investigation_status="open",
            detected_at=datetime.utcnow()
        )
        return await self.repository.create_security_event(security_event)

    # Compliance Reporting
    async def generate_compliance_report(
        self,
        request: ComplianceReportRequest
    ) -> Optional[ComplianceReport]:
        """
        Generate compliance report for specified standard.

        1. Validate compliance standard is supported
        2. Query events for period
        3. Analyze each event against standard requirements
        4. Calculate compliance score
        5. Generate findings and recommendations
        """
        standard_config = self.compliance_standards.get(request.compliance_standard)
        if not standard_config:
            return None

        # Query events
        events = await self.repository.query_audit_events(
            AuditQueryRequest(
                start_time=request.period_start,
                end_time=request.period_end,
                limit=1000
            )
        )

        # Analyze compliance
        analysis = await self._analyze_compliance(events, standard_config)

        return ComplianceReport(
            compliance_standard=request.compliance_standard,
            total_events=len(events),
            compliant_events=analysis["compliant_count"],
            non_compliant_events=analysis["non_compliant_count"],
            compliance_score=analysis["compliance_score"],
            findings=analysis["findings"],
            recommendations=analysis["recommendations"],
            risk_assessment=analysis["risk_assessment"]
        )

    # Private Methods
    async def _apply_compliance_policies(self, event: AuditEvent) -> None:
        """Apply retention policies and compliance flags"""
        # Set retention policy based on category
        if event.category == AuditCategory.SECURITY:
            event.retention_policy = "7_years"
        elif event.category == AuditCategory.AUTHENTICATION:
            event.retention_policy = "3_years"
        else:
            event.retention_policy = "1_year"

        # Set compliance flags
        compliance_flags = []
        if event.user_id and event.event_type in [EventType.USER_DELETE, EventType.USER_UPDATE]:
            compliance_flags.append("GDPR")
        if event.resource_type and event.event_type in [EventType.RESOURCE_UPDATE, EventType.PERMISSION_UPDATE]:
            compliance_flags.append("SOX")
        event.compliance_flags = compliance_flags

    async def _trigger_real_time_analysis(self, event: AuditEvent) -> None:
        """Trigger analysis for high-severity events"""
        if event.severity in [EventSeverity.HIGH, EventSeverity.CRITICAL]:
            logger.warning(f"High severity event: {event.event_type.value} - {event.action}")
        if not event.success and event.category == AuditCategory.AUTHENTICATION:
            logger.warning(f"Auth failure: user={event.user_id}, IP={event.ip_address}")
```

### 3. Repository Layer (audit_repository.py)

**Class**: `AuditRepository`

**Responsibilities**:
- PostgreSQL CRUD operations via gRPC
- Query construction (parameterized for SQL injection prevention)
- Result parsing
- Statistics aggregation
- Data cleanup

**Key Methods**:
```python
class AuditRepository:
    def __init__(self, config: Optional[ConfigManager] = None):
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061
        )
        self.db = AsyncPostgresClient(host=host, port=port, user_id="audit_service")
        self.schema = "audit"
        self.audit_events_table = "audit_events"

    async def create_audit_event(self, event: AuditEvent) -> Optional[AuditEvent]:
        """Insert audit event into database"""
        query = f'''
            INSERT INTO {self.schema}.{self.audit_events_table} (
                event_id, event_type, event_category, event_severity, event_status,
                user_id, organization_id, session_id, ip_address, user_agent,
                action, resource_type, resource_id, resource_name,
                error_message, risk_score, compliance_flags,
                metadata, tags, event_timestamp, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                      $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
            RETURNING *
        '''
        async with self.db:
            results = await self.db.query(query, params=[...])
        return self._row_to_audit_event(results[0]) if results else None

    async def query_audit_events(self, query: AuditQueryRequest) -> List[AuditEvent]:
        """Query audit events with filters"""
        conditions = []
        params = []
        param_count = 0

        if query.user_id:
            param_count += 1
            conditions.append(f"user_id = ${param_count}")
            params.append(query.user_id)

        if query.event_types:
            param_count += 1
            conditions.append(f"event_type = ANY(${param_count})")
            params.append([et.value for et in query.event_types])

        if query.start_time:
            param_count += 1
            conditions.append(f"event_timestamp >= ${param_count}")
            params.append(query.start_time)

        if query.end_time:
            param_count += 1
            conditions.append(f"event_timestamp <= ${param_count}")
            params.append(query.end_time)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        sql = f'''
            SELECT * FROM {self.schema}.{self.audit_events_table}
            {where_clause}
            ORDER BY event_timestamp DESC
            LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        '''
        params.extend([query.limit, query.offset])

        async with self.db:
            results = await self.db.query(sql, params=params)
        return [self._row_to_audit_event(row) for row in results]

    async def get_user_activities(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get user activities for specified period"""
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        query = f'''
            SELECT * FROM {self.schema}.{self.audit_events_table}
            WHERE user_id = $1 AND event_timestamp >= $2
            ORDER BY event_timestamp DESC
            LIMIT $3
        '''
        async with self.db:
            results = await self.db.query(query, params=[user_id, start_time, limit])
        return [dict(row) for row in results] if results else []

    async def get_user_activity_summary(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get aggregated user activity statistics"""
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        query = f'''
            SELECT
                COUNT(*) as total_activities,
                COUNT(CASE WHEN event_status = 'success' THEN 1 END) as success_count,
                COUNT(CASE WHEN event_status = 'failure' THEN 1 END) as failure_count,
                MAX(event_timestamp) as last_activity
            FROM {self.schema}.{self.audit_events_table}
            WHERE user_id = $1 AND event_timestamp >= $2
        '''
        async with self.db:
            results = await self.db.query(query, params=[user_id, start_time])
        return results[0] if results else {}

    async def cleanup_old_events(self, retention_days: int = 365) -> int:
        """Delete events older than retention period"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        query = f'''
            DELETE FROM {self.schema}.{self.audit_events_table}
            WHERE event_timestamp < $1
        '''
        async with self.db:
            count = await self.db.execute(query, params=[cutoff_date])
        return count if count else 0
```

### 4. Event Handlers Layer (events/handlers.py)

**Class**: `AuditEventHandlers`

**Responsibilities**:
- NATS wildcard subscription processing
- Event type mapping (NATS to Audit EventType)
- Category and severity determination
- Idempotent event processing
- Resource information extraction

**Key Methods**:
```python
class AuditEventHandlers:
    def __init__(self, audit_service):
        self.audit_service = audit_service
        self.processed_event_ids = set()  # Idempotency cache

    async def handle_nats_event(self, event):
        """
        Universal NATS event handler.
        Maps any NATS event to audit event and logs it.
        """
        # Idempotency check
        if event.id in self.processed_event_ids:
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        # Extract event details
        event_type_str = event.type
        source = event.source
        data = event.data

        # Map to audit types
        audit_event_type = self._map_nats_event_to_audit_type(event_type_str)
        category = self._determine_audit_category(event_type_str)
        severity = self._determine_event_severity(event_type_str, data)

        # Extract user_id with fallbacks
        user_id = data.get("user_id") or data.get("shared_by") or "system"

        # Extract resource info
        resource_type, resource_id, resource_name = self._extract_resource_info(
            event_type_str, data
        )

        # Create audit request
        audit_request = AuditEventCreateRequest(
            event_type=audit_event_type,
            category=category,
            severity=severity,
            action=event_type_str,
            description=f"NATS event: {event_type_str} from {source}",
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            success=True,
            metadata={
                "nats_event_id": event.id,
                "nats_event_source": source,
                "nats_event_type": event_type_str,
                "original_data": data
            },
            tags=["nats_event", source, event_type_str]
        )

        # Log audit event
        result = await self.audit_service.log_event(audit_request)

        if result:
            # Mark as processed
            self.processed_event_ids.add(event.id)
            # Limit cache size
            if len(self.processed_event_ids) > 10000:
                self.processed_event_ids = set(list(self.processed_event_ids)[5000:])

    def _map_nats_event_to_audit_type(self, nats_event_type: str) -> EventType:
        """Map NATS event type to audit EventType"""
        if "user." in nats_event_type:
            if "created" in nats_event_type:
                return EventType.USER_REGISTER
            elif "logged_in" in nats_event_type:
                return EventType.USER_LOGIN
            elif "deleted" in nats_event_type:
                return EventType.USER_DELETE
            else:
                return EventType.USER_UPDATE
        elif "organization." in nats_event_type:
            if "created" in nats_event_type:
                return EventType.ORGANIZATION_CREATE
            elif "member_added" in nats_event_type:
                return EventType.ORGANIZATION_JOIN
            elif "member_removed" in nats_event_type:
                return EventType.ORGANIZATION_LEAVE
            else:
                return EventType.ORGANIZATION_UPDATE
        elif "file." in nats_event_type:
            if "uploaded" in nats_event_type:
                return EventType.RESOURCE_CREATE
            elif "deleted" in nats_event_type:
                return EventType.RESOURCE_DELETE
            elif "shared" in nats_event_type:
                return EventType.PERMISSION_GRANT
        # Default
        return EventType.RESOURCE_ACCESS

    def _determine_audit_category(self, nats_event_type: str) -> AuditCategory:
        """Determine category based on event type"""
        if "user." in nats_event_type or "device.authenticated" in nats_event_type:
            return AuditCategory.AUTHENTICATION
        elif "permission" in nats_event_type or "member" in nats_event_type:
            return AuditCategory.AUTHORIZATION
        elif "payment" in nats_event_type or "subscription" in nats_event_type:
            return AuditCategory.CONFIGURATION
        elif "file." in nats_event_type or "device." in nats_event_type:
            return AuditCategory.DATA_ACCESS
        return AuditCategory.SYSTEM

    def _determine_event_severity(self, nats_event_type: str, data: dict) -> EventSeverity:
        """Determine severity based on event patterns"""
        # High severity: deletions, removals, failures
        if any(kw in nats_event_type for kw in ["deleted", "removed", "failed", "offline"]):
            return EventSeverity.HIGH
        # Medium severity: updates, shares, member changes
        elif any(kw in nats_event_type for kw in ["updated", "shared", "member_added"]):
            return EventSeverity.MEDIUM
        return EventSeverity.LOW
```

---

## Database Schema Design

### PostgreSQL Schema: `audit`

#### Table: audit.audit_events

```sql
-- Create audit schema
CREATE SCHEMA IF NOT EXISTS audit;

-- Create audit_events table
CREATE TABLE IF NOT EXISTS audit.audit_events (
    -- Primary Key
    event_id VARCHAR(50) PRIMARY KEY,

    -- Event Classification
    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(50) NOT NULL,
    event_severity VARCHAR(20) NOT NULL DEFAULT 'low',
    event_status VARCHAR(20) NOT NULL DEFAULT 'success',

    -- Actor Information
    user_id VARCHAR(255),
    organization_id VARCHAR(255),
    session_id VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,

    -- Action Information
    action VARCHAR(255) NOT NULL,
    description TEXT,
    api_endpoint VARCHAR(255),
    http_method VARCHAR(10),

    -- Resource Information
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    resource_name VARCHAR(255),

    -- Result Information
    status_code INTEGER,
    error_code VARCHAR(50),
    error_message TEXT,
    changes_made JSONB DEFAULT '{}',

    -- Security & Risk
    risk_score FLOAT DEFAULT 0.0,
    threat_indicators JSONB DEFAULT '[]',

    -- Compliance
    compliance_flags JSONB DEFAULT '[]',
    retention_policy VARCHAR(50),

    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[],

    -- Timestamps
    event_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT event_severity_check CHECK (
        event_severity IN ('low', 'medium', 'high', 'critical')
    ),
    CONSTRAINT event_status_check CHECK (
        event_status IN ('success', 'failure', 'pending', 'error')
    ),
    CONSTRAINT event_category_check CHECK (
        event_category IN ('authentication', 'authorization', 'data_access',
                          'configuration', 'security', 'compliance', 'system')
    )
);

-- Indexes for query performance
CREATE INDEX idx_audit_events_user ON audit.audit_events(user_id);
CREATE INDEX idx_audit_events_org ON audit.audit_events(organization_id);
CREATE INDEX idx_audit_events_type ON audit.audit_events(event_type);
CREATE INDEX idx_audit_events_category ON audit.audit_events(event_category);
CREATE INDEX idx_audit_events_severity ON audit.audit_events(event_severity);
CREATE INDEX idx_audit_events_timestamp ON audit.audit_events(event_timestamp DESC);
CREATE INDEX idx_audit_events_resource ON audit.audit_events(resource_type, resource_id);
CREATE INDEX idx_audit_events_compliance ON audit.audit_events USING GIN(compliance_flags);
CREATE INDEX idx_audit_events_tags ON audit.audit_events USING GIN(tags);

-- Composite index for common query patterns
CREATE INDEX idx_audit_events_user_time ON audit.audit_events(user_id, event_timestamp DESC);
CREATE INDEX idx_audit_events_type_time ON audit.audit_events(event_type, event_timestamp DESC);

-- Partial index for security events (frequently queried)
CREATE INDEX idx_audit_security_events ON audit.audit_events(event_timestamp DESC)
    WHERE event_type = 'security_alert';

-- Comments
COMMENT ON TABLE audit.audit_events IS 'Immutable audit trail for all platform events';
COMMENT ON COLUMN audit.audit_events.event_id IS 'Unique event identifier (UUID)';
COMMENT ON COLUMN audit.audit_events.compliance_flags IS 'Regulatory compliance markers (GDPR, SOX, HIPAA)';
COMMENT ON COLUMN audit.audit_events.retention_policy IS 'Data retention tier (1_year, 3_years, 7_years)';
```

### Index Strategy

| Index Name | Columns | Type | Purpose |
|------------|---------|------|---------|
| `event_id` (PK) | event_id | B-tree | Fast lookup by ID |
| `idx_audit_events_user` | user_id | B-tree | User activity queries |
| `idx_audit_events_org` | organization_id | B-tree | Organization filtering |
| `idx_audit_events_type` | event_type | B-tree | Event type filtering |
| `idx_audit_events_timestamp` | event_timestamp DESC | B-tree | Time-based queries |
| `idx_audit_events_compliance` | compliance_flags | GIN | Compliance flag queries |
| `idx_audit_events_tags` | tags | GIN | Tag-based filtering |
| `idx_audit_events_user_time` | user_id, event_timestamp | Composite | User activity with time |
| `idx_audit_security_events` | event_timestamp (partial) | B-tree | Security event queries |

### Database Migrations

| Version | Description | File |
|---------|-------------|------|
| 001 | Initial audit schema | `001_create_audit_schema.sql` |
| 002 | Add compliance indexes | `002_add_compliance_indexes.sql` |
| 003 | Add security event index | `003_add_security_index.sql` |

---

## Data Flow Diagrams

### 1. Audit Event Logging Flow (HTTP API)

```
Client                    Service                  Repository              PostgreSQL
  │                          │                          │                      │
  │  POST /api/v1/audit/events                          │                      │
  │  {event_type, category, action, ...}                │                      │
  │─────────────────────────>│                          │                      │
  │                          │                          │                      │
  │                          │  Validate request        │                      │
  │                          │─────────┐                │                      │
  │                          │<────────┘                │                      │
  │                          │                          │                      │
  │                          │  Create AuditEvent       │                      │
  │                          │  Generate UUID           │                      │
  │                          │  Set timestamp           │                      │
  │                          │─────────┐                │                      │
  │                          │<────────┘                │                      │
  │                          │                          │                      │
  │                          │  _apply_compliance_policies()                   │
  │                          │  - Set retention_policy  │                      │
  │                          │  - Set compliance_flags  │                      │
  │                          │─────────┐                │                      │
  │                          │<────────┘                │                      │
  │                          │                          │                      │
  │                          │  create_audit_event()    │                      │
  │                          │─────────────────────────>│                      │
  │                          │                          │  INSERT INTO         │
  │                          │                          │  audit.audit_events  │
  │                          │                          │─────────────────────>│
  │                          │                          │                      │
  │                          │                          │  RETURNING *         │
  │                          │                          │<─────────────────────│
  │                          │  Return created event    │                      │
  │                          │<─────────────────────────│                      │
  │                          │                          │                      │
  │                          │  _trigger_real_time_analysis()                  │
  │                          │  (for high-severity events)                     │
  │                          │─────────┐                │                      │
  │                          │<────────┘                │                      │
  │                          │                          │                      │
  │  201 Created             │                          │                      │
  │  {id, event_type, ...}   │                          │                      │
  │<─────────────────────────│                          │                      │
```

### 2. NATS Event Capture Flow (Automatic)

```
Any Service              NATS Bus              AuditEventHandlers         AuditService
  │                          │                          │                      │
  │  Publish event           │                          │                      │
  │  e.g., user.created      │                          │                      │
  │─────────────────────────>│                          │                      │
  │                          │                          │                      │
  │                          │  Deliver to subscriber   │                      │
  │                          │  (pattern: *.*)          │                      │
  │                          │─────────────────────────>│                      │
  │                          │                          │                      │
  │                          │                          │  Idempotency check   │
  │                          │                          │  (processed_event_ids)│
  │                          │                          │─────────┐            │
  │                          │                          │<────────┘            │
  │                          │                          │                      │
  │                          │                          │  Map NATS event to   │
  │                          │                          │  audit event type    │
  │                          │                          │─────────┐            │
  │                          │                          │<────────┘            │
  │                          │                          │                      │
  │                          │                          │  Determine category  │
  │                          │                          │  and severity        │
  │                          │                          │─────────┐            │
  │                          │                          │<────────┘            │
  │                          │                          │                      │
  │                          │                          │  Extract resource    │
  │                          │                          │  information         │
  │                          │                          │─────────┐            │
  │                          │                          │<────────┘            │
  │                          │                          │                      │
  │                          │                          │  audit_service.      │
  │                          │                          │    log_event()       │
  │                          │                          │─────────────────────>│
  │                          │                          │                      │
  │                          │                          │  (Persist to DB)     │
  │                          │                          │                      │
  │                          │                          │  Return result       │
  │                          │                          │<─────────────────────│
  │                          │                          │                      │
  │                          │                          │  Add to processed_   │
  │                          │                          │  event_ids cache     │
  │                          │                          │─────────┐            │
  │                          │                          │<────────┘            │
  │                          │                          │                      │
  │                          │  ACK                     │                      │
  │                          │<─────────────────────────│                      │
```

### 3. Compliance Report Generation Flow

```
Compliance Officer         Service                  Repository
  │                          │                          │
  │  POST /api/v1/audit/compliance/reports              │
  │  {compliance_standard: "GDPR",                      │
  │   period_start, period_end}                         │
  │─────────────────────────>│                          │
  │                          │                          │
  │                          │  Validate standard       │
  │                          │  supported               │
  │                          │─────────┐                │
  │                          │<────────┘                │
  │                          │                          │
  │                          │  Get standard config     │
  │                          │  (retention_days,        │
  │                          │   required_fields,       │
  │                          │   sensitive_events)      │
  │                          │─────────┐                │
  │                          │<────────┘                │
  │                          │                          │
  │                          │  query_audit_events()    │
  │                          │  (for period)            │
  │                          │─────────────────────────>│
  │                          │                          │  SELECT * FROM
  │                          │                          │  audit.audit_events
  │                          │                          │  WHERE timestamp
  │                          │                          │    BETWEEN $1 AND $2
  │                          │  Return events           │
  │                          │<─────────────────────────│
  │                          │                          │
  │                          │  _analyze_compliance()   │
  │                          │  For each event:         │
  │                          │  - Check required fields │
  │                          │  - Validate sensitive    │
  │                          │    events have justification
  │                          │  - Track compliant/      │
  │                          │    non-compliant counts  │
  │                          │─────────┐                │
  │                          │<────────┘                │
  │                          │                          │
  │                          │  Calculate score         │
  │                          │  (compliant/total * 100) │
  │                          │─────────┐                │
  │                          │<────────┘                │
  │                          │                          │
  │                          │  Generate recommendations│
  │                          │  and risk assessment     │
  │                          │─────────┐                │
  │                          │<────────┘                │
  │                          │                          │
  │  200 OK                  │                          │
  │  {compliance_score: 98.7,│                          │
  │   findings: [...],       │                          │
  │   recommendations: [...]}│                          │
  │<─────────────────────────│                          │
```

### 4. User Activity Investigation Flow

```
Security Analyst           Service                  Repository
  │                          │                          │
  │  GET /api/v1/audit/users/{user_id}/activities       │
  │  ?days=90&limit=200      │                          │
  │─────────────────────────>│                          │
  │                          │                          │
  │                          │  get_user_activities()   │
  │                          │─────────────────────────>│
  │                          │                          │  SELECT * FROM
  │                          │                          │  audit.audit_events
  │                          │                          │  WHERE user_id = $1
  │                          │                          │    AND timestamp >= $2
  │                          │                          │  ORDER BY timestamp DESC
  │                          │                          │  LIMIT $3
  │                          │  Return activities       │
  │                          │<─────────────────────────│
  │                          │                          │
  │                          │  Convert to JSON-        │
  │                          │  serializable format     │
  │                          │─────────┐                │
  │                          │<────────┘                │
  │                          │                          │
  │  200 OK                  │                          │
  │  {user_id, activities,   │                          │
  │   total_count, period_days}                         │
  │<─────────────────────────│                          │
  │                          │                          │
  │  GET /api/v1/audit/users/{user_id}/summary          │
  │  ?days=90                 │                          │
  │─────────────────────────>│                          │
  │                          │                          │
  │                          │  get_user_activity_      │
  │                          │    summary()             │
  │                          │─────────────────────────>│
  │                          │                          │  SELECT
  │                          │                          │    COUNT(*),
  │                          │                          │    COUNT(success),
  │                          │                          │    COUNT(failure),
  │                          │                          │    MAX(timestamp)
  │                          │                          │  FROM audit_events
  │                          │                          │  WHERE user_id = $1
  │                          │  Return summary          │
  │                          │<─────────────────────────│
  │                          │                          │
  │  200 OK                  │                          │
  │  {total_activities,      │                          │
  │   success_count,         │                          │
  │   failure_count,         │                          │
  │   risk_score}            │                          │
  │<─────────────────────────│                          │
```

---

## Event-Driven Architecture

### Event Subscription (Wildcard Pattern)

**NATS Subscription**:
```
Pattern: *.*
Purpose: Capture ALL events from ALL services
```

**Subscribed Event Patterns**:
| Pattern | Source Services | Audit Mapping |
|---------|----------------|---------------|
| `user.*` | account_service | AUTHENTICATION |
| `payment.*` | payment_service, billing_service | CONFIGURATION |
| `subscription.*` | subscription_service | CONFIGURATION |
| `organization.*` | organization_service | AUTHORIZATION |
| `device.*` | device_service | DATA_ACCESS |
| `file.*` | storage_service | DATA_ACCESS |
| `*` (all others) | Various | SYSTEM |

### Event Publishing

**NATS Subjects**:
```
audit.event_recorded    # Published for critical audit events
```

### Event Models (events/models.py)

```python
class AuditEventRecordedEventData(BaseModel):
    """Event: audit.event_recorded"""
    event_id: str
    event_type: str
    category: str
    severity: str
    user_id: Optional[str]
    action: str
    success: bool
    recorded_at: datetime
```

### Event Flow Diagram

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Account    │  │   Payment    │  │ Organization │  │   Storage    │
│   Service    │  │   Service    │  │   Service    │  │   Service    │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │                 │
       │ user.*          │ payment.*       │ organization.* │ file.*
       ↓                 ↓                 ↓                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                           NATS Event Bus                             │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    Subscription: *.*                            ││
│  │                    (All events captured)                        ││
│  └────────────────────────────┬────────────────────────────────────┘│
└───────────────────────────────┼─────────────────────────────────────┘
                                │
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         Audit Service                                │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    AuditEventHandlers                           ││
│  │                                                                 ││
│  │  1. Idempotency check (processed_event_ids cache)              ││
│  │  2. Map NATS event → Audit EventType                           ││
│  │  3. Determine category (AUTH, AUTHZ, DATA_ACCESS, etc.)        ││
│  │  4. Determine severity (LOW, MEDIUM, HIGH, CRITICAL)           ││
│  │  5. Extract user_id, resource info                             ││
│  │  6. Call audit_service.log_event()                             ││
│  │  7. Add to processed cache                                     ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                │                                    │
│                                ↓                                    │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                      PostgreSQL                                 ││
│  │              Schema: audit.audit_events                         ││
│  │                                                                 ││
│  │  - Immutable storage                                           ││
│  │  - Compliance flags applied                                    ││
│  │  - Retention policies enforced                                 ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Language | Python | 3.11+ | Primary language |
| Framework | FastAPI | 0.104+ | HTTP API framework |
| Validation | Pydantic | 2.0+ | Data validation |
| Async Runtime | asyncio | - | Async/await concurrency |
| ASGI Server | uvicorn | 0.23+ | ASGI server |

### Data Storage

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Database | PostgreSQL | 15+ | Primary data store |
| DB Access | AsyncPostgresClient | gRPC | Database communication |
| Schema | `audit` | - | Service schema |
| Table | `audit_events` | - | Main audit table |

### Event-Driven

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Event Bus | NATS | 2.9+ | Event messaging |
| Subscription | Wildcard (*.*) | - | Universal capture |
| Publisher | audit.event_recorded | - | Critical event alerts |

### Service Discovery

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Registry | Consul | 1.15+ | Service discovery |
| Health Check | HTTP /health | - | Health monitoring |
| Metadata | Route registry | - | API documentation |

### Dependency Injection

| Pattern | Implementation | Purpose |
|---------|----------------|---------|
| Protocols | typing.Protocol | Interface definitions |
| Factory | factory.py | Production vs test instances |
| Config | ConfigManager | Environment-based config |

### Observability

| Component | Technology | Purpose |
|-----------|------------|---------|
| Logging | core.logger | Structured JSON logging |
| Health | /health, /health/detailed | Health monitoring |
| Metrics | (future) | Prometheus metrics |

---

## Security Considerations

### Authentication
- **JWT Token Validation**: Handled by API Gateway
- **Public Endpoints**: /health, /api/v1/audit/info, /api/v1/audit/compliance/standards
- **Protected Endpoints**: All other endpoints require authentication

### Authorization
- **Admin Endpoints**: /api/v1/audit/maintenance/cleanup requires admin role
- **Security Endpoints**: Security alert creation requires security role
- **Data Scoping**: Future: Organization-based data isolation

### Data Protection
- **Immutability**: Audit events cannot be modified after creation
- **SQL Injection Prevention**: Parameterized queries via gRPC
- **Input Validation**: Pydantic models validate all inputs
- **Sensitive Data**: Metadata may contain PII, handle with care

### Compliance
- **GDPR**: Events tagged for data subject access requests
- **SOX**: Financial events flagged for audit trail
- **HIPAA**: Health-related events identified and protected
- **Retention**: Automatic policy enforcement (1-7 years)

### Rate Limiting (Future)
- **Per User**: 1000 requests/hour
- **Per IP**: 5000 requests/hour
- **Burst**: 100 requests/minute

---

## Performance Optimization

### Database Optimization
- **Indexes**: Strategic indexes on user_id, event_type, timestamp
- **Composite Indexes**: user_id + timestamp for activity queries
- **Partial Indexes**: Security events only for faster security queries
- **GIN Indexes**: compliance_flags and tags for JSONB queries
- **Pagination**: All list endpoints use LIMIT/OFFSET

### Query Optimization
- **Parameterized Queries**: SQL injection prevention + query plan caching
- **Query Limits**: Maximum 1000 records per query
- **Time Range Limits**: Maximum 365 days per query
- **Concurrent Queries**: asyncio.gather for statistics

### Event Processing
- **Non-Blocking**: Event processing doesn't block other operations
- **Idempotency Cache**: In-memory cache prevents duplicate processing
- **Cache Pruning**: Cache limited to 10,000 entries
- **Async Processing**: All I/O operations are async

### Caching Strategy (Future)
- **Statistics Cache**: 5-minute TTL for service stats
- **Compliance Config**: In-memory compliance standard configs
- **User Activity Summary**: 1-minute TTL for summaries

---

## Error Handling

### HTTP Status Codes

| Status | Condition | Example |
|--------|-----------|---------|
| 200 OK | Successful operation | Query returned results |
| 201 Created | New event created | Audit event logged |
| 400 Bad Request | Validation error | Invalid event_type |
| 401 Unauthorized | Missing/invalid token | No JWT provided |
| 404 Not Found | Resource not found | Event ID not found |
| 422 Validation Error | Field validation failed | Limit > 1000 |
| 500 Internal Error | Database error | PostgreSQL unavailable |
| 503 Service Unavailable | Service dependency down | NATS disconnected |

### Error Response Format
```json
{
  "detail": "Query limit cannot exceed 1000 records"
}
```

### Exception Handling
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )
```

### Custom Exceptions
```python
class AuditServiceError(Exception):
    """Base exception for audit service"""
    pass

class AuditNotFoundError(AuditServiceError):
    """Audit event not found"""
    pass

class AuditValidationError(AuditServiceError):
    """Validation error"""
    pass
```

---

## Deployment Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_PORT` | HTTP port | 8204 |
| `SERVICE_NAME` | Service identifier | audit_service |
| `LOG_LEVEL` | Logging level | INFO |
| `POSTGRES_HOST` | PostgreSQL gRPC host | isa-postgres-grpc |
| `POSTGRES_PORT` | PostgreSQL gRPC port | 50061 |
| `NATS_URL` | NATS connection URL | nats://isa-nats:4222 |
| `CONSUL_HOST` | Consul host | localhost |
| `CONSUL_PORT` | Consul port | 8500 |
| `CONSUL_ENABLED` | Enable Consul registration | true |

### Health Check

```json
GET /health
{
  "status": "healthy",
  "service": "audit_service",
  "port": 8204,
  "version": "1.0.0"
}

GET /health/detailed
{
  "service": "audit_service",
  "status": "operational",
  "port": 8204,
  "version": "1.0.0",
  "database_connected": true,
  "timestamp": "2025-12-22T12:00:00Z"
}
```

### Consul Registration

```json
{
  "service_name": "audit_service",
  "port": 8204,
  "tags": ["v1", "governance-microservice", "audit", "compliance"],
  "meta": {
    "version": "1.0.0",
    "capabilities": "event_logging,event_querying,user_activity_tracking,security_alerting,compliance_reporting",
    "route_count": "15",
    "base_path": "/api/v1/audit"
  },
  "health_check": {
    "type": "http",
    "path": "/health",
    "interval": "30s"
  }
}
```

### Docker Configuration

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8204

CMD ["python", "-m", "microservices.audit_service.main"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: audit-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: audit-service
  template:
    spec:
      containers:
      - name: audit-service
        image: isa/audit-service:latest
        ports:
        - containerPort: 8204
        env:
        - name: SERVICE_PORT
          value: "8204"
        - name: POSTGRES_HOST
          value: "isa-postgres-grpc"
        - name: NATS_URL
          value: "nats://isa-nats:4222"
        livenessProbe:
          httpGet:
            path: /health
            port: 8204
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/detailed
            port: 8204
          initialDelaySeconds: 5
          periodSeconds: 5
```

---

## Testing Strategy

### Contract Testing (Layer 4 & 5)
- **Data Contract**: Pydantic schema validation
- **Logic Contract**: Business rule documentation
- **TestDataFactory**: Zero hardcoded data generation

### Unit Testing
- **Pure Functions**: Event mapping, severity calculation
- **Model Validation**: Pydantic model tests
- **Factory Tests**: Service creation tests

### Component Testing
- **Service Layer**: Business logic with mocked repository
- **Event Handlers**: NATS event processing tests
- **Compliance Analysis**: Report generation tests

### Integration Testing
- **HTTP + Database**: Full request/response cycle
- **NATS Subscription**: Event capture tests
- **Compliance Reports**: End-to-end report generation

### API Testing
- **Endpoint Contracts**: All 15 endpoints tested
- **Error Handling**: Validation, not found, server errors
- **Pagination**: Page boundaries, empty results

### Smoke Testing
- **E2E Scripts**: Bash scripts for critical paths
- **Health Checks**: Service startup validation
- **Database Connectivity**: PostgreSQL availability

---

**Document Version**: 1.0
**Last Updated**: 2025-12-22
**Maintained By**: Security & Compliance Engineering Team
**Related Documents**:
- Domain Context: docs/domain/audit_service.md
- PRD: docs/prd/audit_service.md
- Data Contract: tests/contracts/audit_service/data_contract.py
- Logic Contract: tests/contracts/audit_service/logic_contract.md
- System Contract: tests/contracts/audit_service/system_contract.md
