# Location Service 设计文档

## 1. 概述

Location Service 是为 IoT 设备生态系统设计的位置管理和地理围栏服务，与现有的 Device Service、Telemetry Service 和 OTA Service 深度集成。

### 1.1 核心功能

- **位置追踪**：实时和历史位置记录
- **地理围栏（Geofencing）**：定义地理区域，检测设备进出
- **位置查询**：按位置搜索设备，查找附近设备
- **轨迹分析**：移动轨迹、速度、距离计算
- **位置共享**：家庭成员间的位置共享
- **位置事件**：位置变化、进出围栏等事件通知

### 1.2 与现有服务的集成

```
┌─────────────────────┐
│  Device Service     │──┐
│  (设备管理)         │  │
└─────────────────────┘  │
                         │
┌─────────────────────┐  │    ┌─────────────────────┐
│  Telemetry Service  │──┼────│  Location Service   │
│  (遥测数据)         │  │    │  (位置服务)         │
└─────────────────────┘  │    └─────────────────────┘
                         │              │
┌─────────────────────┐  │              │
│  OTA Service        │──┘              │
│  (固件更新)         │                 │
└─────────────────────┘                 │
                                        │
                         ┌──────────────┴──────────────┐
                         │                             │
                ┌────────▼─────────┐         ┌────────▼─────────┐
                │  Event Service   │         │  Notification    │
                │  (事件总线)      │         │  Service         │
                └──────────────────┘         └──────────────────┘
```

## 2. 数据模型

### 2.1 核心实体

#### Location (位置记录)
```python
{
    "location_id": str,
    "device_id": str,
    "user_id": str,

    # 地理坐标
    "latitude": float,
    "longitude": float,
    "altitude": Optional[float],
    "accuracy": float,  # 精度（米）
    "heading": Optional[float],  # 方向（度）
    "speed": Optional[float],  # 速度（m/s）

    # 地址信息
    "address": Optional[str],
    "city": Optional[str],
    "state": Optional[str],
    "country": Optional[str],
    "postal_code": Optional[str],

    # 元数据
    "location_method": str,  # GPS, WiFi, Cell, Manual
    "battery_level": Optional[float],
    "timestamp": datetime,
    "source": str,  # device, app, manual
    "metadata": Dict[str, Any]
}
```

#### Geofence (地理围栏)
```python
{
    "geofence_id": str,
    "name": str,
    "description": Optional[str],
    "user_id": str,
    "organization_id": Optional[str],

    # 几何形状
    "shape_type": str,  # circle, polygon, rectangle
    "center_lat": float,
    "center_lon": float,
    "radius": Optional[float],  # 圆形半径（米）
    "polygon_coordinates": Optional[List[Tuple[float, float]]],

    # 配置
    "active": bool,
    "trigger_on_enter": bool,
    "trigger_on_exit": bool,
    "trigger_on_dwell": bool,
    "dwell_time_seconds": Optional[int],

    # 目标设备
    "target_devices": List[str],
    "target_groups": List[str],

    # 时间限制
    "active_days": List[str],  # ["monday", "tuesday", ...]
    "active_hours": Dict[str, str],  # {"start": "09:00", "end": "18:00"}

    # 通知配置
    "notification_channels": List[str],
    "notification_template": Optional[str],

    # 统计
    "total_triggers": int,
    "last_triggered": Optional[datetime],

    "created_at": datetime,
    "updated_at": datetime,
    "tags": List[str],
    "metadata": Dict[str, Any]
}
```

#### LocationEvent (位置事件)
```python
{
    "event_id": str,
    "event_type": str,  # location_update, geofence_enter, geofence_exit, dwell
    "device_id": str,
    "user_id": str,

    # 位置信息
    "location": Location,

    # 地理围栏信息（如果适用）
    "geofence_id": Optional[str],
    "geofence_name": Optional[str],

    # 移动信息
    "distance_from_last": Optional[float],  # 米
    "time_from_last": Optional[float],  # 秒
    "estimated_speed": Optional[float],  # m/s

    # 事件详情
    "trigger_reason": Optional[str],
    "metadata": Dict[str, Any],

    "timestamp": datetime,
    "processed": bool
}
```

#### Place (常用地点)
```python
{
    "place_id": str,
    "user_id": str,
    "name": str,  # "Home", "Office", "School"
    "category": str,  # home, work, favorite

    # 位置
    "latitude": float,
    "longitude": float,
    "address": str,
    "radius": float,  # 识别半径（米）

    # 图标和显示
    "icon": Optional[str],
    "color": Optional[str],

    # 统计
    "visit_count": int,
    "total_time_spent": int,  # 秒
    "last_visit": Optional[datetime],

    "created_at": datetime,
    "updated_at": datetime,
    "tags": List[str]
}
```

#### Route (路线/轨迹)
```python
{
    "route_id": str,
    "device_id": str,
    "user_id": str,
    "name": Optional[str],

    # 路线信息
    "start_location": Location,
    "end_location": Location,
    "waypoints": List[Location],

    # 统计
    "total_distance": float,  # 米
    "total_duration": float,  # 秒
    "avg_speed": float,  # m/s
    "max_speed": float,  # m/s

    "started_at": datetime,
    "ended_at": datetime,
    "created_at": datetime
}
```

### 2.2 枚举类型

```python
class LocationMethod(str, Enum):
    GPS = "gps"
    WIFI = "wifi"
    CELLULAR = "cellular"
    BLUETOOTH = "bluetooth"
    MANUAL = "manual"
    HYBRID = "hybrid"

class GeofenceShapeType(str, Enum):
    CIRCLE = "circle"
    POLYGON = "polygon"
    RECTANGLE = "rectangle"

class GeofenceTriggerType(str, Enum):
    ENTER = "enter"
    EXIT = "exit"
    DWELL = "dwell"

class PlaceCategory(str, Enum):
    HOME = "home"
    WORK = "work"
    SCHOOL = "school"
    FAVORITE = "favorite"
    CUSTOM = "custom"

class LocationEventType(str, Enum):
    LOCATION_UPDATE = "location_update"
    GEOFENCE_ENTER = "geofence_enter"
    GEOFENCE_EXIT = "geofence_exit"
    GEOFENCE_DWELL = "geofence_dwell"
    SIGNIFICANT_MOVEMENT = "significant_movement"
    LOW_BATTERY_AT_LOCATION = "low_battery_at_location"
    DEVICE_STOPPED = "device_stopped"
    DEVICE_MOVING = "device_moving"
```

## 3. API 端点设计

### 3.1 位置管理

```
POST   /locations                     - 报告设备位置
POST   /locations/batch                - 批量报告位置
GET    /locations/device/{device_id}   - 获取设备最新位置
GET    /locations/device/{device_id}/history - 获取位置历史
GET    /locations/user/{user_id}       - 获取用户所有设备位置
DELETE /locations/{location_id}       - 删除位置记录
```

### 3.2 地理围栏

```
POST   /geofences                      - 创建地理围栏
GET    /geofences                      - 列出地理围栏
GET    /geofences/{geofence_id}        - 获取地理围栏详情
PUT    /geofences/{geofence_id}        - 更新地理围栏
DELETE /geofences/{geofence_id}        - 删除地理围栏
POST   /geofences/{geofence_id}/activate - 激活地理围栏
POST   /geofences/{geofence_id}/deactivate - 停用地理围栏
GET    /geofences/{geofence_id}/events - 获取围栏事件历史
GET    /geofences/device/{device_id}/check - 检查设备是否在围栏内
```

### 3.3 位置查询

```
GET    /locations/nearby              - 查找附近的设备
POST   /locations/search/radius       - 圆形区域搜索
POST   /locations/search/polygon      - 多边形区域搜索
POST   /locations/search/route        - 路线搜索
GET    /locations/distance            - 计算两点距离
```

### 3.4 常用地点

```
POST   /places                         - 创建常用地点
GET    /places                         - 列出常用地点
GET    /places/{place_id}              - 获取地点详情
PUT    /places/{place_id}              - 更新地点
DELETE /places/{place_id}              - 删除地点
GET    /places/{place_id}/visits       - 获取访问记录
GET    /places/detect                  - 自动检测常用地点
```

### 3.5 路线/轨迹

```
POST   /routes                         - 开始记录路线
PUT    /routes/{route_id}/end          - 结束路线记录
GET    /routes/{route_id}              - 获取路线详情
GET    /routes/device/{device_id}      - 获取设备路线历史
DELETE /routes/{route_id}              - 删除路线
GET    /routes/{route_id}/replay       - 回放路线
```

### 3.6 位置事件

```
GET    /events                         - 获取位置事件列表
GET    /events/{event_id}              - 获取事件详情
GET    /events/device/{device_id}      - 获取设备事件历史
GET    /events/geofence/{geofence_id}  - 获取围栏事件
```

### 3.7 统计和分析

```
GET    /stats/user/{user_id}           - 用户位置统计
GET    /stats/device/{device_id}       - 设备位置统计
GET    /stats/geofence/{geofence_id}   - 围栏触发统计
GET    /analytics/heatmap              - 热力图数据
GET    /analytics/travel-patterns      - 移动模式分析
```

## 4. 数据库设计

### 4.1 PostgreSQL 表结构

```sql
-- 位置记录表（主表）
CREATE TABLE locations (
    location_id UUID PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,

    -- 地理坐标（使用 PostGIS）
    coordinates GEOGRAPHY(POINT, 4326) NOT NULL,
    altitude FLOAT,
    accuracy FLOAT NOT NULL,
    heading FLOAT,
    speed FLOAT,

    -- 地址信息
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    postal_code VARCHAR(20),

    -- 元数据
    location_method VARCHAR(20),
    battery_level FLOAT,
    source VARCHAR(50),
    metadata JSONB,

    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- 索引
    INDEX idx_device_timestamp (device_id, timestamp DESC),
    INDEX idx_user_timestamp (user_id, timestamp DESC),
    INDEX idx_coordinates USING GIST (coordinates)
);

-- 地理围栏表
CREATE TABLE geofences (
    geofence_id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),

    -- 几何形状
    shape_type VARCHAR(20) NOT NULL,
    geometry GEOGRAPHY NOT NULL,

    -- 配置
    active BOOLEAN DEFAULT TRUE,
    trigger_on_enter BOOLEAN DEFAULT TRUE,
    trigger_on_exit BOOLEAN DEFAULT TRUE,
    trigger_on_dwell BOOLEAN DEFAULT FALSE,
    dwell_time_seconds INT,

    -- 目标设备（JSONB 数组）
    target_devices JSONB,
    target_groups JSONB,

    -- 时间限制
    active_days JSONB,
    active_hours JSONB,

    -- 通知配置
    notification_channels JSONB,
    notification_template TEXT,

    -- 统计
    total_triggers INT DEFAULT 0,
    last_triggered TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    tags JSONB,
    metadata JSONB,

    -- 索引
    INDEX idx_user_active (user_id, active),
    INDEX idx_geometry USING GIST (geometry)
);

-- 位置事件表
CREATE TABLE location_events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    device_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,

    -- 位置信息
    location_id UUID REFERENCES locations(location_id),

    -- 地理围栏信息
    geofence_id UUID REFERENCES geofences(geofence_id),

    -- 移动信息
    distance_from_last FLOAT,
    time_from_last FLOAT,
    estimated_speed FLOAT,

    -- 事件详情
    trigger_reason TEXT,
    metadata JSONB,

    timestamp TIMESTAMPTZ NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- 索引
    INDEX idx_device_timestamp (device_id, timestamp DESC),
    INDEX idx_event_type (event_type, timestamp DESC),
    INDEX idx_geofence_timestamp (geofence_id, timestamp DESC)
);

-- 常用地点表
CREATE TABLE places (
    place_id UUID PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL,

    -- 位置
    coordinates GEOGRAPHY(POINT, 4326) NOT NULL,
    address TEXT,
    radius FLOAT NOT NULL,

    -- 显示
    icon VARCHAR(50),
    color VARCHAR(20),

    -- 统计
    visit_count INT DEFAULT 0,
    total_time_spent INT DEFAULT 0,
    last_visit TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    tags JSONB,

    -- 索引
    INDEX idx_user_category (user_id, category),
    INDEX idx_coordinates USING GIST (coordinates)
);

-- 路线表
CREATE TABLE routes (
    route_id UUID PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    name VARCHAR(200),

    -- 路线信息
    start_location_id UUID REFERENCES locations(location_id),
    end_location_id UUID REFERENCES locations(location_id),

    -- 统计
    total_distance FLOAT,
    total_duration FLOAT,
    avg_speed FLOAT,
    max_speed FLOAT,
    waypoint_count INT DEFAULT 0,

    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- 索引
    INDEX idx_device_started (device_id, started_at DESC),
    INDEX idx_user_started (user_id, started_at DESC)
);

-- 路线轨迹点表（优化：使用 TimescaleDB）
CREATE TABLE route_waypoints (
    route_id UUID REFERENCES routes(route_id),
    location_id UUID REFERENCES locations(location_id),
    sequence_number INT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,

    PRIMARY KEY (route_id, sequence_number),
    INDEX idx_route_timestamp (route_id, timestamp)
);
```

### 4.2 TimescaleDB 优化（可选）

对于高频位置数据，建议将 `locations` 表转换为 TimescaleDB 超表：

```sql
-- 转换为超表
SELECT create_hypertable('locations', 'timestamp');

-- 创建连续聚合（用于快速查询）
CREATE MATERIALIZED VIEW locations_hourly
WITH (timescaledb.continuous) AS
SELECT device_id,
       time_bucket('1 hour', timestamp) AS hour,
       COUNT(*) as location_count,
       AVG(speed) as avg_speed,
       MAX(speed) as max_speed
FROM locations
GROUP BY device_id, hour;

-- 设置数据保留策略
SELECT add_retention_policy('locations', INTERVAL '90 days');
```

## 5. 核心功能实现

### 5.1 地理围栏检测算法

```python
def check_geofence_trigger(location: Location, geofences: List[Geofence]) -> List[GeofenceEvent]:
    """
    检查位置是否触发地理围栏

    算法：
    1. 查询可能相关的围栏（使用空间索引）
    2. 对每个围栏进行精确的几何检测
    3. 对比设备的上一个位置状态
    4. 生成相应的事件（enter/exit/dwell）
    """
    events = []

    for geofence in geofences:
        # 检查是否在活跃时间内
        if not is_geofence_active_now(geofence):
            continue

        # 检查设备是否在目标列表中
        if not is_device_targeted(location.device_id, geofence):
            continue

        # 几何检测
        current_inside = is_point_in_geofence(location.coordinates, geofence.geometry)
        previous_inside = get_previous_status(location.device_id, geofence.geofence_id)

        # 进入事件
        if current_inside and not previous_inside and geofence.trigger_on_enter:
            events.append(create_enter_event(location, geofence))

        # 离开事件
        elif not current_inside and previous_inside and geofence.trigger_on_exit:
            events.append(create_exit_event(location, geofence))

        # 停留事件
        elif current_inside and geofence.trigger_on_dwell:
            dwell_time = get_dwell_time(location.device_id, geofence.geofence_id)
            if dwell_time >= geofence.dwell_time_seconds:
                events.append(create_dwell_event(location, geofence, dwell_time))

        # 更新状态
        update_device_geofence_status(location.device_id, geofence.geofence_id, current_inside)

    return events
```

### 5.2 附近设备查询

```python
async def find_nearby_devices(
    latitude: float,
    longitude: float,
    radius_meters: float,
    user_id: str,
    device_types: Optional[List[str]] = None,
    time_window_minutes: int = 30
) -> List[DeviceLocation]:
    """
    查找指定位置附近的设备

    使用 PostGIS 的地理空间查询
    """
    query = """
        SELECT DISTINCT ON (l.device_id)
            l.device_id,
            l.user_id,
            ST_Y(l.coordinates::geometry) as latitude,
            ST_X(l.coordinates::geometry) as longitude,
            l.timestamp,
            l.accuracy,
            ST_Distance(
                l.coordinates,
                ST_MakePoint($1, $2)::geography
            ) as distance,
            d.device_name,
            d.device_type,
            d.status
        FROM locations l
        INNER JOIN device_service.devices d ON l.device_id = d.device_id
        WHERE
            l.user_id = $3
            AND l.timestamp >= NOW() - INTERVAL '{} minutes'
            AND ST_DWithin(
                l.coordinates,
                ST_MakePoint($1, $2)::geography,
                $4
            )
        ORDER BY l.device_id, l.timestamp DESC
    """.format(time_window_minutes)

    results = await db.fetch(query, longitude, latitude, user_id, radius_meters)
    return [DeviceLocation(**r) for r in results]
```

## 6. 事件集成

### 6.1 发布的事件类型

```python
# 位置更新事件
EventType.LOCATION_UPDATED = "location.updated"

# 地理围栏事件
EventType.GEOFENCE_ENTERED = "location.geofence.entered"
EventType.GEOFENCE_EXITED = "location.geofence.exited"
EventType.GEOFENCE_DWELL = "location.geofence.dwell"

# 移动事件
EventType.DEVICE_STARTED_MOVING = "location.device.started_moving"
EventType.DEVICE_STOPPED = "location.device.stopped"
EventType.SIGNIFICANT_MOVEMENT = "location.significant_movement"

# 低电量位置警报
EventType.LOW_BATTERY_AT_LOCATION = "location.low_battery"
```

### 6.2 与其他服务的事件交互

```
Device Service → Location Service:
  - device.registered → 初始化设备位置追踪
  - device.decommissioned → 停止位置追踪
  - device.status.changed → 更新位置状态

Telemetry Service → Location Service:
  - telemetry.data.received (含位置) → 更新设备位置

Location Service → Notification Service:
  - location.geofence.* → 发送围栏通知
  - location.low_battery → 发送低电量警报

Location Service → Audit Service:
  - location.accessed → 记录位置访问
  - geofence.modified → 记录围栏变更
```

## 7. 性能优化

### 7.1 缓存策略

```python
# Redis 缓存结构
location:device:{device_id}:latest → Location (最新位置，TTL: 1小时)
location:device:{device_id}:geofence_status → Dict[geofence_id, inside] (围栏状态)
location:nearby:{lat}:{lon}:{radius} → List[device_id] (附近设备，TTL: 5分钟)
geofence:{geofence_id} → Geofence (围栏配置，TTL: 1天)
```

### 7.2 批量处理

对于高频位置更新（如车辆追踪），实现批量处理：

```python
# 批量插入位置记录
async def batch_insert_locations(locations: List[Location]):
    # 每批最多1000条
    # 使用 PostgreSQL COPY 命令提高性能
    pass

# 异步地理围栏检测
async def async_check_geofences(location_batch: List[Location]):
    # 使用消息队列（NATS）异步处理
    # 避免阻塞位置更新接口
    pass
```

## 8. 安全和隐私

### 8.1 访问控制

- 用户只能访问自己的设备位置
- 组织管理员可以访问组织内的设备
- 家庭成员间可以通过权限设置共享位置

### 8.2 隐私保护

```python
# 位置模糊化（可选）
def obfuscate_location(location: Location, radius_meters: float = 100) -> Location:
    """将精确位置模糊化到指定半径内的随机点"""
    pass

# 位置历史自动清理
async def cleanup_old_locations(retention_days: int = 90):
    """定期清理超过保留期的位置数据"""
    pass

# 敏感位置标记
def is_sensitive_location(location: Location) -> bool:
    """检测是否为敏感位置（如医院、政府机构等）"""
    pass
```

## 9. 部署配置

```yaml
# docker-compose.yml
services:
  location_service:
    image: isa-location-service:latest
    ports:
      - "8224:8224"
    environment:
      - POSTGRES_HOST=isa-postgres-grpc
      - POSTGRES_PORT=50061
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - NATS_URL=nats://isa-nats:4222
      - CONSUL_HOST=consul
      - CONSUL_PORT=8500
      - ENABLE_GEOFENCING=true
      - ENABLE_ROUTE_TRACKING=true
      - MAX_LOCATION_HISTORY_DAYS=90
      - GEOFENCE_CHECK_INTERVAL_MS=1000
    depends_on:
      - isa-postgres-grpc
      - redis
      - isa-nats
      - consul
    networks:
      - isa_network

# PostGIS 扩展（需要在 PostgreSQL 中启用）
# CREATE EXTENSION postgis;
# CREATE EXTENSION postgis_topology;
```

## 10. 监控指标

```python
# Prometheus 指标
location_updates_total
location_updates_per_second
geofence_triggers_total
geofence_check_duration_seconds
nearby_search_duration_seconds
active_routes_total
location_cache_hit_rate
```

## 11. 未来扩展

1. **室内定位**：支持 WiFi/蓝牙室内定位
2. **轨迹预测**：基于历史数据预测设备移动轨迹
3. **多设备协同定位**：利用多设备位置提高精度
4. **地图服务集成**：集成 Google Maps、OpenStreetMap 等
5. **AR 位置服务**：支持增强现实应用的位置服务
