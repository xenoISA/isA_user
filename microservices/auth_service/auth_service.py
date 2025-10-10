"""
Authentication Service - 纯认证服务
只负责身份认证，不涉及权限控制
"""

import jwt
import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from enum import Enum

logger = logging.getLogger(__name__)

class AuthProvider(Enum):
    """认证提供者"""
    AUTH0 = "auth0"
    SUPABASE = "supabase"
    LOCAL = "local"

class AuthenticationService:
    """纯认证服务 - 重新实现"""

    def __init__(self, config=None):
        """
        Initialize authentication service

        Args:
            config: ServiceConfig object from ConfigManager (optional for backwards compatibility)
        """
        # Auth0配置
        self.auth0_domain = config.auth0_domain if config and config.auth0_domain else "your-auth0-domain.auth0.com"
        self.auth0_audience = config.auth0_audience if config and config.auth0_audience else ""
        self.auth0_algorithms = ["RS256"]

        # Supabase配置
        self.supabase_jwt_secret = config.supabase_key if config else None
        self.supabase_url = config.supabase_url if config else None

        # 本地JWT配置
        self.local_jwt_secret = config.local_jwt_secret if config and config.local_jwt_secret else "your-local-secret-key"
        self.local_jwt_algorithm = config.local_jwt_algorithm if config else "HS256"

        # HTTP客户端
        self.http_client = httpx.AsyncClient(timeout=10.0)
    
    async def verify_token(self, token: str, provider: Optional[str] = None) -> Dict[str, Any]:
        """验证JWT Token"""
        try:
            # Auto-detect provider
            if not provider:
                provider = self._detect_provider(token)
            
            if provider == AuthProvider.AUTH0.value:
                return await self._verify_auth0_token(token)
            elif provider == AuthProvider.SUPABASE.value:
                return await self._verify_supabase_token(token)
            elif provider == AuthProvider.LOCAL.value:
                return await self._verify_local_token(token)
            else:
                return {
                    "valid": False,
                    "error": f"Unsupported provider: {provider}"
                }
                
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def _verify_auth0_token(self, token: str) -> Dict[str, Any]:
        """Verify Auth0 JWT Token"""
        try:
            # 获取Auth0公钥
            jwks_url = f"https://{self.auth0_domain}/.well-known/jwks.json"
            jwks_response = await self.http_client.get(jwks_url)
            jwks = jwks_response.json()
            
            # 解码token头部获取kid
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            
            # 找到对应的公钥
            public_key = None
            for key in jwks["keys"]:
                if key["kid"] == kid:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break
            
            if not public_key:
                return {"valid": False, "error": "Public key not found"}
            
            # 验证token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=self.auth0_algorithms,
                audience=self.auth0_audience,
                issuer=f"https://{self.auth0_domain}/"
            )
            
            return {
                "valid": True,
                "provider": "auth0",
                "payload": payload,
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc)
            }
            
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": f"Invalid token: {str(e)}"}
    
    async def _verify_supabase_token(self, token: str) -> Dict[str, Any]:
        """Verify Supabase JWT Token"""
        try:
            payload = jwt.decode(
                token,
                self.supabase_jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False, "verify_iat": False, "verify_exp": False}
            )
            
            return {
                "valid": True,
                "provider": "supabase",
                "payload": payload,
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "role": payload.get("role"),
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc)
            }
            
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": f"Invalid token: {str(e)}"}
    
    async def _verify_local_token(self, token: str) -> Dict[str, Any]:
        """Verify local JWT Token"""
        try:
            payload = jwt.decode(
                token,
                self.local_jwt_secret,
                algorithms=[self.local_jwt_algorithm]
            )
            
            return {
                "valid": True,
                "provider": "local",
                "payload": payload,
                "user_id": payload.get("user_id"),
                "email": payload.get("email"),
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc)
            }
            
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": f"Invalid token: {str(e)}"}
    
    def _detect_provider(self, token: str) -> str:
        """Auto-detect token provider"""
        try:
            # 解码header查看issuer
            header = jwt.get_unverified_header(token)
            payload = jwt.decode(token, options={"verify_signature": False})
            
            issuer = payload.get("iss", "")
            
            if "auth0.com" in issuer:
                return AuthProvider.AUTH0.value
            elif "supabase" in issuer or payload.get("role"):
                return AuthProvider.SUPABASE.value
            else:
                return AuthProvider.LOCAL.value
                
        except:
            return AuthProvider.LOCAL.value
    
    async def generate_dev_token(self, user_id: str, email: str, expires_in: int = 3600) -> Dict[str, Any]:
        """Generate development token - Supabase格式兼容原有API"""
        try:
            # 使用Supabase格式，兼容原有用户服务API文档
            payload = {
                "aud": "authenticated",
                "exp": int((datetime.now(tz=timezone.utc) + timedelta(seconds=expires_in)).timestamp()),
                "sub": user_id,
                "email": email,
                "role": "authenticated",
                "iss": "supabase",
                "iat": int(datetime.now(tz=timezone.utc).timestamp())
            }
            
            # 使用Supabase service role key作为签名密钥
            supabase_secret = self.supabase_jwt_secret or "your-local-secret-key"
            
            token = jwt.encode(payload, supabase_secret, algorithm="HS256")
            
            return {
                "success": True,
                "token": token,
                "expires_in": expires_in,
                "user_id": user_id,
                "email": email
            }
            
        except Exception as e:
            logger.error(f"Token generation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_user_info_from_token(self, token: str) -> Dict[str, Any]:
        """Extract user information from token"""
        verification_result = await self.verify_token(token)
        
        if not verification_result.get("valid"):
            return {"success": False, "error": verification_result.get("error")}
        
        return {
            "success": True,
            "user_id": verification_result.get("user_id"),
            "email": verification_result.get("email"),
            "provider": verification_result.get("provider"),
            "expires_at": verification_result.get("expires_at")
        }
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()