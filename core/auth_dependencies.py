"""
FastAPI Authentication Dependencies for Microservices

统一的认证依赖函数，供所有微服务使用
"""

from fastapi import Header, HTTPException, status, Request
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)

# 内部服务认证配置
INTERNAL_SERVICE_SECRET = os.getenv(
    "INTERNAL_SERVICE_SECRET",
    "dev-internal-secret-change-in-production"
)


async def require_auth_or_internal_service(
    request: Request,
    user_id: Optional[str] = Header(None, alias="user-id"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_internal_service: Optional[str] = Header(None, alias="X-Internal-Service"),
    x_internal_service_secret: Optional[str] = Header(None, alias="X-Internal-Service-Secret"),
) -> str:
    """
    认证依赖：允许用户认证或内部服务认证

    认证优先级：
    1. 内部服务认证（X-Internal-Service + X-Internal-Service-Secret）
    2. 用户ID认证（user-id 或 X-User-Id）

    Args:
        request: FastAPI Request
        user_id: 用户ID (user-id header)
        x_user_id: 用户ID (X-User-Id header)
        x_internal_service: 内部服务标识
        x_internal_service_secret: 内部服务密钥

    Returns:
        user_id: 用户ID 或 "internal-service"

    Raises:
        HTTPException 401: 认证失败

    使用示例：
        @app.get("/api/resource")
        async def get_resource(
            user_id: str = Depends(require_auth_or_internal_service)
        ):
            if user_id == "internal-service":
                # 内部服务调用，绕过权限检查
                pass
            else:
                # 普通用户调用，检查权限
                pass
    """
    # 1. 检查内部服务认证
    if x_internal_service == "true" and x_internal_service_secret:
        if x_internal_service_secret == INTERNAL_SERVICE_SECRET:
            logger.debug(f"Internal service request to {request.url.path}")
            return "internal-service"
        else:
            logger.warning(f"Invalid internal service secret from {request.client.host}")

    # 2. 检查用户ID认证
    user_id_value = user_id or x_user_id
    if user_id_value:
        return user_id_value

    # 3. 认证失败
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User authentication required"
    )


async def optional_auth_or_internal_service(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    user_id: Optional[str] = Header(None, alias="user-id"),
    x_internal_service: Optional[str] = Header(None, alias="X-Internal-Service"),
    x_internal_service_secret: Optional[str] = Header(None, alias="X-Internal-Service-Secret"),
) -> Optional[str]:
    """
    可选认证依赖：允许匿名、用户或内部服务访问

    Returns:
        user_id: 用户ID、"internal-service" 或 None

    使用示例：
        @app.get("/api/public-resource")
        async def get_public_resource(
            user_id: Optional[str] = Depends(optional_auth_or_internal_service)
        ):
            if user_id is None:
                # 匿名用户
                pass
            elif user_id == "internal-service":
                # 内部服务
                pass
            else:
                # 已认证用户
                pass
    """
    # 检查内部服务认证
    if x_internal_service == "true" and x_internal_service_secret == INTERNAL_SERVICE_SECRET:
        return "internal-service"

    # 返回用户ID（可能为None）
    return user_id or x_user_id


def is_internal_service_request(user_id: str) -> bool:
    """
    检查是否是内部服务请求

    Args:
        user_id: 从认证依赖获得的 user_id

    Returns:
        True 如果是内部服务请求

    使用示例：
        @app.get("/api/resource")
        async def get_resource(
            user_id: str = Depends(require_auth_or_internal_service)
        ):
            if is_internal_service_request(user_id):
                # 跳过权限检查
                return await get_all_data()
            else:
                # 检查用户权限
                return await get_user_data(user_id)
    """
    return user_id == "internal-service"


__all__ = [
    "require_auth_or_internal_service",
    "optional_auth_or_internal_service",
    "is_internal_service_request"
]
