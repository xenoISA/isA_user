"""
Service Clients for Compliance Service

Clients to communicate with other microservices following the pattern.
This allows compliance_service to integrate with audit, account, and storage services.
"""

import logging
import httpx
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class AuditServiceClient:
    """
    Audit Service集成客户端
    用于将合规事件记录到audit_service
    """
    
    def __init__(self, base_url: str = "http://localhost:8203"):
        """
        初始化Audit Service客户端
        
        Args:
            base_url: Audit service的基础URL (默认端口8203)
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=5.0)
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()
    
    async def log_compliance_event(
        self,
        event_type: str,
        user_id: str,
        action: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        severity: str = "medium",
        success: bool = True
    ) -> bool:
        """
        记录合规事件到audit_service
        
        Args:
            event_type: 事件类型 (e.g., "compliance_check")
            user_id: 用户ID
            action: 操作名称
            description: 事件描述
            metadata: 额外元数据
            severity: 严重程度 (low/medium/high/critical)
            success: 是否成功
        
        Returns:
            是否记录成功
        
        Example:
            >>> await audit_client.log_compliance_event(
            ...     event_type="compliance_check",
            ...     user_id="user123",
            ...     action="content_moderation",
            ...     description="Content blocked due to violations",
            ...     metadata={"check_id": "check_123", "risk_level": "high"}
            ... )
        """
        try:
            audit_event = {
                "event_type": event_type,
                "category": "compliance",
                "severity": severity,
                "user_id": user_id,
                "action": action,
                "description": description,
                "success": success,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/audit/events",
                json=audit_event
            )
            
            if response.status_code == 200:
                logger.info(f"Logged compliance event to audit service: {event_type}")
                return True
            else:
                logger.warning(f"Failed to log to audit service: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error logging to audit service: {e}")
            return False


class AccountServiceClient:
    """
    Account Service集成客户端
    用于获取用户信息和验证用户
    """
    
    def __init__(self, base_url: str = "http://localhost:8202"):
        """
        初始化Account Service客户端
        
        Args:
            base_url: Account service的基础URL (默认端口8202)
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=5.0)
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户资料
        
        Args:
            user_id: 用户ID
        
        Returns:
            用户资料信息
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/accounts/{user_id}"
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get user profile: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    async def verify_user_exists(self, user_id: str) -> bool:
        """
        验证用户是否存在
        
        Args:
            user_id: 用户ID
        
        Returns:
            用户是否存在
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/accounts/{user_id}"
            )
            
            return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Error verifying user: {e}")
            return False


class StorageServiceClient:
    """
    Storage Service集成客户端
    用于获取文件信息进行合规检查
    """
    
    def __init__(self, base_url: str = "http://localhost:8209"):
        """
        初始化Storage Service客户端
        
        Args:
            base_url: Storage service的基础URL (默认端口8209)
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()
    
    async def get_file_info(self, file_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息
        
        Args:
            file_id: 文件ID
            user_id: 用户ID
        
        Returns:
            文件信息
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/storage/files/{file_id}",
                headers={"user-id": user_id}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get file info: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None
    
    async def get_file_download_url(self, file_id: str, user_id: str) -> Optional[str]:
        """
        获取文件下载URL（用于内容检查）
        
        Args:
            file_id: 文件ID
            user_id: 用户ID
        
        Returns:
            下载URL
        """
        try:
            file_info = await self.get_file_info(file_id, user_id)
            if file_info:
                return file_info.get("download_url")
            return None
                
        except Exception as e:
            logger.error(f"Error getting download URL: {e}")
            return None


# ==================== 服务客户端管理器 ====================

class ServiceClients:
    """
    服务客户端管理器
    统一管理所有外部服务客户端
    """
    
    def __init__(
        self,
        audit_base_url: str = "http://localhost:8203",
        account_base_url: str = "http://localhost:8202",
        storage_base_url: str = "http://localhost:8209"
    ):
        """
        初始化服务客户端管理器
        
        Args:
            audit_base_url: Audit service URL
            account_base_url: Account service URL
            storage_base_url: Storage service URL
        """
        self.audit = AuditServiceClient(audit_base_url)
        self.account = AccountServiceClient(account_base_url)
        self.storage = StorageServiceClient(storage_base_url)
        
        logger.info("Initialized service clients for compliance service")
    
    async def close_all(self):
        """关闭所有服务客户端"""
        await self.audit.close()
        await self.account.close()
        await self.storage.close()
        logger.info("Closed all service clients")


# ==================== 单例实例 ====================

_service_clients: Optional[ServiceClients] = None

def get_service_clients() -> ServiceClients:
    """
    获取服务客户端管理器实例（单例模式）
    
    Returns:
        ServiceClients实例
    
    Example:
        >>> clients = get_service_clients()
        >>> await clients.audit.log_compliance_event(...)
    """
    global _service_clients
    if _service_clients is None:
        # 这里可以从配置中读取base_url
        # 或者使用service discovery
        _service_clients = ServiceClients()
    return _service_clients

async def close_service_clients():
    """关闭服务客户端管理器"""
    global _service_clients
    if _service_clients:
        await _service_clients.close_all()
        _service_clients = None

