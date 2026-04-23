"""
API Key Service - API key authentication service
Uses organizations.api_keys JSONB field like the main project
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta

import httpx

from .api_key_repository import ApiKeyRepository
from .rate_limit_state import (
    RequestRateLimitExceeded,
    RequestRateLimiter,
    merge_rate_limits,
)

logger = logging.getLogger(__name__)

class ApiKeyService:
    """API key service - compatible with main project structure"""
    
    def __init__(
        self,
        repository: ApiKeyRepository,
        organization_service_client=None,
        request_rate_limiter: Optional[RequestRateLimiter] = None,
        billing_http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.repository = repository
        self.organization_service_client = organization_service_client
        self.request_rate_limiter = request_rate_limiter or RequestRateLimiter()
        self.billing_base_url = (
            os.getenv("BILLING_SERVICE_URL")
            or os.getenv("BILLING_SERVICE_BASE_URL")
            or (
                f"http://{os.getenv('BILLING_SERVICE_HOST', '127.0.0.1')}:"
                f"{os.getenv('BILLING_SERVICE_PORT', '8216')}"
            )
        ).rstrip("/")
        self._billing_http_client = billing_http_client or httpx.AsyncClient(timeout=10.0)

    async def close(self) -> None:
        await self._billing_http_client.aclose()
    
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
                effective_limits, field_sources = await self._resolve_effective_rate_limits(
                    result.get("organization_id"),
                    result.get("key_id"),
                )
                rate_limit_error = await self._enforce_request_limits(
                    organization_id=result.get("organization_id"),
                    key_id=result.get("key_id"),
                    effective_limits=effective_limits,
                    field_sources=field_sources,
                )
                if rate_limit_error is not None:
                    return {
                        "valid": False,
                        "rate_limited": True,
                        "status_code": 429,
                        "detail": rate_limit_error.detail(),
                        "headers": rate_limit_error.headers(),
                    }
                return {
                    "valid": True,
                    "key_id": result.get("key_id"),
                    "organization_id": result.get("organization_id"),
                    "name": result.get("name"),
                    "permissions": result.get("permissions", []),
                    "created_at": result.get("created_at"),
                    "last_used": result.get("last_used"),
                    "effective_rate_limits": effective_limits,
                    "rate_limit_sources": field_sources,
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

    async def get_effective_rate_limits(
        self, organization_id: str, key_id: str
    ) -> Dict[str, Any]:
        """Resolve merged rate limits for a specific API key."""
        effective_limits, field_sources = await self._resolve_effective_rate_limits(
            organization_id,
            key_id,
        )
        return {
            "success": True,
            "rate_limits": effective_limits,
            "field_sources": field_sources,
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

    # ------------------------------------------------------------------
    # Per-key Rate Limits (Story xenoISA/isA_Console#461)
    # ------------------------------------------------------------------

    async def get_rate_limits(
        self, organization_id: str, key_id: str
    ) -> Dict[str, Any]:
        """Read the rate-limit override on a specific api-key.

        Request limits are enforced during API-key validation. APISIX-native
        synchronization remains a separate follow-up issue.
        """
        try:
            raw = await self.repository.get_api_key_rate_limits(
                organization_id, key_id
            )
            if raw is None:
                return {"success": False, "error": "API key not found"}
            # Empty dict means "no override configured" — distinguish via source.
            return {
                "success": True,
                "rate_limits": raw,
                "source": "configured" if raw else "unset",
            }
        except Exception as e:
            logger.error(f"Failed to read api-key rate_limits: {e}")
            return {"success": False, "error": str(e)}

    async def update_rate_limits(
        self,
        organization_id: str,
        key_id: str,
        rate_limits: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Upsert the rate-limit override on a specific api-key."""
        try:
            saved = await self.repository.update_api_key_rate_limits(
                organization_id, key_id, rate_limits
            )
            if saved is None:
                return {"success": False, "error": "API key not found"}
            return {"success": True, "rate_limits": saved, "source": "configured"}
        except Exception as e:
            logger.error(f"Failed to update api-key rate_limits: {e}")
            return {"success": False, "error": str(e)}

    async def get_org_usage_vs_limit(self, organization_id: str) -> Dict[str, Any]:
        """Return current daily consumption against org-level limits."""
        org_limits = await self._get_org_rate_limits(organization_id)
        if org_limits is None:
            return {"success": False, "error": "Organization not found"}

        effective_limits, field_sources = merge_rate_limits(org_limits, None)
        request_usage = await self.request_rate_limiter.snapshot_request_usage(
            organization_id=organization_id,
            key_id="org-default",
            effective_limits=effective_limits,
            field_sources=field_sources,
        )
        daily_usage = await self._get_daily_usage_totals(organization_id)

        usage = {
            "requests_per_day": self._usage_item(
                limit=effective_limits.get("requests_per_day"),
                used=daily_usage["requests"],
                source=field_sources.get("requests_per_day", "unset"),
                window_seconds=86_400,
            ),
            "tokens_per_day": self._usage_item(
                limit=effective_limits.get("tokens_per_day"),
                used=daily_usage["tokens"],
                source=field_sources.get("tokens_per_day", "unset"),
                window_seconds=86_400,
            ),
            "requests_per_second": request_usage.get("requests_per_second"),
            "requests_per_minute": request_usage.get("requests_per_minute"),
        }

        return {
            "success": True,
            "organization_id": organization_id,
            "rate_limits": effective_limits,
            "usage": usage,
            "warnings": daily_usage["warnings"],
        }

    async def _resolve_effective_rate_limits(
        self,
        organization_id: Optional[str],
        key_id: Optional[str],
    ) -> tuple[Dict[str, Optional[int]], Dict[str, str]]:
        org_limits = await self._get_org_rate_limits(organization_id)
        key_limits: Optional[Dict[str, Any]] = {}
        if organization_id and key_id:
            key_limits = await self.repository.get_api_key_rate_limits(organization_id, key_id)
        return merge_rate_limits(org_limits, key_limits)

    async def _get_org_rate_limits(
        self, organization_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        if not organization_id:
            return {}
        if not self.organization_service_client:
            return {}
        return await self.organization_service_client.get_org_rate_limits(organization_id)

    async def _enforce_request_limits(
        self,
        *,
        organization_id: Optional[str],
        key_id: Optional[str],
        effective_limits: Dict[str, Optional[int]],
        field_sources: Dict[str, str],
    ):
        if not organization_id or not key_id:
            return None
        try:
            await self.request_rate_limiter.enforce(
                organization_id=organization_id,
                key_id=key_id,
                effective_limits=effective_limits,
                field_sources=field_sources,
            )
            return None
        except RequestRateLimitExceeded as exc:
            return exc

    async def _get_daily_usage_totals(self, organization_id: str) -> Dict[str, Any]:
        period_end = datetime.now(timezone.utc)
        period_start = period_end.replace(hour=0, minute=0, second=0, microsecond=0)
        warnings: List[str] = []

        try:
            response = await self._billing_http_client.get(
                f"{self.billing_base_url}/api/v1/billing/usage/aggregations",
                params={
                    "organization_id": organization_id,
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "period_type": "daily",
                    "limit": 1,
                },
            )
            response.raise_for_status()
            payload = response.json()
            aggregations = payload.get("aggregations") or []
            return {
                "requests": sum(int(row.get("total_usage_count") or 0) for row in aggregations),
                "tokens": sum(int(float(row.get("total_usage_amount") or 0)) for row in aggregations),
                "warnings": warnings,
            }
        except Exception as e:
            logger.warning(f"Failed to fetch daily usage totals for {organization_id}: {e}")
            warnings.append("billing_usage_unavailable")
            return {"requests": 0, "tokens": 0, "warnings": warnings}

    @staticmethod
    def _usage_item(
        *,
        limit: Optional[int],
        used: int,
        source: str,
        window_seconds: int,
    ) -> Dict[str, Any]:
        remaining = None if limit is None else max(int(limit) - int(used), 0)
        percentage = None
        if limit not in (None, 0):
            percentage = round(min(100.0, (int(used) / int(limit)) * 100), 2)
        return {
            "limit": int(limit) if limit is not None else None,
            "used": int(used),
            "remaining": remaining,
            "source": source,
            "window_seconds": window_seconds,
            "percentage": percentage,
        }
