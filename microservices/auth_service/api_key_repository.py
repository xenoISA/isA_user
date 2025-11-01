"""
API Key Repository - API key data access layer
Uses organizations.api_keys JSONB field (will migrate to dedicated table)
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

from isa_common.postgres_client import PostgresClient

logger = logging.getLogger(__name__)

class ApiKeyRepository:
    """API key repository - compatible with main project structure"""

    def __init__(self, organization_service_client=None):
        # Use organization service client for microservice communication
        self.organization_service_client = organization_service_client

        # PostgreSQL client for API key storage
        # TODO: Use Consul service discovery instead of hardcoded host/port
        self.db = PostgresClient(host='isa-postgres-grpc', port=50061, user_id='auth-service')
        self.schema = "auth"
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
            # Note: Convert datetime objects to ISO strings for JSONB storage
            now = datetime.now(timezone.utc)
            key_data = {
                "key_id": f"key_{uuid.uuid4().hex[:12]}",
                "name": name,
                "key_hash": key_hash,
                "permissions": permissions or [],
                "created_at": now.isoformat(),
                "created_by": created_by,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "is_active": True,
                "last_used": None
            }

            # Verify organization exists via organization_service
            if self.organization_service_client:
                org = await self.organization_service_client.get_organization(
                    organization_id=organization_id,
                    user_id=created_by or "system"
                )
                if not org:
                    raise ValueError(f"Organization '{organization_id}' not found in database. Please ensure the organization exists before creating API keys.")

            # Get current API keys from organization (we still store them in auth schema for now)
            with self.db:
                result = self.db.query_row(
                    f"SELECT api_keys FROM {self.schema}.{self.organizations_table} WHERE organization_id = $1",
                    [organization_id],
                    schema=self.schema
                )

            # If organization doesn't exist in auth schema yet, create it
            if not result:
                # Initialize organization in auth schema with empty API keys
                with self.db:
                    self.db.execute(
                        f"INSERT INTO {self.schema}.{self.organizations_table} (organization_id, name, api_keys) VALUES ($1, $2, $3) ON CONFLICT (organization_id) DO NOTHING",
                        [organization_id, organization_id, json.dumps([])],  # Use org_id as name initially
                        schema=self.schema
                    )
                    # Re-query to get the result
                    result = self.db.query_row(
                        f"SELECT api_keys FROM {self.schema}.{self.organizations_table} WHERE organization_id = $1",
                        [organization_id],
                        schema=self.schema
                    )

            # Parse current API keys - handle proto ListValue
            api_keys_raw = result.get('api_keys', [])
            from google.protobuf.json_format import MessageToDict
            if hasattr(api_keys_raw, 'values'):
                # It's a proto ListValue, convert to Python list
                current_keys = [MessageToDict(val.struct_value) if hasattr(val, 'struct_value') else val
                               for val in api_keys_raw.values]
            elif isinstance(api_keys_raw, str):
                current_keys = json.loads(api_keys_raw)
            elif isinstance(api_keys_raw, list):
                current_keys = api_keys_raw
            else:
                current_keys = []

            # Add new key
            current_keys.append(key_data)

            # Update organization with new API keys list
            # Note: Pass as Python list, PostgresClient will handle JSONB conversion
            with self.db:
                count = self.db.execute(
                    f"UPDATE {self.schema}.{self.organizations_table} SET api_keys = $1, updated_at = $2 WHERE organization_id = $3",
                    [current_keys, now, organization_id],
                    schema=self.schema
                )

            if count == 0:
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
            # Note: Requires scanning all orgs since keys are in JSONB
            with self.db:
                rows = self.db.query(
                    f"SELECT organization_id, api_keys FROM {self.schema}.{self.organizations_table}",
                    schema=self.schema
                )

            for row in rows:
                # api_keys is returned as proto ListValue, need to convert to Python types
                api_keys_raw = row.get('api_keys', [])

                # Convert proto ListValue to Python list using MessageToDict
                from google.protobuf.json_format import MessageToDict
                if hasattr(api_keys_raw, 'values'):
                    # It's a proto ListValue, convert to Python list
                    api_keys = [MessageToDict(val.struct_value) if hasattr(val, 'struct_value') else val
                               for val in api_keys_raw.values]
                elif isinstance(api_keys_raw, str):
                    api_keys = json.loads(api_keys_raw)
                elif isinstance(api_keys_raw, list):
                    api_keys = api_keys_raw
                else:
                    api_keys = []

                # Find matching key
                for key_data in api_keys:
                    if key_data.get('key_hash') == key_hash and key_data.get('is_active', False):
                        # Check expiration
                        expires_at = key_data.get('expires_at')
                        if expires_at:
                            if isinstance(expires_at, str):
                                expiry_time = datetime.fromisoformat(expires_at)
                            else:
                                expiry_time = expires_at

                            if expiry_time.tzinfo is None:
                                current_time = datetime.utcnow().replace(tzinfo=None)
                            else:
                                current_time = datetime.now(timezone.utc)

                            if current_time > expiry_time:
                                return {"valid": False, "error": "API key has expired"}

                        # Update last used timestamp (convert to ISO string for JSONB)
                        key_data['last_used'] = datetime.now(timezone.utc).isoformat()

                        # Update organization with new last_used timestamp
                        with self.db:
                            self.db.execute(
                                f"UPDATE {self.schema}.{self.organizations_table} SET api_keys = $1 WHERE organization_id = $2",
                                [api_keys, row['organization_id']],
                                schema=self.schema
                            )

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
            with self.db:
                result = self.db.query_row(
                    f"SELECT api_keys FROM {self.schema}.{self.organizations_table} WHERE organization_id = $1",
                    [organization_id],
                    schema=self.schema
                )

            if not result:
                raise ValueError(f"Organization '{organization_id}' not found in database.")

            # Convert proto ListValue to Python list
            api_keys_raw = result.get('api_keys', [])
            from google.protobuf.json_format import MessageToDict
            if hasattr(api_keys_raw, 'values'):
                api_keys = [MessageToDict(val.struct_value) if hasattr(val, 'struct_value') else val
                           for val in api_keys_raw.values]
            elif isinstance(api_keys_raw, str):
                api_keys = json.loads(api_keys_raw)
            elif isinstance(api_keys_raw, list):
                api_keys = api_keys_raw
            else:
                api_keys = []

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
            with self.db:
                result = self.db.query_row(
                    f"SELECT api_keys FROM {self.schema}.{self.organizations_table} WHERE organization_id = $1",
                    [organization_id],
                    schema=self.schema
                )

            if not result:
                raise ValueError(f"Organization '{organization_id}' not found in database.")

            # Convert proto ListValue to Python list
            api_keys_raw = result.get('api_keys', [])
            from google.protobuf.json_format import MessageToDict
            if hasattr(api_keys_raw, 'values'):
                api_keys = [MessageToDict(val.struct_value) if hasattr(val, 'struct_value') else val
                           for val in api_keys_raw.values]
            elif isinstance(api_keys_raw, str):
                api_keys = json.loads(api_keys_raw)
            elif isinstance(api_keys_raw, list):
                api_keys = api_keys_raw
            else:
                api_keys = []

            # Find and deactivate the key
            key_found = False
            for key_data in api_keys:
                if key_data.get('key_id') == key_id:
                    key_data['is_active'] = False
                    key_data['revoked_at'] = datetime.now(timezone.utc).isoformat()  # Convert to ISO string
                    key_found = True
                    break

            if not key_found:
                raise ValueError(f"API key not found: {key_id}")

            # Update organization
            now = datetime.now(timezone.utc)
            with self.db:
                self.db.execute(
                    f"UPDATE {self.schema}.{self.organizations_table} SET api_keys = $1, updated_at = $2 WHERE organization_id = $3",
                    [api_keys, now, organization_id],
                    schema=self.schema
                )

            return True

        except Exception as e:
            logger.error(f"Error revoking API key: {str(e)}")
            return False

    async def delete_api_key(self, organization_id: str, key_id: str) -> bool:
        """Delete an API key permanently"""
        try:
            with self.db:
                result = self.db.query_row(
                    f"SELECT api_keys FROM {self.schema}.{self.organizations_table} WHERE organization_id = $1",
                    [organization_id],
                    schema=self.schema
                )

            if not result:
                raise ValueError(f"Organization '{organization_id}' not found in database.")

            # Convert proto ListValue to Python list
            api_keys_raw = result.get('api_keys', [])
            from google.protobuf.json_format import MessageToDict
            if hasattr(api_keys_raw, 'values'):
                api_keys = [MessageToDict(val.struct_value) if hasattr(val, 'struct_value') else val
                           for val in api_keys_raw.values]
            elif isinstance(api_keys_raw, str):
                api_keys = json.loads(api_keys_raw)
            elif isinstance(api_keys_raw, list):
                api_keys = api_keys_raw
            else:
                api_keys = []

            # Remove the key
            original_count = len(api_keys)
            api_keys = [key for key in api_keys if key.get('key_id') != key_id]

            if len(api_keys) == original_count:
                raise ValueError(f"API key not found: {key_id}")

            # Update organization
            now = datetime.now(timezone.utc)
            with self.db:
                self.db.execute(
                    f"UPDATE {self.schema}.{self.organizations_table} SET api_keys = $1, updated_at = $2 WHERE organization_id = $3",
                    [api_keys, now, organization_id],
                    schema=self.schema
                )

            return True

        except Exception as e:
            logger.error(f"Error deleting API key: {str(e)}")
            return False
    
    async def cleanup_expired_keys(self) -> int:
        """Clean up expired API keys across all organizations"""
        try:
            # Get all organizations with API keys
            with self.db:
                rows = self.db.query(
                    f"SELECT organization_id, api_keys FROM {self.schema}.{self.organizations_table} WHERE api_keys IS NOT NULL",
                    schema=self.schema
                )

            total_removed = 0

            for row in rows:
                # Convert proto ListValue to Python list
                api_keys_raw = row.get('api_keys', [])
                from google.protobuf.json_format import MessageToDict
                if hasattr(api_keys_raw, 'values'):
                    api_keys = [MessageToDict(val.struct_value) if hasattr(val, 'struct_value') else val
                               for val in api_keys_raw.values]
                elif isinstance(api_keys_raw, str):
                    api_keys = json.loads(api_keys_raw)
                elif isinstance(api_keys_raw, list):
                    api_keys = api_keys_raw
                else:
                    api_keys = []

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
                    with self.db:
                        self.db.execute(
                            f"UPDATE {self.schema}.{self.organizations_table} SET api_keys = $1, updated_at = $2 WHERE organization_id = $3",
                            [api_keys, now, row['organization_id']],
                            schema=self.schema
                        )
                    total_removed += removed_count

            return total_removed

        except Exception as e:
            logger.error(f"Error cleaning up expired keys: {str(e)}")
            return 0