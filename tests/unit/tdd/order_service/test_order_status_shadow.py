"""Unit tests for order_service status parameter shadowing bug (Issue #138).

The `list_orders` endpoint has a query parameter named `status` which shadows
`fastapi.status` in the except block, causing AttributeError when an error occurs.
"""

import ast
import pytest


class TestOrderServiceStatusShadow:
    """Verify that order_service error handlers don't use shadowed `status` variable."""

    def test_list_orders_error_handler_does_not_use_status_attribute(self):
        """The except block in list_orders must not reference status.HTTP_*."""
        import inspect
        from microservices.order_service import main as order_main

        source = inspect.getsource(order_main)
        tree = ast.parse(source)

        # Find the list_orders function
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "list_orders":
                # Check all exception handlers in this function
                for child in ast.walk(node):
                    if isinstance(child, ast.ExceptHandler):
                        # Look for status.HTTP_ references in the handler
                        for exc_node in ast.walk(child):
                            if isinstance(exc_node, ast.Attribute) and \
                               isinstance(exc_node.value, ast.Name) and \
                               exc_node.value.id == "status" and \
                               exc_node.attr.startswith("HTTP_"):
                                pytest.fail(
                                    "list_orders except block references 'status.HTTP_*' "
                                    "but 'status' is shadowed by the query parameter. "
                                    "Use a literal status code (e.g., 500) instead."
                                )

    def test_complete_order_error_handler_does_not_use_status_attribute(self):
        """The except block in complete_order also has the same pattern — verify it's safe."""
        import inspect
        from microservices.order_service import main as order_main

        source = inspect.getsource(order_main)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "complete_order":
                for child in ast.walk(node):
                    if isinstance(child, ast.ExceptHandler):
                        for exc_node in ast.walk(child):
                            if isinstance(exc_node, ast.Attribute) and \
                               isinstance(exc_node.value, ast.Name) and \
                               exc_node.value.id == "status" and \
                               exc_node.attr.startswith("HTTP_"):
                                pytest.fail(
                                    "complete_order except block references 'status.HTTP_*' "
                                    "but 'status' may be shadowed. Use a literal status code."
                                )
