"""
FastAPI Authentication Dependencies for Microservices

统一的认证依赖函数，供所有微服务使用
"""

from fastapi import Header, HTTPException, status, Request
from typing import Optional
import logging
import os
import httpx

logger = logging.getLogger(__name__)

# 内部服务认证配置 — no default; must be set via environment variable
_ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
INTERNAL_SERVICE_SECRET = os.getenv("INTERNAL_SERVICE_SECRET")
if not INTERNAL_SERVICE_SECRET:
    if _ENVIRONMENT in ("production", "staging"):
        raise RuntimeError("INTERNAL_SERVICE_SECRET must be set in production/staging environments")
    else:
        INTERNAL_SERVICE_SECRET = "dev-internal-secret-change-in-production"
        logger.warning("INTERNAL_SERVICE_SECRET not set — using insecure dev default. Do NOT use in production.")

# Auth service URL for JWT verification
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8201")

# Shared HTTP client with connection pooling + keepalive.
# Reusing a single AsyncClient avoids per-request TCP handshakes against the auth
# service, which otherwise dominate localhost latency for verify-token.
_http_client: Optional[httpx.AsyncClient] = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(5.0, connect=2.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
    return _http_client


async def aclose_http_client() -> None:
    """Close the shared client. Hook into FastAPI lifespan shutdown if desired."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


async def _extract_user_id_from_bearer(authorization: str) -> Optional[str]:
    """Extract user_id from a Bearer JWT token by calling auth service verify-token."""
    if not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    try:
        response = await _get_http_client().post(
            f"{AUTH_SERVICE_URL}/api/v1/auth/verify-token",
            json={"token": token},
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("valid"):
                return result.get("user_id")
        return None
    except Exception as e:
        logger.warning(f"Failed to verify Bearer token via auth service: {e}")
        return None


async def _extract_user_id_from_api_key(api_key: str) -> Optional[str]:
    """Verify an API key by calling auth service and return the associated user/org ID."""
    try:
        response = await _get_http_client().post(
            f"{AUTH_SERVICE_URL}/api/v1/auth/verify-api-key",
            json={"api_key": api_key},
        )
        if response.status_code == 429:
            try:
                payload = response.json()
                detail = payload.get("detail", payload)
            except Exception:
                detail = response.text or "Rate limit exceeded"
            headers = {
                key: value
                for key, value in response.headers.items()
                if key.lower()
                in {
                    "retry-after",
                    "x-ratelimit-limit",
                    "x-ratelimit-remaining",
                    "x-ratelimit-field",
                    "x-ratelimit-source",
                }
            }
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail,
                headers=headers,
            )
        if response.status_code == 200:
            result = response.json()
            if result.get("valid"):
                # Return organization_id as the caller identity
                return result.get("organization_id")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Failed to verify API key via auth service: {e}")
        return None


async def require_auth_or_internal_service(
    request: Request,
    x_internal_service: Optional[str] = Header(None, alias="X-Internal-Service"),
    x_internal_service_secret: Optional[str] = Header(None, alias="X-Internal-Service-Secret"),
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    """
    认证依赖：允许用户认证或内部服务认证

    认证优先级：
    1. 内部服务认证（X-Internal-Service + X-Internal-Service-Secret）
    2. Bearer JWT 认证（Authorization: Bearer <jwt>）
    3. API Key 认证（X-API-Key）

    Returns:
        user_id: 用户ID 或 "internal-service"

    Raises:
        HTTPException 401: 认证失败
    """
    # 1. 检查内部服务认证
    if x_internal_service == "true" and x_internal_service_secret:
        if x_internal_service_secret == INTERNAL_SERVICE_SECRET:
            logger.debug(f"Internal service request to {request.url.path}")
            return "internal-service"
        else:
            logger.warning(f"Invalid internal service secret from {request.client.host}")

    # 2. 检查 Authorization: Bearer <jwt> 认证
    if authorization:
        bearer_user_id = await _extract_user_id_from_bearer(authorization)
        if bearer_user_id:
            return bearer_user_id

    # 3. 检查 X-API-Key 认证
    if x_api_key:
        api_key_user_id = await _extract_user_id_from_api_key(x_api_key)
        if api_key_user_id:
            return api_key_user_id

    # 4. 认证失败 - no longer trusting raw user-id headers
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User authentication required"
    )


async def optional_auth_or_internal_service(
    x_internal_service: Optional[str] = Header(None, alias="X-Internal-Service"),
    x_internal_service_secret: Optional[str] = Header(None, alias="X-Internal-Service-Secret"),
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Optional[str]:
    """
    可选认证依赖：允许匿名、用户或内部服务访问

    Returns:
        user_id: 用户ID、"internal-service" 或 None
    """
    # 检查内部服务认证
    if x_internal_service == "true" and x_internal_service_secret == INTERNAL_SERVICE_SECRET:
        return "internal-service"

    # 检查 Authorization: Bearer <jwt> 认证
    if authorization:
        bearer_user_id = await _extract_user_id_from_bearer(authorization)
        if bearer_user_id:
            return bearer_user_id

    # 检查 X-API-Key 认证
    if x_api_key:
        api_key_user_id = await _extract_user_id_from_api_key(x_api_key)
        if api_key_user_id:
            return api_key_user_id

    # No valid credentials provided
    return None


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
    "is_internal_service_request",
    "aclose_http_client",
]
