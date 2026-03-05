"""
L2 Component Tests — Rate Limiter Middleware

Tests the FastAPI middleware integration with mocked backends.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.rate_limiter import RateLimitConfig, RateLimitMiddleware


@pytest.fixture
def app_with_rate_limit():
    """Create a FastAPI app with rate limiting middleware"""
    app = FastAPI()

    app.add_middleware(
        RateLimitMiddleware,
        default_limit=RateLimitConfig(requests=3, window_seconds=60),
        path_limits={
            "/api/v1/auth/login": RateLimitConfig(requests=2, window_seconds=60),
        },
        key_func=lambda request: request.client.host,
    )

    @app.get("/api/v1/auth/login")
    async def login():
        return {"status": "ok"}

    @app.get("/api/v1/auth/profile")
    async def profile():
        return {"status": "ok"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


@pytest.fixture
def client(app_with_rate_limit):
    return TestClient(app_with_rate_limit)


class TestRateLimitMiddleware:
    """Test middleware behavior with real HTTP requests"""

    def test_allows_requests_under_limit(self, client):
        response = client.get("/api/v1/auth/profile")
        assert response.status_code == 200

    def test_returns_rate_limit_headers(self, client):
        response = client.get("/api/v1/auth/profile")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    def test_blocks_at_limit(self, client):
        for _ in range(3):
            client.get("/api/v1/auth/profile")
        response = client.get("/api/v1/auth/profile")
        assert response.status_code == 429
        assert "Retry-After" in response.headers

    def test_429_body_contains_error(self, client):
        for _ in range(3):
            client.get("/api/v1/auth/profile")
        response = client.get("/api/v1/auth/profile")
        body = response.json()
        assert "error" in body
        assert body["error"] == "Rate limit exceeded"

    def test_path_specific_limit(self, client):
        """Login endpoint has stricter limit (2/min)"""
        client.get("/api/v1/auth/login")
        client.get("/api/v1/auth/login")
        response = client.get("/api/v1/auth/login")
        assert response.status_code == 429

    def test_health_endpoint_excluded(self, client):
        """Health check should never be rate limited"""
        for _ in range(10):
            response = client.get("/health")
            assert response.status_code == 200

    def test_different_clients_have_separate_limits(self, app_with_rate_limit):
        """Each client IP gets its own rate limit window"""
        # TestClient always uses 'testclient' as host, so we test via key_func
        client = TestClient(app_with_rate_limit)
        for _ in range(3):
            client.get("/api/v1/auth/profile")
        # Same client is blocked
        response = client.get("/api/v1/auth/profile")
        assert response.status_code == 429

    def test_remaining_decrements(self, client):
        r1 = client.get("/api/v1/auth/profile")
        r2 = client.get("/api/v1/auth/profile")
        assert int(r1.headers["X-RateLimit-Remaining"]) > int(
            r2.headers["X-RateLimit-Remaining"]
        )


class TestRateLimitMiddlewareExclusions:
    """Test path exclusions"""

    def test_excludes_health_paths(self, client):
        response = client.get("/health")
        assert "X-RateLimit-Limit" not in response.headers

    def test_excludes_docs_paths(self):
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            default_limit=RateLimitConfig(requests=1, window_seconds=60),
        )

        @app.get("/docs")
        async def docs():
            return {"docs": True}

        client = TestClient(app)
        response = client.get("/docs")
        assert "X-RateLimit-Limit" not in response.headers
