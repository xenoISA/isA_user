"""
Product Service Client Example

Professional client for product catalog operations with caching and performance optimizations.
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import time

logger = logging.getLogger(__name__)


@dataclass
class ProductInfo:
    """Product information"""
    product_id: str
    name: str
    description: str
    product_type: str
    provider: str
    is_active: bool
    category_id: str


@dataclass
class PricingInfo:
    """Product pricing information"""
    product: Dict[str, Any]
    pricing_model: Dict[str, Any]
    effective_pricing: Dict[str, Any]


class ProductClient:
    """Professional Product Service Client"""

    def __init__(
        self,
        base_url: str = "http://localhost:8215",
        timeout: float = 10.0,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.client: Optional[httpx.AsyncClient] = None
        self.request_count = 0
        self.error_count = 0

    async def __aenter__(self):
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=60.0
        )
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            limits=limits,
            headers={
                "User-Agent": "product-client/1.0",
                "Accept": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
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
                        error_detail = e.response.json()
                        raise Exception(error_detail.get("detail", str(e)))
                    except:
                        raise Exception(str(e))
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.2 * (2 ** attempt))
            except Exception as e:
                last_exception = e
                self.error_count += 1
                raise
        self.error_count += 1
        raise Exception(f"Request failed after {self.max_retries} attempts: {last_exception}")

    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        return await self._make_request("GET", "/health")

    async def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        return await self._make_request("GET", "/api/v1/info")

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get all product categories"""
        return await self._make_request("GET", "/api/v1/categories")

    async def get_products(
        self,
        category_id: Optional[str] = None,
        product_type: Optional[str] = None,
        is_active: bool = True
    ) -> List[Dict[str, Any]]:
        """Get products with optional filtering"""
        params = {"is_active": is_active}
        if category_id:
            params["category_id"] = category_id
        if product_type:
            params["product_type"] = product_type

        return await self._make_request(
            "GET",
            "/api/v1/products",
            params=params
        )

    async def get_product(self, product_id: str) -> Dict[str, Any]:
        """Get single product details"""
        return await self._make_request(
            "GET",
            f"/api/v1/products/{product_id}"
        )

    async def get_product_pricing(
        self,
        product_id: str,
        user_id: Optional[str] = None,
        subscription_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get product pricing information"""
        params = {}
        if user_id:
            params["user_id"] = user_id
        if subscription_id:
            params["subscription_id"] = subscription_id

        return await self._make_request(
            "GET",
            f"/api/v1/products/{product_id}/pricing",
            params=params
        )

    async def check_product_availability(
        self,
        product_id: str,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check if product is available for user"""
        params = {"user_id": user_id}
        if organization_id:
            params["organization_id"] = organization_id

        return await self._make_request(
            "GET",
            f"/api/v1/products/{product_id}/availability",
            params=params
        )

    async def get_service_statistics(self) -> Dict[str, Any]:
        """Get service statistics"""
        return await self._make_request("GET", "/api/v1/statistics/service")

    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics"""
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0
        }


# Example Usage
async def main():
    print("=" * 70)
    print("Product Service Client Examples")
    print("=" * 70)

    async with ProductClient() as client:
        # Example 1: Health Check
        print("\n1. Health Check")
        print("-" * 70)
        health = await client.health_check()
        print(f"✓ Service: {health['service']}")
        print(f"  Status: {health['status']}")
        print(f"  Port: {health['port']}")

        # Example 2: Get Service Info
        print("\n2. Service Information")
        print("-" * 70)
        info = await client.get_service_info()
        print(f"✓ Service: {info['service']}")
        print(f"  Version: {info['version']}")
        print(f"  Capabilities: {', '.join(info['capabilities'])}")

        # Example 3: Get Product Categories
        print("\n3. Product Categories")
        print("-" * 70)
        categories = await client.get_categories()
        print(f"✓ Found {len(categories)} categories:")
        for cat in categories[:5]:
            print(f"  - {cat['name']} ({cat['category_id']})")

        # Example 4: Get All Products
        print("\n4. All Products")
        print("-" * 70)
        products = await client.get_products()
        print(f"✓ Found {len(products)} products:")
        for product in products[:5]:
            print(f"  - {product['name']} ({product['product_type']})")

        if products:
            product_id = products[0]['product_id']

            # Example 5: Get Product Details
            print("\n5. Product Details")
            print("-" * 70)
            product = await client.get_product(product_id)
            print(f"✓ Product: {product['name']}")
            print(f"  Type: {product['product_type']}")
            print(f"  Provider: {product['provider']}")
            print(f"  Active: {product['is_active']}")

            # Example 6: Get Product Pricing
            print("\n6. Product Pricing")
            print("-" * 70)
            try:
                pricing = await client.get_product_pricing(product_id)
                print(f"✓ Pricing for: {pricing['product']['name']}")
                print(f"  Pricing Type: {pricing['pricing_model']['pricing_type']}")
                print(f"  Currency: {pricing['pricing_model']['currency']}")
            except Exception as e:
                print(f"⚠ Pricing info not available: {e}")

            # Example 7: Check Product Availability
            print("\n7. Product Availability")
            print("-" * 70)
            test_user_id = "test_user_123"
            availability = await client.check_product_availability(
                product_id=product_id,
                user_id=test_user_id
            )
            print(f"✓ Available: {availability.get('available', False)}")
            if not availability.get('available'):
                print(f"  Reason: {availability.get('reason', 'Unknown')}")

        # Example 8: Get Products by Category
        if categories:
            print("\n8. Products by Category")
            print("-" * 70)
            category_id = categories[0]['category_id']
            category_products = await client.get_products(category_id=category_id)
            print(f"✓ Products in '{categories[0]['name']}':")
            for prod in category_products[:5]:
                print(f"  - {prod['name']}")

        # Example 9: Get Service Statistics
        print("\n9. Service Statistics")
        print("-" * 70)
        stats = await client.get_service_statistics()
        print(f"✓ Service: {stats['service']}")
        print(f"  Statistics:")
        for key, value in stats['statistics'].items():
            print(f"    {key}: {value}")

        # Show Client Metrics
        print("\n10. Client Performance Metrics")
        print("-" * 70)
        metrics = client.get_metrics()
        print(f"Total requests: {metrics['total_requests']}")
        print(f"Total errors: {metrics['total_errors']}")
        print(f"Error rate: {metrics['error_rate']:.2%}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
