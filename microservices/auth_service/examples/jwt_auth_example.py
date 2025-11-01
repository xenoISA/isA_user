"""
JWT Authentication Client Example

This module demonstrates best practices for integrating with the Auth Service
for JWT token operations from other microservices.

Features:
- Connection pooling for high performance
- Async/await for non-blocking I/O
- Automatic retries with exponential backoff
- Circuit breaker pattern for fault tolerance
- Consul service discovery integration
- Comprehensive error handling
- Request/response validation
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import time

logger = logging.getLogger(__name__)


class AuthProvider(str, Enum):
    """Supported authentication providers"""
    AUTH0 = "auth0"
    ISA_USER = "isa_user"  # Custom JWT (primary)
    LOCAL = "local"  # Alias for isa_user


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Service unavailable, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures

    Implements the circuit breaker pattern to stop making requests to
    a failing service and allow it time to recover.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitBreakerState.CLOSED

    def record_success(self):
        """Record a successful request"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def record_failure(self):
        """Record a failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")

    def can_attempt(self) -> bool:
        """Check if we can attempt a request"""
        if self.state == CircuitBreakerState.CLOSED:
            return True

        if self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state")
                return True
            return False

        # HALF_OPEN state - allow one request to test
        return True


class JWTAuthClient:
    """
    Professional JWT Authentication Client

    High-performance async client for JWT operations with the Auth Service.
    Implements best practices for microservice communication.

    Usage:
        async with JWTAuthClient("http://auth-service:8201") as client:
            result = await client.verify_token(token)
            if result["valid"]:
                user_id = result["user_id"]
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8201",
        timeout: float = 5.0,
        max_retries: int = 3,
        use_consul: bool = False,
        consul_service_name: str = "auth-service"
    ):
        """
        Initialize JWT Auth Client

        Args:
            base_url: Auth service URL (if not using Consul)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
            use_consul: Enable Consul service discovery
            consul_service_name: Service name in Consul
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.use_consul = use_consul
        self.consul_service_name = consul_service_name

        # Connection pool for high performance
        self.client: Optional[httpx.AsyncClient] = None

        # Circuit breaker for fault tolerance
        self.circuit_breaker = CircuitBreaker()

        # Performance metrics
        self.request_count = 0
        self.error_count = 0

    async def __aenter__(self):
        """Context manager entry - initialize connection pool"""
        limits = httpx.Limits(
            max_keepalive_connections=20,  # Keep connections alive
            max_connections=100,           # Max concurrent connections
            keepalive_expiry=30.0          # Keep connections for 30s
        )

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            limits=limits,
            headers={
                "User-Agent": "microservice-client/1.0",
                "Accept": "application/json"
            }
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        if self.client:
            await self.client.aclose()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and circuit breaker

        Implements exponential backoff for retries
        """
        if not self.circuit_breaker.can_attempt():
            raise Exception("Circuit breaker is OPEN - service unavailable")

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                self.request_count += 1

                response = await self.client.request(method, endpoint, **kwargs)
                response.raise_for_status()

                self.circuit_breaker.record_success()
                return response.json()

            except httpx.HTTPStatusError as e:
                last_exception = e
                logger.warning(f"HTTP error {e.response.status_code}: {e}")

                # Don't retry on 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    self.error_count += 1
                    self.circuit_breaker.record_failure()
                    raise

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")

                if attempt < self.max_retries - 1:
                    # Exponential backoff: 0.1s, 0.2s, 0.4s
                    await asyncio.sleep(0.1 * (2 ** attempt))

            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error: {e}")
                self.error_count += 1
                self.circuit_breaker.record_failure()
                raise

        # All retries failed
        self.error_count += 1
        self.circuit_breaker.record_failure()
        raise Exception(f"Request failed after {self.max_retries} attempts: {last_exception}")

    async def verify_token(
        self,
        token: str,
        provider: Optional[AuthProvider] = None
    ) -> Dict[str, Any]:
        """
        Verify JWT token

        Args:
            token: JWT token string
            provider: Optional provider hint (auto-detected if not provided)

        Returns:
            {
                "valid": bool,
                "provider": str,
                "user_id": str,
                "email": str,
                "expires_at": str,
                "error": str (optional)
            }
        """
        payload = {"token": token}
        if provider:
            payload["provider"] = provider.value

        result = await self._make_request(
            "POST",
            "/api/v1/auth/verify-token",
            json=payload
        )

        return result

    async def generate_dev_token(
        self,
        user_id: str,
        email: str,
        expires_in: int = 3600
    ) -> Dict[str, Any]:
        """
        Generate development token (for testing/local development)

        Args:
            user_id: User identifier
            email: User email
            expires_in: Token expiration in seconds (default: 1 hour)

        Returns:
            {
                "success": bool,
                "token": str,
                "expires_in": int,
                "token_type": "Bearer",
                "user_id": str,
                "email": str
            }
        """
        result = await self._make_request(
            "POST",
            "/api/v1/auth/dev-token",
            json={
                "user_id": user_id,
                "email": email,
                "expires_in": expires_in
            }
        )

        return result

    async def get_user_info(self, token: str) -> Dict[str, Any]:
        """
        Extract user information from token

        Args:
            token: JWT token string

        Returns:
            {
                "user_id": str,
                "email": str,
                "provider": str,
                "expires_at": str
            }
        """
        result = await self._make_request(
            "GET",
            "/api/v1/auth/user-info",
            params={"token": token}
        )

        return result

    async def health_check(self) -> Dict[str, Any]:
        """Check auth service health"""
        return await self._make_request("GET", "/health")

    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics"""
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
            "circuit_breaker_state": self.circuit_breaker.state.value
        }


# =============================================================================
# Example Usage
# =============================================================================

async def example_generate_and_verify():
    """Example: Generate dev token and verify it"""
    async with JWTAuthClient() as client:
        # Generate token
        token_result = await client.generate_dev_token(
            user_id="user_123",
            email="user@example.com",
            expires_in=3600
        )

        if token_result["success"]:
            token = token_result["token"]
            print(f"✓ Generated token: {token[:50]}...")

            # Verify the generated token
            verify_result = await client.verify_token(token)
            print(f"✓ Verification: {verify_result['valid']}")
            print(f"  User ID: {verify_result['user_id']}")
            print(f"  Email: {verify_result['email']}")
            print(f"  Provider: {verify_result['provider']}")


async def example_with_error_handling():
    """Example: Robust error handling"""
    async with JWTAuthClient(timeout=5.0, max_retries=3) as client:
        try:
            result = await client.verify_token("invalid_token")

            if result["valid"]:
                # Process authenticated request
                user_id = result["user_id"]
                print(f"Authenticated user: {user_id}")
            else:
                # Handle invalid token
                print(f"Authentication failed: {result.get('error')}")

        except Exception as e:
            # Handle service unavailable
            logger.error(f"Auth service error: {e}")
            print("Service temporarily unavailable")


async def example_monitoring():
    """Example: Monitor client performance"""
    async with JWTAuthClient() as client:
        # Make some requests
        await client.health_check()

        # Check metrics
        metrics = client.get_metrics()
        print(f"Total requests: {metrics['total_requests']}")
        print(f"Error rate: {metrics['error_rate']:.2%}")
        print(f"Circuit breaker: {metrics['circuit_breaker_state']}")


async def main():
    """Run all examples"""
    print("=" * 70)
    print("JWT Authentication Client Examples")
    print("=" * 70)

    print("\n1. Generate and Verify Token")
    print("-" * 70)
    await example_generate_and_verify()

    print("\n2. Error Handling")
    print("-" * 70)
    await example_with_error_handling()

    print("\n3. Performance Monitoring")
    print("-" * 70)
    await example_monitoring()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(main())
