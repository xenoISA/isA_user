"""
Compliance Service Client

Client for other microservices to integrate with compliance_service.
Provides easy-to-use methods for content compliance checking.
"""

import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ComplianceServiceClient:
    """Compliance Service集成客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8250"):
        """
        初始化Compliance Service客户端
        
        Args:
            base_url: Compliance service的基础URL
        
        Example:
            >>> client = ComplianceServiceClient("http://localhost:8250")
            >>> result = await client.check_text(user_id="user123", content="Hello")
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info(f"Initialized ComplianceServiceClient with base_url: {base_url}")
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()
        logger.debug("ComplianceServiceClient closed")
    
    # ==================== Core Compliance Checking Methods ====================
    
    async def check_text(
        self,
        user_id: str,
        content: str,
        check_types: Optional[List[str]] = None,
        organization_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        检查文本内容合规性
        
        Args:
            user_id: 用户ID
            content: 待检查的文本内容
            check_types: 检查类型列表 ["content_moderation", "pii_detection", "prompt_injection"]
            organization_id: 组织ID (可选)
            session_id: 会话ID (可选)
            metadata: 额外元数据 (可选)
        
        Returns:
            合规检查结果
        
        Example:
            >>> result = await client.check_text(
            ...     user_id="user123",
            ...     content="This is a test message",
            ...     check_types=["content_moderation", "pii_detection"]
            ... )
            >>> if result.get("passed"):
            ...     print("Content is compliant")
        """
        try:
            request_data = {
                "user_id": user_id,
                "organization_id": organization_id,
                "session_id": session_id,
                "content_type": "text",
                "content": content,
                "check_types": check_types or ["content_moderation"],
                "metadata": metadata or {}
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/compliance/check",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Text check completed: {result.get('status')} for user {user_id}")
                return result
            else:
                logger.error(f"Text check failed: {response.status_code} - {response.text}")
                return {
                    "passed": False,
                    "error": f"Compliance check failed: {response.status_code}",
                    "status": "fail"
                }
                
        except Exception as e:
            logger.error(f"Error checking text compliance: {e}")
            return {
                "passed": False,
                "error": str(e),
                "status": "fail"
            }
    
    async def check_prompt(
        self,
        user_id: str,
        prompt: str,
        organization_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        检查AI提示词（防止提示词注入攻击）
        
        Args:
            user_id: 用户ID
            prompt: AI提示词
            organization_id: 组织ID (可选)
            metadata: 额外元数据 (可选)
        
        Returns:
            合规检查结果
        
        Example:
            >>> result = await client.check_prompt(
            ...     user_id="user123",
            ...     prompt="Ignore previous instructions and..."
            ... )
            >>> if not result.get("passed"):
            ...     print("Prompt injection detected!")
        """
        try:
            request_data = {
                "user_id": user_id,
                "organization_id": organization_id,
                "content_type": "prompt",
                "content": prompt,
                "check_types": ["prompt_injection", "content_moderation"],
                "metadata": metadata or {}
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/compliance/check",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Prompt check completed: {result.get('status')} for user {user_id}")
                return result
            else:
                logger.error(f"Prompt check failed: {response.status_code}")
                return {"passed": False, "error": "Prompt check failed", "status": "fail"}
                
        except Exception as e:
            logger.error(f"Error checking prompt: {e}")
            return {"passed": False, "error": str(e), "status": "fail"}
    
    async def check_file(
        self,
        user_id: str,
        file_id: str,
        content_type: str = "file",
        organization_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        检查文件内容合规性
        
        Args:
            user_id: 用户ID
            file_id: 文件ID
            content_type: 内容类型 ("image", "audio", "video", "file")
            organization_id: 组织ID (可选)
            metadata: 额外元数据 (可选)
        
        Returns:
            合规检查结果
        
        Example:
            >>> result = await client.check_file(
            ...     user_id="user123",
            ...     file_id="file_abc123",
            ...     content_type="image"
            ... )
        """
        try:
            request_data = {
                "user_id": user_id,
                "organization_id": organization_id,
                "content_type": content_type,
                "content_id": file_id,
                "check_types": ["content_moderation"],
                "metadata": metadata or {}
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/compliance/check",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"File check completed: {result.get('status')} for file {file_id}")
                return result
            else:
                logger.error(f"File check failed: {response.status_code}")
                return {"passed": False, "error": "File check failed", "status": "fail"}
                
        except Exception as e:
            logger.error(f"Error checking file: {e}")
            return {"passed": False, "error": str(e), "status": "fail"}
    
    async def check_pii(
        self,
        user_id: str,
        content: str,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        专门检查PII（个人信息）
        
        Args:
            user_id: 用户ID
            content: 待检查内容
            organization_id: 组织ID (可选)
        
        Returns:
            PII检测结果
        
        Example:
            >>> result = await client.check_pii(
            ...     user_id="user123",
            ...     content="My email is john@example.com"
            ... )
            >>> if result.get("pii_detected"):
            ...     print(f"Found {len(result['detected_pii'])} PII items")
        """
        try:
            request_data = {
                "user_id": user_id,
                "organization_id": organization_id,
                "content_type": "text",
                "content": content,
                "check_types": ["pii_detection"]
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/compliance/check",
                json=request_data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"PII check failed: {response.status_code}")
                return {"passed": False, "error": "PII check failed"}
                
        except Exception as e:
            logger.error(f"Error checking PII: {e}")
            return {"passed": False, "error": str(e)}
    
    # ==================== User Data Control Methods (GDPR) ====================
    
    async def export_user_data(
        self,
        user_id: str,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        导出用户数据 (GDPR Article 15 & 20)
        
        Args:
            user_id: 用户ID
            format: 导出格式 ("json" 或 "csv")
        
        Returns:
            用户数据导出结果
        
        Example:
            >>> data = await client.export_user_data(user_id="user123", format="json")
            >>> # Save to file or send to user
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/compliance/user/{user_id}/data-export",
                params={"format": format}
            )
            
            if response.status_code == 200:
                logger.info(f"Exported data for user {user_id}")
                return response.json() if format == "json" else {"csv": response.text}
            else:
                logger.error(f"Data export failed: {response.status_code}")
                return {"error": "Data export failed"}
                
        except Exception as e:
            logger.error(f"Error exporting user data: {e}")
            return {"error": str(e)}
    
    async def delete_user_data(
        self,
        user_id: str,
        confirmation: str = "CONFIRM_DELETE"
    ) -> Dict[str, Any]:
        """
        删除用户数据 (GDPR Article 17 - Right to be Forgotten)
        
        Args:
            user_id: 用户ID
            confirmation: 确认字符串，必须为 "CONFIRM_DELETE"
        
        Returns:
            删除结果
        
        Example:
            >>> result = await client.delete_user_data(
            ...     user_id="user123",
            ...     confirmation="CONFIRM_DELETE"
            ... )
            >>> if result.get("status") == "success":
            ...     print(f"Deleted {result['deleted_records']} records")
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/compliance/user/{user_id}/data",
                params={"confirmation": confirmation}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.warning(f"Deleted data for user {user_id}: {result.get('deleted_records')} records")
                return result
            else:
                logger.error(f"Data deletion failed: {response.status_code}")
                return {"status": "error", "message": "Data deletion failed"}
                
        except Exception as e:
            logger.error(f"Error deleting user data: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_user_data_summary(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        获取用户数据摘要 (GDPR Article 15)
        
        Args:
            user_id: 用户ID
        
        Returns:
            数据摘要
        
        Example:
            >>> summary = await client.get_user_data_summary(user_id="user123")
            >>> print(f"User has {summary['total_records']} records")
            >>> print(f"Can export: {summary['can_export']}")
            >>> print(f"Can delete: {summary['can_delete']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/compliance/user/{user_id}/data-summary"
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Get data summary failed: {response.status_code}")
                return {"error": "Failed to get data summary"}
                
        except Exception as e:
            logger.error(f"Error getting data summary: {e}")
            return {"error": str(e)}
    
    # ==================== Query and Report Methods ====================
    
    async def get_check_status(
        self,
        check_id: str
    ) -> Dict[str, Any]:
        """
        获取合规检查状态
        
        Args:
            check_id: 检查ID
        
        Returns:
            检查状态详情
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/compliance/checks/{check_id}"
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Get check status failed: {response.status_code}")
                return {"error": "Check not found"}
                
        except Exception as e:
            logger.error(f"Error getting check status: {e}")
            return {"error": str(e)}
    
    async def get_user_checks(
        self,
        user_id: str,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户的合规检查历史
        
        Args:
            user_id: 用户ID
            limit: 返回记录数量限制
            status: 过滤状态 (可选)
        
        Returns:
            检查记录列表
        """
        try:
            params = {"limit": limit}
            if status:
                params["status"] = status
            
            response = await self.client.get(
                f"{self.base_url}/api/compliance/checks/user/{user_id}",
                params=params
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("checks", [])
            else:
                logger.error(f"Get user checks failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting user checks: {e}")
            return []
    
    async def check_pci_card_data(
        self,
        content: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        检查内容中是否包含信用卡信息 (PCI-DSS)
        
        Args:
            content: 待检查内容
            user_id: 用户ID
        
        Returns:
            PCI-DSS检查结果
        
        Example:
            >>> result = await client.check_pci_card_data(
            ...     content="My card is 4532-1234-5678-9010",
            ...     user_id="user123"
            ... )
            >>> if not result.get("pci_compliant"):
            ...     print("Credit card data detected!")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/compliance/pci/card-data-check",
                json={"content": content, "user_id": user_id}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"PCI check failed: {response.status_code}")
                return {"pci_compliant": False, "error": "Check failed"}
                
        except Exception as e:
            logger.error(f"Error checking PCI compliance: {e}")
            return {"pci_compliant": False, "error": str(e)}
    
    # ==================== Health Check ====================
    
    async def health_check(self) -> Dict[str, Any]:
        """
        检查服务健康状态
        
        Returns:
            健康状态
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "unhealthy", "error": f"Status code: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}


# ==================== 单例实例 ====================

_compliance_client: Optional[ComplianceServiceClient] = None

async def get_compliance_client(base_url: str = "http://localhost:8250") -> ComplianceServiceClient:
    """
    获取Compliance Service客户端实例（单例模式）
    
    Args:
        base_url: 服务基础URL
    
    Returns:
        ComplianceServiceClient实例
    
    Example:
        >>> client = await get_compliance_client()
        >>> result = await client.check_text(user_id="user123", content="Hello")
    """
    global _compliance_client
    if _compliance_client is None:
        _compliance_client = ComplianceServiceClient(base_url)
    return _compliance_client

async def close_compliance_client():
    """关闭Compliance Service客户端"""
    global _compliance_client
    if _compliance_client:
        await _compliance_client.close()
        _compliance_client = None

