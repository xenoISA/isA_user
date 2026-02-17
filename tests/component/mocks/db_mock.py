"""
Database Mock for Component Testing

Mocks AsyncPostgresClient for testing without real database connections.
"""
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock


class MockAsyncPostgresClient:
    """Mock for AsyncPostgresClient (gRPC-based PostgreSQL client)"""

    def __init__(self):
        self.queries: List[tuple] = []
        self._row_response: Optional[Dict[str, Any]] = None
        self._rows_response: List[Dict[str, Any]] = []
        self._execute_response: str = "OK"
        self._should_raise: Optional[Exception] = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def query_row(self, query: str, params: List[Any] = None) -> Optional[Dict[str, Any]]:
        """Mock single row query"""
        self.queries.append(("query_row", query, params or []))

        if self._should_raise:
            raise self._should_raise

        return self._row_response

    async def query(self, query: str, params: List[Any] = None) -> List[Dict[str, Any]]:
        """Mock multi-row query"""
        self.queries.append(("query", query, params or []))

        if self._should_raise:
            raise self._should_raise

        return self._rows_response

    async def execute(self, query: str, params: List[Any] = None) -> str:
        """Mock execute (INSERT/UPDATE/DELETE)"""
        self.queries.append(("execute", query, params or []))

        if self._should_raise:
            raise self._should_raise

        return self._execute_response

    # Test helper methods

    def set_row_response(self, row: Optional[Dict[str, Any]]):
        """Set the response for query_row calls"""
        self._row_response = row

    def set_rows_response(self, rows: List[Dict[str, Any]]):
        """Set the response for query calls"""
        self._rows_response = rows

    def set_execute_response(self, result: str):
        """Set the response for execute calls"""
        self._execute_response = result

    def set_error(self, error: Exception):
        """Set an error to be raised on next call"""
        self._should_raise = error

    def clear_error(self):
        """Clear any pending error"""
        self._should_raise = None

    def get_queries(self, method: Optional[str] = None) -> List[tuple]:
        """Get recorded queries, optionally filtered by method"""
        if method:
            return [q for q in self.queries if q[0] == method]
        return self.queries

    def get_last_query(self) -> Optional[tuple]:
        """Get the last recorded query"""
        return self.queries[-1] if self.queries else None

    def clear_queries(self):
        """Clear recorded queries"""
        self.queries.clear()

    def assert_query_executed(self, pattern: str, method: Optional[str] = None):
        """Assert that a query matching pattern was executed"""
        queries = self.get_queries(method)
        for q in queries:
            if pattern.lower() in q[1].lower():
                return True
        raise AssertionError(f"No query matching '{pattern}' was executed. Queries: {queries}")

    def assert_no_queries(self):
        """Assert that no queries were executed"""
        assert len(self.queries) == 0, f"Expected no queries, but got: {self.queries}"
