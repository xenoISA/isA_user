"""
Session Repository

Data access layer for session management operations.
Using supabase client for database operations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid

# Database client setup  
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database.supabase_client import get_supabase_client
from .models import Session, SessionMessage, SessionMemory

logger = logging.getLogger(__name__)


class SessionNotFoundException(Exception):
    """Session not found exception"""
    pass


class SessionRepository:
    """Session数据访问层"""
    
    def __init__(self):
        """初始化session仓库"""
        self.supabase = get_supabase_client()
        # 表名定义 - 使用dev schema
        self.sessions_table = "sessions"
    
    async def create_session(self, session_data: Dict[str, Any]) -> Optional[Session]:
        """创建会话"""
        try:
            data = {
                "session_id": session_data.get("session_id"),
                "user_id": session_data.get("user_id"),
                "conversation_data": session_data.get("conversation_data", {}),
                "status": session_data.get("status", "active"),
                "metadata": session_data.get("metadata", {}),
                "is_active": True,
                "message_count": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "session_summary": "",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "last_activity": datetime.now(timezone.utc).isoformat()
            }

            result = self.supabase.table(self.sessions_table).insert(data).execute()

            if result.data:
                return Session.model_validate(result.data[0])
            return None

        except Exception as e:
            logger.error(f"Error creating session: {e}", exc_info=True)
            raise
    
    async def get_by_session_id(self, session_id: str) -> Optional[Session]:
        """根据session_id获取会话"""
        try:
            result = self.supabase.table(self.sessions_table).select("*").eq("session_id", session_id).single().execute()
            
            if result.data:
                return Session.model_validate(result.data)
            return None
                
        except Exception as e:
            if "No rows found" in str(e):
                return None
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
            query = self.supabase.table(self.sessions_table).select("*").eq("user_id", user_id)
            
            if active_only:
                query = query.eq("is_active", True)
            
            query = query.order("created_at", desc=True).limit(limit).offset(offset)
            result = query.execute()
            
            sessions = []
            if result.data:
                for session_data in result.data:
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
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            if status == "ended":
                update_data["is_active"] = False
            
            result = self.supabase.table(self.sessions_table).update(update_data).eq("session_id", session_id).execute()
            
            return len(result.data) > 0
                
        except Exception as e:
            logger.error(f"Error updating session status: {e}")
            return False
    
    async def update_session_activity(self, session_id: str) -> bool:
        """更新会话活动时间"""
        try:
            update_data = {
                "last_activity": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table(self.sessions_table).update(update_data).eq("session_id", session_id).execute()
            
            return len(result.data) > 0
                
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
            
            update_data = {
                "message_count": session.message_count + 1,
                "total_tokens": session.total_tokens + tokens_used,
                "total_cost": session.total_cost + cost_usd,
                "last_activity": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table(self.sessions_table).update(update_data).eq("session_id", session_id).execute()
            
            return len(result.data) > 0
                
        except Exception as e:
            logger.error(f"Error incrementing message count: {e}")
            return False
    
    async def expire_old_sessions(self, hours_old: int = 24) -> int:
        """过期旧会话"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_old)
            
            # 更新过期会话状态
            update_data = {
                "status": "expired",
                "is_active": False,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table(self.sessions_table)\
                .update(update_data)\
                .lt("last_activity", cutoff_time.isoformat())\
                .eq("is_active", True)\
                .execute()
            
            return len(result.data) if result.data else 0
                
        except Exception as e:
            logger.error(f"Error expiring old sessions: {e}")
            return 0


class SessionMessageRepository:
    """Session消息数据访问层"""
    
    def __init__(self):
        """初始化消息仓库"""
        self.supabase = get_supabase_client()
        self.messages_table = "session_messages"
    
    async def create_message(self, message_data: Dict[str, Any]) -> Optional[SessionMessage]:
        """创建消息"""
        try:
            data = {
                # id will be auto-generated by database
                "session_id": message_data.get("session_id"),
                "user_id": message_data.get("user_id"),
                "role": message_data.get("role"),
                "content": message_data.get("content"),
                "message_type": message_data.get("message_type", "chat"),
                "message_metadata": message_data.get("metadata", {}),
                "tokens_used": message_data.get("tokens_used", 0),
                "cost_usd": message_data.get("cost_usd", 0.0),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table(self.messages_table).insert(data).execute()
            
            if result.data:
                # Map database columns to SessionMessage model
                message_dict = {
                    "message_id": result.data[0].get("id"),
                    "session_id": result.data[0].get("session_id"),
                    "user_id": result.data[0].get("user_id"),
                    "role": result.data[0].get("role"),
                    "content": result.data[0].get("content"),
                    "message_type": result.data[0].get("message_type"),
                    "metadata": result.data[0].get("message_metadata", {}),
                    "tokens_used": result.data[0].get("tokens_used", 0),
                    "cost_usd": result.data[0].get("cost_usd", 0.0),
                    "created_at": result.data[0].get("created_at")
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
            query = self.supabase.table(self.messages_table)\
                .select("*")\
                .eq("session_id", session_id)\
                .order("created_at", desc=False)\
                .limit(limit)\
                .offset(offset)
            
            result = query.execute()
            
            messages = []
            if result.data:
                for msg in result.data:
                    # Map database columns to SessionMessage model
                    message_dict = {
                        "message_id": msg.get("id"),
                        "session_id": msg.get("session_id"),
                        "user_id": msg.get("user_id"),
                        "role": msg.get("role"),
                        "content": msg.get("content"),
                        "message_type": msg.get("message_type"),
                        "metadata": msg.get("message_metadata", {}),
                        "tokens_used": msg.get("tokens_used", 0),
                        "cost_usd": msg.get("cost_usd", 0.0),
                        "created_at": msg.get("created_at")
                    }
                    messages.append(SessionMessage.model_validate(message_dict))
            
            return messages
                
        except Exception as e:
            logger.error(f"Error getting session messages: {e}")
            return []


class SessionMemoryRepository:
    """Session记忆数据访问层"""
    
    def __init__(self):
        """初始化记忆仓库"""
        self.supabase = get_supabase_client()
        self.memory_table = "session_memories"
    
    async def create_memory(self, memory_data: Dict[str, Any]) -> Optional[SessionMemory]:
        """创建记忆"""
        try:
            # Map to actual database columns
            data = {
                "session_id": memory_data.get("session_id"),
                "user_id": memory_data.get("user_id"),
                "conversation_summary": memory_data.get("content", ""),
                "session_metadata": memory_data.get("metadata", {}),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table(self.memory_table).insert(data).execute()
            
            if result.data:
                # Map database columns to SessionMemory model
                memory_dict = {
                    "memory_id": result.data[0].get("id"),
                    "session_id": result.data[0].get("session_id"),
                    "user_id": result.data[0].get("user_id"),
                    "memory_type": "conversation",  # default type
                    "content": result.data[0].get("conversation_summary", ""),
                    "metadata": result.data[0].get("session_metadata", {}),
                    "created_at": result.data[0].get("created_at")
                }
                return SessionMemory.model_validate(memory_dict)
            return None
                
        except Exception as e:
            logger.error(f"Error creating memory: {e}")
            return None
    
    async def get_by_session_id(self, session_id: str) -> Optional[SessionMemory]:
        """根据session_id获取记忆"""
        try:
            result = self.supabase.table(self.memory_table)\
                .select("*")\
                .eq("session_id", session_id)\
                .single()\
                .execute()
            
            if result.data:
                # Map database columns to SessionMemory model
                memory_dict = {
                    "memory_id": result.data.get("id"),
                    "session_id": result.data.get("session_id"),
                    "user_id": result.data.get("user_id"),
                    "memory_type": "conversation",  # default type
                    "content": result.data.get("conversation_summary", ""),
                    "metadata": result.data.get("session_metadata", {}),
                    "created_at": result.data.get("created_at")
                }
                return SessionMemory.model_validate(memory_dict)
            return None
                
        except Exception as e:
            if "No rows found" in str(e):
                return None
            logger.error(f"Error getting memory: {e}")
            return None
    
    async def update_memory(self, session_id: str, memory_data: Dict[str, Any]) -> bool:
        """更新记忆"""
        try:
            update_data = {
                "conversation_summary": memory_data.get("content"),
                "session_metadata": memory_data.get("metadata", {}),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table(self.memory_table)\
                .update(update_data)\
                .eq("session_id", session_id)\
                .execute()
            
            return len(result.data) > 0
                
        except Exception as e:
            logger.error(f"Error updating memory: {e}")
            return False