"""
Weather Service Client

客户端库，供其他微服务调用天气服务
"""

import httpx
from core.service_discovery import get_service_discovery
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class WeatherServiceClient:
    """Weather Service HTTP客户端"""
    
    def __init__(self, base_url: str = None):
        """
        初始化Weather Service客户端
        
        Args:
            base_url: Weather服务的基础URL，默认使用服务发现
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("weather_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8241"
        
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    # =============================================================================
    # Weather Data
    # =============================================================================
    
    async def get_current_weather(
        self,
        location: str,
        units: str = "metric"
    ) -> Optional[Dict[str, Any]]:
        """
        获取当前天气
        
        Args:
            location: 地点名称 (e.g., "New York", "London")
            units: 单位系统 (metric=摄氏度, imperial=华氏度)
        
        Returns:
            天气数据字典
        
        Example:
            >>> client = WeatherServiceClient()
            >>> weather = await client.get_current_weather("New York")
            >>> print(f"Temperature: {weather['temperature']}°C")
            >>> print(f"Condition: {weather['condition']}")
        """
        try:
            params = {
                "location": location,
                "units": units
            }
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/weather/current",
                params=params
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get current weather: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting current weather: {e}")
            return None
    
    async def get_forecast(
        self,
        location: str,
        days: int = 5,
        units: str = "metric"
    ) -> Optional[Dict[str, Any]]:
        """
        获取天气预报
        
        Args:
            location: 地点名称
            days: 预报天数 (1-16)
            units: 单位系统
        
        Returns:
            天气预报数据字典
        
        Example:
            >>> forecast = await client.get_forecast("London", days=7)
            >>> for day in forecast['forecast']:
            ...     print(f"{day['date']}: {day['temp_max']}°C / {day['temp_min']}°C")
        """
        try:
            params = {
                "location": location,
                "days": days,
                "units": units
            }
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/weather/forecast",
                params=params
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get forecast: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting forecast: {e}")
            return None
    
    async def get_weather_alerts(self, location: str) -> Optional[Dict[str, Any]]:
        """
        获取天气预警
        
        Args:
            location: 地点名称
        
        Returns:
            天气预警数据字典
        
        Example:
            >>> alerts = await client.get_weather_alerts("Miami")
            >>> if alerts['alerts']:
            ...     for alert in alerts['alerts']:
            ...         print(f"⚠️ {alert['headline']} ({alert['severity']})")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/weather/alerts",
                params={"location": location}
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get weather alerts: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting weather alerts: {e}")
            return None
    
    # =============================================================================
    # Favorite Locations
    # =============================================================================
    
    async def save_location(
        self,
        user_id: str,
        location: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        is_default: bool = False,
        nickname: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        保存收藏地点
        
        Args:
            user_id: 用户ID
            location: 地点名称
            latitude: 纬度 (可选)
            longitude: 经度 (可选)
            is_default: 是否设为默认地点
            nickname: 昵称 (可选)
        
        Returns:
            保存的地点数据
        
        Example:
            >>> location = await client.save_location(
            ...     user_id="user123",
            ...     location="San Francisco",
            ...     is_default=True,
            ...     nickname="Home"
            ... )
        """
        try:
            data = {
                "user_id": user_id,
                "location": location,
                "latitude": latitude,
                "longitude": longitude,
                "is_default": is_default,
                "nickname": nickname
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/weather/locations",
                json=data
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to save location: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error saving location: {e}")
            return None
    
    async def get_user_locations(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户的收藏地点
        
        Args:
            user_id: 用户ID
        
        Returns:
            地点列表字典
        
        Example:
            >>> result = await client.get_user_locations("user123")
            >>> for loc in result['locations']:
            ...     print(f"{loc['nickname']}: {loc['location']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/weather/locations/{user_id}"
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get user locations: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting user locations: {e}")
            return None
    
    async def delete_location(self, location_id: int, user_id: str) -> bool:
        """
        删除收藏地点
        
        Args:
            location_id: 地点ID
            user_id: 用户ID
        
        Returns:
            是否删除成功
        
        Example:
            >>> success = await client.delete_location(123, "user123")
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/weather/locations/{location_id}",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete location: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deleting location: {e}")
            return False
    
    # =============================================================================
    # Convenience Methods
    # =============================================================================
    
    async def get_weather_summary(self, location: str) -> Optional[Dict[str, Any]]:
        """
        获取天气摘要（当前天气 + 未来预报）
        
        Args:
            location: 地点名称
        
        Returns:
            包含当前天气和预报的综合信息
        
        Example:
            >>> summary = await client.get_weather_summary("Tokyo")
            >>> print(f"Now: {summary['current']['temperature']}°C")
            >>> print(f"Tomorrow: {summary['forecast'][1]['temp_max']}°C")
        """
        try:
            current = await self.get_current_weather(location)
            forecast = await self.get_forecast(location, days=5)
            
            if current and forecast:
                return {
                    "current": current,
                    "forecast": forecast["forecast"],
                    "location": location
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting weather summary: {e}")
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


__all__ = ["WeatherServiceClient"]

