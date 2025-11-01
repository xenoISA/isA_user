"""
API Key Management Client Example

Professional client for API key operations with caching and performance optimizations.
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import hashlib
import time

logger = logging.getLogger(__name__)


@dataclass
class ApiKeyInfo:
    """API key validation result"""
    valid: bool
    key_id: Optional[str] = None
    organization_id: Optional[str] = None
    name: Optional[str] = None
    permissions: List[str] = None
    error: Optional[str] = None


class ApiKeyCache:
    """LRU cache for API key validation results"""

    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.cache: Dict[str, tuple[ApiKeyInfo, float]] = {}
        self.max_size = max_size
        self.ttl = ttl
        self.hits = 0
        self.misses = 0

    def _hash_key(self, api_key: str) -> str:
        return hashlib.sha256(api_key.encode()).hexdigest()

    def get(self, api_key: str) -> Optional[ApiKeyInfo]:
        key_hash = self._hash_key(api_key)
        if key_hash in self.cache:
            info, timestamp = self.cache[key_hash]
            if time.time() - timestamp < self.ttl:
                self.hits += 1
                return info
            else:
                del self.cache[key_hash]
        self.misses += 1
        return None

    def set(self, api_key: str, info: ApiKeyInfo):
        if not info.valid:
            return  # Don't cache invalid keys
        key_hash = self._hash_key(api_key)
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.items(), key=lambda x: x[1][1])[0]
            del self.cache[oldest_key]
        self.cache[key_hash] = (info, time.time())

    def get_stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total > 0 else 0
        }


class ApiKeyClient:
    """Professional API Key Management Client"""

    def __init__(
        self,
        base_url: str = "http://localhost:8201",
        timeout: float = 5.0,
        max_retries: int = 3,
        enable_cache: bool = True,
        cache_ttl: int = 300
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.client: Optional[httpx.AsyncClient] = None
        self.cache = ApiKeyCache(ttl=cache_ttl) if enable_cache else None
        self.request_count = 0
        self.error_count = 0

    async def __aenter__(self):
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0
        )
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            limits=limits,
            headers={
                "User-Agent": "api-key-client/1.0",
                "Accept": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                self.request_count += 1
                response = await self.client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                last_exception = e
                if 400 <= e.response.status_code < 500:
                    self.error_count += 1
                    try:
                        return e.response.json()
                    except:
                        raise
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.1 * (2 ** attempt))
            except Exception as e:
                last_exception = e
                self.error_count += 1
                raise
        self.error_count += 1
        raise Exception(f"Request failed after {self.max_retries} attempts: {last_exception}")

    async def verify_api_key(self, api_key: str) -> ApiKeyInfo:
        """Verify API key with caching"""
        if self.cache:
            cached = self.cache.get(api_key)
            if cached:
                return cached

        result = await self._make_request(
            "POST",
            "/api/v1/auth/verify-api-key",
            json={"api_key": api_key}
        )

        info = ApiKeyInfo(
            valid=result.get("valid", False),
            key_id=result.get("key_id"),
            organization_id=result.get("organization_id"),
            name=result.get("name"),
            permissions=result.get("permissions", []),
            error=result.get("error")
        )

        if self.cache and info.valid:
            self.cache.set(api_key, info)

        return info

    async def create_api_key(
        self,
        organization_id: str,
        name: str,
        permissions: List[str],
        expires_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create new API key"""
        payload = {
            "organization_id": organization_id,
            "name": name,
            "permissions": permissions
        }
        if expires_days is not None:
            payload["expires_days"] = expires_days

        return await self._make_request("POST", "/api/v1/auth/api-keys", json=payload)

    async def list_api_keys(self, organization_id: str) -> List[Dict[str, Any]]:
        """List organization API keys"""
        result = await self._make_request("GET", f"/api/v1/auth/api-keys/{organization_id}")
        return result.get("api_keys", [])

    async def revoke_api_key(self, key_id: str, organization_id: str) -> bool:
        """Revoke API key"""
        result = await self._make_request(
            "DELETE",
            f"/api/v1/auth/api-keys/{key_id}",
            params={"organization_id": organization_id}
        )
        return result.get("success", False)

    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics"""
        metrics = {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0
        }
        if self.cache:
            metrics["cache"] = self.cache.get_stats()
        return metrics


# Example Usage
async def main():
    print("=" * 70)
    print("API Key Management Client Examples")
    print("=" * 70)

    async with ApiKeyClient(enable_cache=True) as client:
        # Example 1: Create API key
        print("\n1. Creating API Key")
        print("-" * 70)
        create_result = await client.create_api_key(
            organization_id="org_df12fb0e7a8e",
            name=f"Example Key {int(time.time())}",
            permissions=["read", "write", "admin"],
            expires_days=365
        )

        if create_result.get("success"):
            api_key = create_result["api_key"]
            key_id = create_result["key_id"]
            print(f"✓ Created API key: {api_key[:20]}...")
            print(f"  Key ID: {key_id}")
            print(f"  ⚠️  Save this key - shown only once!")

            # Example 2: Verify API key
            print("\n2. Verifying API Key")
            print("-" * 70)
            verify_result = await client.verify_api_key(api_key)
            if verify_result.valid:
                print(f"✓ Key verified successfully")
                print(f"  Organization: {verify_result.organization_id}")
                print(f"  Permissions: {verify_result.permissions}")

            # Example 3: List keys
            print("\n3. Listing Organization Keys")
            print("-" * 70)
            keys = await client.list_api_keys("org_df12fb0e7a8e")
            print(f"Found {len(keys)} API keys:")
            for key in keys[:3]:  # Show first 3
                status = "🟢" if key.get("is_active") else "🔴"
                print(f"  {status} {key['name']} (ID: {key['key_id']})")

            # Example 4: Cache performance
            print("\n4. Cache Performance Test")
            print("-" * 70)
            start = time.time()
            await client.verify_api_key(api_key)
            time1 = time.time() - start

            start = time.time()
            await client.verify_api_key(api_key)
            time2 = time.time() - start

            print(f"First request: {time1*1000:.2f}ms (cache miss)")
            print(f"Second request: {time2*1000:.2f}ms (cache hit)")
            print(f"Speed improvement: {time1/time2:.1f}x faster")

            # Show metrics
            print("\n5. Client Metrics")
            print("-" * 70)
            metrics = client.get_metrics()
            print(f"Total requests: {metrics['total_requests']}")
            print(f"Error rate: {metrics['error_rate']:.1%}")
            if 'cache' in metrics:
                print(f"Cache hit rate: {metrics['cache']['hit_rate']:.1%}")

        else:
            print(f"✗ Failed to create key: {create_result.get('error')}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
