"""
Base Service Client for Internal Microservice Communication

所有微服务客户端的基类，自动处理内部服务认证
"""

import httpx
import logging
from typing import Optional, Dict, Any
from abc import ABC

logger = logging.getLogger(__name__)


class BaseServiceClient(ABC):
    """
    微服务客户端基类

    自动处理：
    1. 服务发现
    2. 内部服务认证
    3. HTTP 客户端管理
    4. 超时控制

    使用示例：
        class AccountServiceClient(BaseServiceClient):
            service_name = "account_service"
            default_port = 8202

            async def get_user(self, user_id: str):
                response = await self.get(f"/api/v1/users/{user_id}")
                return response.json()
    """

    # 子类需要定义这些
    service_name: str = None  # 例如 "account_service"
    default_port: int = None   # 例如 8202

    def __init__(
        self,
        base_url: Optional[str] = None,
        use_internal_auth: bool = True,
        timeout: float = 30.0
    ):
        """
        初始化服务客户端

        Args:
            base_url: 服务基础URL（如果不提供，将使用服务发现）
            use_internal_auth: 是否使用内部服务认证（默认True）
            timeout: 请求超时时间（秒）
        """
        if not self.service_name:
            raise ValueError(f"{self.__class__.__name__} must define 'service_name'")

        # 确定服务 URL
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            self.base_url = self._discover_service()

        # 设置默认 headers
        default_headers = self._build_default_headers(use_internal_auth)

        # 创建 HTTP 客户端
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers=default_headers
        )

        logger.debug(
            f"Initialized {self.service_name} client: {self.base_url} "
            f"(internal_auth={'enabled' if use_internal_auth else 'disabled'})"
        )

    def _discover_service(self) -> str:
        """
        通过服务发现获取服务URL

        Returns:
            服务的基础URL
        """
        try:
            from core.service_discovery import get_service_discovery
            sd = get_service_discovery()
            url = sd.get_service_url(self.service_name)
            logger.debug(f"Discovered {self.service_name} at {url}")
            return url
        except Exception as e:
            # 如果服务发现失败，使用默认localhost
            default_url = f"http://localhost:{self.default_port}" if self.default_port else "http://localhost:8000"
            logger.warning(
                f"Service discovery failed for {self.service_name}, "
                f"using default: {default_url}. Error: {e}"
            )
            return default_url

    def _build_default_headers(self, use_internal_auth: bool) -> Dict[str, str]:
        """
        构建默认请求headers

        Args:
            use_internal_auth: 是否包含内部服务认证

        Returns:
            Headers 字典
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"isA-Internal-Client/{self.service_name}"
        }

        if use_internal_auth:
            from core.internal_service_auth import InternalServiceAuth
            headers.update(InternalServiceAuth.get_internal_service_headers())

        return headers

    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()
        logger.debug(f"Closed {self.service_name} client")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()

    # ========================================
    # HTTP 方法封装
    # ========================================

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """GET 请求"""
        url = f"{self.base_url}{path}"
        response = await self.client.get(url, params=params, headers=headers)
        return response

    async def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """POST 请求"""
        url = f"{self.base_url}{path}"
        response = await self.client.post(url, json=json, data=data, headers=headers)
        return response

    async def put(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """PUT 请求"""
        url = f"{self.base_url}{path}"
        response = await self.client.put(url, json=json, headers=headers)
        return response

    async def delete(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """DELETE 请求"""
        url = f"{self.base_url}{path}"
        response = await self.client.delete(url, headers=headers)
        return response

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            服务是否健康
        """
        try:
            response = await self.get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"{self.service_name} health check failed: {e}")
            return False


__all__ = ["BaseServiceClient"]
