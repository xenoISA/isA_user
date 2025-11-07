"""
Location Repository
Data access layer for location operations with PostGIS support
"""

import logging
import sys
import os
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
import json
import math

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class LocationRepository:
    """Repository for location operations with PostGIS spatial queries"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize location repository with PostgresClient"""
        # 使用 config_manager 进行服务发现
        if config is None:
            config = ConfigManager("location_service")

        # 发现 PostgreSQL 服务
        # 优先级：环境变量 → Consul → localhost fallback
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = PostgresClient(host=host, port=port, user_id='location_service')

        self.schema = "location"

    # ==================== Location Operations ====================

    async def create_location(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new location record"""
        try:
            # Use simple lat/lon columns (simplified schema, no PostGIS)
            query = f"""
                INSERT INTO {self.schema}.locations (
                    location_id, device_id, user_id,
                    latitude, longitude, accuracy,
                    address, city, state, country,
                    location_method, source, metadata,
                    timestamp, created_at
                ) VALUES (
                    $1, $2, $3,
                    $4, $5, $6,
                    $7, $8, $9, $10,
                    $11, $12, $13,
                    $14, $15
                )
                RETURNING location_id
            """

            params = [
                data['location_id'], data['device_id'], data['user_id'],
                data['latitude'], data['longitude'], data['accuracy'],
                data.get('address'), data.get('city'), data.get('state'), data.get('country'),
                data['location_method'], data['source'],
                json.dumps(data.get('metadata', {})),
                data['timestamp'], data['created_at']
            ]

            with self.db:
                result = self.db.execute(query, params, schema=self.schema)
                logger.debug(f"Location insert result: {result}")

            if result:
                return await self.get_location_by_id(data['location_id'])

            logger.warning(f"Location insert returned no result for location_id: {data['location_id']}")
            return None

        except Exception as e:
            logger.error(f"Error creating location: {e}", exc_info=True)
            raise

    async def get_location_by_id(self, location_id: str) -> Optional[Dict[str, Any]]:
        """Get location by ID"""
        try:
            query = f"""
                SELECT
                    location_id::text, device_id, user_id,
                    latitude::float8, longitude::float8, accuracy::float8,
                    address, city, state, country,
                    location_method, source, metadata,
                    timestamp, created_at
                FROM {self.schema}.locations
                WHERE location_id::text = $1
            """

            with self.db:
                results = self.db.query(query, [location_id], schema=self.schema)

            if results and len(results) > 0:
                return self._deserialize_location(results[0])
            return None

        except Exception as e:
            logger.error(f"Error getting location: {e}")
            return None

    async def get_device_latest_location(
        self,
        device_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get device's latest location"""
        try:
            query = f"""
                SELECT
                    location_id::text, device_id, user_id,
                    latitude::float8, longitude::float8, accuracy::float8,
                    address, city, state, country,
                    location_method, source, metadata,
                    timestamp, created_at
                FROM {self.schema}.locations
                WHERE device_id = $1
                ORDER BY timestamp DESC
                LIMIT 1
            """

            with self.db:
                results = self.db.query(query, [device_id], schema=self.schema)

            if results and len(results) > 0:
                return self._deserialize_location(results[0])
            return None

        except Exception as e:
            logger.error(f"Error getting device latest location: {e}")
            return None

    async def get_device_location_history(
        self,
        device_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get device location history"""
        try:
            conditions = ["device_id = $1"]
            params = [device_id]
            param_idx = 2

            if start_time:
                conditions.append(f"timestamp >= ${param_idx}")
                params.append(start_time)
                param_idx += 1

            if end_time:
                conditions.append(f"timestamp <= ${param_idx}")
                params.append(end_time)
                param_idx += 1

            query = f"""
                SELECT
                    location_id::text, device_id, user_id,
                    latitude::float8, longitude::float8, accuracy::float8,
                    address, city, state, country,
                    location_method, source, metadata,
                    timestamp, created_at
                FROM {self.schema}.locations
                WHERE {' AND '.join(conditions)}
                ORDER BY timestamp DESC
                LIMIT {limit} OFFSET {offset}
            """

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [self._deserialize_location(r) for r in results] if results else []

        except Exception as e:
            logger.error(f"Error getting device location history: {e}")
            return []

    async def find_nearby_devices(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float,
        user_id: str,
        time_window_minutes: int = 30,
        device_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Find devices near a location"""
        try:
            # Get most recent location for each device within time window
            time_threshold = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)

            query = f"""
                WITH latest_locations AS (
                    SELECT DISTINCT ON (device_id)
                        location_id, device_id, user_id,
                        coordinates,
                        ST_Y(coordinates::geometry) as latitude,
                        ST_X(coordinates::geometry) as longitude,
                        timestamp, accuracy
                    FROM {self.schema}.locations
                    WHERE user_id = $1
                        AND timestamp >= $2
                    ORDER BY device_id, timestamp DESC
                )
                SELECT
                    l.device_id,
                    l.user_id,
                    l.latitude,
                    l.longitude,
                    l.timestamp,
                    l.accuracy,
                    ST_Distance(
                        l.coordinates,
                        ST_MakePoint($3, $4)::geography
                    ) as distance
                FROM latest_locations l
                WHERE ST_DWithin(
                    l.coordinates,
                    ST_MakePoint($3, $4)::geography,
                    $5
                )
                ORDER BY distance
                LIMIT {limit}
            """

            params = [user_id, time_threshold, longitude, latitude, radius_meters]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [dict(r) for r in results] if results else []

        except Exception as e:
            logger.error(f"Error finding nearby devices: {e}")
            return []

    async def search_locations_in_radius(
        self,
        center_lat: float,
        center_lon: float,
        radius_meters: float,
        start_time: datetime,
        end_time: datetime,
        device_ids: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search locations within a circular area"""
        try:
            conditions = ["timestamp BETWEEN $1 AND $2"]
            params = [start_time, end_time]
            param_idx = 3

            if device_ids:
                placeholders = ','.join([f'${i}' for i in range(param_idx, param_idx + len(device_ids))])
                conditions.append(f"device_id IN ({placeholders})")
                params.extend(device_ids)
                param_idx += len(device_ids)

            query = f"""
                SELECT
                    location_id, device_id, user_id,
                    ST_Y(coordinates::geometry) as latitude,
                    ST_X(coordinates::geometry) as longitude,
                    altitude, accuracy, heading, speed,
                    address, city, state, country, postal_code,
                    location_method, battery_level, source, metadata,
                    timestamp, created_at,
                    ST_Distance(
                        coordinates,
                        ST_MakePoint(${param_idx}, ${param_idx + 1})::geography
                    ) as distance
                FROM {self.schema}.locations
                WHERE {' AND '.join(conditions)}
                    AND ST_DWithin(
                        coordinates,
                        ST_MakePoint(${param_idx}, ${param_idx + 1})::geography,
                        ${param_idx + 2}
                    )
                ORDER BY timestamp DESC
                LIMIT {limit}
            """

            params.extend([center_lon, center_lat, radius_meters])

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [self._deserialize_location(r) for r in results] if results else []

        except Exception as e:
            logger.error(f"Error searching locations in radius: {e}")
            return []

    # ==================== Geofence Operations ====================

    async def create_geofence(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new geofence"""
        try:
            # Build geometry based on shape type
            geometry_sql = self._build_geometry_sql(data)

            query = f"""
                INSERT INTO {self.schema}.geofences (
                    geofence_id, name, description, user_id, organization_id,
                    shape_type, geometry,
                    active, trigger_on_enter, trigger_on_exit, trigger_on_dwell, dwell_time_seconds,
                    target_devices, target_groups,
                    active_days, active_hours,
                    notification_channels, notification_template,
                    total_triggers, created_at, updated_at, tags, metadata
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, {geometry_sql},
                    $7, $8, $9, $10, $11,
                    $12, $13,
                    $14, $15,
                    $16, $17,
                    $18, $19, $20, $21, $22
                )
                RETURNING geofence_id
            """

            params = self._build_geofence_params(data)

            with self.db:
                result = self.db.execute(query, params, schema=self.schema)

            if result:
                return await self.get_geofence_by_id(data['geofence_id'])
            return None

        except Exception as e:
            logger.error(f"Error creating geofence: {e}")
            raise

    async def get_geofence_by_id(self, geofence_id: str) -> Optional[Dict[str, Any]]:
        """Get geofence by ID"""
        try:
            query = f"""
                SELECT
                    geofence_id, name, description, user_id, organization_id,
                    shape_type,
                    ST_Y(ST_Centroid(geometry::geometry)) as center_lat,
                    ST_X(ST_Centroid(geometry::geometry)) as center_lon,
                    active, trigger_on_enter, trigger_on_exit, trigger_on_dwell, dwell_time_seconds,
                    target_devices, target_groups,
                    active_days, active_hours,
                    notification_channels, notification_template,
                    total_triggers, last_triggered,
                    created_at, updated_at, tags, metadata
                FROM {self.schema}.geofences
                WHERE geofence_id = $1
            """

            with self.db:
                results = self.db.query(query, [geofence_id], schema=self.schema)

            if results and len(results) > 0:
                return self._deserialize_geofence(results[0])
            return None

        except Exception as e:
            logger.error(f"Error getting geofence: {e}")
            return None

    async def list_geofences(
        self,
        user_id: str,
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List geofences for a user"""
        try:
            conditions = ["user_id = $1"]
            params = [user_id]

            if active_only:
                conditions.append("active = true")

            query = f"""
                SELECT
                    geofence_id, name, description, user_id, organization_id,
                    shape_type,
                    ST_Y(ST_Centroid(geometry::geometry)) as center_lat,
                    ST_X(ST_Centroid(geometry::geometry)) as center_lon,
                    active, trigger_on_enter, trigger_on_exit, trigger_on_dwell, dwell_time_seconds,
                    target_devices, target_groups,
                    active_days, active_hours,
                    notification_channels, notification_template,
                    total_triggers, last_triggered,
                    created_at, updated_at, tags, metadata
                FROM {self.schema}.geofences
                WHERE {' AND '.join(conditions)}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
            """

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [self._deserialize_geofence(r) for r in results] if results else []

        except Exception as e:
            logger.error(f"Error listing geofences: {e}")
            return []

    async def update_geofence(
        self,
        geofence_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update geofence"""
        try:
            set_clauses = []
            params = []
            param_idx = 1

            for key, value in updates.items():
                if value is not None:
                    if isinstance(value, (list, dict)):
                        set_clauses.append(f"{key} = ${param_idx}::jsonb")
                        params.append(json.dumps(value))
                    else:
                        set_clauses.append(f"{key} = ${param_idx}")
                        params.append(value)
                    param_idx += 1

            if not set_clauses:
                return False

            set_clauses.append(f"updated_at = ${param_idx}")
            params.append(datetime.now(timezone.utc))
            param_idx += 1

            params.append(geofence_id)

            query = f"""
                UPDATE {self.schema}.geofences
                SET {', '.join(set_clauses)}
                WHERE geofence_id = ${param_idx}
            """

            with self.db:
                self.db.execute(query, params, schema=self.schema)

            return True

        except Exception as e:
            logger.error(f"Error updating geofence: {e}")
            return False

    async def delete_geofence(self, geofence_id: str) -> bool:
        """Delete geofence"""
        try:
            query = f"DELETE FROM {self.schema}.geofences WHERE geofence_id = $1"

            with self.db:
                self.db.execute(query, [geofence_id], schema=self.schema)

            return True

        except Exception as e:
            logger.error(f"Error deleting geofence: {e}")
            return False

    async def check_point_in_geofences(
        self,
        latitude: float,
        longitude: float,
        device_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Check if a point is inside any active geofences"""
        try:
            query = f"""
                SELECT
                    geofence_id, name, shape_type,
                    trigger_on_enter, trigger_on_exit, trigger_on_dwell, dwell_time_seconds,
                    notification_channels
                FROM {self.schema}.geofences
                WHERE user_id = $1
                    AND active = true
                    AND (
                        $2 = ANY(target_devices)
                        OR array_length(target_devices, 1) IS NULL
                        OR array_length(target_devices, 1) = 0
                    )
                    AND ST_Contains(
                        geometry::geometry,
                        ST_MakePoint($3, $4)::geometry
                    )
            """

            params = [user_id, device_id, longitude, latitude]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [dict(r) for r in results] if results else []

        except Exception as e:
            logger.error(f"Error checking point in geofences: {e}")
            return []

    # ==================== Place Operations ====================

    async def create_place(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new place"""
        try:
            query = f"""
                INSERT INTO {self.schema}.places (
                    place_id, user_id, name, category,
                    latitude, longitude, address,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4,
                    $5, $6, $7,
                    $8, $9
                )
                RETURNING place_id
            """

            params = [
                data['place_id'], data['user_id'], data['name'], data['category'],
                data['latitude'], data['longitude'], data.get('address'),
                data['created_at'], data['updated_at']
            ]

            with self.db:
                result = self.db.execute(query, params, schema=self.schema)

            if result:
                return await self.get_place_by_id(data['place_id'])
            return None

        except Exception as e:
            logger.error(f"Error creating place: {e}")
            raise

    async def get_place_by_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Get place by ID"""
        try:
            query = f"""
                SELECT
                    place_id::text, user_id, name, category,
                    latitude::float8, longitude::float8, address,
                    created_at, updated_at
                FROM {self.schema}.places
                WHERE place_id::text = $1
            """

            with self.db:
                results = self.db.query(query, [place_id], schema=self.schema)

            if results and len(results) > 0:
                return self._deserialize_place(results[0])
            return None

        except Exception as e:
            logger.error(f"Error getting place: {e}")
            return None

    async def list_user_places(self, user_id: str) -> List[Dict[str, Any]]:
        """List places for a user"""
        try:
            query = f"""
                SELECT
                    place_id::text, user_id, name, category,
                    latitude::float8, longitude::float8, address,
                    created_at, updated_at
                FROM {self.schema}.places
                WHERE user_id = $1
                ORDER BY created_at DESC
            """

            with self.db:
                results = self.db.query(query, [user_id], schema=self.schema)

            return [self._deserialize_place(r) for r in results] if results else []

        except Exception as e:
            logger.error(f"Error listing places: {e}")
            return []

    async def update_place(self, place_id: str, updates: Dict[str, Any]) -> bool:
        """Update place"""
        try:
            set_clauses = []
            params = []
            param_idx = 1

            for key, value in updates.items():
                if value is not None:
                    if key in ['latitude', 'longitude']:
                        # Handle coordinate updates
                        if 'latitude' in updates and 'longitude' in updates:
                            if key == 'latitude':
                                # Only process once when we have both
                                continue
                            set_clauses.append(f"coordinates = ST_MakePoint(${param_idx}, ${param_idx + 1})::geography")
                            params.append(updates['longitude'])
                            params.append(updates['latitude'])
                            param_idx += 2
                            continue
                    elif isinstance(value, (list, dict)):
                        set_clauses.append(f"{key} = ${param_idx}::jsonb")
                        params.append(json.dumps(value))
                    else:
                        set_clauses.append(f"{key} = ${param_idx}")
                        params.append(value)
                    param_idx += 1

            if not set_clauses:
                return False

            set_clauses.append(f"updated_at = ${param_idx}")
            params.append(datetime.now(timezone.utc))
            param_idx += 1

            params.append(place_id)

            query = f"""
                UPDATE {self.schema}.places
                SET {', '.join(set_clauses)}
                WHERE place_id = ${param_idx}
            """

            with self.db:
                self.db.execute(query, params, schema=self.schema)

            return True

        except Exception as e:
            logger.error(f"Error updating place: {e}")
            return False

    async def delete_place(self, place_id: str) -> bool:
        """Delete place"""
        try:
            query = f"DELETE FROM {self.schema}.places WHERE place_id = $1"

            with self.db:
                self.db.execute(query, [place_id], schema=self.schema)

            return True

        except Exception as e:
            logger.error(f"Error deleting place: {e}")
            return False

    # ==================== Helper Methods ====================

    def _deserialize_location(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize location row"""
        if 'metadata' in row and isinstance(row['metadata'], str):
            row['metadata'] = json.loads(row['metadata'])
        return dict(row)

    def _deserialize_geofence(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize geofence row"""
        for key in ['target_devices', 'target_groups', 'active_days', 'active_hours',
                    'notification_channels', 'tags', 'metadata']:
            if key in row and isinstance(row[key], str):
                row[key] = json.loads(row[key])
        return dict(row)

    def _deserialize_place(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize place row"""
        if 'tags' in row and isinstance(row['tags'], str):
            row['tags'] = json.loads(row['tags'])
        return dict(row)

    def _build_geometry_sql(self, data: Dict[str, Any]) -> str:
        """Build PostGIS geometry SQL based on shape type"""
        shape_type = data['shape_type']

        if shape_type == 'circle':
            # Use ST_Buffer to create a circle
            return "ST_Buffer(ST_MakePoint($7, $8)::geography, $9)"
        elif shape_type == 'polygon':
            # Build polygon from coordinates
            return "ST_MakePolygon(ST_MakeLine(ARRAY[$10]))::geography"
        elif shape_type == 'rectangle':
            # Build rectangle from two corner points
            return "ST_MakeEnvelope($7, $8, $9, $10, 4326)::geography"
        else:
            raise ValueError(f"Unsupported shape type: {shape_type}")

    def _build_geofence_params(self, data: Dict[str, Any]) -> List[Any]:
        """Build parameter list for geofence creation"""
        params = [
            data['geofence_id'],
            data['name'],
            data.get('description'),
            data['user_id'],
            data.get('organization_id'),
            data['shape_type'],
            # Geometry parameters added by _build_geometry_sql
            data.get('active', True),
            data.get('trigger_on_enter', True),
            data.get('trigger_on_exit', True),
            data.get('trigger_on_dwell', False),
            data.get('dwell_time_seconds'),
            json.dumps(data.get('target_devices', [])),
            json.dumps(data.get('target_groups', [])),
            json.dumps(data.get('active_days')),
            json.dumps(data.get('active_hours')),
            json.dumps(data.get('notification_channels', [])),
            data.get('notification_template'),
            0,  # total_triggers
            data['created_at'],
            data['updated_at'],
            json.dumps(data.get('tags', [])),
            json.dumps(data.get('metadata', {}))
        ]

        # Add geometry-specific parameters
        if data['shape_type'] == 'circle':
            params.insert(6, data['center_lon'])
            params.insert(7, data['center_lat'])
            params.insert(8, data['radius'])

        return params

    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula (in meters)"""
        R = 6371000  # Earth's radius in meters

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c
