"""
JWT pass-through tests for the remaining memory extract services.

Mirrors test_factual_jwt_passthrough.py (PR xenoISA/isA_user#468) and
test_summary_service_synthesis.py (PR #454). When the route receives an
Authorization header, the extract path forwards it to AsyncISAModel via
extra_headers. When absent/empty, no extra_headers is attached (preserves
the service-level auth path).

Parametrized across episodic / semantic / procedural / working — closes
out the extract slice of xenoISA/isA_user#464.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# (service_name, module_path, class_name, extract_method, response_payload)
SERVICE_MATRIX = [
    (
        "episodic",
        "microservices.memory_service.episodic_service",
        "EpisodicMemoryService",
        "_extract_episodes",
        {"episodes": []},
    ),
    (
        "semantic",
        "microservices.memory_service.semantic_service",
        "SemanticMemoryService",
        "_extract_concepts",
        {"concepts": []},
    ),
    (
        "procedural",
        "microservices.memory_service.procedural_service",
        "ProceduralMemoryService",
        "_extract_procedures",
        {"procedures": []},
    ),
    (
        "working",
        "microservices.memory_service.working_service",
        "WorkingMemoryService",
        # working has no LLM extract step — the JWT is forwarded on
        # _generate_embedding (the only LLM call in the store path).
        "_generate_embedding",
        None,
    ),
]


def _make_service(module_path: str, class_name: str):
    """Build the service without hitting Qdrant/Postgres."""
    import importlib

    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    svc = cls.__new__(cls)
    svc.model_url = "http://isa-model:8082"
    svc.qdrant = MagicMock()
    svc._collection_initialized = True
    return svc


@pytest.fixture
def captured_init_kwargs(request):
    """Capture the kwargs passed to AsyncISAModel so each test can inspect
    extra_headers without mocking the whole inference protocol."""
    service_name, module_path, _, _, payload = request.param
    captured = {}

    class _StubClient:
        def __init__(self, **kwargs):
            captured["init_kwargs"] = kwargs
            # chat path (extract methods)
            self.chat = MagicMock()
            self.chat.completions = MagicMock()
            self.chat.completions.create = AsyncMock(
                return_value=MagicMock(
                    choices=[
                        MagicMock(message=MagicMock(content=json.dumps(payload) if payload is not None else "{}"))
                    ],
                    usage=MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                )
            )
            # embeddings path (working._generate_embedding)
            self.embeddings = MagicMock()
            self.embeddings.create = AsyncMock(return_value=MagicMock(data=[MagicMock(embedding=[0.0] * 1536)]))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a, **kw):
            return False

    with patch(f"{module_path}.AsyncISAModel", new=_StubClient):
        yield captured


@pytest.mark.parametrize(
    "captured_init_kwargs",
    SERVICE_MATRIX,
    indirect=True,
    ids=[row[0] for row in SERVICE_MATRIX],
)
async def test_extract_forwards_auth_header_to_llm(captured_init_kwargs, request):
    service_name, module_path, class_name, method_name, _ = request.node.callspec.params["captured_init_kwargs"]
    svc = _make_service(module_path, class_name)
    method = getattr(svc, method_name)
    await method("alice said hi", auth_token="test-jwt")
    assert captured_init_kwargs["init_kwargs"]["extra_headers"] == {"Authorization": "Bearer test-jwt"}, (
        f"{service_name}.{method_name} did not forward bearer header"
    )


@pytest.mark.parametrize(
    "captured_init_kwargs",
    SERVICE_MATRIX,
    indirect=True,
    ids=[row[0] for row in SERVICE_MATRIX],
)
async def test_extract_no_auth_header_uses_default(captured_init_kwargs, request):
    """Empty / None token → no extra_headers attached → upstream uses default auth."""
    service_name, module_path, class_name, method_name, _ = request.node.callspec.params["captured_init_kwargs"]
    svc = _make_service(module_path, class_name)
    method = getattr(svc, method_name)

    await method("alice said hi")
    assert "extra_headers" not in captured_init_kwargs["init_kwargs"], (
        f"{service_name}.{method_name} leaked extra_headers when no token given"
    )

    await method("alice said hi", auth_token=None)
    assert "extra_headers" not in captured_init_kwargs["init_kwargs"], (
        f"{service_name}.{method_name} leaked extra_headers when token=None"
    )

    await method("alice said hi", auth_token="   ")
    assert "extra_headers" not in captured_init_kwargs["init_kwargs"], (
        f"{service_name}.{method_name} leaked extra_headers when token is whitespace"
    )


@pytest.mark.parametrize(
    "captured_init_kwargs",
    SERVICE_MATRIX,
    indirect=True,
    ids=[row[0] for row in SERVICE_MATRIX],
)
async def test_extract_bare_jwt_gets_bearer_prefix(captured_init_kwargs, request):
    """Tokens that already have 'Bearer ' aren't double-prefixed; bare JWTs get one."""
    service_name, module_path, class_name, method_name, _ = request.node.callspec.params["captured_init_kwargs"]
    svc = _make_service(module_path, class_name)
    method = getattr(svc, method_name)

    await method("x", auth_token="raw-jwt-without-prefix")
    assert captured_init_kwargs["init_kwargs"]["extra_headers"]["Authorization"] == "Bearer raw-jwt-without-prefix", (
        f"{service_name}.{method_name} did not add Bearer prefix to bare JWT"
    )

    await method("x", auth_token="Bearer already-prefixed")
    assert captured_init_kwargs["init_kwargs"]["extra_headers"]["Authorization"] == "Bearer already-prefixed", (
        f"{service_name}.{method_name} double-prefixed Bearer token"
    )
