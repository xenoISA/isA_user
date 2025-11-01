"""
Compliance Middleware

用于其他微服务集成合规检查的中间件
"""

import logging
import httpx
from typing import Optional, List, Callable, Awaitable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .models import (
    ComplianceCheckRequest, ComplianceCheckResponse,
    ContentType, ComplianceCheckType, ComplianceStatus
)

logger = logging.getLogger(__name__)


class ComplianceMiddleware(BaseHTTPMiddleware):
    """
    合规检查中间件
    
    自动拦截请求，对特定内容进行合规检查
    
    **使用示例:**
    ```python
    from fastapi import FastAPI
    from compliance_service.middleware import ComplianceMiddleware
    
    app = FastAPI()
    
    app.add_middleware(
        ComplianceMiddleware,
        compliance_service_url="http://localhost:8250",
        enabled_paths=["/api/messages", "/api/upload"],
        check_types=["content_moderation", "pii_detection"]
    )
    ```
    """
    
    def __init__(
        self,
        app,
        compliance_service_url: str = "http://localhost:8250",
        enabled_paths: Optional[List[str]] = None,
        check_types: Optional[List[str]] = None,
        auto_block: bool = True,
        timeout: float = 5.0
    ):
        super().__init__(app)
        self.compliance_service_url = compliance_service_url.rstrip("/")
        self.enabled_paths = enabled_paths or ["/api/"]
        self.check_types = check_types or ["content_moderation", "pii_detection"]
        self.auto_block = auto_block
        self.timeout = timeout
        self.http_client = httpx.AsyncClient(timeout=timeout)
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """处理请求"""
        
        # 检查路径是否需要合规检查
        if not self._should_check_path(request.url.path):
            return await call_next(request)
        
        # 只检查POST/PUT请求
        if request.method not in ["POST", "PUT", "PATCH"]:
            return await call_next(request)
        
        try:
            # 提取请求体
            body = await request.body()
            
            # 执行合规检查
            compliance_result = await self._check_compliance(request, body)
            
            # 根据合规检查结果决定是否继续
            if not compliance_result.passed and self.auto_block:
                return self._create_blocked_response(compliance_result)
            
            # 将合规检查结果添加到请求状态
            request.state.compliance_check = compliance_result
            
            # 继续处理请求
            response = await call_next(request)
            
            # 添加合规检查头信息
            response.headers["X-Compliance-Check-Id"] = compliance_result.check_id
            response.headers["X-Compliance-Status"] = compliance_result.status.value
            
            return response
            
        except Exception as e:
            logger.error(f"Compliance middleware error: {e}")
            # 发生错误时，根据配置决定是否继续
            if self.auto_block:
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Compliance check failed",
                        "detail": str(e)
                    }
                )
            else:
                return await call_next(request)
    
    def _should_check_path(self, path: str) -> bool:
        """判断路径是否需要合规检查"""
        for enabled_path in self.enabled_paths:
            if path.startswith(enabled_path):
                return True
        return False
    
    async def _check_compliance(
        self,
        request: Request,
        body: bytes
    ) -> ComplianceCheckResponse:
        """执行合规检查"""
        try:
            # 解析请求体（简化处理）
            import json
            try:
                data = json.loads(body.decode())
            except:
                data = {}
            
            # 提取需要检查的内容
            content = data.get("content") or data.get("message") or data.get("text") or ""
            content_type = self._detect_content_type(data)
            
            # 构建合规检查请求
            user_id = getattr(request.state, "user_id", "unknown")
            
            check_request = {
                "user_id": user_id,
                "content_type": content_type,
                "content": content,
                "check_types": self.check_types,
                "metadata": {
                    "path": request.url.path,
                    "method": request.method,
                    "ip": request.client.host if request.client else None
                }
            }
            
            # 调用合规服务
            response = await self.http_client.post(
                f"{self.compliance_service_url}/api/compliance/check",
                json=check_request
            )
            
            if response.status_code == 200:
                result_data = response.json()
                return ComplianceCheckResponse(**result_data)
            else:
                logger.error(f"Compliance service error: {response.status_code}")
                # 返回默认失败结果
                return self._create_default_failed_response()
                
        except Exception as e:
            logger.error(f"Error checking compliance: {e}")
            return self._create_default_failed_response()
    
    def _detect_content_type(self, data: dict) -> str:
        """检测内容类型"""
        if "file_id" in data or "file" in data:
            return "file"
        elif "image" in data or "image_url" in data:
            return "image"
        elif "audio" in data or "audio_url" in data:
            return "audio"
        else:
            return "text"
    
    def _create_blocked_response(self, compliance_result: ComplianceCheckResponse) -> JSONResponse:
        """创建阻止响应"""
        return JSONResponse(
            status_code=403,
            content={
                "error": "Content blocked by compliance check",
                "message": compliance_result.message,
                "check_id": compliance_result.check_id,
                "status": compliance_result.status.value,
                "risk_level": compliance_result.risk_level.value,
                "violations": compliance_result.violations
            }
        )
    
    def _create_default_failed_response(self) -> ComplianceCheckResponse:
        """创建默认失败响应"""
        import uuid
        from datetime import datetime
        
        return ComplianceCheckResponse(
            check_id=str(uuid.uuid4()),
            status=ComplianceStatus.FAIL,
            risk_level="high",
            passed=False,
            violations=[{"issue": "Compliance check service unavailable"}],
            warnings=[],
            action_required="review",
            action_taken="blocked",
            message="Content blocked due to compliance service error",
            checked_at=datetime.utcnow(),
            processing_time_ms=0.0
        )


class ComplianceClient:
    """
    合规服务客户端
    
    用于在代码中主动调用合规检查
    
    **使用示例:**
    ```python
    from compliance_service.middleware import ComplianceClient
    
    client = ComplianceClient("http://localhost:8250")
    
    # 检查文本内容
    result = await client.check_text(
        user_id="user123",
        content="User message here",
        check_types=["content_moderation", "pii_detection"]
    )
    
    if not result.passed:
        raise HTTPException(status_code=403, detail="Content blocked")
    ```
    """
    
    def __init__(self, compliance_service_url: str = "http://localhost:8250"):
        self.base_url = compliance_service_url.rstrip("/")
        self.http_client = httpx.AsyncClient(timeout=10.0)
    
    async def check_text(
        self,
        user_id: str,
        content: str,
        check_types: Optional[List[str]] = None,
        organization_id: Optional[str] = None,
        **kwargs
    ) -> ComplianceCheckResponse:
        """检查文本内容"""
        request = ComplianceCheckRequest(
            user_id=user_id,
            organization_id=organization_id,
            content_type=ContentType.TEXT,
            content=content,
            check_types=[ComplianceCheckType(ct) for ct in (check_types or ["content_moderation"])],
            **kwargs
        )
        return await self._perform_check(request)
    
    async def check_prompt(
        self,
        user_id: str,
        prompt: str,
        organization_id: Optional[str] = None,
        **kwargs
    ) -> ComplianceCheckResponse:
        """检查AI提示词"""
        request = ComplianceCheckRequest(
            user_id=user_id,
            organization_id=organization_id,
            content_type=ContentType.PROMPT,
            content=prompt,
            check_types=[
                ComplianceCheckType.PROMPT_INJECTION,
                ComplianceCheckType.CONTENT_MODERATION
            ],
            **kwargs
        )
        return await self._perform_check(request)
    
    async def check_file(
        self,
        user_id: str,
        file_id: str,
        content_type: ContentType = ContentType.FILE,
        organization_id: Optional[str] = None,
        **kwargs
    ) -> ComplianceCheckResponse:
        """检查文件内容"""
        request = ComplianceCheckRequest(
            user_id=user_id,
            organization_id=organization_id,
            content_type=content_type,
            content_id=file_id,
            check_types=[ComplianceCheckType.CONTENT_MODERATION],
            **kwargs
        )
        return await self._perform_check(request)
    
    async def _perform_check(self, request: ComplianceCheckRequest) -> ComplianceCheckResponse:
        """执行检查请求"""
        try:
            response = await self.http_client.post(
                f"{self.base_url}/api/compliance/check",
                json=request.dict()
            )
            
            if response.status_code == 200:
                return ComplianceCheckResponse(**response.json())
            else:
                raise Exception(f"Compliance check failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Compliance check error: {e}")
            raise
    
    async def get_check_status(self, check_id: str) -> dict:
        """获取检查状态"""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/api/compliance/checks/{check_id}"
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error getting check status: {e}")
            raise
    
    async def close(self):
        """关闭客户端"""
        await self.http_client.aclose()


# ====================
# 依赖注入辅助函数
# ====================

def get_compliance_client(
    compliance_service_url: str = "http://localhost:8250"
) -> ComplianceClient:
    """获取合规客户端实例（用于FastAPI依赖注入）"""
    return ComplianceClient(compliance_service_url)


async def require_compliance_check(
    request: Request,
    compliance_client: ComplianceClient = None
):
    """
    FastAPI依赖 - 要求通过合规检查
    
    **使用示例:**
    ```python
    @app.post("/api/messages")
    async def create_message(
        message: str,
        user_id: str,
        _: None = Depends(require_compliance_check)
    ):
        # 只有通过合规检查的请求才能到达这里
        return {"status": "success"}
    ```
    """
    if not hasattr(request.state, "compliance_check"):
        raise HTTPException(
            status_code=500,
            detail="Compliance check not performed"
        )
    
    compliance_result: ComplianceCheckResponse = request.state.compliance_check
    
    if not compliance_result.passed:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Content blocked by compliance check",
                "check_id": compliance_result.check_id,
                "violations": compliance_result.violations
            }
        )


__all__ = [
    'ComplianceMiddleware',
    'ComplianceClient',
    'get_compliance_client',
    'require_compliance_check'
]

