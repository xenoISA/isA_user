"""
API Key Repository - Async Version

API key data access layer using AsyncPostgresClient.
Uses organizations.api_keys JSONB field (will migrate to dedicated table)
"""

import logging
import json
import uuid
import hashlib
import secrets
import ipaddress
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import sys
import os

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager


from core.postgres_client import compute_pool_size as _pg_compute_pool


def _pg_max_pool() -> int:
    """Per-pod Postgres max pool size; scales with replica count (epic #345/#346)."""
    return _pg_compute_pool()


def _pg_min_pool() -> int:
    """Per-pod Postgres min pool size; small constant to avoid pinning idle connections."""
    return 2 if _pg_max_pool() >= 4 else 1


logger = logging.getLogger(__name__)


API_KEY_OWNER_TYPES = {"organization", "service_account"}


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None


def _ip_matches_allowlist(ip_address: str, allowlist: List[str]) -> bool:
    try:
        parsed_ip = ipaddress.ip_address(ip_address)
    except ValueError:
        parsed_ip = None

    for entry in allowlist:
        if entry == ip_address:
            return True
        if parsed_ip is None:
            continue
        try:
            if parsed_ip in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            continue

    return False


def build_api_key_metadata(key_data: Dict[str, Any]) -> Dict[str, Any]:
    """Return project/service-account metadata with legacy org-key defaults."""
    owner_type = key_data.get("owner_type") or "organization"
    if owner_type not in API_KEY_OWNER_TYPES:
        owner_type = "organization"

    scopes = key_data.get("scopes")
    if scopes is None:
        scopes = key_data.get("permissions", [])

    return {
        "project_id": key_data.get("project_id"),
        "owner_type": owner_type,
        "service_account_id": key_data.get("service_account_id"),
        "scopes": _as_list(scopes),
        "ip_allowlist": _as_list(key_data.get("ip_allowlist")),
        "rate_limits": _as_dict(key_data.get("rate_limits")),
        "spend_limit": key_data.get("spend_limit"),
        "created_by": key_data.get("created_by"),
        "expires_at": key_data.get("expires_at"),
    }


def api_key_matches_project(
    key_data: Dict[str, Any], project_id: Optional[str] = None
) -> bool:
    if project_id is None:
        return True
    return key_data.get("project_id") == project_id


def clean_api_key_for_listing(key_data: Dict[str, Any]) -> Dict[str, Any]:
    """Shape an API-key record for list responses without secret material."""
    metadata = build_api_key_metadata(key_data)
    cleaned_key = {
        "key_id": key_data.get("key_id"),
        "name": key_data.get("name"),
        "permissions": key_data.get("permissions", []),
        "created_at": key_data.get("created_at"),
        "created_by": metadata["created_by"],
        "expires_at": metadata["expires_at"],
        "is_active": key_data.get("is_active", False),
        "last_used": key_data.get("last_used"),
        "key_preview": f"isa_...{key_data.get('key_hash', '')[-8:]}"
        if key_data.get("key_hash")
        else None,
    }
    cleaned_key.update(metadata)
    return cleaned_key


class ApiKeyRepository:
    """API key repository - async data access layer"""

    def __init__(
        self, organization_service_client=None, config: Optional[ConfigManager] = None
    ):
        self.organization_service_client = organization_service_client

        if config is None:
            config = ConfigManager("auth_service")

        host, port = config.discover_service(
            service_name="postgres_service",
            default_host="localhost",
            default_port=5432,
            env_host_key="POSTGRES_HOST",
            env_port_key="POSTGRES_PORT",
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            database=os.getenv("POSTGRES_DB", "isa_platform"),
            username=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            user_id="auth-service",
            min_pool_size=_pg_min_pool(),
            max_pool_size=_pg_max_pool(),
        )
        self.schema = "auth"
        self.organizations_table = "organizations"

    def _generate_api_key(self, prefix: str = "isa") -> str:
        """Generate a new API key with prefix"""
        key_data = secrets.token_urlsafe(32)
        return f"{prefix}_{key_data}"

    def _hash_api_key(self, api_key: str) -> str:
        """Create hash of API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def _parse_api_keys(self, api_keys_raw) -> List[Dict[str, Any]]:
        """Parse API keys from database - handles proto and JSON formats"""
        from google.protobuf.json_format import MessageToDict

        if hasattr(api_keys_raw, "values"):
            return [
                MessageToDict(val.struct_value) if hasattr(val, "struct_value") else val
                for val in api_keys_raw.values
            ]
        elif isinstance(api_keys_raw, str):
            return json.loads(api_keys_raw)
        elif isinstance(api_keys_raw, list):
            return api_keys_raw
        else:
            return []

    async def create_api_key(
        self,
        organization_id: str,
        name: str,
        permissions: List[str] = None,
        expires_at: Optional[datetime] = None,
        created_by: str = None,
        project_id: Optional[str] = None,
        owner_type: str = "organization",
        service_account_id: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        ip_allowlist: Optional[List[str]] = None,
        rate_limits: Optional[Dict[str, Any]] = None,
        spend_limit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Create a new API key for an organization"""
        try:
            owner_type = owner_type or "organization"
            if owner_type not in API_KEY_OWNER_TYPES:
                raise ValueError(f"Unsupported API key owner_type: {owner_type}")
            if owner_type == "service_account" and not service_account_id:
                raise ValueError(
                    "service_account_id is required for service-account keys"
                )

            api_key = self._generate_api_key("isa")
            key_hash = self._hash_api_key(api_key)

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
                "last_used": None,
                "project_id": project_id,
                "owner_type": owner_type,
                "service_account_id": service_account_id,
                "scopes": scopes or [],
                "ip_allowlist": ip_allowlist or [],
                "rate_limits": rate_limits or {},
                "spend_limit": spend_limit,
            }

            # Verify organization exists via organization_service (soft check)
            # Personal accounts use user_id as org scope, so the org may not exist
            if self.organization_service_client:
                try:
                    org = await self.organization_service_client.get_organization(
                        organization_id=organization_id, user_id=created_by or "system"
                    )
                    if not org:
                        logger.info(
                            f"Organization '{organization_id}' not found — treating as personal account"
                        )
                except Exception as e:
                    logger.info(
                        f"Could not verify organization '{organization_id}': {e}"
                    )

            # Get current API keys from organization
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT api_keys FROM {self.schema}.{self.organizations_table} WHERE organization_id = $1",
                    params=[organization_id],
                )

            # If organization doesn't exist in auth schema yet, create it
            if not result:
                async with self.db:
                    await self.db.execute(
                        f"INSERT INTO {self.schema}.{self.organizations_table} (organization_id, name, api_keys) VALUES ($1, $2, $3) ON CONFLICT (organization_id) DO NOTHING",
                        params=[organization_id, organization_id, json.dumps([])],
                    )
                    result = await self.db.query_row(
                        f"SELECT api_keys FROM {self.schema}.{self.organizations_table} WHERE organization_id = $1",
                        params=[organization_id],
                    )

            current_keys = self._parse_api_keys(result.get("api_keys", []))
            current_keys.append(key_data)

            # Update organization with new API keys list
            async with self.db:
                count = await self.db.execute(
                    f"UPDATE {self.schema}.{self.organizations_table} SET api_keys = $1, updated_at = $2 WHERE organization_id = $3",
                    params=[current_keys, now, organization_id],
                )

            if count == 0:
                raise Exception("Failed to create API key")

            result_data = key_data.copy()
            result_data["api_key"] = api_key  # Only returned during creation

            return result_data

        except Exception as e:
            logger.error(f"Failed to create API key: {e}")
            raise

    async def validate_api_key(
        self,
        api_key: str,
        project_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate an API key and return organization/permissions"""
        try:
            key_hash = self._hash_api_key(api_key)

            async with self.db:
                rows = await self.db.query(
                    f"SELECT organization_id, api_keys FROM {self.schema}.{self.organizations_table}",
                    params=[],
                )

            if not rows:
                return {"valid": False, "error": "Invalid API key"}

            for row in rows:
                api_keys = self._parse_api_keys(row.get("api_keys", []))

                for key_data in api_keys:
                    if key_data.get("key_hash") == key_hash and key_data.get(
                        "is_active", False
                    ):
                        metadata = build_api_key_metadata(key_data)

                        if (
                            project_id
                            and metadata.get("project_id")
                            and metadata["project_id"] != project_id
                        ):
                            return {
                                "valid": False,
                                "error": f"API key is not scoped to project {project_id}",
                            }

                        if (
                            ip_address
                            and metadata.get("ip_allowlist")
                            and not _ip_matches_allowlist(
                                ip_address, metadata["ip_allowlist"]
                            )
                        ):
                            return {
                                "valid": False,
                                "error": "IP address is not allowed for this API key",
                            }

                        # Check expiration
                        expires_at = key_data.get("expires_at")
                        if expires_at:
                            expiry_time = _parse_datetime(expires_at)

                            if expiry_time.tzinfo is None:
                                current_time = datetime.utcnow().replace(tzinfo=None)
                            else:
                                current_time = datetime.now(timezone.utc)

                            if current_time > expiry_time:
                                return {"valid": False, "error": "API key has expired"}

                        # Update last used timestamp
                        key_data["last_used"] = datetime.now(timezone.utc).isoformat()

                        async with self.db:
                            await self.db.execute(
                                f"UPDATE {self.schema}.{self.organizations_table} SET api_keys = $1 WHERE organization_id = $2",
                                params=[api_keys, row["organization_id"]],
                            )

                        result = {
                            "valid": True,
                            "organization_id": row["organization_id"],
                            "key_id": key_data.get("key_id"),
                            "name": key_data.get("name"),
                            "permissions": key_data.get("permissions", []),
                            "created_at": key_data.get("created_at"),
                            "last_used": key_data.get("last_used"),
                        }
                        result.update(metadata)
                        return result

            return {"valid": False, "error": "Invalid API key"}

        except Exception as e:
            logger.error(f"Error validating API key: {str(e)}")
            return {"valid": False, "error": f"Failed to validate API key: {str(e)}"}

    async def get_organization_api_keys(
        self, organization_id: str, project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all API keys for an organization (without plain key values)"""
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT api_keys FROM {self.schema}.{self.organizations_table} WHERE organization_id = $1",
                    params=[organization_id],
                )

            if not result:
                # No record yet — return empty list (personal accounts may not have a record)
                return []

            api_keys = self._parse_api_keys(result.get("api_keys", []))

            # Remove sensitive data from response
            cleaned_keys = []
            for key_data in api_keys:
                if not api_key_matches_project(key_data, project_id):
                    continue
                cleaned_keys.append(clean_api_key_for_listing(key_data))

            return cleaned_keys

        except Exception as e:
            logger.error(f"Error getting organization API keys: {str(e)}")
            return []

    async def revoke_api_key(self, organization_id: str, key_id: str) -> bool:
        """Revoke (deactivate) an API key"""
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT api_keys FROM {self.schema}.{self.organizations_table} WHERE organization_id = $1",
                    params=[organization_id],
                )

            if not result:
                raise ValueError(
                    f"Organization '{organization_id}' not found in database."
                )

            api_keys = self._parse_api_keys(result.get("api_keys", []))

            key_found = False
            for key_data in api_keys:
                if key_data.get("key_id") == key_id:
                    key_data["is_active"] = False
                    key_data["revoked_at"] = datetime.now(timezone.utc).isoformat()
                    key_found = True
                    break

            if not key_found:
                raise ValueError(f"API key not found: {key_id}")

            now = datetime.now(timezone.utc)
            async with self.db:
                await self.db.execute(
                    f"UPDATE {self.schema}.{self.organizations_table} SET api_keys = $1, updated_at = $2 WHERE organization_id = $3",
                    params=[api_keys, now, organization_id],
                )

            return True

        except Exception as e:
            logger.error(f"Error revoking API key: {str(e)}")
            return False

    async def delete_api_key(self, organization_id: str, key_id: str) -> bool:
        """Delete an API key permanently"""
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT api_keys FROM {self.schema}.{self.organizations_table} WHERE organization_id = $1",
                    params=[organization_id],
                )

            if not result:
                raise ValueError(
                    f"Organization '{organization_id}' not found in database."
                )

            api_keys = self._parse_api_keys(result.get("api_keys", []))

            original_count = len(api_keys)
            api_keys = [key for key in api_keys if key.get("key_id") != key_id]

            if len(api_keys) == original_count:
                raise ValueError(f"API key not found: {key_id}")

            now = datetime.now(timezone.utc)
            async with self.db:
                await self.db.execute(
                    f"UPDATE {self.schema}.{self.organizations_table} SET api_keys = $1, updated_at = $2 WHERE organization_id = $3",
                    params=[api_keys, now, organization_id],
                )

            return True

        except Exception as e:
            logger.error(f"Error deleting API key: {str(e)}")
            return False

    # ------------------------------------------------------------------
    # Per-key Rate Limits (Story xenoISA/isA_Console#461)
    # ------------------------------------------------------------------

    async def get_api_key_rate_limits(
        self, organization_id: str, key_id: str
    ) -> Optional[Dict[str, Any]]:
        """Return the rate_limits sub-field on a specific api-key entry.

        Returns ``{}`` when the key exists but has no rate-limit override,
        and ``None`` when the org or key is missing.
        """
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT api_keys FROM {self.schema}.{self.organizations_table} "
                    "WHERE organization_id = $1",
                    params=[organization_id],
                )
            if not result:
                return None
            api_keys = self._parse_api_keys(result.get("api_keys", []))
            for key_data in api_keys:
                if key_data.get("key_id") == key_id:
                    raw = key_data.get("rate_limits")
                    if raw is None:
                        return {}
                    if isinstance(raw, str):
                        try:
                            return json.loads(raw)
                        except Exception:
                            return {}
                    return raw
            return None
        except Exception as e:
            logger.error(f"Error reading api-key rate_limits {key_id}: {e}")
            return None

    async def update_api_key_rate_limits(
        self,
        organization_id: str,
        key_id: str,
        rate_limits: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Upsert rate_limits on a specific api-key entry.

        Returns the saved value, or ``None`` if the org / key is missing.
        """
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT api_keys FROM {self.schema}.{self.organizations_table} "
                    "WHERE organization_id = $1",
                    params=[organization_id],
                )
            if not result:
                return None
            api_keys = self._parse_api_keys(result.get("api_keys", []))

            updated = False
            for key_data in api_keys:
                if key_data.get("key_id") == key_id:
                    key_data["rate_limits"] = rate_limits
                    updated = True
                    break
            if not updated:
                return None

            now = datetime.now(timezone.utc)
            async with self.db:
                await self.db.execute(
                    f"UPDATE {self.schema}.{self.organizations_table} "
                    "SET api_keys = $1, updated_at = $2 WHERE organization_id = $3",
                    params=[api_keys, now, organization_id],
                )
            return rate_limits
        except Exception as e:
            logger.error(f"Error updating api-key rate_limits {key_id}: {e}")
            return None

    async def cleanup_expired_keys(self) -> int:
        """Clean up expired API keys across all organizations"""
        try:
            async with self.db:
                rows = await self.db.query(
                    f"SELECT organization_id, api_keys FROM {self.schema}.{self.organizations_table} WHERE api_keys IS NOT NULL",
                    params=[],
                )

            if not rows:
                return 0

            total_removed = 0

            for row in rows:
                api_keys = self._parse_api_keys(row.get("api_keys", []))

                now = datetime.now(timezone.utc)
                original_count = len(api_keys)

                api_keys = [
                    key
                    for key in api_keys
                    if not (
                        key.get("expires_at")
                        and datetime.fromisoformat(key["expires_at"]) <= now
                    )
                ]

                removed_count = original_count - len(api_keys)
                if removed_count > 0:
                    async with self.db:
                        await self.db.execute(
                            f"UPDATE {self.schema}.{self.organizations_table} SET api_keys = $1, updated_at = $2 WHERE organization_id = $3",
                            params=[api_keys, now, row["organization_id"]],
                        )
                    total_removed += removed_count

            return total_removed

        except Exception as e:
            logger.error(f"Error cleaning up expired keys: {str(e)}")
            return 0
