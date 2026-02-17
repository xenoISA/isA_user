# Device Service Design Document

## Architecture Overview

The Device Service follows a microservices architecture pattern with clear separation of concerns, leveraging event-driven communication and modern cloud-native principles. The service is designed for high availability, scalability, and security while maintaining loose coupling with other platform services.

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   Mobile App    │    │  IoT Devices    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │    API Gateway           │
                    │   (Authentication,       │
                    │    Rate Limiting,       │
                    │    Load Balancing)      │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │    Device Service        │
                    │  (FastAPI Application)   │
                    └─────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
    ┌─────┴─────┐        ┌─────┴─────┐        ┌─────┴─────┐
    │   Event   │        │ Database  │        │   MQTT    │
    │   Bus     │        │ PostgreSQL│        │   Broker  │
    │ (NATS)    │        │ (gRPC)    │        │ (EMQX)    │
    └───────────┘        └───────────┘        └───────────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
    ┌─────────────────────────────┴─────────────────────────────┐
    │                 Supporting Services                     │
    │  Auth | Org | Telemetry | Media | Notification | OTA    │
    └───────────────────────────────────────────────────────────┘
```

### Service Components

#### 1. API Layer (FastAPI)
- **Purpose**: HTTP API interface for external clients
- **Responsibilities**: Request validation, authentication, response formatting
- **Technologies**: FastAPI, Pydantic, Uvicorn
- **Features**: Automatic OpenAPI documentation, request validation, async handling

#### 2. Business Logic Layer
- **Purpose**: Core business logic and orchestration
- **Responsibilities**: Device lifecycle management, command execution, health monitoring
- **Technologies**: Python, dependency injection, async/await
- **Features**: Service classes, business rules validation, event publishing

#### 3. Data Access Layer
- **Purpose**: Database operations and data persistence
- **Responsibilities**: CRUD operations, transaction management, data transformation
- **Technologies**: AsyncPostgresClient, gRPC, connection pooling
- **Features**: Async operations, connection management, error handling

#### 4. Event Management
- **Purpose**: Event-driven communication and integration
- **Responsibilities**: Event publishing, subscription handling, message routing
- **Technologies**: NATS, asyncio, event schemas
- **Features**: Reliable delivery, message ordering, error handling

#### 5. Command Execution
- **Purpose**: Device command delivery and tracking
- **Responsibilities**: Command queuing, MQTT publishing, result tracking
- **Technologies**: MQTT, async message handling, retry logic
- **Features**: Priority queuing, timeout management, status tracking

## Component Design

### API Layer Design

#### Request/Response Models
```python
# Request Models
DeviceRegistrationRequest
DeviceUpdateRequest
DeviceAuthRequest
DeviceCommandRequest
BulkCommandRequest
DeviceGroupRequest
DevicePairingRequest

# Response Models
DeviceResponse
DeviceAuthResponse
DeviceStatsResponse
DeviceHealthResponse
DeviceGroupResponse
DeviceListResponse
FrameResponse
```

#### Authentication Middleware
```python
async def get_user_context(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    x_internal_call: Optional[str] = Header(None)
) -> Dict[str, Any]:
    # JWT token verification via AuthServiceClient
    # API key verification
    # Internal service call bypass
    # User context extraction
```

#### Rate Limiting
- **Per-User Rate Limits**: 100 requests/minute per user
- **Per-Device Rate Limits**: 10 commands/minute per device
- **Admin Rate Limits**: 1000 requests/minute for admin operations
- **Burst Capacity**: 20% above limits for short bursts

### Business Logic Design

#### Service Classes
```python
class DeviceService:
    # Device lifecycle management
    async def register_device(user_id: str, device_data: dict) -> DeviceResponse
    async def authenticate_device(device_id: str, auth_data: dict) -> DeviceAuthResponse
    async def update_device_status(device_id: str, status: DeviceStatus) -> bool
    async def decommission_device(device_id: str) -> bool
    
    # Command execution
    async def send_command(device_id: str, user_id: str, command: dict) -> dict
    async def get_command_status(command_id: str) -> dict
    
    # Health monitoring
    async def get_device_health(device_id: str) -> DeviceHealthResponse
    async def get_device_stats(user_id: str) -> DeviceStatsResponse
    
    # Device groups
    async def create_device_group(user_id: str, group_data: dict) -> DeviceGroupResponse
    async def add_device_to_group(group_id: str, device_id: str) -> bool
    
    # Smart frame features
    async def pair_frame(device_id: str, pairing_token: str, user_id: str) -> dict
    async def sync_frame_content(device_id: str, sync_data: dict) -> dict
```

#### Dependency Injection
```python
class DeviceService:
    def __init__(
        self,
        repository: DeviceRepositoryProtocol,
        event_bus: Optional[EventBus] = None,
        mqtt_client: Optional[MQTTClient] = None,
        auth_client: Optional[AuthServiceClient] = None
    ):
        # Constructor injection for testability
        # Lazy loading for external services
        # Circuit breaker pattern for resilience
```

### Data Access Design

#### Repository Pattern
```python
class DeviceRepositoryProtocol(Protocol):
    # Device operations
    async def create_device(device_data: dict) -> DeviceResponse
    async def get_device_by_id(device_id: str) -> Optional[DeviceResponse]
    async def list_user_devices(user_id: str, **filters) -> List[DeviceResponse]
    async def update_device(device_id: str, update_data: dict) -> bool
    async def delete_device(device_id: str) -> bool
    
    # Command operations
    async def create_device_command(command_data: dict) -> bool
    async def update_command_status(command_id: str, status: str) -> bool
    
    # Group operations
    async def create_device_group(group_data: dict) -> DeviceGroupResponse
    async def get_device_group_by_id(group_id: str) -> Optional[DeviceGroupResponse]
    
    # Frame config operations
    async def create_frame_config(device_id: str, config_data: dict) -> bool
    async def get_frame_config(device_id: str) -> Optional[FrameConfig]
```

#### Database Schema Design
```sql
-- Devices table
CREATE TABLE device.devices (
    device_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    device_name VARCHAR(200) NOT NULL,
    device_type VARCHAR(50) NOT NULL,
    manufacturer VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    serial_number VARCHAR(100) NOT NULL UNIQUE,
    firmware_version VARCHAR(50) NOT NULL,
    hardware_version VARCHAR(50),
    mac_address VARCHAR(17),
    connectivity_type VARCHAR(50) NOT NULL,
    security_level VARCHAR(20) DEFAULT 'standard',
    status VARCHAR(20) DEFAULT 'pending',
    last_seen TIMESTAMPTZ,
    location JSONB,
    group_id VARCHAR(255),
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    total_commands INTEGER DEFAULT 0,
    total_telemetry_points INTEGER DEFAULT 0,
    uptime_percentage REAL DEFAULT 0.0,
    registered_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_authenticated_at TIMESTAMPTZ,
    decommissioned_at TIMESTAMPTZ
);

-- Device groups table
CREATE TABLE device.device_groups (
    group_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    group_name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_group_id VARCHAR(255),
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    device_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Device commands table
CREATE TABLE device.device_commands (
    command_id VARCHAR(255) PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    command VARCHAR(100) NOT NULL,
    parameters JSONB DEFAULT '{}',
    timeout INTEGER DEFAULT 30,
    priority INTEGER DEFAULT 1,
    require_ack BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    result JSONB,
    error_message TEXT,
    FOREIGN KEY (device_id) REFERENCES device.devices(device_id)
);

-- Frame configurations table
CREATE TABLE device.frame_configs (
    device_id VARCHAR(255) PRIMARY KEY,
    brightness INTEGER DEFAULT 80,
    contrast INTEGER DEFAULT 100,
    auto_brightness BOOLEAN DEFAULT TRUE,
    orientation VARCHAR(20) DEFAULT 'auto',
    slideshow_interval INTEGER DEFAULT 30,
    slideshow_transition VARCHAR(20) DEFAULT 'fade',
    shuffle_photos BOOLEAN DEFAULT TRUE,
    show_metadata BOOLEAN DEFAULT FALSE,
    sleep_schedule JSONB DEFAULT '{"start": "23:00", "end": "07:00"}',
    auto_sleep BOOLEAN DEFAULT TRUE,
    motion_detection BOOLEAN DEFAULT TRUE,
    auto_sync_albums TEXT[] DEFAULT '{}',
    sync_frequency VARCHAR(20) DEFAULT 'hourly',
    wifi_only_sync BOOLEAN DEFAULT TRUE,
    display_mode VARCHAR(20) DEFAULT 'photo_slideshow',
    location JSONB,
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (device_id) REFERENCES device.devices(device_id)
);

-- Indexes for performance
CREATE INDEX idx_devices_user_id ON device.devices(user_id);
CREATE INDEX idx_devices_status ON device.devices(status);
CREATE INDEX idx_devices_type ON device.devices(device_type);
CREATE INDEX idx_devices_last_seen ON device.devices(last_seen DESC);
CREATE INDEX idx_commands_device_id ON device.device_commands(device_id);
CREATE INDEX idx_commands_status ON device.device_commands(status);
CREATE INDEX idx_groups_user_id ON device.device_groups(user_id);
```

#### Connection Management
```python
class AsyncPostgresClient:
    def __init__(self, host: str, port: int, user_id: str):
        self.host = host
        self.port = port
        self.user_id = user_id
        self._pool = None
        
    async def __aenter__(self):
        # Connection pool management
        # Health checks
        # Retry logic
        # Circuit breaker integration
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Connection cleanup
        # Transaction rollback if needed
        # Performance metrics collection
```

### Event Management Design

#### Event Schemas
```python
# Device lifecycle events
@dataclass
class DeviceRegisteredEvent:
    event_type: str = "device.registered"
    device_id: str
    device_name: str
    device_type: str
    user_id: str
    manufacturer: str
    model: str
    serial_number: str
    connectivity_type: str
    timestamp: str

@dataclass
class DeviceAuthenticatedEvent:
    event_type: str = "device.authenticated"
    device_id: str
    auth_method: str
    token_expiry: int
    authentication_timestamp: str

@dataclass
class DeviceCommandEvent:
    event_type: str = "device.command_sent"
    command_id: str
    device_id: str
    user_id: str
    command: str
    parameters: Dict[str, Any]
    priority: int
    timestamp: str

# Smart frame events
@dataclass
class FramePairedEvent:
    event_type: str = "frame.paired"
    device_id: str
    user_id: str
    pairing_method: str
    pairing_timestamp: str

@dataclass
class FrameSyncStartedEvent:
    event_type: str = "frame.sync_started"
    device_id: str
    sync_type: str
    source_albums: List[str]
    sync_timestamp: str
```

#### Event Publishing Pattern
```python
class EventPublisher:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        
    async def publish_device_registered(self, device: DeviceResponse):
        event = DeviceRegisteredEvent(
            device_id=device.device_id,
            device_name=device.device_name,
            device_type=device.device_type,
            user_id=device.user_id,
            manufacturer=device.manufacturer,
            model=device.model,
            serial_number=device.serial_number,
            connectivity_type=device.connectivity_type,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        await self.event_bus.publish_event(Event(
            event_type=EventType.DEVICE_REGISTERED,
            source=ServiceSource.DEVICE_SERVICE,
            data=asdict(event)
        ))
```

### Command Execution Design

#### Command Queue Architecture
```python
class CommandQueue:
    def __init__(self, mqtt_client: MQTTClient):
        self.mqtt_client = mqtt_client
        self.pending_commands = {}  # command_id -> command_data
        
    async def send_command(self, device_id: str, command_data: dict) -> str:
        # Generate unique command ID
        command_id = secrets.token_hex(16)
        
        # Store in pending queue
        self.pending_commands[command_id] = {
            "device_id": device_id,
            "command": command_data["command"],
            "parameters": command_data.get("parameters", {}),
            "timeout": command_data.get("timeout", 30),
            "priority": command_data.get("priority", 1),
            "created_at": datetime.now(timezone.utc)
        }
        
        # Publish to MQTT topic
        topic = f"devices/{device_id}/commands/{command_id}"
        payload = {
            "command_id": command_id,
            "command": command_data["command"],
            "parameters": command_data.get("parameters", {}),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.mqtt_client.publish(topic, json.dumps(payload))
        return command_id
```

#### MQTT Topic Structure
```
devices/
├── {device_id}/
│   ├── commands/
│   │   ├── {command_id}           # Individual commands
│   │   └── batch                  # Batch operations
│   ├── config/
│   │   ├── update                 # Configuration updates
│   │   └── sync                   # Sync operations
│   ├── status/
│   │   ├── online                 # Online status
│   │   ├── health                 # Health updates
│   │   └── telemetry              # Telemetry data
│   └── responses/
│       ├── {command_id}           # Command responses
│       └── errors                 # Error responses
```

#### Retry and Timeout Logic
```python
class CommandRetryManager:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        
    async def execute_with_retry(self, command_func, *args, **kwargs):
        for attempt in range(self.max_retries + 1):
            try:
                result = await command_func(*args, **kwargs)
                if result.get("success"):
                    return result
            except Exception as e:
                if attempt == self.max_retries:
                    raise
                delay = self.base_delay * (2 ** attempt)  # Exponential backoff
                await asyncio.sleep(delay)
```

## Data Flow Diagrams

### Device Registration Flow
```
┌─────────┐  POST /api/v1/devices  ┌─────────────┐  create_device()  ┌─────────────┐
│ Client   ├─────────────────────────▶│ API Layer   ├─────────────────────▶│Repository   │
└─────────┘                       └─────────────┘                     └─────────────┘
                                           │                                      │
                                           │                                      │
                                           ▼                                      ▼
                                    ┌─────────────┐  publish event  ┌─────────────┐
                                    │   Service   ├─────────────────▶│ Event Bus   │
                                    └─────────────┘                 └─────────────┘
                                           │                                      │
                                           │                                      │
                                           ▼                                      ▼
                                    ┌─────────────┐                       ┌─────────────┐
                                    │   Response  │                       │   Other     │
                                    │   201 OK    │                       │ Services    │
                                    └─────────────┘                       └─────────────┘
```

### Device Command Flow
```
┌─────────┐  POST /api/v1/devices/{id}/commands  ┌─────────────┐
│ Client   ├─────────────────────────────────────────▶│ API Layer   │
└─────────┘                                     └─────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────┐  send_command()  ┌─────────────┐
                                              │   Service   ├───────────────────▶│ MQTT Broker │
                                              └─────────────┘                   └─────────────┘
                                                       │                                │
                                                       ▼                                ▼
                                              ┌─────────────┐  publish topic  ┌─────────────┐
                                              │   Service   ├───────────────────▶│   Device    │
                                              └─────────────┘                   └─────────────┘
                                                       │                                │
                                                       ▼                                ▼
                                              ┌─────────────┐  response topic  ┌─────────────┐
                                              │ MQTT Broker │◀──────────────────┤   Device    │
                                              └─────────────┘                   └─────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────┐
                                              │   Service   │
                                              └─────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────┐
                                              │   Client    │
                                              │  200 OK     │
                                              └─────────────┘
```

### Smart Frame Pairing Flow
```
┌─────────┐  Scan QR Code  ┌─────────────┐  POST /api/v1/devices/{id}/pair  ┌─────────────┐
│   Frame │◀───────────────│ Mobile App  │◀───────────────────────────────────│   User     │
└─────────┘                └─────────────┘                                   └─────────────┘
     │                           │                                                │
     │ Display QR Code           │                                                │
     ▼                           ▼                                                ▼
┌─────────────┐          ┌─────────────┐                                  ┌─────────────┐
│   Frame     │  Token    │ Mobile App  │  Pairing Request              │ Device Svc  │
│ generates   ├───────────▶│ reads token ├───────────────────────────────▶│ validates   │
│ pairing     │           │             │                              │ token with  │
│ token       │           │             │                              │ Auth Svc    │
└─────────────┘           └─────────────┘                                  └─────────────┘
     │                           │                                                │
     │                           │                                                │
     ▼                           ▼                                                ▼
┌─────────────┐          ┌─────────────┐                                  ┌─────────────┐
│   Frame     │ Ownership │ Mobile App  │  Success Response             │ Device Svc  │
│ status      │◀──────────┤ displays    │◀──────────────────────────────┤ updates     │
│ active      │ transfer  │ success     │                              │ device      │
└─────────────┘           └─────────────┘                                  └─────────────┘
```

## Performance Considerations

### Database Optimization
- **Connection Pooling**: Use connection pools to minimize overhead
- **Read Replicas**: Direct read operations to replicas for scalability
- **Indexing Strategy**: Optimize indexes based on query patterns
- **Partitioning**: Consider time-based partitioning for large tables
- **Query Optimization**: Use EXPLAIN ANALYZE for slow query optimization

### Caching Strategy
- **Device Metadata**: Cache frequently accessed device information
- **Authentication Tokens**: Cache validated tokens to reduce Auth Service calls
- **Command Results**: Cache command results for retry scenarios
- **Health Data**: Cache recent health data for performance
- **TTL Management**: Implement appropriate TTL for cached data

### Async Processing
- **Non-blocking Operations**: Use async/await throughout the application
- **Event Processing**: Process events asynchronously to avoid blocking
- **Command Queuing**: Queue commands for background processing
- **Bulk Operations**: Process bulk operations in parallel where possible
- **Resource Management**: Properly manage async resources and cleanup

## Security Architecture

### Authentication Flow
```
┌─────────┐  HTTP Request  ┌─────────────┐  Extract Token  ┌─────────────┐
│ Client   ├─────────────────▶│ API Gateway ├─────────────────▶│ Device Svc  │
└─────────┘                └─────────────┘                 └─────────────┘
                                                               │
                                                               ▼
                                                    ┌─────────────┐  Validate Token  ┌─────────────┐
                                                    │ Device Svc  ├───────────────────▶│ Auth Svc    │
                                                    └─────────────┘                   └─────────────┘
                                                               │                                │
                                                               ▼                                ▼
                                                    ┌─────────────┐  User Context    ┌─────────────┐
                                                    │ Device Svc  │◀─────────────────│ Auth Svc    │
                                                    └─────────────┘                   └─────────────┘
                                                               │
                                                               ▼
                                                    ┌─────────────┐
                                                    │ Processing  │
                                                    │ Continue    │
                                                    └─────────────┘
```

### Authorization Model
```python
class Permission:
    DEVICE_READ = "device:read"
    DEVICE_WRITE = "device:write"
    DEVICE_ADMIN = "device:admin"
    DEVICE_DELETE = "device:delete"
    FRAME_CONTROL = "frame:control"
    FRAME_CONFIG = "frame:config"
    GROUP_MANAGE = "group:manage"
    BULK_OPERATE = "bulk:operate"

class AccessControl:
    def check_permission(self, user_context: dict, permission: str, resource_id: str = None):
        # Check user role
        # Check resource ownership
        # Check family sharing permissions
        # Check organization-based access
        # Return boolean result
```

### Data Encryption
- **Data at Rest**: AES-256 encryption for sensitive data
- **Data in Transit**: TLS 1.3 for all network communications
- **Device Secrets**: Hardware security modules where available
- **Key Management**: Centralized key rotation and management
- **Audit Logging**: Immutable audit trails for all operations

## Monitoring and Observability

### Metrics Collection
```python
# Application metrics
DEVICE_REGISTRATION_COUNT = Counter('device_registrations_total')
DEVICE_AUTHENTICATION_COUNT = Counter('device_authentications_total')
COMMAND_EXECUTION_COUNT = Counter('command_executions_total')
COMMAND_FAILURE_COUNT = Counter('command_failures_total')
API_REQUEST_DURATION = Histogram('api_request_duration_seconds')
DATABASE_QUERY_DURATION = Histogram('database_query_duration_seconds')
MQTT_MESSAGE_COUNT = Counter('mqtt_messages_total')

# System metrics
CPU_USAGE = Gauge('cpu_usage_percent')
MEMORY_USAGE = Gauge('memory_usage_percent')
DISK_USAGE = Gauge('disk_usage_percent')
ACTIVE_CONNECTIONS = Gauge('active_connections')
```

### Health Checks
```python
class HealthChecker:
    async def check_database_health(self) -> bool:
        # Database connectivity check
        # Query performance check
        # Connection pool status
        
    async def check_mqtt_health(self) -> bool:
        # MQTT broker connectivity
        # Topic publishing test
        # Message delivery confirmation
        
    async def check_auth_service_health(self) -> bool:
        # Auth service connectivity
        # Token validation test
        # Service response time
        
    async def check_overall_health(self) -> dict:
        # Aggregate health status
        # Component health summary
        # System metrics overview
```

### Logging Strategy
```python
# Structured logging with correlation IDs
logger.info(
    "Device command sent",
    extra={
        "device_id": device_id,
        "command_id": command_id,
        "user_id": user_id,
        "command_type": command_type,
        "correlation_id": correlation_id,
        "duration_ms": duration_ms
    }
)

# Log levels and retention
# ERROR: Immediate attention required (7 days)
# WARN: Potential issues (30 days)
# INFO: Normal operations (90 days)
# DEBUG: Detailed troubleshooting (7 days)
```

## Deployment Architecture

### Container Design
```dockerfile
FROM python:3.11-slim

# Application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . /app
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8220/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8220"]
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: device-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: device-service
  template:
    metadata:
      labels:
        app: device-service
    spec:
      containers:
      - name: device-service
        image: device-service:latest
        ports:
        - containerPort: 8220
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: MQTT_BROKER_URL
          value: "mqtt://emqx:1883"
        - name: NATS_URL
          value: "nats://nats:4222"
        livenessProbe:
          httpGet:
            path: /health
            port: 8220
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/detailed
            port: 8220
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Service Discovery
```yaml
apiVersion: v1
kind: Service
metadata:
  name: device-service
spec:
  selector:
    app: device-service
  ports:
  - port: 8220
    targetPort: 8220
  type: ClusterIP

---
apiVersion: consul.hashicorp.com/v1alpha1
kind: ServiceDefaults
metadata:
  name: device-service
spec:
  protocol: http
  connect:
    sidecarService:
      port: 20000
```

This design document provides a comprehensive technical blueprint for implementing the Device Service with considerations for scalability, security, performance, and operational excellence.
