"""
API Key Service - API key authentication service
Uses organizations.api_keys JSONB field like the main project
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from .api_key_repository import ApiKeyRepository

logger = logging.getLogger(__name__)

class ApiKeyService:
    """API key service - compatible with main project structure"""
    
    def __init__(self, repository: ApiKeyRepository):
        self.repository = repository
    
    async def create_api_key(self, 
                           organization_id: str,
                           name: str,
                           permissions: List[str] = None,
                           expires_days: Optional[int] = None,
                           created_by: str = None) -> Dict[str, Any]:
        """Create new API key"""
        try:
            # Calculate expiration time
            expires_at = None
            if expires_days:
                expires_at = datetime.now(tz=timezone.utc) + timedelta(days=expires_days)
            
            # Create API key using repository
            result_data = await self.repository.create_api_key(
                organization_id=organization_id,
                name=name,
                permissions=permissions or [],
                expires_at=expires_at,
                created_by=created_by
            )
            
            return {
                "success": True,
                "api_key": result_data["api_key"],  # Only returned during creation
                "key_id": result_data["key_id"],
                "name": name,
                "expires_at": expires_at
            }
            
        except Exception as e:
            logger.error(f"Failed to create API key: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def verify_api_key(self, api_key: str) -> Dict[str, Any]:
        """Verify API key"""
        try:
            # Use repository validation method
            result = await self.repository.validate_api_key(api_key)
            
            if result.get("valid"):
                return {
                    "valid": True,
                    "key_id": result.get("key_id"),
                    "organization_id": result.get("organization_id"),
                    "name": result.get("name"),
                    "permissions": result.get("permissions", []),
                    "created_at": result.get("created_at"),
                    "last_used": result.get("last_used")
                }
            else:
                return {
                    "valid": False,
                    "error": result.get("error", "Invalid API key")
                }
            
        except Exception as e:
            logger.error(f"API key verification failed: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def revoke_api_key(self, key_id: str, organization_id: str) -> Dict[str, Any]:
        """Revoke API key"""
        try:
            success = await self.repository.revoke_api_key(organization_id, key_id)
            
            if success:
                return {"success": True, "message": "API key revoked"}
            else:
                return {"success": False, "error": "API key not found"}
                
        except Exception as e:
            logger.error(f"Failed to revoke API key: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_api_keys(self, organization_id: str) -> Dict[str, Any]:
        """List all API keys for organization"""
        try:
            keys = await self.repository.get_organization_api_keys(organization_id)
            
            return {
                "success": True,
                "api_keys": keys,
                "total": len(keys)
            }
            
        except Exception as e:
            logger.error(f"Failed to list API keys: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_api_key(self, organization_id: str, key_id: str) -> Dict[str, Any]:
        """Delete API key permanently"""
        try:
            success = await self.repository.delete_api_key(organization_id, key_id)
            
            if success:
                return {"success": True, "message": "API key deleted"}
            else:
                return {"success": False, "error": "API key not found"}
                
        except Exception as e:
            logger.error(f"Failed to delete API key: {e}")
            return {
                "success": False,
                "error": str(e)
            }