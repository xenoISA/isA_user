"""
Calendar Service Client

客户端库，供其他微服务调用日历服务
"""

import httpx
from core.service_discovery import get_service_discovery
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CalendarServiceClient:
    """Calendar Service HTTP客户端"""
    
    def __init__(self, base_url: str = None):
        """
        初始化Calendar Service客户端
        
        Args:
            base_url: Calendar服务的基础URL，默认使用服务发现
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("calendar_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8240"
        
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    # =============================================================================
    # Event Management
    # =============================================================================
    
    async def create_event(
        self,
        user_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        category: str = "other",
        all_day: bool = False,
        reminders: List[int] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        创建日历事件
        
        Args:
            user_id: 用户ID
            title: 事件标题
            start_time: 开始时间
            end_time: 结束时间
            description: 事件描述
            location: 地点
            category: 分类 (work, personal, meeting, etc.)
            all_day: 是否全天事件
            reminders: 提醒时间列表（分钟）
            **kwargs: 其他可选参数
        
        Returns:
            事件数据字典
        
        Example:
            >>> client = CalendarServiceClient()
            >>> event = await client.create_event(
            ...     user_id="user123",
            ...     title="Team Meeting",
            ...     start_time=datetime(2025, 10, 23, 10, 0),
            ...     end_time=datetime(2025, 10, 23, 11, 0),
            ...     category="meeting",
            ...     reminders=[15, 60]  # 15 min and 1 hour before
            ... )
        """
        try:
            data = {
                "user_id": user_id,
                "title": title,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "description": description,
                "location": location,
                "category": category,
                "all_day": all_day,
                "reminders": reminders or [],
                **kwargs
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/calendar/events",
                json=data
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create event: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return None
    
    async def get_event(self, event_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取事件详情
        
        Args:
            event_id: 事件ID
            user_id: 用户ID（可选，用于权限验证）
        
        Returns:
            事件数据字典
        
        Example:
            >>> event = await client.get_event("evt_abc123")
        """
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/calendar/events/{event_id}",
                params=params
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get event: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting event: {e}")
            return None
    
    async def list_events(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        查询事件列表
        
        Args:
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期
            category: 分类过滤
            limit: 每页数量
            offset: 偏移量
        
        Returns:
            包含events列表和分页信息的字典
        
        Example:
            >>> result = await client.list_events(
            ...     user_id="user123",
            ...     start_date=datetime(2025, 10, 1),
            ...     end_date=datetime(2025, 10, 31),
            ...     category="meeting"
            ... )
            >>> events = result["events"]
        """
        try:
            params = {
                "user_id": user_id,
                "limit": limit,
                "offset": offset
            }
            
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()
            if category:
                params["category"] = category
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/calendar/events",
                params=params
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list events: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing events: {e}")
            return None
    
    async def update_event(
        self,
        event_id: str,
        user_id: Optional[str] = None,
        **updates
    ) -> Optional[Dict[str, Any]]:
        """
        更新事件
        
        Args:
            event_id: 事件ID
            user_id: 用户ID（可选，用于权限验证）
            **updates: 要更新的字段
        
        Returns:
            更新后的事件数据
        
        Example:
            >>> event = await client.update_event(
            ...     event_id="evt_abc123",
            ...     title="Updated Meeting Title",
            ...     location="Conference Room B"
            ... )
        """
        try:
            # Serialize datetime fields
            for key, value in updates.items():
                if isinstance(value, datetime):
                    updates[key] = value.isoformat()
            
            params = {}
            if user_id:
                params["user_id"] = user_id
            
            response = await self.client.put(
                f"{self.base_url}/api/v1/calendar/events/{event_id}",
                json=updates,
                params=params
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update event: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error updating event: {e}")
            return None
    
    async def delete_event(self, event_id: str, user_id: Optional[str] = None) -> bool:
        """
        删除事件
        
        Args:
            event_id: 事件ID
            user_id: 用户ID（可选，用于权限验证）
        
        Returns:
            是否删除成功
        
        Example:
            >>> success = await client.delete_event("evt_abc123")
        """
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id
            
            response = await self.client.delete(
                f"{self.base_url}/api/v1/calendar/events/{event_id}",
                params=params
            )
            response.raise_for_status()
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete event: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return False
    
    # =============================================================================
    # Query Methods
    # =============================================================================
    
    async def get_upcoming_events(self, user_id: str, days: int = 7) -> Optional[List[Dict[str, Any]]]:
        """
        获取即将到来的事件
        
        Args:
            user_id: 用户ID
            days: 向前查询的天数
        
        Returns:
            事件列表
        
        Example:
            >>> upcoming = await client.get_upcoming_events("user123", days=7)
            >>> for event in upcoming:
            ...     print(f"{event['title']} at {event['start_time']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/calendar/upcoming",
                params={"user_id": user_id, "days": days}
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get upcoming events: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting upcoming events: {e}")
            return None
    
    async def get_today_events(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取今天的事件
        
        Args:
            user_id: 用户ID
        
        Returns:
            今天的事件列表
        
        Example:
            >>> today = await client.get_today_events("user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/calendar/today",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get today's events: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting today's events: {e}")
            return None
    
    # =============================================================================
    # External Calendar Sync
    # =============================================================================
    
    async def sync_external_calendar(
        self,
        user_id: str,
        provider: str,
        credentials: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        同步外部日历
        
        Args:
            user_id: 用户ID
            provider: 日历提供商 (google_calendar, apple_calendar, outlook)
            credentials: OAuth凭证
        
        Returns:
            同步状态
        
        Example:
            >>> status = await client.sync_external_calendar(
            ...     user_id="user123",
            ...     provider="google_calendar",
            ...     credentials={"access_token": "..."}
            ... )
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/calendar/sync",
                params={"user_id": user_id, "provider": provider},
                json=credentials or {}
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to sync calendar: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error syncing calendar: {e}")
            return None
    
    async def get_sync_status(
        self,
        user_id: str,
        provider: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取同步状态
        
        Args:
            user_id: 用户ID
            provider: 日历提供商（可选）
        
        Returns:
            同步状态
        
        Example:
            >>> status = await client.get_sync_status("user123", "google_calendar")
        """
        try:
            params = {"user_id": user_id}
            if provider:
                params["provider"] = provider
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/calendar/sync/status",
                params=params
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get sync status: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return None
    
    # =============================================================================
    # Health Check
    # =============================================================================
    
    async def health_check(self) -> bool:
        """
        检查服务健康状态
        
        Returns:
            服务是否健康
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False


__all__ = ["CalendarServiceClient"]

