"""
API Key Repository - API key data access layer
Uses organizations.api_keys JSONB field like the main project
"""

import logging
import json
import uuid
import hashlib
import secrets
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class ApiKeyRepository:
    """API key repository - compatible with main project structure"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.organizations_table = "organizations"
    
    def _generate_api_key(self, prefix: str = "mcp") -> str:
        """Generate a new API key with prefix"""
        key_data = secrets.token_urlsafe(32)
        return f"{prefix}_{key_data}"

    def _hash_api_key(self, api_key: str) -> str:
        """Create hash of API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    async def create_api_key(self, organization_id: str, name: str, permissions: List[str] = None, 
                            expires_at: Optional[datetime] = None, created_by: str = None) -> Dict[str, Any]:
        """Create a new API key for an organization"""
        try:
            # Generate new API key
            api_key = self._generate_api_key("mcp")
            key_hash = self._hash_api_key(api_key)
            
            # Create key metadata
            key_data = {
                "key_id": f"key_{uuid.uuid4().hex[:12]}",
                "name": name,
                "key_hash": key_hash,
                "permissions": permissions or [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": created_by,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "is_active": True,
                "last_used": None
            }
            
            # Get current API keys from organization
            result = self.supabase.table(self.organizations_table).select("api_keys").eq("organization_id", organization_id).single().execute()
            
            if not result.data:
                raise ValueError(f"Organization not found: {organization_id}")
            
            # Parse current API keys
            current_keys = result.data.get('api_keys') or []
            if isinstance(current_keys, str):
                current_keys = json.loads(current_keys)
            
            # Add new key
            current_keys.append(key_data)
            
            # Update organization with new API keys list
            update_result = self.supabase.table(self.organizations_table).update({
                "api_keys": current_keys,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("organization_id", organization_id).execute()
            
            if not update_result.data:
                raise Exception("Failed to create API key")
            
            # Return key data (with plain API key only for initial creation)
            result_data = key_data.copy()
            result_data["api_key"] = api_key  # Only returned during creation
            
            return result_data
                
        except Exception as e:
            logger.error(f"Failed to create API key: {e}")
            raise
    
    async def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """Validate an API key and return organization/permissions"""
        try:
            key_hash = self._hash_api_key(api_key)
            
            # Get all organizations and check their API keys
            # Note: This requires fetching all organizations since Supabase doesn't support JSONB search directly
            result = self.supabase.table(self.organizations_table).select("organization_id, api_keys").execute()
            
            rows = result.data or []
            
            for row in rows:
                api_keys = row['api_keys'] or []
                if isinstance(api_keys, str):
                    api_keys = json.loads(api_keys)
                
                # Find matching key
                for key_data in api_keys:
                    if key_data.get('key_hash') == key_hash and key_data.get('is_active', False):
                        # Check expiration
                        expires_at = key_data.get('expires_at')
                        if expires_at:
                            expiry_time = datetime.fromisoformat(expires_at)
                            # Make sure both datetimes are timezone-aware or both are naive
                            if expiry_time.tzinfo is None:
                                current_time = datetime.utcnow().replace(tzinfo=None)
                            else:
                                current_time = datetime.now(timezone.utc)
                            
                            if current_time > expiry_time:
                                return {"valid": False, "error": "API key has expired"}
                        
                        # Update last used timestamp
                        key_data['last_used'] = datetime.now(timezone.utc).isoformat()
                        
                        # Update organization with new last_used timestamp
                        self.supabase.table(self.organizations_table).update({
                            "api_keys": api_keys
                        }).eq("organization_id", row['organization_id']).execute()
                        
                        return {
                            "valid": True,
                            "organization_id": row['organization_id'],
                            "key_id": key_data.get('key_id'),
                            "name": key_data.get('name'),
                            "permissions": key_data.get('permissions', []),
                            "created_at": key_data.get('created_at'),
                            "last_used": key_data.get('last_used')
                        }
            
            return {"valid": False, "error": "Invalid API key"}
                
        except Exception as e:
            logger.error(f"Error validating API key: {str(e)}")
            return {"valid": False, "error": f"Failed to validate API key: {str(e)}"}
    
    async def get_organization_api_keys(self, organization_id: str) -> List[Dict[str, Any]]:
        """Get all API keys for an organization (without plain key values)"""
        try:
            result = self.supabase.table(self.organizations_table).select("api_keys").eq("organization_id", organization_id).single().execute()
            
            if not result.data:
                raise ValueError(f"Organization not found: {organization_id}")
            
            api_keys = result.data.get('api_keys') or []
            if isinstance(api_keys, str):
                api_keys = json.loads(api_keys)
            
            # Remove sensitive data (key_hash, plain key) from response
            cleaned_keys = []
            for key_data in api_keys:
                cleaned_key = {
                    "key_id": key_data.get('key_id'),
                    "name": key_data.get('name'),
                    "permissions": key_data.get('permissions', []),
                    "created_at": key_data.get('created_at'),
                    "created_by": key_data.get('created_by'),
                    "expires_at": key_data.get('expires_at'),
                    "is_active": key_data.get('is_active', False),
                    "last_used": key_data.get('last_used'),
                    "key_preview": f"mcp_...{key_data.get('key_hash', '')[-8:]}" if key_data.get('key_hash') else None
                }
                cleaned_keys.append(cleaned_key)
            
            return cleaned_keys
                
        except Exception as e:
            logger.error(f"Error getting organization API keys: {str(e)}")
            return []
    
    async def revoke_api_key(self, organization_id: str, key_id: str) -> bool:
        """Revoke (deactivate) an API key"""
        try:
            result = self.supabase.table(self.organizations_table).select("api_keys").eq("organization_id", organization_id).single().execute()
            
            if not result.data:
                raise ValueError(f"Organization not found: {organization_id}")
            
            api_keys = result.data.get('api_keys') or []
            if isinstance(api_keys, str):
                api_keys = json.loads(api_keys)
            
            # Find and deactivate the key
            key_found = False
            for key_data in api_keys:
                if key_data.get('key_id') == key_id:
                    key_data['is_active'] = False
                    key_data['revoked_at'] = datetime.now(timezone.utc).isoformat()
                    key_found = True
                    break
            
            if not key_found:
                raise ValueError(f"API key not found: {key_id}")
            
            # Update organization
            self.supabase.table(self.organizations_table).update({
                "api_keys": api_keys,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("organization_id", organization_id).execute()
            
            return True
                
        except Exception as e:
            logger.error(f"Error revoking API key: {str(e)}")
            return False
    
    async def delete_api_key(self, organization_id: str, key_id: str) -> bool:
        """Delete an API key permanently"""
        try:
            result = self.supabase.table(self.organizations_table).select("api_keys").eq("organization_id", organization_id).single().execute()
            
            if not result.data:
                raise ValueError(f"Organization not found: {organization_id}")
            
            api_keys = result.data.get('api_keys') or []
            if isinstance(api_keys, str):
                api_keys = json.loads(api_keys)
            
            # Remove the key
            original_count = len(api_keys)
            api_keys = [key for key in api_keys if key.get('key_id') != key_id]
            
            if len(api_keys) == original_count:
                raise ValueError(f"API key not found: {key_id}")
            
            # Update organization
            self.supabase.table(self.organizations_table).update({
                "api_keys": api_keys,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("organization_id", organization_id).execute()
            
            return True
                
        except Exception as e:
            logger.error(f"Error deleting API key: {str(e)}")
            return False
    
    async def cleanup_expired_keys(self) -> int:
        """Clean up expired API keys across all organizations"""
        try:
            # Get all organizations with API keys
            result = self.supabase.table(self.organizations_table).select("organization_id, api_keys").not_.is_("api_keys", "null").execute()
            rows = result.data or []
            
            total_removed = 0
            
            for row in rows:
                api_keys = row['api_keys'] or []
                if isinstance(api_keys, str):
                    api_keys = json.loads(api_keys)
                
                # Filter out expired keys
                now = datetime.now(timezone.utc)
                original_count = len(api_keys)
                
                api_keys = [
                    key for key in api_keys
                    if not (
                        key.get('expires_at') and 
                        datetime.fromisoformat(key['expires_at']) <= now
                    )
                ]
                
                removed_count = original_count - len(api_keys)
                if removed_count > 0:
                    # Update organization
                    self.supabase.table(self.organizations_table).update({
                        "api_keys": api_keys,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("organization_id", row['organization_id']).execute()
                    total_removed += removed_count
            
            return total_removed
                
        except Exception as e:
            logger.error(f"Error cleaning up expired keys: {str(e)}")
            return 0