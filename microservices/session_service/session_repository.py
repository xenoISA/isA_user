"""
Session Repository

Data access layer for session management operations.
Using supabase client for database operations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import json

# Database client setup  
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager
from .models import Session, SessionMessage

logger = logging.getLogger(__name__)


class SessionNotFoundException(Exception):
    """Session not found exception"""
    pass


class SessionRepository:
    """Session数据访问层"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """初始化session仓库"""
        # Use config_manager for service discovery
        if config is None:
            config = ConfigManager("session_service")

        # Discover PostgreSQL service
        # Priority: environment variable → Consul → localhost fallback
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            user_id='session_service'
        )
        self.schema = "session"
        self.sessions_table = "sessions"
    
    async def create_session(self, session_data: Dict[str, Any]) -> Optional[Session]:
        """创建会话"""
        try:
            data = {
                "session_id": session_data.get("session_id"),
                "user_id": session_data.get("user_id"),
                "conversation_data": session_data.get("conversation_data") or {},
                "status": session_data.get("status", "active"),
                "metadata": session_data.get("metadata") or {},
                "is_active": True,
                "message_count": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "session_summary": "",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "last_activity": datetime.now(timezone.utc).isoformat()
            }

            async with self.db:
                count = await self.db.insert_into(
                    self.sessions_table,
                    [data],
                    schema=self.schema
                )

            # Check if insert succeeded
            if count is not None and count > 0:
                return await self.get_by_session_id(data["session_id"])

            # Insert returned None or 0, check if record exists anyway
            return await self.get_by_session_id(data["session_id"])

        except Exception as e:
            logger.error(f"Error creating session: {e}", exc_info=True)
            raise
    
    async def get_by_session_id(self, session_id: str) -> Optional[Session]:
        """根据session_id获取会话"""
        try:
            query = f"SELECT * FROM {self.schema}.{self.sessions_table} WHERE session_id = $1"
            params = [session_id]

            async with self.db:
                result = await self.db.query_row(query, params, schema=self.schema)

            if result:
                return Session.model_validate(result)
            return None

        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None
    
    async def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Session]:
        """获取用户的会话列表"""
        try:
            conditions = ["user_id = $1"]
            params = [user_id]
            param_count = 1

            if active_only:
                param_count += 1
                conditions.append(f"is_active = ${param_count}")
                params.append(True)

            where_clause = " AND ".join(conditions)
            query = f"""
                SELECT * FROM {self.schema}.{self.sessions_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
            """

            async with self.db:
                result = await self.db.query(query, params, schema=self.schema)

            sessions = []
            if result:
                for session_data in result:
                    sessions.append(Session.model_validate(session_data))

            return sessions

        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []
    
    async def update_session_status(self, session_id: str, status: str) -> bool:
        """更新会话状态"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc)
            }

            if status == "ended":
                update_data["is_active"] = False

            set_clauses = []
            params = []
            param_count = 0

            for key, value in update_data.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            # Add WHERE condition
            param_count += 1
            params.append(session_id)

            set_clause = ", ".join(set_clauses)
            query = f"""
                UPDATE {self.schema}.{self.sessions_table}
                SET {set_clause}
                WHERE session_id = ${param_count}
            """

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating session status: {e}")
            return False
    
    async def update_session_activity(self, session_id: str) -> bool:
        """更新会话活动时间"""
        try:
            now = datetime.now(timezone.utc)
            query = f"""
                UPDATE {self.schema}.{self.sessions_table}
                SET last_activity = $1, updated_at = $2
                WHERE session_id = $3
            """
            params = [now, now, session_id]

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating session activity: {e}")
            return False
    
    async def increment_message_count(self, session_id: str, tokens_used: int = 0, cost_usd: float = 0.0) -> bool:
        """增加消息计数和统计信息"""
        try:
            # 首先获取当前会话
            session = await self.get_by_session_id(session_id)
            if not session:
                return False

            now = datetime.now(timezone.utc)
            query = f"""
                UPDATE {self.schema}.{self.sessions_table}
                SET message_count = $1,
                    total_tokens = $2,
                    total_cost = $3,
                    last_activity = $4,
                    updated_at = $5
                WHERE session_id = $6
            """
            params = [
                session.message_count + 1,
                session.total_tokens + tokens_used,
                session.total_cost + cost_usd,
                now,
                now,
                session_id
            ]

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error incrementing message count: {e}")
            return False
    
    async def expire_old_sessions(self, hours_old: int = 24) -> int:
        """过期旧会话"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_old)
            now = datetime.now(timezone.utc)

            query = f"""
                UPDATE {self.schema}.{self.sessions_table}
                SET status = $1, is_active = $2, updated_at = $3
                WHERE last_activity < $4 AND is_active = $5
            """
            params = ["expired", False, now, cutoff_time, True]

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            return count if count is not None else 0

        except Exception as e:
            logger.error(f"Error expiring old sessions: {e}")
            return 0


class SessionMessageRepository:
    """Session消息数据访问层"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """初始化消息仓库"""
        # Use config_manager for service discovery
        if config is None:
            config = ConfigManager("session_service")

        # Discover PostgreSQL service
        # Priority: environment variable → Consul → localhost fallback
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"SessionMessageRepository connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            user_id='session_service'
        )
        self.schema = "session"
        self.messages_table = "session_messages"
    
    async def create_message(self, message_data: Dict[str, Any]) -> Optional[SessionMessage]:
        """创建消息"""
        try:
            # Generate UUID for message
            message_id = str(uuid.uuid4())

            data = {
                "id": message_id,  # UUID id
                "session_id": message_data.get("session_id"),
                "user_id": message_data.get("user_id"),
                "role": message_data.get("role"),
                "content": message_data.get("content"),
                "message_type": message_data.get("message_type", "chat"),
                "message_metadata": message_data.get("metadata") or {},  # Actual column name
                "tokens_used": message_data.get("tokens_used", 0),
                "cost_usd": message_data.get("cost_usd", 0.0),
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            async with self.db:
                count = await self.db.insert_into(
                    self.messages_table,
                    [data],
                    schema=self.schema
                )

            if count is not None and count > 0:
                # Query the inserted message
                query = f"SELECT * FROM {self.schema}.{self.messages_table} WHERE id = $1"
                async with self.db:
                    result = await self.db.query_row(query, [message_id], schema=self.schema)

                if result:
                    # Map database columns to SessionMessage model
                    message_dict = {
                        "message_id": result.get("id"),  # UUID id as message_id
                        "session_id": result.get("session_id"),
                        "user_id": result.get("user_id"),
                        "role": result.get("role"),
                        "content": result.get("content"),
                        "message_type": result.get("message_type"),
                        "metadata": result.get("message_metadata") or {},  # Actual column name
                        "tokens_used": result.get("tokens_used", 0),
                        "cost_usd": result.get("cost_usd", 0.0),
                        "created_at": result.get("created_at")
                    }
                    return SessionMessage.model_validate(message_dict)

            return None

        except Exception as e:
            logger.error(f"Error creating message: {e}")
            return None
    
    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[SessionMessage]:
        """获取会话消息"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.messages_table}
                WHERE session_id = $1
                ORDER BY created_at ASC
                LIMIT {limit} OFFSET {offset}
            """
            params = [session_id]

            async with self.db:
                result = await self.db.query(query, params, schema=self.schema)

            messages = []
            if result:
                for msg in result:
                    # Map database columns to SessionMessage model
                    message_dict = {
                        "message_id": msg.get("id"),  # UUID id column
                        "session_id": msg.get("session_id"),
                        "user_id": msg.get("user_id"),
                        "role": msg.get("role"),
                        "content": msg.get("content"),
                        "message_type": msg.get("message_type"),
                        "metadata": msg.get("message_metadata") or {},  # Actual column name
                        "tokens_used": msg.get("tokens_used", 0),
                        "cost_usd": msg.get("cost_usd", 0.0),
                        "created_at": msg.get("created_at")
                    }
                    messages.append(SessionMessage.model_validate(message_dict))

            return messages

        except Exception as e:
            logger.error(f"Error getting session messages: {e}")
            return []