"""
Internal Service Authentication Middleware

用于微服务间通信的内部认证机制
允许服务间调用绕过常规的用户认证

使用方式:
1. 在服务端添加中间件来识别内部服务请求
2. 在客户端发送请求时添加内部服务标识 header
"""

from fastapi import Request, HTTPException, status
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

# 内部服务认证密钥（从环境变量读取，生产环境必须设置）
INTERNAL_SERVICE_SECRET = os.getenv("INTERNAL_SERVICE_SECRET", "dev-internal-secret-change-in-production")
INTERNAL_SERVICE_HEADER = "X-Internal-Service"
INTERNAL_SERVICE_SECRET_HEADER = "X-Internal-Service-Secret"


class InternalServiceAuth:
    """内部服务认证工具类"""

    @staticmethod
    def get_internal_service_headers() -> dict:
        """
        获取内部服务认证 headers

        用于客户端发送请求时添加

        Returns:
            包含内部服务认证信息的 headers 字典
        """
        return {
            INTERNAL_SERVICE_HEADER: "true",
            INTERNAL_SERVICE_SECRET_HEADER: INTERNAL_SERVICE_SECRET
        }

    @staticmethod
    def is_internal_service_request(request: Request) -> bool:
        """
        检查请求是否来自内部服务

        验证条件：
        1. 包含 X-Internal-Service: true header
        2. 包含正确的 X-Internal-Service-Secret header

        Args:
            request: FastAPI Request 对象

        Returns:
            True 如果是有效的内部服务请求
        """
        internal_service = request.headers.get(INTERNAL_SERVICE_HEADER)
        secret = request.headers.get(INTERNAL_SERVICE_SECRET_HEADER)

        if internal_service == "true" and secret == INTERNAL_SERVICE_SECRET:
            logger.debug("Valid internal service request detected")
            return True

        return False

    @staticmethod
    def get_service_user_id() -> str:
        """
        获取服务调用的 user_id

        Returns:
            内部服务使用的 user_id
        """
        return "internal-service"


async def require_auth_or_internal_service(request: Request) -> Optional[str]:
    """
    认证中间件依赖函数

    允许两种认证方式：
    1. 常规用户认证（user-id header）
    2. 内部服务认证（X-Internal-Service headers）

    Args:
        request: FastAPI Request 对象

    Returns:
        user_id: 用户ID 或 "internal-service"

    Raises:
        HTTPException: 401 如果认证失败

    用法:
        @app.get("/api/v1/resource")
        async def get_resource(user_id: str = Depends(require_auth_or_internal_service)):
            # user_id 可能是实际用户 ID 或 "internal-service"
            ...
    """
    # 首先检查是否是内部服务请求
    if InternalServiceAuth.is_internal_service_request(request):
        return InternalServiceAuth.get_service_user_id()

    # 否则检查常规用户认证
    user_id = request.headers.get("user-id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication required"
        )

    return user_id


def create_internal_service_bypass_dependency():
    """
    创建一个允许内部服务绕过认证的依赖函数

    Returns:
        依赖函数

    用法:
        from core.internal_service_auth import create_internal_service_bypass_dependency

        OptionalAuth = create_internal_service_bypass_dependency()

        @app.get("/api/v1/resource")
        async def get_resource(user_id: Optional[str] = Depends(OptionalAuth)):
            # user_id 可能是 None（内部服务）或实际用户ID
            ...
    """
    async def optional_auth(request: Request) -> Optional[str]:
        # 如果是内部服务请求，返回特殊标识
        if InternalServiceAuth.is_internal_service_request(request):
            return InternalServiceAuth.get_service_user_id()

        # 否则返回用户ID（可能为 None）
        return request.headers.get("user-id")

    return optional_auth


__all__ = [
    "InternalServiceAuth",
    "require_auth_or_internal_service",
    "create_internal_service_bypass_dependency",
    "INTERNAL_SERVICE_HEADER",
    "INTERNAL_SERVICE_SECRET_HEADER"
]
