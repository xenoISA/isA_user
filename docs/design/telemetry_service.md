# Telemetry Service - Design Document

## Design Overview

**Service Name**: telemetry_service
**Port**: 8218
**Version**: 1.0.0
**Protocol**: HTTP REST API + WebSocket
**Last Updated**: 2025-12-18

### Design Principles
1. **High Throughput First**: Optimize for sustained 10K+ data points/second
2. **Time-Series Native**: Data model optimized for time-based queries
3. **Real-Time Alerting**: Sub-minute alert evaluation and triggering
4. **Event-Driven Integration**: Loose coupling via NATS events
5. **Flexible Schema**: Support multiple data types without rigid schemas
6. **Graceful Degradation**: Alert failures don't block data ingestion

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         External Clients                             │
│   (IoT Devices, Gateways, Dashboards, Analytics, Admin Tools)       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP REST API / WebSocket
                               │ (via API Gateway - JWT/API Key validation)
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│                   Telemetry Service (Port 8218)                      │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │               FastAPI HTTP Layer (main.py)                   │   │
│  │  - Request validation (Pydantic models)                      │   │
│  │  - Response formatting                                       │   │
│  │  - Error handling & exception handlers                       │   │
│  │  - Health checks (/health, /health/detailed)                 │   │
│  │  - Lifecycle management (startup/shutdown)                   │   │
│  │  - WebSocket endpoint for real-time streaming               │   │
│  └────────────────────────────┬────────────────────────────────┘   │
│                               │                                      │
│  ┌────────────────────────────▼────────────────────────────────┐   │
│  │           Service Layer (telemetry_service.py)               │   │
│  │  - Data ingestion logic (single, batch, bulk)                │   │
│  │  - Metric definition management                              │   │
│  │  - Alert rule creation and evaluation                        │   │
│  │  - Real-time subscription management                         │   │
│  │  - Query execution and aggregation                           │   │
│  │  - Event publishing orchestration                            │   │
│  │  - Statistics aggregation                                    │   │
│  └────────────────────────────┬────────────────────────────────┘   │
│                               │                                      │
│  ┌────────────────────────────▼────────────────────────────────┐   │
│  │          Repository Layer (telemetry_repository.py)          │   │
│  │  - Time-series data CRUD operations                          │   │
│  │  - PostgreSQL gRPC communication                             │   │
│  │  - Query construction (parameterized)                        │   │
│  │  - Metric definition storage                                 │   │
│  │  - Alert rule and alert storage                              │   │
│  │  - Statistics queries                                        │   │
│  └────────────────────────────┬────────────────────────────────┘   │
│                               │                                      │
│  ┌────────────────────────────▼────────────────────────────────┐   │
│  │             Event Publishing (events/publishers.py)          │   │
│  │  - NATS event bus integration                                │   │
│  │  - Event model construction                                  │   │
│  │  - Async non-blocking publishing                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┼───────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ↓                       ↓                       ↓
┌──────────────────┐    ┌─────────────────┐     ┌────────────────┐
│   PostgreSQL     │    │      NATS       │     │     Consul     │
│     (gRPC)       │    │    (Events)     │     │   (Discovery)  │
│                  │    │                 │     │                │
│  Schema:         │    │  Subjects:      │     │  Service:      │
│  telemetry       │    │  telemetry.*    │     │  telemetry_    │
│                  │    │  alert.*        │     │  service       │
│  Tables:         │    │  metric.*       │     │                │
│  - telemetry_data│    │                 │     │  Health:       │
│  - metric_defs   │    │  Publishers:    │     │  /health       │
│  - alert_rules   │    │  - data.received│     │                │
│  - alerts        │    │  - triggered    │     │                │
│                  │    │  - resolved     │     │                │
│  Indexes:        │    │  - defined      │     │                │
│  - time          │    │  - rule.created │     │                │
│  - device_id     │    │                 │     │                │
│  - metric_name   │    │  Subscribers:   │     │                │
│                  │    │  - device.deleted│    │                │
│                  │    │  - user.deleted │     │                │
└──────────────────┘    └─────────────────┘     └────────────────┘
```

### Component Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                       Telemetry Service                             │
│                                                                     │
│  ┌─────────────────┐   ┌──────────────────┐   ┌─────────────────┐ │
│  │     Models      │──→│     Service      │──→│   Repository    │ │
│  │   (Pydantic)    │   │   (Business)     │   │     (Data)      │ │
│  │                 │   │                  │   │                 │ │
│  │ - DataType      │   │ - Telemetry      │   │ - Telemetry     │ │
│  │ - MetricType    │   │   Service        │   │   Repository    │ │
│  │ - AlertLevel    │   │                  │   │                 │ │
│  │ - AlertStatus   │   │                  │   │                 │ │
│  │ - Aggregation   │   │                  │   │                 │ │
│  │ - DataPoint     │   │                  │   │                 │ │
│  │ - MetricDef     │   │                  │   │                 │ │
│  │ - AlertRule     │   │                  │   │                 │ │
│  │ - Alert         │   │                  │   │                 │ │
│  └─────────────────┘   └──────────────────┘   └─────────────────┘ │
│          ↑                      ↑                      ↑          │
│          │                      │                      │          │
│  ┌───────┴──────────────────────┴──────────────────────┴────────┐ │
│  │                 FastAPI Main (main.py)                        │ │
│  │  - Dependency Injection (get_user_context)                    │ │
│  │  - Route Handlers (25+ endpoints)                             │ │
│  │  - WebSocket Handler (real-time streaming)                    │ │
│  │  - Exception Handlers (custom errors)                         │ │
│  └──────────────────────────┬───────────────────────────────────┘ │
│                             │                                      │
│  ┌──────────────────────────▼───────────────────────────────────┐ │
│  │                  Event Publishers                             │ │
│  │           (events/publishers.py, events/models.py)            │ │
│  │  - publish_telemetry_data_received                            │ │
│  │  - publish_metric_defined                                     │ │
│  │  - publish_alert_rule_created                                 │ │
│  │  - publish_alert_triggered                                    │ │
│  │  - publish_alert_resolved                                     │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                  Event Handlers                               │ │
│  │                (events/handlers.py)                           │ │
│  │  - handle_device_deleted                                      │ │
│  │  - handle_user_deleted                                        │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                    Factory Pattern                            │ │
│  │               (factory.py, protocols.py)                      │ │
│  │  - create_telemetry_service (production)                      │ │
│  │  - TelemetryRepositoryProtocol (interface)                    │ │
│  │  - EventBusProtocol (interface)                               │ │
│  │  - Enables dependency injection for tests                     │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Responsibilities**:
- HTTP request/response handling
- WebSocket connection management
- Request validation via Pydantic models
- Route definitions (25+ endpoints)
- Health checks
- Service initialization (lifespan management)
- Consul registration
- NATS event bus setup
- Exception handling

**Key Endpoints**:
```python
# Health Checks
GET /health                                              # Basic health check
GET /health/detailed                                     # Component status

# Data Ingestion
POST /api/v1/telemetry/devices/{device_id}/telemetry    # Single data point
POST /api/v1/telemetry/devices/{device_id}/telemetry/batch  # Batch ingestion
POST /api/v1/telemetry/bulk                              # Multi-device bulk

# Metric Management
POST /api/v1/telemetry/metrics                           # Create metric definition
GET  /api/v1/telemetry/metrics                           # List metric definitions
GET  /api/v1/telemetry/metrics/{metric_name}             # Get metric definition
DELETE /api/v1/telemetry/metrics/{metric_name}           # Delete metric definition

# Data Query
POST /api/v1/telemetry/query                             # Query telemetry data
GET  /api/v1/telemetry/devices/{device_id}/metrics/{metric_name}/latest  # Latest value
GET  /api/v1/telemetry/devices/{device_id}/metrics       # List device metrics
GET  /api/v1/telemetry/devices/{device_id}/metrics/{metric_name}/range  # Range query
GET  /api/v1/telemetry/aggregated                        # Aggregated data

# Alert Management
POST /api/v1/telemetry/alerts/rules                      # Create alert rule
GET  /api/v1/telemetry/alerts/rules                      # List alert rules
GET  /api/v1/telemetry/alerts/rules/{rule_id}            # Get alert rule
PUT  /api/v1/telemetry/alerts/rules/{rule_id}/enable     # Enable/disable rule
GET  /api/v1/telemetry/alerts                            # List alerts
PUT  /api/v1/telemetry/alerts/{alert_id}/acknowledge     # Acknowledge alert
PUT  /api/v1/telemetry/alerts/{alert_id}/resolve         # Resolve alert

# Real-Time Streaming
POST /api/v1/telemetry/subscribe                         # Create subscription
DELETE /api/v1/telemetry/subscribe/{subscription_id}     # Cancel subscription
WS   /ws/telemetry/{subscription_id}                     # WebSocket stream

# Statistics
GET  /api/v1/telemetry/devices/{device_id}/stats         # Device statistics
GET  /api/v1/telemetry/stats                             # Service statistics

# Export
GET  /api/v1/telemetry/export/csv                        # Export to CSV
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    event_bus = await get_event_bus("telemetry_service")
    await microservice.initialize(event_bus=event_bus)

    # Set up event subscriptions
    if event_bus:
        telemetry_repo = TelemetryRepository()
        event_handler = TelemetryEventHandler(telemetry_repo)

        # Subscribe to device.deleted events
        await event_bus.subscribe_to_events(
            pattern="device_service.device.deleted",
            handler=event_handler.handle_event,
            durable="telemetry_device_deleted"
        )

        # Subscribe to user.deleted events
        await event_bus.subscribe_to_events(
            pattern="account_service.user.deleted",
            handler=event_handler.handle_event,
            durable="telemetry_user_deleted"
        )

    # Consul registration
    if config.consul_enabled:
        consul_registry.register()

    yield  # Service runs

    # Shutdown
    await microservice.shutdown()
    if event_bus:
        await event_bus.close()
```

### 2. Service Layer (telemetry_service.py)

**Class**: `TelemetryService`

**Responsibilities**:
- Data ingestion orchestration
- Metric definition management
- Alert rule evaluation
- Real-time subscription management
- Query execution and aggregation
- Event publishing coordination
- Statistics aggregation

**Key Methods**:
```python
class TelemetryService:
    def __init__(self, event_bus=None, config=None):
        self.repository = TelemetryRepository(config=config)
        self.event_bus = event_bus
        self.real_time_subscribers = {}  # In-memory subscriptions
        self.max_batch_size = 1000
        self.max_query_points = 10000
        self.default_retention_days = 90

    # Data Ingestion
    async def ingest_telemetry_data(
        self,
        device_id: str,
        data_points: List[TelemetryDataPoint]
    ) -> Dict[str, Any]:
        """
        Ingest telemetry data points for a device.
        1. Store data via repository
        2. Validate each point against metric definition
        3. Check alert rules
        4. Notify real-time subscribers
        5. Publish telemetry.data.received event
        """
        result = await self.repository.ingest_data_points(device_id, data_points)

        for data_point in data_points:
            await self._validate_data_point(device_id, data_point)
            await self._check_alert_rules(device_id, data_point)
            await self._notify_real_time_subscribers(device_id, data_point)

        # Publish event
        if self.event_bus and result.get('ingested_count', 0) > 0:
            await publish_telemetry_data_received(
                event_bus=self.event_bus,
                device_id=device_id,
                metrics_count=len(set(dp.metric_name for dp in data_points)),
                points_count=result['ingested_count']
            )

        return result

    # Metric Definition
    async def create_metric_definition(
        self,
        user_id: str,
        metric_data: Dict[str, Any]
    ) -> Optional[MetricDefinitionResponse]:
        """Create a new metric definition with validation"""
        metric_def_data = {
            "name": metric_data["name"],
            "description": metric_data.get("description"),
            "data_type": metric_data["data_type"],
            "metric_type": metric_data.get("metric_type", MetricType.GAUGE.value),
            "unit": metric_data.get("unit"),
            "min_value": metric_data.get("min_value"),
            "max_value": metric_data.get("max_value"),
            "retention_days": metric_data.get("retention_days", self.default_retention_days),
            "aggregation_interval": metric_data.get("aggregation_interval", 60),
            "tags": metric_data.get("tags", []),
            "metadata": metric_data.get("metadata", {}),
            "created_by": user_id
        }

        result = await self.repository.create_metric_definition(metric_def_data)

        if result and self.event_bus:
            await publish_metric_defined(
                event_bus=self.event_bus,
                metric_id=result["metric_id"],
                name=result["name"],
                data_type=result["data_type"],
                metric_type=result["metric_type"],
                unit=result.get("unit"),
                created_by=user_id
            )

        return MetricDefinitionResponse(**result) if result else None

    # Alert Rule
    async def create_alert_rule(
        self,
        user_id: str,
        rule_data: Dict[str, Any]
    ) -> Optional[AlertRuleResponse]:
        """Create an alert rule for metric monitoring"""
        alert_rule_data = {
            "name": rule_data["name"],
            "description": rule_data.get("description"),
            "metric_name": rule_data["metric_name"],
            "condition": rule_data["condition"],
            "threshold_value": str(rule_data["threshold_value"]),
            "evaluation_window": rule_data.get("evaluation_window", 300),
            "trigger_count": rule_data.get("trigger_count", 1),
            "level": rule_data.get("level", AlertLevel.WARNING.value),
            "device_ids": rule_data.get("device_ids", []),
            "device_groups": rule_data.get("device_groups", []),
            "notification_channels": rule_data.get("notification_channels", []),
            "cooldown_minutes": rule_data.get("cooldown_minutes", 15),
            "auto_resolve": rule_data.get("auto_resolve", True),
            "auto_resolve_timeout": rule_data.get("auto_resolve_timeout", 3600),
            "enabled": rule_data.get("enabled", True),
            "created_by": user_id
        }

        result = await self.repository.create_alert_rule(alert_rule_data)

        if result and self.event_bus:
            await publish_alert_rule_created(
                event_bus=self.event_bus,
                rule_id=result["rule_id"],
                name=result["name"],
                metric_name=result["metric_name"],
                condition=result["condition"],
                threshold_value=result["threshold_value"],
                level=result["level"],
                enabled=result["enabled"],
                created_by=user_id
            )

        return AlertRuleResponse(**result) if result else None

    # Query
    async def query_telemetry_data(
        self,
        query_params: Dict[str, Any]
    ) -> Optional[TelemetryDataResponse]:
        """Query telemetry data with filters and aggregation"""
        device_ids = query_params.get("devices") or query_params.get("device_ids", [])
        metric_names = query_params.get("metrics") or query_params.get("metric_names", [])
        start_time = query_params["start_time"]
        end_time = query_params["end_time"]
        aggregation = query_params.get("aggregation")
        interval = query_params.get("interval")

        all_data_points = []

        for device_id in device_ids:
            raw_data = await self.repository.query_telemetry_data(
                device_id=device_id,
                metric_names=metric_names,
                start_time=start_time,
                end_time=end_time,
                limit=query_params.get("limit", 1000)
            )
            # Convert to TelemetryDataPoint objects
            all_data_points.extend(self._convert_raw_data(raw_data))

        # Apply aggregation if requested
        if aggregation and interval:
            all_data_points = await self._aggregate_data_points(
                all_data_points, aggregation, interval
            )

        return TelemetryDataResponse(
            device_id=device_ids[0] if len(device_ids) == 1 else "multiple",
            metric_name=metric_names[0] if len(metric_names) == 1 else "multiple",
            data_points=all_data_points,
            count=len(all_data_points),
            aggregation=aggregation,
            interval=interval,
            start_time=start_time,
            end_time=end_time
        )

    # Real-Time
    async def subscribe_real_time(
        self,
        subscription_data: Dict[str, Any]
    ) -> str:
        """Create a real-time data subscription"""
        subscription_id = secrets.token_hex(16)
        self.real_time_subscribers[subscription_id] = {
            "device_ids": subscription_data.get("device_ids", []),
            "metric_names": subscription_data.get("metric_names", []),
            "tags": subscription_data.get("tags", {}),
            "filter_condition": subscription_data.get("filter_condition"),
            "max_frequency": subscription_data.get("max_frequency", 1000),
            "created_at": datetime.now(timezone.utc),
            "last_sent": datetime.now(timezone.utc)
        }
        return subscription_id

    # Alert Resolution
    async def resolve_alert(
        self,
        alert_id: str,
        resolved_by: str,
        resolution_note: Optional[str] = None
    ) -> bool:
        """Resolve an alert and publish event"""
        alerts = await self.repository.get_alerts()
        alert_data = next((a for a in alerts if a.get("alert_id") == alert_id), None)

        if not alert_data:
            return False

        update_data = {
            "status": AlertStatus.RESOLVED.value,
            "resolved_at": datetime.now(timezone.utc),
            "resolved_by": resolved_by
        }
        if resolution_note:
            update_data["resolution_note"] = resolution_note

        success = await self.repository.update_alert(alert_id, update_data)

        if success and self.event_bus:
            await publish_alert_resolved(
                event_bus=self.event_bus,
                alert_id=alert_id,
                rule_id=alert_data.get("rule_id"),
                rule_name=alert_data.get("rule_name"),
                device_id=alert_data.get("device_id"),
                metric_name=alert_data.get("metric_name"),
                level=alert_data.get("level"),
                resolved_by=resolved_by,
                resolution_note=resolution_note
            )

        return success

    # Private: Alert Checking
    async def _check_alert_rules(
        self,
        device_id: str,
        data_point: TelemetryDataPoint
    ):
        """Check all enabled alert rules for this metric"""
        alert_rules = await self.repository.get_alert_rules(
            metric_name=data_point.metric_name,
            enabled_only=True
        )

        for rule_data in alert_rules:
            # Check device filter
            device_ids = rule_data.get("device_ids", [])
            if device_ids and device_id not in device_ids:
                continue

            # Evaluate condition
            if await self._evaluate_alert_condition(
                rule_data["condition"],
                rule_data["threshold_value"],
                data_point
            ):
                await self._trigger_alert(rule_data, device_id, data_point)

    async def _evaluate_alert_condition(
        self,
        condition: str,
        threshold_value: str,
        data_point: TelemetryDataPoint
    ) -> bool:
        """Evaluate alert condition against data point value"""
        try:
            value = data_point.value
            threshold = float(threshold_value)

            if condition.startswith(">"):
                return isinstance(value, (int, float)) and value > threshold
            elif condition.startswith("<"):
                return isinstance(value, (int, float)) and value < threshold
            elif condition.startswith("=="):
                return value == threshold
            elif condition.startswith("!="):
                return value != threshold

            return False
        except Exception:
            return False

    async def _trigger_alert(
        self,
        rule_data: Dict[str, Any],
        device_id: str,
        data_point: TelemetryDataPoint
    ):
        """Create alert and publish event"""
        alert_data = {
            "rule_id": rule_data["rule_id"],
            "rule_name": rule_data["name"],
            "device_id": device_id,
            "metric_name": rule_data["metric_name"],
            "level": rule_data["level"],
            "status": AlertStatus.ACTIVE.value,
            "message": f"Alert triggered: {rule_data['name']}",
            "current_value": str(data_point.value),
            "threshold_value": rule_data["threshold_value"],
            "triggered_at": datetime.now(timezone.utc),
            "affected_devices_count": 1,
            "tags": rule_data.get("tags", []),
            "metadata": {"trigger_value": data_point.value}
        }

        alert_result = await self.repository.create_alert(alert_data)

        if alert_result:
            await self.repository.update_alert_rule_stats(rule_data["rule_id"])

            if self.event_bus:
                await publish_alert_triggered(
                    event_bus=self.event_bus,
                    alert_id=alert_result.get("alert_id"),
                    rule_id=rule_data["rule_id"],
                    rule_name=rule_data["name"],
                    device_id=device_id,
                    metric_name=rule_data["metric_name"],
                    level=rule_data["level"],
                    current_value=str(data_point.value),
                    threshold_value=rule_data["threshold_value"]
                )
```

### 3. Repository Layer (telemetry_repository.py)

**Class**: `TelemetryRepository`

**Responsibilities**:
- Time-series data CRUD operations
- PostgreSQL gRPC communication
- Query construction (parameterized)
- Metric definition storage
- Alert rule and alert management
- Statistics queries

**Key Methods**:
```python
class TelemetryRepository:
    def __init__(self, config: Optional[ConfigManager] = None):
        # Discover PostgreSQL gRPC service
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061
        )
        self.db = AsyncPostgresClient(host=host, port=port, user_id='telemetry_service')
        self.schema = "telemetry"
        self.data_table = "telemetry_data"
        self.metric_definitions_table = "metric_definitions"
        self.alert_rules_table = "alert_rules"
        self.alerts_table = "alerts"

    # Data Ingestion
    async def ingest_data_points(
        self,
        device_id: str,
        data_points: List[TelemetryDataPoint]
    ) -> Dict[str, Any]:
        """Ingest multiple telemetry data points"""
        ingested_count = 0
        failed_count = 0

        for data_point in data_points:
            success = await self.ingest_single_point(device_id, data_point)
            if success:
                ingested_count += 1
            else:
                failed_count += 1

        return {
            "success": True,
            "ingested_count": ingested_count,
            "failed_count": failed_count
        }

    async def ingest_single_point(
        self,
        device_id: str,
        data_point: TelemetryDataPoint
    ) -> bool:
        """Ingest a single telemetry data point with type routing"""
        # Route value to appropriate column based on type
        value_numeric = None
        value_string = None
        value_boolean = None
        value_json = None

        if isinstance(data_point.value, (int, float)):
            value_numeric = float(data_point.value)
        elif isinstance(data_point.value, str):
            value_string = data_point.value
        elif isinstance(data_point.value, bool):
            value_boolean = data_point.value
        elif isinstance(data_point.value, dict):
            value_json = data_point.value

        query = f'''
            INSERT INTO {self.schema}.{self.data_table} (
                time, device_id, metric_name, value_numeric, value_string,
                value_boolean, value_json, unit, tags, metadata, quality
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (time, device_id, metric_name) DO UPDATE
            SET value_numeric = EXCLUDED.value_numeric,
                value_string = EXCLUDED.value_string,
                value_boolean = EXCLUDED.value_boolean,
                value_json = EXCLUDED.value_json
        '''

        params = [
            data_point.timestamp, device_id, data_point.metric_name,
            value_numeric, value_string, value_boolean, value_json,
            data_point.unit, data_point.tags or {}, data_point.metadata or {}, 100
        ]

        async with self.db:
            count = await self.db.execute(query, params, schema=self.schema)
        return count is not None and count >= 0

    # Query
    async def query_telemetry_data(
        self,
        device_id: Optional[str] = None,
        metric_names: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query telemetry data with filters"""
        conditions = []
        params = []
        param_count = 0

        if device_id:
            param_count += 1
            conditions.append(f"device_id = ${param_count}")
            params.append(device_id)

        if metric_names:
            param_count += 1
            conditions.append(f"metric_name = ANY(${param_count})")
            params.append(metric_names)

        if start_time:
            param_count += 1
            conditions.append(f"time >= ${param_count}")
            params.append(start_time)

        if end_time:
            param_count += 1
            conditions.append(f"time <= ${param_count}")
            params.append(end_time)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        query = f'''
            SELECT * FROM {self.schema}.{self.data_table}
            {where_clause}
            ORDER BY time DESC
            LIMIT ${len(params)}
        '''

        async with self.db:
            results = await self.db.query(query, params, schema=self.schema)

        return self._convert_results(results) if results else []

    # Statistics
    async def get_device_stats(self, device_id: str) -> Dict[str, Any]:
        """Get statistics for a specific device"""
        count_query = f'''
            SELECT COUNT(*) as total_points
            FROM {self.schema}.{self.data_table}
            WHERE device_id = $1
        '''

        metrics_query = f'''
            SELECT DISTINCT metric_name
            FROM {self.schema}.{self.data_table}
            WHERE device_id = $1
        '''

        latest_query = f'''
            SELECT time as last_data_received
            FROM {self.schema}.{self.data_table}
            WHERE device_id = $1
            ORDER BY time DESC LIMIT 1
        '''

        async with self.db:
            count_results = await self.db.query(count_query, [device_id], schema=self.schema)
            metrics_results = await self.db.query(metrics_query, [device_id], schema=self.schema)
            latest_results = await self.db.query(latest_query, [device_id], schema=self.schema)

        return {
            "device_id": device_id,
            "total_points": count_results[0]['total_points'] if count_results else 0,
            "active_metrics": len(metrics_results) if metrics_results else 0,
            "last_data_received": latest_results[0]['last_data_received'] if latest_results else None,
            "metrics": [m["metric_name"] for m in metrics_results] if metrics_results else []
        }

    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global telemetry statistics"""
        devices_query = f'SELECT COUNT(DISTINCT device_id) as total_devices FROM {self.schema}.{self.data_table}'
        points_query = f'SELECT COUNT(*) as total_points FROM {self.schema}.{self.data_table}'
        metrics_query = f'SELECT COUNT(DISTINCT metric_name) as total_metrics FROM {self.schema}.{self.data_table}'
        alerts_query = f'SELECT COUNT(*) as active_alerts FROM {self.schema}.{self.alerts_table} WHERE status = $1'

        async with self.db:
            devices_results = await self.db.query(devices_query, [], schema=self.schema)
            points_results = await self.db.query(points_query, [], schema=self.schema)
            metrics_results = await self.db.query(metrics_query, [], schema=self.schema)
            alerts_results = await self.db.query(alerts_query, ["active"], schema=self.schema)

        return {
            "total_devices": devices_results[0]['total_devices'] if devices_results else 0,
            "total_points": points_results[0]['total_points'] if points_results else 0,
            "total_metrics": metrics_results[0]['total_metrics'] if metrics_results else 0,
            "active_alerts": alerts_results[0]['active_alerts'] if alerts_results else 0
        }
```

---

## Database Schema Design

### PostgreSQL Schema: `telemetry`

#### Table: telemetry.telemetry_data (Time-Series)

```sql
-- Create telemetry schema
CREATE SCHEMA IF NOT EXISTS telemetry;

-- Main telemetry data table (time-series optimized)
CREATE TABLE IF NOT EXISTS telemetry.telemetry_data (
    -- Composite primary key for time-series
    time TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(100) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,

    -- Multi-type value storage
    value_numeric DOUBLE PRECISION,
    value_string VARCHAR(1000),
    value_boolean BOOLEAN,
    value_json JSONB,

    -- Metadata
    unit VARCHAR(20),
    tags JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    quality INTEGER DEFAULT 100,

    -- Composite primary key
    PRIMARY KEY (time, device_id, metric_name)
);

-- Time-based partitioning hint (TimescaleDB compatible)
-- For high-volume: SELECT create_hypertable('telemetry.telemetry_data', 'time');

-- Indexes for query performance
CREATE INDEX idx_telemetry_device_time ON telemetry.telemetry_data(device_id, time DESC);
CREATE INDEX idx_telemetry_metric_time ON telemetry.telemetry_data(metric_name, time DESC);
CREATE INDEX idx_telemetry_device_metric ON telemetry.telemetry_data(device_id, metric_name, time DESC);
CREATE INDEX idx_telemetry_tags ON telemetry.telemetry_data USING GIN(tags);

-- Comments
COMMENT ON TABLE telemetry.telemetry_data IS 'Time-series telemetry data from IoT devices';
COMMENT ON COLUMN telemetry.telemetry_data.time IS 'Timestamp of measurement';
COMMENT ON COLUMN telemetry.telemetry_data.device_id IS 'Device identifier';
COMMENT ON COLUMN telemetry.telemetry_data.metric_name IS 'Metric type (e.g., temperature, cpu_usage)';
COMMENT ON COLUMN telemetry.telemetry_data.quality IS 'Data quality indicator (0-100)';
```

#### Table: telemetry.metric_definitions

```sql
CREATE TABLE IF NOT EXISTS telemetry.metric_definitions (
    metric_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(500),
    data_type VARCHAR(20) NOT NULL,  -- numeric, string, boolean, json, binary, geolocation, timestamp
    metric_type VARCHAR(20) NOT NULL DEFAULT 'gauge',  -- gauge, counter, histogram, summary
    unit VARCHAR(20),
    min_value DOUBLE PRECISION,
    max_value DOUBLE PRECISION,
    retention_days INTEGER DEFAULT 90,
    aggregation_interval INTEGER DEFAULT 60,  -- seconds
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT metric_data_type_check CHECK (
        data_type IN ('numeric', 'string', 'boolean', 'json', 'binary', 'geolocation', 'timestamp')
    ),
    CONSTRAINT metric_type_check CHECK (
        metric_type IN ('gauge', 'counter', 'histogram', 'summary')
    )
);

CREATE INDEX idx_metric_defs_data_type ON telemetry.metric_definitions(data_type);
CREATE INDEX idx_metric_defs_metric_type ON telemetry.metric_definitions(metric_type);
```

#### Table: telemetry.alert_rules

```sql
CREATE TABLE IF NOT EXISTS telemetry.alert_rules (
    rule_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description VARCHAR(1000),
    metric_name VARCHAR(100) NOT NULL,
    condition VARCHAR(10) NOT NULL,  -- >, <, >=, <=, ==, !=
    threshold_value VARCHAR(100) NOT NULL,
    evaluation_window INTEGER DEFAULT 300,  -- seconds
    trigger_count INTEGER DEFAULT 1,
    level VARCHAR(20) NOT NULL DEFAULT 'warning',  -- info, warning, error, critical, emergency
    device_ids TEXT[] DEFAULT '{}',
    device_groups TEXT[] DEFAULT '{}',
    device_filters JSONB DEFAULT '{}',
    notification_channels TEXT[] DEFAULT '{}',
    cooldown_minutes INTEGER DEFAULT 15,
    auto_resolve BOOLEAN DEFAULT TRUE,
    auto_resolve_timeout INTEGER DEFAULT 3600,  -- seconds
    enabled BOOLEAN DEFAULT TRUE,
    tags TEXT[] DEFAULT '{}',
    total_triggers INTEGER DEFAULT 0,
    last_triggered TIMESTAMPTZ,
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT alert_level_check CHECK (
        level IN ('info', 'warning', 'error', 'critical', 'emergency')
    )
);

CREATE INDEX idx_alert_rules_metric ON telemetry.alert_rules(metric_name);
CREATE INDEX idx_alert_rules_enabled ON telemetry.alert_rules(enabled) WHERE enabled = TRUE;
CREATE INDEX idx_alert_rules_level ON telemetry.alert_rules(level);
```

#### Table: telemetry.alerts

```sql
CREATE TABLE IF NOT EXISTS telemetry.alerts (
    alert_id VARCHAR(50) PRIMARY KEY,
    rule_id VARCHAR(50) NOT NULL REFERENCES telemetry.alert_rules(rule_id),
    rule_name VARCHAR(200) NOT NULL,
    device_id VARCHAR(100) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    level VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, acknowledged, resolved, suppressed
    message VARCHAR(1000),
    current_value VARCHAR(100),
    threshold_value VARCHAR(100),
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    auto_resolve_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(100),
    resolved_by VARCHAR(100),
    resolution_note VARCHAR(1000),
    affected_devices_count INTEGER DEFAULT 1,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',

    CONSTRAINT alert_status_check CHECK (
        status IN ('active', 'acknowledged', 'resolved', 'suppressed')
    )
);

CREATE INDEX idx_alerts_status ON telemetry.alerts(status);
CREATE INDEX idx_alerts_level ON telemetry.alerts(level);
CREATE INDEX idx_alerts_device ON telemetry.alerts(device_id);
CREATE INDEX idx_alerts_triggered ON telemetry.alerts(triggered_at DESC);
CREATE INDEX idx_alerts_rule ON telemetry.alerts(rule_id);
```

### Index Strategy

| Table | Index | Type | Purpose |
|-------|-------|------|---------|
| telemetry_data | (time, device_id, metric_name) | PRIMARY | Unique constraint, upsert |
| telemetry_data | (device_id, time DESC) | B-tree | Device-specific queries |
| telemetry_data | (metric_name, time DESC) | B-tree | Metric-specific queries |
| telemetry_data | (tags) | GIN | Tag-based filtering |
| metric_definitions | (name) | UNIQUE | Name lookup |
| alert_rules | (metric_name) | B-tree | Rule matching during ingestion |
| alert_rules | (enabled) PARTIAL | B-tree | Only enabled rules |
| alerts | (status) | B-tree | Active alerts query |
| alerts | (triggered_at DESC) | B-tree | Recent alerts |

---

## Event-Driven Architecture

### Event Publishing (events/publishers.py)

**NATS Subjects**:
```
telemetry.data.received     # Data points ingested
metric.defined              # New metric definition created
alert.rule.created          # New alert rule created
alert.triggered             # Alert condition met
alert.resolved              # Alert resolved
```

### Event Models (events/models.py)

```python
class TelemetryDataReceivedEvent(BaseModel):
    """Event: telemetry.data.received"""
    device_id: str
    metrics_count: int
    points_count: int
    timestamp: str  # ISO8601

class MetricDefinedEvent(BaseModel):
    """Event: metric.defined"""
    metric_id: str
    name: str
    data_type: str
    metric_type: str
    unit: Optional[str]
    created_by: str
    timestamp: str

class AlertRuleCreatedEvent(BaseModel):
    """Event: alert.rule.created"""
    rule_id: str
    name: str
    metric_name: str
    condition: str
    threshold_value: str
    level: str
    enabled: bool
    created_by: str
    timestamp: str

class AlertTriggeredEvent(BaseModel):
    """Event: alert.triggered"""
    alert_id: str
    rule_id: str
    rule_name: str
    device_id: str
    metric_name: str
    level: str
    current_value: str
    threshold_value: str
    timestamp: str

class AlertResolvedEvent(BaseModel):
    """Event: alert.resolved"""
    alert_id: str
    rule_id: str
    rule_name: str
    device_id: str
    metric_name: str
    level: str
    resolved_by: str
    resolution_note: Optional[str]
    timestamp: str
```

### Event Handlers (events/handlers.py)

```python
class TelemetryEventHandler:
    def __init__(self, telemetry_repository):
        self.telemetry_repo = telemetry_repository

    async def handle_device_deleted(self, event_data: Dict[str, Any]) -> bool:
        """Handle device.deleted - disable alert rules for device"""
        device_id = event_data.get('device_id')
        if not device_id:
            return False

        disabled_count = await self.telemetry_repo.disable_device_alert_rules(device_id)
        logger.info(f"Disabled {disabled_count} alert rules for deleted device {device_id}")
        return True

    async def handle_user_deleted(self, event_data: Dict[str, Any]) -> bool:
        """Handle user.deleted - anonymize user references"""
        user_id = event_data.get('user_id')
        if not user_id:
            return False

        # Disable alert rules created by user
        # Anonymize user references in metadata
        return True
```

### Event Flow Diagram

```
Device sends telemetry data
    │
    ↓
POST /api/v1/telemetry/devices/{device_id}/telemetry
    │
    ↓
┌───────────────────────────────────┐
│      TelemetryService             │
│                                   │
│  1. Store data                    │───→ PostgreSQL (telemetry.telemetry_data)
│  2. Validate against metric def   │
│  3. Check alert rules             │
│     └── Condition met?            │
│          └── Create alert ────────┼───→ PostgreSQL (telemetry.alerts)
│              └── Publish event ───┼───→ NATS: alert.triggered
│  4. Notify subscribers            │───→ WebSocket clients
│  5. Publish data event            │───→ NATS: telemetry.data.received
└───────────────────────────────────┘
    │
    ↓
┌────────────────────────────────┐
│       Event Subscribers        │
│ - Notification Service         │ ← alert.triggered
│ - Analytics Service            │ ← telemetry.data.received
│ - Device Service               │ ← telemetry.data.received
│ - Billing Service              │ ← telemetry.data.received
└────────────────────────────────┘
```

---

## Data Flow Diagrams

### 1. Telemetry Data Ingestion Flow

```
IoT Device sends POST /api/v1/telemetry/devices/dev_001/telemetry
    │  {timestamp, metric_name: "temperature", value: 85.5}
    ↓
┌─────────────────────────────────────────┐
│     TelemetryService.ingest_telemetry   │
│                                         │
│  Step 1: Store data                     │
│    repository.ingest_single_point() ────┼───→ PostgreSQL: INSERT INTO telemetry_data
│                                    ←────┤         ON CONFLICT DO UPDATE
│    Success                              │
│                                         │
│  Step 2: Validate (optional)            │
│    repository.get_metric_definition() ──┼───→ PostgreSQL: SELECT FROM metric_definitions
│                                    ←────┤
│    Check min_value, max_value           │
│                                         │
│  Step 3: Check alert rules              │
│    repository.get_alert_rules() ────────┼───→ PostgreSQL: SELECT FROM alert_rules
│                                    ←────┤         WHERE metric_name = 'temperature'
│    For each enabled rule:               │
│      evaluate_condition("> 80", 85.5)   │
│      └── TRUE → trigger_alert()         │
│                                         │
│  Step 4: Trigger alert (if condition met)│
│    repository.create_alert() ───────────┼───→ PostgreSQL: INSERT INTO alerts
│    publish_alert_triggered() ───────────┼───→ NATS: alert.triggered
│                                         │
│  Step 5: Notify subscribers             │
│    For each matching subscription:      │
│      send via WebSocket                 │
│                                         │
│  Step 6: Publish event                  │
│    publish_telemetry_data_received() ───┼───→ NATS: telemetry.data.received
│                                         │
└─────────────────────────────────────────┘
    │
    ↓
Return {success: true, ingested_count: 1}
```

### 2. Time-Series Query Flow

```
Dashboard requests POST /api/v1/telemetry/query
    │  {devices: ["dev_001"], metrics: ["temperature"],
    │   start_time: "2025-12-17T00:00:00Z", end_time: "2025-12-18T00:00:00Z",
    │   aggregation: "avg", interval: 3600}
    ↓
┌─────────────────────────────────────────┐
│     TelemetryService.query_telemetry    │
│                                         │
│  Step 1: Query raw data                 │
│    repository.query_telemetry_data() ───┼───→ PostgreSQL:
│      device_id = 'dev_001'              │       SELECT * FROM telemetry_data
│      metric_names = ['temperature']     │       WHERE device_id = $1
│      start_time, end_time               │         AND metric_name = ANY($2)
│                                    ←────┤         AND time >= $3 AND time <= $4
│    Result: 1440 raw data points         │       ORDER BY time DESC LIMIT 10000
│                                         │
│  Step 2: Aggregate by interval          │
│    _aggregate_data_points()             │
│    Group by 3600-second buckets         │
│    Apply AVG aggregation                │
│                                    ←────┤
│    Result: 24 aggregated points         │
│                                         │
│  Step 3: Build response                 │
│    TelemetryDataResponse(               │
│      data_points: [...],                │
│      count: 24,                         │
│      aggregation: "avg",                │
│      interval: 3600                     │
│    )                                    │
└─────────────────────────────────────────┘
    │
    ↓
Return TelemetryDataResponse
```

### 3. Alert Rule Evaluation Flow

```
Data point arrives: {metric_name: "cpu_percent", value: 95}
    │
    ↓
┌─────────────────────────────────────────┐
│     _check_alert_rules()                │
│                                         │
│  Step 1: Get matching rules             │
│    repository.get_alert_rules(          │
│      metric_name="cpu_percent",         │
│      enabled_only=True                  │───→ PostgreSQL: SELECT FROM alert_rules
│    )                                ←───┤
│    Result: [                            │
│      {rule_id: "r1", condition: ">",    │
│       threshold: 90, level: "warning"}  │
│    ]                                    │
│                                         │
│  Step 2: Evaluate each rule             │
│    _evaluate_alert_condition(           │
│      condition=">",                     │
│      threshold="90",                    │
│      value=95                           │
│    )                                    │
│    Result: TRUE (95 > 90)               │
│                                         │
│  Step 3: Check device filter            │
│    device_ids=[] (empty = all devices)  │
│    Result: PASS                         │
│                                         │
│  Step 4: Trigger alert                  │
│    _trigger_alert(rule, device, point)  │
│                                         │
│    4a. Create alert record              │───→ PostgreSQL: INSERT INTO alerts
│    4b. Update rule statistics           │───→ PostgreSQL: UPDATE alert_rules
│    4c. Publish event                    │───→ NATS: alert.triggered
│                                         │
└─────────────────────────────────────────┘
    │
    ↓
Alert created and event published
```

### 4. Real-Time Subscription Flow

```
Dashboard creates subscription
POST /api/v1/telemetry/subscribe
{device_ids: ["dev_001"], metric_names: ["temperature"], max_frequency: 1000}
    │
    ↓
┌─────────────────────────────────────────┐
│     subscribe_real_time()               │
│                                         │
│  Step 1: Generate subscription ID       │
│    subscription_id = secrets.token_hex()│
│                                         │
│  Step 2: Store in memory                │
│    real_time_subscribers[sub_id] = {    │
│      device_ids: ["dev_001"],           │
│      metric_names: ["temperature"],     │
│      max_frequency: 1000,               │
│      last_sent: now()                   │
│    }                                    │
│                                         │
│  Step 3: Return WebSocket URL           │
│    {subscription_id, websocket_url}     │
└─────────────────────────────────────────┘
    │
    ↓
Dashboard connects: WS /ws/telemetry/{subscription_id}
    │
    ↓
┌─────────────────────────────────────────┐
│     WebSocket Connection Active         │
│                                         │
│  When data ingested for dev_001:        │
│    _notify_real_time_subscribers()      │
│                                         │
│    1. Check device_ids filter           │
│       "dev_001" in ["dev_001"] ✓        │
│                                         │
│    2. Check metric_names filter         │
│       "temperature" in ["temperature"] ✓ │
│                                         │
│    3. Check rate limit                  │
│       now - last_sent >= 1000ms ✓       │
│                                         │
│    4. Push data via WebSocket           │───→ Dashboard
│       {subscription_id, device_id,      │
│        data_points: [...], timestamp}   │
│                                         │
│    5. Update last_sent                  │
│                                         │
└─────────────────────────────────────────┘
```

---

## Technology Stack

### Core Technologies
- **Python 3.11+**: Programming language
- **FastAPI 0.104+**: Web framework + WebSocket
- **Pydantic 2.0+**: Data validation
- **asyncio**: Async/await concurrency
- **uvicorn**: ASGI server
- **websockets**: WebSocket support

### Data Storage
- **PostgreSQL 15+**: Primary database
- **AsyncPostgresClient** (gRPC): Database communication
- **Schema**: `telemetry`
- **Tables**: `telemetry_data`, `metric_definitions`, `alert_rules`, `alerts`

### Event-Driven
- **NATS 2.9+**: Event bus
- **Subjects**: `telemetry.*`, `alert.*`, `metric.*`
- **Publishers**: Telemetry Service
- **Subscribers**: Notification, Analytics, Device, Billing services

### Service Discovery
- **Consul 1.15+**: Service registry
- **Health Checks**: HTTP `/health`
- **Metadata**: Route registration

### Dependency Injection
- **Protocols (typing.Protocol)**: Interface definitions
- **Factory Pattern**: Production vs test instances
- **ConfigManager**: Environment-based configuration

### Observability
- **Structured Logging**: JSON format
- **core.logger**: Service logger
- **Health Endpoints**: `/health`, `/health/detailed`

---

## Security Considerations

### Authentication
- **JWT Token**: Via Authorization header
- **API Key**: Via X-Api-Key header
- **Internal Calls**: X-Internal-Call: true (service-to-service)
- **Validation**: Auth service verification

### Authorization
- **User Context**: Extracted from JWT/API key
- **Resource Access**: User-scoped queries (future)
- **Admin Operations**: Privileged endpoints (future)

### Input Validation
- **Pydantic Models**: All requests validated
- **SQL Injection**: Parameterized queries via gRPC
- **Data Type Validation**: Metric value type checking
- **Range Validation**: Min/max bounds from metric definitions

### Data Protection
- **Soft Delete**: Alert data preserved for audit
- **Data Retention**: Configurable per metric
- **Encryption in Transit**: TLS for all communication

### Rate Limiting (Future)
- **Per Device**: 100 data points/second
- **Per User**: 1000 API calls/hour
- **Burst**: 50 requests/second

---

## Performance Optimization

### Data Ingestion Optimization
- **Batch Processing**: Up to 1000 points per batch
- **Upsert Strategy**: ON CONFLICT DO UPDATE for idempotency
- **Async Operations**: Non-blocking event publishing
- **Connection Pooling**: gRPC client pools

### Query Optimization
- **Indexes**: Strategic indexes on (device_id, time), (metric_name, time)
- **Time-Range Filtering**: Indexed time column
- **Server-Side Aggregation**: Reduce data transfer
- **Result Limits**: Max 10,000 points per query

### Alert Evaluation Optimization
- **Partial Index**: Only enabled rules indexed
- **In-Memory Caching**: Recently triggered alerts (cooldown)
- **Batch Rule Fetch**: Load rules once per ingestion batch

### Real-Time Streaming Optimization
- **Rate Limiting**: max_frequency prevents client overload
- **In-Memory Subscriptions**: Fast lookup for matching
- **WebSocket Multiplexing**: Single connection per client

---

## Error Handling

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: New resource created
- `400 Bad Request`: Validation error
- `401 Unauthorized`: Missing/invalid authentication
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Semantic validation error
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Database unavailable

### Error Response Format
```json
{
  "detail": "Alert rule not found with rule_id: rule_xyz"
}
```

### Exception Handling
```python
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

---

## Deployment Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_PORT` | HTTP port | 8218 |
| `SERVICE_HOST` | Bind address | 0.0.0.0 |
| `POSTGRES_HOST` | PostgreSQL gRPC host | isa-postgres-grpc |
| `POSTGRES_PORT` | PostgreSQL gRPC port | 50061 |
| `NATS_URL` | NATS connection | nats://isa-nats:4222 |
| `CONSUL_HOST` | Consul host | localhost |
| `CONSUL_PORT` | Consul port | 8500 |
| `AUTH_SERVICE_HOST` | Auth service host | localhost |
| `AUTH_SERVICE_PORT` | Auth service port | 8201 |
| `LOG_LEVEL` | Logging level | INFO |
| `DEBUG` | Debug mode | false |

### Health Check

```json
GET /health
{
  "status": "healthy",
  "service": "telemetry_service",
  "port": 8218,
  "version": "1.0.0"
}

GET /health/detailed
{
  "status": "healthy",
  "service": "telemetry_service",
  "port": 8218,
  "version": "1.0.0",
  "components": {
    "data_ingestion": "healthy",
    "time_series_db": "healthy",
    "alert_engine": "healthy",
    "real_time_stream": "healthy"
  },
  "performance": {
    "ingestion_rate": "1250 points/sec",
    "query_latency": "45ms",
    "storage_usage": "67%"
  }
}
```

### Consul Registration

```json
{
  "service_name": "telemetry_service",
  "port": 8218,
  "tags": ["api", "telemetry", "iot", "monitoring"],
  "meta": {
    "version": "1.0.0",
    "capabilities": "data_ingestion,metrics,alerts,realtime,aggregation",
    "route_count": "25",
    "routes": "/api/v1/telemetry/*"
  },
  "health_check_type": "http",
  "health_check_path": "/health"
}
```

---

## Testing Strategy

### Contract Testing (Layer 4 & 5)
- **Data Contract**: Pydantic schema validation
- **Logic Contract**: Business rule documentation
- **Component Tests**: Factory, builder, validation tests

### Integration Testing
- **HTTP + Database**: Full request/response cycle
- **Event Publishing**: Verify events published correctly
- **Alert Evaluation**: End-to-end alert triggering

### API Testing
- **Endpoint Contracts**: All 25+ endpoints tested
- **Error Handling**: Validation, not found, server errors
- **Pagination**: Page boundaries, empty results

### Smoke Testing
- **E2E Scripts**: Bash scripts for critical paths
- **Health Checks**: Service startup validation
- **Database Connectivity**: PostgreSQL availability

---

**Document Version**: 1.0
**Last Updated**: 2025-12-18
**Maintained By**: Telemetry Service Engineering Team
**Related Documents**:
- Domain Context: docs/domain/telemetry_service.md
- PRD: docs/prd/telemetry_service.md
- Data Contract: tests/contracts/telemetry_service/data_contract.py
- Logic Contract: tests/contracts/telemetry_service/logic_contract.md
- System Contract: tests/contracts/telemetry_service/system_contract.md
