# Telemetry Service - Domain Context

## Overview

The Telemetry Service is the **IoT data backbone** for the isA_user platform. It provides centralized management of device telemetry data including ingestion, storage, querying, aggregation, and alerting capabilities. Every IoT device sends its sensor readings and operational metrics through this service.

**Business Context**: Enable real-time device monitoring and historical data analysis through efficient time-series data management. Telemetry Service owns the "what" of device behavior - capturing, storing, and analyzing the continuous stream of data from connected devices.

**Core Value Proposition**: Transform raw device data into actionable insights through intelligent data ingestion, flexible metric definitions, powerful aggregation capabilities, and proactive alerting mechanisms.

---

## Business Taxonomy

### Core Entities

#### 1. Telemetry Data Point
**Definition**: A single measurement or reading from a device at a specific point in time.

**Business Purpose**:
- Capture real-time device state and measurements
- Enable historical analysis and trend detection
- Support time-series queries and visualizations
- Provide data for alert condition evaluation

**Key Attributes**:
- Timestamp (when the measurement was taken)
- Device ID (which device produced the data)
- Metric Name (type of measurement: temperature, cpu_usage, etc.)
- Value (numeric, string, boolean, or JSON)
- Unit (measurement unit: celsius, percent, etc.)
- Tags (key-value pairs for filtering)
- Metadata (additional context)
- Quality (data quality indicator, 0-100)

**Data Types Supported**:
- **Numeric**: Integer or floating-point values (temperature: 25.5)
- **String**: Text values (status: "running")
- **Boolean**: True/false values (is_online: true)
- **JSON**: Complex structured data (location: {lat: 37.7, lng: -122.4})
- **Binary**: Raw binary data
- **Geolocation**: GPS coordinates
- **Timestamp**: Date/time values

#### 2. Metric Definition
**Definition**: Schema definition for a type of telemetry metric, specifying data type, validation rules, and aggregation behavior.

**Business Purpose**:
- Standardize metric naming and data types
- Enable data validation on ingestion
- Configure retention and aggregation policies
- Support metric discovery and documentation

**Key Attributes**:
- Metric ID (unique identifier)
- Name (human-readable metric name)
- Description (purpose and usage)
- Data Type (numeric/string/boolean/json)
- Metric Type (gauge/counter/histogram/summary)
- Unit (measurement unit)
- Min/Max Value (validation bounds)
- Retention Days (data retention period)
- Aggregation Interval (default aggregation window)
- Tags (categorization labels)
- Metadata (additional configuration)

**Metric Types**:
- **Gauge**: Instantaneous values that can go up or down (temperature, memory usage)
- **Counter**: Monotonically increasing values (request count, bytes sent)
- **Histogram**: Distribution of values (response time buckets)
- **Summary**: Statistical aggregations (percentiles)

#### 3. Alert Rule
**Definition**: A conditional rule that monitors telemetry data and triggers alerts when conditions are met.

**Business Purpose**:
- Proactively detect anomalies and issues
- Enable automated incident response
- Reduce mean time to detection (MTTD)
- Support operational excellence

**Key Attributes**:
- Rule ID (unique identifier)
- Name (rule display name)
- Description (what this rule monitors)
- Metric Name (which metric to monitor)
- Condition (comparison operator: >, <, ==, !=)
- Threshold Value (trigger threshold)
- Evaluation Window (seconds to evaluate)
- Trigger Count (consecutive violations required)
- Level (info/warning/error/critical/emergency)
- Device IDs (specific devices to monitor)
- Device Groups (device groups to monitor)
- Device Filters (dynamic device selection)
- Notification Channels (where to send alerts)
- Cooldown Minutes (minimum time between alerts)
- Auto Resolve (automatically resolve when normal)
- Auto Resolve Timeout (seconds before auto-resolve)
- Enabled (is rule active)
- Tags (categorization labels)

**Alert Levels**:
- **Info**: Informational, no action required
- **Warning**: Potential issue, investigate soon
- **Error**: Problem detected, action required
- **Critical**: Severe issue, immediate action required
- **Emergency**: System-wide emergency, all hands on deck

#### 4. Alert
**Definition**: An instance of a triggered alert rule, representing a detected issue.

**Business Purpose**:
- Track active issues requiring attention
- Enable incident management workflow
- Provide audit trail of system issues
- Support root cause analysis

**Key Attributes**:
- Alert ID (unique identifier)
- Rule ID (which rule triggered)
- Rule Name (rule display name)
- Device ID (affected device)
- Metric Name (metric that triggered)
- Level (severity level)
- Status (active/acknowledged/resolved/suppressed)
- Message (alert description)
- Current Value (value when triggered)
- Threshold Value (rule threshold)
- Triggered At (when alert fired)
- Acknowledged At (when someone acknowledged)
- Resolved At (when alert resolved)
- Auto Resolve At (scheduled auto-resolve time)
- Acknowledged By (user who acknowledged)
- Resolved By (user who resolved)
- Resolution Note (closure notes)
- Affected Devices Count (scope of impact)
- Tags (categorization labels)
- Metadata (additional context)

**Alert States**:
- **Active**: Alert is currently firing, issue persists
- **Acknowledged**: Someone is aware and investigating
- **Resolved**: Issue has been addressed and confirmed fixed
- **Suppressed**: Alert temporarily muted (maintenance window)

#### 5. Real-Time Subscription
**Definition**: A subscription for receiving real-time telemetry data updates via WebSocket.

**Business Purpose**:
- Enable live dashboards and monitoring
- Support real-time device tracking
- Power interactive data visualizations
- Reduce polling overhead

**Key Attributes**:
- Subscription ID (unique identifier)
- Device IDs (devices to subscribe to)
- Metric Names (metrics to receive)
- Tags (filter by tags)
- Filter Condition (additional filtering)
- Max Frequency (rate limiting in milliseconds)
- Created At (subscription start time)
- Last Sent (last data transmission time)

---

## Domain Scenarios

### Scenario 1: Telemetry Data Ingestion
**Actor**: IoT Device, Device Gateway
**Trigger**: Device sends sensor readings at regular intervals
**Flow**:
1. Device collects sensor data (temperature: 25.5C, humidity: 60%)
2. Device or gateway calls `POST /api/v1/telemetry/devices/{device_id}/telemetry` with data point
3. Telemetry Service validates data point against metric definition (if exists)
4. Service stores data in PostgreSQL time-series table with proper value type
5. Service checks all enabled alert rules for this metric
6. If alert condition met, triggers alert and publishes `alert.triggered` event
7. Service notifies real-time subscribers matching this device/metric
8. Publishes `telemetry.data.received` event to NATS
9. Returns success confirmation to device

**Outcome**: Data point stored, alerts evaluated, real-time subscribers notified, audit trail created

### Scenario 2: Batch Data Ingestion
**Actor**: Device Gateway, Edge Computing Node
**Trigger**: Gateway buffers device data and sends in batches for efficiency
**Flow**:
1. Gateway collects 100 data points from multiple sensors over 1 minute
2. Gateway calls `POST /api/v1/telemetry/devices/{device_id}/telemetry/batch` with batch request
3. Telemetry Service processes each data point in the batch
4. Service validates each point and stores successfully validated points
5. Service tracks ingested count and failed count
6. Service evaluates alert rules for each stored point
7. Publishes single `telemetry.data.received` event with aggregate counts
8. Returns detailed result: {ingested_count: 98, failed_count: 2, errors: [...]}

**Outcome**: Efficient batch processing, partial success handling, reduced network overhead

### Scenario 3: Metric Definition Creation
**Actor**: System Administrator, DevOps Engineer
**Trigger**: Need to define schema for a new type of sensor data
**Flow**:
1. Admin identifies need for new metric: "battery_level"
2. Admin calls `POST /api/v1/telemetry/metrics` with metric definition:
   - Name: "battery_level"
   - Data Type: numeric
   - Metric Type: gauge
   - Unit: "percent"
   - Min Value: 0
   - Max Value: 100
   - Retention Days: 90
3. Telemetry Service validates metric name uniqueness
4. Service creates metric definition in PostgreSQL
5. Publishes `metric.defined` event to NATS
6. Returns MetricDefinitionResponse with metric_id
7. Future data ingestion for this metric will be validated against bounds

**Outcome**: Standardized metric schema, data validation enabled, metric discoverable

### Scenario 4: Alert Rule Configuration
**Actor**: Operations Engineer, SRE
**Trigger**: Need to be notified when device temperature exceeds safe threshold
**Flow**:
1. Engineer identifies monitoring requirement: "Alert if CPU > 90%"
2. Engineer calls `POST /api/v1/telemetry/alerts/rules` with:
   - Name: "High CPU Usage"
   - Metric Name: "cpu_percent"
   - Condition: ">"
   - Threshold Value: 90
   - Level: warning
   - Evaluation Window: 300 (5 minutes)
   - Trigger Count: 3 (3 consecutive violations)
   - Auto Resolve: true
   - Auto Resolve Timeout: 600
3. Telemetry Service creates alert rule in PostgreSQL
4. Publishes `alert.rule.created` event
5. Returns AlertRuleResponse with rule_id
6. Service starts evaluating incoming data against this rule
7. When 3 consecutive readings > 90%, alert triggers

**Outcome**: Proactive monitoring configured, automatic alerting enabled

### Scenario 5: Time-Series Data Query
**Actor**: Analytics Dashboard, Reporting System
**Trigger**: User wants to view historical temperature data for analysis
**Flow**:
1. Dashboard needs 24 hours of temperature data for device_001
2. Dashboard calls `POST /api/v1/telemetry/query` with:
   - Devices: ["device_001"]
   - Metrics: ["temperature"]
   - Start Time: now - 24h
   - End Time: now
   - Aggregation: AVG
   - Interval: 3600 (hourly aggregation)
3. Telemetry Service queries PostgreSQL with time range filter
4. Service aggregates raw data points into hourly averages
5. Returns TelemetryDataResponse with 24 aggregated data points
6. Dashboard renders time-series chart
7. User can drill down to raw data if needed

**Outcome**: Efficient historical data retrieval, server-side aggregation, reduced data transfer

### Scenario 6: Real-Time Data Subscription
**Actor**: Live Dashboard, Mobile App
**Trigger**: User opens live device monitoring view
**Flow**:
1. Dashboard calls `POST /api/v1/telemetry/subscribe` with:
   - Device IDs: ["device_001", "device_002"]
   - Metric Names: ["temperature", "humidity"]
   - Max Frequency: 1000 (1 second minimum interval)
2. Telemetry Service creates subscription with unique subscription_id
3. Returns subscription details with WebSocket URL
4. Dashboard opens WebSocket connection to `/ws/telemetry/{subscription_id}`
5. Service pushes matching data points as they arrive
6. Dashboard updates charts in real-time
7. When dashboard closes, calls `DELETE /api/v1/telemetry/subscribe/{subscription_id}`
8. Service removes subscription and closes WebSocket

**Outcome**: Real-time data streaming, efficient push-based updates, clean resource cleanup

### Scenario 7: Alert Lifecycle Management
**Actor**: On-Call Engineer, NOC Operator
**Trigger**: Alert fires for high memory usage on production server
**Flow**:
1. Memory exceeds 95% on device_prod_001
2. Alert rule "High Memory" triggers
3. Telemetry Service creates alert with status "active"
4. Publishes `alert.triggered` event
5. Notification Service sends Slack/PagerDuty alert
6. On-call engineer acknowledges: `PUT /api/v1/telemetry/alerts/{alert_id}/acknowledge`
7. Alert status changes to "acknowledged"
8. Engineer investigates and fixes memory leak
9. Engineer resolves: `PUT /api/v1/telemetry/alerts/{alert_id}/resolve` with resolution note
10. Alert status changes to "resolved"
11. Publishes `alert.resolved` event
12. Incident tracked in audit log

**Outcome**: Complete alert lifecycle tracking, clear ownership, audit trail maintained

### Scenario 8: Device Telemetry Statistics
**Actor**: Device Manager, Support Engineer
**Trigger**: Need to understand telemetry health for a specific device
**Flow**:
1. Support engineer investigating device connectivity issues
2. Calls `GET /api/v1/telemetry/devices/{device_id}/stats`
3. Telemetry Service queries PostgreSQL for device statistics:
   - Total data points count
   - Number of active metrics
   - Last update timestamp
   - Last 24 hours point count
   - Last 24 hours alert count
4. Calculates average data frequency (points per minute)
5. Identifies top metrics by volume
6. Returns DeviceTelemetryStatsResponse
7. Engineer sees device hasn't sent data in 2 hours
8. Initiates device troubleshooting

**Outcome**: Device health visibility, quick diagnostics, proactive issue detection

---

## Domain Events

### Published Events

#### 1. `telemetry.data.received` (EventType.TELEMETRY_DATA_RECEIVED)
**Trigger**: After successful telemetry data ingestion
**Payload**:
```json
{
  "event_id": "uuid",
  "event_type": "telemetry.data.received",
  "device_id": "device_001",
  "metrics_count": 3,
  "points_count": 10,
  "timestamp": "2025-01-01T00:00:00Z"
}
```
**Subscribers**:
- **Analytics Service**: Track data ingestion metrics
- **Device Service**: Update device last_seen timestamp
- **Billing Service**: Track data usage for billing

#### 2. `metric.defined` (EventType.METRIC_DEFINED)
**Trigger**: After successful metric definition creation
**Payload**:
```json
{
  "event_id": "uuid",
  "event_type": "metric.defined",
  "metric_id": "uuid",
  "name": "battery_level",
  "data_type": "numeric",
  "metric_type": "gauge",
  "unit": "percent",
  "created_by": "user_123",
  "timestamp": "2025-01-01T00:00:00Z"
}
```
**Subscribers**:
- **Audit Service**: Log metric definition changes
- **Analytics Service**: Track metric catalog growth

#### 3. `alert.rule.created` (EventType.ALERT_RULE_CREATED)
**Trigger**: After successful alert rule creation
**Payload**:
```json
{
  "event_id": "uuid",
  "event_type": "alert.rule.created",
  "rule_id": "uuid",
  "name": "High CPU Usage",
  "metric_name": "cpu_percent",
  "condition": ">",
  "threshold_value": "90",
  "level": "warning",
  "enabled": true,
  "created_by": "user_123",
  "timestamp": "2025-01-01T00:00:00Z"
}
```
**Subscribers**:
- **Audit Service**: Log alert configuration changes
- **Notification Service**: Prepare notification channels

#### 4. `alert.triggered` (EventType.ALERT_TRIGGERED)
**Trigger**: When alert condition is met and alert fires
**Payload**:
```json
{
  "event_id": "uuid",
  "event_type": "alert.triggered",
  "alert_id": "uuid",
  "rule_id": "uuid",
  "rule_name": "High CPU Usage",
  "device_id": "device_001",
  "metric_name": "cpu_percent",
  "level": "warning",
  "current_value": "95.5",
  "threshold_value": "90",
  "timestamp": "2025-01-01T00:00:00Z"
}
```
**Subscribers**:
- **Notification Service**: Send alert notifications (email, Slack, PagerDuty)
- **Audit Service**: Log security and operational events
- **Analytics Service**: Track alert patterns and frequencies
- **Device Service**: Update device health status

#### 5. `alert.resolved` (EventType.ALERT_RESOLVED)
**Trigger**: When alert is manually or automatically resolved
**Payload**:
```json
{
  "event_id": "uuid",
  "event_type": "alert.resolved",
  "alert_id": "uuid",
  "rule_id": "uuid",
  "rule_name": "High CPU Usage",
  "device_id": "device_001",
  "metric_name": "cpu_percent",
  "level": "warning",
  "resolved_by": "user_123",
  "resolution_note": "Memory leak fixed in v2.3.1",
  "timestamp": "2025-01-01T00:00:00Z"
}
```
**Subscribers**:
- **Notification Service**: Send resolution notifications
- **Audit Service**: Complete incident audit trail
- **Analytics Service**: Calculate MTTR metrics

### Subscribed Events

#### 1. `device.deleted` from device_service
**Handler**: `handle_device_deleted()`
**Purpose**: Clean up alert rules and stop data processing for deleted devices
**Processing**:
- Disable alert rules targeting this device
- Keep historical telemetry data for analysis
- Log cleanup action

#### 2. `user.deleted` from account_service
**Handler**: `handle_user_deleted()`
**Purpose**: Handle privacy compliance when user is deleted
**Processing**:
- Disable alert rules created by user
- Anonymize user references in telemetry metadata
- Log GDPR compliance action

---

## Core Concepts

### Time-Series Data Model
Telemetry data is fundamentally time-series data - each data point has a timestamp and represents a measurement at that moment. The service optimizes for:
- **High write throughput**: Devices continuously produce data
- **Range queries**: Most queries are for time ranges (last hour, last day)
- **Aggregation**: Raw data often aggregated for visualization
- **Retention management**: Old data expires based on retention policy

### Data Ingestion Pipeline
1. **Receive**: Accept data via REST API (single, batch, bulk)
2. **Validate**: Check against metric definition if exists
3. **Store**: Persist to PostgreSQL time-series table
4. **Evaluate**: Check against active alert rules
5. **Notify**: Push to real-time subscribers
6. **Publish**: Emit event for downstream processing

### Alert Evaluation Engine
Alert rules are evaluated in real-time as data arrives:
- **Condition matching**: Compare current value against threshold
- **Window evaluation**: Track values over evaluation window
- **Trigger counting**: Require N consecutive violations
- **Cooldown enforcement**: Prevent alert storms
- **Auto-resolution**: Automatically resolve when normal

### Aggregation Strategies
Multiple aggregation types support different use cases:
- **AVG**: Average value over interval (typical for gauges)
- **MIN/MAX**: Extremes over interval (peak detection)
- **SUM**: Total over interval (counters)
- **COUNT**: Number of readings (data density)
- **MEDIAN**: Middle value (outlier-resistant)
- **P95/P99**: Percentiles (latency analysis)

### Real-Time Streaming Architecture
WebSocket-based streaming enables live dashboards:
- Subscription-based filtering (device, metric, tags)
- Rate limiting to prevent client overload
- Automatic cleanup on disconnect
- Efficient fan-out to multiple subscribers

### Data Retention and Lifecycle
- Default retention: 90 days
- Configurable per metric definition
- Automatic cleanup of expired data
- Aggregated data may have longer retention
- Historical alerts retained for audit

---

## High-Level Business Rules

### Data Ingestion Rules (BR-TEL-001 to BR-TEL-010)

**BR-TEL-001: Timestamp Requirement**
- Every data point MUST have a valid timestamp
- Timestamp MUST be ISO 8601 format
- Future timestamps (>5 min ahead) are rejected
- Error: "TelemetryError: Invalid timestamp - cannot be in the future"

**BR-TEL-002: Device ID Requirement**
- Every data point MUST have an associated device_id
- Device ID format: string, 1-100 characters
- Error: "TelemetryError: device_id is required"

**BR-TEL-003: Metric Name Requirements**
- Metric name MUST be non-empty
- Metric name length: 1-100 characters
- Metric name SHOULD follow naming convention: snake_case
- Example: `cpu_usage`, `temperature_celsius`, `battery_level`

**BR-TEL-004: Value Type Validation**
- Value MUST match metric definition data_type (if defined)
- Numeric values stored in value_numeric column
- String values stored in value_string column
- Boolean values stored in value_boolean column
- JSON/complex values stored in value_json column
- Error: "TelemetryError: Value type mismatch for metric {name}"

**BR-TEL-005: Value Range Validation**
- If metric definition has min_value, data MUST be >= min_value
- If metric definition has max_value, data MUST be <= max_value
- Validation only applies to numeric values
- Error: "TelemetryError: Value out of range for metric {name}"

**BR-TEL-006: Batch Size Limits**
- Maximum batch size: 1000 data points
- Batches exceeding limit are rejected entirely
- Use bulk endpoint for multi-device batches
- Error: "TelemetryError: Batch size exceeds maximum of 1000"

**BR-TEL-007: Idempotent Upsert**
- Duplicate data points (same time, device, metric) are upserted
- Later values overwrite earlier values for same key
- Enables safe retry without data duplication

**BR-TEL-008: Quality Indicator**
- Quality field indicates data reliability (0-100)
- Default quality: 100 (assumed good)
- Lower quality values used for estimated/interpolated data

**BR-TEL-009: Tag Format**
- Tags MUST be key-value string pairs
- Tag keys: 1-50 characters
- Tag values: 1-100 characters
- Maximum 20 tags per data point

**BR-TEL-010: Metadata Format**
- Metadata stored as JSONB
- No fixed schema, service-defined keys
- Maximum size: 10KB per data point

### Metric Definition Rules (BR-MET-001 to BR-MET-010)

**BR-MET-001: Unique Metric Names**
- Metric name MUST be unique across all definitions
- Case-sensitive uniqueness
- Error: "MetricError: Metric with name '{name}' already exists"

**BR-MET-002: Data Type Required**
- Data type MUST be specified: numeric, string, boolean, json, binary, geolocation, timestamp
- Cannot be changed after creation (immutable)

**BR-MET-003: Metric Type Specification**
- Metric type defaults to "gauge" if not specified
- Valid types: gauge, counter, histogram, summary
- Type affects aggregation behavior

**BR-MET-004: Retention Configuration**
- Retention days range: 1-3650 (1 day to 10 years)
- Default retention: 90 days
- Shorter retention for high-volume metrics

**BR-MET-005: Aggregation Interval**
- Aggregation interval range: 1-86400 seconds (1 second to 24 hours)
- Default interval: 60 seconds
- Affects pre-computed aggregation granularity

**BR-MET-006: Value Bounds**
- min_value and max_value are optional
- Only applicable to numeric data types
- min_value MUST be < max_value if both specified
- Error: "MetricError: min_value must be less than max_value"

**BR-MET-007: Unit Specification**
- Unit is optional but recommended
- Max length: 20 characters
- Examples: "celsius", "percent", "bytes", "ms"

**BR-MET-008: Description Requirement**
- Description is optional but recommended
- Max length: 500 characters
- Should explain metric purpose and usage

**BR-MET-009: Creator Tracking**
- created_by field tracks who defined the metric
- Cannot be changed after creation
- Used for audit and ownership tracking

**BR-MET-010: Deletion Cascade**
- Deleting metric definition does NOT delete data
- Data retention continues based on original policy
- Alert rules referencing metric should be disabled

### Alert Rule Rules (BR-ALR-001 to BR-ALR-010)

**BR-ALR-001: Rule Name Requirements**
- Rule name MUST be non-empty
- Rule name length: 1-200 characters
- Should be descriptive: "High CPU on Production Servers"

**BR-ALR-002: Condition Format**
- Condition MUST be valid comparison operator
- Supported: >, <, >=, <=, ==, !=
- Applied to numeric metrics primarily
- Error: "AlertError: Invalid condition operator"

**BR-ALR-003: Threshold Value Type**
- Threshold value can be numeric or string
- Should match metric data type
- Stored as string for flexibility

**BR-ALR-004: Evaluation Window Bounds**
- Evaluation window range: 60-3600 seconds (1 minute to 1 hour)
- Default: 300 seconds (5 minutes)
- Shorter windows for faster detection, more noise

**BR-ALR-005: Trigger Count Configuration**
- Trigger count range: 1-100
- Default: 1 (trigger on first violation)
- Higher counts reduce false positives

**BR-ALR-006: Alert Level Required**
- Level MUST be specified: info, warning, error, critical, emergency
- Default: warning
- Affects notification routing and urgency

**BR-ALR-007: Cooldown Period**
- Cooldown range: 1-1440 minutes (1 minute to 24 hours)
- Default: 15 minutes
- Prevents duplicate alerts for same condition

**BR-ALR-008: Auto-Resolve Configuration**
- Auto-resolve can be enabled/disabled
- Auto-resolve timeout: 300-86400 seconds (5 minutes to 24 hours)
- Default timeout: 3600 seconds (1 hour)

**BR-ALR-009: Device Targeting**
- Rules can target: specific device_ids, device groups, or filters
- Empty targeting = all devices
- Filter format is JSONB for flexible matching

**BR-ALR-010: Rule Enable/Disable**
- Disabled rules are not evaluated
- Rules can be enabled/disabled without deletion
- Status change is immediate

### Alert Management Rules (BR-ALM-001 to BR-ALM-005)

**BR-ALM-001: Alert Status Transitions**
- Active -> Acknowledged: User acknowledges
- Active -> Resolved: User resolves or auto-resolve
- Acknowledged -> Resolved: User resolves
- Suppressed: Temporary state during maintenance
- Invalid transitions rejected

**BR-ALM-002: Acknowledgement Requirements**
- Only active alerts can be acknowledged
- Acknowledging sets acknowledged_by and acknowledged_at
- Optional note can be provided

**BR-ALM-003: Resolution Requirements**
- Active or acknowledged alerts can be resolved
- Resolution sets resolved_by and resolved_at
- Resolution note is optional but recommended
- Publishes alert.resolved event

**BR-ALM-004: Alert Deduplication**
- Same rule/device combination has cooldown period
- Duplicate alerts within cooldown are suppressed
- Cooldown resets after resolution

**BR-ALM-005: Alert Statistics Tracking**
- total_triggers incremented on each trigger
- last_triggered updated on each trigger
- Used for rule effectiveness analysis

### Query Rules (BR-QRY-001 to BR-QRY-010)

**BR-QRY-001: Time Range Required**
- start_time and end_time are REQUIRED
- end_time MUST be > start_time
- Maximum range: 90 days (configurable)
- Error: "QueryError: Invalid time range"

**BR-QRY-002: Metric Filter Required**
- At least one metric_name MUST be specified
- Multiple metrics supported in single query

**BR-QRY-003: Result Limits**
- Default limit: 1000 data points
- Maximum limit: 10000 data points
- Pagination supported via offset

**BR-QRY-004: Aggregation Requirements**
- Aggregation type and interval must be specified together
- Interval range: 60-86400 seconds
- Supported types: avg, min, max, sum, count, median, p95, p99

**BR-QRY-005: Device Filtering**
- Device IDs are optional (query all devices if empty)
- Multiple device IDs supported

**BR-QRY-006: Tag Filtering**
- Tags can filter results
- All specified tags must match (AND logic)

**BR-QRY-007: Query Timeout**
- Complex queries timeout after 30 seconds
- Aggregation helps reduce data volume

**BR-QRY-008: Result Ordering**
- Results ordered by timestamp DESC (newest first)
- Consistent ordering for pagination

**BR-QRY-009: Empty Results**
- No data in range returns empty array, not error
- Count is 0 for empty results

**BR-QRY-010: Aggregated vs Raw**
- Without aggregation: returns raw data points
- With aggregation: returns aggregated buckets
- Aggregation reduces result volume significantly

### Real-Time Subscription Rules (BR-RTS-001 to BR-RTS-005)

**BR-RTS-001: Subscription Limits**
- Maximum subscriptions per user: 10
- Maximum devices per subscription: 100
- Maximum metrics per subscription: 50

**BR-RTS-002: Frequency Limits**
- min_frequency range: 100-10000 milliseconds
- Default: 1000ms (1 update per second)
- Prevents client overload

**BR-RTS-003: WebSocket Lifecycle**
- Subscription creates WebSocket URL
- Connection must be established within 60 seconds
- Idle connections closed after 5 minutes

**BR-RTS-004: Subscription Cleanup**
- Explicit unsubscribe removes subscription
- WebSocket close removes subscription
- Server restart clears all subscriptions

**BR-RTS-005: Data Filtering**
- Subscriptions filter by device_id, metric_name, tags
- Only matching data points are pushed
- Additional filter_condition for complex filtering

### Authorization Rules (BR-AUTH-001 to BR-AUTH-005)

**BR-AUTH-001: Authentication Required**
- All endpoints require authentication (JWT or API key)
- Exception: /health endpoints for load balancer checks
- Error: 401 "Authentication required"

**BR-AUTH-002: Internal Service Calls**
- X-Internal-Call: true header bypasses auth
- Used for trusted service-to-service communication
- Should be restricted at network level

**BR-AUTH-003: User Context**
- All operations track user_id from auth context
- Used for audit trail and ownership

**BR-AUTH-004: Metric Definition Access**
- All authenticated users can create/read metrics
- Delete restricted to creator or admin (future)

**BR-AUTH-005: Alert Rule Ownership**
- Alert rules track created_by
- Modification should be restricted to owner/admin (future)

---

## Telemetry Service in the Ecosystem

### Upstream Dependencies
- **Device Service**: Provides device context and validates device existence
- **Auth Service**: JWT/API key validation for authentication
- **PostgreSQL gRPC Service**: Time-series data persistence
- **NATS Event Bus**: Event publishing infrastructure
- **Consul**: Service discovery and health checks
- **API Gateway**: Request routing and rate limiting

### Downstream Consumers
- **Device Service**: Updates device health status based on telemetry
- **Notification Service**: Sends alert notifications
- **Audit Service**: Logs telemetry operations and alerts
- **Analytics Service**: Aggregates telemetry for business intelligence
- **Billing Service**: Tracks data usage for billing
- **Dashboard Service**: Visualizes telemetry data and alerts
- **Compliance Service**: Monitors compliance-related metrics

### Integration Patterns
- **Synchronous REST**: CRUD operations via FastAPI endpoints
- **Asynchronous Events**: NATS for real-time event publishing
- **WebSocket**: Real-time data streaming
- **Service Discovery**: Consul for dynamic service location
- **Protocol Buffers**: PostgreSQL gRPC communication
- **Health Checks**: `/health` and `/health/detailed` endpoints

### Dependency Injection
- **Repository Pattern**: TelemetryRepository for data access
- **Protocol Interfaces**: TelemetryRepositoryProtocol, EventBusProtocol
- **Factory Pattern**: create_telemetry_service() for production instances
- **Mock-Friendly**: Protocols enable test doubles and mocks

---

## Success Metrics

### Data Quality Metrics
- **Ingestion Success Rate**: % of data points successfully stored (target: >99.9%)
- **Validation Pass Rate**: % of data points passing validation (target: >99%)
- **Data Freshness**: Time since last data point per device (target: <5 min)
- **Missing Data Rate**: Gaps in expected time series (target: <0.1%)

### Performance Metrics
- **Ingestion Latency**: Time from API call to storage (target: <100ms)
- **Query Latency**: Time for time-range query (target: <200ms)
- **Aggregation Latency**: Time for aggregated query (target: <500ms)
- **Real-time Delay**: Time from ingestion to WebSocket delivery (target: <100ms)

### Alert Metrics
- **Mean Time to Detection (MTTD)**: Time from issue to alert (target: <1 min)
- **False Positive Rate**: % of alerts that were not real issues (target: <5%)
- **Alert Storm Prevention**: Duplicate alerts prevented by cooldown (target: >90%)
- **Auto-Resolution Rate**: % of alerts auto-resolved (target: ~30%)

### Availability Metrics
- **Service Uptime**: Telemetry Service availability (target: 99.9%)
- **Database Connectivity**: PostgreSQL connection success (target: 99.99%)
- **Event Publishing Success**: % of events successfully published (target: >99.5%)
- **WebSocket Availability**: Real-time streaming uptime (target: 99.5%)

### Business Metrics
- **Daily Data Points**: Total data points ingested per day
- **Active Devices**: Devices sending data in last 24 hours
- **Metric Diversity**: Number of distinct metrics tracked
- **Alert Resolution Time**: Average time to resolve alerts

---

## Glossary

**Telemetry**: Automated measurement and transmission of data from remote sources
**Data Point**: Single measurement with timestamp, device, metric, and value
**Metric**: Type of measurement (temperature, cpu_usage, battery_level)
**Gauge**: Metric type for instantaneous values that can go up or down
**Counter**: Metric type for monotonically increasing values
**Time Series**: Sequence of data points ordered by time
**Aggregation**: Combining multiple data points into summary statistics
**Alert Rule**: Condition that triggers alerts when met
**Threshold**: Value that triggers alert when crossed
**Evaluation Window**: Time period for alert condition evaluation
**Cooldown**: Minimum time between repeated alerts
**Auto-Resolve**: Automatic alert resolution when condition clears
**Real-Time Subscription**: WebSocket-based live data streaming
**Ingestion**: Process of receiving and storing telemetry data
**Retention**: Duration data is kept before automatic deletion
**JSONB**: PostgreSQL JSON binary format for flexible data storage

---

**Document Version**: 1.0
**Last Updated**: 2025-12-18
**Maintained By**: Telemetry Service Team
