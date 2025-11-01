"""
Weather Repository

天气数据访问层 - PostgreSQL + gRPC
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient
from .models import FavoriteLocation

logger = logging.getLogger(__name__)


class WeatherRepository:
    """天气数据访问层 - PostgreSQL"""

    def __init__(self):
        self.db = PostgresClient(
            host=os.getenv("POSTGRES_GRPC_HOST", "isa-postgres-grpc"),
            port=int(os.getenv("POSTGRES_GRPC_PORT", "50061")),
            user_id="weather_service"
        )
        self.schema = "weather"
        self.locations_table = "weather_locations"
        self.cache_table = "weather_cache"
        self.alerts_table = "weather_alerts"

        # Try to initialize Redis for caching
        self.redis = None
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis = redis.from_url(redis_url, decode_responses=True)
            logger.info("Redis cache initialized")
        except Exception as e:
            logger.warning(f"Redis not available, using database cache: {e}")

    # =============================================================================
    # Cache Operations
    # =============================================================================

    async def get_cached_weather(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """从缓存获取天气数据"""
        try:
            # Try Redis first
            if self.redis:
                cached = self.redis.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit (Redis): {cache_key}")
                    return json.loads(cached)

            # Fallback to database cache
            query = f'''
                SELECT data FROM {self.schema}.{self.cache_table}
                WHERE cache_key = $1 AND expires_at >= $2
            '''

            with self.db:
                results = self.db.query(query, [cache_key, datetime.now(timezone.utc)], schema=self.schema)

            if results and len(results) > 0:
                logger.debug(f"Cache hit (DB): {cache_key}")
                return results[0].get("data")

            logger.debug(f"Cache miss: {cache_key}")
            return None

        except Exception as e:
            logger.error(f"Error reading cache: {e}")
            return None

    async def set_cached_weather(self, cache_key: str, data: Dict[str, Any],
                                 ttl_seconds: int = 900) -> bool:
        """缓存天气数据"""
        try:
            # Cache in Redis
            if self.redis:
                self.redis.setex(
                    cache_key,
                    ttl_seconds,
                    json.dumps(data)
                )
                logger.debug(f"Cached in Redis: {cache_key} (TTL: {ttl_seconds}s)")

            # Also cache in database as backup
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            now = datetime.now(timezone.utc)

            # Upsert using INSERT ... ON CONFLICT
            query = f'''
                INSERT INTO {self.schema}.{self.cache_table} (
                    cache_key, location, data, cached_at, expires_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (cache_key) DO UPDATE
                SET location = EXCLUDED.location,
                    data = EXCLUDED.data,
                    cached_at = EXCLUDED.cached_at,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = EXCLUDED.updated_at
            '''

            params = [
                cache_key,
                data.get("location", ""),
                json.dumps(data),
                now,
                expires_at,
                now,
                now
            ]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            logger.debug(f"Cached in DB: {cache_key}")
            return count is not None and count >= 0

        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False

    async def clear_location_cache(self, location: str):
        """清除特定地点的所有缓存"""
        try:
            if self.redis:
                # Delete Redis keys matching location
                pattern = f"weather:*:{location}:*"
                for key in self.redis.scan_iter(match=pattern):
                    self.redis.delete(key)

            # Delete from database cache
            query = f'''
                DELETE FROM {self.schema}.{self.cache_table}
                WHERE cache_key LIKE $1
            '''

            with self.db:
                self.db.execute(query, [f"%{location}%"], schema=self.schema)

            logger.info(f"Cleared cache for location: {location}")

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

    # =============================================================================
    # Favorite Locations
    # =============================================================================

    async def save_location(self, location_data: Dict[str, Any]) -> Optional[FavoriteLocation]:
        """保存收藏地点"""
        try:
            # If setting as default, unset other defaults first
            if location_data.get("is_default", False):
                update_query = f'''
                    UPDATE {self.schema}.{self.locations_table}
                    SET is_default = FALSE, updated_at = $1
                    WHERE user_id = $2
                '''
                with self.db:
                    self.db.execute(update_query, [datetime.now(timezone.utc), location_data["user_id"]], schema=self.schema)

            # Insert new location
            query = f'''
                INSERT INTO {self.schema}.{self.locations_table} (
                    user_id, location, latitude, longitude, is_default, nickname, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
            '''

            now = datetime.now(timezone.utc)
            params = [
                location_data["user_id"],
                location_data["location"],
                location_data.get("latitude"),
                location_data.get("longitude"),
                location_data.get("is_default", False),
                location_data.get("nickname"),
                now,
                now
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                return FavoriteLocation(**results[0])
            return None

        except Exception as e:
            logger.error(f"Failed to save location: {e}", exc_info=True)
            return None

    async def get_user_locations(self, user_id: str) -> List[FavoriteLocation]:
        """获取用户的收藏地点"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.locations_table}
                WHERE user_id = $1
                ORDER BY is_default DESC, created_at DESC
            '''

            with self.db:
                results = self.db.query(query, [user_id], schema=self.schema)

            if results:
                return [FavoriteLocation(**loc) for loc in results]
            return []

        except Exception as e:
            logger.error(f"Failed to get user locations: {e}")
            return []

    async def get_default_location(self, user_id: str) -> Optional[FavoriteLocation]:
        """获取用户的默认地点"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.locations_table}
                WHERE user_id = $1 AND is_default = TRUE
                LIMIT 1
            '''

            with self.db:
                results = self.db.query(query, [user_id], schema=self.schema)

            if results and len(results) > 0:
                return FavoriteLocation(**results[0])
            return None

        except Exception as e:
            logger.error(f"Failed to get default location: {e}")
            return None

    async def delete_location(self, location_id: int, user_id: str) -> bool:
        """删除收藏地点"""
        try:
            query = f'''
                DELETE FROM {self.schema}.{self.locations_table}
                WHERE id = $1 AND user_id = $2
            '''

            with self.db:
                count = self.db.execute(query, [location_id, user_id], schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to delete location: {e}")
            return False

    # =============================================================================
    # Weather Alerts
    # =============================================================================

    async def save_alert(self, alert_data: Dict[str, Any]) -> bool:
        """保存天气预警"""
        try:
            # Handle datetime serialization
            start_time = alert_data["start_time"]
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))

            end_time = alert_data["end_time"]
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

            query = f'''
                INSERT INTO {self.schema}.{self.alerts_table} (
                    location, alert_type, severity, headline, description,
                    start_time, end_time, source, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            '''

            now = datetime.now(timezone.utc)
            params = [
                alert_data["location"],
                alert_data["alert_type"],
                alert_data["severity"],
                alert_data["headline"],
                alert_data.get("description", ""),
                start_time,
                end_time,
                alert_data["source"],
                now,
                now
            ]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to save alert: {e}", exc_info=True)
            return False

    async def get_active_alerts(self, location: str) -> List[Dict[str, Any]]:
        """获取活跃的天气预警"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                SELECT * FROM {self.schema}.{self.alerts_table}
                WHERE location = $1 AND end_time >= $2
                ORDER BY severity DESC
            '''

            with self.db:
                results = self.db.query(query, [location, now], schema=self.schema)

            if results:
                return results
            return []

        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []


__all__ = ["WeatherRepository"]
