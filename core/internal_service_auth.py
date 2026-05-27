"""
Internal Service Authentication Middleware

用于微服务间通信的内部认证机制
允许服务间调用绕过常规的用户认证

使用方式:
1. 在服务端添加中间件来识别内部服务请求
2. 在客户端发送请求时添加内部服务标识 header
"""

from fastapi import Request
import os
import logging

logger = logging.getLogger(__name__)

# 内部服务认证密钥 — no default; must be set via environment variable
_ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
INTERNAL_SERVICE_SECRET = os.getenv("INTERNAL_SERVICE_SECRET")
if not INTERNAL_SERVICE_SECRET:
    if _ENVIRONMENT in ("production", "staging"):
        raise RuntimeError("INTERNAL_SERVICE_SECRET must be set in production/staging environments")
    else:
        INTERNAL_SERVICE_SECRET = "dev-internal-secret-change-in-production"
        logger.warning("INTERNAL_SERVICE_SECRET not set — using insecure dev default. Do NOT use in production.")
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


__all__ = [
    "InternalServiceAuth",
    "INTERNAL_SERVICE_HEADER",
    "INTERNAL_SERVICE_SECRET_HEADER",
]
