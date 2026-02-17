"""
HTTP Client Mock for Component Testing

Mocks httpx.AsyncClient for testing inter-service HTTP calls.
"""
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock


class MockHttpResponse:
    """Mock HTTP response"""

    def __init__(
        self,
        status_code: int = 200,
        json_data: Optional[Dict[str, Any]] = None,
        text: str = "",
        headers: Optional[Dict[str, str]] = None
    ):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text or str(json_data)
        self.headers = headers or {}
        self.content = text.encode() if text else b""

    def json(self) -> Dict[str, Any]:
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}: {self.text}")


class MockHttpClient:
    """Mock for httpx.AsyncClient"""

    def __init__(self):
        self.requests: List[Dict[str, Any]] = []
        self._responses: Dict[str, MockHttpResponse] = {}
        self._default_response = MockHttpResponse(200, {"success": True})
        self._should_raise: Optional[Exception] = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def get(self, url: str, **kwargs) -> MockHttpResponse:
        """Mock GET request"""
        return await self._make_request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> MockHttpResponse:
        """Mock POST request"""
        return await self._make_request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> MockHttpResponse:
        """Mock PUT request"""
        return await self._make_request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> MockHttpResponse:
        """Mock DELETE request"""
        return await self._make_request("DELETE", url, **kwargs)

    async def patch(self, url: str, **kwargs) -> MockHttpResponse:
        """Mock PATCH request"""
        return await self._make_request("PATCH", url, **kwargs)

    async def _make_request(self, method: str, url: str, **kwargs) -> MockHttpResponse:
        """Internal request handler"""
        self.requests.append({
            "method": method,
            "url": url,
            **kwargs
        })

        if self._should_raise:
            raise self._should_raise

        # Check for specific URL response
        key = f"{method}:{url}"
        if key in self._responses:
            return self._responses[key]

        # Check for pattern match
        for pattern, response in self._responses.items():
            if "*" in pattern:
                method_pattern, url_pattern = pattern.split(":", 1)
                if method_pattern == method and self._url_matches(url, url_pattern):
                    return response

        return self._default_response

    def _url_matches(self, url: str, pattern: str) -> bool:
        """Simple URL pattern matching"""
        import fnmatch
        return fnmatch.fnmatch(url, pattern)

    # Test helper methods

    def set_response(
        self,
        method: str,
        url: str,
        status_code: int = 200,
        json_data: Optional[Dict[str, Any]] = None,
        text: str = ""
    ):
        """Set response for specific method and URL"""
        key = f"{method}:{url}"
        self._responses[key] = MockHttpResponse(status_code, json_data, text)

    def set_default_response(
        self,
        status_code: int = 200,
        json_data: Optional[Dict[str, Any]] = None
    ):
        """Set default response for unmatched requests"""
        self._default_response = MockHttpResponse(status_code, json_data)

    def set_error(self, error: Exception):
        """Set an error to be raised on next request"""
        self._should_raise = error

    def clear_error(self):
        """Clear any pending error"""
        self._should_raise = None

    def get_requests(self, method: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recorded requests, optionally filtered by method"""
        if method:
            return [r for r in self.requests if r["method"] == method]
        return self.requests

    def get_last_request(self) -> Optional[Dict[str, Any]]:
        """Get the last recorded request"""
        return self.requests[-1] if self.requests else None

    def clear_requests(self):
        """Clear recorded requests"""
        self.requests.clear()

    def assert_request_made(self, method: str, url_pattern: str):
        """Assert that a request was made"""
        for req in self.requests:
            if req["method"] == method and self._url_matches(req["url"], url_pattern):
                return req
        raise AssertionError(
            f"No {method} request matching '{url_pattern}' was made. Requests: {self.requests}"
        )

    def assert_no_requests(self):
        """Assert that no requests were made"""
        assert len(self.requests) == 0, f"Expected no requests, but got: {self.requests}"
