"""
Auth Service HTTP Client

Synchronous HTTP client for calling auth_service APIs.
Following wallet_service pattern.
"""

import logging
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AuthServiceClient:
    """
    HTTP client for auth_service
    
    Handles synchronous communication with auth_service for:
    - Device pairing token verification
    - Device authentication
    - Token revocation
    """
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        """
        Initialize auth service client
        
        Args:
            base_url: Base URL of auth_service (default: http://localhost:8001)
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info(f"AuthServiceClient initialized with base_url: {self.base_url}")
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def verify_pairing_token(
        self,
        device_id: str,
        pairing_token: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Verify device pairing token
        
        Args:
            device_id: Device ID
            pairing_token: Pairing token to verify
            user_id: User ID attempting to pair
            
        Returns:
            Dict with verification result:
            {
                "valid": bool,
                "device_id": str,
                "user_id": str,
                "expires_at": str (ISO datetime),
                "error": str (if invalid)
            }
        """
        try:
            url = f"{self.base_url}/api/v1/auth/device/pairing-token/verify"
            payload = {
                "device_id": device_id,
                "pairing_token": pairing_token,
                "user_id": user_id
            }
            
            logger.debug(f"Verifying pairing token for device {device_id}, user {user_id}")
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Pairing token verification result: {result.get('valid', False)}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error verifying pairing token: {e.response.status_code}")
            return {
                "valid": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            logger.error(f"Error verifying pairing token: {e}", exc_info=True)
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def revoke_device_token(
        self,
        device_id: str,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Revoke device authentication token
        
        Args:
            device_id: Device ID
            auth_token: Optional authentication token for authorization
            
        Returns:
            Dict with revocation result:
            {
                "success": bool,
                "message": str,
                "error": str (if failed)
            }
        """
        try:
            url = f"{self.base_url}/api/v1/auth/device/{device_id}"
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            logger.debug(f"Revoking device token for device {device_id}")
            
            response = await self.client.delete(url, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Device token revoked for device {device_id}")
            return {
                "success": True,
                "message": result.get("message", "Token revoked successfully")
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error revoking device token: {e.response.status_code}")
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            logger.error(f"Error revoking device token: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def authenticate_device(
        self,
        device_id: str,
        device_secret: str
    ) -> Dict[str, Any]:
        """
        Authenticate device with auth_service
        
        Args:
            device_id: Device ID
            device_secret: Device secret
            
        Returns:
            Dict with authentication result:
            {
                "success": bool,
                "access_token": str,
                "token_type": str,
                "expires_in": int,
                "error": str (if failed)
            }
        """
        try:
            url = f"{self.base_url}/api/v1/auth/device/authenticate"
            payload = {
                "device_id": device_id,
                "device_secret": device_secret
            }
            
            logger.debug(f"Authenticating device {device_id}")
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Device {device_id} authenticated successfully")
            return {
                "success": True,
                **result
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error authenticating device: {e.response.status_code}")
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            logger.error(f"Error authenticating device: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
_auth_client: Optional[AuthServiceClient] = None


def get_auth_client(base_url: str = "http://localhost:8001") -> AuthServiceClient:
    """
    Get singleton auth service client
    
    Args:
        base_url: Base URL of auth_service
        
    Returns:
        AuthServiceClient instance
    """
    global _auth_client
    if _auth_client is None:
        _auth_client = AuthServiceClient(base_url)
    return _auth_client


async def close_auth_client():
    """Close the singleton auth service client"""
    global _auth_client
    if _auth_client is not None:
        await _auth_client.close()
        _auth_client = None
