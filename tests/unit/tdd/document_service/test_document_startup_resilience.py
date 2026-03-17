"""Unit tests for document_service startup resilience (Issue #139).

The document_service crashes with RuntimeError during startup if the DB health
check fails. It should log a warning and continue with degraded status instead.
"""

import ast
import pytest


class TestDocumentServiceStartupResilience:
    """Verify that document_service lifespan does not crash on DB failure."""

    def test_lifespan_does_not_raise_on_db_failure(self):
        """The lifespan function must not raise RuntimeError when DB is unavailable."""
        import inspect
        from microservices.document_service import main as doc_main

        source = inspect.getsource(doc_main)
        tree = ast.parse(source)

        # Find the lifespan function
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "lifespan":
                # Check for `raise RuntimeError` with "Database connection failed"
                for child in ast.walk(node):
                    if isinstance(child, ast.Raise) and child.exc is not None:
                        if isinstance(child.exc, ast.Call):
                            func = child.exc.func
                            if isinstance(func, ast.Name) and func.id == "RuntimeError":
                                # Check if the message mentions database
                                for arg in child.exc.args:
                                    if isinstance(arg, ast.Constant) and \
                                       "database" in str(arg.value).lower():
                                        pytest.fail(
                                            "document_service lifespan raises RuntimeError "
                                            "on DB failure. Should log warning and continue."
                                        )
