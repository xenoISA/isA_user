"""
Base Memory Repository
Base class for all memory repositories with common database operations
Uses AsyncPostgresClient with gRPC for PostgreSQL access
"""

import logging
import sys
import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager
from google.protobuf.json_format import MessageToDict

logger = logging.getLogger(__name__)


class BaseMemoryRepository:
    """Base repository class for memory operations"""

    def __init__(self, schema: str = "memory", table_name: str = "memories", config: Optional[ConfigManager] = None):
        """
        Initialize base memory repository with PostgresClient

        Args:
            schema: Database schema name
            table_name: Table name for this memory type
            config: ConfigManager instance for service discovery
        """
        # 使用 config_manager 进行服务发现
        if config is None:
            config = ConfigManager("memory_service")

        # 发现 PostgreSQL 服务
        # 优先级：环境变量 → Consul → localhost fallback
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_GRPC_HOST',
            env_port_key='POSTGRES_GRPC_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(host=host, port=port, user_id='memory_service')
        self.schema = schema
        self.table_name = table_name

    def _clean_protobuf_objects(self, value: Any) -> Any:
        """
        Recursively clean protobuf objects from values
        Converts any remaining protobuf objects to Python native types
        """
        import json

        # Check if it's a protobuf message/descriptor object
        if hasattr(value, 'DESCRIPTOR') or type(value).__module__.startswith('google.protobuf') or type(value).__module__.startswith('google._upb'):
            # Try to convert to dict, or return empty dict/list as appropriate
            try:
                if hasattr(value, 'values'):
                    # It's a list-like proto object
                    values_data = value.values() if callable(value.values) else value.values
                    return [self._clean_protobuf_objects(v) for v in values_data]
                else:
                    # Try MessageToDict or return empty dict
                    try:
                        return MessageToDict(value)
                    except:
                        return {}
            except:
                logger.warning(f"Could not convert protobuf object of type {type(value)}, returning empty dict")
                return {}

        # Handle lists recursively
        elif isinstance(value, list):
            return [self._clean_protobuf_objects(item) for item in value]

        # Handle dicts recursively
        elif isinstance(value, dict):
            return {k: self._clean_protobuf_objects(v) for k, v in value.items()}

        # Return other types as-is
        else:
            return value

    def _deserialize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deserialize row data from PostgreSQL gRPC client
        Converts protobuf objects to Python types
        """
        import json

        if not row:
            return None

        deserialized = {}

        # Fields that are stored as JSON strings and need parsing
        json_fields = {'context', 'conversation_state', 'task_context', 'properties', 'tags'}

        for key, value in row.items():
            if value is None:
                deserialized[key] = None
            # Parse JSON string fields back to dict
            elif key in json_fields and isinstance(value, str):
                try:
                    deserialized[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, keep as string
                    deserialized[key] = value
            # Convert proto ListValue to Python list
            elif hasattr(value, 'values'):
                try:
                    # Check if values is a method or attribute
                    values_data = value.values() if callable(value.values) else value.values
                    deserialized[key] = [
                        MessageToDict(val.struct_value) if hasattr(val, 'struct_value') else val
                        for val in values_data
                    ]
                except (TypeError, AttributeError):
                    # If iteration fails, try to convert directly
                    try:
                        deserialized[key] = list(value) if value else []
                    except TypeError:
                        # If list conversion fails, return empty list for safety
                        logger.warning(f"Could not deserialize field '{key}', setting to empty list")
                        deserialized[key] = []
            # Keep other types as-is (includes lists, strings, numbers, dates)
            else:
                deserialized[key] = value

        # Clean any remaining protobuf objects
        deserialized = self._clean_protobuf_objects(deserialized)

        return deserialized

    def _serialize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize data for PostgreSQL gRPC client
        Converts Python types to PostgreSQL-compatible types
        """
        import json
        serialized = {}

        # Fields that should remain as Python lists for PostgreSQL array types
        array_fields = {
            'participants', 'related_concepts', 'steps', 'prerequisites',
            'related_facts'
        }

        # Fields that should be JSON strings
        json_fields = {'context', 'conversation_state', 'task_context', 'properties', 'tags'}

        for key, value in data.items():
            if value is None:
                serialized[key] = None
            elif isinstance(value, datetime):
                # Convert datetime to ISO string
                serialized[key] = value.isoformat()
            elif isinstance(value, list):
                # Keep as Python list for array fields, convert to JSON for others
                if key in array_fields:
                    serialized[key] = value  # Keep as list for PostgreSQL arrays
                else:
                    # Always serialize lists to JSON, even if empty
                    serialized[key] = json.dumps(value)
            elif isinstance(value, dict):
                # Always convert dicts to JSON string, even if empty
                # Empty dict {} should be '{}' not None
                serialized[key] = json.dumps(value)
            else:
                serialized[key] = value

        return serialized

    async def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new memory record

        Args:
            data: Memory data dictionary

        Returns:
            Created memory record or None
        """
        try:
            # Ensure timestamps
            if 'created_at' not in data:
                data['created_at'] = datetime.now(timezone.utc)
            if 'updated_at' not in data:
                data['updated_at'] = datetime.now(timezone.utc)

            # Serialize data for gRPC
            serialized_data = self._serialize_data(data)

            async with self.db:
                count = await self.db.insert_into(self.table_name, [serialized_data], schema=self.schema)

            if count is not None and count > 0:
                # Retrieve the created record
                return await self.get_by_id(data['id'], data.get('user_id'))
            return None

        except Exception as e:
            logger.error(f"Error creating memory in {self.table_name}: {e}")
            raise

    async def get_by_id(
        self,
        memory_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get memory by ID

        Args:
            memory_id: Memory ID
            user_id: Optional user ID for additional filtering

        Returns:
            Memory record or None
        """
        try:
            if user_id:
                query = f"""
                    SELECT * FROM {self.schema}.{self.table_name}
                    WHERE id = $1 AND user_id = $2
                """
                params = [memory_id, user_id]
            else:
                query = f"""
                    SELECT * FROM {self.schema}.{self.table_name}
                    WHERE id = $1
                """
                params = [memory_id]

            async with self.db:
                result = await self.db.query_row(query, params, schema=self.schema)

            return self._deserialize_row(result)

        except Exception as e:
            logger.error(f"Error getting memory by ID from {self.table_name}: {e}")
            return None

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        List memories for a user with optional filters

        Args:
            user_id: User ID
            limit: Maximum number of records
            offset: Offset for pagination
            filters: Additional filter conditions

        Returns:
            List of memory records
        """
        try:
            conditions = ["user_id = $1"]
            params = [user_id]
            param_count = 1

            # Apply additional filters
            if filters:
                for key, value in filters.items():
                    if value is not None:
                        param_count += 1
                        conditions.append(f"{key} = ${param_count}")
                        params.append(value)

            where_clause = " AND ".join(conditions)
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
            """

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            # Deserialize all rows
            return [self._deserialize_row(row) for row in (results or [])]

        except Exception as e:
            logger.error(f"Error listing memories from {self.table_name}: {e}")
            return []

    async def update(
        self,
        memory_id: str,
        updates: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> bool:
        """
        Update a memory record

        Args:
            memory_id: Memory ID
            updates: Fields to update
            user_id: Optional user ID for additional filtering

        Returns:
            True if updated successfully
        """
        try:
            # Build SET clause dynamically
            set_clauses = []
            params = []
            param_count = 0

            for key, value in updates.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            # Add updated_at
            param_count += 1
            set_clauses.append(f"updated_at = ${param_count}")
            params.append(datetime.now(timezone.utc))

            # Add WHERE conditions
            param_count += 1
            params.append(memory_id)
            memory_id_param = param_count

            if user_id:
                param_count += 1
                params.append(user_id)
                user_id_param = param_count
                where_clause = f"id = ${memory_id_param} AND user_id = ${user_id_param}"
            else:
                where_clause = f"id = ${memory_id_param}"

            set_clause = ", ".join(set_clauses)
            query = f"""
                UPDATE {self.schema}.{self.table_name}
                SET {set_clause}
                WHERE {where_clause}
            """

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            return count > 0

        except Exception as e:
            logger.error(f"Error updating memory in {self.table_name}: {e}")
            raise

    async def delete(
        self,
        memory_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Delete a memory record

        Args:
            memory_id: Memory ID
            user_id: Optional user ID for additional filtering

        Returns:
            True if deleted successfully
        """
        try:
            if user_id:
                query = f"""
                    DELETE FROM {self.schema}.{self.table_name}
                    WHERE id = $1 AND user_id = $2
                """
                params = [memory_id, user_id]
            else:
                query = f"""
                    DELETE FROM {self.schema}.{self.table_name}
                    WHERE id = $1
                """
                params = [memory_id]

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            return count > 0

        except Exception as e:
            logger.error(f"Error deleting memory from {self.table_name}: {e}")
            raise

    async def get_count(self, user_id: str) -> int:
        """
        Get total count of memories for a user

        Args:
            user_id: User ID

        Returns:
            Count of memories
        """
        try:
            query = f"""
                SELECT COUNT(*) as count FROM {self.schema}.{self.table_name}
                WHERE user_id = $1
            """
            params = [user_id]

            async with self.db:
                result = await self.db.query_row(query, params, schema=self.schema)

            return result.get('count', 0) if result else 0

        except Exception as e:
            logger.error(f"Error getting count from {self.table_name}: {e}")
            return 0

    async def check_connection(self) -> bool:
        """
        Check database connection

        Returns:
            True if connected
        """
        try:
            async with self.db:
                result = await self.db.query_row("SELECT 1 as connected", [])
            return result is not None
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False

    async def increment_access_count(
        self,
        memory_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Increment access count for a memory

        Args:
            memory_id: Memory ID
            user_id: Optional user ID for additional filtering

        Returns:
            True if updated successfully
        """
        try:
            if user_id:
                query = f"""
                    UPDATE {self.schema}.{self.table_name}
                    SET access_count = access_count + 1,
                        last_accessed_at = $1
                    WHERE id = $2 AND user_id = $3
                """
                params = [datetime.now(timezone.utc), memory_id, user_id]
            else:
                query = f"""
                    UPDATE {self.schema}.{self.table_name}
                    SET access_count = access_count + 1,
                        last_accessed_at = $1
                    WHERE id = $2
                """
                params = [datetime.now(timezone.utc), memory_id]

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            return count > 0

        except Exception as e:
            logger.error(f"Error incrementing access count: {e}")
            return False
